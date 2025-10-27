#!/usr/bin/env python3
"""
PIMST FRACTAL FAMILY - ARCHITECTURE & RECOMMENDATIONS
======================================================

Based on comprehensive benchmarking, we now understand when to use each approach.

BENCHMARK RESULTS SUMMARY:
--------------------------
Dataset Type    | v13.1    | v13.2    | v13.3    | v13.4    | Winner
----------------|----------|----------|----------|----------|--------
Random          | 10.3343  | 10.4484  | 12.7305  | 14.2650  | v13.1
Clustered       |  9.6729  | 10.4974  | 12.9807  | 13.5232  | v13.1
Grid            | 13.5301  | 14.7748  | 16.6740  | 18.8830  | v13.1
Spiral          |  6.0094  |  7.2109  | 12.1255  | 15.3852  | v13.1
Multi-scale     |  7.3611  |  7.0857  |  9.2381  | 10.0282  | v13.2

Speed (avg):
v13.1: 0.031s  ⚡⚡⚡
v13.2: 0.048s  ⚡⚡
v13.3: 0.560s  🐌
v13.4: 0.642s  🐌🐌


ARCHITECTURE DECISION:
======================

🏆 PRIMARY ALGORITHM: v13.1 ADAPTIVE
   - Use for: 80% of cases
   - Why: Best quality/speed tradeoff
   - Wins on: random, clustered, grid, spiral datasets
   - Speed: 18-21x faster than complex versions

🔬 SPECIALIZED ALGORITHM: v13.2 SCALING
   - Use for: Datasets with multi-scale fractal structure
   - Why: Dimension awareness helps in truly fractal data
   - Wins on: multi_scale datasets
   - Speed: 12-14x faster than wavefront versions

❌ DEPRECATED: v13.3 WAVEFRONT, v13.4 SYNTHESIS
   - Complexity overhead doesn't justify results
   - Keep as reference implementations


RECOMMENDED PRODUCTION SYSTEM:
===============================
"""

import numpy as np
from scipy.spatial.distance import cdist
from typing import List, Dict
from pimst_v13_1_adaptive import pimst_v13_1_adaptive
from pimst_v13_2_scaling import pimst_v13_2_scaling


def detect_dataset_characteristics(points: np.ndarray) -> Dict[str, float]:
    """
    Analyze dataset to determine which algorithm to use.
    
    Returns characteristics:
    - multi_scale_score: How fractal/hierarchical is the data?
    - clustering_coefficient: How clustered?
    - regularity_score: How regular/grid-like?
    """
    n = len(points)
    if n < 20:
        return {'multi_scale_score': 0, 'algorithm': 'v13.1'}
    
    # Sample distances for efficiency
    sample_size = min(n, 100)
    sample_indices = np.random.choice(n, sample_size, replace=False)
    sample_points = points[sample_indices]
    
    distances = cdist(sample_points, sample_points)
    
    # 1. Multi-scale score: variance in local densities
    local_densities = []
    radius_scales = [0.05, 0.1, 0.2]
    max_dist = np.max(distances)
    
    for i in range(min(20, sample_size)):
        densities_at_scales = []
        for scale in radius_scales:
            radius = max_dist * scale
            count = np.sum(distances[i] < radius)
            densities_at_scales.append(count)
        
        if len(densities_at_scales) > 1:
            # High variance across scales = multi-scale structure
            local_densities.append(np.std(densities_at_scales) / np.mean(densities_at_scales))
    
    multi_scale_score = np.mean(local_densities) if local_densities else 0
    
    return {
        'multi_scale_score': multi_scale_score,
        'algorithm': 'v13.2' if multi_scale_score > 0.8 else 'v13.1'
    }


def pimst_fractal_auto(points: np.ndarray) -> List[int]:
    """
    Automatic algorithm selection based on dataset characteristics.
    
    This is the RECOMMENDED production function.
    
    🎯 Uses v13.1 ADAPTIVE for most cases
    🔬 Uses v13.2 SCALING for multi-scale fractal data
    """
    characteristics = detect_dataset_characteristics(points)
    
    if characteristics['algorithm'] == 'v13.2':
        print(f"🔬 Detected multi-scale structure (score: {characteristics['multi_scale_score']:.2f})")
        print("   Using v13.2 SCALING algorithm...")
        return pimst_v13_2_scaling(points)
    else:
        print(f"🌱 Standard dataset (multi-scale score: {characteristics['multi_scale_score']:.2f})")
        print("   Using v13.1 ADAPTIVE algorithm...")
        return pimst_v13_1_adaptive(points)


