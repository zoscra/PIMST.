"""
PIMST v14.1: Convex Hull Progressive + 2-opt Optimization
==========================================================

Mejora v14.0 añadiendo optimización 2-opt como post-procesamiento.

Filosofía:
1. Construcción inicial con Convex Hull Progressive (v14.0)
2. Mejora local con 2-opt para eliminar cruces
3. Resultado: Mayor calidad manteniendo velocidad razonable
"""

import numpy as np
from scipy.spatial import ConvexHull, distance_matrix
from sklearn.cluster import DBSCAN
import matplotlib.pyplot as plt
from typing import List, Tuple
import time


class PIMST_v14_1:
    """PIMST v14.1: Convex Hull Progressive + 2-opt"""
    
    def __init__(self, hot_spot_weight=0.4, phi=1.618):
        self.hot_spot_weight = hot_spot_weight
        self.phi = phi
        self.distance_weight = 1.0 - hot_spot_weight
        
    def solve(self, cities: np.ndarray, apply_2opt=True, max_iterations=1000) -> Tuple[List[int], float]:
        """
        Resuelve TSP usando Convex Hull Progressive + 2-opt opcional
        
        Args:
            cities: Array (n, 2) con coordenadas
            apply_2opt: Si True, aplica optimización 2-opt
            max_iterations: Máximo de iteraciones para 2-opt
            
        Returns:
            (tour, distance)
        """
        start_time = time.time()
        
        # PASO 1: Construcción inicial con Convex Hull Progressive
        tour = self._convex_hull_progressive(cities)
        
        construction_time = time.time() - start_time
        
        # PASO 2: Optimización 2-opt (opcional)
        if apply_2opt:
            tour, improvements = self._two_opt(cities, tour, max_iterations)
            opt_time = time.time() - start_time - construction_time
            print(f"  2-opt: {improvements} mejoras en {opt_time:.3f}s")
        
        # Calcular distancia final
        distance = self._calculate_tour_distance(cities, tour)
        
        total_time = time.time() - start_time
        print(f"  Tiempo total: {total_time:.3f}s")
        
        return tour, distance
    
    def _convex_hull_progressive(self, cities: np.ndarray) -> List[int]:
        """Construcción inicial: Convex Hull Progressive (v14.0)"""
        n = len(cities)
        
        if n < 4:
            return list(range(n))
        
        # Hot spots usando DBSCAN
        hot_spots = self._calculate_hot_spots_dbscan(cities)
        
        # Convex Hull inicial (los "clavos externos")
        hull = ConvexHull(cities)
        tour = list(hull.vertices)
        remaining = set(range(n)) - set(tour)
        
        # Inserción progresiva hacia el interior
        while remaining:
            best_city = None
            best_position = None
            best_score = float('inf')
            
            for city in remaining:
                for i in range(len(tour)):
                    score = self._insertion_score(cities, hot_spots, tour, city, i)
                    if score < best_score:
                        best_score = score
                        best_city = city
                        best_position = i
            
            tour.insert(best_position + 1, best_city)
            remaining.remove(best_city)
        
        return tour
    
    def _calculate_hot_spots_dbscan(self, cities: np.ndarray) -> np.ndarray:
        """Calcula hot spots usando DBSCAN clustering"""
        if len(cities) < 10:
            return np.mean(cities, axis=0, keepdims=True)
        
        # DBSCAN para encontrar clusters
        eps = np.percentile(distance_matrix(cities, cities), 15)
        dbscan = DBSCAN(eps=eps, min_samples=max(2, len(cities) // 20))
        labels = dbscan.fit_predict(cities)
        
        # Hot spots = centroides de clusters
        unique_labels = set(labels) - {-1}
        if not unique_labels:
            return np.mean(cities, axis=0, keepdims=True)
        
        hot_spots = []
        for label in unique_labels:
            cluster_cities = cities[labels == label]
            hot_spots.append(np.mean(cluster_cities, axis=0))
        
        return np.array(hot_spots)
    
    def _insertion_score(self, cities: np.ndarray, hot_spots: np.ndarray, 
                        tour: List[int], city: int, position: int) -> float:
        """Calcula score de insertar city en position del tour"""
        city_coord = cities[city]
        prev_coord = cities[tour[position]]
        next_coord = cities[tour[(position + 1) % len(tour)]]
        
        # Costo de distancia
        dist_removed = np.linalg.norm(prev_coord - next_coord)
        dist_added = (np.linalg.norm(prev_coord - city_coord) + 
                     np.linalg.norm(city_coord - next_coord))
        distance_cost = dist_added - dist_removed
        
        # Costo de hot spots (distancia a hot spot más cercano)
        distances_to_hotspots = [np.linalg.norm(city_coord - hs) for hs in hot_spots]
        hotspot_cost = min(distances_to_hotspots)
        
        # Score combinado
        score = (self.distance_weight * distance_cost + 
                self.hot_spot_weight * hotspot_cost)
        
        return score
    
    def _two_opt(self, cities: np.ndarray, tour: List[int], max_iterations: int) -> Tuple[List[int], int]:
        """
        Optimización 2-opt: Elimina cruces intercambiando aristas
        
        Concepto:
        - Toma dos aristas: (i, i+1) y (j, j+1)
        - Las elimina y reconecta: (i, j) y (i+1, j+1)
        - Si mejora la distancia, acepta el cambio
        """
        tour = tour.copy()
        n = len(tour)
        improvements = 0
        improved = True
        iterations = 0
        
        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            
            for i in range(n - 1):
                for j in range(i + 2, n):
                    # Evitar adyacentes
                    if j == i + 1 or (i == 0 and j == n - 1):
                        continue
                    
                    # Calcular mejora de intercambiar (i, i+1) con (j, j+1)
                    improvement = self._two_opt_improvement(cities, tour, i, j)
                    
                    if improvement > 1e-9:  # Mejora significativa
                        # Aplicar 2-opt swap
                        tour[i+1:j+1] = reversed(tour[i+1:j+1])
                        improvements += 1
                        improved = True
                        break
                
                if improved:
                    break
        
        return tour, improvements
    
    def _two_opt_improvement(self, cities: np.ndarray, tour: List[int], i: int, j: int) -> float:
        """Calcula la mejora de hacer un 2-opt swap entre posiciones i y j"""
        n = len(tour)
        
        # Aristas actuales
        a, b = tour[i], tour[i + 1]
        c, d = tour[j], tour[(j + 1) % n]
        
        # Distancia actual
        current_dist = (np.linalg.norm(cities[a] - cities[b]) + 
                       np.linalg.norm(cities[c] - cities[d]))
        
        # Distancia después del swap
        new_dist = (np.linalg.norm(cities[a] - cities[c]) + 
                   np.linalg.norm(cities[b] - cities[d]))
        
        # Mejora (positiva si reduce distancia)
        return current_dist - new_dist
    
    def _calculate_tour_distance(self, cities: np.ndarray, tour: List[int]) -> float:
        """Calcula la distancia total del tour"""
        distance = 0
        for i in range(len(tour)):
            city1 = cities[tour[i]]
            city2 = cities[tour[(i + 1) % len(tour)]]
            distance += np.linalg.norm(city1 - city2)
        return distance


def nearest_neighbor(cities: np.ndarray, start: int = 0) -> Tuple[List[int], float]:
    """Algoritmo Nearest Neighbor baseline"""
    n = len(cities)
    unvisited = set(range(n))
    tour = [start]
    unvisited.remove(start)
    
    current = start
    while unvisited:
        nearest = min(unvisited, 
                     key=lambda city: np.linalg.norm(cities[current] - cities[city]))
        tour.append(nearest)
        unvisited.remove(nearest)
        current = nearest
    
    # Calcular distancia
    distance = sum(np.linalg.norm(cities[tour[i]] - cities[tour[(i+1) % n]]) 
                   for i in range(n))
    
    return tour, distance


def generate_test_dataset(dataset_type: str, n_cities: int, seed: int = 42) -> np.ndarray:
    """Genera datasets de prueba"""
    np.random.seed(seed)
    
    if dataset_type == "uniform":
        return np.random.rand(n_cities, 2) * 100
    
    elif dataset_type == "clusters":
        cities = []
        n_clusters = 4
        cities_per_cluster = n_cities // n_clusters
        
        for i in range(n_clusters):
            center_x = np.random.rand() * 80 + 10
            center_y = np.random.rand() * 80 + 10
            cluster = np.random.randn(cities_per_cluster, 2) * 5 + [center_x, center_y]
            cities.append(cluster)
        
        return np.vstack(cities)
    
    elif dataset_type == "peripheral":
        # Anillo exterior
        angles = np.linspace(0, 2*np.pi, n_cities//2, endpoint=False)
        outer = np.column_stack([50 + 40*np.cos(angles), 50 + 40*np.sin(angles)])
        
        # Centro disperso
        inner = np.random.rand(n_cities - n_cities//2, 2) * 30 + 35
        
        return np.vstack([outer, inner])
    
    else:
        raise ValueError(f"Unknown dataset type: {dataset_type}")


def visualize_comparison(cities: np.ndarray, tour_v14_0: List[int], tour_v14_1: List[int],
                        dist_v14_0: float, dist_v14_1: float, title: str):
    """Visualiza comparación entre v14.0 y v14.1"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # v14.0 (sin 2-opt)
    ax = axes[0]
    tour_coords = cities[tour_v14_0 + [tour_v14_0[0]]]
    ax.plot(tour_coords[:, 0], tour_coords[:, 1], 'b-', alpha=0.6, linewidth=1.5)
    ax.scatter(cities[:, 0], cities[:, 1], c='red', s=50, zorder=5)
    ax.set_title(f'v14.0 (sin 2-opt)\nDistancia: {dist_v14_0:.2f}', fontsize=12, fontweight='bold')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    
    # v14.1 (con 2-opt)
    ax = axes[1]
    tour_coords = cities[tour_v14_1 + [tour_v14_1[0]]]
    ax.plot(tour_coords[:, 0], tour_coords[:, 1], 'g-', alpha=0.6, linewidth=1.5)
    ax.scatter(cities[:, 0], cities[:, 1], c='red', s=50, zorder=5)
    improvement = ((dist_v14_0 - dist_v14_1) / dist_v14_0) * 100
    ax.set_title(f'v14.1 (con 2-opt)\nDistancia: {dist_v14_1:.2f}\nMejora: {improvement:.2f}%', 
                fontsize=12, fontweight='bold')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    
    plt.suptitle(title, fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(f'/home/claude/{title.replace(" ", "_").lower()}.png', 
                dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Visualización guardada: {title.replace(' ', '_').lower()}.png")


def run_benchmark():
    """Ejecuta benchmark completo: v14.0 vs v14.1 vs NN"""
    print("="*80)
    print("BENCHMARK: PIMST v14.0 vs v14.1 (con 2-opt) vs Nearest Neighbor")
    print("="*80)
    
    datasets = [
        ("uniform", 50, "Uniforme 50 ciudades"),
        ("clusters", 48, "Clusters 4×12"),
        ("peripheral", 50, "Periférico (anillo + centro)")
    ]
    
    results = []
    
    for dataset_type, n_cities, dataset_name in datasets:
        print(f"\n{'='*80}")
        print(f"Dataset: {dataset_name}")
        print(f"{'='*80}")
        
        cities = generate_test_dataset(dataset_type, n_cities)
        
        # Nearest Neighbor
        print("Ejecutando NN...")
        tour_nn, dist_nn = nearest_neighbor(cities)
        print(f"  NN: {dist_nn:.4f}")
        
        # v14.0 (sin 2-opt)
        print("Ejecutando v14.0 (sin 2-opt)...")
        solver_v14_0 = PIMST_v14_1()
        tour_v14_0, dist_v14_0 = solver_v14_0.solve(cities, apply_2opt=False)
        
        # v14.1 (con 2-opt)
        print("Ejecutando v14.1 (con 2-opt)...")
        solver_v14_1 = PIMST_v14_1()
        tour_v14_1, dist_v14_1 = solver_v14_1.solve(cities, apply_2opt=True, max_iterations=500)
        
        # Calcular mejoras
        improvement_v14_0_vs_nn = ((dist_nn - dist_v14_0) / dist_nn) * 100
        improvement_v14_1_vs_nn = ((dist_nn - dist_v14_1) / dist_nn) * 100
        improvement_v14_1_vs_v14_0 = ((dist_v14_0 - dist_v14_1) / dist_v14_0) * 100
        
        print(f"\n  Resultados:")
        print(f"    NN:    {dist_nn:.4f} (baseline)")
        print(f"    v14.0: {dist_v14_0:.4f} ({improvement_v14_0_vs_nn:+.2f}% vs NN)")
        print(f"    v14.1: {dist_v14_1:.4f} ({improvement_v14_1_vs_nn:+.2f}% vs NN)")
        print(f"    Mejora 2-opt: {improvement_v14_1_vs_v14_0:.2f}%")
        
        results.append({
            'dataset': dataset_name,
            'nn': dist_nn,
            'v14_0': dist_v14_0,
            'v14_1': dist_v14_1,
            'improvement_v14_0': improvement_v14_0_vs_nn,
            'improvement_v14_1': improvement_v14_1_vs_nn,
            'improvement_2opt': improvement_v14_1_vs_v14_0
        })
        
        # Visualización
        visualize_comparison(cities, tour_v14_0, tour_v14_1, dist_v14_0, dist_v14_1, dataset_name)
    
    # Resumen final
    print("\n" + "="*80)
    print("RESUMEN FINAL")
    print("="*80)
    print(f"{'Dataset':<30} {'v14.0 vs NN':>15} {'v14.1 vs NN':>15} {'Mejora 2-opt':>15}")
    print("-"*80)
    
    for r in results:
        print(f"{r['dataset']:<30} {r['improvement_v14_0']:>14.2f}% {r['improvement_v14_1']:>14.2f}% "
              f"{r['improvement_2opt']:>14.2f}%")
    
    print("-"*80)
    avg_v14_0 = np.mean([r['improvement_v14_0'] for r in results])
    avg_v14_1 = np.mean([r['improvement_v14_1'] for r in results])
    avg_2opt = np.mean([r['improvement_2opt'] for r in results])
    
    print(f"{'PROMEDIO':<30} {avg_v14_0:>14.2f}% {avg_v14_1:>14.2f}% {avg_2opt:>14.2f}%")
    print("="*80)
    
    # Gráfica comparativa
    create_summary_chart(results)
    
    return results


def create_summary_chart(results):
    """Crea gráfica resumen de resultados"""
    datasets = [r['dataset'] for r in results]
    v14_0_improvements = [r['improvement_v14_0'] for r in results]
    v14_1_improvements = [r['improvement_v14_1'] for r in results]
    
    x = np.arange(len(datasets))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    bars1 = ax.bar(x - width/2, v14_0_improvements, width, label='v14.0 (sin 2-opt)', 
                   color='steelblue', alpha=0.8)
    bars2 = ax.bar(x + width/2, v14_1_improvements, width, label='v14.1 (con 2-opt)', 
                   color='seagreen', alpha=0.8)
    
    ax.set_xlabel('Dataset', fontsize=12, fontweight='bold')
    ax.set_ylabel('Mejora sobre NN (%)', fontsize=12, fontweight='bold')
    ax.set_title('Comparación: v14.0 vs v14.1 (con 2-opt)', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(datasets, rotation=15, ha='right')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.5)
    
    # Añadir valores en las barras
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}%', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig('/home/claude/pimst_v14_comparison_summary.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("\n  Gráfica resumen guardada: pimst_v14_comparison_summary.png")


if __name__ == "__main__":
    results = run_benchmark()
