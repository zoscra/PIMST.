"""
PIMST v7.0 "GOLDEN NEEDLE"
===========================

FILOSOFÍA:
"Equilibrio entre dominar rígidamente el problema para darle estabilidad 
y seguir la corriente de los datos para que sea óptimo. En la fina línea 
donde chocan esos paradigmas, hallamos la solución óptima."

La aguja dorada no es muy brillante - es SUTIL.

DISEÑO:
-------
✓ De v6.0: Puntos calientes de intersecciones (funcionó)
✓ De v6.0: Proporción áurea φ para radios adaptativos
✗ De v6.0: Recalculo dinámico abrupto (causó discontinuidad)
✗ De v6.0: Múltiples círculos conflictivos

INNOVACIÓN v7.0:
----------------
1. CAMPO CONTINUO de potenciales (no círculos discretos)
2. DECAIMIENTO GAUSSIANO suave (no desapariciones abruptas)
3. BALANCE 70-30: 70% datos locales + 30% estructura global
4. Radio adaptativo LOCAL con φ (no global rígido)
5. Un solo punto de coordenadas SUAVE que evoluciona gradualmente
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist
from typing import List, Tuple
import time

# Proporción áurea
PHI = (1 + np.sqrt(5)) / 2
GOLDEN_ANGLE = np.pi * (3 - np.sqrt(5))

# ============================================================================
# ANÁLISIS DE INTERSECCIONES (de v5.0 - funcionó bien)
# ============================================================================

def find_intersections_sample(cities, n_sample=20):
    """
    Encuentra intersecciones usando muestreo.
    Versión optimizada de v5.0/v6.0 que funcionó bien.
    """
    n = len(cities)
    if n < 10:
        n_sample = n
    
    # Muestreo estratégico
    step = max(1, n // n_sample)
    sample_indices = list(range(0, n, step))
    if len(sample_indices) > n_sample:
        sample_indices = sample_indices[:n_sample]
    
    intersections = []
    
    # Solo las conexiones más probables
    for i in range(len(sample_indices)):
        for j in range(i + 2, min(i + 8, len(sample_indices))):
            idx1, idx2 = sample_indices[i], sample_indices[j]
            p1, p2 = cities[idx1], cities[idx2]
            
            for k in range(j + 1, min(j + 6, len(sample_indices))):
                for l in range(k + 1, min(k + 6, len(sample_indices))):
                    idx3, idx4 = sample_indices[k], sample_indices[l]
                    p3, p4 = cities[idx3], cities[idx4]
                    
                    intersection = line_intersection(p1, p2, p3, p4)
                    if intersection is not None:
                        intersections.append(intersection)
    
    return np.array(intersections) if intersections else np.array([]).reshape(0, 2)

def line_intersection(p1, p2, p3, p4):
    """Intersección de dos segmentos."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    
    denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
    if abs(denom) < 1e-10:
        return None
    
    t = ((x1-x3)*(y3-y4) - (y1-y3)*(x3-x4)) / denom
    u = -((x1-x2)*(y1-y3) - (y1-y2)*(x1-x3)) / denom
    
    if 0 <= t <= 1 and 0 <= u <= 1:
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        return np.array([x, y])
    
    return None

# ============================================================================
# CAMPO CONTINUO DE POTENCIALES (INNOVACIÓN v7.0)
# ============================================================================

def create_smooth_potential_field(cities, visited_mask, intersections, 
                                   global_center, global_radius):
    """
    Crea un campo continuo de potenciales en lugar de círculos discretos.
    
    FILOSOFÍA:
    - 70% influencia LOCAL (intersecciones densas)
    - 30% influencia GLOBAL (estructura suave)
    - Decaimiento gaussiano (no desapariciones abruptas)
    """
    n = len(cities)
    unvisited = cities[~visited_mask]
    
    if len(unvisited) == 0:
        return None
    
    # COMPONENTE LOCAL (70%): Densidad de intersecciones
    if len(intersections) > 0:
        # Kernel de densidad con ancho adaptativo (proporción áurea)
        bandwidth = np.std(cities) / PHI  # Radio adaptativo suave
        
        # Para cada ciudad no visitada, calcular densidad de intersecciones cercanas
        local_potentials = []
        for city in unvisited:
            distances = np.linalg.norm(intersections - city, axis=1)
            # Kernel gaussiano (decaimiento suave, no abrupto)
            density = np.sum(np.exp(-distances**2 / (2 * bandwidth**2)))
            local_potentials.append(density)
        
        local_potentials = np.array(local_potentials)
        # Normalizar
        if local_potentials.max() > 0:
            local_potentials = local_potentials / local_potentials.max()
    else:
        local_potentials = np.zeros(len(unvisited))
    
    # COMPONENTE GLOBAL (30%): Estructura suave basada en dispersión
    global_potentials = []
    for city in unvisited:
        dist_to_center = np.linalg.norm(city - global_center)
        # Decaimiento gaussiano desde el centro global
        global_potential = np.exp(-(dist_to_center / global_radius)**2)
        global_potentials.append(global_potential)
    
    global_potentials = np.array(global_potentials)
    if global_potentials.max() > 0:
        global_potentials = global_potentials / global_potentials.max()
    
    # BALANCE 70-30 (la aguja dorada)
    combined_potential = 0.7 * local_potentials + 0.3 * global_potentials
    
    return combined_potential

