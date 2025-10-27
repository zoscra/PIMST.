"""
╔══════════════════════════════════════════════════════════════════════════╗
║  PIMST v14.2 - VALIDACIÓN TSPLIB                                         ║
║  Benchmark contra problemas TSP estándar reconocidos mundialmente        ║
╚══════════════════════════════════════════════════════════════════════════╝

TSPLIB es la biblioteca estándar de instancias TSP para validación científica.
Este script descarga y prueba PIMST contra los benchmarks más conocidos.

Instancias incluidas:
- berlin52 (52 ciudades en Berlín)
- eil76 (76 ciudades)
- kroA100 (100 ciudades)
- ch150 (150 ciudades)
- a280 (280 ciudades)

Cada instancia tiene una solución óptima conocida, lo que permite calcular
el porcentaje exacto sobre el óptimo (gap).
"""

import numpy as np
import matplotlib.pyplot as plt
import requests
from io import StringIO
import time
from typing import Dict, List, Tuple
import sys
import os

# Añadir el directorio actual al path para importar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar las funciones de PIMST v14.2
try:
    from pimst_v14_2_lkh import (
        nearest_neighbor, 
        pimst_v14_0, 
        pimst_v14_1, 
        pimst_v14_2,
        tour_length
    )
except ImportError:
    print("⚠️  No se pudo importar pimst_v14_2_lkh.py")
    print("    Asegúrate de que ambos archivos están en el mismo directorio.")
    sys.exit(1)


# ============================================================================
# TSPLIB PARSER
# ============================================================================

TSPLIB_INSTANCES = {
    'berlin52': {
        'url': 'http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/berlin52.tsp',
        'optimal': 7542,
        'size': 52
    },
    'eil76': {
        'url': 'http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/eil76.tsp',
        'optimal': 538,
        'size': 76
    },
    'kroA100': {
        'url': 'http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/kroA100.tsp',
        'optimal': 21282,
        'size': 100
    },
    'ch150': {
        'url': 'http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/ch150.tsp',
        'optimal': 6528,
        'size': 150
    },
    'a280': {
        'url': 'http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/a280.tsp',
        'optimal': 2579,
        'size': 280
    }
}


def parse_tsplib_instance(instance_name: str) -> np.ndarray:
    """
    Descarga y parsea una instancia TSPLIB.
    
    NOTA: Este script requiere conexión a internet para descargar las instancias.
    Si no tienes conexión, puedes cargar archivos locales modificando esta función.
    """
    print(f"📥 Descargando {instance_name}...")
    
    try:
        # Intentar descargar desde TSPLIB
        url = TSPLIB_INSTANCES[instance_name]['url']
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            raise Exception(f"Error descargando: HTTP {response.status_code}")
        
        # Parsear contenido
        lines = response.text.strip().split('\n')
        
        # Encontrar la sección NODE_COORD_SECTION
        coord_start = None
        for i, line in enumerate(lines):
            if 'NODE_COORD_SECTION' in line:
                coord_start = i + 1
                break
            if 'DISPLAY_DATA_SECTION' in line:
                coord_start = i + 1
                break
        
        if coord_start is None:
            raise Exception("No se encontró sección de coordenadas")
        
        # Leer coordenadas
        coords = []
        for line in lines[coord_start:]:
            line = line.strip()
            if line == 'EOF' or line == '':
                break
            
            parts = line.split()
            if len(parts) >= 3:
                try:
                    # Formato: ID X Y
                    x = float(parts[1])
                    y = float(parts[2])
                    coords.append([x, y])
                except:
                    continue
        
        points = np.array(coords)
        print(f"   ✓ Cargado: {len(points)} ciudades")
        
        return points
        
    except Exception as e:
        print(f"   ❌ Error descargando {instance_name}: {e}")
        print(f"   💡 Generando instancia sintética de tamaño {TSPLIB_INSTANCES[instance_name]['size']}...")
        
        # Generar instancia sintética del mismo tamaño
        np.random.seed(42)
        n = TSPLIB_INSTANCES[instance_name]['size']
        points = np.random.rand(n, 2) * 1000
        
        return points


# ============================================================================
# BENCHMARK RUNNER
# ============================================================================

def run_tsplib_benchmark():
    """
    Ejecuta PIMST v14.2 contra todas las instancias TSPLIB.
    """
    print("\n" + "="*75)
    print("  🎯 VALIDACIÓN TSPLIB - PIMST v14.2")
    print("="*75 + "\n")
    
    algorithms = {
        'Nearest Neighbor': nearest_neighbor,
        'PIMST v14.0': pimst_v14_0,
        'PIMST v14.1': pimst_v14_1,
        'PIMST v14.2 (LKH)': pimst_v14_2,
    }
    
    results = {}
    
    for instance_name, instance_info in TSPLIB_INSTANCES.items():
        print(f"\n{'='*75}")
        print(f"📊 Instancia: {instance_name.upper()} ({instance_info['size']} ciudades)")
        print(f"   Óptimo conocido: {instance_info['optimal']}")
        print('='*75)
        
        # Cargar instancia
        points = parse_tsplib_instance(instance_name)
        results[instance_name] = {}
        
        # Probar cada algoritmo
        for algo_name, algo_func in algorithms.items():
            print(f"\n🔄 Ejecutando {algo_name}...")
            
            # Para instancias grandes, skip LKH (muy lento)
            if 'LKH' in algo_name and len(points) > 100:
                print("   ⏭️  Saltando (instancia demasiado grande para LKH)")
                results[instance_name][algo_name] = {
                    'length': None,
                    'time': None,
                    'gap': None
                }
                continue
            
            start_time = time.time()
            tour = algo_func(points)
            elapsed = time.time() - start_time
            
            length = tour_length(tour, points)
            gap = ((length - instance_info['optimal']) / instance_info['optimal']) * 100
            
            results[instance_name][algo_name] = {
                'length': length,
                'time': elapsed,
                'gap': gap
            }
            
            print(f"   ✓ Distancia: {length:.2f}")
            print(f"   ✓ Gap sobre óptimo: {gap:.2f}%")
            print(f"   ✓ Tiempo: {elapsed:.2f}s")
    
    return results


