#!/usr/bin/env python3
"""
PIMST FRACTAL - Production Module
==================================

Fast, effective TSP solver using fractal growth principles.

Quick Start:
    from pimst_fractal import solve_tsp
    
    points = np.random.rand(100, 2)
    tour = solve_tsp(points)

Advanced Usage:
    from pimst_fractal import PIMST_Fractal
    
    solver = PIMST_Fractal()
    tour = solver.solve(points, algorithm='auto')
    length = solver.calculate_length(points, tour)

Algorithms:
    - 'auto': Automatically selects best algorithm (RECOMMENDED)
    - 'v13.1' or 'adaptive': Fast territorial competition (80% of cases)
    - 'v13.2' or 'scaling': Fractal dimension scaling (multi-scale data)
"""

import numpy as np
from typing import List, Optional
from pimst_v13_1_adaptive import pimst_v13_1_adaptive
from pimst_v13_2_scaling import pimst_v13_2_scaling
from pimst_fractal_architecture import PIMST_Fractal, detect_dataset_characteristics


# ============================================================================
# SIMPLE API
# ============================================================================

def solve_tsp(points: np.ndarray, 
              algorithm: str = 'auto',
              return_length: bool = False) -> np.ndarray:
    """
    Solve TSP using fractal growth approach.
    
    This is the simplest way to use PIMST Fractal.
    
    Args:
        points: Nx2 numpy array of point coordinates
        algorithm: 'auto', 'adaptive', or 'scaling' (default: 'auto')
        return_length: If True, returns (tour, length) tuple
    
    Returns:
        Tour as array of point indices, or (tour, length) if return_length=True
    
    Example:
        >>> points = np.random.rand(50, 2)
        >>> tour = solve_tsp(points)
        >>> print(f"Tour visits {len(tour)} points")
    """
    solver = PIMST_Fractal()
    tour = solver.solve(points, algorithm=algorithm)
    
    if return_length:
        length = solver.calculate_length(points, tour)
        return np.array(tour), length
    
    return np.array(tour)


def calculate_tour_length(points: np.ndarray, tour: List[int]) -> float:
    """
    Calculate the total length of a tour.
    
    Args:
        points: Nx2 array of coordinates
        tour: List of point indices
    
    Returns:
        Total Euclidean tour length
    """
    if len(tour) < 2:
        return 0.0
    length = sum(np.linalg.norm(points[tour[i]] - points[tour[i+1]]) 
                 for i in range(len(tour)-1))
    length += np.linalg.norm(points[tour[-1]] - points[tour[0]])
    return length


def recommend_algorithm(points: np.ndarray) -> str:
    """
    Analyze dataset and recommend which algorithm to use.
    
    Args:
        points: Nx2 array of coordinates
    
    Returns:
        'adaptive' or 'scaling'
    """
    characteristics = detect_dataset_characteristics(points)
    return characteristics['algorithm'].replace('v13.', '')


# ============================================================================
# BATCH PROCESSING
# ============================================================================

def solve_tsp_batch(datasets: List[np.ndarray],
                    algorithm: str = 'auto',
                    verbose: bool = True) -> List[np.ndarray]:
    """
    Solve multiple TSP instances efficiently.
    
    Args:
        datasets: List of Nx2 coordinate arrays
        algorithm: Algorithm to use for all datasets
        verbose: Print progress
    
    Returns:
        List of tour arrays
    """
    solver = PIMST_Fractal()
    tours = []
    
    for i, points in enumerate(datasets):
        if verbose:
            print(f"Solving dataset {i+1}/{len(datasets)} ({len(points)} points)...", 
                  end=' ')
        
        tour = solver.solve(points, algorithm=algorithm)
        tours.append(np.array(tour))
        
        if verbose:
            length = solver.calculate_length(points, tour)
            print(f"✅ Length: {length:.4f}")
    
    return tours


# ============================================================================
# COMPARISON & BENCHMARKING
# ============================================================================

def compare_algorithms(points: np.ndarray, 
                      algorithms: Optional[List[str]] = None) -> dict:
    """
    Compare different algorithms on the same dataset.
    
    Args:
        points: Nx2 array of coordinates
        algorithms: List of algorithms to test (default: ['adaptive', 'scaling'])
    
    Returns:
        Dictionary with algorithm names as keys and (tour, length, time) as values
    """
    import time
    
    if algorithms is None:
        algorithms = ['adaptive', 'scaling']
    
    solver = PIMST_Fractal()
    results = {}
    
    for algo in algorithms:
        start = time.time()
        tour = solver.solve(points, algorithm=algo)
        elapsed = time.time() - start
        
        length = solver.calculate_length(points, tour)
        results[algo] = {
            'tour': tour,
            'length': length,
            'time': elapsed
        }
    
    return results


# ============================================================================
# VISUALIZATION
# ============================================================================

def visualize_tour(points: np.ndarray, 
                   tour: List[int],
                   title: str = "PIMST Fractal Tour",
                   save_path: Optional[str] = None):
    """
    Create a visualization of the tour.
    
    Args:
        points: Nx2 array of coordinates
        tour: List of point indices
        title: Plot title
        save_path: If provided, save to this path
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Matplotlib not available for visualization")
        return
    
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Plot tour
    tour_points = points[tour + [tour[0]]]
    ax.plot(tour_points[:, 0], tour_points[:, 1], 
            'b-', linewidth=2, alpha=0.6, label='Tour')
    
    # Plot points
    ax.scatter(points[:, 0], points[:, 1], 
               c='red', s=100, zorder=5, alpha=0.8, label='Cities')
    
    # Highlight start
    ax.scatter(points[tour[0], 0], points[tour[0], 1],
               c='green', s=300, marker='*', zorder=6, 
               label='Start', edgecolors='black', linewidths=2)
    
    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"✅ Visualization saved to {save_path}")
    else:
        plt.show()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'solve_tsp',
    'calculate_tour_length',
    'recommend_algorithm',
    'solve_tsp_batch',
    'compare_algorithms',
    'visualize_tour',
    'PIMST_Fractal',
]

__version__ = '13.1.0'
__author__ = 'PIMST Fractal Research'


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("PIMST FRACTAL - Production Module Demo")
    print("="*70 + "\n")
    
    # Generate test data
    np.random.seed(42)
    points = np.random.rand(50, 2)
    
    # 1. Simple usage
    print("1️⃣  Simple API:")
    tour, length = solve_tsp(points, return_length=True)
    print(f"   Tour length: {length:.4f}\n")
    
    # 2. Recommendation
    print("2️⃣  Algorithm recommendation:")
    recommended = recommend_algorithm(points)
    print(f"   Recommended: {recommended}\n")
    
    # 3. Comparison
    print("3️⃣  Algorithm comparison:")
    results = compare_algorithms(points)
    for algo, res in results.items():
        print(f"   {algo:10s}: length={res['length']:.4f}, time={res['time']:.4f}s")
    
    print("\n✅ All demos complete!")
    print("="*70)
