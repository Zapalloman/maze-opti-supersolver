# Benchmarks

Two harnesses, two questions.

## `algo_benchmark.py` — pure algorithm time

Each solver receives the same in-memory ASCII payload and returns a list of
moves. We time only the `solve(...)` call (best-of-N), no HTTP, no I/O.

```bash
python3 benchmarks/algo_benchmark.py
```

Validates that the move sequence is **byte-for-byte identical** across all
three solvers on every (size, seed) pair before reporting timings.

This is the comparison that answers *which solver is faster*.

## `e2e_benchmark.py` — wall-time playing the live API

Spins up `maze_api`'s HTTP server in a daemon thread on an ephemeral port,
then for each solver does:

```
POST /reset { seed }
GET  /ascii            -> ascii_maze
solve(ascii_maze)      -> moves
POST /move { dir }     -> repeat per move until status == "won"
```

Reports `fetch`, `solve`, `play`, `total` separately.

```bash
python3 benchmarks/e2e_benchmark.py
```

This is the comparison that answers *which solver finishes the game fastest
under the current API contract*. Spoiler: past size ~50 the per-move HTTP
round trip dominates and the three solvers tie on `total`. The algorithmic
win is real but invisible in wall-time until the API exposes a batch endpoint
(e.g. `POST /moves`) — see the discussion in the top-level `README.md`.
