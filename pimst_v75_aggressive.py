"""
PIMST v7.5 "AGGRESSIVE GOLDEN NEEDLE"
======================================

FILOSOFÍA:
"Combinar la CONVICCIÓN de v5.0 con la CONTINUIDAD de v7.0"

- Campo continuo suave (v7.0) ✓
- Pesos agresivos en hot spots (v5.0) ✓
- Balance 60-40 efectivo (v5.0) ✓
- Sin dilución excesiva (problema de v7.0) ✗

INNOVACIÓN:
-----------
Aprendimos que v7.0 DILUYE demasiado la señal:
  v7.0: Hot spots al 7% efectivo → Insuficiente
  v5.0: Hot spots al 40% efectivo → Óptimo

v7.5 corrige esto manteniendo la continuidad del campo:
  v7.5: Hot spots al ~34% efectivo → Balance correcto
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple
import time

# Proporción áurea
PHI = (1 + np.sqrt(5)) / 2
GOLDEN_ANGLE = np.pi * (3 - np.sqrt(5))

# ============================================================================
# ANÁLISIS DE INTERSECCIONES (de v5.0/v7.0 - funciona bien)
# ============================================================================

def find_intersections_sample(cities, n_sample=20):
    """
    Encuentra intersecciones usando muestreo estratégico.
    """
    n = len(cities)
    if n < 10:
        n_sample = n
    
    step = max(1, n // n_sample)
    sample_indices = list(range(0, n, step))
    if len(sample_indices) > n_sample:
        sample_indices = sample_indices[:n_sample]
    
    intersections = []
    
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
# CAMPO CONTINUO AGRESIVO (v7.5)
# ============================================================================

def create_aggressive_potential_field(cities, visited_mask, intersections, 
                                      global_center, global_radius,
                                      local_weight=0.85):
    """
    Campo de potenciales con peso AGRESIVO en estructura local.
    
    Args:
        local_weight: Peso de estructura local (default 0.85 vs 0.7 en v7.0)
                     Esto da MÁS importancia a los hot spots emergentes
    """
    n = len(cities)
    unvisited = cities[~visited_mask]
    
    if len(unvisited) == 0:
        return None
    
    # COMPONENTE LOCAL (DOMINANTE): Densidad de intersecciones
    if len(intersections) > 0:
        bandwidth = np.std(cities) / PHI
        
        local_potentials = []
        for city in unvisited:
            distances = np.linalg.norm(intersections - city, axis=1)
            density = np.sum(np.exp(-distances**2 / (2 * bandwidth**2)))
            local_potentials.append(density)
        
        local_potentials = np.array(local_potentials)
        if local_potentials.max() > 0:
            local_potentials = local_potentials / local_potentials.max()
    else:
        local_potentials = np.zeros(len(unvisited))
    
    # COMPONENTE GLOBAL (MÍNIMO): Estructura suave de respaldo
    global_potentials = []
    for city in unvisited:
        dist_to_center = np.linalg.norm(city - global_center)
        global_potential = np.exp(-(dist_to_center / global_radius)**2)
        global_potentials.append(global_potential)
    
    global_potentials = np.array(global_potentials)
    if global_potentials.max() > 0:
        global_potentials = global_potentials / global_potentials.max()
    
    # Balance AGRESIVO: 85% local + 15% global
    # (vs 70-30 en v7.0)
    global_weight = 1.0 - local_weight
    combined_potential = local_weight * local_potentials + global_weight * global_potentials
    
    return combined_potential

def compute_aggressive_guide(current_city, candidate_city, 
                             combined_potential, unvisited, 
                             prev_direction=None,
                             direction_weight=0.1):
    """
    Guía con peso REDUCIDO en dirección (más peso al campo de potenciales).
    
    Args:
        direction_weight: Peso de dirección (default 0.1 vs 0.2 en v7.0)
                         Menos inercia direccional, más reactividad a estructura
    """
    idx = np.where(np.all(unvisited == candidate_city, axis=1))[0]
    if len(idx) == 0:
        return 0.0
    
    potential_value = combined_potential[idx[0]]
    
    direction_bonus = 0.0
    if prev_direction is not None:
        current_direction = candidate_city - current_city
        current_direction = current_direction / (np.linalg.norm(current_direction) + 1e-10)
        
        direction_bonus = np.dot(current_direction, prev_direction)
        direction_bonus = (direction_bonus + 1) / 2
    
    # Balance: 90% potencial + 10% dirección
    # (vs 80-20 en v7.0)
    potential_weight = 1.0 - direction_weight
    guide = potential_weight * potential_value + direction_weight * direction_bonus
    
    return guide

# ============================================================================
# ALGORITMO TSP - AGGRESSIVE GOLDEN NEEDLE
# ============================================================================

def tsp_aggressive_golden_needle(cities, start_idx=0, verbose=False):
    """
    PIMST v7.5 "AGGRESSIVE GOLDEN NEEDLE"
    
    Combina:
    - Campo continuo suave (v7.0)
    - Pesos agresivos (v5.0)
    
    Balance efectivo esperado: ~34% en hot spots
    """
    n = len(cities)
    visited = np.zeros(n, dtype=bool)
    tour = [start_idx]
    visited[start_idx] = True
    current_city = cities[start_idx]
    
    # PARÁMETROS AGRESIVOS (v7.5)
    DIST_WEIGHT = 0.6      # vs 0.9 en v7.0 - MÁS peso a estructura
    LOCAL_WEIGHT = 0.85    # vs 0.7 en v7.0 - PREFERIR local fuertemente
    DIRECTION_WEIGHT = 0.1 # vs 0.2 en v7.0 - MENOS inercia
    
    # Estructura global (mínima, solo respaldo)
    global_center = np.mean(cities, axis=0)
    global_radius = np.mean(np.linalg.norm(cities - global_center, axis=1))
    
    # Análisis de intersecciones una vez (estabilidad)
    intersections = find_intersections_sample(cities)
    
    if verbose:
        print(f"🎯 PARÁMETROS AGRESIVOS v7.5:")
        print(f"   • Distancia: {DIST_WEIGHT*100:.0f}% (vs 90% en v7.0)")
        print(f"   • Estructura local: {LOCAL_WEIGHT*100:.0f}% (vs 70% en v7.0)")
        print(f"   • Dirección: {DIRECTION_WEIGHT*100:.0f}% (vs 20% en v7.0)")
        print(f"   • Hot spots efectivos: ~{(1-DIST_WEIGHT)*LOCAL_WEIGHT*(1-DIRECTION_WEIGHT)*100:.0f}%")
        print(f"🔥 Puntos calientes: {len(intersections)} intersecciones")
    
    prev_direction = None
    
    # Construcción del tour
    for step in range(n - 1):
        # Campo de potenciales con balance AGRESIVO
        potential_field = create_aggressive_potential_field(
            cities, visited, intersections, global_center, global_radius,
            local_weight=LOCAL_WEIGHT
        )
        
        unvisited_mask = ~visited
        unvisited_cities = cities[unvisited_mask]
        distances = np.linalg.norm(unvisited_cities - current_city, axis=1)
        
        # Guías con dirección REDUCIDA
        guides = np.array([
            compute_aggressive_guide(current_city, candidate, 
                                   potential_field, unvisited_cities, prev_direction,
                                   direction_weight=DIRECTION_WEIGHT)
            for candidate in unvisited_cities
        ])
        
        # FUNCIÓN OBJETIVO AGRESIVA: 60% distancia + 40% guía
        # (vs 90-10 en v7.0)
        normalized_distances = distances / (distances.max() + 1e-10)
        guide_weight = 1.0 - DIST_WEIGHT
        scores = DIST_WEIGHT * normalized_distances - guide_weight * guides
        
        best_idx_local = np.argmin(scores)
        best_idx_global = np.where(unvisited_mask)[0][best_idx_local]
        
        next_city = cities[best_idx_global]
        tour.append(best_idx_global)
        visited[best_idx_global] = True
        
        # Actualizar dirección suavemente (menos inercia que v7.0)
        new_direction = next_city - current_city
        new_direction = new_direction / (np.linalg.norm(new_direction) + 1e-10)
        
        if prev_direction is not None:
            # Menos inercia: 70% nueva dirección vs 60% en v7.0
            alpha = 0.7
            prev_direction = alpha * new_direction + (1 - alpha) * prev_direction
            prev_direction = prev_direction / (np.linalg.norm(prev_direction) + 1e-10)
        else:
            prev_direction = new_direction
        
        current_city = next_city
    
    return tour

# ============================================================================
# OPTIMIZACIÓN MULTI-START
# ============================================================================

def pimst_v75_aggressive(cities, k=8, verbose=False):
    """
    PIMST v7.5 con multi-start usando filotaxis.
    """
    n = len(cities)
    best_tour = None
    best_length = float('inf')
    
    angles = [i * GOLDEN_ANGLE for i in range(k)]
    
    for i, angle in enumerate(angles):
        centroid = np.mean(cities, axis=0)
        radius = np.mean(np.linalg.norm(cities - centroid, axis=1))
        
        start_point = centroid + radius * np.array([np.cos(angle), np.sin(angle)])
        start_idx = np.argmin(np.linalg.norm(cities - start_point, axis=1))
        
        tour = tsp_aggressive_golden_needle(cities, start_idx, verbose=(i==0 and verbose))
        
        length = sum(np.linalg.norm(cities[tour[i]] - cities[tour[i+1]]) 
                    for i in range(len(tour)-1))
        length += np.linalg.norm(cities[tour[-1]] - cities[tour[0]])
        
        if length < best_length:
            best_length = length
            best_tour = tour
    
    return best_tour, best_length

# ============================================================================
# FUNCIONES AUXILIARES
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

# ============================================================================
# VISUALIZACIÓN
# ============================================================================

def visualize_v75(cities, tours_dict, intersections, title="PIMST v7.5 AGGRESSIVE"):
    """
    Visualización comparativa de múltiples versiones.
    
    tours_dict: {'v5.0': tour5, 'v7.0': tour7, 'v7.5': tour75, 'NN': tour_nn}
    """
    n_versions = len(tours_dict)
    fig, axes = plt.subplots(1, n_versions, figsize=(6*n_versions, 6))
    if n_versions == 1:
        axes = [axes]
    
    colors = {
        'NN': 'gray',
        'v5.0': 'blue',
        'v7.0': 'gold',
        'v7.5': 'red'
    }
    
    for idx, (version, tour) in enumerate(tours_dict.items()):
        ax = axes[idx]
        
        # Tour
        tour_coords = cities[tour + [tour[0]]]
        color = colors.get(version, 'green')
        linewidth = 3 if version == 'v7.5' else 2
        alpha = 1.0 if version == 'v7.5' else 0.7
        
        ax.plot(tour_coords[:, 0], tour_coords[:, 1], 
               'o-', color=color, linewidth=linewidth, markersize=8, 
               alpha=alpha, label=version,
               markeredgecolor='black' if version == 'v7.5' else color,
               markeredgewidth=2 if version == 'v7.5' else 1)
        
        # Ciudad inicial
        ax.scatter(cities[tour[0], 0], cities[tour[0], 1], 
                  c='red', s=300, marker='*', zorder=5, 
                  edgecolors='black', linewidth=2)
        
        # Hot spots (solo en v7.5)
        if version == 'v7.5' and len(intersections) > 0:
            ax.scatter(intersections[:, 0], intersections[:, 1], 
                      c='orange', s=20, alpha=0.3, label='Hot spots', zorder=1)
        
        length = tour_length(cities, tour)
        ax.set_title(f'{version}\nLongitud: {length:.4f}', 
                    fontsize=12, fontweight='bold')
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=9)
    
    plt.suptitle(title, fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    return fig

# ============================================================================
# PRUEBA SIMPLE
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("PIMST v7.5 - AGGRESSIVE GOLDEN NEEDLE")
    print("="*80)
    print()
    print("CONCEPTO:")
    print("  Combinar la CONVICCIÓN de v5.0 (40% hot spots)")
    print("  con la CONTINUIDAD de v7.0 (campo suave)")
    print()
    print("PARÁMETROS:")
    print("  • dist_weight: 0.6 (vs 0.9 en v7.0)")
    print("  • local_weight: 0.85 (vs 0.7 en v7.0)")
    print("  • direction_weight: 0.1 (vs 0.2 en v7.0)")
    print()
    print("  → Peso efectivo en hot spots: ~34%")
    print("    (vs 7% en v7.0, 40% en v5.0)")
    print()
    print("="*80)
    print()
    
    # Problema de prueba
    np.random.seed(42)
    n = 50
    
    # Distribución con clusters (donde v5.0 destaca)
    centers = np.random.uniform(-5, 5, (4, 2))
    cities = []
    for center in centers:
        cluster = np.random.randn(n//4, 2) * 0.8 + center
        cities.extend(cluster)
    cities = np.array(cities[:n])
    
    print(f"Problema: {n} ciudades con 4 clusters")
    print()
    
    # Baseline
    print("Calculando baseline (Nearest Neighbor)...")
    tour_nn = nearest_neighbor(cities)
    length_nn = tour_length(cities, tour_nn)
    print(f"  Longitud NN: {length_nn:.4f}")
    print()
    
    # PIMST v7.5 Aggressive
    print("Ejecutando PIMST v7.5 Aggressive Golden Needle...")
    start_time = time.time()
    tour_v75, length_v75 = pimst_v75_aggressive(cities, k=8, verbose=True)
    elapsed = time.time() - start_time
    
    print()
    print("="*80)
    print("RESULTADO")
    print("="*80)
    print(f"  Baseline NN:     {length_nn:.4f}")
    print(f"  v7.5 Aggressive: {length_v75:.4f}")
    
    improvement = ((length_nn - length_v75) / length_nn) * 100
    print(f"  Mejora:          {improvement:+.2f}%")
    print(f"  Tiempo:          {elapsed:.2f}s")
    print()
    
    # Intersecciones para visualización
    intersections = find_intersections_sample(cities)
    
    # Visualizar
    tours = {
        'NN': tour_nn,
        'v7.5 Aggressive': tour_v75
    }
    
    fig = visualize_v75(cities, tours, intersections)
    plt.savefig('/home/claude/pimst_v75_aggressive.png', dpi=150, bbox_inches='tight')
    print("✓ Visualización guardada: pimst_v75_aggressive.png")
    print()
    
    if improvement > 5:
        print("🎉 ¡EXCELENTE! La agresividad paga dividendos")
    elif improvement > 0:
        print("✅ Mejora positiva - en la dirección correcta")
    else:
        print("⚠️  Esta instancia no muestra mejora")
    
    print()
    print("="*80)
