import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple, Optional
from itertools import combinations
import time

# ============================================================================
# FUNCIONES DE ANÁLISIS DE INTERSECCIONES
# ============================================================================

def line_intersection(p1: np.ndarray, p2: np.ndarray, 
                      p3: np.ndarray, p4: np.ndarray) -> Optional[np.ndarray]:
    """Encuentra el punto de intersección entre dos segmentos."""
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

def find_intersection_centers(cities: np.ndarray, 
                              sample_ratio: float = 0.3,
                              cluster_radius: float = 0.15) -> List[np.ndarray]:
    """
    Encuentra centros de convergencia basados en intersecciones.
    Usa sampling para ciudades >50 para mantener eficiencia.
    """
    n = len(cities)
    
    # Para conjuntos grandes, usar muestreo
    if n > 50:
        n_sample = int(n * sample_ratio)
        sample_indices = np.random.choice(n, n_sample, replace=False)
        sample_cities = cities[sample_indices]
    else:
        sample_cities = cities
    
    intersections = []
    edges = list(combinations(range(len(sample_cities)), 2))
    
    # Calcular intersecciones
    for i, (a, b) in enumerate(edges):
        for c, d in edges[i+1:]:
            if len({a, b, c, d}) == 4:
                intersection = line_intersection(
                    sample_cities[a], sample_cities[b],
                    sample_cities[c], sample_cities[d]
                )
                if intersection is not None:
                    intersections.append(intersection)
    
    if not intersections:
        return []
    
    intersections = np.array(intersections)
    
    # Agrupar intersecciones cercanas
    clusters = []
    used = set()
    
    for i, point in enumerate(intersections):
        if i in used:
            continue
        
        distances = np.linalg.norm(intersections - point, axis=1)
        cluster_indices = np.where(distances < cluster_radius)[0]
        used.update(cluster_indices)
        
        centroid = np.mean(intersections[cluster_indices], axis=0)
        clusters.append(centroid)
    
    return clusters

def create_secondary_guides(cities: np.ndarray,
                           intersection_centers: List[np.ndarray],
                           n_circles: int = 3) -> List[Tuple[np.ndarray, float]]:
    """
    Crea círculos secundarios basados en centros de intersección.
    """
    if not intersection_centers:
        return []
    
    centers = np.array(intersection_centers)
    
    # Calcular densidad (ciudades cercanas) para cada centro
    densities = []
    for center in centers:
        distances = np.linalg.norm(cities - center, axis=1)
        density = np.sum(distances < np.median(distances))
        densities.append(density)
    
    # Seleccionar centros más densos
    sorted_indices = np.argsort(densities)[::-1]
    selected_centers = centers[sorted_indices[:min(n_circles, len(centers))]]
    
    # Calcular radio para cada círculo
    circles = []
    for center in selected_centers:
        distances = np.linalg.norm(cities - center, axis=1)
        radius = np.mean(distances) * 0.8  # 80% de la distancia media
        circles.append((center, radius))
    
    return circles

# ============================================================================
# ALGORITMO TSP MEJORADO CON MÚLTIPLES GUÍAS GEOMÉTRICAS
# ============================================================================

def calculate_tour_length(tour: List[int], cities: np.ndarray) -> float:
    """Calcula la longitud total del tour."""
    length = 0
    for i in range(len(tour)):
        length += np.linalg.norm(cities[tour[i]] - cities[tour[(i+1) % len(tour)]])
    return length

def two_opt(tour: List[int], cities: np.ndarray, max_iterations: int = 1000) -> List[int]:
    """Optimización 2-opt."""
    improved = True
    iterations = 0
    best_tour = tour.copy()
    best_length = calculate_tour_length(best_tour, cities)
    
    while improved and iterations < max_iterations:
        improved = False
        for i in range(1, len(tour) - 1):
            for j in range(i + 1, len(tour)):
                new_tour = best_tour[:i] + best_tour[i:j][::-1] + best_tour[j:]
                new_length = calculate_tour_length(new_tour, cities)
                
                if new_length < best_length:
                    best_tour = new_tour
                    best_length = new_length
                    improved = True
                    break
            if improved:
                break
        iterations += 1
    
    return best_tour

