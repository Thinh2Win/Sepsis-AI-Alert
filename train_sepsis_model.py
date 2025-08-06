#!/usr/bin/env python3
"""
CLI Training Script for Sepsis ML Model

Command-line interface for training sepsis prediction models with:
- Configurable training parameters
- Multiple predefined configurations
- Comprehensive logging and progress tracking
- Model evaluation and artifact management
- Integration with existing virtual environment

Usage:
    python train_sepsis_model.py --config production
    python train_sepsis_model.py --patients 2000 --optimize
    python train_sepsis_model.py --config development --quick
"""

import argparse
import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add backend to Python path
backend_path = Path(__file__).parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

try:
    from app.ml.ml_model_trainer import SepsisMLTrainer
    from app.ml.training_config import TrainingConfig, PredefinedConfigs
    from app.ml.model_manager import ModelRegistry, ModelMetadata, ProductionModelManager
    from app.ml.model_evaluation import SepsisModelEvaluator
except ImportError as e:
    print(f"Error importing ML modules: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Setup logging configuration."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)
    
    return logging.getLogger(__name__)

def create_custom_config(args) -> TrainingConfig:
    """Create custom training configuration from command line arguments."""
    from app.ml.training_config import DataConfig, FeatureConfig, ModelConfig, EvaluationConfig, OptimizationStrategy
    
    # Data configuration
    data_config = DataConfig(
        n_patients=args.patients,
        time_window_hours=args.time_window,
        test_size=args.test_size,
        val_size=args.val_size,
        random_state=args.seed
    )
    
    # Model configuration
    optimization_strategy = OptimizationStrategy.GRID_SEARCH if args.optimize else OptimizationStrategy.NONE
    model_config = ModelConfig(
        optimization_strategy=optimization_strategy,
        cv_folds=args.cv_folds,
        handle_imbalance=args.handle_imbalance
    )
    
    # Feature configuration
    feature_config = FeatureConfig(
        max_features=args.max_features,
        use_advanced_features=args.advanced_features
    )
    
    # Evaluation configuration
    evaluation_config = EvaluationConfig(
        use_shap_values=args.shap and not args.quick,
        target_sensitivity=args.min_sensitivity,
        target_specificity=args.min_specificity
    )
    
    return TrainingConfig(data_config, feature_config, model_config, evaluation_config)

def train_model(config: TrainingConfig, 
               model_version: str,
               output_dir: str,
               logger: logging.Logger) -> dict:
    """Execute model training pipeline."""
    
    logger.info("="*60)
    logger.info("SEPSIS ML MODEL TRAINING PIPELINE")
    logger.info("="*60)
    logger.info(f"Model Version: {model_version}")
    logger.info(f"Training Configuration:")
    logger.info(f"  Patients: {config.data.n_patients}")
    logger.info(f"  Optimization: {config.model.optimization_strategy.value}")
    logger.info(f"  Features: {config.features.max_features or 'All (76)'}")
    logger.info(f"  Output: {output_dir}")
    logger.info("="*60)
    
    # Initialize trainer
    trainer = SepsisMLTrainer(
        model_version=model_version,
        random_state=config.data.random_state
    )
    
    # Execute training pipeline
    logger.info("Starting training pipeline...")
    start_time = datetime.now()
    
    try:
        # Run complete pipeline
        results = trainer.run_complete_training_pipeline(
            n_patients=config.data.n_patients,
            hyperparameter_tuning=config.model.optimization_strategy.value != 'none',
            save_artifacts=True
        )
        
        if not results['pipeline_success']:
            logger.error(f"Training failed: {results.get('error', 'Unknown error')}")
            return results
        
        training_duration = datetime.now() - start_time
        logger.info(f"Training completed in {training_duration}")
        
        # Performance summary
        auc_roc = results['evaluation_results']['ml_metrics']['auc_roc']
        sensitivity = results['evaluation_results']['clinical_metrics']['sensitivity']
        specificity = results['evaluation_results']['clinical_metrics']['specificity']
        
        logger.info("="*60)
        logger.info("TRAINING RESULTS SUMMARY")
        logger.info("="*60)
        logger.info(f"AUC-ROC:     {auc_roc:.3f}")
        logger.info(f"Sensitivity: {sensitivity:.3f}")
        logger.info(f"Specificity: {specificity:.3f}")
        logger.info(f"Features:    {results['feature_count']}")
        logger.info("="*60)
        
        # Check performance thresholds
        meets_clinical_threshold = (
            auc_roc >= config.evaluation.early_detection_target_auc and
            sensitivity >= config.evaluation.target_sensitivity and
            specificity >= config.evaluation.target_specificity
        )
        
        if meets_clinical_threshold:
            logger.info("✅ Model meets clinical performance thresholds")
        else:
            logger.warning("⚠️  Model does not meet all clinical thresholds")
        
        # Register model if successful
        if results['pipeline_success']:
            register_model_in_registry(trainer, results, config, model_version, logger)
        
        return results
        
    except Exception as e:
        logger.error(f"Training pipeline failed: {str(e)}")
        return {'pipeline_success': False, 'error': str(e)}

