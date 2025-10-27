"""
TEST EXHAUSTIVO - PIMST v7.0 GOLDEN NEEDLE
==========================================

Buscar el balance óptimo entre:
1. Distancia vs Guía del campo
2. Estructura Local vs Global
3. Coherencia direccional

"La aguja dorada no es brillante - es SUTIL"
Debemos encontrarla mediante experimentación rigurosa.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist
import time
import itertools

# Importar funciones base
from pimst_v7_golden_needle import (
    find_intersections_sample, 
    nearest_neighbor, 
    tour_length,
    GOLDEN_ANGLE, PHI
)

# ============================================================================
# VERSIÓN PARAMETRIZABLE DE V7.0
# ============================================================================

def create_smooth_potential_field_param(cities, visited_mask, intersections, 
                                        global_center, global_radius,
                                        local_weight=0.7):
    """
    Campo de potenciales con balance LOCAL-GLOBAL parametrizable.
    
    Args:
        local_weight: Peso de estructura local (0-1)
                     El resto (1-local_weight) es estructura global
    """
    n = len(cities)
    unvisited = cities[~visited_mask]
    
    if len(unvisited) == 0:
        return None
    
    # COMPONENTE LOCAL: Densidad de intersecciones
    if len(intersections) > 0:
        bandwidth = np.std(cities) / PHI
        
        local_potentials = []
        for city in unvisited:
            distances = np.linalg.norm(intersections - city, axis=1)
            density = np.sum(np.exp(-distances**2 / (2 * bandwidth**2)))
            local_potentials.append(density)
        
        local_potentials = np.array(local_potentials)
        if local_potentials.max() > 0:
            local_potentials = local_potentials / local_potentials.max()
    else:
        local_potentials = np.zeros(len(unvisited))
    
    # COMPONENTE GLOBAL: Estructura suave
    global_potentials = []
    for city in unvisited:
        dist_to_center = np.linalg.norm(city - global_center)
        global_potential = np.exp(-(dist_to_center / global_radius)**2)
        global_potentials.append(global_potential)
    
    global_potentials = np.array(global_potentials)
    if global_potentials.max() > 0:
        global_potentials = global_potentials / global_potentials.max()
    
    # Balance parametrizable
    global_weight = 1.0 - local_weight
    combined_potential = local_weight * local_potentials + global_weight * global_potentials
    
    return combined_potential

def compute_smooth_guide_param(current_city, candidate_city, 
                               combined_potential, unvisited, 
                               prev_direction=None,
                               direction_weight=0.2):
    """
    Guía suave con peso de dirección parametrizable.
    
    Args:
        direction_weight: Peso de coherencia direccional (0-1)
    """
    idx = np.where(np.all(unvisited == candidate_city, axis=1))[0]
    if len(idx) == 0:
        return 0.0
    
    potential_value = combined_potential[idx[0]]
    
    direction_bonus = 0.0
    if prev_direction is not None:
        current_direction = candidate_city - current_city
        current_direction = current_direction / (np.linalg.norm(current_direction) + 1e-10)
        
        direction_bonus = np.dot(current_direction, prev_direction)
        direction_bonus = (direction_bonus + 1) / 2
    
    # Balance parametrizable
    potential_weight = 1.0 - direction_weight
    guide = potential_weight * potential_value + direction_weight * direction_bonus
    
    return guide

def tsp_golden_needle_param(cities, start_idx, params):
    """
    PIMST v7.0 con parámetros ajustables.
    
    Args:
        params: dict con 'dist_weight', 'local_weight', 'direction_weight'
    """
    n = len(cities)
    visited = np.zeros(n, dtype=bool)
    tour = [start_idx]
    visited[start_idx] = True
    current_city = cities[start_idx]
    
    dist_weight = params['dist_weight']
    guide_weight = 1.0 - dist_weight
    local_weight = params['local_weight']
    direction_weight = params['direction_weight']
    
    global_center = np.mean(cities, axis=0)
    global_radius = np.mean(np.linalg.norm(cities - global_center, axis=1))
    intersections = find_intersections_sample(cities)
    
    prev_direction = None
    
    for step in range(n - 1):
        potential_field = create_smooth_potential_field_param(
            cities, visited, intersections, global_center, global_radius,
            local_weight=local_weight
        )
        
        unvisited_mask = ~visited
        unvisited_cities = cities[unvisited_mask]
        distances = np.linalg.norm(unvisited_cities - current_city, axis=1)
        
        guides = np.array([
            compute_smooth_guide_param(current_city, candidate, 
                                      potential_field, unvisited_cities, prev_direction,
                                      direction_weight=direction_weight)
            for candidate in unvisited_cities
        ])
        
        # Función objetivo parametrizable
        normalized_distances = distances / (distances.max() + 1e-10)
        scores = dist_weight * normalized_distances - guide_weight * guides
        
        best_idx_local = np.argmin(scores)
        best_idx_global = np.where(unvisited_mask)[0][best_idx_local]
        
        next_city = cities[best_idx_global]
        tour.append(best_idx_global)
        visited[best_idx_global] = True
        
        new_direction = next_city - current_city
        new_direction = new_direction / (np.linalg.norm(new_direction) + 1e-10)
        
        if prev_direction is not None:
            alpha = 0.6
            prev_direction = alpha * new_direction + (1 - alpha) * prev_direction
            prev_direction = prev_direction / (np.linalg.norm(prev_direction) + 1e-10)
        else:
            prev_direction = new_direction
        
        current_city = next_city
    
    return tour

def pimst_v7_param(cities, k, params):
    """Multi-start con parámetros."""
    n = len(cities)
    best_tour = None
    best_length = float('inf')
    
    angles = [i * GOLDEN_ANGLE for i in range(k)]
    centroid = np.mean(cities, axis=0)
    radius = np.mean(np.linalg.norm(cities - centroid, axis=1))
    
    for angle in angles:
        start_point = centroid + radius * np.array([np.cos(angle), np.sin(angle)])
        start_idx = np.argmin(np.linalg.norm(cities - start_point, axis=1))
        
        tour = tsp_golden_needle_param(cities, start_idx, params)
        length = tour_length(cities, tour)
        
        if length < best_length:
            best_length = length
            best_tour = tour
    
    return best_tour, best_length

# ============================================================================
# GENERACIÓN DE PROBLEMAS DE PRUEBA
# ============================================================================

def generate_test_problems():
    """Genera 5 tipos de distribuciones diferentes."""
    np.random.seed(42)
    problems = {}
    
    # 1. Clusters densos
    centers = np.random.uniform(-5, 5, (4, 2))
    cities = []
    for center in centers:
        cluster = np.random.randn(12, 2) * 0.6 + center
        cities.extend(cluster)
    problems['clusters_densos'] = np.array(cities[:50])
    
    # 2. Uniforme
    problems['uniforme'] = np.random.uniform(-10, 10, (50, 2))
    
    # 3. Anillo
    angles = np.linspace(0, 2*np.pi, 50, endpoint=False)
    radius = 5 + np.random.randn(50) * 0.5
    problems['anillo'] = np.column_stack([
        radius * np.cos(angles),
        radius * np.sin(angles)
    ])
    
    # 4. Mix (algunos clusters + algunos dispersos)
    centers = np.random.uniform(-5, 5, (3, 2))
    cities = []
    for center in centers:
        cluster = np.random.randn(12, 2) * 0.8 + center
        cities.extend(cluster)
    # Añadir dispersos
    dispersed = np.random.uniform(-8, 8, (14, 2))
    cities.extend(dispersed)
    problems['mix'] = np.array(cities[:50])
    
    # 5. Dos grupos separados
    group1 = np.random.randn(25, 2) * 1.5 + np.array([-5, 0])
    group2 = np.random.randn(25, 2) * 1.5 + np.array([5, 0])
    problems['dos_grupos'] = np.vstack([group1, group2])
    
    return problems

# ============================================================================
# EXPLORACIÓN DEL ESPACIO DE PARÁMETROS
# ============================================================================

def grid_search_optimal_balance():
    """
    Búsqueda exhaustiva del balance óptimo.
    
    Explora:
    - dist_weight: [0.5, 0.6, 0.7, 0.8, 0.9]
    - local_weight: [0.3, 0.5, 0.7, 0.9]
    - direction_weight: [0.1, 0.2, 0.3]
    """
    print("="*80)
    print("BÚSQUEDA DE LA AGUJA DORADA")
    print("="*80)
    print()
    print("Explorando espacio de parámetros...")
    print()
    
    # Generar problemas
    problems = generate_test_problems()
    
    # Grilla de parámetros
    dist_weights = [0.5, 0.6, 0.7, 0.8, 0.9]
    local_weights = [0.3, 0.5, 0.7, 0.9]
    direction_weights = [0.1, 0.2, 0.3]
    
    total_configs = len(dist_weights) * len(local_weights) * len(direction_weights)
    print(f"Configuraciones a probar: {total_configs}")
    print(f"Problemas de prueba: {len(problems)}")
    print(f"Total de evaluaciones: {total_configs * len(problems)}")
    print()
    
    results = []
    config_num = 0
    
    for dist_w in dist_weights:
        for local_w in local_weights:
            for dir_w in direction_weights:
                config_num += 1
                params = {
                    'dist_weight': dist_w,
                    'local_weight': local_w,
                    'direction_weight': dir_w
                }
                
                improvements = []
                
                for prob_name, cities in problems.items():
                    # Baseline
                    tour_nn = nearest_neighbor(cities)
                    length_nn = tour_length(cities, tour_nn)
                    
                    # v7.0 con estos parámetros
                    tour_v7, length_v7 = pimst_v7_param(cities, k=6, params=params)
                    
                    improvement = ((length_nn - length_v7) / length_nn) * 100
                    improvements.append(improvement)
                
                avg_improvement = np.mean(improvements)
                
                results.append({
                    'config': config_num,
                    'dist_weight': dist_w,
                    'local_weight': local_w,
                    'direction_weight': dir_w,
                    'avg_improvement': avg_improvement,
                    'improvements': improvements
                })
                
                # Mostrar progreso cada 10 configs
                if config_num % 10 == 0:
                    print(f"  [{config_num}/{total_configs}] Mejor hasta ahora: {max(r['avg_improvement'] for r in results):.2f}%")
    
    print()
    print("✓ Exploración completada")
    print()
    
    # Ordenar por mejor mejora promedio
    results.sort(key=lambda x: x['avg_improvement'], reverse=True)
    
    return results, problems

def visualize_results(results, problems):
    """Visualiza los resultados de la búsqueda."""
    
    # Top 10 configuraciones
    top10 = results[:10]
    
    fig = plt.figure(figsize=(20, 12))
    
    # 1. Mejora promedio de top 10 configs
    ax1 = plt.subplot(2, 3, 1)
    config_labels = [f"#{r['config']}" for r in top10]
    improvements = [r['avg_improvement'] for r in top10]
    bars = ax1.barh(config_labels, improvements, color='gold', edgecolor='darkgoldenrod', linewidth=2)
    
    # Colorear según mejora
    for i, bar in enumerate(bars):
        if improvements[i] > 5:
            bar.set_color('darkgreen')
        elif improvements[i] > 0:
            bar.set_color('gold')
        else:
            bar.set_color('salmon')
    
    ax1.axvline(0, color='red', linestyle='--', linewidth=2, alpha=0.7)
    ax1.set_xlabel('Mejora Promedio (%)', fontweight='bold')
    ax1.set_title('Top 10 Configuraciones', fontsize=12, fontweight='bold')
    ax1.grid(axis='x', alpha=0.3)
    
    # 2. Parámetros de la mejor configuración
    ax2 = plt.subplot(2, 3, 2)
    best = top10[0]
    params_names = ['dist_weight', 'local_weight', 'direction_weight']
    params_values = [best['dist_weight'], best['local_weight'], best['direction_weight']]
    
    bars = ax2.bar(params_names, params_values, color=['navy', 'orange', 'green'], 
                   edgecolor='black', linewidth=2, alpha=0.7)
    ax2.set_ylim([0, 1])
    ax2.set_ylabel('Valor del parámetro', fontweight='bold')
    ax2.set_title(f'🎯 AGUJA DORADA (Config #{best["config"]})\n' + 
                 f'Mejora: {best["avg_improvement"]:.2f}%', 
                 fontsize=12, fontweight='bold', color='darkgreen')
    ax2.grid(axis='y', alpha=0.3)
    
    # Añadir valores sobre las barras
    for i, (bar, val) in enumerate(zip(bars, params_values)):
        ax2.text(bar.get_x() + bar.get_width()/2, val + 0.02, 
                f'{val:.2f}', ha='center', va='bottom', fontweight='bold')
    
    # 3. Heatmap: dist_weight vs local_weight
    ax3 = plt.subplot(2, 3, 3)
    
    # Agrupar por dist_weight y local_weight (promediando direction_weight)
    dist_vals = sorted(set(r['dist_weight'] for r in results))
    local_vals = sorted(set(r['local_weight'] for r in results))
    
    heatmap_data = np.zeros((len(dist_vals), len(local_vals)))
    for i, dw in enumerate(dist_vals):
        for j, lw in enumerate(local_vals):
            matching = [r for r in results 
                       if r['dist_weight'] == dw and r['local_weight'] == lw]
            heatmap_data[i, j] = np.mean([r['avg_improvement'] for r in matching])
    
    im = ax3.imshow(heatmap_data, cmap='RdYlGn', aspect='auto', origin='lower')
    ax3.set_xticks(range(len(local_vals)))
    ax3.set_yticks(range(len(dist_vals)))
    ax3.set_xticklabels([f'{v:.1f}' for v in local_vals])
    ax3.set_yticklabels([f'{v:.1f}' for v in dist_vals])
    ax3.set_xlabel('local_weight', fontweight='bold')
    ax3.set_ylabel('dist_weight', fontweight='bold')
    ax3.set_title('Heatmap: Distancia vs Estructura Local', fontsize=11, fontweight='bold')
    plt.colorbar(im, ax=ax3, label='Mejora (%)')
    
    # 4. Mejora por tipo de problema (mejor config)
    ax4 = plt.subplot(2, 3, 4)
    problem_names = list(problems.keys())
    best_improvements = best['improvements']
    
    bars = ax4.bar(problem_names, best_improvements, 
                   color=['green' if x > 0 else 'red' for x in best_improvements],
                   edgecolor='black', linewidth=2, alpha=0.7)
    ax4.axhline(0, color='black', linestyle='-', linewidth=1)
    ax4.set_ylabel('Mejora (%)', fontweight='bold')
    ax4.set_title('Rendimiento por Tipo de Problema\n(Mejor configuración)', 
                 fontsize=11, fontweight='bold')
    ax4.grid(axis='y', alpha=0.3)
    plt.xticks(rotation=45, ha='right')
    
    # Añadir valores sobre las barras
    for bar, val in zip(bars, best_improvements):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2, height,
                f'{val:+.1f}%', ha='center', 
                va='bottom' if height > 0 else 'top',
                fontweight='bold', fontsize=9)
    
    # 5. Distribución de mejoras (todas las configs)
    ax5 = plt.subplot(2, 3, 5)
    all_improvements = [r['avg_improvement'] for r in results]
    ax5.hist(all_improvements, bins=30, color='skyblue', edgecolor='navy', alpha=0.7)
    ax5.axvline(best['avg_improvement'], color='gold', linestyle='--', 
               linewidth=3, label=f'Mejor: {best["avg_improvement"]:.2f}%')
    ax5.axvline(0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Sin mejora')
    ax5.set_xlabel('Mejora Promedio (%)', fontweight='bold')
    ax5.set_ylabel('Frecuencia', fontweight='bold')
    ax5.set_title('Distribución de Todas las Configuraciones', 
                 fontsize=11, fontweight='bold')
    ax5.legend(loc='best')
    ax5.grid(axis='y', alpha=0.3)
    
    # 6. Comparación: Peor vs Mejor config
    ax6 = plt.subplot(2, 3, 6)
    worst = results[-1]
    
    x = np.arange(len(problem_names))
    width = 0.35
    
    bars1 = ax6.bar(x - width/2, worst['improvements'], width, 
                   label=f'Peor Config #{worst["config"]}',
                   color='salmon', edgecolor='darkred', linewidth=1.5, alpha=0.7)
    bars2 = ax6.bar(x + width/2, best['improvements'], width,
                   label=f'Mejor Config #{best["config"]}',
                   color='gold', edgecolor='darkgoldenrod', linewidth=1.5, alpha=0.9)
    
    ax6.axhline(0, color='black', linestyle='-', linewidth=1)
    ax6.set_ylabel('Mejora (%)', fontweight='bold')
    ax6.set_title('Comparación: Peor vs Mejor Configuración', 
                 fontsize=11, fontweight='bold')
    ax6.set_xticks(x)
    ax6.set_xticklabels(problem_names, rotation=45, ha='right')
    ax6.legend(loc='best', fontsize=9)
    ax6.grid(axis='y', alpha=0.3)
    
    plt.suptitle('🔍 BÚSQUEDA DE LA AGUJA DORADA - PIMST v7.0\n' + 
                '"El equilibrio sutil entre estructura y adaptación"',
                fontsize=16, fontweight='bold', y=0.995)
    
    plt.tight_layout()
    return fig

# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    print()
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "  PIMST v7.0 - BÚSQUEDA EXHAUSTIVA DE LA AGUJA DORADA".center(78) + "║")
    print("║" + " "*78 + "║")
    print("║" + "  'En la fina línea donde chocan estructura y adaptación,'".center(78) + "║")
    print("║" + "   hallamos la solución óptima'".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    print()
    
    start_time = time.time()
    
    # Búsqueda exhaustiva
    results, problems = grid_search_optimal_balance()
    
    elapsed = time.time() - start_time
    
    # Mostrar resultados
    print("="*80)
    print("RESULTADOS FINALES")
    print("="*80)
    print()
    
    print("🏆 TOP 5 CONFIGURACIONES:")
    print()
    for i, r in enumerate(results[:5], 1):
        print(f"{i}. Config #{r['config']:3d} - Mejora promedio: {r['avg_improvement']:+.2f}%")
        print(f"   dist_weight={r['dist_weight']:.1f}, " + 
              f"local_weight={r['local_weight']:.1f}, " +
              f"direction_weight={r['direction_weight']:.1f}")
        print()
    
    best = results[0]
    print("="*80)
    print("🎯 LA AGUJA DORADA ENCONTRADA:")
    print("="*80)
    print(f"  Configuración #{best['config']}")
    print(f"  • Peso de distancia:    {best['dist_weight']:.2f}")
    print(f"  • Peso estructura local: {best['local_weight']:.2f}")
    print(f"  • Peso dirección:       {best['direction_weight']:.2f}")
    print()
    print(f"  Mejora promedio: {best['avg_improvement']:+.2f}%")
    print()
    print("  Rendimiento por problema:")
    for prob_name, improvement in zip(problems.keys(), best['improvements']):
        status = "✓" if improvement > 0 else "✗"
        print(f"    {status} {prob_name:20s}: {improvement:+.2f}%")
    print()
    print(f"  Tiempo total: {elapsed:.1f}s")
    print()
    
    # Análisis estadístico
    successful_configs = [r for r in results if r['avg_improvement'] > 0]
    print(f"  Configuraciones exitosas: {len(successful_configs)}/{len(results)} " + 
          f"({len(successful_configs)/len(results)*100:.1f}%)")
    print()
    
    # Visualizar
    print("Generando visualizaciones...")
    fig = visualize_results(results, problems)
    plt.savefig('/home/claude/pimst_v7_parameter_search.png', dpi=150, bbox_inches='tight')
    print("✓ Visualización guardada: pimst_v7_parameter_search.png")
    print()
    
    # Guardar mejor configuración
    import json
    with open('/home/claude/pimst_v7_golden_config.json', 'w') as f:
        json.dump({
            'best_params': {
                'dist_weight': best['dist_weight'],
                'local_weight': best['local_weight'],
                'direction_weight': best['direction_weight']
            },
            'avg_improvement': best['avg_improvement'],
            'improvements_by_problem': dict(zip(problems.keys(), best['improvements']))
        }, f, indent=2)
    print("✓ Configuración óptima guardada: pimst_v7_golden_config.json")
    print()
    
    print("="*80)
    print()
    
    if best['avg_improvement'] > 0:
        print("✨ ¡LA AGUJA DORADA HA SIDO ENCONTRADA! ✨")
        print()
        print(f"El equilibrio sutil logra {best['avg_improvement']:.2f}% de mejora promedio.")
        print()
        print("INTERPRETACIÓN:")
        print(f"  • Distancia domina con {best['dist_weight']*100:.0f}% (no olvidar lo fundamental)")
        print(f"  • Estructura local con {best['local_weight']*100:.0f}% vs " + 
              f"global {(1-best['local_weight'])*100:.0f}%")
        print(f"  • Coherencia direccional sutil: {best['direction_weight']*100:.0f}%")
    else:
        print("⚠️  La aguja dorada es esquiva en este espacio de parámetros")
        print("   Puede requerir un balance aún más fino o diferentes componentes")
    
    print()
    print("="*80)
