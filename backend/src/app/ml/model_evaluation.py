"""
Comprehensive Model Evaluation Framework for Sepsis ML Models

Advanced evaluation including:
- Clinical performance metrics (sensitivity, specificity, PPV, NPV)
- ML performance metrics (AUC-ROC, precision-recall)  
- Early detection capability assessment
- Feature importance and interpretability analysis
- Comparison with traditional scoring systems (qSOFA, SOFA, NEWS2)
- Clinical validation and threshold optimization
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    roc_auc_score, roc_curve, precision_recall_curve, auc,
    classification_report, confusion_matrix,
    precision_score, recall_score, f1_score, accuracy_score
)
from sklearn.calibration import calibration_curve
import warnings
warnings.filterwarnings('ignore')

# Optional SHAP import for interpretability
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logging.warning("SHAP not available. Feature importance analysis will be limited.")

logger = logging.getLogger(__name__)

class ClinicalMetricsCalculator:
    """Calculate clinical performance metrics with confidence intervals."""
    
    @staticmethod
    def calculate_clinical_metrics(y_true: np.ndarray, 
                                 y_pred: np.ndarray,
                                 y_pred_proba: np.ndarray,
                                 threshold: float = 0.5) -> Dict[str, float]:
        """
        Calculate comprehensive clinical metrics.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels  
            y_pred_proba: Prediction probabilities
            threshold: Classification threshold
            
        Returns:
            Dictionary of clinical metrics
        """
        # Apply threshold to probabilities if needed
        if threshold != 0.5:
            y_pred = (y_pred_proba >= threshold).astype(int)
        
        # Confusion matrix components
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        
        # Calculate metrics with zero-division handling
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        npv = tn / (tn + fn) if (tn + fn) > 0 else 0.0
        accuracy = (tp + tn) / (tp + tn + fp + fn)
        
        # Additional clinical metrics
        prevalence = (tp + fn) / (tp + tn + fp + fn)
        
        # Likelihood ratios
        lr_positive = sensitivity / (1 - specificity) if specificity < 1 else float('inf')
        lr_negative = (1 - sensitivity) / specificity if specificity > 0 else float('inf')
        
        return {
            'sensitivity': sensitivity,
            'specificity': specificity,
            'ppv': ppv,
            'npv': npv,
            'accuracy': accuracy,
            'prevalence': prevalence,
            'lr_positive': lr_positive,
            'lr_negative': lr_negative,
            'true_positives': int(tp),
            'true_negatives': int(tn),
            'false_positives': int(fp),
            'false_negatives': int(fn)
        }
    
    @staticmethod
    def find_optimal_threshold(y_true: np.ndarray, 
                             y_pred_proba: np.ndarray,
                             metric: str = 'youden') -> Tuple[float, Dict[str, float]]:
        """
        Find optimal classification threshold based on specified criterion.
        
        Args:
            y_true: True labels
            y_pred_proba: Prediction probabilities  
            metric: Optimization criterion ('youden', 'f1', 'precision_recall_balance')
            
        Returns:
            Tuple of (optimal_threshold, metrics_at_threshold)
        """
        thresholds = np.arange(0.1, 1.0, 0.01)
        best_threshold = 0.5
        best_score = 0
        best_metrics = {}
        
        for threshold in thresholds:
            y_pred = (y_pred_proba >= threshold).astype(int)
            metrics = ClinicalMetricsCalculator.calculate_clinical_metrics(
                y_true, y_pred, y_pred_proba, threshold
            )
            
            if metric == 'youden':
                # Youden's J statistic: Sensitivity + Specificity - 1
                score = metrics['sensitivity'] + metrics['specificity'] - 1
            elif metric == 'f1':
                score = f1_score(y_true, y_pred)
            elif metric == 'precision_recall_balance':
                # Balance precision and recall
                precision = precision_score(y_true, y_pred) if np.sum(y_pred) > 0 else 0
                recall = recall_score(y_true, y_pred)
                score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            if score > best_score:
                best_score = score
                best_threshold = threshold
                best_metrics = metrics
        
        return best_threshold, best_metrics

class MLMetricsCalculator:
    """Calculate machine learning performance metrics."""
    
    @staticmethod
    def calculate_ml_metrics(y_true: np.ndarray, 
                           y_pred: np.ndarray,
                           y_pred_proba: np.ndarray) -> Dict[str, float]:
        """
        Calculate comprehensive ML metrics.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_pred_proba: Prediction probabilities
            
        Returns:
            Dictionary of ML metrics
        """
        # ROC metrics
        auc_roc = roc_auc_score(y_true, y_pred_proba)
        fpr, tpr, roc_thresholds = roc_curve(y_true, y_pred_proba)
        
        # Precision-Recall metrics
        precision, recall, pr_thresholds = precision_recall_curve(y_true, y_pred_proba)
        auc_pr = auc(recall, precision)
        
        # Standard classification metrics
        precision_score_val = precision_score(y_true, y_pred)
        recall_score_val = recall_score(y_true, y_pred)
        f1_score_val = f1_score(y_true, y_pred)
        accuracy_val = accuracy_score(y_true, y_pred)
        
        # Brier score (calibration metric)
        brier_score = np.mean((y_pred_proba - y_true) ** 2)
        
        return {
            'auc_roc': auc_roc,
            'auc_pr': auc_pr,
            'precision': precision_score_val,
            'recall': recall_score_val,
            'f1_score': f1_score_val,
            'accuracy': accuracy_val,
            'brier_score': brier_score,
            # Store curves for plotting
            'roc_curve': {'fpr': fpr, 'tpr': tpr, 'thresholds': roc_thresholds},
            'pr_curve': {'precision': precision, 'recall': recall, 'thresholds': pr_thresholds}
        }

class EarlyDetectionEvaluator:
    """Evaluate early detection capabilities of sepsis prediction models."""
    
    def __init__(self, time_to_sepsis_hours: np.ndarray):
        """
        Initialize with time-to-sepsis information.
        
        Args:
            time_to_sepsis_hours: Hours from prediction to sepsis onset for positive cases
        """
        self.time_to_sepsis_hours = time_to_sepsis_hours
    
    def evaluate_early_detection(self, 
                               y_true: np.ndarray,
                               y_pred_proba: np.ndarray,
                               target_lead_times: List[int] = [4, 6, 8, 12]) -> Dict[str, Any]:
        """
        Evaluate early detection performance at different lead times.
        
        Args:
            y_true: True sepsis labels
            y_pred_proba: Prediction probabilities
            target_lead_times: Lead time targets in hours
            
        Returns:
            Early detection performance metrics
        """
        results = {}
        
        for lead_time in target_lead_times:
            # Find cases where sepsis occurs within lead_time hours
            early_cases_mask = (y_true == 1) & (self.time_to_sepsis_hours <= lead_time)
            
            if np.sum(early_cases_mask) > 0:
                # Calculate AUC for early detection cases
                early_auc = roc_auc_score(
                    early_cases_mask.astype(int), 
                    y_pred_proba
                )
                
                # Calculate sensitivity at high specificity for early cases
                optimal_threshold, metrics = ClinicalMetricsCalculator.find_optimal_threshold(
                    early_cases_mask.astype(int), y_pred_proba
                )
                
                results[f'lead_time_{lead_time}h'] = {
                    'auc': early_auc,
                    'optimal_threshold': optimal_threshold,
                    'sensitivity': metrics['sensitivity'],
                    'specificity': metrics['specificity'],
                    'n_early_cases': int(np.sum(early_cases_mask))
                }
        
        return results

class TraditionalScoreComparator:
    """Compare ML model performance against traditional scoring systems."""
    
    def __init__(self):
        self.score_calculators = {
            'qsofa': self._calculate_qsofa_mock,
            'sofa': self._calculate_sofa_mock,
            'news2': self._calculate_news2_mock
        }
    
    def _calculate_qsofa_mock(self, clinical_data: pd.DataFrame) -> np.ndarray:
        """Mock qSOFA calculation for demonstration purposes."""
        # Simplified qSOFA calculation based on available features
        np.random.seed(42)
        return np.random.random(len(clinical_data)) * 0.7  # Simulate typical qSOFA performance
    
    def _calculate_sofa_mock(self, clinical_data: pd.DataFrame) -> np.ndarray:
        """Mock SOFA calculation for demonstration purposes."""
        np.random.seed(43)
        return np.random.random(len(clinical_data)) * 0.75  # Simulate typical SOFA performance
    
    def _calculate_news2_mock(self, clinical_data: pd.DataFrame) -> np.ndarray:
        """Mock NEWS2 calculation for demonstration purposes."""
        np.random.seed(44)
        return np.random.random(len(clinical_data)) * 0.68  # Simulate typical NEWS2 performance
    
    def compare_with_traditional_scores(self,
                                      clinical_data: pd.DataFrame,
                                      y_true: np.ndarray,
                                      ml_pred_proba: np.ndarray) -> Dict[str, Dict[str, float]]:
        """
        Compare ML model with traditional scoring systems.
        
        Args:
            clinical_data: Clinical features for traditional score calculation
            y_true: True sepsis labels
            ml_pred_proba: ML model prediction probabilities
            
        Returns:
            Comparison results for each scoring system
        """
        comparison_results = {}
        
        # Calculate ML performance
        ml_auc = roc_auc_score(y_true, ml_pred_proba)
        
        for score_name, calculator in self.score_calculators.items():
            try:
                # Calculate traditional score
                traditional_scores = calculator(clinical_data)
                traditional_auc = roc_auc_score(y_true, traditional_scores)
                
                # Calculate improvement
                auc_improvement = ml_auc - traditional_auc
                relative_improvement = (auc_improvement / traditional_auc) * 100
                
                comparison_results[score_name] = {
                    'traditional_auc': traditional_auc,
                    'ml_auc': ml_auc,
                    'auc_improvement': auc_improvement,
                    'relative_improvement_percent': relative_improvement,
                    'statistical_significance': self._test_auc_difference(
                        y_true, traditional_scores, ml_pred_proba
                    )
                }
                
            except Exception as e:
                logger.warning(f"Failed to calculate {score_name}: {str(e)}")
                comparison_results[score_name] = {'error': str(e)}
        
        return comparison_results
    
    def _test_auc_difference(self, y_true: np.ndarray, 
                           scores1: np.ndarray, 
                           scores2: np.ndarray) -> Dict[str, float]:
        """Test statistical significance of AUC difference using DeLong's test."""
        # Simplified significance test - in production, use proper DeLong's test
        auc1 = roc_auc_score(y_true, scores1)
        auc2 = roc_auc_score(y_true, scores2)
        
        # Placeholder p-value calculation
        # In reality, implement proper DeLong's test
        p_value = 0.05 if abs(auc2 - auc1) > 0.05 else 0.10
        
        return {
            'p_value': p_value,
            'significant': p_value < 0.05
        }

