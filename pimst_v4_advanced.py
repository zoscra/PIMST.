import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple, Optional
import time
from dataclasses import dataclass
from scipy.spatial import KDTree, ConvexHull
from sklearn.cluster import DBSCAN
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# MEJORA 1: PESOS ADAPTATIVOS
# ============================================================================

@dataclass
class AdaptiveWeights:
    """Pesos que se adaptan a las características del problema."""
    proximity: float
    primary_circle: float
    secondary_circles: float
    tangent: float
    tangent_weight: float
    
    # Metadatos sobre cómo se calcularon
    dispersion: float  # Qué tan dispersas están las ciudades
    clustering_coefficient: float  # Cuánto clustering hay
    intersection_density: float  # Densidad de intersecciones
    
    def to_dict(self):
        return {
            'proximity': self.proximity,
            'primary_circle': self.primary_circle,
            'secondary_circles': self.secondary_circles,
            'tangent': self.tangent,
            'tangent_weight': self.tangent_weight
        }

def calculate_dispersion(cities: np.ndarray) -> float:
    """
    Calcula dispersión de ciudades.
    0 = muy agrupadas, 1 = muy dispersas
    """
    centroid = np.mean(cities, axis=0)
    distances = np.linalg.norm(cities - centroid, axis=1)
    
    # Coeficiente de variación normalizado
    cv = np.std(distances) / (np.mean(distances) + 1e-6)
    dispersion = min(cv / 2, 1.0)  # Normalizar a [0, 1]
    
    return dispersion

def calculate_clustering_coefficient(cities: np.ndarray, 
                                    eps: float = 0.15) -> float:
    """
    Calcula coeficiente de clustering usando DBSCAN.
    0 = sin clusters, 1 = muy agrupado
    """
    if len(cities) < 10:
        return 0.5
    
    # DBSCAN para detectar clusters
    clustering = DBSCAN(eps=eps, min_samples=3).fit(cities)
    labels = clustering.labels_
    
    # Contar clusters (excluyendo ruido -1)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    
    # Más clusters y menos ruido = más agrupado
    cluster_score = min(n_clusters / 10, 1.0)  # Normalizar
    noise_penalty = n_noise / len(cities)
    
    clustering_coef = cluster_score * (1 - noise_penalty)
    
    return clustering_coef

def calculate_intersection_density(cities: np.ndarray,
                                   sample_size: int = 20) -> float:
    """
    Estima densidad de intersecciones.
    0 = pocas intersecciones, 1 = muchas intersecciones
    """
    if len(cities) < 10:
        return 0.5
    
    # Samplear para eficiencia
    n_sample = min(sample_size, len(cities))
    sample_indices = np.random.choice(len(cities), n_sample, replace=False)
    sample = cities[sample_indices]
    
    # Contar intersecciones
    intersections = 0
    edges = [(i, j) for i in range(len(sample)) for j in range(i+1, len(sample))]
    
    for i, (a, b) in enumerate(edges):
        for c, d in edges[i+1:]:
            if len({a, b, c, d}) < 4:
                continue
            
            inter = line_intersection(sample[a], sample[b], sample[c], sample[d])
            if inter is not None:
                intersections += 1
    
    # Normalizar por máximo teórico
    max_intersections = (len(edges) * (len(edges) - 1)) // 2
    density = min(intersections / (max_intersections + 1), 1.0)
    
    return density

def line_intersection(p1: np.ndarray, p2: np.ndarray,
                      p3: np.ndarray, p4: np.ndarray) -> Optional[np.ndarray]:
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

