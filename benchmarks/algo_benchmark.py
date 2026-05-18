#!/usr/bin/env python3
"""Three-way solver shoot-out: pure algorithm time, no HTTP in the loop.

Compares:
  * baseline    — maze_api.solver        (BFS over dataclasses + dict-of-sets)
  * solver_v1   — solver_v1.solver       (Python BFS over a 1D ASCII string)
  * super       — super_solver           (native Rust over a packed bit grid)

For every (size, seed) pair the three solvers receive the same ASCII payload
and must return the exact same move sequence. Best-of-N timing per call.
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

# Make every solver importable as a top-level package.
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "super_solver"))

from maze_api.server import MazeGame                          # noqa: E402
from maze_api.solver import solve_ascii_maze as baseline_solve  # noqa: E402
from solver_v1 import solve as solver_v1_solve                # noqa: E402
import super_solver as super_mod                              # noqa: E402


# --- Timing helpers --------------------------------------------------------

def _time_solver(fn, payload, repeats: int) -> float:
    """Return best-of-N seconds for a single solver call."""
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn(payload)
        dt = time.perf_counter() - t0
        if dt < best:
            best = dt
    return best


def _baseline_call(ascii_maze: str):
    return baseline_solve(ascii_maze).moves


def _v1_call(ascii_maze: str):
    return solver_v1_solve(ascii_maze)


def _super_call(ascii_maze: str):
    return super_mod.solve(ascii_maze)


# --- Bench -----------------------------------------------------------------

SIZES = [10, 50, 100, 250, 500]
SEEDS_PER_SIZE = 8
REPEATS = 3


def main() -> None:
    print(
        f"Python: {sys.version.split()[0]}  |  "
        f"seeds/size: {SEEDS_PER_SIZE}  |  best-of: {REPEATS}"
    )
    print("=" * 92)
    header = (
        f"{'size':>5} {'baseline (ms)':>15} "
        f"{'v1 (ms)':>13} {'super (ms)':>13} "
        f"{'B/S':>8} {'V/S':>8}"
    )
    print(header)
    print("-" * 92)

    agg = {"baseline": 0.0, "v1": 0.0, "super": 0.0}
    mismatches = 0

    for size in SIZES:
        size_times = {"baseline": [], "v1": [], "super": []}
        for seed in range(SEEDS_PER_SIZE):
            game = MazeGame(size=size, seed=seed)
            ascii_maze = game.ascii_maze()

            base_moves = _baseline_call(ascii_maze)
            v1_moves = _v1_call(ascii_maze)
            super_moves = _super_call(ascii_maze)
            if super_moves != base_moves:
                mismatches += 1
                print(f"  MISMATCH (super vs baseline) size={size} seed={seed}")
            if v1_moves != base_moves:
                mismatches += 1
                print(f"  MISMATCH (v1 vs baseline) size={size} seed={seed}")

            size_times["baseline"].append(_time_solver(_baseline_call, ascii_maze, REPEATS))
            size_times["v1"].append(_time_solver(_v1_call, ascii_maze, REPEATS))
            size_times["super"].append(_time_solver(_super_call, ascii_maze, REPEATS))

        bmean = statistics.mean(size_times["baseline"]) * 1000
        vmean = statistics.mean(size_times["v1"]) * 1000
        smean = statistics.mean(size_times["super"]) * 1000

        agg["baseline"] += sum(size_times["baseline"])
        agg["v1"] += sum(size_times["v1"])
        agg["super"] += sum(size_times["super"])

        bs = bmean / smean if smean > 0 else float("inf")
        vs = vmean / smean if smean > 0 else float("inf")
        print(f"{size:>5} {bmean:>15.4f} {vmean:>13.4f} {smean:>13.4f} {bs:>8.2f}x {vs:>8.2f}x")

    print("-" * 92)
    print(
        f"Totals:  baseline={agg['baseline']:.4f}s  "
        f"v1={agg['v1']:.4f}s  super={agg['super']:.4f}s"
    )
    if agg["super"] > 0:
        print(
            f"super is {agg['baseline']/agg['super']:.2f}x faster than baseline, "
            f"{agg['v1']/agg['super']:.2f}x faster than solver_v1."
        )
    if mismatches:
        print(f"\n{mismatches} mismatches detected.")
        sys.exit(1)
    print("All solver outputs match.")


if __name__ == "__main__":
    main()
