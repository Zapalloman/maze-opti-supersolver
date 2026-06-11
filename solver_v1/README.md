# solver_v1

Primer solver propio, en Python puro. ~25× más rápido que el original;
superado después por `flood_solver/` (~2,5× adicional). Se conserva como paso
intermedio.

## Idea

Sin grafo: el laberinto ASCII se recorre como un string 1D con offsets
enteros.

| Dirección | Celda vecina            | Byte de pared       |
|-----------|-------------------------|---------------------|
| N         | `idx - 2 * ancho_linea` | `idx - ancho_linea` |
| S         | `idx + 2 * ancho_linea` | `idx + ancho_linea` |
| W         | `idx - 4`               | `idx - 2`           |
| E         | `idx + 4`               | `idx + 2`           |

Hay pasillo si el byte de pared es `' '`. BFS sobre índices enteros, padres en
`dict[int, (int, str)]`. El límite que le quedó: una búsqueda de diccionario
por visita — `flood_solver/` la reemplaza por un `bytearray` plano.

## Uso

```bash
python3 -m solver_v1.solver --size 50 --seed 42
python3 -m solver_v1.solver --file laberinto.txt
curl http://127.0.0.1:8000/ascii | python3 -m solver_v1.solver --stdin
```

```python
from solver_v1 import solve
moves = solve(ascii_maze)   # ['E', 'E', 'S', ...]
```