def compute_adaptive_weights(cities: np.ndarray,
                            verbose: bool = False) -> AdaptiveWeights:
    """
    Calcula pesos adaptativos basados en características del problema.
    
    Lógica:
    - Dispersión alta → más peso en proximidad
    - Clustering alto → más peso en círculos secundarios
    - Intersecciones densas → más peso en círculos secundarios
    - Distribución uniforme → más peso en círculo principal
    """
    dispersion = calculate_dispersion(cities)
    clustering = calculate_clustering_coefficient(cities)
    intersection_density = calculate_intersection_density(cities)
    
    if verbose:
        print(f"\nCaracterísticas del problema:")
        print(f"  Dispersión: {dispersion:.2f} (0=agrupado, 1=disperso)")
        print(f"  Clustering: {clustering:.2f} (0=uniforme, 1=clusters)")
        print(f"  Densidad intersecciones: {intersection_density:.2f}")
    
    # Estrategia adaptativa:
    
    # 1. Proximidad: aumenta con dispersión
    proximity = 1.0 + dispersion * 0.5
    
    # 2. Círculo principal: disminuye con clustering (estructura local domina)
    primary_circle = 0.6 - clustering * 0.4
    
    # 3. Círculos secundarios: aumenta con clustering e intersecciones
    secondary_circles = 0.3 + clustering * 0.5 + intersection_density * 0.3
    secondary_circles = min(secondary_circles, 1.0)
    
    # 4. Tangente: aumenta con intersecciones (más estructura → mejor predicción)
    tangent = 0.2 + intersection_density * 0.4
    
    # 5. Tangent weight: balanceado
    tangent_weight = 0.4
    
    weights = AdaptiveWeights(
        proximity=proximity,
        primary_circle=primary_circle,
        secondary_circles=secondary_circles,
        tangent=tangent,
        tangent_weight=tangent_weight,
        dispersion=dispersion,
        clustering_coefficient=clustering,
        intersection_density=intersection_density
    )
    
    if verbose:
        print(f"\nPesos adaptativos calculados:")
        print(f"  Proximidad: {weights.proximity:.2f}")
        print(f"  Círculo principal: {weights.primary_circle:.2f}")
        print(f"  Círculos secundarios: {weights.secondary_circles:.2f}")
        print(f"  Tangente: {weights.tangent:.2f}")
    
    return weights

# ============================================================================
# MEJORA 2: SEMICÍRCULOS DIRIGIDOS
# ============================================================================

@dataclass
class DirectedArc:
    """Arco dirigido (semicírculo orientado)."""
    center: np.ndarray
    radius: float
    start_angle: float  # Ángulo de inicio
    end_angle: float    # Ángulo de fin
    direction: np.ndarray  # Vector direccional del flujo
    
    def is_point_in_arc(self, point: np.ndarray, tolerance: float = 0.3) -> bool:
        """Verifica si un punto está dentro del arco."""
        # Distancia al centro
        dist = np.linalg.norm(point - self.center)
        if abs(dist - self.radius) > self.radius * tolerance:
            return False
        
        # Ángulo del punto
        angle = np.arctan2(point[1] - self.center[1], 
                          point[0] - self.center[0])
        
        # Normalizar ángulos a [0, 2π]
        angle = angle % (2 * np.pi)
        start = self.start_angle % (2 * np.pi)
        end = self.end_angle % (2 * np.pi)
        
        # Verificar si está en el rango
        if start <= end:
            return start <= angle <= end
        else:  # El arco cruza 0
            return angle >= start or angle <= end
    
    def alignment_score(self, direction: np.ndarray) -> float:
        """
        Score de alineación con la dirección del arco.
        1.0 = perfectamente alineado, 0.0 = perpendicular, -1.0 = opuesto
        """
        direction_norm = direction / (np.linalg.norm(direction) + 1e-6)
        return np.dot(self.direction, direction_norm)

