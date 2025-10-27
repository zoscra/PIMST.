#!/usr/bin/env python3
"""
PIMST v13.2 - SCALING FRACTAL DIMENSION
========================================
🔬 Fractal dimension adapts to local density
📏 Box-counting inspired metrics
🌀 Multi-scale exploration strategy
"""

import numpy as np
from scipy.spatial.distance import cdist
from typing import List, Tuple
import math

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio

def compute_local_fractal_dimension(points: np.ndarray, center_idx: int, 
                                    radius_scales: List[float] = None) -> float:
    """
    Estimate local fractal dimension using correlation integral method.
    
    🔬 Higher dimension = denser region = more careful exploration needed
    """
    if radius_scales is None:
        # Use multiple scales based on dataset
        max_dist = np.max(cdist(points, points))
        radius_scales = [max_dist * r for r in [0.05, 0.1, 0.2, 0.4]]
    
    center = points[center_idx]
    distances = np.linalg.norm(points - center, axis=1)
    
    counts = []
    for radius in radius_scales:
        count = np.sum(distances < radius)
        counts.append(count if count > 0 else 1)
    
    # Fit log-log relationship: log(count) ~ D * log(radius)
    log_radii = np.log(radius_scales)
    log_counts = np.log(counts)
    
    # Linear regression for dimension
    if len(log_radii) > 1:
        slope = np.polyfit(log_radii, log_counts, 1)[0]
        dimension = max(1.0, min(2.0, slope))  # Clamp to [1, 2]
    else:
        dimension = 1.5  # Default
    
    return dimension


def compute_density_map(points: np.ndarray) -> np.ndarray:
    """
    Compute local density at each point using fractal dimension.
    
    📊 Returns array of local fractal dimensions.
    """
    n = len(points)
    density_map = np.zeros(n)
    
    # Compute for a sample of points (for efficiency)
    sample_size = min(n, 50)
    sample_indices = np.random.choice(n, sample_size, replace=False)
    
    for idx in sample_indices:
        density_map[idx] = compute_local_fractal_dimension(points, idx)
    
    # Interpolate for remaining points
    if sample_size < n:
        distances = cdist(points, points[sample_indices])
        weights = 1.0 / (distances + 1e-10)
        weights = weights / np.sum(weights, axis=1, keepdims=True)
        
        for i in range(n):
            if i not in sample_indices:
                density_map[i] = np.dot(weights[i], density_map[sample_indices])
    
    return density_map


def identify_hot_spots_scaling(points: np.ndarray, density_map: np.ndarray, 
                                k: int = None) -> List[int]:
    """
    Identify hot spots considering fractal dimension.
    
    🎯 High dimension areas need more seeds.
    """
    n = len(points)
    if k is None:
        # Adaptive k based on average dimension
        avg_dimension = np.mean(density_map)
        k = max(3, int(np.sqrt(n) * (avg_dimension / 1.5)))
    
    hot_spots = []
    remaining = set(range(n))
    
    # First: highest dimension (densest area)
    first = np.argmax(density_map)
    hot_spots.append(first)
    remaining.remove(first)
    
    # Subsequent: balance dimension and spacing
    distances = cdist(points, points)
    
    while len(hot_spots) < k and remaining:
        scores = np.zeros(n)
        for i in remaining:
            # Dimension component (higher = more important)
            dim_score = density_map[i] / (np.max(density_map) + 1e-10)
            
            # Separation from existing hot spots
            min_dist = min(distances[i, h] for h in hot_spots)
            sep_score = min_dist / (np.max(distances) + 1e-10)
            
            # Phi-weighted
            scores[i] = (PHI - 1) * dim_score + (2 - PHI) * sep_score
        
        best = max(remaining, key=lambda x: scores[x])
        hot_spots.append(best)
        remaining.remove(best)
    
    return hot_spots


def grow_fractal_with_scaling(points: np.ndarray, territory: List[int], 
                               seed: int, density_map: np.ndarray) -> List[int]:
    """
    Grow fractal tour with exploration rate adjusted by local dimension.
    
    🌀 High dimension → more local exploration
    🌀 Low dimension → larger jumps allowed
    """
    if not territory:
        return []
    
    tour = [seed]
    remaining = set(territory) - {seed}
    
    while remaining:
        current = tour[-1]
        current_pos = points[current]
        current_dimension = density_map[current]
        
        # Exploration radius scales with dimension
        # Higher dimension → smaller exploration (more careful)
        exploration_factor = 2.0 / (current_dimension + 0.5)
        
        candidates = list(remaining)
        if not candidates:
            break
        
        # Score candidates with dimension-aware weighting
        scores = []
        for candidate in candidates:
            dist = np.linalg.norm(points[candidate] - current_pos)
            
            # Dimension-scaled distance penalty
            scaled_dist = dist / exploration_factor
            
            # Angular smoothness
            if len(tour) >= 2:
                prev_vec = current_pos - points[tour[-2]]
                next_vec = points[candidate] - current_pos
                
                prev_norm = np.linalg.norm(prev_vec)
                next_norm = np.linalg.norm(next_vec)
                
                if prev_norm > 1e-10 and next_norm > 1e-10:
                    cos_angle = np.dot(prev_vec, next_vec) / (prev_norm * next_norm)
                    angle_score = (1 + cos_angle) / 2
                else:
                    angle_score = 0.5
            else:
                angle_score = 0.5
            
            # Target dimension compatibility
            target_dimension = density_map[candidate]
            dimension_compatibility = 1.0 - abs(current_dimension - target_dimension) / 2.0
            
            # Combined score with fractal scaling
            distance_score = 1.0 / (scaled_dist + 1e-10)
            score = (PHI - 1) * distance_score + \
                    (2 - PHI) * 0.5 * (angle_score + dimension_compatibility)
            scores.append(score)
        
        # Select best
        best_idx = np.argmax(scores)
        best = candidates[best_idx]
        tour.append(best)
        remaining.remove(best)
    
    return tour


