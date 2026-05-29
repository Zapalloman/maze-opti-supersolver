# super_solver (Rust — no se usa en la competencia)

> **Nota:** esta es una versión anterior del solver escrita en **Rust** (expuesta
> a Python con `ctypes`). **No se usa en la competencia**, porque la final es en
> **Python puro**. El solver que se ejecuta es `flood_solver/`. Esta carpeta se
> conserva solo como referencia histórica / experimento.

Solver nativo del laberinto en formato `maze_api`, escrito en Rust. Produce la
**misma secuencia de movimientos, byte por byte**, que el solver original.

## Build

```bash
cd super_solver
cargo build --release
```

Genera `target/release/libsuper_solver.so`, que el wrapper de Python carga con
`ctypes`.

## Uso desde Python

```python
from super_solver import solve, solve_ascii_maze

moves = solve(ascii_maze)          # list[str]: ['E', 'E', 'S', ...]
result = solve_ascii_maze(text)    # dataclass con .moves y .elapsed_seconds
```

```bash
python3 super_solver.py --size 100 --seed 42
python3 super_solver.py --file maze.txt
curl http://127.0.0.1:8000/ascii | python3 super_solver.py --stdin
```

## Archivos

- `src/lib.rs` — parser + BFS + reconstrucción del camino
- `super_solver.py` — wrapper `ctypes`, resultado como dataclass, CLI
- `Cargo.toml` — perfil release afinado (`lto="fat"`, un solo codegen unit)
