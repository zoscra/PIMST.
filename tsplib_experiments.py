"""
TSPLIB Experiments for PIMST
=============================

This script runs comprehensive experiments on TSPLIB instances
and generates tables/figures for publication.

Usage:
    python tsplib_experiments.py --instances berlin52 eil76 kroA100
    python tsplib_experiments.py --all  # Run all instances
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import time
from pathlib import Path
from pimst import PIMST, nearest_neighbor


class TSPLIBParser:
    """Parser for TSPLIB format files"""
    
    @staticmethod
    def parse(filename: str) -> np.ndarray:
        """
        Parse TSPLIB .tsp file
        
        Parameters
        ----------
        filename : str
            Path to .tsp file
        
        Returns
        -------
        cities : np.ndarray
            Array of city coordinates
        """
        with open(filename, 'r') as f:
            lines = f.readlines()
        
        # Find coordinate section
        start_reading = False
        coords = []
        
        for line in lines:
            line = line.strip()
            
            if 'NODE_COORD_SECTION' in line:
                start_reading = True
                continue
            
            if 'EOF' in line or line == '':
                break
            
            if start_reading:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        idx = int(parts[0])
                        x = float(parts[1])
                        y = float(parts[2])
                        coords.append([x, y])
                    except ValueError:
                        continue
        
        return np.array(coords)


# TSPLIB instances with known optima
TSPLIB_INSTANCES = {
    'berlin52': {'n': 52, 'optimal': 7542},
    'eil76': {'n': 76, 'optimal': 538},
    'kroA100': {'n': 100, 'optimal': 21282},
    'ch150': {'n': 150, 'optimal': 6528},
    'd198': {'n': 198, 'optimal': 15780},
    'lin318': {'n': 318, 'optimal': 42029},
    'pcb442': {'n': 442, 'optimal': 50778},
}


def run_single_experiment(cities: np.ndarray, instance_name: str, 
                         optimal: float, n_runs: int = 10) -> dict:
    """
    Run experiment on single instance
    
    Parameters
    ----------
    cities : np.ndarray
        City coordinates
    instance_name : str
        Name of instance
    optimal : float
        Known optimal distance
    n_runs : int
        Number of independent runs
    
    Returns
    -------
    results : dict
        Experimental results
    """
    print(f"\n{'='*70}")
    print(f"Instance: {instance_name} (n={len(cities)})")
    print(f"Known optimal: {optimal}")
    print(f"{'='*70}")
    
    # Run PIMST multiple times
    pimst_distances = []
    pimst_times = []
    
    print(f"\nRunning PIMST ({n_runs} runs)...")
    for run in range(n_runs):
        # Use different random seed for starting point selection
        np.random.seed(42 + run)
        
        solver = PIMST(cities, alpha=0.5, k_starts=8)
        tour, distance, stats = solver.solve(verbose=False)
        
        pimst_distances.append(distance)
        pimst_times.append(stats['time'])
        
        print(f"  Run {run+1}: {distance:.2f} ({stats['time']:.3f}s)")
    
    # Run Nearest Neighbor multiple times (different starts)
    nn_distances = []
    nn_times = []
    
    print(f"\nRunning Nearest Neighbor ({n_runs} runs)...")
    for run in range(n_runs):
        start_city = run % len(cities)
        
        start_time = time.time()
        tour, distance = nearest_neighbor(cities, start=start_city)
        elapsed = time.time() - start_time
        
        nn_distances.append(distance)
        nn_times.append(elapsed)
        
        print(f"  Run {run+1}: {distance:.2f} ({elapsed:.3f}s)")
    
    # Compute statistics
    results = {
        'instance': instance_name,
        'n': len(cities),
        'optimal': optimal,
        
        # PIMST results
        'pimst_best': np.min(pimst_distances),
        'pimst_mean': np.mean(pimst_distances),
        'pimst_std': np.std(pimst_distances),
        'pimst_worst': np.max(pimst_distances),
        'pimst_time_mean': np.mean(pimst_times),
        'pimst_gap': ((np.min(pimst_distances) - optimal) / optimal) * 100,
        
        # NN results
        'nn_best': np.min(nn_distances),
        'nn_mean': np.mean(nn_distances),
        'nn_std': np.std(nn_distances),
        'nn_worst': np.max(nn_distances),
        'nn_time_mean': np.mean(nn_times),
        'nn_gap': ((np.min(nn_distances) - optimal) / optimal) * 100,
        
        # Comparison
        'improvement': ((np.mean(nn_distances) - np.mean(pimst_distances)) / 
                       np.mean(nn_distances)) * 100,
    }
    
    # Print summary
    print(f"\n{'='*70}")
    print("RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"PIMST:")
    print(f"  Best:    {results['pimst_best']:.2f} (gap: {results['pimst_gap']:.2f}%)")
    print(f"  Mean:    {results['pimst_mean']:.2f} ± {results['pimst_std']:.2f}")
    print(f"  Time:    {results['pimst_time_mean']:.3f}s")
    print(f"\nNearest Neighbor:")
    print(f"  Best:    {results['nn_best']:.2f} (gap: {results['nn_gap']:.2f}%)")
    print(f"  Mean:    {results['nn_mean']:.2f} ± {results['nn_std']:.2f}")
    print(f"  Time:    {results['nn_time_mean']:.3f}s")
    print(f"\nImprovement: {results['improvement']:.2f}%")
    print(f"{'='*70}")
    
    return results


def run_all_experiments(instances: list, data_dir: str = './tsplib_data',
                       n_runs: int = 10) -> pd.DataFrame:
    """
    Run experiments on multiple instances
    
    Parameters
    ----------
    instances : list
        List of instance names to run
    data_dir : str
        Directory containing TSPLIB files
    n_runs : int
        Number of runs per instance
    
    Returns
    -------
    results_df : pd.DataFrame
        Results for all instances
    """
    results = []
    
    for instance_name in instances:
        if instance_name not in TSPLIB_INSTANCES:
            print(f"Warning: Unknown instance {instance_name}, skipping")
            continue
        
        # Load instance
        filename = f"{data_dir}/{instance_name}.tsp"
        
        try:
            cities = TSPLIBParser.parse(filename)
        except FileNotFoundError:
            print(f"Error: File {filename} not found, skipping")
            print(f"Download from: http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/")
            continue
        
        # Run experiment
        result = run_single_experiment(
            cities, 
            instance_name,
            TSPLIB_INSTANCES[instance_name]['optimal'],
            n_runs
        )
        results.append(result)
    
    # Create dataframe
    df = pd.DataFrame(results)
    
    return df


def generate_latex_table(df: pd.DataFrame, output_file: str = 'results_table.tex'):
    """Generate LaTeX table for paper"""
    
    latex = r"""
