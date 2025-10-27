"""
Phyllotaxis-Inspired Multi-Start TSP (PIMST)
============================================

A bio-inspired heuristic for the Traveling Salesman Problem based on
phyllotaxis patterns found in nature (e.g., sunflower seed arrangements).

Author: [Tu Nombre]
Date: 2025
License: MIT
"""

import numpy as np
import time
from typing import List, Tuple, Dict
import math


class PIMST:
    """
    Phyllotaxis-Inspired Multi-Start TSP Heuristic
    
    This algorithm uses the golden angle (≈137.5°) to distribute starting
    points uniformly around the problem space, combined with circular greedy
    construction and 2-opt local search.
    
    Parameters
    ----------
    cities : np.ndarray
        Array of shape (n, 2) with city coordinates
    alpha : float, default=0.5
        Radius factor for circular greedy (range: 0.3-0.7)
    k_starts : int, default=8
        Number of starting points to try
    max_2opt_iter : int, default=100
        Maximum iterations for 2-opt refinement
    """
    
    def __init__(self, cities: np.ndarray, alpha: float = 0.5, 
                 k_starts: int = 8, max_2opt_iter: int = 100):
        self.cities = np.array(cities)
        self.n_cities = len(cities)
        self.alpha = alpha
        self.k_starts = k_starts
        self.max_2opt_iter = max_2opt_iter
        
        # Golden ratio and golden angle
        self.PHI = (1 + math.sqrt(5)) / 2  # ≈ 1.618
        self.GOLDEN_ANGLE = 2 * math.pi * (1 - 1/self.PHI)  # ≈ 2.399 rad
        
        # Precompute centroid
        self.centroid = np.mean(cities, axis=0)
    
    def solve(self, verbose: bool = False) -> Tuple[List[int], float, Dict]:
        """
        Solve TSP using PIMST heuristic
        
        Parameters
        ----------
        verbose : bool
            Print progress information
        
        Returns
        -------
        best_tour : List[int]
            Best tour found (list of city indices)
        best_distance : float
            Distance of best tour
        stats : Dict
            Statistics about the run
        """
        start_time = time.time()
        
        # Generate starting points using golden angle
        starting_cities = self._generate_starting_points()
        
        # Run from each starting point
        tours = []
        distances = []
        
        for i, start_city in enumerate(starting_cities):
            if verbose:
                print(f"Starting point {i+1}/{self.k_starts}: City {start_city}")
            
            # Circular greedy construction
            tour = self._circular_greedy(start_city)
            
            # 2-opt refinement
            tour = self._two_opt(tour)
            
            distance = self._tour_distance(tour)
            
            tours.append(tour)
            distances.append(distance)
            
            if verbose:
                print(f"  Distance: {distance:.2f}")
        
        # Select best tour
        best_idx = np.argmin(distances)
        best_tour = tours[best_idx]
        best_distance = distances[best_idx]
        
        end_time = time.time()
        
        stats = {
            'time': end_time - start_time,
            'best_distance': best_distance,
            'mean_distance': np.mean(distances),
            'std_distance': np.std(distances),
            'worst_distance': np.max(distances),
            'all_distances': distances,
            'starting_points': starting_cities
        }
        
        if verbose:
            print(f"\nBest distance: {best_distance:.2f}")
            print(f"Time: {stats['time']:.3f}s")
        
        return best_tour, best_distance, stats
    
    def _generate_starting_points(self) -> List[int]:
        """
        Generate starting points using golden angle distribution
        
        Returns
        -------
        starting_cities : List[int]
            Indices of cities to use as starting points
        """
        starting_cities = []
        angle = 0
        
        for _ in range(self.k_starts):
            # Find city closest to this angle
            best_city = None
            min_diff = float('inf')
            
            for city_idx in range(self.n_cities):
                city_angle = self._compute_angle(city_idx)
                diff = abs(city_angle - angle)
                
                # Handle circular difference
                if diff > math.pi:
                    diff = 2 * math.pi - diff
                
                if diff < min_diff and city_idx not in starting_cities:
                    min_diff = diff
                    best_city = city_idx
            
            if best_city is not None:
                starting_cities.append(best_city)
            
            # Next angle using golden angle
            angle += self.GOLDEN_ANGLE
            if angle > math.pi:
                angle -= 2 * math.pi
        
        return starting_cities
    
    def _circular_greedy(self, start: int) -> List[int]:
        """
        Circular greedy construction
        
        Parameters
        ----------
        start : int
            Starting city index
        
        Returns
        -------
        tour : List[int]
            Constructed tour
        """
        tour = [start]
        visited = {start}
        unvisited = set(range(self.n_cities)) - visited
        
        while unvisited:
            current = tour[-1]
            
            # Compute average distance to unvisited cities
            distances = [self._distance(current, city) for city in unvisited]
            avg_dist = np.mean(distances)
            
            # Radius for circular selection
            radius = self.alpha * avg_dist
            
            # Find cities within radius
            in_circle = []
            for city in unvisited:
                if self._distance(current, city) <= radius:
                    in_circle.append((city, self._distance(current, city)))
            
            # If no cities in circle, take nearest
            if not in_circle:
                nearest = min(unvisited, key=lambda c: self._distance(current, c))
                in_circle = [(nearest, self._distance(current, nearest))]
            
            # Sort by distance and add all to tour
            in_circle.sort(key=lambda x: x[1])
            for city, _ in in_circle:
                tour.append(city)
                visited.add(city)
                unvisited.discard(city)
        
        return tour
    
    def _two_opt(self, tour: List[int]) -> List[int]:
        """
        2-opt local search
        
        Parameters
        ----------
        tour : List[int]
            Initial tour
        
        Returns
        -------
        improved_tour : List[int]
            Improved tour
        """
        best_tour = tour.copy()
        improved = True
        iteration = 0
        
        while improved and iteration < self.max_2opt_iter:
            improved = False
            iteration += 1
            
            for i in range(1, len(best_tour) - 1):
                for j in range(i + 1, len(best_tour)):
                    if j - i == 1:
                        continue
                    
                    # Compute improvement
                    current_edges = (
                        self._distance_idx(best_tour[i-1], best_tour[i]) +
                        self._distance_idx(best_tour[j], 
                                          best_tour[(j+1) % len(best_tour)])
                    )
                    
                    new_edges = (
                        self._distance_idx(best_tour[i-1], best_tour[j]) +
                        self._distance_idx(best_tour[i], 
                                          best_tour[(j+1) % len(best_tour)])
                    )
                    
                    if new_edges < current_edges:
                        # Reverse segment
                        best_tour[i:j+1] = best_tour[i:j+1][::-1]
                        improved = True
                        break
                
                if improved:
                    break
        
        return best_tour
    
    def _compute_angle(self, city_idx: int) -> float:
        """Compute angle of city relative to centroid"""
        dx = self.cities[city_idx][0] - self.centroid[0]
        dy = self.cities[city_idx][1] - self.centroid[1]
        return math.atan2(dy, dx)
    
    def _distance(self, city1_idx: int, city2_idx: int) -> float:
        """Euclidean distance between two cities"""
        return np.linalg.norm(self.cities[city1_idx] - self.cities[city2_idx])
    
    def _distance_idx(self, idx1: int, idx2: int) -> float:
        """Alias for _distance"""
        return self._distance(idx1, idx2)
    
    def _tour_distance(self, tour: List[int]) -> float:
        """Compute total tour distance"""
        distance = 0
        for i in range(len(tour)):
            distance += self._distance(tour[i], tour[(i+1) % len(tour)])
        return distance


