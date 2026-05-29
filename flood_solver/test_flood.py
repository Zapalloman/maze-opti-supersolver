#!/usr/bin/env python3
"""Correctness tests for flood_solver against the course baseline.

Run: python3 -m flood_solver.test_flood   (from the repo root)
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from maze_api.server import MazeGame, DIRECTIONS, Cell
from maze_api.solver import solve_ascii_maze as baseline_solve
import flood_solver


def _moves_escape(game: MazeGame, moves) -> bool:
    """Replay moves against a fresh game and confirm they reach the exit."""
    pos = game.maze.start_cell
    for i, mv in enumerate(moves):
        seen = game.maze.visible_directions(pos)[mv]
        if seen == "wall":
            return False
        last = i == len(moves) - 1
        if seen == "exit":
            return last
        if last:
            return False
        d = DIRECTIONS[mv]
        pos = Cell(pos.row + d[0], pos.col + d[1])
    return False


class FloodSolverTest(unittest.TestCase):
    SEEDS = list(range(12))
    SIZES = [1, 2, 3, 4, 8, 16, 32, 64]

    def test_matches_baseline_exactly(self):
        for n in self.SIZES:
            for seed in self.SEEDS:
                game = MazeGame(size=n, seed=seed)
                a = game.ascii_maze()
                base = baseline_solve(a).moves
                got = flood_solver.solve(a.encode())
                self.assertEqual(
                    got, base,
                    f"unidir mismatch N={n} seed={seed}: {len(got)} vs {len(base)}",
                )

    def test_bidirectional_is_shortest_and_valid(self):
        for n in self.SIZES:
            for seed in self.SEEDS:
                game = MazeGame(size=n, seed=seed)
                a = game.ascii_maze()
                base = baseline_solve(a).moves
                got = flood_solver.solve_bidirectional(a.encode())
                self.assertEqual(len(got), len(base),
                                 f"bidir length N={n} seed={seed}")
                self.assertTrue(_moves_escape(game, got),
                                f"bidir invalid escape N={n} seed={seed}")

    def test_unidir_moves_escape(self):
        for n in (5, 17, 33):
            for seed in (100, 101, 102):
                game = MazeGame(size=n, seed=seed)
                got = flood_solver.solve(game.ascii_maze().encode())
                self.assertTrue(_moves_escape(game, got),
                                f"unidir invalid escape N={n} seed={seed}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