def compute_smooth_guide(current_city, candidate_city, 
                        combined_potential, unvisited, 
                        prev_direction=None):
    """
    Guía suave que combina:
    1. Potencial del campo continuo
    2. Dirección previa suavizada (no tangentes rígidas)
    """
    # Índice del candidato en unvisited
    idx = np.where(np.all(unvisited == candidate_city, axis=1))[0]
    if len(idx) == 0:
        return 0.0
    
    potential_value = combined_potential[idx[0]]
    
    # Componente direccional suave (si hay dirección previa)
    direction_bonus = 0.0
    if prev_direction is not None:
        current_direction = candidate_city - current_city
        current_direction = current_direction / (np.linalg.norm(current_direction) + 1e-10)
        
        # Coherencia direccional suave (no rígida)
        direction_bonus = np.dot(current_direction, prev_direction)
        # Mapear [-1, 1] a [0, 1]
        direction_bonus = (direction_bonus + 1) / 2
    
    # Combinar: 80% potencial del campo, 20% dirección
    # (La estructura domina un poco más que el movimiento)
    guide = 0.8 * potential_value + 0.2 * direction_bonus
    
    return guide

# ============================================================================
# ALGORITMO TSP - GOLDEN NEEDLE
# ============================================================================

def tsp_golden_needle(cities, start_idx=0, verbose=False):
    """
    PIMST v7.0 "GOLDEN NEEDLE"
    
    El equilibrio perfecto entre estructura y adaptación.
    La aguja dorada no es brillante - es SUTIL.
    """
    n = len(cities)
    visited = np.zeros(n, dtype=bool)
    tour = [start_idx]
    visited[start_idx] = True
    current_city = cities[start_idx]
    
    # Estructura global (30% de influencia)
    global_center = np.mean(cities, axis=0)
    global_radius = np.mean(np.linalg.norm(cities - global_center, axis=1))
    
    # Análisis de intersecciones una vez (no recalculo dinámico)
    # Esto da ESTABILIDAD
    intersections = find_intersections_sample(cities)
    
    if verbose:
        print(f"🧭 Estructura global: centro={global_center}, radio={global_radius:.2f}")
        print(f"🔥 Puntos calientes: {len(intersections)} intersecciones")
    
    prev_direction = None
    
    # Construcción del tour
    for step in range(n - 1):
        # Campo de potenciales actualizado suavemente
        # (se actualiza, pero sin recalcular intersecciones - continuidad)
        potential_field = create_smooth_potential_field(
            cities, visited, intersections, global_center, global_radius
        )
        
        # Candidatos no visitados
        unvisited_mask = ~visited
        unvisited_cities = cities[unvisited_mask]
        
        # Distancias base
        distances = np.linalg.norm(unvisited_cities - current_city, axis=1)
        
        # Calcular guías suaves para cada candidato
        guides = np.array([
            compute_smooth_guide(current_city, candidate, 
                               potential_field, unvisited_cities, prev_direction)
            for candidate in unvisited_cities
        ])
        
        # FUNCIÓN OBJETIVO: Balance sutil
        # 60% distancia (fundamental)
        # 40% guía del campo (estructura + adaptación)
        normalized_distances = distances / (distances.max() + 1e-10)
        scores = 0.6 * normalized_distances - 0.4 * guides
        
        # Mejor candidato
        best_idx_local = np.argmin(scores)
        best_idx_global = np.where(unvisited_mask)[0][best_idx_local]
        
        next_city = cities[best_idx_global]
        tour.append(best_idx_global)
        visited[best_idx_global] = True
        
        # Actualizar dirección suavemente (no abrupta)
        new_direction = next_city - current_city
        new_direction = new_direction / (np.linalg.norm(new_direction) + 1e-10)
        
        if prev_direction is not None:
            # Suavizado exponencial (la dirección evoluciona gradualmente)
            alpha = 0.6  # Balance entre nueva y antigua dirección
            prev_direction = alpha * new_direction + (1 - alpha) * prev_direction
            prev_direction = prev_direction / (np.linalg.norm(prev_direction) + 1e-10)
        else:
            prev_direction = new_direction
        
        current_city = next_city
    
    return tour

