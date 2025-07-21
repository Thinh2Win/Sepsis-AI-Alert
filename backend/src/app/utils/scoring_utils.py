"""
Shared Scoring Utilities

Common utilities for both SOFA and qSOFA scoring to eliminate code duplication
and maintain DRY/KISS principles.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.services.fhir_client import FHIRClient
from app.utils.fhir_utils import extract_observations_by_loinc

logger = logging.getLogger(__name__)


async def collect_fhir_parameters(
    fhir_client: FHIRClient,
    patient_id: str,
    start_date: datetime,
    end_date: datetime,
    parameter_configs: Dict[str, Dict[str, Any]],
    parameter_class
) -> Dict[str, Any]:
    """
    Generic FHIR parameter collector for any scoring system
    
    Args:
        fhir_client: FHIR client instance
        patient_id: Patient FHIR ID
        start_date: Start date for data collection
        end_date: End date for data collection
        parameter_configs: Dict mapping parameter names to their FHIR configs
        parameter_class: Parameter class (SofaParameter or QsofaParameter)
    
    Returns:
        Dict with collected parameters as parameter_class objects
    """
    logger.debug(f"Collecting FHIR parameters for patient [REDACTED]")
    
    result = {}
    
    for param_name, config in parameter_configs.items():
        codes = config.get("codes", [])
        count = config.get("count", 1)
        parameter_mapping = config.get("parameter_mapping", {})
        system_name = config.get("system_name", param_name)
        
        # Initialize all expected parameters
        for loinc_code, mapped_name in parameter_mapping.items():
            result[mapped_name] = parameter_class()
        
        try:
            bundle = await fhir_client._make_request(
                "GET", "Observation",
                params={
                    "patient": patient_id,
                    "code": ",".join(codes),
                    "date": f"ge{start_date.isoformat()}&date=le{end_date.isoformat()}",
                    "_sort": "-date",
                    "_count": str(count)
                }
            )
            
            observations = extract_observations_by_loinc(bundle, codes)
            
            # Process observations
            for obs in observations:
                loinc_code = obs.get("loinc_code")
                mapped_name = parameter_mapping.get(loinc_code)
                
                if mapped_name and mapped_name in result:
                    param = result[mapped_name]
                    if param.value is None:  # Use most recent value only
                        param.value = obs.get("value")
                        param.unit = obs.get("unit")
                        param.timestamp = obs.get("timestamp")
                        param.source = "measured"
            
        except Exception as e:
            logger.error(f"Error collecting {system_name} parameters: {str(e)}")
            # Continue with empty parameters - they'll be handled by defaults
    
    return result


def create_default_component_score(
    component_name: str,
    score: int,
    threshold_met: bool,
    interpretation: str,
    parameters_used: List[str],
    component_score_class
):
    """
    Create a default component score for fallback scenarios
    
    Args:
        component_name: Name of the component (e.g., "Respiratory")
        score: The score value
        threshold_met: Whether the threshold was met
        interpretation: Human-readable interpretation
        parameters_used: List of parameters used
        component_score_class: Component score class to instantiate
    
    Returns:
        Component score instance
    """
    return component_score_class(
        component=component_name,
        score=score,
        threshold_met=threshold_met,
        interpretation=interpretation,
        parameters_used=parameters_used
    )


def apply_parameter_defaults(
    parameters: Dict[str, Any],
    defaults: Dict[str, float],
    units: Dict[str, str],
    parameter_class
) -> Dict[str, Any]:
    """
    Apply default values to missing parameters
    
    Args:
        parameters: Dict of parameter objects
        defaults: Dict of default values by parameter name
        units: Dict of units by parameter name
        parameter_class: Parameter class for creating new instances
    
    Returns:
        Updated parameters dict with defaults applied
    """
    for param_name, default_value in defaults.items():
        if param_name in parameters:
            param = parameters[param_name]
            if param.value is None:
                param.value = default_value
                param.unit = units.get(param_name, "")
                param.source = "default"
                param.is_estimated = True
                logger.debug(f"Applied default for {param_name}: {default_value}")
        else:
            # Create new parameter with default
            parameters[param_name] = parameter_class(
                value=default_value,
                unit=units.get(param_name, ""),
                source="default",
                is_estimated=True
            )
    
    return parameters


def calculate_data_reliability_score(
    total_parameters: int,
    estimated_count: int
) -> float:
    """
    Calculate data reliability score based on estimated parameters
    
    Args:
        total_parameters: Total number of parameters
        estimated_count: Number of estimated parameters
    
    Returns:
        Reliability score (0.0 to 1.0)
    """
    if total_parameters <= 0:
        return 0.0
    return max(0.0, (total_parameters - estimated_count) / total_parameters)


def validate_score_range(score: int, min_score: int, max_score: int) -> int:
    """
    Validate and clamp score to valid range
    
    Args:
        score: The score to validate
        min_score: Minimum allowed score
        max_score: Maximum allowed score
    
    Returns:
        Clamped score within valid range
    """
    return max(min_score, min(max_score, score))