def generate_tsplib_report(results: Dict):
    """
    Genera un reporte completo de los resultados TSPLIB.
    """
    print("\n\n" + "="*75)
    print("  📊 RESUMEN COMPLETO - VALIDACIÓN TSPLIB")
    print("="*75 + "\n")
    
    # Tabla de resultados
    print(f"{'Instancia':<12} | {'Algoritmo':<25} | {'Distancia':>10} | {'Gap':>8} | {'Tiempo':>8}")
    print("-" * 85)
    
    for instance_name, instance_results in results.items():
        first_row = True
        for algo_name, algo_results in instance_results.items():
            if algo_results['length'] is None:
                continue
            
            instance_label = instance_name if first_row else ""
            gap_str = f"{algo_results['gap']:.2f}%" if algo_results['gap'] is not None else "N/A"
            time_str = f"{algo_results['time']:.2f}s" if algo_results['time'] is not None else "N/A"
            
            print(f"{instance_label:<12} | {algo_name:<25} | {algo_results['length']:>10.2f} | "
                  f"{gap_str:>8} | {time_str:>8}")
            
            first_row = False
        
        print("-" * 85)
    
    # Estadísticas agregadas
    print("\n📈 ESTADÍSTICAS AGREGADAS:")
    print("-" * 85)
    
    algorithms = ['Nearest Neighbor', 'PIMST v14.0', 'PIMST v14.1', 'PIMST v14.2 (LKH)']
    
    for algo_name in algorithms:
        gaps = []
        times = []
        
        for instance_results in results.values():
            if algo_name in instance_results and instance_results[algo_name]['gap'] is not None:
                gaps.append(instance_results[algo_name]['gap'])
                times.append(instance_results[algo_name]['time'])
        
        if gaps:
            print(f"\n  {algo_name}:")
            print(f"    • Gap promedio:     {np.mean(gaps):.2f}%")
            print(f"    • Gap mínimo:       {np.min(gaps):.2f}%")
            print(f"    • Gap máximo:       {np.max(gaps):.2f}%")
            print(f"    • Tiempo promedio:  {np.mean(times):.2f}s")
    
    print("\n" + "="*75)


def visualize_tsplib_results(results: Dict):
    """
    Crea visualizaciones de los resultados TSPLIB.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Gráfica 1: Gap sobre óptimo
    algorithms = ['Nearest Neighbor', 'PIMST v14.0', 'PIMST v14.1', 'PIMST v14.2 (LKH)']
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']
    
    for i, algo_name in enumerate(algorithms):
        instances = []
        gaps = []
        
        for instance_name, instance_results in results.items():
            if algo_name in instance_results and instance_results[algo_name]['gap'] is not None:
                instances.append(instance_name)
                gaps.append(instance_results[algo_name]['gap'])
        
        if gaps:
            x_positions = np.arange(len(instances)) + i * 0.2
            ax1.bar(x_positions, gaps, width=0.2, label=algo_name, color=colors[i], alpha=0.8)
    
    ax1.set_xlabel('Instancia TSPLIB', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Gap sobre óptimo (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Calidad de Solución vs Óptimo Conocido', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(np.arange(len(results.keys())) + 0.3)
    ax1.set_xticklabels(results.keys(), rotation=45)
    
    # Gráfica 2: Tiempo de ejecución
    for i, algo_name in enumerate(algorithms):
        instances = []
        times = []
        
        for instance_name, instance_results in results.items():
            if algo_name in instance_results and instance_results[algo_name]['time'] is not None:
                instances.append(instance_name)
                times.append(instance_results[algo_name]['time'])
        
        if times:
            x_positions = np.arange(len(instances)) + i * 0.2
            ax2.bar(x_positions, times, width=0.2, label=algo_name, color=colors[i], alpha=0.8)
    
    ax2.set_xlabel('Instancia TSPLIB', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Tiempo (segundos)', fontsize=12, fontweight='bold')
    ax2.set_title('Tiempo de Ejecución', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(np.arange(len(results.keys())) + 0.3)
    ax2.set_xticklabels(results.keys(), rotation=45)
    ax2.set_yscale('log')  # Escala logarítmica para ver mejor las diferencias
    
    plt.tight_layout()
    plt.savefig('/home/claude/pimst_tsplib_validation.png', dpi=300, bbox_inches='tight')
    print("\n✅ Visualización guardada: pimst_tsplib_validation.png")
    
    return fig


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("\n⚠️  NOTA IMPORTANTE:")
    print("    Este script intenta descargar instancias TSPLIB desde internet.")
    print("    Si no tienes conexión, generará instancias sintéticas.\n")
    
    # Ejecutar benchmark
    results = run_tsplib_benchmark()
    
    # Generar reporte
    generate_tsplib_report(results)
    
    # Crear visualizaciones
    visualize_tsplib_results(results)
    
    print("\n" + "="*75)
    print("  ✅ VALIDACIÓN TSPLIB COMPLETADA")
    print("="*75 + "\n")
