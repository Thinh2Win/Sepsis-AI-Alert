# app/ml/feature_definitions.py

"""
Feature definitions and metadata for sepsis prediction model.
Provides clinical rationale and calculation logic for all features.
"""

import numpy as np

CLINICAL_FEATURES = {
    # Hemodynamic Features
    'shock_index': {
        'formula': 'heart_rate / systolic_bp',
        'unit': 'ratio',
        'range': (0.5, 2.0),
        'clinical_rationale': 'Early indicator of hemodynamic compromise',
        'threshold': {'normal': '<0.7', 'abnormal': '>0.9', 'critical': '>1.3'}
    },
    'modified_shock_index': {
        'formula': 'heart_rate / mean_arterial_pressure',
        'unit': 'ratio',
        'range': (0.7, 3.0),
        'clinical_rationale': 'More sensitive than traditional shock index'
    },
    'pulse_pressure': {
        'formula': 'systolic_bp - diastolic_bp',
        'unit': 'mmHg',
        'range': (20, 80),
        'clinical_rationale': 'Indicator of arterial stiffness and cardiac output'
    },
    'vasopressor_load': {
        'formula': 'norepinephrine + epinephrine + dopamine/100',
        'unit': 'mcg/kg/min equivalent',
        'range': (0, 2.0),
        'clinical_rationale': 'Quantifies vasopressor dependency'
    },
    
    # Respiratory Features
    'pf_ratio': {
        'formula': 'pao2 / fio2',
        'unit': 'mmHg',
        'range': (0, 600),
        'clinical_rationale': 'Gold standard for assessing oxygenation',
        'threshold': {'severe_ards': '<100', 'moderate_ards': '<200', 'mild_ards': '<300'}
    },
    'oxygenation_index': {
        'formula': '(fio2 * 100) / pf_ratio',
        'unit': 'index',
        'range': (0, 50),
        'clinical_rationale': 'Pediatric oxygenation assessment'
    },
    
    # Organ Dysfunction Features
    'organ_failure_count': {
        'formula': 'sum of organ failures',
        'unit': 'count',
        'range': (0, 6),
        'clinical_rationale': 'Number of failing organ systems',
        'threshold': {'single': 1, 'multiple': '>=2'}
    },
    'aki_risk_score': {
        'formula': '(creatinine - 1.5) / 1.5 if creatinine > 1.5 else 0',
        'unit': 'score',
        'range': (0, 5),
        'clinical_rationale': 'Acute kidney injury severity'
    },
    
    # Sepsis Pattern Features
    'qsofa_score': {
        'formula': 'sum of qSOFA criteria met',
        'unit': 'score',
        'range': (0, 3),
        'clinical_rationale': 'Quick bedside sepsis screening',
        'threshold': {'positive': '>=2'}
    },
    'temperature_deviation': {
        'formula': 'abs(temperature - 37.0)',
        'unit': '°C',
        'range': (0, 5),
        'clinical_rationale': 'Deviation from normal temperature'
    }
}

