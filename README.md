# Laberintos: flood solver en Python

Este repositorio contiene un **juego de laberintos** con una API HTTP
(`maze_api/`) y un **solver rápido en Python puro** que lo resuelve por el
método de **inundación** (flood fill): `flood_solver/`.

Objetivo: resolver el laberinto **en el menor tiempo posible**, en Python puro.

---

## Demostración rápida

Resuelve el mismo laberinto con el solver original y con el flood solver, mide
el tiempo de cada uno y verifica que el resultado sea correcto:

```bash
python3 comparacion.py              # laberinto mediano
python3 comparacion.py --size 1000  # 1.000.000 de celdas
```

Salida:

```
Generando un laberinto de 1000 x 1000 = 1,000,000 celdas (semilla 42)...

Los dos resolvieron el mismo laberinto. El camino tiene 224,207 pasos.

SOLVER                     TIEMPO (ms)   CAMINO CORRECTO
--------------------------------------------------------
Original (maze_api)            5956.52      (referencia)
Flood (inundacion)              305.67                SI
--------------------------------------------------------

El flood solver es 19.5 veces mas rapido, con el mismo camino correcto.
```

- **CAMINO CORRECTO: SI** → el flood solver da exactamente el mismo camino que
  el solver original (misma respuesta, solo que más rápido).
- **~19× más rápido**, tanto en laberintos chicos como de un millón de celdas.

---

## Demostración en vivo (jugando contra la API)

Lo más parecido a una partida real: se levanta el **servidor del juego** en una
terminal y el solver lo **juega por la red** desde otra.

**Terminal 1** — levantar el laberinto (queda escuchando):

```bash
python3 -m maze_api 30 --seed 7
```

**Terminal 2** — el solver juega contra ese servidor:

```bash
python3 flood_solver/solver.py --play --host 127.0.0.1 --port 8000
```

Salida:

```
moves=424 won=True
reset=0.00ms  fetch=15.77ms  solve=0.280ms  play=134.33ms  total=150.38ms
```

`won=True` significa que el solver **salió del laberinto**.

- Para cambiar el tamaño: `python3 -m maze_api 100` (laberinto de 100×100).
- Para detener el servidor: `Ctrl+C` en la Terminal 1.

---

## ¿Qué es cada cosa?

```
.
├── comparacion.py     → demostración: original vs flood solver, mismo laberinto
├── maze_api/          → el juego: genera el laberinto y la API HTTP
│   └── solver.py          el solver original (el de referencia)
├── flood_solver/      → el flood solver (inundación, Python puro)
│   ├── solver.py          el código que resuelve el laberinto
│   ├── compare.py         comparación con más tamaños
│   ├── demo.ipynb         notebook para presentar (Run All)
│   └── test_flood.py      verifica que el resultado sea correcto
├── solver_v1/         → primer intento de solver (más lento, queda de historia)
└── super_solver/      → versión en Rust (no se usa: aquí se compite en Python)
```

**Importante:** el flood solver **solo resuelve**; no crea laberintos. El
laberinto lo genera `maze_api/`. Por eso ambas carpetas van juntas. No hace
falta instalar nada: es solo Python (sin librerías externas).

---

## Comandos individuales

```bash
# resolver un laberinto generado (sin comparar)
python3 flood_solver/solver.py --size 10 --seed 42     # chico, se ve el camino
python3 flood_solver/solver.py --size 1000 --seed 42   # 1.000.000 de celdas

# verificar que el flood solver es correcto en muchos laberintos
python3 -m flood_solver.test_flood
```

---

## ¿Por qué el flood solver es más rápido?

El solver original crea **un objeto de Python por cada celda** del laberinto:
mucha memoria y trabajo. El flood solver trabaja directo sobre el texto del
laberinto usando **una lista plana de bytes** (1 byte por celda), sin crear
objetos. Es el mismo algoritmo (inundación / BFS), pero mucho más liviano: unas
**~19 veces más rápido** y aguanta laberintos mucho más grandes.
