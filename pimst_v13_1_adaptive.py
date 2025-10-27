#!/usr/bin/env python3
"""
PIMST v13.1 - ADAPTIVE FRACTAL GROWTH
=====================================
🌱 Hot spots compete for territory
🎯 Voronoi-like partitioning
🔄 Dynamic resource allocation
"""

import numpy as np
from scipy.spatial.distance import cdist
from typing import List, Set, Tuple
import math

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio

def identify_hot_spots_adaptive(points: np.ndarray, k: int = None) -> List[int]:
    """
    Identify hot spots using density + strategic positioning.
    These become the "seeds" for fractal growth.
    """
    n = len(points)
    if k is None:
        k = max(3, int(np.sqrt(n)))
    
    # Density map
    distances = cdist(points, points)
    density = np.sum(distances < np.median(distances), axis=1)
    
    hot_spots = []
    remaining = set(range(n))
    
    # First hot spot: highest density
    first = np.argmax(density)
    hot_spots.append(first)
    remaining.remove(first)
    
    # Subsequent hot spots: balance density and distance
    while len(hot_spots) < k and remaining:
        scores = np.zeros(len(points))
        for i in remaining:
            # Density component
            density_score = density[i] / (np.max(density) + 1e-10)
            
            # Distance from existing hot spots (separation)
            min_dist = min(distances[i, h] for h in hot_spots)
            separation_score = min_dist / (np.max(distances) + 1e-10)
            
            # Golden ratio weighting
            scores[i] = (PHI - 1) * density_score + (2 - PHI) * separation_score
        
        best = max(remaining, key=lambda x: scores[x])
        hot_spots.append(best)
        remaining.remove(best)
    
    return hot_spots


def compute_territories(points: np.ndarray, hot_spots: List[int]) -> dict:
    """
    Partition space into territories (Voronoi-like).
    Each hot spot "owns" its nearest points.
    
    🌱 This is the ADAPTIVE COMPETITION part.
    """
    n = len(points)
    territories = {h: [] for h in hot_spots}
    
    # Assign each point to nearest hot spot
    distances = cdist(points, points[hot_spots])
    assignments = np.argmin(distances, axis=1)
    
    for i in range(n):
        hot_spot = hot_spots[assignments[i]]
        territories[hot_spot].append(i)
    
    return territories


def grow_fractal_in_territory(points: np.ndarray, territory: List[int], 
                               seed: int) -> List[int]:
    """
    Grow a fractal tour within a territory from its seed.
    Uses nearest-neighbor with phi-weighted exploration.
    
    🌀 The fractal "edge" emerges naturally.
    """
    if not territory:
        return []
    
    tour = [seed]
    remaining = set(territory) - {seed}
    
    while remaining:
        current = tour[-1]
        current_pos = points[current]
        
        # Find candidates
        candidates = list(remaining)
        if not candidates:
            break
        
        # Score based on distance and angular alignment
        scores = []
        for candidate in candidates:
            dist = np.linalg.norm(points[candidate] - current_pos)
            
            # Angular component (favors smooth curves)
            if len(tour) >= 2:
                prev_vec = current_pos - points[tour[-2]]
                next_vec = points[candidate] - current_pos
                
                prev_norm = np.linalg.norm(prev_vec)
                next_norm = np.linalg.norm(next_vec)
                
                if prev_norm > 1e-10 and next_norm > 1e-10:
                    cos_angle = np.dot(prev_vec, next_vec) / (prev_norm * next_norm)
                    angle_score = (1 + cos_angle) / 2  # Normalize to [0,1]
                else:
                    angle_score = 0.5
            else:
                angle_score = 0.5
            
            # Phi-weighted combination
            score = (PHI - 1) * (1.0 / (dist + 1e-10)) + (2 - PHI) * angle_score
            scores.append(score)
        
        # Select best
        best_idx = np.argmax(scores)
        best = candidates[best_idx]
        tour.append(best)
        remaining.remove(best)
    
    return tour