# ============================================================================
# OPTIMIZACIÓN MULTI-START
# ============================================================================

def pimst_v7_golden_needle(cities, k=8, verbose=False):
    """
    PIMST v7.0 con multi-start usando filotaxis.
    
    k=8 es el balance óptimo descubierto en v1-v6.
    """
    n = len(cities)
    best_tour = None
    best_length = float('inf')
    
    # Puntos de inicio con filotaxis (estructura suave de la naturaleza)
    angles = [i * GOLDEN_ANGLE for i in range(k)]
    
    for i, angle in enumerate(angles):
        # Punto de inicio rotado
        centroid = np.mean(cities, axis=0)
        radius = np.mean(np.linalg.norm(cities - centroid, axis=1))
        
        start_point = centroid + radius * np.array([np.cos(angle), np.sin(angle)])
        start_idx = np.argmin(np.linalg.norm(cities - start_point, axis=1))
        
        # Construir tour
        tour = tsp_golden_needle(cities, start_idx, verbose=(i==0 and verbose))
        
        # Calcular longitud
        length = sum(np.linalg.norm(cities[tour[i]] - cities[tour[i+1]]) 
                    for i in range(len(tour)-1))
        length += np.linalg.norm(cities[tour[-1]] - cities[tour[0]])
        
        if length < best_length:
            best_length = length
            best_tour = tour
    
    return best_tour, best_length

# ============================================================================
# EVALUACIÓN Y VISUALIZACIÓN
# ============================================================================

def nearest_neighbor(cities, start_idx=0):
    """Baseline: vecino más cercano."""
    n = len(cities)
    visited = np.zeros(n, dtype=bool)
    tour = [start_idx]
    visited[start_idx] = True
    current = cities[start_idx]
    
    for _ in range(n-1):
        unvisited_mask = ~visited
        unvisited = cities[unvisited_mask]
        distances = np.linalg.norm(unvisited - current, axis=1)
        next_idx_local = np.argmin(distances)
        next_idx_global = np.where(unvisited_mask)[0][next_idx_local]
        
        tour.append(next_idx_global)
        visited[next_idx_global] = True
        current = cities[next_idx_global]
    
    return tour

def tour_length(cities, tour):
    """Calcula longitud total del tour."""
    length = sum(np.linalg.norm(cities[tour[i]] - cities[tour[i+1]]) 
                for i in range(len(tour)-1))
    length += np.linalg.norm(cities[tour[-1]] - cities[tour[0]])
    return length

