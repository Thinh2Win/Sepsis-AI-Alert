from datetime import datetime, date
from typing import Optional, Union
import math

def calculate_age(birth_date: Union[str, date, datetime]) -> Optional[int]:
    """
    Calculate age from birth date
    
    Args:
        birth_date: Birth date as string (YYYY-MM-DD), date, or datetime object
    
    Returns:
        Age in years or None if invalid date
    """
    try:
        if isinstance(birth_date, str):
            birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
        elif isinstance(birth_date, datetime):
            birth_date = birth_date.date()
        
        today = date.today()
        age = today.year - birth_date.year
        
        # Adjust if birthday hasn't occurred this year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
            
        return age
    except (ValueError, TypeError, AttributeError):
        return None

def calculate_bmi(height_cm: Optional[float], weight_kg: Optional[float]) -> Optional[float]:
    """
    Calculate BMI from height and weight
    
    Args:
        height_cm: Height in centimeters
        weight_kg: Weight in kilograms
    
    Returns:
        BMI value or None if invalid inputs
    """
    if not height_cm or not weight_kg or height_cm <= 0 or weight_kg <= 0:
        return None
    
    try:
        height_m = height_cm / 100
        bmi = weight_kg / (height_m ** 2)
        return round(bmi, 2)
    except (ValueError, ZeroDivisionError):
        return None

def convert_height_to_cm(value: float, unit: str) -> Optional[float]:
    """
    Convert height to centimeters
    
    Args:
        value: Height value
        unit: Unit (cm, m, in, ft)
    
    Returns:
        Height in centimeters or None if invalid
    """
    if not value or value <= 0:
        return None
    
    unit = unit.lower().strip()
    
    conversion_factors = {
        'cm': 1.0,
        'm': 100.0,
        'in': 2.54,
        'ft': 30.48
    }
    
    factor = conversion_factors.get(unit)
    if factor is None:
        return None
    
    return round(value * factor, 2)

def convert_weight_to_kg(value: float, unit: str) -> Optional[float]:
    """
    Convert weight to kilograms
    
    Args:
        value: Weight value
        unit: Unit (kg, g, lb, oz)
    
    Returns:
        Weight in kilograms or None if invalid
    """
    if not value or value <= 0:
        return None
    
    unit = unit.lower().strip()
    
    conversion_factors = {
        'kg': 1.0,
        'g': 0.001,
        'lb': 0.453592,
        'oz': 0.0283495
    }
    
    factor = conversion_factors.get(unit)
    if factor is None:
        return None
    
    return round(value * factor, 2)

def calculate_mean_arterial_pressure(systolic: Optional[float], diastolic: Optional[float]) -> Optional[float]:
    """
    Calculate Mean Arterial Pressure (MAP)
    
    Args:
        systolic: Systolic blood pressure
        diastolic: Diastolic blood pressure
    
    Returns:
        MAP value or None if invalid inputs
    """
    if not systolic or not diastolic or systolic <= 0 or diastolic <= 0:
        return None
    
    try:
        map_value = (systolic + 2 * diastolic) / 3
        return round(map_value, 2)
    except (ValueError, ZeroDivisionError):
        return None

def calculate_pulse_pressure(systolic: Optional[float], diastolic: Optional[float]) -> Optional[float]:
    """
    Calculate Pulse Pressure
    
    Args:
        systolic: Systolic blood pressure
        diastolic: Diastolic blood pressure
    
    Returns:
        Pulse pressure or None if invalid inputs
    """
    if not systolic or not diastolic or systolic <= 0 or diastolic <= 0:
        return None
    
    try:
        pulse_pressure = systolic - diastolic
        return round(pulse_pressure, 2)
    except (ValueError, TypeError):
        return None

def categorize_bmi(bmi: Optional[float]) -> Optional[str]:
    """
    Categorize BMI according to WHO standards
    
    Args:
        bmi: BMI value
    
    Returns:
        BMI category or None if invalid BMI
    """
    if not bmi or bmi <= 0:
        return None
    
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal weight"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"

def is_fever(temperature: Optional[float], unit: str = "C") -> Optional[bool]:
    """
    Determine if temperature indicates fever
    
    Args:
        temperature: Temperature value
        unit: Temperature unit (C or F)
    
    Returns:
        True if fever, False if normal, None if invalid
    """
    if not temperature:
        return None
    
    unit = unit.upper().strip()
    
    if unit == "F":
        # Convert to Celsius
        temperature = (temperature - 32) * 5/9
    elif unit != "C":
        return None
    
    # Fever threshold in Celsius
    return temperature >= 38.0

def calculate_heart_rate_variability_simple(heart_rates: list) -> Optional[float]:
    """
    Calculate simple heart rate variability (standard deviation)
    
    Args:
        heart_rates: List of heart rate values
    
    Returns:
        Heart rate variability or None if insufficient data
    """
    if not heart_rates or len(heart_rates) < 2:
        return None
    
    try:
        mean_hr = sum(heart_rates) / len(heart_rates)
        variance = sum((hr - mean_hr) ** 2 for hr in heart_rates) / len(heart_rates)
        return round(math.sqrt(variance), 2)
    except (ValueError, TypeError):
        return None