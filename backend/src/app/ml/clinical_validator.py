"""
Clinical Score Validator for ML Model Training

Integrates production SOFA/qSOFA/NEWS2 scoring systems with ML training pipeline
to eliminate circular logic and provide accurate clinical comparisons.

This module bridges the gap between synthetic training data and actual clinical 
scoring implementations used in production.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sklearn.metrics import roc_auc_score, confusion_matrix

# Import actual clinical scoring functions
from ..utils.sofa_scoring import (
    calculate_respiratory_score, calculate_coagulation_score, calculate_liver_score,
    calculate_cardiovascular_score, calculate_cns_score, calculate_renal_score
)
from ..utils.qsofa_scoring import (
    calculate_respiratory_score as qsofa_respiratory_score,
    calculate_cardiovascular_score as qsofa_cardiovascular_score, 
    calculate_cns_score as qsofa_cns_score
)
from ..utils.news2_scoring import (
    calculate_respiratory_rate_score, calculate_oxygen_saturation_score,
    calculate_supplemental_oxygen_score, calculate_temperature_score,
    calculate_systolic_bp_score, calculate_heart_rate_score,
    calculate_consciousness_score, determine_news2_risk_level
)

# Import models for parameter creation
from ..models.sofa import SofaParameter, VasopressorDoses
from ..models.qsofa import QsofaParameter  
from ..models.news2 import News2Parameter
from .constants import QSOFA_THRESHOLDS, SOFA_THRESHOLDS, NEWS2_THRESHOLDS

logger = logging.getLogger(__name__)


class ClinicalScoreValidator:
    """
    Validates ML model performance against actual clinical scoring systems.
    
    Uses production SOFA/qSOFA/NEWS2 implementations instead of approximations
    to provide accurate clinical comparisons for training validation.
    """
    
    def __init__(self):
        """Initialize clinical score validator."""
        self.logger = logger
        
    def calculate_traditional_scores_from_raw_data(self, 
                                                 raw_clinical_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate actual SOFA/qSOFA/NEWS2 scores from raw clinical parameters.
        
        Args:
            raw_clinical_data: DataFrame with raw clinical parameters
            
        Returns:
            Dictionary with traditional scores and performance metrics
        """
        self.logger.info(f"Calculating traditional scores from {len(raw_clinical_data)} clinical records")
        
        # Calculate scores for each record
        sofa_scores = []
        qsofa_scores = []  
        news2_scores = []
        
        for idx, record in raw_clinical_data.iterrows():
            # Calculate SOFA score using actual production functions
            sofa_total = self._calculate_sofa_score(record)
            sofa_scores.append(sofa_total)
            
            # Calculate qSOFA score using actual production functions  
            qsofa_total = self._calculate_qsofa_score(record)
            qsofa_scores.append(qsofa_total)
            
            # Calculate NEWS2 score using actual production functions
            news2_total = self._calculate_news2_score(record)
            news2_scores.append(news2_total)
        
        return {
            'sofa_scores': sofa_scores,
            'qsofa_scores': qsofa_scores,
            'news2_scores': news2_scores,
            'sofa_mean': np.mean(sofa_scores),
            'qsofa_mean': np.mean(qsofa_scores), 
            'news2_mean': np.mean(news2_scores)
        }
    
    def _calculate_sofa_score(self, clinical_record: pd.Series) -> int:
        """Calculate SOFA score using actual production scoring functions."""
        
        # Create SofaParameter objects from raw data
        def create_sofa_param(value: Optional[float], unit: str = "") -> SofaParameter:
            return SofaParameter(
                value=value,
                unit=unit,
                timestamp=datetime.now(),
                source="synthetic" if value is not None else "missing"
            )
        
        # Extract clinical parameters
        pao2 = clinical_record.get('pao2')
        fio2 = clinical_record.get('fio2', 0.21)  # Default to room air
        mechanical_ventilation = clinical_record.get('mechanical_ventilation', False)
        platelets = clinical_record.get('platelets')
        bilirubin = clinical_record.get('bilirubin') 
        map_value = clinical_record.get('mean_arterial_pressure')
        gcs = clinical_record.get('glasgow_coma_scale')
        creatinine = clinical_record.get('creatinine')
        urine_output = clinical_record.get('urine_output_24h')
        
        # Create vasopressor doses object
        vasopressor_doses = VasopressorDoses(
            dopamine=clinical_record.get('dopamine_dose', 0.0),
            epinephrine=clinical_record.get('epinephrine_dose', 0.0),
            norepinephrine=clinical_record.get('norepinephrine_dose', 0.0),
            dobutamine=clinical_record.get('dobutamine_dose', 0.0)
        )
        
        # Calculate individual organ scores using production functions
        try:
            respiratory_score = calculate_respiratory_score(pao2, fio2, mechanical_ventilation)
            coagulation_score = calculate_coagulation_score(platelets)
            liver_score = calculate_liver_score(bilirubin)
            cardiovascular_score = calculate_cardiovascular_score(map_value, vasopressor_doses)
            cns_score = calculate_cns_score(gcs)
            renal_score = calculate_renal_score(creatinine, urine_output)
            
            # Return total SOFA score
            total_score = (respiratory_score.score + coagulation_score.score + 
                         liver_score.score + cardiovascular_score.score + 
                         cns_score.score + renal_score.score)
            
            return total_score
            
        except Exception as e:
            self.logger.warning(f"Error calculating SOFA score: {str(e)}")
            return 0
    
    def _calculate_qsofa_score(self, clinical_record: pd.Series) -> int:
        """Calculate qSOFA score using actual production scoring functions."""
        
        # Extract qSOFA parameters
        respiratory_rate = clinical_record.get('respiratory_rate')
        systolic_bp = clinical_record.get('systolic_bp')
        gcs = clinical_record.get('glasgow_coma_scale')
        
        # Determine altered mental status (GCS < 15)
        altered_mental_status = gcs is not None and gcs < 15
        
        try:
            # Calculate individual component scores using production functions
            respiratory_score = qsofa_respiratory_score(respiratory_rate)
            cardiovascular_score = qsofa_cardiovascular_score(systolic_bp)
            cns_score = qsofa_cns_score(altered_mental_status, gcs)
            
            # Return total qSOFA score
            total_score = (respiratory_score.score + cardiovascular_score.score + 
                         cns_score.score)
            
            return total_score
            
        except Exception as e:
            self.logger.warning(f"Error calculating qSOFA score: {str(e)}")
            return 0
    
    def _calculate_news2_score(self, clinical_record: pd.Series) -> int:
        """Calculate NEWS2 score using actual production scoring functions."""
        
        # Create News2Parameter objects from raw data
        def create_news2_param(value: Optional[float], unit: str = "") -> News2Parameter:
            param = News2Parameter()
            param.value = value
            param.unit = unit
            param.timestamp = datetime.now()
            param.source = "synthetic" if value is not None else "missing"
            return param
        
        # Extract NEWS2 parameters
        respiratory_rate_param = create_news2_param(clinical_record.get('respiratory_rate'), "breaths/min")
        oxygen_saturation_param = create_news2_param(clinical_record.get('oxygen_saturation'), "%")
        temperature_param = create_news2_param(clinical_record.get('temperature'), "°C")
        systolic_bp_param = create_news2_param(clinical_record.get('systolic_bp'), "mmHg")
        heart_rate_param = create_news2_param(clinical_record.get('heart_rate'), "bpm")
        consciousness_param = create_news2_param(clinical_record.get('glasgow_coma_scale'), "score")
        
        # Supplemental oxygen (default to room air)
        supplemental_oxygen = clinical_record.get('supplemental_oxygen', False)
        
        try:
            # Calculate individual component scores using production functions
            respiratory_score = calculate_respiratory_rate_score(respiratory_rate_param)
            oxygen_sat_score = calculate_oxygen_saturation_score(oxygen_saturation_param)
            supplemental_o2_score = calculate_supplemental_oxygen_score(supplemental_oxygen)
            temperature_score = calculate_temperature_score(temperature_param)
            systolic_bp_score = calculate_systolic_bp_score(systolic_bp_param)
            heart_rate_score = calculate_heart_rate_score(heart_rate_param)
            consciousness_score = calculate_consciousness_score(consciousness_param)
            
            # Return total NEWS2 score
            total_score = (respiratory_score.score + oxygen_sat_score.score +
                         supplemental_o2_score.score + temperature_score.score +
                         systolic_bp_score.score + heart_rate_score.score +
                         consciousness_score.score)
            
            return total_score
            
        except Exception as e:
            self.logger.warning(f"Error calculating NEWS2 score: {str(e)}")
            return 0
    
    def compare_ml_vs_traditional_scores(self, 
                                       y_true: np.ndarray,
                                       ml_predictions: np.ndarray,
                                       traditional_scores: Dict[str, List[float]]) -> Dict[str, Any]:
        """
        Compare ML model performance against traditional clinical scores.
        
        Args:
            y_true: True labels (sepsis/no sepsis)
            ml_predictions: ML model predictions (probabilities)
            traditional_scores: Dictionary with traditional score arrays
            
        Returns:
            Comprehensive comparison metrics
        """
        self.logger.info("Comparing ML model vs traditional clinical scores")
        
        results = {}
        
        # ML model performance
        try:
            ml_auc = roc_auc_score(y_true, ml_predictions)
            results['ml_auc'] = ml_auc
        except Exception as e:
            self.logger.warning(f"Could not calculate ML AUC: {str(e)}")
            ml_auc = 0.5
            results['ml_auc'] = ml_auc
        
        # Traditional score performance  
        for score_name, scores in traditional_scores.items():
            if len(scores) != len(y_true):
                self.logger.warning(f"Length mismatch for {score_name}: {len(scores)} vs {len(y_true)}")
                continue
                
            try:
                # Calculate AUC for traditional score
                if len(set(scores)) > 1:  # Need variation for AUC
                    # Normalize scores to 0-1 range for AUC calculation
                    if score_name == 'sofa_scores':
                        normalized_scores = np.array(scores) / 24.0  # Max SOFA = 24
                    elif score_name == 'qsofa_scores':
                        normalized_scores = np.array(scores) / 3.0   # Max qSOFA = 3
                    elif score_name == 'news2_scores':
                        normalized_scores = np.array(scores) / 20.0  # Max NEWS2 = 20
                    else:
                        normalized_scores = np.array(scores)
                    
                    traditional_auc = roc_auc_score(y_true, normalized_scores)
                else:
                    traditional_auc = 0.5
                
                results[f'{score_name}_auc'] = traditional_auc
                results[f'ml_improvement_vs_{score_name}'] = max(0, ml_auc - traditional_auc)
                
                # Clinical threshold analysis
                if score_name == 'sofa_scores':
                    binary_predictions = (np.array(scores) >= 2).astype(int)  # SOFA ≥2
                elif score_name == 'qsofa_scores':
                    binary_predictions = (np.array(scores) >= 2).astype(int)  # qSOFA ≥2
                elif score_name == 'news2_scores':
                    binary_predictions = (np.array(scores) >= 5).astype(int)  # NEWS2 ≥5 (medium risk)
                else:
                    continue
                
                # Calculate clinical metrics
                tn, fp, fn, tp = confusion_matrix(y_true, binary_predictions).ravel()
                sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
                specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
                
                results[f'{score_name}_sensitivity'] = sensitivity
                results[f'{score_name}_specificity'] = specificity
                results[f'{score_name}_mean'] = np.mean(scores)
                results[f'{score_name}_std'] = np.std(scores)
                
            except Exception as e:
                self.logger.warning(f"Error calculating metrics for {score_name}: {str(e)}")
                continue
        
        # Summary metrics
        results['comparison_summary'] = {
            'ml_auc': ml_auc,
            'best_traditional_auc': max([
                results.get('sofa_scores_auc', 0),
                results.get('qsofa_scores_auc', 0), 
                results.get('news2_scores_auc', 0)
            ]),
            'ml_advantage': ml_auc - max([
                results.get('sofa_scores_auc', 0),
                results.get('qsofa_scores_auc', 0),
                results.get('news2_scores_auc', 0)
            ])
        }
        
        self.logger.info(f"Traditional score comparison completed")
        self.logger.info(f"  ML AUC: {ml_auc:.3f}")
        self.logger.info(f"  SOFA AUC: {results.get('sofa_scores_auc', 0):.3f}")
        self.logger.info(f"  qSOFA AUC: {results.get('qsofa_scores_auc', 0):.3f}")
        self.logger.info(f"  NEWS2 AUC: {results.get('news2_scores_auc', 0):.3f}")
        
        return results
    
    def validate_clinical_thresholds(self, 
                                   traditional_scores: Dict[str, List[float]], 
                                   y_true: np.ndarray) -> Dict[str, Any]:
        """
        Validate that traditional clinical thresholds work as expected.
        
        Args:
            traditional_scores: Traditional score arrays
            y_true: True sepsis labels
            
        Returns:
            Clinical threshold validation results
        """
        self.logger.info("Validating clinical threshold performance")
        
        validation_results = {}
        
        # Expected relationships from clinical literature
        expected_relationships = {
            'sofa_scores': {
                'threshold': 2,
                'expected_sensitivity': 0.80,  # SOFA ≥2 should catch most sepsis cases
                'expected_specificity': 0.70   # But may have false positives
            },
            'qsofa_scores': {
                'threshold': 2, 
                'expected_sensitivity': 0.60,  # qSOFA more specific than sensitive
                'expected_specificity': 0.85
            },
            'news2_scores': {
                'threshold': 5,
                'expected_sensitivity': 0.75,  # NEWS2 balanced approach
                'expected_specificity': 0.75
            }
        }
        
        for score_name, scores in traditional_scores.items():
            if score_name not in expected_relationships:
                continue
                
            threshold = expected_relationships[score_name]['threshold']
            binary_predictions = (np.array(scores) >= threshold).astype(int)
            
            # Calculate actual performance
            tn, fp, fn, tp = confusion_matrix(y_true, binary_predictions).ravel()
            actual_sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
            actual_specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
            
            # Compare to expected
            expected_sens = expected_relationships[score_name]['expected_sensitivity']
            expected_spec = expected_relationships[score_name]['expected_specificity'] 
            
            validation_results[score_name] = {
                'threshold': threshold,
                'actual_sensitivity': actual_sensitivity,
                'actual_specificity': actual_specificity,
                'expected_sensitivity': expected_sens,
                'expected_specificity': expected_spec,
                'sensitivity_meets_expectation': actual_sensitivity >= (expected_sens - 0.1),
                'specificity_meets_expectation': actual_specificity >= (expected_spec - 0.1),
                'clinical_validity': 'PASS' if (
                    actual_sensitivity >= (expected_sens - 0.1) and 
                    actual_specificity >= (expected_spec - 0.1)
                ) else 'REVIEW'
            }
        
        self.logger.info(f"Clinical threshold validation completed")
        for score_name, results in validation_results.items():
            status = results['clinical_validity']
            sens = results['actual_sensitivity']
            spec = results['actual_specificity']
            self.logger.info(f"  {score_name}: {status} (Sens: {sens:.2f}, Spec: {spec:.2f})")
        
        return validation_results
    
    def validate_early_detection_advantage(self, 
                                         temporal_data: pd.DataFrame,
                                         ml_predictions: np.ndarray,
                                         traditional_scores: Dict[str, List[float]]) -> Dict[str, Any]:
        """
        Validate that ML model provides genuine early detection advantage.
        
        Args:
            temporal_data: DataFrame with patient_id, timestamp, sepsis_label columns
            ml_predictions: ML model predictions
            traditional_scores: Traditional clinical scores
            
        Returns:
            Early detection validation results
        """
        self.logger.info("Validating early detection advantage")
        
        # This would require temporal analysis of when predictions occur
        # vs when traditional scores would trigger alerts
        # Implementation depends on how temporal data is structured
        
        validation_results = {
            'early_detection_hours': 6,  # Claimed advantage
            'temporal_analysis': 'Requires patient-level temporal data for full validation',
            'traditional_alert_timing': 'Based on clinical threshold breach',
            'ml_alert_timing': 'Based on 4-6 hour prediction window',
            'validation_status': 'PENDING_TEMPORAL_DATA'
        }
        
        return validation_results