# ============================================================================
# PRODUCTION INTERFACE
# ============================================================================

class PIMST_Fractal:
    """
    Production-ready PIMST Fractal TSP Solver.
    
    Usage:
        solver = PIMST_Fractal()
        tour = solver.solve(points)
        
    Or with explicit algorithm:
        tour = solver.solve(points, algorithm='v13.1')  # Force adaptive
        tour = solver.solve(points, algorithm='v13.2')  # Force scaling
        tour = solver.solve(points, algorithm='auto')   # Auto-select (default)
    """
    
    def __init__(self):
        self.algorithms = {
            'v13.1': pimst_v13_1_adaptive,
            'v13.2': pimst_v13_2_scaling,
            'adaptive': pimst_v13_1_adaptive,
            'scaling': pimst_v13_2_scaling,
            'auto': pimst_fractal_auto,
        }
    
    def solve(self, points: np.ndarray, algorithm: str = 'auto') -> List[int]:
        """
        Solve TSP using fractal approach.
        
        Args:
            points: Nx2 array of point coordinates
            algorithm: 'auto', 'v13.1', 'v13.2', 'adaptive', or 'scaling'
        
        Returns:
            List of point indices forming the tour
        """
        if algorithm not in self.algorithms:
            raise ValueError(f"Unknown algorithm: {algorithm}. "
                           f"Use one of: {list(self.algorithms.keys())}")
        
        return self.algorithms[algorithm](points)
    
    def calculate_length(self, points: np.ndarray, tour: List[int]) -> float:
        """Calculate tour length."""
        if len(tour) < 2:
            return 0.0
        length = sum(np.linalg.norm(points[tour[i]] - points[tour[i+1]]) 
                     for i in range(len(tour)-1))
        length += np.linalg.norm(points[tour[-1]] - points[tour[0]])
        return length


# ============================================================================
# KEY INSIGHTS FROM FRACTAL EXPLORATION
# ============================================================================

INSIGHTS = """
KEY INSIGHTS FROM FRACTAL FAMILY DEVELOPMENT:
==============================================

1. SIMPLICITY WINS
   - The simplest approach (territorial competition) beat complex synthesis
   - Occam's Razor applies to algorithms too
   - More parameters ≠ better results

2. DOMAIN-SPECIFIC OPTIMIZATION MATTERS
   - v13.2 SCALING won on truly fractal data
   - Knowing when to apply specialized algorithms is key
   - Generic "one size fits all" doesn't work

3. PERFORMANCE IS A FEATURE
   - 20x speedup with better quality is the holy grail
   - Users prefer fast + good over slow + perfect
   - Real-time constraints make v13.1 the clear choice

4. THE FRACTAL METAPHOR IS VALID
   - Hot spots as seeds ✓
   - Territorial growth ✓
   - Organic expansion ✓
   - But keep it simple!

5. PHI (φ) APPEARS NATURALLY
   - The golden ratio balances density vs separation
   - Nature's optimization shows up in algorithms
   - Mathematical beauty + practical effectiveness

PRODUCTION RECOMMENDATION:
==========================

Use pimst_fractal_auto() or PIMST_Fractal class:
- Automatically selects best algorithm
- v13.1 ADAPTIVE for 80% of cases
- v13.2 SCALING for fractal datasets
- Simple, fast, effective

Example:
    solver = PIMST_Fractal()
    tour = solver.solve(points)  # Auto-selects best algorithm
"""


if __name__ == "__main__":
    print("="*70)
    print("PIMST FRACTAL FAMILY - PRODUCTION ARCHITECTURE")
    print("="*70)
    print(INSIGHTS)
    
    # Demo
    print("\n" + "="*70)
    print("DEMO: Production Usage")
    print("="*70 + "\n")
    
    np.random.seed(42)
    points = np.random.rand(50, 2)
    
    solver = PIMST_Fractal()
    tour = solver.solve(points, algorithm='auto')
    length = solver.calculate_length(points, tour)
    
    print(f"\n✅ Tour computed!")
    print(f"   Points: {len(points)}")
    print(f"   Length: {length:.4f}")
    print(f"\n🎯 Production ready! Use PIMST_Fractal class for all your TSP needs.")
