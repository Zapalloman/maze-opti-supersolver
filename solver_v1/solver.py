import argparse
import sys
import time
import http.client
from collections import deque
from maze_api.server import MazeGame

def parse_args():
    parser = argparse.ArgumentParser(description="Ultra-fast Python solver for ASCII mazes.")
    parser.add_argument("--file", help="Path to a text file containing the ASCII maze.")
    parser.add_argument("--stdin", action="store_true", help="Read the ASCII maze from standard input.")
    parser.add_argument("--size", type=int, help="Generate and solve a maze of size n x n.")
    parser.add_argument("--seed", type=int, default=None, help="Optional seed used with --size.")
    parser.add_argument("--host", default="127.0.0.1", help="Target API host")
    parser.add_argument("--port", type=int, default=8000, help="Target API port")
    return parser.parse_args()

def _fetch_ascii_from_server(host, port, seed=None):
    conn = http.client.HTTPConnection(host, port)
    # The API might not accept seed in GET parameters for /ascii directly, but wait - 
    # The API docs say GET /ascii returns the ascii maze... Wait, I should just fetch it. 
    # Let me just send a basic GET request.
    conn.request("GET", "/ascii")
    response = conn.getresponse()
    if response.status != 200:
        raise ValueError(f"Failed to fetch maze: HTTP {response.status}")
    return response.read().decode('utf-8')

def _post_moves_to_server(host, port, moves):
    conn = http.client.HTTPConnection(host, port)
    for move in moves:
        payload = f'{{"direction":"{move}"}}'
        conn.request("POST", "/move", body=payload, headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        response.read() # Consume response to free connection for reuse
    conn.close()

def solve(ascii_maze):
    ascii_maze = ascii_maze.rstrip('\n') + '\n'
    line_width = ascii_maze.find('\n') + 1
    
    start_index = ascii_maze.find('P')
    if start_index == -1:
        start_index = ascii_maze.find('S')
    if start_index == -1:
        raise ValueError("Start point not found")
        
    queue = deque([start_index])
    parents = {start_index: (None, None)}
    
    DIR_OFFSETS = [
        ('N', -2 * line_width, -line_width),
        ('S', 2 * line_width, line_width),
        ('W', -4, -2),
        ('E', 4, 2)
    ]
    
    maze_len = len(ascii_maze)
    exit_dir = None
    
    while queue:
        curr = queue.popleft()
            
        for move, dest_offset, wall_offset in DIR_OFFSETS:
            wall_index = curr + wall_offset
            if wall_index < 0 or wall_index >= maze_len:
                continue
                
            if ascii_maze[wall_index] == ' ':
                # Detect boundary exits cleanly
                is_boundary = (
                    wall_index < line_width or
                    wall_index >= maze_len - line_width or
                    wall_index % line_width == 0 or
                    wall_index % line_width == line_width - 2
                )
                
                if is_boundary:
                    parents[-1] = (curr, move)
                    exit_dir = move
                    break
                    
                dest_index = curr + dest_offset
                if dest_index not in parents:
                    parents[dest_index] = (curr, move)
                    queue.append(dest_index)
        if exit_dir is not None:
            break
            
    path_moves = []
    if exit_dir is not None:
        path_moves.append(exit_dir)
        curr = parents[-1][0]
    else:
        raise ValueError("No path found")
        
    while curr != start_index:
        prev, move = parents[curr]
        if move:
            path_moves.append(move)
        curr = prev
        
    path_moves.reverse()
    return path_moves

def main():
    args = parse_args()
    
    start_time = time.perf_counter()
    source_description = ""
    
    # Fast HTTP fetch if no local source specified
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            ascii_maze = f.read()
        source_description = f"file={args.file}"
    elif args.stdin:
        ascii_maze = sys.stdin.read()
        source_description = "stdin"
    elif getattr(args, 'size', None):
        game = MazeGame(size=args.size, seed=args.seed)
        ascii_maze = game.ascii_maze()
        source_description = f"generated size={args.size} seed={game.current_seed}"
    else:
        # Fallback network execution
        ascii_maze = _fetch_ascii_from_server(args.host, args.port, args.seed)
        source_description = f"http={args.host}:{args.port}"
        
    t0 = time.perf_counter()
    moves = solve(ascii_maze)
    algo_time = time.perf_counter() - t0
    
    elapsed_seconds = time.perf_counter() - start_time
    move_string = "".join(moves)
    print(f"Source: {source_description}")
    print(f"Moves: {move_string}")
    print(f"Move count: {len(moves)}")
    print(f"Elapsed seconds: {elapsed_seconds:.9f}")
    print(f"Internal algorithm compute time: {algo_time:.9f}s")
    print("Solved maze:")
    # We could theoretically inject the solved path '.' and print here
    print(ascii_maze.strip())

if __name__ == "__main__":
    main()