def calculate_multi_guide_score(current_city: np.ndarray,
                                candidate_city: np.ndarray,
                                primary_circle_center: np.ndarray,
                                primary_radius: float,
                                secondary_circles: List[Tuple[np.ndarray, float]],
                                tangent_direction: Optional[np.ndarray],
                                weights: dict) -> float:
    """
    Calcula score combinando múltiples guías geométricas:
    1. Proximidad (distancia básica)
    2. Círculo principal (filotaxis)
    3. Círculos secundarios (intersecciones)
    4. Tangente (predicción de dirección)
    """
    distance = np.linalg.norm(candidate_city - current_city)
    
    # 1. Score de proximidad (invertido - menor distancia = mejor)
    proximity_score = 1.0 / (distance + 1e-6)
    
    # 2. Score del círculo principal
    current_angle = np.arctan2(current_city[1] - primary_circle_center[1],
                               current_city[0] - primary_circle_center[0])
    candidate_angle = np.arctan2(candidate_city[1] - primary_circle_center[1],
                                 candidate_city[0] - primary_circle_center[0])
    angle_diff = abs(((candidate_angle - current_angle + np.pi) % (2 * np.pi)) - np.pi)
    
    current_dist_to_center = np.linalg.norm(current_city - primary_circle_center)
    candidate_dist_to_center = np.linalg.norm(candidate_city - primary_circle_center)
    
    is_on_circle = abs(candidate_dist_to_center - primary_radius) < primary_radius * 0.3
    primary_circle_score = (1.0 - angle_diff / np.pi) * (1.0 if is_on_circle else 0.5)
    
    # 3. Score de círculos secundarios
    secondary_score = 0.0
    if secondary_circles:
        for sec_center, sec_radius in secondary_circles:
            cand_dist = np.linalg.norm(candidate_city - sec_center)
            if cand_dist < sec_radius * 1.2:  # Dentro o cerca del semicírculo
                # Bonus si está cerca del borde del círculo secundario
                on_edge_bonus = 1.0 - abs(cand_dist - sec_radius) / sec_radius
                secondary_score += on_edge_bonus * 0.5
        secondary_score = min(secondary_score, 1.0)  # Normalizar
    
    # 4. Score de tangente
    tangent_score = 0.0
    if tangent_direction is not None:
        direction_to_candidate = candidate_city - current_city
        direction_to_candidate = direction_to_candidate / (np.linalg.norm(direction_to_candidate) + 1e-6)
        
        dot_product = np.dot(tangent_direction, direction_to_candidate)
        tangent_score = (dot_product + 1) / 2  # Normalizar a [0, 1]
    
    # Combinar scores con pesos
    total_score = (weights['proximity'] * proximity_score +
                   weights['primary_circle'] * primary_circle_score +
                   weights['secondary_circles'] * secondary_score +
                   weights['tangent'] * tangent_score)
    
    return total_score

def construct_tour_multi_guide(cities: np.ndarray,
                               start_idx: int,
                               primary_circle_center: np.ndarray,
                               primary_radius: float,
                               secondary_circles: List[Tuple[np.ndarray, float]],
                               weights: dict) -> List[int]:
    """
    Construye un tour usando múltiples guías geométricas.
    """
    n = len(cities)
    tour = [start_idx]
    unvisited = set(range(n)) - {start_idx}
    
    while unvisited:
        current_idx = tour[-1]
        current_city = cities[current_idx]
        
        # Calcular dirección tangente del círculo principal
        tangent_direction = None
        if len(tour) >= 2:
            prev_city = cities[tour[-2]]
            direction = current_city - prev_city
            direction = direction / (np.linalg.norm(direction) + 1e-6)
            
            # Tangente perpendicular al radio
            to_center = primary_circle_center - current_city
            to_center = to_center / (np.linalg.norm(to_center) + 1e-6)
            tangent = np.array([-to_center[1], to_center[0]])
            
            # Combinar dirección previa con tangente
            tangent_direction = weights['tangent_weight'] * tangent + \
                              (1 - weights['tangent_weight']) * direction
            tangent_direction = tangent_direction / (np.linalg.norm(tangent_direction) + 1e-6)
        
        # Evaluar todas las ciudades no visitadas
        best_score = -float('inf')
        best_idx = None
        
        for idx in unvisited:
            candidate_city = cities[idx]
            score = calculate_multi_guide_score(
                current_city, candidate_city,
                primary_circle_center, primary_radius,
                secondary_circles, tangent_direction, weights
            )
            
            if score > best_score:
                best_score = score
                best_idx = idx
        
        tour.append(best_idx)
        unvisited.remove(best_idx)
    
    return tour

