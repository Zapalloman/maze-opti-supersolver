# super_solver (Rust — fuera de la competencia)

Solver nativo en Rust (expuesto a Python con `ctypes`). Produce la misma
secuencia de movimientos, byte por byte, que el solver original. No compite:
la final es en Python puro (`flood_solver/`); se conserva como referencia.

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