FEATURE_CALCULATIONS = {
    # Hemodynamic features
    'shock_index': lambda df: df['heart_rate'] / df['systolic_bp'],
    'modified_shock_index': lambda df: df['heart_rate'] / df['mean_arterial_pressure'],
    'age_shock_index': lambda df: (df['heart_rate'] / df['systolic_bp']) * df.get('age', 60) / 60,
    'pulse_pressure': lambda df: df['systolic_bp'] - df['diastolic_bp'],
    'pulse_pressure_ratio': lambda df: (df['systolic_bp'] - df['diastolic_bp']) / df['systolic_bp'],
    'perfusion_pressure': lambda df: df['mean_arterial_pressure'] - 12,  # Assuming CVP ~12
    'vasopressor_load': lambda df: (
        df.get('norepinephrine', 0) + df.get('epinephrine', 0) + 
        df.get('dopamine', 0) / 100 + df.get('dobutamine', 0) / 100 + 
        df.get('phenylephrine', 0) / 10
    ),
    
    # Respiratory features
    'pf_ratio': lambda df: df['pao2'] / df['fio2'],
    'oxygenation_index': lambda df: (df['fio2'] * 100) / (df['pao2'] / df['fio2']),
    'hypoxemic_index': lambda df: (100 - df['oxygen_saturation']) / 100,
    'work_of_breathing': lambda df: (
        df['respiratory_rate'] * 
        (1 + (df['fio2'] - 0.21) * 2) *
        (1 + (100 - df['oxygen_saturation']) / 100)
    ),
    
    # Organ dysfunction features
    'aki_risk_score': lambda df: df.apply(
        lambda row: (row['creatinine'] - 1.5) / 1.5 if row['creatinine'] > 1.5 else 0, axis=1
    ),
    'estimated_gfr': lambda df: 186 * (df['creatinine'] ** -1.154) * (df.get('age', 60) ** -0.203),
    'hepatic_dysfunction_score': lambda df: df['bilirubin'].apply(lambda x: np.log1p(x)),
    'coagulopathy_score': lambda df: df.apply(
        lambda row: (150 - row['platelets']) / 150 if row['platelets'] < 150 else 0, axis=1
    ),
    'neurological_dysfunction_score': lambda df: (15 - df['glasgow_coma_scale']) / 12,
    
    # Sepsis pattern features
    'qsofa_score': lambda df: (
        (df['respiratory_rate'] >= 22).astype(int) +
        (df['systolic_bp'] <= 100).astype(int) +
        (df['glasgow_coma_scale'] < 15).astype(int)
    ),
    'temperature_deviation': lambda df: (df['temperature'] - 37.0).abs(),
    'sirs_score': lambda df: (
        ((df['temperature'] > 38.0) | (df['temperature'] < 36.0)).astype(int) +
        (df['heart_rate'] > 90).astype(int) +
        (df['respiratory_rate'] > 20).astype(int)
    ),
    
    # Support intervention features
    'oxygen_dependency': lambda df: df['fio2'] - 0.21,
    'life_support_score': lambda df: (
        df.get('mechanical_ventilation', 0).astype(int) * 3 +
        (df.get('norepinephrine', 0) + df.get('epinephrine', 0) > 0).astype(int) * 3
    ),
}

FEATURE_DEPENDENCIES = {
    # Hemodynamic features
    'shock_index': ['heart_rate', 'systolic_bp'],
    'modified_shock_index': ['heart_rate', 'mean_arterial_pressure'],
    'age_shock_index': ['heart_rate', 'systolic_bp', 'age'],
    'pulse_pressure': ['systolic_bp', 'diastolic_bp'],
    'pulse_pressure_ratio': ['systolic_bp', 'diastolic_bp'],
    'perfusion_pressure': ['mean_arterial_pressure'],
    'vasopressor_load': ['norepinephrine', 'epinephrine', 'dopamine', 'dobutamine', 'phenylephrine'],
    
    # Respiratory features
    'pf_ratio': ['pao2', 'fio2'],
    'oxygenation_index': ['pao2', 'fio2'],
    'hypoxemic_index': ['oxygen_saturation'],
    'work_of_breathing': ['respiratory_rate', 'fio2', 'oxygen_saturation'],
    
    # Organ dysfunction features
    'aki_risk_score': ['creatinine'],
    'estimated_gfr': ['creatinine', 'age'],
    'hepatic_dysfunction_score': ['bilirubin'],
    'coagulopathy_score': ['platelets'],
    'neurological_dysfunction_score': ['glasgow_coma_scale'],
    
    # Sepsis pattern features
    'qsofa_score': ['respiratory_rate', 'systolic_bp', 'glasgow_coma_scale'],
    'temperature_deviation': ['temperature'],
    'sirs_score': ['temperature', 'heart_rate', 'respiratory_rate'],
    
    # Support intervention features
    'oxygen_dependency': ['fio2'],
    'life_support_score': ['mechanical_ventilation', 'norepinephrine', 'epinephrine'],
    
    # Derived features with multiple dependencies
    'organ_failure_count': ['creatinine', 'bilirubin', 'platelets', 'glasgow_coma_scale', 'pao2', 'fio2', 'mean_arterial_pressure'],
    'critical_illness_score': ['organ_failure_count', 'life_support_score'],
    'hypotension_severity': ['mean_arterial_pressure'],
    'tachycardia_severity': ['heart_rate'],
    'respiratory_support_score': ['supplemental_oxygen', 'mechanical_ventilation', 'fio2'],
    'septic_shock_pattern': ['mean_arterial_pressure', 'vasopressor_load', 'lactate'],
}