def pimst_v3_with_intersection_guides(cities: np.ndarray,
                                      n_starts: int = 8,
                                      use_intersection_guides: bool = True,
                                      n_secondary_circles: int = 3,
                                      weights: Optional[dict] = None) -> Tuple[List[int], float, dict]:
    """
    PIMST v3.0: Filotaxis + Tangentes + Círculos Secundarios de Intersección
    """
    if weights is None:
        weights = {
            'proximity': 1.0,
            'primary_circle': 0.8,
            'secondary_circles': 0.6,
            'tangent': 0.4,
            'tangent_weight': 0.4
        }
    
    start_time = time.time()
    n = len(cities)
    
    # Calcular centro y radio del círculo principal
    centroid = np.mean(cities, axis=0)
    distances = np.linalg.norm(cities - centroid, axis=1)
    radius = np.mean(distances)
    
    # Crear círculos secundarios basados en intersecciones
    secondary_circles = []
    if use_intersection_guides:
        print("Analizando intersecciones para crear guías secundarias...")
        intersection_centers = find_intersection_centers(cities, 
                                                        sample_ratio=0.4,
                                                        cluster_radius=0.15)
        if intersection_centers:
            secondary_circles = create_secondary_guides(cities, 
                                                       intersection_centers,
                                                       n_secondary_circles)
            print(f"  → {len(secondary_circles)} círculos secundarios creados")
    
    # Generar puntos de inicio usando ángulo dorado (filotaxis)
    golden_angle = np.pi * (3 - np.sqrt(5))
    angles = np.array([i * golden_angle for i in range(n_starts)])
    start_points = centroid + radius * np.column_stack([np.cos(angles), np.sin(angles)])
    
    # Encontrar ciudad más cercana a cada punto de inicio
    start_indices = []
    for point in start_points:
        distances = np.linalg.norm(cities - point, axis=1)
        start_indices.append(np.argmin(distances))
    start_indices = list(set(start_indices))
    
    print(f"Ejecutando {len(start_indices)} construcciones multi-guía...")
    
    # Construir tours desde cada punto de inicio
    best_tour = None
    best_length = float('inf')
    
    for idx in start_indices:
        tour = construct_tour_multi_guide(cities, idx, centroid, radius,
                                         secondary_circles, weights)
        tour = two_opt(tour, cities, max_iterations=1000)
        length = calculate_tour_length(tour, cities)
        
        if length < best_length:
            best_length = length
            best_tour = tour
    
    stats = {
        'computation_time': time.time() - start_time,
        'n_starts': len(start_indices),
        'n_secondary_circles': len(secondary_circles),
        'primary_radius': radius,
        'weights': weights
    }
    
    return best_tour, best_length, stats

# ============================================================================
# VISUALIZACIÓN
# ============================================================================

def visualize_solution_with_guides(cities: np.ndarray,
                                   tour: List[int],
                                   secondary_circles: List[Tuple[np.ndarray, float]],
                                   primary_center: np.ndarray,
                                   primary_radius: float,
                                   title: str = "PIMST v3.0 con Guías Múltiples"):
    """Visualiza la solución mostrando todas las guías geométricas."""
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
    
    # Panel izquierdo: Guías geométricas
    ax = axes[0]
    ax.scatter(cities[:, 0], cities[:, 1], c='red', s=100, zorder=5, 
              alpha=0.6, label='Ciudades')
    
    # Círculo principal (filotaxis)
    circle_main = plt.Circle(primary_center, primary_radius, 
                            fill=False, color='blue', linewidth=2, 
                            linestyle='--', label='Círculo Principal')
    ax.add_patch(circle_main)
    ax.scatter([primary_center[0]], [primary_center[1]], 
              c='blue', s=200, marker='x', linewidths=3)
    
    # Círculos secundarios (intersecciones)
    for i, (center, radius) in enumerate(secondary_circles):
        circle = plt.Circle(center, radius, fill=False, 
                          color=f'C{i+2}', linewidth=2, alpha=0.7,
                          label=f'Guía Secundaria {i+1}')
        ax.add_patch(circle)
        ax.scatter([center[0]], [center[1]], 
                  c=f'C{i+2}', s=150, marker='*', 
                  edgecolors='black', linewidths=2, zorder=6)
    
    ax.set_title('Guías Geométricas', fontsize=14, fontweight='bold')
    ax.set_aspect('equal')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    # Panel derecho: Solución final
    ax = axes[1]
    ax.scatter(cities[:, 0], cities[:, 1], c='red', s=100, zorder=5, alpha=0.6)
    
    for i in range(len(tour)):
        start = cities[tour[i]]
        end = cities[tour[(i+1) % len(tour)]]
        ax.plot([start[0], end[0]], [start[1], end[1]], 
               'g-', linewidth=2, alpha=0.7)
    
    # Marcar inicio
    start_city = cities[tour[0]]
    ax.scatter([start_city[0]], [start_city[1]], c='lime', s=300, 
              marker='*', edgecolors='black', linewidths=2, 
              zorder=7, label='Inicio')
    
    ax.set_title('Solución Final', fontsize=14, fontweight='bold')
    ax.set_aspect('equal')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.suptitle(title, fontsize=16, fontweight='bold')
    plt.tight_layout()
    return fig

# ============================================================================
# EXPERIMENTO COMPARATIVO
# ============================================================================

