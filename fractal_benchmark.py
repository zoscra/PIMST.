#!/usr/bin/env python3
"""
FRACTAL FAMILY BENCHMARK
=========================
Compare all four fractal approaches:
- v13.1 ADAPTIVE: Territorial competition
- v13.2 SCALING: Variable fractal dimension
- v13.3 WAVEFRONT: Wave expansion
- v13.4 SYNTHESIS: All three combined

Test on multiple dataset types to see which works best when.
"""

import numpy as np
import time
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt

# Import all versions
from pimst_v13_1_adaptive import pimst_v13_1_adaptive
from pimst_v13_2_scaling import pimst_v13_2_scaling
from pimst_v13_3_wavefront import pimst_v13_3_wavefront
from pimst_v13_4_synthesis import pimst_v13_4_synthesis


def calculate_tour_length(points: np.ndarray, tour: List[int]) -> float:
    """Calculate total tour length."""
    if len(tour) < 2:
        return 0.0
    length = sum(np.linalg.norm(points[tour[i]] - points[tour[i+1]]) 
                 for i in range(len(tour)-1))
    length += np.linalg.norm(points[tour[-1]] - points[tour[0]])
    return length


def generate_datasets(n: int = 100, seed: int = 42) -> Dict[str, np.ndarray]:
    """
    Generate different types of datasets to test fractal behavior.
    
    Dataset types:
    1. Random: Uniform random points
    2. Clustered: Multiple dense clusters
    3. Grid: Regular grid pattern
    4. Spiral: Spiral pattern (fractal-like)
    5. Multi-scale: Clusters at different scales
    """
    np.random.seed(seed)
    datasets = {}
    
    # 1. Random uniform
    datasets['random'] = np.random.rand(n, 2)
    
    # 2. Clustered
    n_clusters = 5
    points_per_cluster = n // n_clusters
    clustered = []
    for i in range(n_clusters):
        center = np.random.rand(2)
        cluster = np.random.randn(points_per_cluster, 2) * 0.1 + center
        clustered.append(cluster)
    datasets['clustered'] = np.vstack(clustered)
    
    # 3. Grid
    side = int(np.sqrt(n))
    x = np.linspace(0, 1, side)
    y = np.linspace(0, 1, side)
    xx, yy = np.meshgrid(x, y)
    datasets['grid'] = np.column_stack([xx.ravel()[:n], yy.ravel()[:n]])
    
    # 4. Spiral (fractal-like)
    theta = np.linspace(0, 4*np.pi, n)
    r = np.linspace(0, 1, n)
    x = r * np.cos(theta) * 0.5 + 0.5
    y = r * np.sin(theta) * 0.5 + 0.5
    datasets['spiral'] = np.column_stack([x, y])
    
    # 5. Multi-scale (fractal structure)
    multi_scale = []
    # Large cluster
    multi_scale.append(np.random.randn(n//2, 2) * 0.15 + [0.3, 0.3])
    # Medium clusters
    for _ in range(3):
        center = np.random.rand(2) * 0.4 + [0.4, 0.4]
        multi_scale.append(np.random.randn(n//8, 2) * 0.05 + center)
    # Small clusters
    for _ in range(5):
        center = np.random.rand(2) * 0.6 + [0.2, 0.2]
        multi_scale.append(np.random.randn(n//20, 2) * 0.02 + center)
    datasets['multi_scale'] = np.vstack(multi_scale)[:n]
    
    return datasets


def benchmark_algorithm(algo_func, algo_name: str, points: np.ndarray) -> Dict:
    """
    Benchmark a single algorithm on a dataset.
    
    Returns metrics: time, length, quality score.
    """
    try:
        start_time = time.time()
        tour = algo_func(points)
        elapsed = time.time() - start_time
        
        if not tour or len(tour) != len(points):
            return {
                'success': False,
                'time': elapsed,
                'length': float('inf'),
                'error': 'Invalid tour'
            }
        
        length = calculate_tour_length(points, tour)
        
        return {
            'success': True,
            'time': elapsed,
            'length': length,
            'tour': tour
        }
    except Exception as e:
        return {
            'success': False,
            'time': 0,
            'length': float('inf'),
            'error': str(e)
        }


def run_benchmark(n_points: int = 100, seed: int = 42):
    """
    Run comprehensive benchmark across all algorithms and datasets.
    """
    print("🌀" + "="*70 + "🌀")
    print("           FRACTAL FAMILY BENCHMARK")
    print("🌀" + "="*70 + "🌀\n")
    
    algorithms = {
        'v13.1 ADAPTIVE': pimst_v13_1_adaptive,
        'v13.2 SCALING': pimst_v13_2_scaling,
        'v13.3 WAVEFRONT': pimst_v13_3_wavefront,
        'v13.4 SYNTHESIS': pimst_v13_4_synthesis,
    }
    
    datasets = generate_datasets(n_points, seed)
    
    results = {algo: {} for algo in algorithms.keys()}
    
    for dataset_name, points in datasets.items():
        print(f"\n📊 Testing on: {dataset_name.upper()} ({len(points)} points)")
        print("-" * 70)
        
        for algo_name, algo_func in algorithms.items():
            print(f"   {algo_name}...", end=' ', flush=True)
            result = benchmark_algorithm(algo_func, algo_name, points)
            results[algo_name][dataset_name] = result
            
            if result['success']:
                print(f"✅ {result['length']:.4f} ({result['time']:.3f}s)")
            else:
                print(f"❌ {result.get('error', 'Failed')}")
    
    # Summary
    print("\n" + "="*70)
    print("📈 SUMMARY")
    print("="*70)
    
    for algo_name in algorithms.keys():
        print(f"\n{algo_name}:")
        wins = 0
        total_time = 0
        successful = 0
        
        for dataset_name in datasets.keys():
            result = results[algo_name][dataset_name]
            if result['success']:
                successful += 1
                total_time += result['time']
                
                # Check if this algo won on this dataset
                lengths = [results[a][dataset_name]['length'] 
                          for a in algorithms.keys() 
                          if results[a][dataset_name]['success']]
                if lengths and result['length'] == min(lengths):
                    wins += 1
                    print(f"   🏆 Won on {dataset_name}: {result['length']:.4f}")
        
        print(f"   Total wins: {wins}/{len(datasets)}")
        print(f"   Avg time: {total_time/max(successful,1):.3f}s")
        print(f"   Success rate: {successful}/{len(datasets)}")
    
    # Best algorithm recommendation
    print("\n" + "="*70)
    print("🎯 RECOMMENDATIONS")
    print("="*70)
    
    algo_scores = {}
    for algo_name in algorithms.keys():
        score = sum(1 for dataset_name in datasets.keys()
                   if results[algo_name][dataset_name]['success'] and
                   results[algo_name][dataset_name]['length'] == 
                   min(results[a][dataset_name]['length'] 
                       for a in algorithms.keys() 
                       if results[a][dataset_name]['success']))
        algo_scores[algo_name] = score
    
    best_algo = max(algo_scores.items(), key=lambda x: x[1])
    print(f"\n🏆 BEST OVERALL: {best_algo[0]} ({best_algo[1]} wins)\n")
    
    # Dataset-specific recommendations
    print("📌 Best for each dataset type:")
    for dataset_name in datasets.keys():
        best_for_dataset = min(
            [(algo, results[algo][dataset_name]['length']) 
             for algo in algorithms.keys() 
             if results[algo][dataset_name]['success']],
            key=lambda x: x[1]
        )
        print(f"   {dataset_name}: {best_for_dataset[0]} ({best_for_dataset[1]:.4f})")
    
    return results


def visualize_results(results: Dict, datasets: Dict):
    """
    Create visualization of results.
    """
    print("\n📊 Creating visualization...")
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('Fractal Family Performance Comparison', fontsize=16, fontweight='bold')
    
    dataset_names = list(datasets.keys())
    algo_names = list(results.keys())
    
    # Plot tour lengths for each dataset
    for idx, dataset_name in enumerate(dataset_names):
        ax = axes[idx // 3, idx % 3]
        
        lengths = [results[algo][dataset_name]['length'] 
                  for algo in algo_names
                  if results[algo][dataset_name]['success']]
        labels = [algo for algo in algo_names 
                 if results[algo][dataset_name]['success']]
        
        if lengths:
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A'][:len(lengths)]
            bars = ax.bar(range(len(lengths)), lengths, color=colors, alpha=0.7)
            ax.set_xticks(range(len(lengths)))
            ax.set_xticklabels([l.split()[0] for l in labels], rotation=45, ha='right')
            ax.set_ylabel('Tour Length')
            ax.set_title(f'{dataset_name.upper()}')
            ax.grid(axis='y', alpha=0.3)
            
            # Highlight best
            min_length = min(lengths)
            for i, length in enumerate(lengths):
                if length == min_length:
                    bars[i].set_edgecolor('gold')
                    bars[i].set_linewidth(3)
    
    plt.tight_layout()
    plt.savefig('/mnt/user-data/outputs/fractal_benchmark.png', dpi=150, bbox_inches='tight')
    print("✅ Visualization saved!")


if __name__ == "__main__":
    # Run benchmark
    results = run_benchmark(n_points=100, seed=42)
    
    # Generate datasets for visualization
    datasets = generate_datasets(100, 42)
    
    # Visualize
    visualize_results(results, datasets)
    
    print("\n✨ Fractal family benchmark complete! ✨\n")
