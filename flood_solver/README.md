# flood_solver — fastest pure-Python flood-fill maze solver

**Pure stdlib Python** (no Rust, no numpy, no deps), the *método de inundación*
(flood fill = BFS). Built to solve the maze in the least **time**, both on raw
compute and on the live HTTP game's **wall-clock**.

## Why pure Python, and where the win actually is

The earlier Rust `super_solver` is ~26× faster than the best Python solver on
raw compute — that gap is CPython interpreter overhead and **cannot** be closed
in pure Python on the same algorithm. So this solver does not try to out-compute
Rust. It wins where the final is actually decided:

1. **Fastest pure-Python compute** — beats the course baseline and `solver_v1`
   (the previous Python champion), so it stays ahead of ordinary Python code.
2. **Wall-clock of the live game** — past trivial sizes the wall-clock is
   dominated by HTTP round trips (≈one TCP setup per move; the stdlib server is
   HTTP/1.0 and closes each connection). There the Rust compute edge is
   *invisible*, and the winner is whoever issues **the fewest requests** and
   makes **the fewest physical moves**. This solver does both.

## The core: `solve(ascii) -> list[str]`

Flood BFS that floods outward from the start until it laps the boundary exit,
then walks the parent trail back. CPython-tuned:

- works on **`bytes`** (int compares `== 32`, not char compares);
- a cell is just the **integer byte-offset** of its centre — no objects, no
  graph, no dict; neighbours are fixed offsets;
- visited/parent state is **one flat `bytearray`** indexed by that offset →
  O(1) array access, zero hashing (the big win over `solver_v1`'s dict);
- the unique exit is found with four C-level slice scans, so there is no
  per-step boundary test in the hot loop;
- the 4-neighbour expansion is hand-unrolled with every hot name bound local.

Output is **byte-for-byte identical** to the course baseline (validated in
`test_flood.py` across sizes 1–64 × 12 seeds).

`solve_bidirectional(ascii)` floods from both start and exit and meets in the
middle. Because the maze is a perfect maze (a tree) the meeting point lies on
the unique path, so it returns the same shortest path; useful when the start is
the farthest cell from the exit (the generator's default), where a single
source must explore almost everything.

## Playing the live API

```bash
# fastest legal wall-clock: read the map once, replay the shortest path
python3 flood_solver/solver.py --play --host 127.0.0.1 --port 8000

# blind / Micromouse: never read /ascii, explore with flood fill via /move only
python3 flood_solver/solver.py --blind --host 127.0.0.1 --port 8000
```

`--play` does `GET /ascii` once, solves instantly, then **1** `POST /move` per
move (no `/state` spam). `--blind` learns walls only from `/move` responses and
stores **only visited cells** (O(path) memory, not O(N²)) — the mode that scales
toward the "10⁶" mazes whose full ASCII (~8 TB at 10⁶ per side) could never fit
in memory.

## Offline use / parity with the other solvers

```bash
python3 flood_solver/solver.py --size 500 --seed 42        # generate + solve
python3 flood_solver/solver.py --file maze.txt
curl -s localhost:8000/ascii | python3 flood_solver/solver.py --stdin
python3 flood_solver/solver.py --size 500 --seed 42 --bidir # bidirectional
```

```python
from flood_solver import solve
moves = solve(open("maze.txt","rb").read())   # ['E','E','S', ...]
```

## Comparación y pruebas

```bash
python3 comparacion.py                  # original vs flood (desde la raiz del repo)
python3 flood_solver/compare.py         # comparacion con varios tamanos
python3 -m flood_solver.test_flood      # verifica que el resultado sea correcto
```