def run_comparison_experiment(cities: np.ndarray):
    """Compara diferentes configuraciones del algoritmo."""
    print("=" * 70)
    print("EXPERIMENTO COMPARATIVO - PIMST v3.0")
    print("=" * 70)
    
    # Baseline: Nearest Neighbor
    print("\n1. Baseline - Nearest Neighbor...")
    nn_tour = [0]
    unvisited = set(range(1, len(cities)))
    while unvisited:
        current = cities[nn_tour[-1]]
        distances = {idx: np.linalg.norm(cities[idx] - current) for idx in unvisited}
        next_city = min(distances, key=distances.get)
        nn_tour.append(next_city)
        unvisited.remove(next_city)
    nn_tour = two_opt(nn_tour, cities)
    nn_length = calculate_tour_length(nn_tour, cities)
    print(f"   Longitud: {nn_length:.4f}")
    
    # PIMST v2 (solo círculo + tangentes)
    print("\n2. PIMST v2.0 (Círculo Principal + Tangentes)...")
    tour_v2, length_v2, stats_v2 = pimst_v3_with_intersection_guides(
        cities, n_starts=8, use_intersection_guides=False
    )
    improvement_v2 = ((nn_length - length_v2) / nn_length) * 100
    print(f"   Longitud: {length_v2:.4f}")
    print(f"   Mejora vs NN: {improvement_v2:.2f}%")
    print(f"   Tiempo: {stats_v2['computation_time']:.2f}s")
    
    # PIMST v3 (círculo + tangentes + círculos secundarios)
    print("\n3. PIMST v3.0 (+ Círculos Secundarios de Intersección)...")
    tour_v3, length_v3, stats_v3 = pimst_v3_with_intersection_guides(
        cities, n_starts=8, use_intersection_guides=True, n_secondary_circles=3
    )
    improvement_v3 = ((nn_length - length_v3) / nn_length) * 100
    additional_improvement = ((length_v2 - length_v3) / length_v2) * 100
    print(f"   Longitud: {length_v3:.4f}")
    print(f"   Mejora vs NN: {improvement_v3:.2f}%")
    print(f"   Mejora adicional vs v2.0: {additional_improvement:.2f}%")
    print(f"   Tiempo: {stats_v3['computation_time']:.2f}s")
    print(f"   Círculos secundarios: {stats_v3['n_secondary_circles']}")
    
    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"{'Método':<40} {'Longitud':<12} {'Mejora vs NN':<15}")
    print("-" * 70)
    print(f"{'Nearest Neighbor (Baseline)':<40} {nn_length:>10.4f}  {'0.00%':>13}")
    print(f"{'PIMST v2.0 (Círculo + Tangentes)':<40} {length_v2:>10.4f}  {improvement_v2:>12.2f}%")
    print(f"{'PIMST v3.0 (+ Círculos Secundarios)':<40} {length_v3:>10.4f}  {improvement_v3:>12.2f}%")
    print("=" * 70)
    
    # Crear centros y radios para visualización
    centroid = np.mean(cities, axis=0)
    radius = np.mean(np.linalg.norm(cities - centroid, axis=1))
    
    intersection_centers = find_intersection_centers(cities, sample_ratio=0.4)
    secondary_circles = create_secondary_guides(cities, intersection_centers, 3) if intersection_centers else []
    
    # Visualizar
    fig = visualize_solution_with_guides(
        cities, tour_v3, secondary_circles, centroid, radius,
        f"PIMST v3.0 - Mejora: {improvement_v3:.2f}% vs NN, {additional_improvement:.2f}% vs v2.0"
    )
    
    return fig, {
        'nn_length': nn_length,
        'v2_length': length_v2,
        'v3_length': length_v3,
        'improvement_v2': improvement_v2,
        'improvement_v3': improvement_v3,
        'additional_improvement': additional_improvement
    }

# ============================================================================
# EJECUCIÓN
# ============================================================================

if __name__ == "__main__":
    np.random.seed(42)
    
    # Generar problema de prueba con estructura interesante
    n_cities = 50
    cities = np.random.rand(n_cities, 2)
    
    # Añadir algunos clusters para hacer el problema más interesante
    cluster1 = np.random.randn(8, 2) * 0.08 + np.array([0.25, 0.75])
    cluster2 = np.random.randn(8, 2) * 0.08 + np.array([0.75, 0.25])
    cluster3 = np.random.randn(6, 2) * 0.06 + np.array([0.5, 0.5])
    cities = np.vstack([cities, cluster1, cluster2, cluster3])
    
    print(f"\nProblema TSP con {len(cities)} ciudades\n")
    
    fig, results = run_comparison_experiment(cities)
    
    plt.savefig('/home/claude/pimst_v3_results.png', dpi=300, bbox_inches='tight')
    print("\n✓ Resultados guardados en 'pimst_v3_results.png'")
    plt.close()
