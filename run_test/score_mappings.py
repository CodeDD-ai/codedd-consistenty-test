"""Module containing shared score mappings for code auditing."""

SCORE_MAPPINGS = {
    # Quality scores
    "readability": {"highly readable": 100, "moderately readable": 50, "low readability": 0},
    "consistency": {"highly consistent": 100, "somewhat inconsistent": 50, "not consistent": 0},
    "modularity": {"excellent": 100, "average": 50, "poor": 0},
    "maintainability": {"high": 100, "moderate": 50, "low": 0},
    "reusability": {"high": 100, "moderate": 50, "low": 0},
    "redundancy": {"no redundancies": 100, "some redundancies": 50, "high redundancy": 0},
    "technical_debt": {"none": 100, "low": 66, "moderate": 33, "high": 0},
    "code_smells": {"none": 100, "low": 66, "moderate": 33, "high": 0},

    # Functionality scores
    "completeness": {"fully functional": 100, "partially functional": 50, "not functional": 0},
    "edge_cases": {"excellently covered": 100, "partially covered": 66, "poorly covered": 33, "none covered": 0},
    "error_handling": {"robust": 100, "adequate": 50, "poor": 0},

    # Performance scores
    "efficiency": {"high": 100, "average": 50, "poor": 0},
    "scalability": {"high": 100, "moderate": 50, "not scalable": 0},
    "resource_utilization": {"optimal": 100, "acceptable": 50, "excessive": 0},
    "load_handling": {"excellent": 100, "good": 66, "average": 33, "poor": 0},
    "parallel_processing": {"fully supported": 100, "partially supported": 50, "not supported": 0, "not required": 100},
    "database_interaction_efficiency": {"optimized": 100, "sufficient": 50, "inefficient": 0, "not required": 100},
    "concurrency_management": {"robust": 100, "adequate": 50, "poor": 0, "not required": 100},
    "state_management_efficiency": {"optimal": 100, "adequate": 50, "problematic": 0, "not required": 100},
    "modularity_decoupling": {"highly modular": 100, "somewhat modular": 50, "monolithic": 0},
    "configuration_customization_ease": {"flexible": 100, "moderate": 50, "rigid": 0},

    # Security scores
    "input_validation": {"strong": 100, "adequate": 50, "weak": 0, "not required": 100},
    "data_handling": {"secure": 100, "moderately secure": 50, "insecure": 0, "not required": 100},
    "authentication": {"robust": 100, "adequate": 50, "non-existent": 0, "not required": 100},

    # Compatibility scores
    "independence": {"multi-platform": 100, "limited platforms": 50, "single platform": 25},
    "integration": {"seamless": 100, "requires workarounds": 50, "incompatible": 0},

    # Documentation scores
    "inline_comments": {"comprehensive": 100, "adequate": 66, "sparse": 33, "none": 0},

    # Standards scores
    "standards": {"fully compliant": 100, "partially compliant": 50, "non-compliant": 0},
    "design_patterns": {"extensive": 100, "moderate": 66, "rare": 33, "none": 0},
    "code_complexity": {"low": 100, "moderate": 50, "high": 0},
    "refactoring_opportunities": {"many": 100, "some": 66, "few": 33, "none": 0}
}

def get_score(attribute: str, value: str) -> int:
    """Get the numerical score for a given attribute and value.
    
    Args:
        attribute: The attribute being scored (e.g., 'readability', 'efficiency')
        value: The text value to convert to a score
        
    Returns:
        int: The numerical score (0-100) for the given value
    """
    if attribute not in SCORE_MAPPINGS:
        return 0
        
    value = value.lower()
    mapping = SCORE_MAPPINGS[attribute]
    
    for key, score in mapping.items():
        if value.startswith(key):
            return score
            
    return 0  # Default score if no match found 