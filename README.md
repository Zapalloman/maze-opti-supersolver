# Maze API + solver shoot-out

A small HTTP-controlled maze game (the **API**) plus **three solvers** built
on top of it, compared head to head.

The interesting question is not "can we solve a maze" — BFS does that — but
**how much performance can be squeezed out of the same algorithm** as you
move from naive Python to disciplined Python to native code.

## Layout

```
.
├── maze_api/        # the game: perfect n×n maze + HTTP server + baseline solver
│   ├── server.py        # generator + game state + HTTP handlers
│   ├── solver.py        # BFS over dataclasses + dict-of-sets  (baseline)
│   ├── test_api.py
│   └── test_solver.py
├── solver_v1/       # first custom solver — pure Python, 1D ASCII string BFS
│   ├── solver.py
│   └── README.md
├── super_solver/    # native Rust solver, packed-bit grid + contiguous arrays
│   ├── src/lib.rs
│   ├── super_solver.py  # ctypes wrapper (stdlib only)
│   ├── Cargo.toml
│   └── README.md
└── benchmarks/
    ├── algo_benchmark.py   # pure compute time, no HTTP
    └── e2e_benchmark.py    # plays the live HTTP API (reset → ascii → moves)
```

## The three solvers

| | author | language | data structures | key idea |
|---|---|---|---|---|
| `maze_api.solver` (baseline) | course material | Python | `dataclass(frozen=True) Cell`, `dict[Cell, set[str]]` | clean OOP BFS, one node = one object |
| `solver_v1` | mine, earlier | Python | `int` indices into the ASCII string, `dict[int, (int, str)]` | skip parsing — read wall characters on demand by integer offset |
| `super_solver` | mine, current | Rust + ctypes | `Vec<u8>` 4-bit packed passages, `Vec<u32>` BFS queue with head pointer | parse once into a packed grid, run BFS over contiguous memory, expose as `cdylib` to Python |

All three are validated **byte-for-byte against each other** on every benchmark
run. Same input, same output, different motor.

## Running the game

```bash
python3 -m maze_api 10 --seed 42
# Maze API listening on http://127.0.0.1:8000
```

Then `curl http://127.0.0.1:8000/state`, `/ascii`, `/move?direction=N`, etc.
See `maze_api/server.py` for the full endpoint list.

## Running each solver

```bash
# baseline
python3 -m maze_api.solver --size 50 --seed 42

# v1
python3 -m solver_v1.solver --size 50 --seed 42

# super (requires building once)
cd super_solver && cargo build --release && cd ..
python3 super_solver/super_solver.py --size 50 --seed 42
```

All three support `--file maze.txt` and `--stdin`.

## Benchmarks

### Algorithmic (no HTTP)

```bash
python3 benchmarks/algo_benchmark.py
```

```
 size   baseline (ms)       v1 (ms)    super (ms)      B/S      V/S
   10          0.36          0.05         0.005     76x      11x
   50          8.24          1.13         0.053    156x      21x
  100         37.55          5.93         0.252    149x      24x
  250        257.49         35.25         1.367    188x      26x
  500       1244.65        136.90         5.236    238x      26x

super is ~224x faster than baseline, ~26x faster than solver_v1.
All solver outputs match.
```

The gap widens with size: at 500×500 the Rust BFS is ~238× over baseline and
~26× over the 1D Python solver. That ~26× is essentially "CPython interpreter
overhead vs native code", since the algorithm is the same shape.

### End-to-end (plays the live HTTP API)

```bash
python3 benchmarks/e2e_benchmark.py
```

```
 size     solver   fetch (ms)   solve (ms)    play (ms)   total (ms)   moves
   50   baseline         3.91         9.83       457.87       471.61    1162
   50  solver_v1         4.00         1.61       461.32       466.93    1162
   50      super         3.98         0.13       464.38       468.49    1162

  200   baseline        57.46       164.18      3517.18      3738.83    8836
  200  solver_v1        57.20        23.03      3526.87      3607.09    8836
  200      super        57.68         0.96      3513.18      3571.81    8836
```

Reading this honestly:

- **`solve`** preserves the algorithmic gap: 0.96 ms vs 23 ms vs 164 ms at
  size 200. That's the comparison that matters for "which solver is faster".
- **`play`** is HTTP overhead — one round-trip per move. It's ~0.4 ms per
  move regardless of solver, because the bottleneck has moved from compute
  to localhost TCP + JSON. All three solvers pay the same cost here.
- **`total`** is therefore dominated by `play` past size ~50. Even a perfect
  zero-time solver would only shave ~5 % off the wall-clock at size 200.

That's not a flaw in `super_solver`; it's an upper bound the API design
imposes. Two ways to actually use the algorithmic win in wall-time:
- run the solver offline (download `/ascii`, compute, display), or
- add a `POST /moves` batch endpoint to the API (10 lines on top of
  `MazeGame`), so the round trip cost becomes O(1) instead of O(moves).

## Requirements

- Python 3.10+
- Rust toolchain (for `super_solver` only) — `cargo build --release` once,
  produces `super_solver/target/release/libsuper_solver.so`. The Python
  wrapper loads it through `ctypes` — no `maturin`, no `pyo3`, no `cffi`.
