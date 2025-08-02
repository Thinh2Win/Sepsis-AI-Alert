# app/ml/feature_engineering.py

import pandas as pd
import numpy as np
from typing import Dict, List, Union, Optional, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SepsisFeatureEngineer:
    """
    Feature engineering for sepsis prediction model.
    Ensures consistency between training and inference.
    """
    
    VERSION = "1.0.0"  # Track feature engineering version
    
    def __init__(self):
        """Initialize feature engineer with feature definitions"""
        self.feature_version = self.VERSION
        self.feature_names = []
        self._initialize_feature_definitions()
    
    def transform_parameters(self, 
                           parameters: Union[Dict, pd.DataFrame], 
                           include_metadata: bool = False) -> Union[Dict, pd.DataFrame]:
        """
        Transform raw clinical parameters into engineered features.
        
        Args:
            parameters: Raw clinical parameters (dict for single prediction, DataFrame for batch)
            include_metadata: Whether to include feature quality metadata
            
        Returns:
            Engineered features in same format as input
        """
        # Handle single prediction vs batch
        single_prediction = isinstance(parameters, dict)
        if single_prediction:
            df = pd.DataFrame([parameters])
        else:
            df = parameters.copy()
        
        # Validate and preprocess
        df = self._preprocess_parameters(df)
        
        # Engineer features by category
        features = pd.DataFrame(index=df.index)
        
        # 1. Hemodynamic features
        hemodynamic_features = self._engineer_hemodynamic_features(df)
        features = pd.concat([features, hemodynamic_features], axis=1)
        
        # 2. Respiratory features
        respiratory_features = self._engineer_respiratory_features(df)
        features = pd.concat([features, respiratory_features], axis=1)
        
        # 3. Organ dysfunction features
        organ_features = self._engineer_organ_dysfunction_features(df)
        features = pd.concat([features, organ_features], axis=1)
        
        # 4. Sepsis pattern features
        sepsis_features = self._engineer_sepsis_pattern_features(df)
        features = pd.concat([features, sepsis_features], axis=1)
        
        # 5. Support intervention features
        support_features = self._engineer_support_features(df)
        features = pd.concat([features, support_features], axis=1)
        
        # 6. Include raw features that are directly useful
        raw_features = self._select_raw_features(df)
        features = pd.concat([features, raw_features], axis=1)
        
        # Store feature names for consistency checking
        self.feature_names = features.columns.tolist()
        
        # Add metadata if requested
        if include_metadata:
            metadata = self._calculate_feature_quality_metrics(df, features)
            features = pd.concat([features, metadata], axis=1)
        
        # Return in same format as input
        if single_prediction:
            return features.iloc[0].to_dict()
        return features
    
    def _preprocess_parameters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and preprocess raw parameters"""
        df = df.copy()
        
        # Handle missing values with clinical defaults
        defaults = {
            'fio2': 0.21,  # Room air
            'glasgow_coma_scale': 15,  # Normal consciousness
            'urine_output_24h': 1500,  # Normal output
            'mechanical_ventilation': 0,
            'supplemental_oxygen': 0,
            # Vasopressors default to 0
            'dopamine': 0, 'dobutamine': 0, 'epinephrine': 0,
            'norepinephrine': 0, 'phenylephrine': 0
        }
        
        for col, default in defaults.items():
            if col in df.columns:
                df[col] = df[col].fillna(default)
        
        # Ensure MAP is calculated if missing
        if 'mean_arterial_pressure' not in df.columns or df['mean_arterial_pressure'].isna().any():
            df['mean_arterial_pressure'] = (df['systolic_bp'] + 2 * df['diastolic_bp']) / 3
        
        # Validate bounds
        df = self._apply_clinical_bounds(df)
        
        return df
    
    def _apply_clinical_bounds(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply clinically valid bounds to parameters"""
        bounds = {
            'temperature': (30.0, 45.0),
            'heart_rate': (20, 300),
            'systolic_bp': (40, 300),
            'diastolic_bp': (20, 200),
            'respiratory_rate': (5, 60),
            'oxygen_saturation': (50, 100),
            'glasgow_coma_scale': (3, 15),
            'creatinine': (0.1, 25.0),
            'bilirubin': (0.1, 50.0),
            'platelets': (1, 1000),
            'pao2': (30, 600),
            'fio2': (0.21, 1.0)
        }
        
        for col, (min_val, max_val) in bounds.items():
            if col in df.columns:
                df[col] = df[col].clip(lower=min_val, upper=max_val)
        
        return df
    
    def _engineer_hemodynamic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer hemodynamic instability features"""
        features = pd.DataFrame(index=df.index)
        
        # Shock indices
        features['shock_index'] = df['heart_rate'] / df['systolic_bp']
        features['modified_shock_index'] = df['heart_rate'] / df['mean_arterial_pressure']
        features['age_shock_index'] = features['shock_index'] * df.get('age', 60) / 60
        
        # Perfusion pressure indicators
        features['pulse_pressure'] = df['systolic_bp'] - df['diastolic_bp']
        features['pulse_pressure_ratio'] = features['pulse_pressure'] / df['systolic_bp']
        features['perfusion_pressure'] = df['mean_arterial_pressure'] - 12  # Assuming CVP ~12
        
        # Hemodynamic instability flags
        features['hypotension_severity'] = np.where(
            df['mean_arterial_pressure'] < 65, 
            (65 - df['mean_arterial_pressure']) / 65,
            0
        )
        features['severe_hypotension'] = (df['mean_arterial_pressure'] < 55).astype(int)
        features['tachycardia_severity'] = np.maximum(0, (df['heart_rate'] - 100) / 100)
        
        # Vasopressor load score (norepinephrine equivalents)
        # Based on Surviving Sepsis Campaign equivalencies
        features['vasopressor_load'] = (
            df.get('norepinephrine', 0) +
            df.get('epinephrine', 0) +
            df.get('dopamine', 0) / 100 +  # Dopamine is ~100x less potent
            df.get('dobutamine', 0) / 100 +
            df.get('phenylephrine', 0) / 10
        )
        
        features['on_vasopressors'] = (features['vasopressor_load'] > 0).astype(int)
        features['high_dose_vasopressors'] = (features['vasopressor_load'] > 0.2).astype(int)
        
        return features
    
    def _engineer_respiratory_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer respiratory dysfunction features"""
        features = pd.DataFrame(index=df.index)
        
        # P/F ratio and oxygenation
        features['pf_ratio'] = df['pao2'] / df['fio2']
        features['oxygenation_index'] = (df['fio2'] * 100) / features['pf_ratio']
        
        # ARDS severity (Berlin criteria)
        features['ards_severity'] = pd.cut(
            features['pf_ratio'],
            bins=[-np.inf, 100, 200, 300, np.inf],
            labels=[3, 2, 1, 0]  # 3=severe, 2=moderate, 1=mild, 0=none
        ).astype(int)
        
        # Hypoxemia indicators
        features['hypoxemia'] = (df['oxygen_saturation'] < 90).astype(int)
        features['severe_hypoxemia'] = (df['oxygen_saturation'] < 85).astype(int)
        features['hypoxemic_index'] = (100 - df['oxygen_saturation']) / 100
        
        # Respiratory support score
        features['respiratory_support_score'] = (
            df.get('supplemental_oxygen', 0) * 1 +
            df.get('mechanical_ventilation', 0) * 3 +
            (df['fio2'] > 0.5).astype(int) * 2
        )
        
        # Respiratory distress indicators
        features['tachypnea_severity'] = np.maximum(0, (df['respiratory_rate'] - 20) / 20)
        features['respiratory_failure'] = (
            (features['pf_ratio'] < 300) | 
            (df['respiratory_rate'] > 30) |
            (df['oxygen_saturation'] < 88)
        ).astype(int)
        
        # Work of breathing estimate
        features['work_of_breathing'] = (
            df['respiratory_rate'] * 
            (1 + (df['fio2'] - 0.21) * 2) *
            (1 + features['hypoxemic_index'])
        )
        
        return features
    
    def _engineer_organ_dysfunction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer organ dysfunction indicators"""
        features = pd.DataFrame(index=df.index)
        
        # Renal dysfunction
        features['aki_risk_score'] = np.where(
            df['creatinine'] > 1.5,
            (df['creatinine'] - 1.5) / 1.5,
            0
        )
        features['severe_aki'] = (df['creatinine'] > 3.0).astype(int)
        features['oliguria'] = (df['urine_output_24h'] < 500).astype(int)
        features['anuria'] = (df['urine_output_24h'] < 100).astype(int)
        
        # Estimated GFR (simplified MDRD)
        age = df.get('age', 60)
        features['estimated_gfr'] = 186 * (df['creatinine'] ** -1.154) * (age ** -0.203)
        
        # Hepatic dysfunction
        features['hyperbilirubinemia'] = (df['bilirubin'] > 2.0).astype(int)
        features['severe_hyperbilirubinemia'] = (df['bilirubin'] > 6.0).astype(int)
        features['hepatic_dysfunction_score'] = np.log1p(df['bilirubin'])
        
        # Coagulation dysfunction
        features['thrombocytopenia'] = (df['platelets'] < 150).astype(int)
        features['severe_thrombocytopenia'] = (df['platelets'] < 50).astype(int)
        features['coagulopathy_score'] = np.where(
            df['platelets'] < 150,
            (150 - df['platelets']) / 150,
            0
        )
        
        # Neurological dysfunction
        features['altered_mental_status'] = (df['glasgow_coma_scale'] < 15).astype(int)
        features['coma'] = (df['glasgow_coma_scale'] < 9).astype(int)
        features['neurological_dysfunction_score'] = (15 - df['glasgow_coma_scale']) / 12
        
        # Multi-organ dysfunction
        organ_failures = (
            features['severe_aki'] +
            features['severe_hyperbilirubinemia'] +
            features['severe_thrombocytopenia'] +
            features['coma'] +
            (features.get('respiratory_failure', 0) if 'respiratory_failure' in features else 0) +
            (features.get('severe_hypotension', 0) if 'severe_hypotension' in features else 0)
        )
        
        features['organ_failure_count'] = organ_failures
        features['multi_organ_failure'] = (organ_failures >= 2).astype(int)
        
        # SOFA-like continuous scores
        features['sofa_respiratory'] = pd.cut(
            df['pao2'] / df['fio2'],
            bins=[-np.inf, 100, 200, 300, 400, np.inf],
            labels=[4, 3, 2, 1, 0]
        ).astype(int)
        
        features['sofa_coagulation'] = pd.cut(
            df['platelets'],
            bins=[-np.inf, 20, 50, 100, 150, np.inf],
            labels=[4, 3, 2, 1, 0]
        ).astype(int)
        
        features['sofa_liver'] = pd.cut(
            df['bilirubin'],
            bins=[-np.inf, 1.2, 2.0, 6.0, 12.0, np.inf],
            labels=[0, 1, 2, 3, 4]
        ).astype(int)
        
        return features
    
    def _engineer_sepsis_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer specific sepsis pattern features"""
        features = pd.DataFrame(index=df.index)
        
        # qSOFA components as continuous features
        features['qsofa_respiratory_component'] = (df['respiratory_rate'] >= 22).astype(int)
        features['qsofa_bp_component'] = (df['systolic_bp'] <= 100).astype(int)
        features['qsofa_mental_component'] = (df['glasgow_coma_scale'] < 15).astype(int)
        features['qsofa_score'] = (
            features['qsofa_respiratory_component'] +
            features['qsofa_bp_component'] +
            features['qsofa_mental_component']
        )
        
        # SIRS-like features
        features['fever'] = (df['temperature'] > 38.0).astype(int)
        features['hypothermia'] = (df['temperature'] < 36.0).astype(int)
        features['temperature_abnormal'] = features['fever'] | features['hypothermia']
        features['temperature_deviation'] = np.abs(df['temperature'] - 37.0)
        
        # Inflammatory response patterns
        features['sirs_temp'] = features['temperature_abnormal']
        features['sirs_hr'] = (df['heart_rate'] > 90).astype(int)
        features['sirs_rr'] = (df['respiratory_rate'] > 20).astype(int)
        features['sirs_score'] = (
            features['sirs_temp'] +
            features['sirs_hr'] +
            features['sirs_rr']
        )
        
        # Sepsis syndrome patterns
        features['septic_shock_pattern'] = (
            (df['mean_arterial_pressure'] < 65) &
            (features.get('on_vasopressors', 0) > 0) &
            (df.get('lactate', 2) > 2)  # Use lactate if available
        ).astype(int)
        
        # Temperature-HR dissociation (relative bradycardia)
        expected_hr = 10 * (df['temperature'] - 37) + 80
        features['relative_bradycardia'] = (
            (df['heart_rate'] < expected_hr - 10) &
            (df['temperature'] > 38.3)
        ).astype(int)
        
        # Compensated vs decompensated patterns
        features['compensated_shock'] = (
            (features.get('shock_index', 0) > 0.9) &
            (df['mean_arterial_pressure'] >= 65)
        ).astype(int)
        
        features['decompensated_shock'] = (
            (features.get('shock_index', 0) > 1.0) &
            (df['mean_arterial_pressure'] < 65)
        ).astype(int)
        
        return features
    
    def _engineer_support_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer features related to supportive interventions"""
        features = pd.DataFrame(index=df.index)
        
        # Ventilation features
        features['on_mechanical_ventilation'] = df.get('mechanical_ventilation', 0)
        features['high_fio2_requirement'] = (df['fio2'] > 0.6).astype(int)
        features['oxygen_dependency'] = df['fio2'] - 0.21
        
        # Combined support score
        features['life_support_score'] = (
            features['on_mechanical_ventilation'] * 3 +
            features.get('on_vasopressors', 0) * 3 +
            features.get('aki_risk_score', 0) * 2
        )
        
        # Critical illness severity
        features['critical_illness_score'] = (
            features.get('organ_failure_count', 0) * 2 +
            features['life_support_score'] / 3
        )
        
        return features
    
    def _select_raw_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Select raw features that are directly useful for the model"""
        raw_features_to_include = [
            'heart_rate', 'systolic_bp', 'diastolic_bp', 'mean_arterial_pressure',
            'respiratory_rate', 'temperature', 'oxygen_saturation',
            'glasgow_coma_scale', 'creatinine', 'bilirubin', 'platelets',
            'pao2', 'fio2', 'urine_output_24h'
        ]
        
        # Only include features that exist in the dataframe
        available_features = [f for f in raw_features_to_include if f in df.columns]
        return df[available_features]
    
    def _calculate_feature_quality_metrics(self, 
                                         raw_df: pd.DataFrame, 
                                         features_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate metadata about feature quality and completeness"""
        metadata = pd.DataFrame(index=features_df.index)
        
        # Data completeness score
        critical_params = ['heart_rate', 'systolic_bp', 'respiratory_rate', 
                          'temperature', 'oxygen_saturation']
        available_critical = sum(1 for p in critical_params if p in raw_df.columns 
                               and not raw_df[p].isna().any())
        metadata['data_completeness_score'] = available_critical / len(critical_params)
        
        # Measurement reliability indicators
        metadata['has_invasive_monitoring'] = (
            (raw_df.get('pao2', 0) > 0) |
            (raw_df.get('mechanical_ventilation', 0) > 0)
        ).astype(int)
        
        metadata['feature_engineering_version'] = self.feature_version
        
        return metadata
    
    def get_feature_importance_groups(self) -> Dict[str, List[str]]:
        """Return features grouped by clinical category for interpretation"""
        return {
            'hemodynamic': [
                'shock_index', 'modified_shock_index', 'pulse_pressure',
                'hypotension_severity', 'vasopressor_load'
            ],
            'respiratory': [
                'pf_ratio', 'ards_severity', 'respiratory_support_score',
                'work_of_breathing'
            ],
            'organ_dysfunction': [
                'organ_failure_count', 'aki_risk_score', 'coagulopathy_score',
                'hepatic_dysfunction_score'
            ],
            'sepsis_patterns': [
                'qsofa_score', 'sirs_score', 'septic_shock_pattern',
                'temperature_deviation'
            ],
            'critical_illness': [
                'life_support_score', 'critical_illness_score'
            ]
        }
    
    def _initialize_feature_definitions(self):
        """Initialize feature definitions and metadata"""
        # This would load from feature_definitions.py
        pass
    
    def save_config(self, path: str):
        """Save feature configuration for consistency"""
        config = {
            'version': self.feature_version,
            'feature_names': self.feature_names,
            'timestamp': datetime.now().isoformat()
        }
        with open(path, 'w') as f:
            import json
            json.dump(config, f, indent=2)
    
    def load_config(self, path: str):
        """Load feature configuration"""
        with open(path, 'r') as f:
            import json
            config = json.load(f)
            self.feature_version = config['version']
            self.feature_names = config['feature_names']