def compute_territories_scaling(points: np.ndarray, hot_spots: List[int],
                                density_map: np.ndarray) -> dict:
    """
    Partition space considering fractal dimension.
    
    📐 Territories in high-dimension areas are smaller.
    """
    n = len(points)
    territories = {h: [] for h in hot_spots}
    
    # Dimension-weighted distance
    distances = cdist(points, points[hot_spots])
    
    # Adjust distances by dimension of hot spots
    for i, h in enumerate(hot_spots):
        # Higher dimension = stronger attraction (smaller effective distance)
        dimension_weight = density_map[h] / (np.mean(density_map) + 1e-10)
        distances[:, i] = distances[:, i] / (dimension_weight + 0.5)
    
    assignments = np.argmin(distances, axis=1)
    
    for i in range(n):
        hot_spot = hot_spots[assignments[i]]
        territories[hot_spot].append(i)
    
    return territories


def merge_tours_scaling(points: np.ndarray, territorial_tours: dict,
                        density_map: np.ndarray) -> List[int]:
    """
    Merge tours with dimension-aware bridging.
    
    🔗 Prefer bridges through lower-dimension regions.
    """
    if not territorial_tours:
        return []
    
    valid_tours = [(seed, tour) for seed, tour in territorial_tours.items() 
                   if tour and len(tour) > 0]
    
    if not valid_tours:
        return []
    
    if len(valid_tours) == 1:
        return valid_tours[0][1]
    
    # Start with largest
    valid_tours.sort(key=lambda x: len(x[1]), reverse=True)
    merged = list(valid_tours[0][1])
    remaining_tours = [tour for _, tour in valid_tours[1:]]
    
    while remaining_tours:
        best_tour_idx = -1
        best_insert_pos = -1
        best_cost = float('inf')
        
        for tour_idx, tour in enumerate(remaining_tours):
            if not tour:
                continue
            
            for insert_pos in range(len(merged) + 1):
                # Calculate dimension-weighted cost
                if insert_pos == 0:
                    bridge_points = [tour[0], merged[0]]
                elif insert_pos == len(merged):
                    bridge_points = [merged[-1], tour[0]]
                else:
                    bridge_points = [merged[insert_pos-1], tour[0], 
                                   tour[-1], merged[insert_pos]]
                
                # Average dimension along bridge
                bridge_dimensions = [density_map[p] for p in bridge_points]
                avg_dimension = np.mean(bridge_dimensions)
                
                # Base geometric cost
                if insert_pos == 0:
                    geom_cost = np.linalg.norm(points[merged[0]] - points[tour[0]])
                elif insert_pos == len(merged):
                    geom_cost = np.linalg.norm(points[merged[-1]] - points[tour[0]])
                else:
                    removed = np.linalg.norm(points[merged[insert_pos-1]] - 
                                           points[merged[insert_pos]])
                    added = (np.linalg.norm(points[merged[insert_pos-1]] - points[tour[0]]) +
                            np.linalg.norm(points[tour[-1]] - points[merged[insert_pos]]))
                    geom_cost = added - removed
                
                # Dimension penalty (prefer low-dimension bridges)
                dimension_penalty = avg_dimension / 2.0
                cost = geom_cost * dimension_penalty
                
                if cost < best_cost:
                    best_cost = cost
                    best_tour_idx = tour_idx
                    best_insert_pos = insert_pos
        
        if best_tour_idx >= 0:
            tour_to_insert = remaining_tours[best_tour_idx]
            merged[best_insert_pos:best_insert_pos] = tour_to_insert
            remaining_tours.pop(best_tour_idx)
        else:
            break
    
    return merged


def pimst_v13_2_scaling(points: np.ndarray) -> List[int]:
    """
    PIMST v13.2 - SCALING FRACTAL DIMENSION
    
    🔬 Key Innovation: Adapts to local fractal dimension
    
    Steps:
    1. Compute local fractal dimension everywhere
    2. Identify hot spots scaled by dimension
    3. Create dimension-aware territories
    4. Grow tours with dimension-scaled exploration
    5. Merge via low-dimension bridges
    """
    n = len(points)
    
    if n <= 3:
        return list(range(n))
    
    # Step 1: Compute density map (fractal dimensions)
    print("🔬 Computing fractal dimensions...")
    density_map = compute_density_map(points)
    
    # Step 2: Identify hot spots
    k = max(3, min(12, int(np.sqrt(n))))
    hot_spots = identify_hot_spots_scaling(points, density_map, k)
    
    # Step 3: Create territories
    territories = compute_territories_scaling(points, hot_spots, density_map)
    
    # Step 4: Grow fractal tours
    territorial_tours = {}
    for seed, territory in territories.items():
        if territory:
            tour = grow_fractal_with_scaling(points, territory, seed, density_map)
            territorial_tours[seed] = tour
    
    # Step 5: Merge
    final_tour = merge_tours_scaling(points, territorial_tours, density_map)
    
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
    print("🔬 PIMST v13.2 - SCALING FRACTAL DIMENSION")
    print("=" * 50)
    
    np.random.seed(42)
    n = 100
    points = np.random.rand(n, 2)
    
    tour = pimst_v13_2_scaling(points)
    length = calculate_tour_length(points, tour)
    
    print(f"Points: {n}")
    print(f"Tour length: {length:.4f}")
    print(f"✅ Dimension-scaled fractal growth complete!")
