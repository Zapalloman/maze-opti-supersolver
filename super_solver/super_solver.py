#!/usr/bin/env python3
"""Python wrapper over the native Rust maze solver.

Mirrors the public surface of ``maze_api.solver`` so the benchmark can compare
move-by-move with both the baseline and the previous 1D solver_v1.
"""

from __future__ import annotations

import argparse
import ctypes
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LIB_PATH = _HERE / "target" / "release" / "libsuper_solver.so"


def _load_library() -> ctypes.CDLL:
    if not _LIB_PATH.exists():
        raise RuntimeError(
            f"Native solver not built. Run `cargo build --release` in {_HERE}."
        )
    lib = ctypes.CDLL(str(_LIB_PATH))
    lib.solve.restype = ctypes.c_int32
    lib.solve.argtypes = [
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.c_char_p,
        ctypes.c_size_t,
    ]
    return lib


_LIB = _load_library()

_ERRORS = {
    -1: "Invalid ASCII shape",
    -2: "No start marker (P/S) found",
    -3: "No (or ambiguous) boundary exit",
    -4: "Goal unreachable from start",
    -5: "Output buffer too small",
}


@dataclass(frozen=True)
class SolveResult:
    moves: list[str]
    elapsed_seconds: float

    @property
    def move_string(self) -> str:
        return "".join(self.moves)


def solve(ascii_maze: str) -> list[str]:
    """Solve and return moves as a list of single-char strings."""
    payload = ascii_maze.encode("utf-8")
    out_cap = max(64, len(payload))
    out_buf = ctypes.create_string_buffer(out_cap)
    n = _LIB.solve(payload, len(payload), out_buf, out_cap)
    if n < 0:
        raise ValueError(f"super_solver error: {_ERRORS.get(n, n)}")
    return [chr(b) for b in out_buf.raw[:n]]


def solve_bytes(ascii_maze: bytes) -> bytes:
    """Faster path when caller already has bytes; returns raw move bytes."""
    out_cap = max(64, len(ascii_maze))
    out_buf = ctypes.create_string_buffer(out_cap)
    n = _LIB.solve(ascii_maze, len(ascii_maze), out_buf, out_cap)
    if n < 0:
        raise ValueError(f"super_solver error: {_ERRORS.get(n, n)}")
    return out_buf.raw[:n]


def solve_ascii_maze(ascii_maze: str) -> SolveResult:
    t0 = time.perf_counter()
    moves = solve(ascii_maze)
    return SolveResult(moves=moves, elapsed_seconds=time.perf_counter() - t0)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Native (Rust) ASCII maze solver.")
    parser.add_argument("--file")
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--size", type=int)
    parser.add_argument("--seed", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.file:
        ascii_maze = Path(args.file).read_text(encoding="utf-8")
        source = f"file={args.file}"
    elif args.stdin:
        ascii_maze = sys.stdin.read()
        source = "stdin"
    elif args.size:
        # Local import so the wrapper is usable without the maze_api package.
        sys.path.insert(0, str(_HERE.parent))
        from maze_api.server import MazeGame  # type: ignore

        game = MazeGame(size=args.size, seed=args.seed)
        ascii_maze = game.ascii_maze()
        source = f"generated size={args.size} seed={game.current_seed}"
    else:
        raise SystemExit("Choose one of --file, --stdin, --size.")

    t0 = time.perf_counter()
    moves = solve(ascii_maze)
    elapsed = time.perf_counter() - t0

    print(f"Source: {source}")
    print(f"Moves: {''.join(moves)}")
    print(f"Move count: {len(moves)}")
    print(f"Elapsed seconds: {elapsed:.9f}")


if __name__ == "__main__":
    main()
