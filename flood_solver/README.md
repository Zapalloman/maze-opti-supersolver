# flood_solver

Solver por **inundación** (flood fill = BFS) en Python puro, sin dependencias.
Devuelve exactamente el mismo camino que el solver original (validado byte por
byte en `test_flood.py`).

| Solver           | 10⁶ celdas (1000×1000) |
|------------------|------------------------|
| Original (curso) | ~4,5 s                 |
| solver_v1        | ~0,44 s                |
| **flood_solver** | **~0,18 s**            |

## Uso

```bash
# modo juez: laberinto por stdin, movimientos por stdout (se autodetecta)
python3 flood_solver/solver.py < laberinto.txt
python3 flood_solver/solver.py --classic < laberinto.txt   # formato del solver original
python3 flood_solver/solver.py --sep " " < laberinto.txt   # movimientos separados

# otras fuentes
python3 flood_solver/solver.py --file laberinto.txt
python3 flood_solver/solver.py --size 1000 --seed 42       # genera y resuelve
```

```python
from flood_solver import solve
moves = solve(ascii_maze)   # ['E', 'E', 'S', ...]
```

En modo juez stdout lleva solo los movimientos (estadísticas por stderr);
tolera CRLF y líneas en blanco iniciales. `--classic` replica la salida del
solver original byte por byte (`Moves:` / `Solved maze` / etc.).

## Contra la API en vivo

```bash
python3 flood_solver/solver.py --play  --host 127.0.0.1 --port 8000
python3 flood_solver/solver.py --blind --host 127.0.0.1 --port 8000
```

`--play`: lee `/ascii` una vez y hace 1 `POST /move` por paso (mínimo de
peticiones, que es lo que domina el tiempo en vivo). `--blind`: nunca lee el
mapa, explora solo con `/move`; memoria proporcional al camino recorrido.

## Diseño

- Una celda es el offset entero de su carácter central en el texto; los
  vecinos están a ±4 columnas / ±2 filas, y hay pasillo si el byte intermedio
  es espacio.
- Trabaja sobre `bytes` (comparaciones enteras, no de caracteres).
- Visitado + rastro del camino en un único `bytearray` plano: acceso directo,
  sin diccionarios ni objetos por celda.
- La salida se localiza una sola vez con 4 escaneos de slice sobre los bordes.

`solve_bidirectional()` (inunda desde ambos extremos) queda como alternativa
documentada: en CPython resulta más lenta que la unidireccional.

## Pruebas

```bash
python3 -m flood_solver.test_flood       # camino idéntico al original (1–64 × 12 semillas)
python3 flood_solver/compare.py          # tiempos en varios tamaños
python3 comparacion.py                   # demo original vs flood (raíz del repo)
```
