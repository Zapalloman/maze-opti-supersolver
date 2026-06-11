# Laberintos: flood solver en Python

Juego de laberintos con API HTTP (`maze_api/`) y un solver en Python puro que
lo resuelve por **inundación** (flood fill): `flood_solver/`. Objetivo: menor
tiempo posible.

## Evaluación (stdin → stdout)

```bash
python3 flood_solver/solver.py < laberinto.txt             # imprime los movimientos: SSENNE...
python3 flood_solver/solver.py --classic < laberinto.txt   # formato del solver original
python3 flood_solver/solver.py --sep $'\n' < laberinto.txt # un movimiento por línea
```

stdout lleva solo la respuesta; las estadísticas van por stderr. `--classic`
es idéntico byte por byte a la salida del solver original, ~18× más rápido.

## Comparación

```bash
python3 comparacion.py              # original vs flood, mismo laberinto
python3 comparacion.py --size 1000  # 1.000.000 de celdas
```

```
SOLVER                     TIEMPO (ms)   CAMINO CORRECTO
--------------------------------------------------------
Original (maze_api)            5956.52      (referencia)
Flood (inundacion)              305.67                SI
--------------------------------------------------------

El flood solver es 19.5 veces mas rapido, con el mismo camino correcto.
```

## Contra la API en vivo

```bash
python3 -m maze_api 30 --seed 7                                  # terminal 1: servidor
python3 flood_solver/solver.py --play --host 127.0.0.1 --port 8000  # terminal 2: juega
```

```
moves=424 won=True
reset=0.00ms  fetch=15.77ms  solve=0.280ms  play=134.33ms  total=150.38ms
```

## Estructura

```
.
├── comparacion.py     → demo: original vs flood, mismo laberinto
├── maze_api/          → el juego: generador + API HTTP + solver original
├── flood_solver/      → el solver que compite (inundación, Python puro)
├── solver_v1/         → primer intento propio (superado por flood_solver)
└── super_solver/      → versión en Rust (fuera de la competencia: es Python puro)
```

Sin dependencias externas: solo Python estándar.

## Por qué es más rápido

Mismo algoritmo (BFS / inundación) que el original, pero sin crear un objeto
por celda: el laberinto es su propio texto y el estado vive en un `bytearray`
plano (1 byte por celda). ~19× más rápido y escala a laberintos mucho más
grandes.
