# super_solver

Native ASCII-maze solver for the `maze_api` format, written in Rust and exposed
to Python via `ctypes` (stdlib only — no `maturin`, no `pyo3`, no `cffi`).

Drop-in replacement for `maze_api.solver.solve_ascii_maze`. Produces the
**same move sequence, byte for byte**, validated across every benchmark run.

## Why it is fast

Compared to `maze_api/solver.py` (baseline) and `solver_v1/solver.py`
(the prior 1D Python solver), the wins compound:

| Layer | baseline | solver_v1 (Python 1D) | super_solver (Rust) |
| --- | --- | --- | --- |
| Cell representation | `dataclass(frozen=True)` | int index into ASCII string | int index into packed grid |
| Passages | `dict[Cell, set[str]]` | implicit (scan walls on demand) | `Vec<u8>` with 4 bits per cell |
| Visited / parent | `dict` | `dict[int, (int, str)]` | contiguous `Vec<u8>` |
| Frontier | `collections.deque` | `collections.deque` | `Vec<u32>` + head pointer |
| Per-step work | many Python bytecodes | a few bytecodes per neighbor | a handful of inlined ops |
| Allocation profile | per-cell objects | one dict grows | two `Vec`s pre-sized to `N²` |

We also reduced the algorithm to **one** linear scan over the ASCII (parse +
boundary detection + start detection) and **one** BFS pass. No regex, no
splitting on `\n`, no second normalization pass.

## Build

```bash
cd super_solver
cargo build --release
```

Outputs `target/release/libsuper_solver.so`.

## Use from Python

```python
from super_solver import solve, solve_ascii_maze

moves = solve(ascii_maze)         # list[str]: ['E', 'E', 'S', ...]
result = solve_ascii_maze(text)   # dataclass with .moves and .elapsed_seconds
```

CLI parity with the baseline solver:

```bash
python3 super_solver.py --size 100 --seed 42
python3 super_solver.py --file maze.txt
curl http://127.0.0.1:8000/ascii | python3 super_solver.py --stdin
```

## Benchmark

```bash
python3 benchmarks/algo_benchmark.py    # pure compute time
python3 benchmarks/e2e_benchmark.py     # plays the live HTTP API
```

Sample (Python 3.14, Arch Linux, sizes 10/50/100/250/500, 8 seeds each,
best-of-3 per call):

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

The gap widens with size: at `N=500` the Rust BFS is ~238× over the Python
baseline and ~26× over the 1D Python solver — close to the ceiling the FFI
boundary lets us see from Python.

## ABI

```c
int32_t solve(
    const uint8_t* ascii_ptr,
    size_t          ascii_len,
    uint8_t*        out_ptr,
    size_t          out_cap
);
```

Returns the number of bytes written to `out_ptr` (the move string, ASCII
`N`/`S`/`E`/`W`), or a negative error code:

| code | meaning |
| --- | --- |
| -1 | invalid ASCII shape |
| -2 | no start marker (P/S) |
| -3 | no (or ambiguous) boundary exit |
| -4 | goal unreachable |
| -5 | output buffer too small |

## Files

- `src/lib.rs` — parser + BFS + reconstruction
- `super_solver.py` — `ctypes` wrapper, dataclass-shaped result, CLI
- `Cargo.toml` — release profile tuned for inlining (`lto="fat"`, single codegen unit)

Benchmarks live one level up in `benchmarks/`.