VALIDATION_RULES = {
    # Vital signs
    'temperature': {'min': 30.0, 'max': 45.0, 'unit': '°C'},
    'heart_rate': {'min': 20, 'max': 300, 'unit': 'bpm'},
    'systolic_bp': {'min': 40, 'max': 300, 'unit': 'mmHg'},
    'diastolic_bp': {'min': 20, 'max': 200, 'unit': 'mmHg'},
    'mean_arterial_pressure': {'min': 40, 'max': 150, 'unit': 'mmHg'},
    'respiratory_rate': {'min': 5, 'max': 60, 'unit': 'breaths/min'},
    'oxygen_saturation': {'min': 50, 'max': 100, 'unit': '%'},
    
    # Neurological
    'glasgow_coma_scale': {'min': 3, 'max': 15, 'unit': 'score'},
    
    # Laboratory values
    'creatinine': {'min': 0.1, 'max': 25.0, 'unit': 'mg/dL'},
    'bilirubin': {'min': 0.1, 'max': 50.0, 'unit': 'mg/dL'},
    'platelets': {'min': 1, 'max': 1000, 'unit': '×10³/μL'},
    'lactate': {'min': 0.5, 'max': 30.0, 'unit': 'mmol/L'},
    'albumin': {'min': 1.0, 'max': 6.0, 'unit': 'g/dL'},
    'hemoglobin': {'min': 3.0, 'max': 25.0, 'unit': 'g/dL'},
    'white_blood_cells': {'min': 0.5, 'max': 100.0, 'unit': '×10³/μL'},
    
    # Respiratory parameters
    'pao2': {'min': 30, 'max': 600, 'unit': 'mmHg'},
    'fio2': {'min': 0.21, 'max': 1.0, 'unit': 'fraction'},
    'paco2': {'min': 15, 'max': 100, 'unit': 'mmHg'},
    'ph': {'min': 6.8, 'max': 7.8, 'unit': 'pH'},
    'bicarbonate': {'min': 5, 'max': 50, 'unit': 'mmol/L'},
    
    # Fluid balance
    'urine_output_24h': {'min': 0, 'max': 8000, 'unit': 'mL'},
    'fluid_balance_24h': {'min': -5000, 'max': 10000, 'unit': 'mL'},
    
    # Vasopressors (mcg/kg/min)
    'norepinephrine': {'min': 0, 'max': 5.0, 'unit': 'mcg/kg/min'},
    'epinephrine': {'min': 0, 'max': 2.0, 'unit': 'mcg/kg/min'},
    'dopamine': {'min': 0, 'max': 50.0, 'unit': 'mcg/kg/min'},
    'dobutamine': {'min': 0, 'max': 40.0, 'unit': 'mcg/kg/min'},
    'phenylephrine': {'min': 0, 'max': 20.0, 'unit': 'mcg/kg/min'},
    'vasopressin': {'min': 0, 'max': 10.0, 'unit': 'units/hr'},
    
    # Demographics
    'age': {'min': 0, 'max': 120, 'unit': 'years'},
    'weight': {'min': 1, 'max': 300, 'unit': 'kg'},
    'height': {'min': 30, 'max': 250, 'unit': 'cm'},
    'bmi': {'min': 10, 'max': 80, 'unit': 'kg/m²'},
    
    # Derived feature validation ranges
    'shock_index': {'min': 0.1, 'max': 5.0, 'unit': 'ratio'},
    'pf_ratio': {'min': 50, 'max': 600, 'unit': 'mmHg'},
    'organ_failure_count': {'min': 0, 'max': 6, 'unit': 'count'},
    'qsofa_score': {'min': 0, 'max': 3, 'unit': 'score'},
    'sirs_score': {'min': 0, 'max': 4, 'unit': 'score'},
    'sofa_score': {'min': 0, 'max': 24, 'unit': 'score'},
    'news2_score': {'min': 0, 'max': 20, 'unit': 'score'},
}