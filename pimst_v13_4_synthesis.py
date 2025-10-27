#!/usr/bin/env python3
"""
PIMST v13.4 - FRACTAL SYNTHESIS
================================
✨ Combines ALL three fractal mechanisms:
   🌱 Adaptive territorial competition
   🔬 Variable fractal dimension scaling  
   🌊 Wavefront expansion dynamics

This is the ULTIMATE fractal approach.
"""

import numpy as np
from scipy.spatial.distance import cdist
from typing import List, Set, Tuple, Dict
import heapq
import math

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio

# ============================================================================
# FRACTAL DIMENSION COMPUTATION (from v13.2)
# ============================================================================

def compute_local_fractal_dimension(points: np.ndarray, center_idx: int, 
                                    radius_scales: List[float] = None) -> float:
    """
    Estimate local fractal dimension using correlation integral method.
    
    🔬 Higher dimension = denser region
    """
    if radius_scales is None:
        max_dist = np.max(cdist(points, points))
        radius_scales = [max_dist * r for r in [0.05, 0.1, 0.2, 0.4]]
    
    center = points[center_idx]
    distances = np.linalg.norm(points - center, axis=1)
    
    counts = []
    for radius in radius_scales:
        count = np.sum(distances < radius)
        counts.append(count if count > 0 else 1)
    
    log_radii = np.log(radius_scales)
    log_counts = np.log(counts)
    
    if len(log_radii) > 1:
        slope = np.polyfit(log_radii, log_counts, 1)[0]
        dimension = max(1.0, min(2.0, slope))
    else:
        dimension = 1.5
    
    return dimension


def compute_density_map(points: np.ndarray) -> np.ndarray:
    """
    Compute local fractal dimension at each point.
    
    📊 Returns density map as fractal dimensions.
    """
    n = len(points)
    density_map = np.zeros(n)
    
    sample_size = min(n, 50)
    sample_indices = np.random.choice(n, sample_size, replace=False)
    
    for idx in sample_indices:
        density_map[idx] = compute_local_fractal_dimension(points, idx)
    
    if sample_size < n:
        distances = cdist(points, points[sample_indices])
        weights = 1.0 / (distances + 1e-10)
        weights = weights / np.sum(weights, axis=1, keepdims=True)
        
        for i in range(n):
            if i not in sample_indices:
                density_map[i] = np.dot(weights[i], density_map[sample_indices])
    
    return density_map


# ============================================================================
# HOT SPOT IDENTIFICATION (synthesis of all three)
# ============================================================================

def identify_hot_spots_synthesis(points: np.ndarray, density_map: np.ndarray,
                                  k: int = None) -> List[int]:
    """
    Identify hot spots using ALL three principles:
    - Adaptive: Balance density and spacing
    - Scaling: Weight by fractal dimension
    - Wavefront: Optimize for wave coverage
    
    🎯 The ultimate seed selection.
    """
    n = len(points)
    if k is None:
        avg_dimension = np.mean(density_map)
        k = max(3, int(np.sqrt(n) * (avg_dimension / 1.5)))
    
    distances = cdist(points, points)
    
    hot_spots = []
    remaining = set(range(n))
    
    # First: highest dimension (densest)
    first = np.argmax(density_map)
    hot_spots.append(first)
    remaining.remove(first)
    
    while len(hot_spots) < k and remaining:
        scores = np.zeros(n)
        for i in remaining:
            # Dimension score (SCALING principle)
            dim_score = density_map[i] / (np.max(density_map) + 1e-10)
            
            # Separation score (ADAPTIVE principle)
            min_dist = min(distances[i, h] for h in hot_spots)
            sep_score = min_dist / (np.max(distances) + 1e-10)
            
            # Coverage score (WAVEFRONT principle)
            # Estimate how many new points this seed would reach
            potential_coverage = np.sum(
                np.min([distances[i, h] for h in hot_spots] + [distances[i, i]]) 
                == distances[i, i]
            )
            coverage_score = potential_coverage / n
            
            # Phi-weighted synthesis
            scores[i] = (PHI - 1) * dim_score + \
                        (2 - PHI) * 0.5 * (sep_score + coverage_score)
        
        best = max(remaining, key=lambda x: scores[x])
        hot_spots.append(best)
        remaining.remove(best)
    
    return hot_spots


