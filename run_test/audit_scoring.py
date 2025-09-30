from .score_mappings import get_score

def get_score_for_value(attribute: str, value: str) -> int:
    """Map audit response values to numerical scores.
    
    Args:
        attribute: The attribute being scored
        value: The value to convert to a score (can be string or int)
        
    Returns:
        int: The numerical score (0-100)
    """
    # If value is already a number, return it directly
    if isinstance(value, (int, float)):
        return int(value)
        
    # Otherwise, convert string value to score
    return get_score(attribute, value)

def calculate_deviations(results: list[dict]) -> dict:
    """Calculate deviations in scores across cycles for each file and metric."""
    # Group results by filename
    files_data = {}
    for row in results:
        filename = row['filename']
        if filename not in files_data:
            files_data[filename] = []
        files_data[filename].append(row)
    
    deviations = {
        'per_file': {},
        'overall': {
            'metrics': {},
            'total_deviation': 0,
            'avg_total_deviation': 0
        }
    }

    numeric_fields = [
        'readability', 'consistency', 'modularity', 'maintainability', 'reusability',
        'redundancy', 'technical_debt', 'code_smells', 'completeness', 'edge_cases',
        'error_handling', 'efficiency', 'scalability', 'resource_utilization',
        'load_handling', 'parallel_processing', 'database_interaction_efficiency',
        'concurrency_management', 'state_management_efficiency', 'modularity_decoupling',
        'configuration_customization_ease', 'input_validation', 'data_handling',
        'authentication', 'independence', 'integration', 'inline_comments', 'standards',
        'design_patterns', 'code_complexity', 'refactoring_opportunities'
    ]
    
    # Initialize overall metrics
    for field in numeric_fields:
        deviations['overall']['metrics'][field] = {
            'total_deviation': 0,
            'count': 0,
            'avg_deviation': 0
        }

    # Calculate per-file deviations
    for filename, file_results in files_data.items():
        deviations['per_file'][filename] = {
            'metrics': {},
            'total_deviation': 0,
            'max_deviation': 0,
            'most_inconsistent_metric': None,
            'avg_total_deviation': 0
        }
        
        # Calculate deviations for each metric
        for field in numeric_fields:
            values = [int(result[field]) for result in file_results]
            if not values:
                continue
                
            mean_value = sum(values) / len(values)
            max_value = max(values)
            min_value = min(values)
            absolute_range = max_value - min_value
            
            if mean_value > 0:
                deviations_from_mean = [abs(v - mean_value) / mean_value * 100 for v in values]
                avg_deviation = sum(deviations_from_mean) / len(deviations_from_mean)
            else:
                avg_deviation = 0
            
            metric_info = {
                'mean': round(mean_value, 2),
                'min': min_value,
                'max': max_value,
                'range': absolute_range,
                'avg_deviation_percent': round(avg_deviation, 2),
                'values_per_cycle': values
            }
            
            deviations['per_file'][filename]['metrics'][field] = metric_info
            
            # Update max deviation if this metric has larger deviation
            if avg_deviation > deviations['per_file'][filename]['max_deviation']:
                deviations['per_file'][filename]['max_deviation'] = avg_deviation
                deviations['per_file'][filename]['most_inconsistent_metric'] = field
            
            # Add to total deviation
            deviations['per_file'][filename]['total_deviation'] += avg_deviation
            
            # Update overall metrics
            deviations['overall']['metrics'][field]['total_deviation'] += avg_deviation
            deviations['overall']['metrics'][field]['count'] += 1
        
        # Calculate average deviation for this file
        num_metrics = len(numeric_fields)
        deviations['per_file'][filename]['avg_total_deviation'] = round(
            deviations['per_file'][filename]['total_deviation'] / num_metrics, 2
        )
        
        # Add to overall total
        deviations['overall']['total_deviation'] += deviations['per_file'][filename]['avg_total_deviation']
    
    # Calculate overall averages
    num_files = len(files_data)
    if num_files > 0:
        deviations['overall']['avg_total_deviation'] = round(
            deviations['overall']['total_deviation'] / num_files, 2
        )
        
        # Calculate average deviation per metric
        for field in numeric_fields:
            metric_data = deviations['overall']['metrics'][field]
            if metric_data['count'] > 0:
                metric_data['avg_deviation'] = round(
                    metric_data['total_deviation'] / metric_data['count'], 2
                )
    
    return deviations

def format_deviation_summary(deviations: dict) -> tuple[str, str]:
    """
    Format deviation analysis results into two summaries:
    - A detailed summary for the file
    - A concise summary for the console
    
    Returns:
        tuple[str, str]: (detailed_summary, console_summary)
    """
    # Generate overall statistics
    overall_stats = "\n📈 Overall Statistics\n" + "=" * 50 + "\n"
    overall_stats += f"\nAverage total deviation across all files: {deviations['overall']['avg_total_deviation']}%\n"
    
    # Sort metrics by average deviation
    sorted_overall_metrics = sorted(
        deviations['overall']['metrics'].items(),
        key=lambda x: x[1]['avg_deviation'],
        reverse=True
    )
    
    overall_stats += "\nDeviation by metric (sorted by inconsistency):\n"
    for metric, stats in sorted_overall_metrics:
        if stats['count'] > 0:
            overall_stats += f"  • {metric}: ±{stats['avg_deviation']}%\n"
    
    # Start detailed summary with overall statistics
    detailed = "\n📊 Consistency Analysis Summary\n" + "=" * 50 + "\n"
    detailed += overall_stats  # Add overall stats at the beginning
    detailed += "\n📄 Per-File Analysis\n" + "=" * 50 + "\n"
    
    # Per-file analysis
    for filename, file_stats in deviations['per_file'].items():
        detailed += f"\n📁 {filename}\n"
        detailed += f"  Average deviation across all metrics: {file_stats['avg_total_deviation']}%\n"
        detailed += f"  Most inconsistent metric: {file_stats['most_inconsistent_metric']} "
        detailed += f"(±{round(file_stats['max_deviation'], 2)}%)\n"
        
        # Show top 5 most inconsistent metrics
        sorted_metrics = sorted(
            file_stats['metrics'].items(),
            key=lambda x: x[1]['avg_deviation_percent'],
            reverse=True
        )[:5]
        
        detailed += "\n  Top 5 most inconsistent metrics:\n"
        for metric, stats in sorted_metrics:
            detailed += f"    • {metric}: ±{stats['avg_deviation_percent']}% "
            detailed += f"(range: {stats['min']}-{stats['max']})\n"
    
    # Console summary is just the overall statistics
    console = overall_stats
    
    return detailed, console 