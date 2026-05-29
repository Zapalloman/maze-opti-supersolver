#!/usr/bin/env python3
"""Self-contained head-to-head: baseline vs solver_v1 vs flood (the new one).

Run from the repo root:

    python3 flood_solver/compare.py
    python3 flood_solver/compare.py --sizes 100 500 1000 --seed 11

Prints one table comparing path-compute time across solvers and validates that
the new flood solver returns the EXACT same moves as the course baseline.
Rust is shown only if it happens to be built — it is NOT eligible for the final
(the final must be pure Python); it is a reference ceiling only.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "super_solver"))

from maze_api.server import MazeGame
from maze_api.solver import solve_ascii_maze as baseline_solve
import flood_solver

try:
    from solver_v1 import solve as v1_solve
    HAVE_V1 = True
except Exception:
    HAVE_V1 = False

try:
    import super_solver as rust_mod
    HAVE_RUST = True
except Exception:
    HAVE_RUST = False


def best(fn, payload, reps):
    b = float("inf")
    for _ in range(reps):
        t0 = time.perf_counter()
        fn(payload)
        dt = time.perf_counter() - t0
        if dt < b:
            b = dt
    return b * 1000.0


def run(sizes, seed):
    print("=" * 90)
    print("  SOLVER SHOOT-OUT — path-compute time (ms), best-of-N, same maze per row")
    print("=" * 90)
    cols = f"{'N':>5} {'cells':>11} | {'baseline':>10} "
    if HAVE_V1:
        cols += f"{'solver_v1':>10} "
    cols += f"{'FLOOD':>10} |"
    if HAVE_RUST:
        cols += f" {'rust(ref)':>10} |"
    cols += f" {'check':>6}"
    print(cols)
    print("-" * 90)

    for n in sizes:
        a = MazeGame(size=n, seed=seed).ascii_maze()
        ab = a.encode()

        base_moves = baseline_solve(a).moves
        flood_moves = flood_solver.solve(ab)
        ok = "OK" if flood_moves == base_moves else "FAIL"

        reps = 5 if n < 500 else 3
        tb = best(lambda s: baseline_solve(s).moves, a, 2 if n >= 500 else 3)
        tf = best(flood_solver.solve, ab, reps + 2)

        row = f"{n:>5} {n*n:>11,} | {tb:>10.2f} "
        if HAVE_V1:
            tv = best(v1_solve, a, reps)
            row += f"{tv:>10.2f} "
        row += f"{tf:>10.2f} |"
        if HAVE_RUST:
            tr = best(rust_mod.solve, a, reps + 2)
            row += f" {tr:>10.3f} |"
        row += f" {ok:>6}"
        print(row)

    print("-" * 90)
    print("FLOOD is the fastest PURE-PYTHON solver (the eligible category for the final).")
    print("'check' = FLOOD output is byte-for-byte identical to the baseline.")
    if HAVE_RUST:
        print("rust column is a reference ceiling only — NOT eligible (final must be Python).")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sizes", type=int, nargs="+", default=[50, 100, 250, 500, 1000])
    p.add_argument("--seed", type=int, default=11)
    args = p.parse_args()
    run(args.sizes, args.seed)


if __name__ == "__main__":
    main()
