from datetime import datetime, date, timedelta
from typing import Optional, Union, Tuple
import re

def parse_fhir_datetime(fhir_datetime: str) -> Optional[datetime]:
    """
    Parse FHIR datetime string to datetime object
    
    Args:
        fhir_datetime: FHIR datetime string
    
    Returns:
        Parsed datetime or None if invalid
    """
    if not fhir_datetime:
        return None
    
    # Common FHIR datetime formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(fhir_datetime, fmt)
        except ValueError:
            continue
    
    return None

def format_datetime_for_fhir(dt: datetime) -> str:
    """
    Format datetime for FHIR API
    
    Args:
        dt: Datetime object
    
    Returns:
        FHIR-formatted datetime string
    """
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

def validate_date_range(start_date: Optional[datetime], end_date: Optional[datetime]) -> Tuple[bool, str]:
    """
    Validate date range for FHIR queries
    
    Args:
        start_date: Start date
        end_date: End date
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not start_date and not end_date:
        return True, ""
    
    if start_date and end_date:
        if start_date > end_date:
            return False, "Start date must be before end date"
        
        # Check if date range is too large (more than 1 year)
        if (end_date - start_date).days > 365:
            return False, "Date range cannot exceed 365 days"
    
    # Check if dates are in the future
    now = datetime.now()
    if start_date and start_date > now:
        return False, "Start date cannot be in the future"
    
    if end_date and end_date > now:
        return False, "End date cannot be in the future"
    
    return True, ""

def get_date_range_for_sepsis_monitoring(hours_back: int = 72) -> Tuple[datetime, datetime]:
    """
    Get appropriate date range for sepsis monitoring (typically last 72 hours)
    
    Args:
        hours_back: Number of hours to look back
    
    Returns:
        Tuple of (start_date, end_date)
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=hours_back)
    return start_date, end_date

def get_recent_time_window(hours: int = 24) -> Tuple[datetime, datetime]:
    """
    Get time window for recent observations
    
    Args:
        hours: Number of hours to look back
    
    Returns:
        Tuple of (start_date, end_date)
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=hours)
    return start_date, end_date

def is_recent_observation(observation_time: Optional[datetime], hours_threshold: int = 24) -> bool:
    """
    Check if observation is recent (within specified hours)
    
    Args:
        observation_time: Observation datetime
        hours_threshold: Threshold in hours
    
    Returns:
        True if recent, False otherwise
    """
    if not observation_time:
        return False
    
    threshold_time = datetime.now() - timedelta(hours=hours_threshold)
    return observation_time >= threshold_time

def calculate_time_since_observation(observation_time: Optional[datetime]) -> Optional[str]:
    """
    Calculate human-readable time since observation
    
    Args:
        observation_time: Observation datetime
    
    Returns:
        Human-readable time string or None
    """
    if not observation_time:
        return None
    
    now = datetime.now()
    
    # Handle timezone-aware datetime
    if observation_time.tzinfo is not None:
        if now.tzinfo is None:
            now = now.replace(tzinfo=observation_time.tzinfo)
    
    delta = now - observation_time
    
    if delta.days > 0:
        return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
    
    hours = delta.seconds // 3600
    if hours > 0:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    
    minutes = (delta.seconds % 3600) // 60
    if minutes > 0:
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    
    return "Just now"

def group_observations_by_time_window(observations: list, window_hours: int = 1) -> dict:
    """
    Group observations by time windows
    
    Args:
        observations: List of observations with timestamp
        window_hours: Time window in hours
    
    Returns:
        Dictionary grouped by time windows
    """
    if not observations:
        return {}
    
    groups = {}
    window_delta = timedelta(hours=window_hours)
    
    for obs in observations:
        timestamp = obs.get('timestamp')
        if not timestamp:
            continue
        
        # Find appropriate time window
        window_start = timestamp.replace(minute=0, second=0, microsecond=0)
        window_key = window_start.strftime("%Y-%m-%d %H:00")
        
        if window_key not in groups:
            groups[window_key] = []
        
        groups[window_key].append(obs)
    
    return groups

def get_business_hours_filter() -> Tuple[int, int]:
    """
    Get business hours filter (e.g., 8 AM to 6 PM)
    
    Returns:
        Tuple of (start_hour, end_hour)
    """
    return 8, 18

def is_within_business_hours(dt: datetime) -> bool:
    """
    Check if datetime is within business hours
    
    Args:
        dt: Datetime to check
    
    Returns:
        True if within business hours
    """
    start_hour, end_hour = get_business_hours_filter()
    return start_hour <= dt.hour < end_hour