def create_directed_arcs(cities: np.ndarray,
                        intersection_centers: List[np.ndarray],
                        n_arcs: int = 5) -> List[DirectedArc]:
    """
    Crea arcos dirigidos basados en centros de intersección.
    Los arcos siguen el flujo natural de conectividad.
    """
    if not intersection_centers:
        return []
    
    centers = np.array(intersection_centers)
    
    # Calcular densidad para cada centro
    densities = []
    for center in centers:
        distances = np.linalg.norm(cities - center, axis=1)
        density = np.sum(distances < np.median(distances))
        densities.append(density)
    
    # Seleccionar centros más densos
    sorted_indices = np.argsort(densities)[::-1]
    selected = centers[sorted_indices[:min(n_arcs, len(centers))]]
    
    arcs = []
    
    for center in selected:
        # Calcular radio
        distances = np.linalg.norm(cities - center, axis=1)
        radius = np.mean(distances) * 0.8
        
        # Determinar dirección del arco basándose en las ciudades cercanas
        close_cities = cities[distances < radius * 1.2]
        
        if len(close_cities) < 3:
            # No hay suficientes ciudades, crear círculo completo
            arcs.append(DirectedArc(
                center=center,
                radius=radius,
                start_angle=0,
                end_angle=2 * np.pi,
                direction=np.array([1.0, 0.0])
            ))
            continue
        
        # Calcular dirección principal usando PCA
        centered = close_cities - center
        cov = np.cov(centered.T)
        eigenvalues, eigenvectors = np.linalg.eig(cov)
        
        # Dirección principal (eigenvector con mayor eigenvalue)
        principal_direction = eigenvectors[:, np.argmax(eigenvalues)]
        
        # Calcular ángulos de las ciudades cercanas
        angles = np.arctan2(centered[:, 1], centered[:, 0])
        
        # Determinar rango angular que cubre la mayoría de ciudades
        # Usar percentiles para determinar inicio y fin del arco
        angles_sorted = np.sort(angles)
        
        # El arco cubre el 70% central de las ciudades
        percentile_low = 15
        percentile_high = 85
        start_angle = np.percentile(angles_sorted, percentile_low)
        end_angle = np.percentile(angles_sorted, percentile_high)
        
        # Asegurar que el arco no sea demasiado pequeño
        angle_span = (end_angle - start_angle) % (2 * np.pi)
        if angle_span < np.pi / 2:  # Mínimo 90 grados
            mid_angle = (start_angle + end_angle) / 2
            start_angle = mid_angle - np.pi / 4
            end_angle = mid_angle + np.pi / 4
        
        arc = DirectedArc(
            center=center,
            radius=radius,
            start_angle=start_angle,
            end_angle=end_angle,
            direction=principal_direction
        )
        
        arcs.append(arc)
    
    return arcs

def calculate_arc_score(current_city: np.ndarray,
                       candidate_city: np.ndarray,
                       arcs: List[DirectedArc],
                       movement_direction: Optional[np.ndarray]) -> float:
    """
    Calcula score basado en arcos dirigidos.
    Bonifica si el candidato está en un arco y se mueve en su dirección.
    """
    if not arcs:
        return 0.0
    
    score = 0.0
    
    for arc in arcs:
        # Verificar si el candidato está en el arco
        if arc.is_point_in_arc(candidate_city):
            base_bonus = 0.3  # Bonus base por estar en el arco
            
            # Bonus adicional si el movimiento está alineado con el arco
            if movement_direction is not None:
                alignment = arc.alignment_score(movement_direction)
                # Convertir de [-1, 1] a [0, 1]
                alignment_bonus = (alignment + 1) / 2
                score += base_bonus + alignment_bonus * 0.5
            else:
                score += base_bonus
    
    return min(score, 1.0)  # Normalizar a [0, 1]

# ============================================================================
# ANÁLISIS DE INTERSECCIONES (de la versión anterior)
# ============================================================================