def nearest_neighbor(cities: np.ndarray, start: int = 0) -> Tuple[List[int], float]:
    """
    Nearest neighbor heuristic (baseline)
    
    Parameters
    ----------
    cities : np.ndarray
        Array of city coordinates
    start : int
        Starting city
    
    Returns
    -------
    tour : List[int]
        Tour as list of city indices
    distance : float
        Total tour distance
    """
    n = len(cities)
    tour = [start]
    visited = {start}
    
    while len(visited) < n:
        current = tour[-1]
        nearest = min(
            (i for i in range(n) if i not in visited),
            key=lambda i: np.linalg.norm(cities[current] - cities[i])
        )
        tour.append(nearest)
        visited.add(nearest)
    
    # Compute distance
    distance = sum(
        np.linalg.norm(cities[tour[i]] - cities[tour[(i+1)%n]])
        for i in range(n)
    )
    
    return tour, distance


# Example usage
if __name__ == "__main__":
    # Generate random cities
    np.random.seed(42)
    cities = np.random.rand(50, 2) * 100
    
    # Solve with PIMST
    print("="*60)
    print("PIMST - Phyllotaxis-Inspired Multi-Start TSP")
    print("="*60)
    
    solver = PIMST(cities, alpha=0.5, k_starts=8)
    tour, distance, stats = solver.solve(verbose=True)
    
    # Compare with nearest neighbor
    print("\n" + "="*60)
    print("Comparison with Nearest Neighbor")
    print("="*60)
    
    nn_tour, nn_distance = nearest_neighbor(cities)
    print(f"Nearest Neighbor: {nn_distance:.2f}")
    print(f"PIMST:           {distance:.2f}")
    
    improvement = (nn_distance - distance) / nn_distance * 100
    print(f"Improvement:     {improvement:.2f}%")