# ============================================================================
# WAVEFRONT EXPANSION WITH DIMENSION SCALING (v13.2 + v13.3)
# ============================================================================

def expand_dimensional_wavefront(points: np.ndarray, seed: int,
                                 all_points: Set[int],
                                 density_map: np.ndarray) -> Tuple[List[int], Dict[int, float]]:
    """
    Expand wavefront with dimension-aware propagation.
    
    🌊🔬 Waves travel faster through low-dimension space.
    """
    visited = set()
    arrival_times = {}
    tour = []
    
    pq = [(0.0, seed)]
    arrival_times[seed] = 0.0
    
    while pq and len(visited) < len(all_points):
        current_time, current = heapq.heappop(pq)
        
        if current in visited:
            continue
        if current not in all_points:
            continue
        
        visited.add(current)
        tour.append(current)
        
        current_pos = points[current]
        current_dimension = density_map[current]
        
        for next_point in all_points:
            if next_point in visited:
                continue
            
            # Base distance
            dist = np.linalg.norm(points[next_point] - current_pos)
            
            # Dimension-scaled distance (waves slow in high-dimension regions)
            next_dimension = density_map[next_point]
            avg_dimension = (current_dimension + next_dimension) / 2.0
            dimension_factor = avg_dimension / 1.5  # Normalize around 1.0
            scaled_dist = dist * dimension_factor
            
            # Angular penalty (smooth propagation)
            if len(tour) >= 2:
                prev_vec = current_pos - points[tour[-2]]
                next_vec = points[next_point] - current_pos
                
                prev_norm = np.linalg.norm(prev_vec)
                next_norm = np.linalg.norm(next_vec)
                
                if prev_norm > 1e-10 and next_norm > 1e-10:
                    cos_angle = np.dot(prev_vec, next_vec) / (prev_norm * next_norm)
                    angle_penalty = (1 - cos_angle) * scaled_dist * 0.5
                else:
                    angle_penalty = 0.0
            else:
                angle_penalty = 0.0
            
            travel_time = scaled_dist + angle_penalty
            arrival_time = current_time + travel_time
            
            if next_point not in arrival_times or arrival_time < arrival_times[next_point]:
                arrival_times[next_point] = arrival_time
                heapq.heappush(pq, (arrival_time, next_point))
    
    return tour, arrival_times


# ============================================================================
# TERRITORY COMPUTATION (ADAPTIVE + WAVEFRONT interference)
# ============================================================================

def compute_adaptive_wave_territories(points: np.ndarray, hot_spots: List[int],
                                      all_arrival_times: Dict[int, Dict[int, float]],
                                      density_map: np.ndarray) -> Dict[int, List[int]]:
    """
    Partition using wave interference + dimension weighting.
    
    🌊🌱 Combines wavefront and adaptive principles.
    """
    n = len(points)
    territories = {h: [] for h in hot_spots}
    
    for point in range(n):
        # Find earliest arrival with dimension adjustment
        best_score = float('inf')
        winning_hot_spot = hot_spots[0]
        
        for hot_spot in hot_spots:
            if point in all_arrival_times[hot_spot]:
                arrival = all_arrival_times[hot_spot][point]
                
                # Dimension compatibility bonus
                dimension_compatibility = 1.0 - abs(density_map[hot_spot] - 
                                                   density_map[point]) / 2.0
                
                # Combined score (lower is better)
                score = arrival / (dimension_compatibility + 0.5)
                
                if score < best_score:
                    best_score = score
                    winning_hot_spot = hot_spot
        
        territories[winning_hot_spot].append(point)
    
    return territories


# ============================================================================
# TOUR GROWTH (ALL three principles)
# ============================================================================

