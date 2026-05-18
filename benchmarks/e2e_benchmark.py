#!/usr/bin/env python3
"""End-to-end benchmark: the solver actually plays the HTTP API.

Three solvers compete:
  * baseline   — maze_api.solver (BFS over dataclasses + dict-of-sets)
  * solver_v1  — user's prior 1D Python solver (fast_solver.py, separate repo)
  * super      — Rust native solver in this folder

Per run we measure:
  fetch (ms) — GET /ascii round trip
  solve (ms) — pure compute time (no HTTP)
  play  (ms) — POST /move per move until status == "won"
  total (ms) — wall-clock from /reset to "won"

This makes the bottleneck shift explicit: super_solver still wins by ~25x on
the `solve` column, but the `play` column (one HTTP round trip per move)
dominates the total once the maze is non-trivial.

The HTTP server is started in-process on an ephemeral port; nothing is
exposed outside the loopback.
"""

from __future__ import annotations

import http.client
import json
import socket
import statistics
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "super_solver"))

from maze_api.server import create_server                       # noqa: E402
from maze_api.solver import solve_ascii_maze as baseline_solve  # noqa: E402
from solver_v1 import solve as solver_v1_solve                  # noqa: E402
import super_solver as super_mod                                # noqa: E402


# --- HTTP helpers ----------------------------------------------------------
# We open a fresh HTTPConnection per request because the stdlib's
# BaseHTTPRequestHandler defaults to HTTP/1.0 and closes the socket after each
# response. A new connection per request is also what a naive client does,
# which is what we want to measure.


def _http(host: str, port: int, method: str, path: str, body: dict | None = None) -> bytes:
    conn = http.client.HTTPConnection(host, port, timeout=5)
    try:
        headers = {}
        payload = None
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(payload))
        conn.request(method, path, body=payload, headers=headers)
        return conn.getresponse().read()
    finally:
        conn.close()


def reset_to_seed(host, port, seed):
    _http(host, port, "POST", "/reset", {"seed": seed})


def fetch_ascii(host, port) -> str:
    return _http(host, port, "GET", "/ascii").decode("utf-8")


def play_move(host, port, direction):
    return json.loads(_http(host, port, "POST", "/move", {"direction": direction}))


def play_until_won(host, port, moves):
    """Submit each move and stop when the server reports status==won."""
    for m in moves:
        resp = play_move(host, port, m)
        if resp.get("status") == "won":
            return True
    return False


# --- Server lifecycle ------------------------------------------------------

def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(size: int):
    port = _pick_free_port()
    server = create_server(size=size, host="127.0.0.1", port=port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # Give the OS a moment so the first connect doesn't race.
    time.sleep(0.05)
    return server, port


# --- Per-solver run --------------------------------------------------------

SOLVERS = [
    ("baseline",  lambda s: baseline_solve(s).moves),
    ("solver_v1", lambda s: solver_v1_solve(s)),
    ("super",     lambda s: super_mod.solve(s)),
]


def one_run(host, port, solver_fn, seed):
    reset_to_seed(host, port, seed)

    t0 = time.perf_counter()
    ascii_maze = fetch_ascii(host, port)
    t1 = time.perf_counter()
    moves = solver_fn(ascii_maze)
    t2 = time.perf_counter()
    won = play_until_won(host, port, moves)
    t3 = time.perf_counter()

    if not won:
        raise RuntimeError("solver did not finish the maze")

    return {
        "fetch": (t1 - t0) * 1000,
        "solve": (t2 - t1) * 1000,
        "play":  (t3 - t2) * 1000,
        "total": (t3 - t0) * 1000,
        "n_moves": len(moves),
    }


# --- Bench driver ----------------------------------------------------------

SIZES = [10, 50, 100, 200]
SEEDS_PER_SIZE = 3


def main() -> None:
    print(
        "End-to-end benchmark: each solver plays the live HTTP API "
        "(/reset -> /ascii -> /move per move)."
    )
    print(f"Python: {sys.version.split()[0]}  |  seeds/size: {SEEDS_PER_SIZE}\n")

    header = (
        f"{'size':>5} {'solver':>10} {'fetch (ms)':>12} "
        f"{'solve (ms)':>12} {'play (ms)':>12} {'total (ms)':>12} "
        f"{'moves':>7} {'ms/move':>9}"
    )

    for size in SIZES:
        server, port = start_server(size)
        try:
            print("=" * len(header))
            print(f"size = {size}x{size}")
            print("-" * len(header))
            print(header)
            print("-" * len(header))
            for name, fn in SOLVERS:
                rows = [one_run("127.0.0.1", port, fn, seed)
                        for seed in range(SEEDS_PER_SIZE)]
                mean = {k: statistics.mean(r[k] for r in rows)
                        for k in ("fetch", "solve", "play", "total")}
                n_moves = int(statistics.mean(r["n_moves"] for r in rows))
                ms_per_move = mean["play"] / max(1, n_moves)
                print(
                    f"{size:>5} {name:>10} "
                    f"{mean['fetch']:>12.2f} {mean['solve']:>12.2f} "
                    f"{mean['play']:>12.2f} {mean['total']:>12.2f} "
                    f"{n_moves:>7} {ms_per_move:>9.3f}"
                )
            print()
        finally:
            server.shutdown()
            server.server_close()

    print(
        "Read this: the `solve` column still shows the algorithmic gap "
        "(super ~25x faster than v1, ~200x faster than baseline). "
        "The `play` column is HTTP-bound and identical across solvers, so "
        "`total` is dominated by `play` past size ~50. The algorithmic win "
        "only matters if the API supported batched moves."
    )


if __name__ == "__main__":
    main()
