"""
Enhanced Synthetic Data Generator for Sepsis Prediction Training

Combines clinical sophistication with API compatibility:
- Age-stratified sepsis risk modeling
- Realistic progression patterns (rapid vs gradual)
- Superior physiological correlations
- Perfect API feature compatibility
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Literal
import random
import os

# API Features from the sepsis alert system
API_FEATURES = [
    "pao2", "fio2", "mechanical_ventilation", "platelets", 
    "bilirubin", "systolic_bp", "diastolic_bp", "mean_arterial_pressure",
    "glasgow_coma_scale", "creatinine", "urine_output_24h",
    "dopamine", "dobutamine", "epinephrine", "norepinephrine", 
    "phenylephrine", "respiratory_rate", "heart_rate", "temperature",
    "oxygen_saturation", "supplemental_oxygen"
]

class EnhancedSepsisDataGenerator:
    """
    Enhanced synthetic data generator combining clinical realism with API compatibility.
    
    Features:
    - Age-stratified sepsis risk modeling
    - Realistic sepsis progression patterns
    - Superior physiological correlations
    - Exact API feature compatibility
    """
    
    def __init__(self, seed: int = 42):
        """Initialize the enhanced generator with reproducible seed."""
        np.random.seed(seed)
        random.seed(seed)
        
        # Age-stratified sepsis risk (from clinical data)
        self.sepsis_risk_by_age = {
            'young': 0.15,      # <40 years
            'middle': 0.25,     # 40-65 years  
            'elderly': 0.40     # >65 years
        }
        
        # Normal parameter ranges (evidence-based)
        self.normal_ranges = {
            "pao2": (80, 100),  # mmHg
            "fio2": (0.21, 0.30),  # fraction
            "platelets": (150, 400),  # x10^3/uL
            "bilirubin": (0.3, 1.2),  # mg/dL
            "systolic_bp": (110, 140),  # mmHg
            "diastolic_bp": (70, 90),  # mmHg
            "glasgow_coma_scale": (15, 15),  # points
            "creatinine": (0.6, 1.2),  # mg/dL
            "urine_output_24h": (1200, 2000),  # mL
            "respiratory_rate": (12, 20),  # breaths/min
            "heart_rate": (60, 100),  # bpm
            "temperature": (36.1, 37.2),  # °C
            "oxygen_saturation": (95, 100),  # %
        }
        
        # Realistic bounds for parameters
        self.parameter_bounds = {
            "pao2": (40, 120),
            "fio2": (0.21, 1.0),
            "platelets": (10, 600),
            "bilirubin": (0.1, 30.0),
            "systolic_bp": (60, 200),
            "diastolic_bp": (30, 120),
            "mean_arterial_pressure": (40, 130),
            "glasgow_coma_scale": (3, 15),
            "creatinine": (0.3, 10.0),
            "urine_output_24h": (0, 4000),
            "respiratory_rate": (8, 40),
            "heart_rate": (40, 180),
            "temperature": (34.0, 42.0),
            "oxygen_saturation": (70, 100),
        }
    
    def generate_patient_age(self) -> int:
        """Generate realistic age distribution (bimodal for ICU population)."""
        if np.random.random() < 0.7:
            # Elderly peak (more common in ICU)
            age = int(np.random.normal(65, 15))
        else:
            # Younger peak
            age = int(np.random.normal(45, 15))
        return max(18, min(95, age))  # Reasonable bounds
    
    def get_age_group(self, age: int) -> Literal['young', 'middle', 'elderly']:
        """Categorize age into sepsis risk groups."""
        if age < 40:
            return 'young'
        elif age < 65:
            return 'middle'
        else:
            return 'elderly'
    
    def generate_patient_baseline(self, patient_id: str, age: int) -> Dict:
        """Generate age-adjusted baseline parameters for a patient."""
        
        age_factor = age / 100  # Normalize age for adjustments
        baseline = {
            "patient_id": patient_id,
            "age": age,
        }
        
        # Age-adjusted normal ranges
        for param, (low, high) in self.normal_ranges.items():
            if param == "heart_rate":
                # Elderly tend to have lower resting HR
                baseline[param] = np.random.uniform(
                    low - 5*age_factor, high - 10*age_factor
                )
            elif param == "systolic_bp":
                # BP tends to increase with age
                baseline[param] = np.random.uniform(
                    low + 10*age_factor, high + 15*age_factor
                )
            elif param == "creatinine":
                # Kidney function decreases with age
                baseline[param] = np.random.uniform(
                    low + 0.2*age_factor, high + 0.3*age_factor
                )
            else:
                # Normal distribution within range
                baseline[param] = np.random.uniform(low, high)
        
        # Calculate mean arterial pressure
        baseline["mean_arterial_pressure"] = (
            baseline["systolic_bp"] + 2 * baseline["diastolic_bp"]
        ) / 3
        
        # Initialize binary parameters
        baseline["mechanical_ventilation"] = 0
        baseline["supplemental_oxygen"] = 0
        
        # Initialize vasopressors (normally zero)
        for vasopressor in ["dopamine", "dobutamine", "epinephrine", 
                           "norepinephrine", "phenylephrine"]:
            baseline[vasopressor] = 0.0
        
        return baseline
    
    def calculate_sepsis_progression(self, current_hour: int, onset_hour: int,
                                   progression_speed: Literal['rapid', 'gradual']) -> float:
        """Calculate sepsis progression (0 to 1) with realistic patterns."""
        
        # Pre-sepsis phase (6 hours before onset)
        if current_hour < onset_hour - 6:
            return 0.0
        
        hours_since_prodrome = current_hour - (onset_hour - 6)
        
        if progression_speed == 'rapid':
            # Rapid progression over 6-8 hours
            max_hours = 8
            # Sigmoid curve for rapid deterioration
            progress = 1 / (1 + np.exp(-0.8 * (hours_since_prodrome - 4)))
        else:
            # Gradual progression over 12-18 hours  
            max_hours = 18
            # More linear progression
            progress = min(1.0, hours_since_prodrome / max_hours)
        
        # Add small amount of noise
        progress += np.random.normal(0, 0.03)
        return np.clip(progress, 0, 1)
    
    def apply_sepsis_physiology(self, baseline: Dict, progression: float,
                               previous_values: Optional[Dict] = None) -> Dict:
        """Apply realistic sepsis physiology based on progression."""
        
        # Start with baseline or previous values for continuity
        if previous_values:
            current = {k: v for k, v in previous_values.items() 
                      if k in baseline and k != "patient_id" and k != "age"}
        else:
            current = baseline.copy()
        
        if progression == 0:
            # Normal physiological variation
            self._apply_normal_variation(current, baseline)
            return current
        
        # Temperature: fever (70%) or hypothermia (30%) - key sepsis feature
        if np.random.random() < 0.7:
            # Fever pattern
            temp_increase = progression * np.random.uniform(1.5, 3.5)
            current["temperature"] = baseline["temperature"] + temp_increase
        else:
            # Hypothermia pattern (worse prognosis)
            temp_decrease = progression * np.random.uniform(1.0, 2.5)
            current["temperature"] = baseline["temperature"] - temp_decrease
        
        # Cardiovascular: tachycardia and hypotension
        hr_increase = progression * np.random.uniform(20, 60)
        current["heart_rate"] = baseline["heart_rate"] + hr_increase
        
        # Hypotension (distributive shock)
        bp_decrease = progression * np.random.uniform(15, 50)
        current["systolic_bp"] = baseline["systolic_bp"] - bp_decrease
        current["diastolic_bp"] = current["systolic_bp"] * 0.6 + np.random.normal(0, 3)
        current["mean_arterial_pressure"] = (
            current["systolic_bp"] + 2 * current["diastolic_bp"]
        ) / 3
        
        # Respiratory: tachypnea and hypoxemia
        rr_increase = progression * np.random.uniform(8, 18)
        current["respiratory_rate"] = baseline["respiratory_rate"] + rr_increase
        
        # Oxygen saturation decreases
        o2_decrease = progression * np.random.uniform(3, 12)
        current["oxygen_saturation"] = baseline["oxygen_saturation"] - o2_decrease
        
        # PaO2 decreases (lung dysfunction)
        pao2_decrease = progression * np.random.uniform(15, 40)
        current["pao2"] = baseline["pao2"] - pao2_decrease
        
        # FiO2 increases as patient requires more oxygen
        if current["oxygen_saturation"] < 92:
            current["fio2"] = min(1.0, 0.21 + progression * 0.6)
        else:
            current["fio2"] = 0.21 + progression * 0.3
        
        # Neurological: altered mental status
        if progression > 0.4:
            gcs_decrease = np.random.poisson(progression * 3)
            current["glasgow_coma_scale"] = max(3, 15 - gcs_decrease)
        else:
            current["glasgow_coma_scale"] = 15
        
        # Organ dysfunction markers
        
        # Renal: creatinine increase, urine output decrease
        creat_increase = progression * np.random.exponential(1.5)
        current["creatinine"] = baseline["creatinine"] + creat_increase
        current["urine_output_24h"] = baseline["urine_output_24h"] * (1 - progression * 0.8)
        
        # Hepatic: bilirubin increase
        bili_increase = progression * np.random.exponential(2.0)
        current["bilirubin"] = baseline["bilirubin"] + bili_increase
        
        # Hematologic: thrombocytopenia
        platelet_decrease = progression * np.random.uniform(0.4, 0.7)
        current["platelets"] = baseline["platelets"] * (1 - platelet_decrease)
        
        # Support devices and interventions
        
        # Supplemental oxygen
        current["supplemental_oxygen"] = int(
            current["oxygen_saturation"] < 94 or current["fio2"] > 0.21
        )
        
        # Mechanical ventilation (severe respiratory failure)
        pf_ratio = current["pao2"] / current["fio2"]
        current["mechanical_ventilation"] = int(
            progression > 0.7 and pf_ratio < 200
        )
        
        # Vasopressor support (septic shock)
        if progression > 0.6 and current["mean_arterial_pressure"] < 65:
            # Norepinephrine first-line
            current["norepinephrine"] = np.random.uniform(0.05, 0.5 * progression)
            
            # Additional pressors for refractory shock
            if progression > 0.8:
                current["epinephrine"] = np.random.uniform(0, 0.1)
                # Note: phenylephrine can be used as alternative
                if np.random.random() < 0.3:
                    current["phenylephrine"] = np.random.uniform(0.5, 2.0)
            
            # Dopamine less commonly used (reserved for specific cases)
            if progression > 0.85 and np.random.random() < 0.2:
                current["dopamine"] = np.random.uniform(5, 15)
        
        # Apply noise and bounds
        self._apply_measurement_noise_and_bounds(current)
        
        return current
    
    def _apply_normal_variation(self, current: Dict, baseline: Dict):
        """Apply normal physiological variation."""
        variation_params = [
            "heart_rate", "systolic_bp", "diastolic_bp", "respiratory_rate",
            "temperature", "oxygen_saturation", "pao2"
        ]
        
        for param in variation_params:
            if param in current:
                # Small random variation (±3-5%)
                variation = np.random.normal(0, 0.04)
                current[param] = baseline[param] * (1 + variation)
        
        # Recalculate MAP
        current["mean_arterial_pressure"] = (
            current["systolic_bp"] + 2 * current["diastolic_bp"]
        ) / 3
    
    def _apply_measurement_noise_and_bounds(self, values: Dict):
        """Apply realistic measurement noise and enforce clinical bounds."""
        
        # Add measurement noise
        noise_levels = {
            "pao2": 2.0, "platelets": 10.0, "bilirubin": 0.05,
            "systolic_bp": 2.0, "diastolic_bp": 1.5, "heart_rate": 2.0,
            "respiratory_rate": 1.0, "temperature": 0.1, "oxygen_saturation": 0.5,
            "creatinine": 0.03, "urine_output_24h": 30.0
        }
        
        for param, noise_std in noise_levels.items():
            if param in values and param != "glasgow_coma_scale":
                values[param] += np.random.normal(0, noise_std)
        
        # Apply bounds
        for param, value in values.items():
            if param in self.parameter_bounds:
                low, high = self.parameter_bounds[param]
                values[param] = np.clip(value, low, high)
        
        # Round appropriately
        integer_params = [
            "heart_rate", "respiratory_rate", "glasgow_coma_scale", 
            "platelets", "urine_output_24h"
        ]
        for param in integer_params:
            if param in values:
                values[param] = int(round(values[param]))
        
        # Round to 1 decimal
        decimal_params = [
            "temperature", "systolic_bp", "diastolic_bp", "mean_arterial_pressure",
            "oxygen_saturation", "creatinine", "bilirubin", "pao2"
        ]
        for param in decimal_params:
            if param in values:
                values[param] = round(values[param], 1)
        
        # Round FiO2 to 2 decimals
        if "fio2" in values:
            values["fio2"] = round(values["fio2"], 2)
        
        # Round vasopressors to 3 decimals
        for pressor in ["dopamine", "dobutamine", "epinephrine", 
                       "norepinephrine", "phenylephrine"]:
            if pressor in values:
                values[pressor] = round(values[pressor], 3)
    
    def simulate_patient_progression(self, patient_id: str, hours: int = 48) -> List[Dict]:
        """
        Simulate complete patient progression with enhanced realism.
        
        Args:
            patient_id: Unique patient identifier
            hours: Total hours to simulate
            
        Returns:
            List of patient records over time
        """
        
        # Generate patient characteristics
        age = self.generate_patient_age()
        age_group = self.get_age_group(age)
        will_develop_sepsis = np.random.random() < self.sepsis_risk_by_age[age_group]
        
        # Generate baseline parameters
        baseline = self.generate_patient_baseline(patient_id, age)
        
        # Determine sepsis characteristics if applicable
        if will_develop_sepsis:
            onset_hour = np.random.randint(8, hours - 12)
            progression_speed = np.random.choice(['rapid', 'gradual'], p=[0.3, 0.7])
        else:
            onset_hour = None
            progression_speed = None
        
        # Generate time points (every 2-4 hours)
        time_points = []
        current_hour = 0
        base_time = datetime.now() - timedelta(hours=hours)
        
        while current_hour < hours:
            time_points.append(current_hour)
            # Variable intervals (2-4 hours)
            current_hour += np.random.randint(2, 5)
        
        # Generate progression
        progression_data = []
        previous_values = None
        
        for i, hour in enumerate(time_points):
            # Calculate sepsis progression
            if will_develop_sepsis and onset_hour:
                progression = self.calculate_sepsis_progression(
                    hour, onset_hour, progression_speed
                )
            else:
                progression = 0.0
            
            # Generate physiological parameters
            current_values = self.apply_sepsis_physiology(
                baseline, progression, previous_values
            )
            
            # Add metadata
            record = {
                "patient_id": patient_id,
                "timestamp": base_time + timedelta(hours=hour),
                "sepsis_label": int(progression > 0.5),  # Binary label
                "sepsis_progression": round(progression, 3),  # Continuous risk
                "hours_from_start": hour,
            }
            
            # Add all API features
            for feature in API_FEATURES:
                record[feature] = current_values.get(feature, 0.0)
            
            progression_data.append(record)
            previous_values = current_values
        
        return progression_data
    
    def generate_dataset(self, n_patients: int = 1000, hours_range: Tuple[int, int] = (24, 48)) -> pd.DataFrame:
        """
        Generate complete enhanced synthetic dataset.
        
        Args:
            n_patients: Number of patients to generate
            hours_range: Range of simulation hours per patient
            
        Returns:
            DataFrame with all patient records
        """
        all_records = []
        
        print(f"Generating enhanced dataset with {n_patients} patients...")
        
        for i in range(n_patients):
            patient_id = f"patient_{i:05d}"
            hours = np.random.randint(hours_range[0], hours_range[1] + 1)
            
            patient_data = self.simulate_patient_progression(patient_id, hours)
            all_records.extend(patient_data)
            
            if (i + 1) % 100 == 0:
                print(f"Generated {i + 1}/{n_patients} patients")
        
        # Create DataFrame
        df = pd.DataFrame(all_records)
        
        # Ensure column order: metadata + API features
        metadata_cols = ["patient_id", "timestamp", "sepsis_label", "sepsis_progression", "hours_from_start"]
        column_order = metadata_cols + API_FEATURES
        df = df[column_order]
        
        # Summary statistics
        sepsis_patients = df.groupby('patient_id')['sepsis_label'].max().sum()
        sepsis_records = df['sepsis_label'].sum()
        
        print(f"\nEnhanced dataset generated:")
        print(f"Total records: {len(df)}")
        print(f"Unique patients: {df['patient_id'].nunique()}")
        print(f"Patients with sepsis: {sepsis_patients} ({sepsis_patients/n_patients:.1%})")
        print(f"Sepsis-positive records: {sepsis_records} ({sepsis_records/len(df):.1%})")
        
        return df
    
    def save_dataset(self, df: pd.DataFrame, filepath: str):
        """Save enhanced dataset with summary statistics."""
        df.to_csv(filepath, index=False)
        print(f"Enhanced dataset saved to {filepath}")
        
        # Detailed summary
        print(f"\nDataset Summary:")
        print(f"Shape: {df.shape}")
        print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"Average records per patient: {len(df) / df['patient_id'].nunique():.1f}")
        
        # Risk distribution
        progression_stats = df[df['sepsis_progression'] > 0]['sepsis_progression'].describe()
        if len(progression_stats) > 0:
            print(f"Sepsis progression distribution:")
            print(f"  Mean: {progression_stats['mean']:.3f}")
            print(f"  Std: {progression_stats['std']:.3f}")
            print(f"  Range: {progression_stats['min']:.3f} - {progression_stats['max']:.3f}")


def main():
    """Generate and save enhanced synthetic sepsis dataset."""
    generator = EnhancedSepsisDataGenerator(seed=42)
    
    # Generate enhanced dataset
    df = generator.generate_dataset(
        n_patients=1000,
        hours_range=(24, 48)
    )
    
    # Save dataset
    output_path = os.path.join(os.path.dirname(__file__), "enhanced_synthetic_sepsis_data.csv")
    generator.save_dataset(df, output_path)


if __name__ == "__main__":
    main()