def grow_synthesis_tour(points: np.ndarray, territory: List[int],
                        seed: int, arrival_times: Dict[int, float],
                        density_map: np.ndarray) -> List[int]:
    """
    Grow tour using:
    - Wave arrival order (WAVEFRONT)
    - Dimension-scaled exploration (SCALING)
    - Adaptive local optimization (ADAPTIVE)
    
    🌀✨ The complete fractal growth algorithm.
    """
    if not territory:
        return []
    
    # Start with wave arrival order
    territory_with_times = [(p, arrival_times.get(p, float('inf'))) 
                           for p in territory]
    territory_with_times.sort(key=lambda x: x[1])
    tour = [p for p, _ in territory_with_times]
    
    # Adaptive local optimization with dimension awareness
    if len(tour) > 3:
        tour = optimize_dimensional_tour(points, tour, density_map)
    
    return tour


def optimize_dimensional_tour(points: np.ndarray, tour: List[int],
                               density_map: np.ndarray, window: int = 5) -> List[int]:
    """
    Local optimization considering fractal dimension.
    
    🔧 Smooth while respecting dimension landscape.
    """
    n = len(tour)
    improved = True
    iterations = 0
    max_iterations = 3
    
    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        
        for i in range(n):
            for j in range(i + 2, min(i + window, n)):
                # Current cost
                p1, p2 = tour[i], tour[i+1]
                p3, p4 = tour[j], tour[(j+1) % n]
                
                current_geom = (np.linalg.norm(points[p1] - points[p2]) +
                               np.linalg.norm(points[p3] - points[p4]))
                
                # Dimension penalty for current edges
                current_dim = (density_map[p1] + density_map[p2] +
                              density_map[p3] + density_map[p4]) / 4.0
                current_cost = current_geom * (current_dim / 1.5)
                
                # New cost if reversed
                new_geom = (np.linalg.norm(points[p1] - points[p3]) +
                           np.linalg.norm(points[p2] - points[p4]))
                new_dim = current_dim  # Same points, same average dimension
                new_cost = new_geom * (new_dim / 1.5)
                
                if new_cost < current_cost:
                    tour[i+1:j+1] = tour[i+1:j+1][::-1]
                    improved = True
    
    return tour


# ============================================================================
# TOUR MERGING (Synthesis of all principles)
# ============================================================================