def register_model_in_registry(trainer: SepsisMLTrainer,
                             results: dict,
                             config: TrainingConfig,
                             model_version: str,
                             logger: logging.Logger):
    """Register trained model in model registry."""
    
    try:
        logger.info("Registering model in registry...")
        
        # Initialize registry
        registry = ModelRegistry("models/registry")
        
        # Create metadata
        metadata = ModelMetadata(
            model_id="sepsis_xgboost",
            version=model_version,
            model_type="XGBoost",
            training_timestamp=datetime.now().isoformat(),
            performance_metrics=results['evaluation_results']['ml_metrics'],
            feature_count=results['feature_count'],
            feature_names=getattr(trainer.feature_engineer, 'feature_names', []),
            training_config=config.to_dict(),
            data_config=results['training_metadata'],
            model_size_mb=0.0,  # Will be calculated during registration
            checksum="",  # Will be calculated during registration
            tags=["xgboost", "baseline", f"v{model_version}"],
            description=f"Sepsis prediction model v{model_version} trained on {config.data.n_patients} patients"
        )
        
        # Register model
        registry_path = registry.register_model(
            trainer.model,
            metadata,
            artifacts=results.get('saved_files', {})
        )
        
        logger.info(f"Model registered at: {registry_path}")
        
        # Initialize production manager
        prod_manager = ProductionModelManager(registry)
        
        # Check if model is production-ready
        auc_roc = results['evaluation_results']['ml_metrics']['auc_roc']
        if auc_roc >= 0.85:  # Production threshold
            logger.info("Model meets production criteria - consider deployment")
        
    except Exception as e:
        logger.error(f"Model registration failed: {str(e)}")

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Train Sepsis Prediction ML Model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --config production                    # Full production training
  %(prog)s --config development                   # Quick development training  
  %(prog)s --patients 2000 --optimize            # Custom training with optimization
  %(prog)s --config early_detection --shap       # Early detection with interpretability
        """
    )
    
    # Configuration options
    parser.add_argument(
        "--config", 
        choices=["production", "development", "early_detection", "interpretability"],
        help="Use predefined configuration"
    )
    
    # Data options
    parser.add_argument("--patients", type=int, default=1000, 
                       help="Number of patients to simulate (default: 1000)")
    parser.add_argument("--time-window", type=int, default=48,
                       help="Time window in hours (default: 48)")
    parser.add_argument("--test-size", type=float, default=0.2,
                       help="Test set size (default: 0.2)")
    parser.add_argument("--val-size", type=float, default=0.2,
                       help="Validation set size (default: 0.2)")
    
    # Model options
    parser.add_argument("--optimize", action="store_true",
                       help="Enable hyperparameter optimization")
    parser.add_argument("--cv-folds", type=int, default=3,
                       help="Cross-validation folds (default: 3)")
    parser.add_argument("--max-features", type=int,
                       help="Maximum features to use (default: all)")
    parser.add_argument("--no-advanced-features", dest="advanced_features", 
                       action="store_false", default=True,
                       help="Disable advanced feature engineering")
    parser.add_argument("--handle-imbalance", action="store_true", default=True,
                       help="Handle class imbalance")
    
    # Evaluation options
    parser.add_argument("--shap", action="store_true",
                       help="Enable SHAP interpretability analysis")
    parser.add_argument("--min-sensitivity", type=float, default=0.80,
                       help="Minimum required sensitivity (default: 0.80)")
    parser.add_argument("--min-specificity", type=float, default=0.80,
                       help="Minimum required specificity (default: 0.80)")
    
    # System options
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed (default: 42)")
    parser.add_argument("--output-dir", default="training_output",
                       help="Output directory (default: training_output)")
    parser.add_argument("--log-level", default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level (default: INFO)")
    parser.add_argument("--log-file",
                       help="Log file path (default: stdout only)")
    parser.add_argument("--version", default="1.0.0",
                       help="Model version (default: 1.0.0)")
    
    # Quick options
    parser.add_argument("--quick", action="store_true",
                       help="Quick training (small dataset, no optimization)")
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_level, args.log_file)
    
    # Quick mode overrides
    if args.quick:
        args.patients = min(args.patients, 200)
        args.optimize = False
        args.shap = False
        logger.info("Quick mode enabled - using reduced dataset and no optimization")
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    try:
        # Create configuration
        if args.config:
            logger.info(f"Using predefined configuration: {args.config}")
            config_map = {
                "production": PredefinedConfigs.production_config,
                "development": PredefinedConfigs.development_config,
                "early_detection": PredefinedConfigs.early_detection_config,
                "interpretability": PredefinedConfigs.interpretability_config
            }
            config = config_map[args.config]()
            
            # Override with command line arguments
            if args.patients != 1000:
                config.data.n_patients = args.patients
            
        else:
            logger.info("Using custom configuration from command line arguments")
            config = create_custom_config(args)
        
        # Validate configuration
        logger.info("Validating configuration...")
        # Configuration validation happens in TrainingConfig.__init__
        
        # Train model
        results = train_model(config, args.version, str(output_dir), logger)
        
        # Exit with appropriate code
        if results.get('pipeline_success', False):
            logger.info("Training completed successfully! 🎉")
            sys.exit(0)
        else:
            logger.error("Training failed! ❌")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Training interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.debug("Exception details:", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()