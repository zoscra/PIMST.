#!/usr/bin/env python3
"""
PIMST v13.3 - WAVEFRONT FRACTAL EXPANSION
==========================================
🌊 Tours expand as waves from hot spot seeds
🔄 BFS-inspired organic growth
💫 Interference patterns guide connections
"""

import numpy as np
from scipy.spatial.distance import cdist
from typing import List, Set, Tuple, Dict
import heapq
import math

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio

def identify_hot_spots_wavefront(points: np.ndarray, k: int = None) -> List[int]:
    """
    Identify hot spots that will serve as wave sources.
    
    🎯 Strategic positioning for optimal wave coverage.
    """
    n = len(points)
    if k is None:
        k = max(3, int(np.sqrt(n)))
    
    distances = cdist(points, points)
    density = np.sum(distances < np.median(distances), axis=1)
    
    hot_spots = []
    remaining = set(range(n))
    
    # First: highest density
    first = np.argmax(density)
    hot_spots.append(first)
    remaining.remove(first)
    
    # Rest: maximize coverage
    while len(hot_spots) < k and remaining:
        scores = np.zeros(n)
        for i in remaining:
            density_score = density[i] / (np.max(density) + 1e-10)
            min_dist = min(distances[i, h] for h in hot_spots)
            separation_score = min_dist / (np.max(distances) + 1e-10)
            scores[i] = (PHI - 1) * density_score + (2 - PHI) * separation_score
        
        best = max(remaining, key=lambda x: scores[x])
        hot_spots.append(best)
        remaining.remove(best)
    
    return hot_spots


def expand_wavefront(points: np.ndarray, seed: int, 
                     all_points: Set[int]) -> Tuple[List[int], Dict[int, float]]:
    """
    Expand a wavefront from seed using Dijkstra-like algorithm.
    
    🌊 Wave grows outward, recording arrival times.
    
    Returns:
        - Expansion order (the tour)
        - Arrival times (wave phase)
    """
    n = len(points)
    visited = set()
    arrival_times = {}
    tour = []
    
    # Priority queue: (time, point_index)
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
        
        # Expand to neighbors
        current_pos = points[current]
        
        for next_point in all_points:
            if next_point in visited:
                continue
            
            # Wave travel time = distance + angular penalty
            dist = np.linalg.norm(points[next_point] - current_pos)
            
            # Angular smoothness (waves prefer straight propagation)
            if len(tour) >= 2:
                prev_pos = points[tour[-2]]
                prev_vec = current_pos - prev_pos
                next_vec = points[next_point] - current_pos
                
                prev_norm = np.linalg.norm(prev_vec)
                next_norm = np.linalg.norm(next_vec)
                
                if prev_norm > 1e-10 and next_norm > 1e-10:
                    cos_angle = np.dot(prev_vec, next_vec) / (prev_norm * next_norm)
                    # Penalty for sharp turns (waves refract smoothly)
                    angle_penalty = (1 - cos_angle) * dist * 0.5
                else:
                    angle_penalty = 0.0
            else:
                angle_penalty = 0.0
            
            travel_time = dist + angle_penalty
            arrival_time = current_time + travel_time
            
            # Update if faster arrival or first time
            if next_point not in arrival_times or arrival_time < arrival_times[next_point]:
                arrival_times[next_point] = arrival_time
                heapq.heappush(pq, (arrival_time, next_point))
    
    return tour, arrival_times


def compute_wave_territories(points: np.ndarray, hot_spots: List[int],
                             all_arrival_times: Dict[int, Dict[int, float]]) -> Dict[int, List[int]]:
    """
    Partition points based on which wave arrives first.
    
    🌊 Interference pattern determines territories.
    """
    n = len(points)
    territories = {h: [] for h in hot_spots}
    
    for point in range(n):
        # Find which hot spot's wave arrives first
        earliest_arrival = float('inf')
        winning_hot_spot = hot_spots[0]
        
        for hot_spot in hot_spots:
            if point in all_arrival_times[hot_spot]:
                arrival = all_arrival_times[hot_spot][point]
                if arrival < earliest_arrival:
                    earliest_arrival = arrival
                    winning_hot_spot = hot_spot
        
        territories[winning_hot_spot].append(point)
    
    return territories


def grow_wave_tour(points: np.ndarray, territory: List[int], 
                   seed: int, arrival_times: Dict[int, float]) -> List[int]:
    """
    Create tour following wave arrival order.
    
    🌊 Tour traces the wavefront expansion.
    """
    if not territory:
        return []
    
    # Sort by arrival time
    territory_with_times = [(p, arrival_times.get(p, float('inf'))) 
                           for p in territory]
    territory_with_times.sort(key=lambda x: x[1])
    
    # Extract tour order
    tour = [p for p, _ in territory_with_times]
    
    # Optional: local optimization to reduce crossings
    # Keep the wave structure but smooth locally
    if len(tour) > 3:
        tour = optimize_wave_tour_local(points, tour)
    
    return tour


