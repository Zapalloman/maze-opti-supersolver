"""solver_v1 — first iteration of a custom maze solver.

Pure Python, operates directly on the ASCII payload as a 1D string,
indexing wall characters by integer offset instead of building a graph.

Exposes a single ``solve`` function for parity with the other solvers.
The submodule is loaded lazily so ``python3 -m solver_v1.solver`` keeps
working without the dual-import warning.
"""

from typing import Any

__all__ = ["solve"]


def __getattr__(name: str) -> Any:
    if name == "solve":
        from .solver import solve as _solve
        return _solve
    raise AttributeError(f"module 'solver_v1' has no attribute {name!r}")
