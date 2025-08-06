"""
Constants for ML Model Training and Evaluation

Clinical thresholds and configuration values used across the ML pipeline.
"""

# === CLINICAL SCORING THRESHOLDS ===

# NEWS2 (National Early Warning Score 2) Thresholds
NEWS2_THRESHOLDS = {
    'respiratory_rate': {
        'critical': {'min': None, 'max': 8, 'points': 3},
        'high': {'min': 9, 'max': 11, 'points': 1},
        'normal': {'min': 12, 'max': 20, 'points': 0},
        'high_upper': {'min': 21, 'max': 24, 'points': 1},
        'critical_upper': {'min': 25, 'max': None, 'points': 3}
    },
    'oxygen_saturation': {
        'critical': {'min': None, 'max': 91, 'points': 3},
        'high': {'min': 92, 'max': 93, 'points': 2},
        'medium': {'min': 94, 'max': 95, 'points': 1},
        'normal': {'min': 96, 'max': None, 'points': 0}
    },
    'systolic_bp': {
        'critical': {'min': None, 'max': 90, 'points': 3},
        'high': {'min': 91, 'max': 100, 'points': 2},
        'medium': {'min': 101, 'max': 110, 'points': 1},
        'normal': {'min': 111, 'max': None, 'points': 0}
    },
    'heart_rate': {
        'critical_low': {'min': None, 'max': 40, 'points': 3},
        'medium_low': {'min': 41, 'max': 50, 'points': 1},
        'normal': {'min': 51, 'max': 110, 'points': 0},
        'medium_high': {'min': 111, 'max': 130, 'points': 1},
        'critical_high': {'min': 131, 'max': None, 'points': 3}
    },
    'temperature': {
        'critical_low': {'min': None, 'max': 35.0, 'points': 3},
        'normal': {'min': 35.1, 'max': 39.0, 'points': 0},
        'high': {'min': 39.1, 'max': None, 'points': 2}
    }
}

# qSOFA Thresholds
QSOFA_THRESHOLDS = {
    'respiratory_rate': 22,  # ≥22 breaths/min
    'systolic_bp': 100,      # ≤100 mmHg
    'glasgow_coma_scale': 15  # <15 points
}

# SOFA Thresholds (simplified for comparison)
SOFA_THRESHOLDS = {
    'pao2_fio2_ratio': [400, 300, 200, 100],  # P/F ratio thresholds
    'platelets': [150, 100, 50, 20],          # Platelet count thresholds (x10^3/uL)
    'bilirubin': [1.2, 2.0, 6.0, 12.0],      # Bilirubin thresholds (mg/dL)
    'cardiovascular_map': [70, 70, 70, 70],   # MAP thresholds (simplified)
    'glasgow_coma_scale': [15, 13, 10, 6],    # GCS thresholds
    'creatinine': [1.2, 2.0, 3.5, 5.0]       # Creatinine thresholds (mg/dL)
}

# === ML MODEL DEFAULTS ===

# Model Performance Targets
PERFORMANCE_TARGETS = {
    'sensitivity': 0.80,      # Minimum sensitivity (recall)
    'specificity': 0.90,      # Minimum specificity
    'auc_roc': 0.85,         # Minimum AUC-ROC
    'precision': 0.70,        # Minimum precision
    'f1_score': 0.75         # Minimum F1 score
}

# Training Defaults
TRAINING_DEFAULTS = {
    'random_state': 42,
    'test_size': 0.2,
    'validation_size': 0.2,
    'cv_folds': 3,
    'early_stopping_rounds': 20
}

# Early Detection Configuration
EARLY_DETECTION = {
    'prediction_window_hours': 6,    # Predict sepsis 6 hours early
    'minimum_observation_hours': 4,  # Need at least 4 hours of data
    'early_label_window_start': 6,   # Start of early detection window
    'early_label_window_end': 4      # End of early detection window
}

# === CLINICAL PARAMETER RANGES ===

# Age-based sepsis risk (epidemiological data)
AGE_SEPSIS_RISK = {
    'young': {'age_range': (18, 39), 'sepsis_rate': 0.15},
    'middle': {'age_range': (40, 64), 'sepsis_rate': 0.25},
    'elderly': {'age_range': (65, 95), 'sepsis_rate': 0.40}
}

# Normal clinical parameter ranges
NORMAL_RANGES = {
    'heart_rate': (60, 100),           # bpm
    'respiratory_rate': (12, 20),      # breaths/min
    'systolic_bp': (110, 140),         # mmHg
    'temperature': (36.1, 37.2),       # °C
    'oxygen_saturation': (95, 100),    # %
    'glasgow_coma_scale': (15, 15),    # points
    'creatinine': (0.6, 1.2),         # mg/dL
    'platelets': (150, 400),           # x10^3/uL
    'bilirubin': (0.3, 1.2)           # mg/dL
}

# === FEATURE ENGINEERING CONSTANTS ===

# Feature Engineering Version
FEATURE_ENGINEERING_VERSION = "1.0.0"

# Number of engineered features
TOTAL_ENGINEERED_FEATURES = 76
TOTAL_RAW_FEATURES = 21

# Feature importance analysis
TOP_FEATURES_COUNT = 20
FEATURE_IMPORTANCE_CATEGORIES = [
    'hemodynamic',
    'respiratory', 
    'organ_dysfunction',
    'sepsis_patterns',
    'support_interventions',
    'raw_clinical'
]

# === EVALUATION CONSTANTS ===

# Traditional score comparison defaults (from literature)
LITERATURE_PERFORMANCE = {
    'qsofa_auc': 0.65,    # Typical qSOFA AUC from literature
    'sofa_auc': 0.70,     # Typical SOFA AUC from literature  
    'news2_auc': 0.68     # Typical NEWS2 AUC from literature
}

# Clinical validation thresholds
CLINICAL_VALIDATION = {
    'minimum_sensitivity': 0.80,
    'minimum_specificity': 0.85,
    'minimum_ppv': 0.30,
    'minimum_npv': 0.95,
    'sepsis_prevalence': 0.15  # Expected sepsis rate in ICU
}