def optimize_wave_tour_local(points: np.ndarray, tour: List[int], 
                             window: int = 5) -> List[int]:
    """
    Local 2-opt style optimization within sliding windows.
    
    🔧 Smooth the wave path without destroying global structure.
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
                # Try reversing segment [i+1, j]
                current_cost = (
                    np.linalg.norm(points[tour[i]] - points[tour[i+1]]) +
                    np.linalg.norm(points[tour[j]] - points[tour[(j+1) % n]])
                )
                
                new_cost = (
                    np.linalg.norm(points[tour[i]] - points[tour[j]]) +
                    np.linalg.norm(points[tour[i+1]] - points[tour[(j+1) % n]])
                )
                
                if new_cost < current_cost:
                    # Reverse segment
                    tour[i+1:j+1] = tour[i+1:j+1][::-1]
                    improved = True
    
    return tour


def merge_wave_tours(points: np.ndarray, territorial_tours: Dict[int, List[int]],
                     all_arrival_times: Dict[int, Dict[int, float]]) -> List[int]:
    """
    Merge wave tours considering interference patterns.
    
    🌊 Connect at wavefront boundaries.
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
        best_boundary_quality = -float('inf')
        
        for tour_idx, (seed, tour) in enumerate(remaining_tours):
            if not tour:
                continue
            
            for insert_pos in range(len(merged) + 1):
                # Calculate geometric cost
                if insert_pos == 0:
                    geom_cost = np.linalg.norm(points[merged[0]] - points[tour[0]])
                    boundary_points = [tour[0], merged[0]]
                elif insert_pos == len(merged):
                    geom_cost = np.linalg.norm(points[merged[-1]] - points[tour[0]])
                    boundary_points = [merged[-1], tour[0]]
                else:
                    removed = np.linalg.norm(points[merged[insert_pos-1]] - 
                                           points[merged[insert_pos]])
                    added = (np.linalg.norm(points[merged[insert_pos-1]] - points[tour[0]]) +
                            np.linalg.norm(points[tour[-1]] - points[merged[insert_pos]]))
                    geom_cost = added - removed
                    boundary_points = [merged[insert_pos-1], tour[0], 
                                     tour[-1], merged[insert_pos]]
                
                # Boundary quality: prefer connections at wavefront edges
                # (where arrival times are similar from different sources)
                boundary_quality = 0.0
                for bp in boundary_points:
                    times_at_point = [all_arrival_times[s].get(bp, float('inf')) 
                                     for s, _ in remaining_tours + [(seed, tour)]]
                    # High quality = small variance in arrival times
                    if len(times_at_point) > 1:
                        variance = np.var([t for t in times_at_point if t < float('inf')])
                        boundary_quality += 1.0 / (variance + 1e-10)
                
                # Combined score
                cost = geom_cost - 0.1 * boundary_quality
                
                if cost < best_cost:
                    best_cost = cost
                    best_tour_idx = tour_idx
                    best_insert_pos = insert_pos
                    best_boundary_quality = boundary_quality
        
        if best_tour_idx >= 0:
            _, tour_to_insert = remaining_tours[best_tour_idx]
            merged[best_insert_pos:best_insert_pos] = tour_to_insert
            remaining_tours.pop(best_tour_idx)
        else:
            break
    
    return merged


def pimst_v13_3_wavefront(points: np.ndarray) -> List[int]:
    """
    PIMST v13.3 - WAVEFRONT FRACTAL EXPANSION
    
    🌊 Key Innovation: Tours grow as expanding waves
    
    Steps:
    1. Identify hot spots (wave sources)
    2. Expand wavefronts from each source
    3. Compute territories by wave interference
    4. Create tours following wave arrival order
    5. Merge at wavefront boundaries
    """
    n = len(points)
    
    if n <= 3:
        return list(range(n))
    
    # Step 1: Identify hot spots
    k = max(3, min(12, int(np.sqrt(n))))
    hot_spots = identify_hot_spots_wavefront(points, k)
    
    print(f"🌊 Expanding {len(hot_spots)} wavefronts...")
    
    # Step 2: Expand wavefronts
    all_points = set(range(n))
    all_arrival_times = {}
    wavefront_tours = {}
    
    for seed in hot_spots:
        tour, arrival_times = expand_wavefront(points, seed, all_points)
        wavefront_tours[seed] = tour
        all_arrival_times[seed] = arrival_times
    
    # Step 3: Compute wave-based territories
    territories = compute_wave_territories(points, hot_spots, all_arrival_times)
    
    # Step 4: Create tours from wave expansion
    territorial_tours = {}
    for seed, territory in territories.items():
        if territory:
            tour = grow_wave_tour(points, territory, seed, all_arrival_times[seed])
            territorial_tours[seed] = tour
    
    # Step 5: Merge at boundaries
    final_tour = merge_wave_tours(points, territorial_tours, all_arrival_times)
    
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
    print("🌊 PIMST v13.3 - WAVEFRONT FRACTAL EXPANSION")
    print("=" * 50)
    
    np.random.seed(42)
    n = 100
    points = np.random.rand(n, 2)
    
    tour = pimst_v13_3_wavefront(points)
    length = calculate_tour_length(points, tour)
    
    print(f"Points: {n}")
    print(f"Tour length: {length:.4f}")
    print(f"✅ Wavefront expansion complete!")
