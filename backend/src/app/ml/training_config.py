"""
Training Configuration Management for Sepsis ML Model

Centralized configuration for:
- Hyperparameter grids and optimization
- Cross-validation settings  
- Feature selection parameters
- Model evaluation metrics
- Clinical validation thresholds
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class ModelType(Enum):
    """Supported model types for training."""
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    RANDOM_FOREST = "random_forest"

class OptimizationStrategy(Enum):
    """Hyperparameter optimization strategies."""
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search" 
    BAYESIAN = "bayesian"
    NONE = "none"

@dataclass
class DataConfig:
    """Configuration for data generation and processing."""
    n_patients: int = 1000
    time_window_hours: int = 48
    test_size: float = 0.2
    val_size: float = 0.2
    random_state: int = 42
    
    # Early detection configuration
    early_detection_hours: int = 6  # Predict sepsis N hours early
    min_observation_hours: int = 4  # Minimum observation before prediction
    
    # Data quality filters
    min_data_completeness: float = 0.7  # Minimum feature completeness
    max_missing_critical_params: int = 2  # Max missing critical parameters

@dataclass
class FeatureConfig:
    """Configuration for feature engineering and selection."""
    use_advanced_features: bool = True
    feature_selection_method: Optional[str] = None  # 'univariate', 'recursive', None
    max_features: Optional[int] = None  # Maximum features to select
    
    # Feature categories to include/exclude
    include_hemodynamic: bool = True
    include_respiratory: bool = True
    include_organ_dysfunction: bool = True
    include_sepsis_patterns: bool = True
    include_support_features: bool = True
    include_raw_features: bool = True
    
    # Feature engineering parameters
    age_stratification: bool = True
    personalized_thresholds: bool = True
    interaction_features: bool = True

@dataclass 
class ModelConfig:
    """Configuration for model training and architecture."""
    model_type: ModelType = ModelType.XGBOOST
    optimization_strategy: OptimizationStrategy = OptimizationStrategy.GRID_SEARCH
    
    # Cross-validation settings
    cv_folds: int = 3
    cv_scoring: str = 'roc_auc'
    
    # Early stopping
    early_stopping_rounds: int = 20
    eval_metric: str = 'auc'
    
    # Class balance handling
    handle_imbalance: bool = True
    class_weight: str = 'balanced'  # 'balanced', 'balanced_subsample', or None

@dataclass
class EvaluationConfig:
    """Configuration for model evaluation and validation."""
    
    # Primary evaluation metrics
    primary_metric: str = 'auc_roc'
    clinical_threshold: float = 0.5  # Default classification threshold
    
    # Clinical performance targets
    target_sensitivity: float = 0.80  # Target sensitivity (recall)
    target_specificity: float = 0.90  # Target specificity  
    min_ppv: float = 0.30  # Minimum positive predictive value
    min_npv: float = 0.95  # Minimum negative predictive value
    
    # Early detection validation
    early_detection_window: int = 6  # Hours before traditional alert
    early_detection_target_auc: float = 0.75  # Target AUC for early detection
    
    # Feature importance analysis
    analyze_feature_importance: bool = True
    use_shap_values: bool = True
    top_features_count: int = 20

class TrainingConfig:
    """
    Complete training configuration combining all settings.
    Provides default configurations and validation.
    """
    
    def __init__(self,
                 data_config: Optional[DataConfig] = None,
                 feature_config: Optional[FeatureConfig] = None,
                 model_config: Optional[ModelConfig] = None,
                 evaluation_config: Optional[EvaluationConfig] = None):
        
        self.data = data_config or DataConfig()
        self.features = feature_config or FeatureConfig()
        self.model = model_config or ModelConfig()
        self.evaluation = evaluation_config or EvaluationConfig()
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration settings for consistency."""
        
        # Data validation
        if self.data.test_size + self.data.val_size >= 1.0:
            raise ValueError("test_size + val_size must be < 1.0")
        
        if self.data.early_detection_hours < self.data.min_observation_hours:
            raise ValueError("early_detection_hours must be >= min_observation_hours")
        
        # Feature validation
        if self.features.max_features is not None and self.features.max_features < 10:
            raise ValueError("max_features should be at least 10 for clinical prediction")
        
        # Model validation
        if self.model.cv_folds < 2:
            raise ValueError("cv_folds must be at least 2")
        
        # Evaluation validation  
        if not 0 < self.evaluation.clinical_threshold < 1:
            raise ValueError("clinical_threshold must be between 0 and 1")
    
    def get_xgboost_param_grid(self) -> Dict[str, List[Any]]:
        """Get XGBoost hyperparameter grid for optimization."""
        
        if self.model.optimization_strategy == OptimizationStrategy.GRID_SEARCH:
            return {
                'n_estimators': [100, 200, 300],
                'max_depth': [3, 4, 5, 6],
                'learning_rate': [0.01, 0.1, 0.2],
                'subsample': [0.8, 0.9, 1.0],
                'colsample_bytree': [0.8, 0.9, 1.0],
                'reg_alpha': [0, 0.1, 1],
                'reg_lambda': [1, 1.5, 2],
                'scale_pos_weight': [1, 2, 3] if self.model.handle_imbalance else [1]
            }
        
        elif self.model.optimization_strategy == OptimizationStrategy.RANDOM_SEARCH:
            return {
                'n_estimators': list(range(50, 500, 25)),
                'max_depth': list(range(3, 10)),
                'learning_rate': [0.01, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3],
                'subsample': [0.6, 0.7, 0.8, 0.9, 1.0],
                'colsample_bytree': [0.6, 0.7, 0.8, 0.9, 1.0],
                'reg_alpha': [0, 0.1, 0.5, 1, 2],
                'reg_lambda': [0.5, 1, 1.5, 2, 3],
                'scale_pos_weight': list(range(1, 10)) if self.model.handle_imbalance else [1]
            }
        
        else:
            # Default parameters for no optimization
            return {
                'n_estimators': [200],
                'max_depth': [4],
                'learning_rate': [0.1],
                'subsample': [0.9],
                'colsample_bytree': [0.9],
                'reg_alpha': [0.1],
                'reg_lambda': [1],
                'scale_pos_weight': [2] if self.model.handle_imbalance else [1]
            }
    
    def get_base_model_params(self) -> Dict[str, Any]:
        """Get base model parameters that don't change during optimization."""
        
        base_params = {
            'objective': 'binary:logistic',
            'eval_metric': self.model.eval_metric,
            'random_state': self.data.random_state,
            'n_jobs': -1,
            'verbosity': 0
        }
        
        if self.model.handle_imbalance:
            # Calculate class weights based on data
            # This would be updated during training with actual class distribution
            base_params['scale_pos_weight'] = 5  # Approximate for 15% positive class
        
        return base_params
    
    def get_evaluation_metrics(self) -> List[str]:
        """Get list of evaluation metrics to calculate."""
        
        metrics = [
            'auc_roc', 'auc_pr', 'precision', 'recall', 'f1_score',
            'sensitivity', 'specificity', 'ppv', 'npv', 'accuracy'
        ]
        
        if self.evaluation.analyze_feature_importance:
            metrics.extend(['feature_importance', 'permutation_importance'])
        
        if self.evaluation.use_shap_values:
            metrics.append('shap_values')
        
        return metrics
    
    def get_clinical_thresholds(self) -> Dict[str, float]:
        """Get clinical performance thresholds for validation."""
        
        return {
            'min_sensitivity': self.evaluation.target_sensitivity,
            'min_specificity': self.evaluation.target_specificity,
            'min_ppv': self.evaluation.min_ppv,
            'min_npv': self.evaluation.min_npv,
            'min_auc': self.evaluation.early_detection_target_auc,
            'classification_threshold': self.evaluation.clinical_threshold
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        
        return {
            'data_config': {
                'n_patients': self.data.n_patients,
                'time_window_hours': self.data.time_window_hours,
                'test_size': self.data.test_size,
                'val_size': self.data.val_size,
                'random_state': self.data.random_state,
                'early_detection_hours': self.data.early_detection_hours,
                'min_observation_hours': self.data.min_observation_hours,
                'min_data_completeness': self.data.min_data_completeness,
                'max_missing_critical_params': self.data.max_missing_critical_params
            },
            'feature_config': {
                'use_advanced_features': self.features.use_advanced_features,
                'feature_selection_method': self.features.feature_selection_method,
                'max_features': self.features.max_features,
                'include_hemodynamic': self.features.include_hemodynamic,
                'include_respiratory': self.features.include_respiratory,
                'include_organ_dysfunction': self.features.include_organ_dysfunction,
                'include_sepsis_patterns': self.features.include_sepsis_patterns,
                'include_support_features': self.features.include_support_features,
                'include_raw_features': self.features.include_raw_features,
                'age_stratification': self.features.age_stratification,
                'personalized_thresholds': self.features.personalized_thresholds,
                'interaction_features': self.features.interaction_features
            },
            'model_config': {
                'model_type': self.model.model_type.value,
                'optimization_strategy': self.model.optimization_strategy.value,
                'cv_folds': self.model.cv_folds,
                'cv_scoring': self.model.cv_scoring,
                'early_stopping_rounds': self.model.early_stopping_rounds,
                'eval_metric': self.model.eval_metric,
                'handle_imbalance': self.model.handle_imbalance,
                'class_weight': self.model.class_weight
            },
            'evaluation_config': {
                'primary_metric': self.evaluation.primary_metric,
                'clinical_threshold': self.evaluation.clinical_threshold,
                'target_sensitivity': self.evaluation.target_sensitivity,
                'target_specificity': self.evaluation.target_specificity,
                'min_ppv': self.evaluation.min_ppv,
                'min_npv': self.evaluation.min_npv,
                'early_detection_window': self.evaluation.early_detection_window,
                'early_detection_target_auc': self.evaluation.early_detection_target_auc,
                'analyze_feature_importance': self.evaluation.analyze_feature_importance,
                'use_shap_values': self.evaluation.use_shap_values,
                'top_features_count': self.evaluation.top_features_count
            }
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'TrainingConfig':
        """Create TrainingConfig from dictionary."""
        
        data_config = DataConfig(**config_dict.get('data_config', {}))
        feature_config = FeatureConfig(**config_dict.get('feature_config', {}))
        
        model_dict = config_dict.get('model_config', {})
        if 'model_type' in model_dict:
            model_dict['model_type'] = ModelType(model_dict['model_type'])
        if 'optimization_strategy' in model_dict:
            model_dict['optimization_strategy'] = OptimizationStrategy(model_dict['optimization_strategy'])
        model_config = ModelConfig(**model_dict)
        
        evaluation_config = EvaluationConfig(**config_dict.get('evaluation_config', {}))
        
        return cls(data_config, feature_config, model_config, evaluation_config)

# Predefined configurations for different use cases

class PredefinedConfigs:
    """Predefined training configurations for common scenarios."""
    
    @staticmethod
    def development_config() -> TrainingConfig:
        """Fast configuration for development and testing."""
        return TrainingConfig(
            data_config=DataConfig(
                n_patients=100,  # Small dataset for speed
                time_window_hours=24
            ),
            model_config=ModelConfig(
                optimization_strategy=OptimizationStrategy.NONE,
                cv_folds=2  # Minimal CV
            ),
            evaluation_config=EvaluationConfig(
                use_shap_values=False  # Skip expensive analysis
            )
        )
    
    @staticmethod
    def production_config() -> TrainingConfig:
        """Full configuration for production model training."""
        return TrainingConfig(
            data_config=DataConfig(
                n_patients=2000,  # Large dataset
                time_window_hours=48
            ),
            model_config=ModelConfig(
                optimization_strategy=OptimizationStrategy.GRID_SEARCH,
                cv_folds=5  # Full cross-validation
            ),
            evaluation_config=EvaluationConfig(
                use_shap_values=True,  # Full interpretability analysis
                target_sensitivity=0.85,
                target_specificity=0.90
            )
        )
    
    @staticmethod
    def early_detection_config() -> TrainingConfig:
        """Configuration optimized for early sepsis detection."""
        return TrainingConfig(
            data_config=DataConfig(
                n_patients=1500,
                early_detection_hours=6,  # 6-hour early prediction
                min_observation_hours=4
            ),
            feature_config=FeatureConfig(
                personalized_thresholds=True,
                interaction_features=True  # Enable complex patterns
            ),
            model_config=ModelConfig(
                optimization_strategy=OptimizationStrategy.BAYESIAN,  # Advanced optimization
                handle_imbalance=True
            ),
            evaluation_config=EvaluationConfig(
                early_detection_target_auc=0.80,  # Higher target for early detection
                target_sensitivity=0.80,
                use_shap_values=True
            )
        )
    
    @staticmethod
    def interpretability_config() -> TrainingConfig:
        """Configuration focused on model interpretability and clinical validation."""
        return TrainingConfig(
            feature_config=FeatureConfig(
                max_features=30,  # Limit features for interpretability
                feature_selection_method='univariate'
            ),
            model_config=ModelConfig(
                optimization_strategy=OptimizationStrategy.GRID_SEARCH
            ),
            evaluation_config=EvaluationConfig(
                analyze_feature_importance=True,
                use_shap_values=True,
                top_features_count=15  # Focus on top features
            )
        )

if __name__ == "__main__":
    # Example usage
    config = PredefinedConfigs.production_config()
    print("Production config created:")
    print(f"Patients: {config.data.n_patients}")
    print(f"Optimization: {config.model.optimization_strategy.value}")
    print(f"Target sensitivity: {config.evaluation.target_sensitivity}")
    
    # Save configuration
    import json
    with open("training_config.json", "w") as f:
        json.dump(config.to_dict(), f, indent=2)