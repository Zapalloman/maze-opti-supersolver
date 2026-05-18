# solver_v1

First iteration of a custom maze solver, written in pure Python.

## Idea

Skip building any graph. Treat the ASCII maze as a single 1D string and walk
it with integer offsets:

| Direction | Step to neighbor cell | Wall sample byte |
| --- | --- | --- |
| N | `idx - 2 * line_width` | `idx - line_width` |
| S | `idx + 2 * line_width` | `idx + line_width` |
| W | `idx - 4` | `idx - 2` |
| E | `idx + 4` | `idx + 2` |

A passage exists iff the wall byte is `' '`. BFS proceeds over `int` indices,
parents are stored in a `dict[int, (int, str)]`. No `Cell` objects, no
`dict[Cell, set[str]]`, no second normalization pass over the input.

Boundary openings (the maze's exit) are detected by checking whether the wall
index falls on the perimeter of the string: line 0, last line, column 0, or
column `line_width - 2`.

## Use

```python
from solver_v1 import solve

moves = solve(ascii_maze)  # returns ['E', 'E', 'S', ...]
```

CLI parity with the baseline:

```bash
python3 -m solver_v1.solver --size 50 --seed 42
python3 -m solver_v1.solver --file maze.txt
curl http://127.0.0.1:8000/ascii | python3 -m solver_v1.solver --stdin
```

## Why a v1

This solver got ~25× over the baseline by avoiding per-cell allocations. The
ceiling is CPython itself — each BFS step still pays bytecode overhead and a
dict lookup per visit. `super_solver/` rewrites the same algorithm in Rust to
break that ceiling.