def merge_synthesis_tours(points: np.ndarray, 
                         territorial_tours: Dict[int, List[int]],
                         all_arrival_times: Dict[int, Dict[int, float]],
                         density_map: np.ndarray) -> List[int]:
    """
    Merge tours using:
    - Adaptive cost minimization
    - Dimension-aware bridging
    - Wavefront boundary quality
    
    🔗✨ The ultimate merge strategy.
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
    remaining_tours = [(seed, tour) for seed, tour in valid_tours[1:]]
    
    while remaining_tours:
        best_tour_idx = -1
        best_insert_pos = -1
        best_cost = float('inf')
        
        for tour_idx, (seed, tour) in enumerate(remaining_tours):
            if not tour:
                continue
            
            for insert_pos in range(len(merged) + 1):
                # Geometric cost (ADAPTIVE)
                if insert_pos == 0:
                    geom_cost = np.linalg.norm(points[merged[0]] - points[tour[0]])
                    bridge_points = [tour[0], merged[0]]
                elif insert_pos == len(merged):
                    geom_cost = np.linalg.norm(points[merged[-1]] - points[tour[0]])
                    bridge_points = [merged[-1], tour[0]]
                else:
                    removed = np.linalg.norm(points[merged[insert_pos-1]] - 
                                           points[merged[insert_pos]])
                    added = (np.linalg.norm(points[merged[insert_pos-1]] - points[tour[0]]) +
                            np.linalg.norm(points[tour[-1]] - points[merged[insert_pos]]))
                    geom_cost = added - removed
                    bridge_points = [merged[insert_pos-1], tour[0], 
                                   tour[-1], merged[insert_pos]]
                
                # Dimension penalty (SCALING)
                avg_dimension = np.mean([density_map[p] for p in bridge_points])
                dimension_penalty = avg_dimension / 1.5
                
                # Wavefront boundary quality (WAVEFRONT)
                boundary_quality = 0.0
                for bp in bridge_points:
                    times_at_point = [all_arrival_times[s].get(bp, float('inf')) 
                                     for s, _ in remaining_tours + [(seed, tour)]]
                    if len(times_at_point) > 1:
                        valid_times = [t for t in times_at_point if t < float('inf')]
                        if valid_times:
                            variance = np.var(valid_times)
                            boundary_quality += 1.0 / (variance + 1e-10)
                
                # Synthesized cost
                cost = geom_cost * dimension_penalty - 0.05 * boundary_quality
                
                if cost < best_cost:
                    best_cost = cost
                    best_tour_idx = tour_idx
                    best_insert_pos = insert_pos
        
        if best_tour_idx >= 0:
            _, tour_to_insert = remaining_tours[best_tour_idx]
            merged[best_insert_pos:best_insert_pos] = tour_to_insert
            remaining_tours.pop(best_tour_idx)
        else:
            break
    
    return merged


# ============================================================================
# MAIN ALGORITHM
# ============================================================================

def pimst_v13_4_synthesis(points: np.ndarray) -> List[int]:
    """
    PIMST v13.4 - FRACTAL SYNTHESIS
    
    ✨ THE ULTIMATE FRACTAL TSP SOLVER ✨
    
    Combines:
    🌱 Adaptive territorial competition
    🔬 Variable fractal dimension scaling
    🌊 Wavefront expansion dynamics
    
    Steps:
    1. Compute fractal dimension landscape
    2. Identify optimal hot spots (synthesis of all principles)
    3. Expand dimension-aware wavefronts
    4. Create adaptive territories from wave interference
    5. Grow tours using wave order + dimension scaling + adaptive optimization
    6. Merge using synthesized cost function
    """
    n = len(points)
    
    if n <= 3:
        return list(range(n))
    
    print("✨ FRACTAL SYNTHESIS v13.4")
    print("=" * 50)
    
    # Step 1: Compute fractal dimensions
    print("🔬 Computing fractal dimension landscape...")
    density_map = compute_density_map(points)
    print(f"   Dimension range: [{np.min(density_map):.3f}, {np.max(density_map):.3f}]")
    
    # Step 2: Identify hot spots
    k = max(3, min(12, int(np.sqrt(n))))
    print(f"🎯 Identifying {k} optimal hot spots...")
    hot_spots = identify_hot_spots_synthesis(points, density_map, k)
    
    # Step 3: Expand dimensional wavefronts
    print(f"🌊 Expanding {len(hot_spots)} dimension-aware wavefronts...")
    all_points = set(range(n))
    all_arrival_times = {}
    
    for seed in hot_spots:
        tour, arrival_times = expand_dimensional_wavefront(points, seed, 
                                                          all_points, density_map)
        all_arrival_times[seed] = arrival_times
    
    # Step 4: Create adaptive territories
    print("🌱 Computing adaptive wave territories...")
    territories = compute_adaptive_wave_territories(points, hot_spots,
                                                    all_arrival_times, density_map)
    
    # Step 5: Grow synthesis tours
    print("🌀 Growing fractal tours in each territory...")
    territorial_tours = {}
    for seed, territory in territories.items():
        if territory:
            tour = grow_synthesis_tour(points, territory, seed,
                                       all_arrival_times[seed], density_map)
            territorial_tours[seed] = tour
    
    # Step 6: Merge with synthesis strategy
    print("🔗 Merging territories with synthesis strategy...")
    final_tour = merge_synthesis_tours(points, territorial_tours,
                                       all_arrival_times, density_map)
    
    print("✅ Fractal synthesis complete!")
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
    print("\n" + "="*60)
    print("🌀✨ PIMST v13.4 - FRACTAL SYNTHESIS ✨🌀")
    print("="*60 + "\n")
    
    np.random.seed(42)
    n = 100
    points = np.random.rand(n, 2)
    
    tour = pimst_v13_4_synthesis(points)
    length = calculate_tour_length(points, tour)
    
    print(f"\n📊 RESULTS:")
    print(f"   Points: {n}")
    print(f"   Tour length: {length:.4f}")
    print(f"\n✨ All three fractal principles working in harmony! ✨")
