import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple, Optional
import time

# ============================================================================
# FUNCIONES BÁSICAS
# ============================================================================

def line_intersection(p1, p2, p3, p4):
    """Calcula intersección entre dos segmentos."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    
    denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
    if abs(denom) < 1e-10:
        return None
    
    t = ((x1-x3)*(y3-y4) - (y1-y3)*(x3-x4)) / denom
    u = -((x1-x2)*(y1-y3) - (y1-y2)*(x1-x3)) / denom
    
    if 0 < t < 1 and 0 < u < 1:
        x = x1 + t*(x2-x1)
        y = y1 + t*(y2-y1)
        return np.array([x, y])
    
    return None

def find_intersections_simple(cities, n_sample=20):
    """Encuentra intersecciones simplificado."""
    n = len(cities)
    if n > 40:
        indices = np.random.choice(n, n_sample, replace=False)
        sample = cities[indices]
    else:
        sample = cities
    
    intersections = []
    for i in range(len(sample)):
        for j in range(i+1, len(sample)):
            for k in range(len(sample)):
                for l in range(k+1, len(sample)):
                    if len({i,j,k,l}) < 4:
                        continue
                    inter = line_intersection(sample[i], sample[j], sample[k], sample[l])
                    if inter is not None:
                        intersections.append(inter)
    
    return np.array(intersections) if intersections else np.array([]).reshape(0,2)

def cluster_intersections(intersections, radius=0.12):
    """Agrupa intersecciones cercanas."""
    if len(intersections) == 0:
        return []
    
    used = set()
    centers = []
    
    for i, point in enumerate(intersections):
        if i in used:
            continue
        distances = np.linalg.norm(intersections - point, axis=1)
        nearby = np.where(distances < radius)[0]
        used.update(nearby)
        center = np.mean(intersections[nearby], axis=0)
        centers.append(center)
    
    return centers

def create_hotspot_arcs(cities, centers, n_arcs=5):
    """Crea arcos basados en puntos calientes."""
    if not centers:
        return []
    
    # Calcular importancia de cada centro
    importance = []
    for center in centers:
        distances = np.linalg.norm(cities - center, axis=1)
        nearby_cities = np.sum(distances < 0.2)
        importance.append(nearby_cities)
    
    # Seleccionar los más importantes
    sorted_idx = np.argsort(importance)[::-1]
    selected = [centers[i] for i in sorted_idx[:min(n_arcs, len(centers))]]
    
    arcs = []
    for center in selected:
        distances = np.linalg.norm(cities - center, axis=1)
        radius = np.mean(distances) * 0.7
        arcs.append({'center': center, 'radius': radius})
    
    return arcs

# ============================================================================
# CONSTRUCCIÓN DE TOUR
# ============================================================================

def calculate_score_v5(current, candidate, arcs):
    """Score basado SOLO en arcos (sin círculo principal)."""
    distance = np.linalg.norm(candidate - current)
    
    # Proximidad básica
    proximity = 1.0 / (distance + 1e-6)
    
    # Score de arcos
    arc_score = 0.0
    for arc in arcs:
        dist_to_center = np.linalg.norm(candidate - arc['center'])
        if dist_to_center < arc['radius'] * 1.2:
            # Bonus por estar cerca del arco
            on_arc = 1.0 - abs(dist_to_center - arc['radius']) / arc['radius']
            arc_score += on_arc * 0.5
    
    arc_score = min(arc_score, 1.0)
    
    # Combinar: más peso en arcos que en círculo principal (v3)
    total = proximity * 1.0 + arc_score * 2.5
    return total

def construct_tour(cities, start_idx, arcs):
    """Construye tour guiado por arcos."""
    n = len(cities)
    tour = [start_idx]
    unvisited = set(range(n)) - {start_idx}
    
    while unvisited:
        current = cities[tour[-1]]
        
        best_score = -float('inf')
        best_idx = None
        
        for idx in unvisited:
            candidate = cities[idx]
            score = calculate_score_v5(current, candidate, arcs)
            if score > best_score:
                best_score = score
                best_idx = idx
        
        if best_idx is None:
            distances = {i: np.linalg.norm(cities[i] - current) for i in unvisited}
            best_idx = min(distances, key=distances.get)
        
        tour.append(best_idx)
        unvisited.remove(best_idx)
    
    return tour

def two_opt(tour, cities, max_iter=300):
    """Optimización 2-opt."""
    best = tour.copy()
    best_len = sum(np.linalg.norm(cities[best[i]] - cities[best[(i+1)%len(best)]]) 
                   for i in range(len(best)))
    
    improved = True
    iters = 0
    
    while improved and iters < max_iter:
        improved = False
        for i in range(1, len(tour)-1):
            for j in range(i+1, len(tour)):
                new_tour = best[:i] + best[i:j][::-1] + best[j:]
                new_len = sum(np.linalg.norm(cities[new_tour[k]] - cities[new_tour[(k+1)%len(new_tour)]]) 
                             for k in range(len(new_tour)))
                if new_len < best_len:
                    best = new_tour
                    best_len = new_len
                    improved = True
                    break
            if improved:
                break
        iters += 1
    
    return best

# ============================================================================
# ALGORITMO PRINCIPAL
# ============================================================================

def pimst_v5_simple(cities, n_starts=8, n_arcs=5):
    """PIMST v5.0 simplificado - Solo puntos calientes."""
    print(f"\n{'='*70}")
    print(f"PIMST v5.0 - SOLO PUNTOS CALIENTES")
    print(f"{'='*70}")
    
    start_time = time.time()
    
    # 1. Encontrar intersecciones
    print(f"\n🔍 Analizando {len(cities)} ciudades...")
    intersections = find_intersections_simple(cities, n_sample=25)
    print(f"   → {len(intersections)} intersecciones encontradas")
    
    # 2. Agrupar en puntos calientes
    hot_centers = cluster_intersections(intersections, radius=0.12)
    print(f"   → {len(hot_centers)} puntos calientes identificados")
    
    # 3. Crear arcos
    arcs = create_hotspot_arcs(cities, hot_centers, n_arcs)
    print(f"   → {len(arcs)} arcos creados")
    
    # 4. Generar starts desde puntos calientes
    start_indices = []
    if hot_centers:
        for center in hot_centers[:n_starts]:
            distances = np.linalg.norm(cities - center, axis=1)
            start_indices.append(np.argmin(distances))
    else:
        # Fallback: starts aleatorios
        start_indices = list(range(min(n_starts, len(cities))))
    
    start_indices = list(set(start_indices))
    print(f"\n🚀 Construyendo {len(start_indices)} tours...")
    
    # 5. Construir tours
    best_tour = None
    best_length = float('inf')
    
    for idx in start_indices:
        tour = construct_tour(cities, idx, arcs)
        tour = two_opt(tour, cities)
        
        length = sum(np.linalg.norm(cities[tour[i]] - cities[tour[(i+1)%len(tour)]]) 
                    for i in range(len(tour)))
        
        if length < best_length:
            best_length = length
            best_tour = tour
    
    total_time = time.time() - start_time
    
    print(f"\n✓ Mejor tour: {best_length:.4f} (en {total_time:.2f}s)")
    
    return best_tour, best_length, {
        'arcs': arcs,
        'hot_centers': hot_centers,
        'intersections': intersections,
        'time': total_time
    }

# ============================================================================
# COMPARACIÓN
# ============================================================================

def compare_versions(cities):
    """Compara v3.0 (con círculo) vs v5.0 (solo puntos calientes)."""
    print("\n" + "="*70)
    print("COMPARACIÓN: v3.0 (Con Círculo) vs v5.0 (Solo Puntos Calientes)")
    print("="*70)
    
    # Baseline
    print("\n1. Baseline (Nearest Neighbor + 2-opt)")
    nn_tour = [0]
    unvisited = set(range(1, len(cities)))
    while unvisited:
        current = cities[nn_tour[-1]]
        distances = {i: np.linalg.norm(cities[i] - current) for i in unvisited}
        next_idx = min(distances, key=distances.get)
        nn_tour.append(next_idx)
        unvisited.remove(next_idx)
    nn_tour = two_opt(nn_tour, cities)
    nn_length = sum(np.linalg.norm(cities[nn_tour[i]] - cities[nn_tour[(i+1)%len(nn_tour)]]) 
                   for i in range(len(nn_tour)))
    print(f"   Longitud: {nn_length:.4f}")
    
    # v5.0
    print("\n2. PIMST v5.0 (Solo Puntos Calientes)")
    tour_v5, length_v5, stats_v5 = pimst_v5_simple(cities, n_starts=8, n_arcs=5)
    improvement_v5 = ((nn_length - length_v5) / nn_length) * 100
    
    print(f"\n{'='*70}")
    print("RESUMEN")
    print(f"{'='*70}")
    print(f"Baseline NN:        {nn_length:.4f}")
    print(f"PIMST v5.0:         {length_v5:.4f}")
    print(f"Mejora:             {improvement_v5:+.2f}%")
    print(f"{'='*70}")
    
    return {
        'nn_length': nn_length,
        'v5_length': length_v5,
        'improvement': improvement_v5,
        'tour': tour_v5,
        'stats': stats_v5
    }

# ============================================================================
# VISUALIZACIÓN
# ============================================================================

def visualize_v5(cities, tour, stats):
    """Visualiza solución v5.0."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    
    # Panel izquierdo: Puntos calientes y arcos
    ax = axes[0]
    ax.scatter(cities[:, 0], cities[:, 1], c='red', s=80, zorder=5, alpha=0.7)
    
    # Intersecciones
    if len(stats['intersections']) > 0:
        ax.scatter(stats['intersections'][:, 0], stats['intersections'][:, 1],
                  c='lightblue', s=20, alpha=0.4, label='Intersecciones')
    
    # Puntos calientes
    for i, center in enumerate(stats['hot_centers']):
        ax.scatter([center[0]], [center[1]], c=f'C{i}', s=300, marker='*',
                  edgecolors='black', linewidths=2, zorder=10)
    
    # Arcos (sin círculo principal)
    for i, arc in enumerate(stats['arcs']):
        circle = plt.Circle(arc['center'], arc['radius'], 
                          fill=False, color=f'C{i}', linewidth=3, alpha=0.7,
                          label=f'Arco {i+1}' if i < 3 else '')
        ax.add_patch(circle)
    
    ax.set_title('Guías: SOLO Puntos Calientes\n(Sin Círculo Principal)',
                fontsize=13, fontweight='bold')
    ax.set_aspect('equal')
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.2)
    
    # Panel derecho: Solución
    ax = axes[1]
    ax.scatter(cities[:, 0], cities[:, 1], c='red', s=80, zorder=5, alpha=0.7)
    
    for i in range(len(tour)):
        start = cities[tour[i]]
        end = cities[tour[(i+1) % len(tour)]]
        ax.plot([start[0], end[0]], [start[1], end[1]],
               'darkgreen', linewidth=2, alpha=0.7)
    
    start_city = cities[tour[0]]
    ax.scatter([start_city[0]], [start_city[1]], c='lime', s=200,
              marker='*', edgecolors='black', linewidths=2, zorder=7)
    
    ax.set_title('Solución Final', fontsize=13, fontweight='bold')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.2)
    
    plt.suptitle('PIMST v5.0: Estructura Puramente Local', 
                fontsize=15, fontweight='bold')
    plt.tight_layout()
    
    return fig

# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    np.random.seed(42)
    
    print("Generando problema con clusters...")
    
    # Base + clusters
    cities = np.random.rand(35, 2) * 0.6 + 0.2
    cluster1 = np.random.randn(8, 2) * 0.05 + np.array([0.25, 0.75])
    cluster2 = np.random.randn(8, 2) * 0.05 + np.array([0.75, 0.25])
    cluster3 = np.random.randn(6, 2) * 0.04 + np.array([0.5, 0.5])
    cities = np.vstack([cities, cluster1, cluster2, cluster3])
    
    print(f"Problema: {len(cities)} ciudades")
    
    # Comparación
    results = compare_versions(cities)
    
    # Visualización
    print("\nGenerando visualización...")
    fig = visualize_v5(cities, results['tour'], results['stats'])
    plt.savefig('/home/claude/pimst_v5_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ Guardado: pimst_v5_comparison.png")
    plt.close()
    
    print("\n" + "="*70)
    print("INNOVACIÓN CLAVE DE v5.0")
    print("="*70)
    print("""
🎯 FILOSOFÍA:
   "Olvida la geometría artificial (círculo global).
    Sigue SOLO la estructura natural revelada por 
    los puntos donde se concentran las intersecciones."

✨ VENTAJAS:
   • 100% adaptado a la estructura del problema
   • No hay bias de círculo arbitrario
   • Guías puramente locales y orgánicas

🔬 CUÁNDO PUEDE SER MEJOR:
   • Problemas con clustering muy marcado
   • Distribuciones irregulares
   • Cuando el círculo global es contraproducente

⚠️ LIMITACIONES:
   • Depende de calidad de intersecciones
   • Puede fallar en distribuciones uniformes
   • Sin coordinación global
""")