def visualize_v7(cities, tour_v7, tour_nn, intersections, title="PIMST v7.0 GOLDEN NEEDLE"):
    """Visualización comparativa."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    # 1. Campo de intersecciones (estructura local)
    ax = axes[0]
    ax.scatter(cities[:, 0], cities[:, 1], c='navy', s=100, zorder=3, alpha=0.6)
    if len(intersections) > 0:
        ax.scatter(intersections[:, 0], intersections[:, 1], 
                  c='orange', s=30, alpha=0.4, label='Hot spots')
    
    # Centro global (estructura global)
    center = np.mean(cities, axis=0)
    radius = np.mean(np.linalg.norm(cities - center, axis=1))
    circle = plt.Circle(center, radius, fill=False, color='gray', 
                       linestyle='--', linewidth=1, alpha=0.3, label='Estructura global')
    ax.add_patch(circle)
    ax.scatter(*center, c='red', s=200, marker='*', zorder=5, 
              label='Centro global', edgecolors='black', linewidth=1)
    
    ax.set_title('Campo de Potenciales\n(70% local + 30% global)', fontsize=11, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    
    # 2. Tour Golden Needle
    ax = axes[1]
    tour_coords_v7 = cities[tour_v7 + [tour_v7[0]]]
    ax.plot(tour_coords_v7[:, 0], tour_coords_v7[:, 1], 
           'o-', color='gold', linewidth=2, markersize=8, 
           label=f'v7.0 Golden Needle', markeredgecolor='darkgoldenrod', markeredgewidth=1.5)
    ax.scatter(cities[tour_v7[0], 0], cities[tour_v7[0], 1], 
              c='red', s=300, marker='*', zorder=5, edgecolors='black', linewidth=2)
    
    length_v7 = tour_length(cities, tour_v7)
    ax.set_title(f'PIMST v7.0 - Golden Needle\nLongitud: {length_v7:.4f}', 
                fontsize=11, fontweight='bold')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=9)
    
    # 3. Comparación con Baseline
    ax = axes[2]
    tour_coords_nn = cities[tour_nn + [tour_nn[0]]]
    ax.plot(tour_coords_nn[:, 0], tour_coords_nn[:, 1], 
           'o-', color='gray', linewidth=1.5, markersize=6, 
           alpha=0.6, label='Nearest Neighbor')
    ax.plot(tour_coords_v7[:, 0], tour_coords_v7[:, 1], 
           'o-', color='gold', linewidth=2, markersize=8, 
           label='v7.0 Golden Needle', markeredgecolor='darkgoldenrod', markeredgewidth=1.5)
    
    length_nn = tour_length(cities, tour_nn)
    improvement = ((length_nn - length_v7) / length_nn) * 100
    
    ax.set_title(f'Comparación\nNN: {length_nn:.4f} vs v7.0: {length_v7:.4f}\n' + 
                f'Mejora: {improvement:+.2f}%', 
                fontsize=11, fontweight='bold')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=9)
    
    plt.suptitle(title + '\n"En la fina línea donde chocan estructura y adaptación"', 
                fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    return fig

# ============================================================================
# PRUEBA
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("PIMST v7.0 - GOLDEN NEEDLE")
    print("="*70)
    print()
    print("FILOSOFÍA:")
    print("  'Equilibrio entre dominar rígidamente el problema y seguir")
    print("   la corriente de los datos. La aguja dorada no es brillante - es SUTIL.'")
    print()
    print("="*70)
    print()
    
    # Generar problema de prueba
    np.random.seed(42)
    n = 50
    
    # Distribución con clusters (estructura natural)
    centers = np.random.uniform(-5, 5, (4, 2))
    cities = []
    for center in centers:
        cluster = np.random.randn(n//4, 2) * 0.8 + center
        cities.extend(cluster)
    cities = np.array(cities[:n])
    
    print(f"Problema: {n} ciudades con estructura de clusters")
    print()
    
    # Baseline
    print("Calculando baseline (Nearest Neighbor)...")
    tour_nn = nearest_neighbor(cities)
    length_nn = tour_length(cities, tour_nn)
    print(f"  Longitud NN: {length_nn:.4f}")
    print()
    
    # PIMST v7.0 Golden Needle
    print("Ejecutando PIMST v7.0 Golden Needle...")
    start_time = time.time()
    tour_v7, length_v7 = pimst_v7_golden_needle(cities, k=8, verbose=True)
    elapsed = time.time() - start_time
    
    print()
    print("="*70)
    print("RESULTADOS")
    print("="*70)
    print(f"  Baseline NN:     {length_nn:.4f}")
    print(f"  v7.0 Golden:     {length_v7:.4f}")
    
    improvement = ((length_nn - length_v7) / length_nn) * 100
    print(f"  Mejora:          {improvement:+.2f}%")
    print(f"  Tiempo:          {elapsed:.2f}s")
    print()
    
    # Análisis de intersecciones para visualización
    intersections = find_intersections_sample(cities)
    
    # Visualizar
    fig = visualize_v7(cities, tour_v7, tour_nn, intersections)
    plt.savefig('/home/claude/pimst_v7_golden_needle.png', dpi=150, bbox_inches='tight')
    print("✓ Visualización guardada: pimst_v7_golden_needle.png")
    print()
    
    if improvement > 0:
        print("✨ LA AGUJA DORADA ENCONTRÓ EL CAMINO ✨")
        print()
        print("El equilibrio sutil entre estructura y adaptación superó al baseline.")
    else:
        print("⚠️  Esta instancia no muestra mejora")
        print("   (El balance puede necesitar ajuste según el problema)")
    
    print()
    print("="*70)
