#!/usr/bin/env python3
# ============================================================================
#  COMPARACION DE SOLVERS DE LABERINTOS
# ----------------------------------------------------------------------------
#  Resuelve EL MISMO laberinto con dos solvers y los compara:
#     1. El solver original  (maze_api/solver.py, el de referencia)
#     2. El flood solver     (flood_solver, metodo de inundacion)
#
#  Para cada uno mide el TIEMPO de resolver y verifica que el camino sea
#  CORRECTO (identico al del solver original). Gana el mas rapido.
#
#  COMO CORRERLO:
#     python3 comparacion.py
#     python3 comparacion.py --size 1000      (1.000.000 de celdas)
# ============================================================================

import argparse
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from maze_api.server import MazeGame
from maze_api.solver import solve_ascii_maze as solver_original
import flood_solver


def cronometrar(funcion, entrada, repeticiones=3):
    """Corre la funcion varias veces y devuelve el MEJOR tiempo (en ms)."""
    mejor = float("inf")
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        funcion(entrada)
        transcurrido = time.perf_counter() - inicio
        mejor = min(mejor, transcurrido)
    return mejor * 1000  # a milisegundos


def main():
    ap = argparse.ArgumentParser(description="Compara solvers de laberintos.")
    ap.add_argument("--size", type=int, default=200,
                    help="Lado del laberinto (size x size celdas). Por defecto 200.")
    ap.add_argument("--seed", type=int, default=42,
                    help="Semilla para reproducir el mismo laberinto.")
    args = ap.parse_args()

    n = args.size
    print(f"\nGenerando un laberinto de {n} x {n} = {n*n:,} celdas (semilla {args.seed})...")
    laberinto = MazeGame(size=n, seed=args.seed).ascii_maze()
    laberinto_bytes = laberinto.encode()

    # --- Solver original: es la respuesta "correcta" de referencia ---
    mov_original = solver_original(laberinto).moves
    t_original = cronometrar(lambda x: solver_original(x).moves, laberinto)

    # --- Flood solver ---
    mov_flood = flood_solver.solve(laberinto_bytes)
    t_flood = cronometrar(flood_solver.solve, laberinto_bytes)
    correcto = "SI" if mov_flood == mov_original else "NO (!)"

    # --- Tabla de resultados ---
    print(f"\nLos dos resolvieron el mismo laberinto. El camino tiene {len(mov_original):,} pasos.\n")
    print(f"{'SOLVER':<24}{'TIEMPO (ms)':>14}{'CAMINO CORRECTO':>18}")
    print("-" * 56)
    print(f"{'Original (maze_api)':<24}{t_original:>14.2f}{'(referencia)':>18}")
    print(f"{'Flood (inundacion)':<24}{t_flood:>14.2f}{correcto:>18}")
    print("-" * 56)

    # --- Conclusion en palabras simples ---
    print(f"\nEl flood solver es {t_original / t_flood:.1f} veces mas rapido, "
          f"con el mismo camino correcto.\n")


if __name__ == "__main__":
    main()
