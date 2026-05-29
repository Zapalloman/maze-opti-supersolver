#!/usr/bin/env python3
"""flood_solver — fastest pure-Python flood-fill (BFS) solver for maze_api.

Design notes (why this beats baseline and solver_v1, in pure CPython):

* Operate on ``bytes``, not ``str``. Indexing ``bytes`` yields ``int`` and
  comparisons are int-vs-int (``== 32``), far cheaper than char comparisons.
* No per-cell objects, no graph, no dict. The maze IS its ASCII buffer; a cell
  is the integer byte-offset of its center character. Neighbours are reached by
  fixed offsets (``+/- 4`` columns, ``+/- 2*lw`` rows). A passage exists iff the
  wall-sample byte equals ``b' '`` (32).
* Visited / parent info lives in **two flat ``bytearray``s** indexed by that
  same byte-offset (``came_from``), so every lookup is an O(1) array index with
  zero hashing — the single biggest win over solver_v1's ``dict``.
* The unique boundary exit is located once with four C-level slice scans
  (no per-step boundary test in the hot loop).
* The four-neighbour expansion is hand-unrolled (no inner ``for`` over
  directions) and every hot name is bound to a local.

This is the "método de inundación": BFS floods outward from the start like
water, level by level, until it laps against the exit cell; the parent trail
left behind reconstructs the unique shortest path.

Public API mirrors the other solvers: ``solve(ascii) -> list[str]``.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import deque

# Direction byte codes (ASCII): used both as the emitted move and as the
# came_from marker (none of them is 0, so 0 cleanly means "unvisited").
_N = 78  # 'N'
_S = 83  # 'S'
_E = 69  # 'E'
_W = 87  # 'W'


def _to_bytes(ascii_maze) -> bytes:
    if isinstance(ascii_maze, (bytes, bytearray)):
        return bytes(ascii_maze)
    return ascii_maze.encode("ascii")


def _line_width(data: bytes) -> int:
    nl = data.find(b"\n")
    if nl < 0:
        raise ValueError("ASCII maze has no newline; cannot infer width.")
    return nl + 1  # keep '\n' in the stride so row arithmetic is uniform


def _find_start(data: bytes) -> int:
    i = data.find(b"P")
    if i < 0:
        i = data.find(b"S")
    if i < 0:
        raise ValueError("No start marker (P/S) found.")
    return i


def _find_exit(data: bytes, lw: int):
    """Return (exit_cell_center_index, exit_direction_byte).

    The exit is the single ``' '`` opening on the maze perimeter. We scan the
    four borders with C-level slicing instead of testing every cell.
    """
    inner = lw - 1
    n = (inner - 1) // 4
    total_lines = (len(data) + 1) // lw

    # North border: line 0, scan its bytes for a space at a cell-centre column.
    top = data[0:lw]
    p = top.find(b" ")
    if 0 <= p < inner:
        c = (p - 1) // 4  # first space of an open segment sits at index 4c+1
        center = (1) * lw + (4 * c + 2)
        return center, _N

    # South border: the bottom '+---+' line at row index 2*n.
    south_off = (2 * n) * lw
    bottom = data[south_off:south_off + lw]
    p = bottom.find(b" ")
    if 0 <= p < inner:
        c = (p - 1) // 4  # first space of an open segment sits at index 4c+1
        center = (2 * n - 1) * lw + (4 * c + 2)
        return center, _S

    # West border: leftmost char of each interior row -> offsets lw, 3lw, 5lw...
    west_col = data[lw::2 * lw]
    p = west_col.find(b" ")
    if p >= 0:
        r = p
        center = (2 * r + 1) * lw + 2
        return center, _W

    # East border: rightmost interior char -> offsets lw+4n, 3lw+4n, ...
    east_col = data[lw + 4 * n::2 * lw]
    p = east_col.find(b" ")
    if p >= 0:
        r = p
        center = (2 * r + 1) * lw + (4 * n - 2)
        return center, _E

    raise ValueError("No boundary exit found.")


def _reconstruct(came_from: bytearray, start: int, exit_cell: int,
                 exit_dir: int, lw: int) -> list:
    """Walk the parent trail back from exit_cell to start and emit moves."""
    out = bytearray()
    cur = exit_cell
    # Predecessor of a cell reached by moving D is cur - dest_offset(D).
    back = {_N: 2 * lw, _S: -2 * lw, _E: -4, _W: 4}
    while cur != start:
        d = came_from[cur]
        if d == 0:
            raise ValueError("Path reconstruction failed (unreachable exit).")
        out.append(d)
        cur += back[d]
    out.reverse()
    if exit_dir:
        out.append(exit_dir)
    return [chr(b) for b in out]


def solve(ascii_maze) -> list:
    """Solve the maze; return moves as a list of single-char strings.

    Unidirectional flood fill (BFS) from start to the boundary exit.
    """
    data = _to_bytes(ascii_maze)
    lw = _line_width(data)
    start = _find_start(data)
    exit_cell, exit_dir = _find_exit(data, lw)

    if start == exit_cell:
        return [chr(exit_dir)] if exit_dir else []

    came_from = bytearray(len(data))  # 0 == unvisited
    came_from[start] = 1  # sentinel: visited, but not via a real move

    # Hot-loop locals.
    SPACE = 32
    dlw = 2 * lw
    q = deque((start,))
    popleft = q.popleft
    append = q.append

    while q:
        cur = popleft()

        # North
        if data[cur - lw] == SPACE:
            nb = cur - dlw
            if came_from[nb] == 0:
                came_from[nb] = _N
                if nb == exit_cell:
                    break
                append(nb)
        # South
        if data[cur + lw] == SPACE:
            nb = cur + dlw
            if came_from[nb] == 0:
                came_from[nb] = _S
                if nb == exit_cell:
                    break
                append(nb)
        # East
        if data[cur + 2] == SPACE:
            nb = cur + 4
            if came_from[nb] == 0:
                came_from[nb] = _E
                if nb == exit_cell:
                    break
                append(nb)
        # West
        if data[cur - 2] == SPACE:
            nb = cur - 4
            if came_from[nb] == 0:
                came_from[nb] = _W
                if nb == exit_cell:
                    break
                append(nb)

    if came_from[exit_cell] == 0:
        raise ValueError("Goal unreachable from start.")

    return _reconstruct(came_from, start, exit_cell, exit_dir, lw)


def solve_bidirectional(ascii_maze) -> list:
    """Bidirectional flood fill: flood from start AND from the exit until the
    two wavefronts touch. In a perfect maze the start is the farthest cell from
    the exit, so a single-source BFS explores almost everything before it
    arrives; meeting in the middle can cut the explored area substantially.
    """
    data = _to_bytes(ascii_maze)
    lw = _line_width(data)
    start = _find_start(data)
    exit_cell, exit_dir = _find_exit(data, lw)

    if start == exit_cell:
        return [chr(exit_dir)] if exit_dir else []

    SPACE = 32
    dlw = 2 * lw

    # came_s[x]: move used to reach x from the start side.
    # came_e[x]: move used to reach x from the exit side.
    came_s = bytearray(len(data))
    came_e = bytearray(len(data))
    came_s[start] = 1
    came_e[exit_cell] = 1

    qs = deque((start,))
    qe = deque((exit_cell,))

    meet = -1
    L = len(data)

    # Each direction: (wall_offset, dest_offset, code). The bounds guard on nb
    # matters here because the exit-side flood starts AT the boundary cell and
    # would otherwise step out through the exit opening (a ' ' on the border).
    dirs = ((-lw, -dlw, _N), (lw, dlw, _S), (2, 4, _E), (-2, -4, _W))

    while qs and qe and meet < 0:
        # Expand the smaller frontier (classic bidirectional balancing).
        if len(qs) <= len(qe):
            for _ in range(len(qs)):
                cur = qs.popleft()
                for woff, doff, code in dirs:
                    wi = cur + woff
                    if 0 <= wi < L and data[wi] == SPACE:
                        nb = cur + doff
                        if 0 <= nb < L and came_s[nb] == 0:
                            came_s[nb] = code
                            if came_e[nb]:
                                meet = nb
                                break
                            qs.append(nb)
                if meet >= 0:
                    break
        else:
            for _ in range(len(qe)):
                cur = qe.popleft()
                for woff, doff, code in dirs:
                    wi = cur + woff
                    if 0 <= wi < L and data[wi] == SPACE:
                        nb = cur + doff
                        if 0 <= nb < L and came_e[nb] == 0:
                            came_e[nb] = code
                            if came_s[nb]:
                                meet = nb
                                break
                            qe.append(nb)
                if meet >= 0:
                    break

    if meet < 0:
        raise ValueError("Goal unreachable from start.")

    # Build start -> meet using came_s.
    back = {_N: 2 * lw, _S: -2 * lw, _E: -4, _W: 4}
    left = bytearray()
    cur = meet
    while cur != start:
        d = came_s[cur]
        left.append(d)
        cur += back[d]
    left.reverse()

    # Build meet -> exit using came_e. came_e[x] is the move that reached x from
    # the exit side, i.e. the move FROM the exit-side parent TO x. Walking from
    # meet back to exit_cell and inverting gives forward moves meet->exit.
    fwd = {_N: _S, _S: _N, _E: _W, _W: _E}
    right = bytearray()
    cur = meet
    while cur != exit_cell:
        d = came_e[cur]
        right.append(fwd[d])  # invert: parent->x recorded as the move into x
        cur += back[d]
    # 'right' currently lists moves from meet toward exit in order already,
    # because we step meet -> ... -> exit following came_e parents.

    out = bytes(left) + bytes(right)
    moves = [chr(b) for b in out]
    if exit_dir:
        moves.append(chr(exit_dir))
    return moves


# --------------------------------------------------------------------------
# Play modes (wall-clock): talk to the live HTTP API.
# --------------------------------------------------------------------------

def _http(host, port, method, path, body=None, timeout=10):
    import http.client
    import json as _json
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        payload = None
        headers = {}
        if body is not None:
            payload = _json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(payload))
        conn.request(method, path, body=payload, headers=headers)
        return conn.getresponse().read()
    finally:
        conn.close()


def play_offline(host, port, seed=None, verbose=True):
    """Fastest legal wall-clock strategy when /ascii is allowed:

      POST /reset {seed?}  (optional)
      GET  /ascii          (one round trip — read the whole map)
      solve(...)           (instant flood fill)
      POST /move x len(path)  (one round trip per move, NO /state spam)

    Returns (moves, timings).
    """
    import json as _json
    t0 = time.perf_counter()
    if seed is not None:
        _http(host, port, "POST", "/reset", {"seed": seed})
    t_reset = time.perf_counter()
    ascii_maze = _http(host, port, "GET", "/ascii")
    t_fetch = time.perf_counter()
    moves = solve(ascii_maze)
    t_solve = time.perf_counter()

    won = False
    for m in moves:
        resp = _http(host, port, "POST", "/move", {"direction": m})
        # Cheap "won" check without full JSON parse on every move.
        if b'"status": "won"' in resp or b'"status":"won"' in resp:
            won = True
    t_play = time.perf_counter()

    if verbose:
        print(f"moves={len(moves)} won={won}")
        print(f"reset={ (t_reset-t0)*1000:.2f}ms  fetch={(t_fetch-t_reset)*1000:.2f}ms  "
              f"solve={(t_solve-t_fetch)*1000:.3f}ms  play={(t_play-t_solve)*1000:.2f}ms  "
              f"total={(t_play-t0)*1000:.2f}ms")
    return moves, {
        "fetch": t_fetch - t_reset,
        "solve": t_solve - t_fetch,
        "play": t_play - t_solve,
        "total": t_play - t0,
        "n_moves": len(moves),
        "won": won,
    }


def play_blind(host, port, seed=None, verbose=True):
    """True flood-fill exploration: never read /ascii. Learn walls only from
    /move responses, build the map incrementally with iterative DFS, and stop
    on the first 'exit'. Stores only VISITED cells (a dict/set), so memory is
    O(path explored), not O(N**2) — this is what lets it scale toward huge
    mazes the full ASCII could never fit in memory.

    Uses 1 HTTP round trip per physical move (the /move response already carries
    the new position + visible directions; no separate /state call).
    """
    import json as _json
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from maze_api.server import OPPOSITE

    t0 = time.perf_counter()
    if seed is not None:
        _http(host, port, "POST", "/reset", {"seed": seed})

    st = _json.loads(_http(host, port, "GET", "/state"))
    pos = (st["position"]["row"], st["position"]["col"])
    requests = 1
    moves_made = 0
    visited = {pos}

    def open_dirs(d):
        return [k for k, v in d.items() if v != "wall"]

    stack = [(pos, iter(open_dirs(st["directions"])), None)]
    won = False

    while stack and not won:
        cell, it, entered_via = stack[-1]
        advanced = False
        for d in it:
            if entered_via is not None and d == OPPOSITE[entered_via]:
                continue
            resp = _json.loads(_http(host, port, "POST", "/move", {"direction": d}))
            requests += 1
            moves_made += 1
            if resp.get("status") == "won":
                won = True
                break
            npos = (resp["position"]["row"], resp["position"]["col"])
            if npos in visited:
                _http(host, port, "POST", "/move", {"direction": OPPOSITE[d]})
                requests += 1
                moves_made += 1
                continue
            visited.add(npos)
            stack.append((npos, iter(open_dirs(resp["directions"])), d))
            advanced = True
            break
        if won or advanced:
            continue
        stack.pop()
        if entered_via is not None:
            _http(host, port, "POST", "/move", {"direction": OPPOSITE[entered_via]})
            requests += 1
            moves_made += 1

    total = time.perf_counter() - t0
    if verbose:
        print(f"blind: won={won} moves={moves_made} requests={requests} "
              f"cells_seen={len(visited)} total={total*1000:.2f}ms")
    return {"won": won, "moves": moves_made, "requests": requests,
            "cells_seen": len(visited), "total": total}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _parse_args():
    p = argparse.ArgumentParser(description="Pure-Python flood-fill maze solver.")
    p.add_argument("--file")
    p.add_argument("--stdin", action="store_true")
    p.add_argument("--size", type=int)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--bidir", action="store_true", help="Use bidirectional flood fill.")
    p.add_argument("--play", action="store_true",
                   help="Play the live HTTP API (fetch /ascii once, replay shortest path).")
    p.add_argument("--blind", action="store_true",
                   help="Play blind: flood-fill exploration via /move only (no /ascii).")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    return p.parse_args()


def main():
    args = _parse_args()

    if args.play:
        play_offline(args.host, args.port, seed=args.seed)
        return

    if args.blind and not (args.file or args.stdin or args.size):
        play_blind(args.host, args.port, seed=args.seed)
        return

    if args.file:
        with open(args.file, "rb") as f:
            ascii_maze = f.read()
        source = f"file={args.file}"
    elif args.stdin:
        ascii_maze = sys.stdin.buffer.read()
        source = "stdin"
    elif args.size:
        # Make maze_api importable even when this file is run directly as a
        # script (python3 flood_solver/solver.py ...), not just as a module.
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from maze_api.server import MazeGame
        game = MazeGame(size=args.size, seed=args.seed)
        ascii_maze = game.ascii_maze()
        source = f"generated size={args.size} seed={game.current_seed}"
    else:
        raise SystemExit("Choose one of --file, --stdin, --size, or --play.")

    fn = solve_bidirectional if args.bidir else solve
    t0 = time.perf_counter()
    moves = fn(ascii_maze)
    elapsed = time.perf_counter() - t0

    print(f"Source: {source}")
    print(f"Algorithm: {'bidirectional' if args.bidir else 'unidirectional'} flood fill")
    print(f"Moves: {''.join(moves)}")
    print(f"Move count: {len(moves)}")
    print(f"Elapsed seconds: {elapsed:.9f}")


if __name__ == "__main__":
    main()
