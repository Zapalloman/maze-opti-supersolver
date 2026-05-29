"""flood_solver — fastest pure-Python flood-fill (BFS) maze solver.

The final python solver: pure stdlib Python, the "método de inundación".
Exposes ``solve`` (unidirectional) and ``solve_bidirectional`` for parity with
the other solvers in this repo.
"""

from typing import Any

__all__ = ["solve", "solve_bidirectional", "play_offline"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from . import solver
        return getattr(solver, name)
    raise AttributeError(f"module 'flood_solver' has no attribute {name!r}")