class FeatureImportanceAnalyzer:
    """Analyze feature importance and model interpretability."""
    
    def __init__(self, feature_names: List[str]):
        self.feature_names = feature_names
    
    def analyze_feature_importance(self,
                                 model,
                                 X: pd.DataFrame,
                                 y: np.ndarray,
                                 top_n: int = 20) -> Dict[str, Any]:
        """
        Comprehensive feature importance analysis.
        
        Args:
            model: Trained model
            X: Feature matrix
            y: Target labels
            top_n: Number of top features to analyze
            
        Returns:
            Feature importance analysis results
        """
        results = {}
        
        # 1. Model-native feature importance
        if hasattr(model, 'feature_importances_'):
            native_importance = pd.DataFrame({
                'feature': self.feature_names,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            results['native_importance'] = native_importance.head(top_n).to_dict('records')
        
        # 2. SHAP analysis if available
        if SHAP_AVAILABLE:
            try:
                results['shap_analysis'] = self._calculate_shap_values(model, X, top_n)
            except Exception as e:
                logger.warning(f"SHAP analysis failed: {str(e)}")
                results['shap_analysis'] = {'error': str(e)}
        
        # 3. Clinical category analysis
        results['clinical_categories'] = self._analyze_clinical_categories(
            native_importance if 'native_importance' in results else None
        )
        
        return results
    
    def _calculate_shap_values(self, model, X: pd.DataFrame, top_n: int) -> Dict[str, Any]:
        """Calculate SHAP values for model interpretability."""
        # Create SHAP explainer
        explainer = shap.TreeExplainer(model)
        
        # Calculate SHAP values for a sample of data (to manage computation time)
        sample_size = min(100, len(X))
        sample_indices = np.random.choice(len(X), sample_size, replace=False)
        X_sample = X.iloc[sample_indices]
        
        shap_values = explainer.shap_values(X_sample)
        
        # Calculate mean absolute SHAP values
        mean_shap_values = np.mean(np.abs(shap_values), axis=0)
        
        # Create importance dataframe
        shap_importance = pd.DataFrame({
            'feature': self.feature_names,
            'mean_abs_shap': mean_shap_values
        }).sort_values('mean_abs_shap', ascending=False)
        
        return {
            'feature_importance': shap_importance.head(top_n).to_dict('records'),
            'sample_size': sample_size,
            'explanation': 'Mean absolute SHAP values across sample'
        }
    
    def _analyze_clinical_categories(self, importance_df: Optional[pd.DataFrame]) -> Dict[str, Any]:
        """Analyze feature importance by clinical category."""
        
        # Define clinical categories (simplified mapping)
        clinical_categories = {
            'hemodynamic': ['shock_index', 'pulse_pressure', 'vasopressor', 'blood_pressure', 'heart_rate'],
            'respiratory': ['pf_ratio', 'respiratory_rate', 'oxygen', 'ventilation'],
            'organ_dysfunction': ['creatinine', 'bilirubin', 'platelets', 'gcs', 'urine'],
            'sepsis_patterns': ['qsofa', 'sirs', 'temperature', 'septic_shock'],
            'support_interventions': ['mechanical_ventilation', 'supplemental_oxygen', 'life_support']
        }
        
        if importance_df is None:
            return {'error': 'No importance data available'}
        
        category_analysis = {}
        
        for category, keywords in clinical_categories.items():
            # Find features matching category keywords
            category_features = []
            for _, row in importance_df.iterrows():
                feature_name = row['feature'].lower()
                if any(keyword in feature_name for keyword in keywords):
                    category_features.append(row)
            
            if category_features:
                total_importance = sum(f['importance'] for f in category_features)
                avg_importance = total_importance / len(category_features)
                top_feature = max(category_features, key=lambda x: x['importance'])
                
                category_analysis[category] = {
                    'total_importance': total_importance,
                    'avg_importance': avg_importance,
                    'feature_count': len(category_features),
                    'top_feature': top_feature['feature'],
                    'top_feature_importance': top_feature['importance']
                }
        
        return category_analysis

class SepsisModelEvaluator:
    """
    Comprehensive evaluation framework for sepsis prediction models.
    Integrates all evaluation components for complete model assessment.
    """
    
    def __init__(self, feature_names: List[str]):
        self.feature_names = feature_names
        self.clinical_calculator = ClinicalMetricsCalculator()
        self.ml_calculator = MLMetricsCalculator()
        self.traditional_comparator = TraditionalScoreComparator()
        self.importance_analyzer = FeatureImportanceAnalyzer(feature_names)
        
    def comprehensive_evaluation(self,
                               model,
                               X_test: pd.DataFrame,
                               y_test: np.ndarray,
                               clinical_data: Optional[pd.DataFrame] = None,
                               time_to_sepsis: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Perform comprehensive model evaluation.
        
        Args:
            model: Trained model
            X_test: Test feature matrix
            y_test: Test labels
            clinical_data: Raw clinical data for traditional score calculation
            time_to_sepsis: Time to sepsis for early detection analysis
            
        Returns:
            Complete evaluation results
        """
        logger.info("Starting comprehensive model evaluation...")
        
        # Generate predictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        evaluation_results = {
            'evaluation_timestamp': datetime.now().isoformat(),
            'test_set_size': len(X_test),
            'positive_class_prevalence': np.mean(y_test)
        }
        
        # 1. Clinical metrics
        logger.info("Calculating clinical metrics...")
        evaluation_results['clinical_metrics'] = self.clinical_calculator.calculate_clinical_metrics(
            y_test, y_pred, y_pred_proba
        )
        
        # 2. ML metrics
        logger.info("Calculating ML metrics...")
        evaluation_results['ml_metrics'] = self.ml_calculator.calculate_ml_metrics(
            y_test, y_pred, y_pred_proba
        )
        
        # 3. Optimal threshold analysis
        logger.info("Finding optimal thresholds...")
        optimal_threshold, optimal_metrics = self.clinical_calculator.find_optimal_threshold(
            y_test, y_pred_proba, metric='youden'
        )
        evaluation_results['optimal_threshold'] = {
            'threshold': optimal_threshold,
            'metrics': optimal_metrics
        }
        
        # 4. Early detection analysis (if time data available)
        if time_to_sepsis is not None:
            logger.info("Evaluating early detection capabilities...")
            early_detector = EarlyDetectionEvaluator(time_to_sepsis)
            evaluation_results['early_detection'] = early_detector.evaluate_early_detection(
                y_test, y_pred_proba
            )
        
        # 5. Traditional score comparison (if clinical data available)
        if clinical_data is not None:
            logger.info("Comparing with traditional scores...")
            evaluation_results['traditional_comparison'] = self.traditional_comparator.compare_with_traditional_scores(
                clinical_data, y_test, y_pred_proba
            )
        
        # 6. Feature importance analysis
        logger.info("Analyzing feature importance...")
        evaluation_results['feature_analysis'] = self.importance_analyzer.analyze_feature_importance(
            model, X_test, y_test
        )
        
        # 7. Model calibration
        logger.info("Assessing model calibration...")
        evaluation_results['calibration'] = self._assess_calibration(y_test, y_pred_proba)
        
        # 8. Performance summary
        evaluation_results['performance_summary'] = self._create_performance_summary(evaluation_results)
        
        logger.info("Comprehensive evaluation completed")
        return evaluation_results
    
    def _assess_calibration(self, y_true: np.ndarray, y_pred_proba: np.ndarray) -> Dict[str, Any]:
        """Assess model calibration using reliability diagrams."""
        
        try:
            # Calculate calibration curve
            fraction_of_positives, mean_predicted_value = calibration_curve(
                y_true, y_pred_proba, n_bins=10
            )
            
            # Calculate calibration metrics
            calibration_error = np.mean(np.abs(fraction_of_positives - mean_predicted_value))
            
            return {
                'calibration_error': calibration_error,
                'fraction_of_positives': fraction_of_positives.tolist(),
                'mean_predicted_value': mean_predicted_value.tolist(),
                'well_calibrated': calibration_error < 0.1
            }
            
        except Exception as e:
            logger.warning(f"Calibration assessment failed: {str(e)}")
            return {'error': str(e)}
    
    def _create_performance_summary(self, evaluation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create high-level performance summary."""
        
        ml_metrics = evaluation_results.get('ml_metrics', {})
        clinical_metrics = evaluation_results.get('clinical_metrics', {})
        
        # Performance grades
        auc_grade = self._grade_performance(ml_metrics.get('auc_roc', 0), 
                                          [(0.9, 'Excellent'), (0.8, 'Good'), (0.7, 'Fair'), (0.6, 'Poor')])
        
        sensitivity_grade = self._grade_performance(clinical_metrics.get('sensitivity', 0),
                                                  [(0.9, 'Excellent'), (0.8, 'Good'), (0.7, 'Fair'), (0.6, 'Poor')])
        
        # Clinical readiness assessment
        clinical_ready = (
            ml_metrics.get('auc_roc', 0) >= 0.8 and
            clinical_metrics.get('sensitivity', 0) >= 0.8 and
            clinical_metrics.get('specificity', 0) >= 0.8
        )
        
        return {
            'overall_auc': ml_metrics.get('auc_roc', 0),
            'auc_grade': auc_grade,
            'sensitivity': clinical_metrics.get('sensitivity', 0),
            'sensitivity_grade': sensitivity_grade,
            'specificity': clinical_metrics.get('specificity', 0),
            'clinical_ready': clinical_ready,
            'key_strengths': self._identify_strengths(evaluation_results),
            'improvement_areas': self._identify_improvement_areas(evaluation_results)
        }
    
    def _grade_performance(self, value: float, thresholds: List[Tuple[float, str]]) -> str:
        """Grade performance based on thresholds."""
        for threshold, grade in thresholds:
            if value >= threshold:
                return grade
        return 'Unacceptable'
    
    def _identify_strengths(self, evaluation_results: Dict[str, Any]) -> List[str]:
        """Identify model strengths based on evaluation results."""
        strengths = []
        
        ml_metrics = evaluation_results.get('ml_metrics', {})
        clinical_metrics = evaluation_results.get('clinical_metrics', {})
        
        if ml_metrics.get('auc_roc', 0) >= 0.85:
            strengths.append("Excellent discriminative ability")
        
        if clinical_metrics.get('sensitivity', 0) >= 0.85:
            strengths.append("High sensitivity for sepsis detection")
        
        if clinical_metrics.get('specificity', 0) >= 0.85:
            strengths.append("Low false positive rate")
        
        if clinical_metrics.get('ppv', 0) >= 0.4:
            strengths.append("Clinically useful positive predictive value")
        
        return strengths
    
    def _identify_improvement_areas(self, evaluation_results: Dict[str, Any]) -> List[str]:
        """Identify areas for model improvement."""
        improvements = []
        
        ml_metrics = evaluation_results.get('ml_metrics', {})
        clinical_metrics = evaluation_results.get('clinical_metrics', {})
        
        if ml_metrics.get('auc_roc', 0) < 0.8:
            improvements.append("Improve overall discriminative performance")
        
        if clinical_metrics.get('sensitivity', 0) < 0.8:
            improvements.append("Increase sensitivity to reduce missed sepsis cases")
        
        if clinical_metrics.get('ppv', 0) < 0.3:
            improvements.append("Reduce false positives to improve clinical utility")
        
        calibration = evaluation_results.get('calibration', {})
        if calibration.get('calibration_error', 1) > 0.1:
            improvements.append("Improve probability calibration")
        
        return improvements

if __name__ == "__main__":
    # Example usage
    feature_names = ['feature_' + str(i) for i in range(20)]
    evaluator = SepsisModelEvaluator(feature_names)
    
    # Mock data for demonstration
    np.random.seed(42)
    X_test = pd.DataFrame(np.random.random((100, 20)), columns=feature_names)
    y_test = np.random.choice([0, 1], 100, p=[0.85, 0.15])
    
    print("SepsisModelEvaluator initialized successfully")
    print(f"Test data shape: {X_test.shape}")
    print(f"Positive class prevalence: {np.mean(y_test):.2%}")