\begin{table}[t]
\centering
\caption{Experimental results on TSPLIB instances. Results show mean ± std over 10 runs.}
\label{tab:results}
\begin{tabular}{lrrrrr}
\hline
\textbf{Instance} & \textbf{n} & \textbf{Optimal} & \textbf{PIMST} & \textbf{NN} & \textbf{Gap (\%)} \\
\hline
"""
    
    for _, row in df.iterrows():
        latex += f"{row['instance']} & "
        latex += f"{row['n']} & "
        latex += f"{row['optimal']:.0f} & "
        latex += f"{row['pimst_mean']:.0f} $\\pm$ {row['pimst_std']:.0f} & "
        latex += f"{row['nn_mean']:.0f} $\\pm$ {row['nn_std']:.0f} & "
        latex += f"{row['pimst_gap']:.2f} \\\\\n"
    
    latex += r"""\hline
\end{tabular}
\end{table}
"""
    
    with open(output_file, 'w') as f:
        f.write(latex)
    
    print(f"\n✅ LaTeX table saved to {output_file}")


def plot_results(df: pd.DataFrame, output_file: str = 'results_plot.png'):
    """Generate comparison plots"""
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Plot 1: Comparison with optimal
    ax1 = axes[0]
    x = np.arange(len(df))
    width = 0.35
    
    ax1.bar(x - width/2, df['pimst_gap'], width, label='PIMST', color='gold')
    ax1.bar(x + width/2, df['nn_gap'], width, label='NN', color='lightblue')
    
    ax1.set_xlabel('Instance', fontsize=12)
    ax1.set_ylabel('Gap from Optimal (%)', fontsize=12)
    ax1.set_title('Solution Quality', fontsize=13, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(df['instance'], rotation=45, ha='right')
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)
    
    # Plot 2: Time comparison
    ax2 = axes[1]
    
    ax2.bar(x - width/2, df['pimst_time_mean'], width, label='PIMST', color='gold')
    ax2.bar(x + width/2, df['nn_time_mean'], width, label='NN', color='lightblue')
    
    ax2.set_xlabel('Instance', fontsize=12)
    ax2.set_ylabel('Time (seconds)', fontsize=12)
    ax2.set_title('Computational Time', fontsize=13, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(df['instance'], rotation=45, ha='right')
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)
    ax2.set_yscale('log')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Plot saved to {output_file}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Run TSPLIB experiments')
    parser.add_argument('--instances', nargs='+', 
                       help='Specific instances to run')
    parser.add_argument('--all', action='store_true',
                       help='Run all available instances')
    parser.add_argument('--data-dir', default='./tsplib_data',
                       help='Directory with TSPLIB files')
    parser.add_argument('--runs', type=int, default=10,
                       help='Number of runs per instance')
    parser.add_argument('--output-dir', default='./results',
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    # Determine which instances to run
    if args.all:
        instances = list(TSPLIB_INSTANCES.keys())
    elif args.instances:
        instances = args.instances
    else:
        # Default: run small to medium instances
        instances = ['berlin52', 'eil76', 'kroA100', 'ch150']
    
    print(f"Running experiments on: {', '.join(instances)}")
    print(f"Number of runs per instance: {args.runs}")
    
    # Create output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    # Run experiments
    results_df = run_all_experiments(instances, args.data_dir, args.runs)
    
    # Save results
    csv_file = f"{args.output_dir}/results.csv"
    results_df.to_csv(csv_file, index=False)
    print(f"\n✅ Results saved to {csv_file}")
    
    # Generate LaTeX table
    latex_file = f"{args.output_dir}/results_table.tex"
    generate_latex_table(results_df, latex_file)
    
    # Generate plots
    plot_file = f"{args.output_dir}/results_plot.png"
    plot_results(results_df, plot_file)
    
    print(f"\n{'='*70}")
    print("EXPERIMENTS COMPLETED")
    print(f"{'='*70}")
    print(f"Results directory: {args.output_dir}/")
    print("Files generated:")
    print(f"  - results.csv (raw data)")
    print(f"  - results_table.tex (for paper)")
    print(f"  - results_plot.png (figure for paper)")


if __name__ == "__main__":
    main()