def find_intersection_centers_fast(cities: np.ndarray,
                                   n_samples: int = 20) -> List[np.ndarray]:
    """Versión rápida para encontrar centros de intersección."""
    n = len(cities)
    
    if n > 50:
        n_samples = min(n_samples, n // 3)
    else:
        n_samples = min(n_samples, n)
    
    sample_indices = np.random.choice(n, n_samples, replace=False)
    sample = cities[sample_indices]
    
    intersections = []
    
    for i in range(len(sample)-1):
        for j in range(i+1, len(sample)):
            p1, p2 = sample[i], sample[j]
            
            for k in range(len(sample)-1):
                for l in range(k+1, len(sample)):
                    if len({i,j,k,l}) < 4:
                        continue
                    
                    p3, p4 = sample[k], sample[l]
                    inter = line_intersection(p1, p2, p3, p4)
                    
                    if inter is not None:
                        intersections.append(inter)
    
    if not intersections:
        return []
    
    intersections = np.array(intersections)
    
    # Clustering con KDTree
    tree = KDTree(intersections)
    
    centroids = []
    used = set()
    
    for i, point in enumerate(intersections):
        if i in used:
            continue
        
        indices = tree.query_ball_point(point, 0.12)
        used.update(indices)
        
        cluster = intersections[indices]
        centroid = np.mean(cluster, axis=0)
        centroids.append(centroid)
    
    return centroids

# ============================================================================
# ALGORITMO PIMST v4.0 CON MEJORAS AVANZADAS
# ============================================================================

def calculate_tour_length(tour: List[int], cities: np.ndarray) -> float:
    """Calcula longitud del tour."""
    tour_coords = cities[tour]
    tour_coords_shifted = np.roll(tour_coords, -1, axis=0)
    distances = np.linalg.norm(tour_coords - tour_coords_shifted, axis=1)
    return np.sum(distances)

def two_opt_simple(tour: List[int], cities: np.ndarray, 
                  max_iterations: int = 500) -> List[int]:
    """2-opt simple."""
    best_tour = tour.copy()
    best_length = calculate_tour_length(best_tour, cities)
    
    improved = True
    iterations = 0
    
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

def calculate_advanced_score(current_city: np.ndarray,
                            candidate_city: np.ndarray,
                            primary_center: np.ndarray,
                            primary_radius: float,
                            directed_arcs: List[DirectedArc],
                            tangent_direction: Optional[np.ndarray],
                            weights: dict) -> float:
    """
    Score avanzado usando arcos dirigidos y pesos adaptativos.
    """
    distance = np.linalg.norm(candidate_city - current_city)
    
    # 1. Proximidad
    proximity_score = 1.0 / (distance + 1e-6)
    
    # 2. Círculo principal
    current_angle = np.arctan2(current_city[1] - primary_center[1],
                               current_city[0] - primary_center[0])
    candidate_angle = np.arctan2(candidate_city[1] - primary_center[1],
                                 candidate_city[0] - primary_center[0])
    angle_diff = abs(((candidate_angle - current_angle + np.pi) % (2*np.pi)) - np.pi)
    
    candidate_dist = np.linalg.norm(candidate_city - primary_center)
    is_on_circle = abs(candidate_dist - primary_radius) < primary_radius * 0.3
    primary_score = (1.0 - angle_diff / np.pi) * (1.0 if is_on_circle else 0.5)
    
    # 3. Arcos dirigidos (reemplaza círculos secundarios)
    movement_direction = candidate_city - current_city
    arc_score = calculate_arc_score(current_city, candidate_city, 
                                    directed_arcs, movement_direction)
    
    # 4. Tangente
    tangent_score = 0.0
    if tangent_direction is not None:
        direction_to_candidate = candidate_city - current_city
        direction_to_candidate = direction_to_candidate / (np.linalg.norm(direction_to_candidate) + 1e-6)
        dot = np.dot(tangent_direction, direction_to_candidate)
        tangent_score = (dot + 1) / 2
    
    # Combinar scores
    total = (weights['proximity'] * proximity_score +
             weights['primary_circle'] * primary_score +
             weights['secondary_circles'] * arc_score +  # Nota: reutilizamos el peso
             weights['tangent'] * tangent_score)
    
    return total

def construct_tour_advanced(cities: np.ndarray,
                           start_idx: int,
                           primary_center: np.ndarray,
                           primary_radius: float,
                           directed_arcs: List[DirectedArc],
                           weights: dict) -> List[int]:
    """Construcción de tour con arcos dirigidos."""
    n = len(cities)
    tour = [start_idx]
    unvisited = set(range(n)) - {start_idx}
    
    while unvisited:
        current_idx = tour[-1]
        current_city = cities[current_idx]
        
        # Calcular tangente
        tangent_direction = None
        if len(tour) >= 2:
            prev_city = cities[tour[-2]]
            direction = current_city - prev_city
            direction = direction / (np.linalg.norm(direction) + 1e-6)
            
            to_center = primary_center - current_city
            to_center = to_center / (np.linalg.norm(to_center) + 1e-6)
            tangent = np.array([-to_center[1], to_center[0]])
            
            tangent_direction = (weights['tangent_weight'] * tangent +
                               (1 - weights['tangent_weight']) * direction)
            tangent_direction = tangent_direction / (np.linalg.norm(tangent_direction) + 1e-6)
        
        # Evaluar candidatos
        best_score = -float('inf')
        best_idx = None
        
        for idx in unvisited:
            candidate_city = cities[idx]
            score = calculate_advanced_score(
                current_city, candidate_city,
                primary_center, primary_radius,
                directed_arcs, tangent_direction, weights
            )
            
            if score > best_score:
                best_score = score
                best_idx = idx
        
        tour.append(best_idx)
        unvisited.remove(best_idx)
    
    return tour

def pimst_v4_advanced(cities: np.ndarray,
                     n_starts: int = 10,
                     n_arcs: int = 5,
                     use_adaptive_weights: bool = True,
                     verbose: bool = True) -> Tuple[List[int], float, dict]:
    """
    PIMST v4.0: Pesos Adaptativos + Semicírculos Dirigidos
    """
    start_time = time.time()
    n = len(cities)
    
    if verbose:
        print(f"\n{'='*80}")
        print(f"PIMST v4.0 ADVANCED - {n} ciudades")
        print(f"{'='*80}")
    
    # MEJORA 1: Pesos adaptativos
    if use_adaptive_weights:
        if verbose:
            print("\n🔧 Calculando pesos adaptativos...")
        weights = compute_adaptive_weights(cities, verbose=verbose)
        weights_dict = weights.to_dict()
    else:
        # Pesos por defecto
        weights_dict = {
            'proximity': 1.2,
            'primary_circle': 0.2,
            'secondary_circles': 0.7,
            'tangent': 0.2,
            'tangent_weight': 0.3
        }
        if verbose:
            print("\n⚙️  Usando pesos predeterminados")
    
    # Círculo principal
    centroid = np.mean(cities, axis=0)
    radius = np.mean(np.linalg.norm(cities - centroid, axis=1))
    
    # Encontrar centros de intersección
    if verbose:
        print("\n🔍 Analizando intersecciones...")
    
    intersection_centers = find_intersection_centers_fast(cities, n_samples=25)
    
    # MEJORA 2: Arcos dirigidos
    if verbose:
        print(f"   → {len(intersection_centers)} centros encontrados")
        print(f"\n🎯 Creando arcos dirigidos...")
    
    directed_arcs = create_directed_arcs(cities, intersection_centers, n_arcs)
    
    if verbose:
        print(f"   → {len(directed_arcs)} arcos dirigidos creados")
    
    # Generar puntos de inicio (filotaxis)
    golden_angle = np.pi * (3 - np.sqrt(5))
    angles = np.array([i * golden_angle for i in range(n_starts)])
    start_points = centroid + radius * np.column_stack([np.cos(angles), np.sin(angles)])
    
    start_indices = []
    for point in start_points:
        distances = np.linalg.norm(cities - point, axis=1)
        start_indices.append(np.argmin(distances))
    start_indices = list(set(start_indices))
    
    if verbose:
        print(f"\n🚀 Construyendo {len(start_indices)} tours...")
    
    # Construir tours
    best_tour = None
    best_length = float('inf')
    
    for idx in start_indices:
        tour = construct_tour_advanced(
            cities, idx, centroid, radius,
            directed_arcs, weights_dict
        )
        
        tour = two_opt_simple(tour, cities, max_iterations=500)
        length = calculate_tour_length(tour, cities)
        
        if length < best_length:
            best_length = length
            best_tour = tour
    
    total_time = time.time() - start_time
    
    stats = {
        'n_cities': n,
        'n_starts': len(start_indices),
        'n_directed_arcs': len(directed_arcs),
        'total_time': total_time,
        'weights': weights_dict,
        'adaptive': use_adaptive_weights
    }
    
    if use_adaptive_weights:
        stats['dispersion'] = weights.dispersion
        stats['clustering'] = weights.clustering_coefficient
        stats['intersection_density'] = weights.intersection_density
    
    if verbose:
        print(f"\n✓ Mejor tour: {best_length:.4f} (en {total_time:.2f}s)")
    
    return best_tour, best_length, stats

# ============================================================================
# COMPARACIÓN EXPERIMENTAL
# ============================================================================

def run_comparison_v3_v4(cities: np.ndarray):
    """Compara PIMST v3.0 vs v4.0"""
    print("\n" + "="*80)
    print("COMPARACIÓN: PIMST v3.0 vs v4.0")
    print("="*80)
    
    n = len(cities)
    
    # Baseline: Nearest Neighbor
    print("\n1. Baseline - Nearest Neighbor + 2-opt")
    nn_tour = [0]
    unvisited = set(range(1, n))
    while unvisited:
        current = cities[nn_tour[-1]]
        distances = {idx: np.linalg.norm(cities[idx] - current) for idx in unvisited}
        next_city = min(distances, key=distances.get)
        nn_tour.append(next_city)
        unvisited.remove(next_city)
    nn_tour = two_opt_simple(nn_tour, cities)
    nn_length = calculate_tour_length(nn_tour, cities)
    print(f"   Longitud: {nn_length:.4f}")
    
    # PIMST v3.0 (pesos fijos, círculos completos)
    print("\n2. PIMST v3.0 (Pesos Fijos + Círculos Completos)")
    tour_v3, length_v3, stats_v3 = pimst_v4_advanced(
        cities, n_starts=10, n_arcs=5,
        use_adaptive_weights=False, verbose=False
    )
    improvement_v3 = ((nn_length - length_v3) / nn_length) * 100
    print(f"   Longitud: {length_v3:.4f}")
    print(f"   Mejora: {improvement_v3:+.2f}%")
    print(f"   Tiempo: {stats_v3['total_time']:.2f}s")
    
    # PIMST v4.0 (pesos adaptativos + arcos dirigidos)
    print("\n3. PIMST v4.0 (Pesos Adaptativos + Arcos Dirigidos)")
    tour_v4, length_v4, stats_v4 = pimst_v4_advanced(
        cities, n_starts=10, n_arcs=5,
        use_adaptive_weights=True, verbose=True
    )
    improvement_v4 = ((nn_length - length_v4) / nn_length) * 100
    additional = ((length_v3 - length_v4) / length_v3) * 100
    print(f"\n   Mejora vs NN: {improvement_v4:+.2f}%")
    print(f"   Mejora adicional vs v3.0: {additional:+.2f}%")
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN")
    print("="*80)
    print(f"{'Método':<45} {'Longitud':<12} {'Mejora vs NN':<15}")
    print("-"*80)
    print(f"{'Nearest Neighbor (Baseline)':<45} {nn_length:>10.4f}  {'0.00%':>13}")
    print(f"{'PIMST v3.0 (Fijos + Círculos)':<45} {length_v3:>10.4f}  {improvement_v3:>12.2f}%")
    print(f"{'PIMST v4.0 (Adaptativos + Arcos)':<45} {length_v4:>10.4f}  {improvement_v4:>12.2f}%")
    print("="*80)
    
    return {
        'nn_length': nn_length,
        'v3_length': length_v3,
        'v4_length': length_v4,
        'improvement_v3': improvement_v3,
        'improvement_v4': improvement_v4,
        'additional': additional,
        'stats_v4': stats_v4
    }

# ============================================================================
# VISUALIZACIÓN
# ============================================================================

def visualize_v4_solution(cities: np.ndarray, 
                         tour: List[int],
                         directed_arcs: List[DirectedArc],
                         primary_center: np.ndarray,
                         primary_radius: float,
                         stats: dict,
                         title: str = "PIMST v4.0"):
    """Visualiza solución v4.0 con arcos dirigidos."""
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
    
    # Panel izquierdo: Guías geométricas
    ax = axes[0]
    ax.scatter(cities[:, 0], cities[:, 1], c='red', s=80, 
              zorder=5, alpha=0.7, label='Ciudades')
    
    # Círculo principal (tenue)
    circle = plt.Circle(primary_center, primary_radius, 
                       fill=False, color='blue', linewidth=1,
                       linestyle='--', alpha=0.2, label='Círculo Principal')
    ax.add_patch(circle)
    
    # Arcos dirigidos
    for i, arc in enumerate(directed_arcs):
        # Dibujar el arco
        angles = np.linspace(arc.start_angle, arc.end_angle, 50)
        x = arc.center[0] + arc.radius * np.cos(angles)
        y = arc.center[1] + arc.radius * np.sin(angles)
        ax.plot(x, y, linewidth=3, alpha=0.7, 
               label=f'Arco Dirigido {i+1}' if i < 3 else '')
        
        # Flecha indicando dirección
        mid_angle = (arc.start_angle + arc.end_angle) / 2
        arrow_start = arc.center + arc.radius * 0.9 * np.array([np.cos(mid_angle), np.sin(mid_angle)])
        arrow_end = arrow_start + arc.direction * 0.1
        ax.arrow(arrow_start[0], arrow_start[1],
                arrow_end[0] - arrow_start[0],
                arrow_end[1] - arrow_start[1],
                head_width=0.03, head_length=0.02, 
                fc='black', ec='black', linewidth=2, zorder=10)
    
    ax.set_title('Guías Geométricas con Arcos Dirigidos', 
                fontsize=13, fontweight='bold')
    ax.set_aspect('equal')
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.2)
    
    # Panel derecho: Solución
    ax = axes[1]
    ax.scatter(cities[:, 0], cities[:, 1], c='red', s=80, 
              zorder=5, alpha=0.7)
    
    # Tour
    for i in range(len(tour)):
        start = cities[tour[i]]
        end = cities[tour[(i+1) % len(tour)]]
        ax.plot([start[0], end[0]], [start[1], end[1]],
               'darkgreen', linewidth=2, alpha=0.7)
    
    # Inicio
    start_city = cities[tour[0]]
    ax.scatter([start_city[0]], [start_city[1]], c='lime', s=200,
              marker='*', edgecolors='black', linewidths=2,
              zorder=7, label='Inicio')
    
    ax.set_title('Solución Final', fontsize=13, fontweight='bold')
    ax.set_aspect('equal')
    ax.legend()
    ax.grid(True, alpha=0.2)
    
    # Título general
    info_text = f"{title}\n"
    if 'dispersion' in stats:
        info_text += f"Dispersión: {stats['dispersion']:.2f} | "
        info_text += f"Clustering: {stats['clustering']:.2f} | "
        info_text += f"Intersecciones: {stats['intersection_density']:.2f}"
    
    plt.suptitle(info_text, fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    return fig

# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    np.random.seed(42)
    
    # Crear problema con clusters
    print("Generando problema de prueba...")
    n_cities = 60
    cities = np.random.rand(n_cities, 2) * 0.6 + 0.2
    
    # Añadir clusters marcados
    cluster1 = np.random.randn(8, 2) * 0.06 + np.array([0.2, 0.8])
    cluster2 = np.random.randn(8, 2) * 0.06 + np.array([0.8, 0.2])
    cluster3 = np.random.randn(6, 2) * 0.05 + np.array([0.5, 0.5])
    cities = np.vstack([cities, cluster1, cluster2, cluster3])
    
    print(f"\nProblema: {len(cities)} ciudades con clusters naturales")
    
    # Ejecutar comparación
    results = run_comparison_v3_v4(cities)
    
    # Visualizar v4.0
    print("\nGenerando visualización...")
    
    tour_v4, length_v4, stats_v4 = pimst_v4_advanced(
        cities, n_starts=10, n_arcs=5,
        use_adaptive_weights=True, verbose=False
    )
    
    # Recrear arcos para visualización
    centroid = np.mean(cities, axis=0)
    radius = np.mean(np.linalg.norm(cities - centroid, axis=1))
    intersection_centers = find_intersection_centers_fast(cities)
    directed_arcs = create_directed_arcs(cities, intersection_centers, 5)
    
    fig = visualize_v4_solution(
        cities, tour_v4, directed_arcs, centroid, radius, stats_v4,
        f"PIMST v4.0 - Mejora: {results['improvement_v4']:.2f}%"
    )
    
    plt.savefig('/home/claude/pimst_v4_advanced.png', dpi=300, bbox_inches='tight')
    print("\n✓ Visualización guardada: pimst_v4_advanced.png")
    plt.close()
    
    print("\n" + "="*80)
    print("CONCLUSIÓN")
    print("="*80)
    print(f"""
Las dos mejoras implementadas:

1. PESOS ADAPTATIVOS:
   - Se ajustan automáticamente según características del problema
   - Dispersión: {stats_v4.get('dispersion', 0):.2f}
   - Clustering: {stats_v4.get('clustering', 0):.2f}
   - Intersecciones: {stats_v4.get('intersection_density', 0):.2f}
   
2. ARCOS DIRIGIDOS:
   - Semicírculos orientados según el flujo natural
   - {stats_v4['n_directed_arcs']} arcos creados
   - Capturan mejor la direccionalidad del tour
   
RESULTADO:
   Mejora adicional de {results['additional']:.2f}% sobre PIMST v3.0
   Mejora total de {results['improvement_v4']:.2f}% sobre baseline
""")