def merge_territories_adaptive(points: np.ndarray, 
                               territorial_tours: dict) -> List[int]:
    """
    Merge territorial tours using adaptive bridging.
    
    🔗 Bridges minimize total connection cost while respecting
       the fractal structure that emerged.
    """
    if not territorial_tours:
        return []
    
    # Extract valid tours
    valid_tours = [(seed, tour) for seed, tour in territorial_tours.items() 
                   if tour and len(tour) > 0]
    
    if not valid_tours:
        return []
    
    if len(valid_tours) == 1:
        return valid_tours[0][1]
    
    # Start with the largest territory
    valid_tours.sort(key=lambda x: len(x[1]), reverse=True)
    merged = list(valid_tours[0][1])
    remaining_tours = [tour for _, tour in valid_tours[1:]]
    
    # Merge remaining tours one by one
    while remaining_tours:
        # Find best insertion point for next tour
        best_tour_idx = -1
        best_insert_pos = -1
        best_cost = float('inf')
        
        for tour_idx, tour in enumerate(remaining_tours):
            if not tour:
                continue
            
            # Try inserting this tour at different positions in merged
            for insert_pos in range(len(merged) + 1):
                # Calculate connection cost
                if insert_pos == 0:
                    cost = np.linalg.norm(points[merged[0]] - points[tour[0]])
                elif insert_pos == len(merged):
                    cost = np.linalg.norm(points[merged[-1]] - points[tour[0]])
                else:
                    # Cost of breaking merged and inserting tour
                    removed_edge = np.linalg.norm(points[merged[insert_pos-1]] - 
                                                 points[merged[insert_pos]])
                    new_edges = (np.linalg.norm(points[merged[insert_pos-1]] - points[tour[0]]) +
                                np.linalg.norm(points[tour[-1]] - points[merged[insert_pos]]))
                    cost = new_edges - removed_edge
                
                if cost < best_cost:
                    best_cost = cost
                    best_tour_idx = tour_idx
                    best_insert_pos = insert_pos
        
        # Insert best tour
        if best_tour_idx >= 0:
            tour_to_insert = remaining_tours[best_tour_idx]
            merged[best_insert_pos:best_insert_pos] = tour_to_insert
            remaining_tours.pop(best_tour_idx)
        else:
            break
    
    return merged


def pimst_v13_1_adaptive(points: np.ndarray) -> List[int]:
    """
    PIMST v13.1 - ADAPTIVE FRACTAL GROWTH
    
    🌱 Key Innovation: Hot spots compete for territory
    
    Steps:
    1. Identify hot spots (fractal seeds)
    2. Partition space into territories (competition)
    3. Grow fractal tour within each territory
    4. Merge territories adaptively
    """
    n = len(points)
    
    if n <= 3:
        return list(range(n))
    
    # Step 1: Identify hot spots
    k = max(3, min(12, int(np.sqrt(n))))
    hot_spots = identify_hot_spots_adaptive(points, k)
    
    # Step 2: Compute territories (ADAPTIVE COMPETITION)
    territories = compute_territories(points, hot_spots)
    
    # Step 3: Grow fractal tours in each territory
    territorial_tours = {}
    for seed, territory in territories.items():
        if territory:
            tour = grow_fractal_in_territory(points, territory, seed)
            territorial_tours[seed] = tour
    
    # Step 4: Merge territories
    final_tour = merge_territories_adaptive(points, territorial_tours)
    
    return final_tour


def calculate_tour_length(points: np.ndarray, tour: List[int]) -> float:
    """Calculate total tour length."""
    if len(tour) < 2:
        return 0.0
    length = sum(np.linalg.norm(points[tour[i]] - points[tour[i+1]]) 
                 for i in range(len(tour)-1))
    length += np.linalg.norm(points[tour[-1]] - points[tour[0]])
    return length


if __name__ == "__main__":
    print("🌱 PIMST v13.1 - ADAPTIVE FRACTAL GROWTH")
    print("=" * 50)
    
    # Test with sample data
    np.random.seed(42)
    n = 100
    points = np.random.rand(n, 2)
    
    tour = pimst_v13_1_adaptive(points)
    length = calculate_tour_length(points, tour)
    
    print(f"Points: {n}")
    print(f"Tour length: {length:.4f}")
    print(f"✅ Adaptive territorial growth complete!")
