# ML Model Training Guide

## Overview

This guide provides comprehensive instructions for training sepsis prediction models using the Sepsis AI Alert System's ML training pipeline. The system supports multiple training configurations, from quick development iterations to full production training with advanced evaluation.

## Quick Start

### Prerequisites

1. **Environment Setup**: Ensure virtual environment is activated
2. **Dependencies**: All ML dependencies installed (automatically handled by requirements.txt)
3. **Working Directory**: Run commands from project root directory

### Basic Training Commands

```bash
# Quick development training (recommended for first-time users)
python train_sepsis_model.py --config development --quick

# Production training with full optimization
python train_sepsis_model.py --config production

# Early detection optimization
python train_sepsis_model.py --config early_detection

# Interpretability-focused training
python train_sepsis_model.py --config interpretability --shap
```

## Training Configurations

### Predefined Configurations

#### Development Configuration
- **Purpose**: Fast iteration during development and testing
- **Parameters**: 100 patients, no hyperparameter optimization, 2-fold CV
- **Training Time**: ~2 minutes
- **Use Case**: Code testing, feature validation, quick experiments

```bash
python train_sepsis_model.py --config development
```

#### Production Configuration
- **Purpose**: Full-scale training for production deployment
- **Parameters**: 2000 patients, grid search optimization, 5-fold CV
- **Training Time**: ~30-60 minutes
- **Use Case**: Final model training, production deployment

```bash
python train_sepsis_model.py --config production
```

#### Early Detection Configuration
- **Purpose**: Optimized for 4-6 hour early sepsis prediction
- **Parameters**: 1500 patients, Bayesian optimization, personalized features
- **Training Time**: ~45 minutes
- **Use Case**: Early warning system optimization

```bash
python train_sepsis_model.py --config early_detection
```

#### Interpretability Configuration
- **Purpose**: Clinical validation with feature interpretability
- **Parameters**: Limited features (30), SHAP analysis enabled
- **Training Time**: ~15 minutes
- **Use Case**: Clinical review, regulatory validation

```bash
python train_sepsis_model.py --config interpretability --shap
```

### Custom Configuration Parameters

#### Data Parameters
```bash
--patients 1500          # Number of synthetic patients (default: 1000)
--time-window 48         # Monitoring window in hours (default: 48)
--test-size 0.2          # Test set fraction (default: 0.2)
--val-size 0.2           # Validation set fraction (default: 0.2)
--seed 42                # Random seed for reproducibility
```

#### Model Parameters
```bash
--optimize               # Enable hyperparameter optimization
--cv-folds 5             # Cross-validation folds (default: 3)
--max-features 50        # Maximum features to use (default: all 76)
--handle-imbalance       # Enable class imbalance handling
```

#### Evaluation Parameters
```bash
--shap                   # Enable SHAP interpretability analysis
--min-sensitivity 0.85   # Minimum required sensitivity (default: 0.80)
--min-specificity 0.90   # Minimum required specificity (default: 0.80)
```

#### System Parameters
```bash
--output-dir training_output  # Output directory for artifacts
--log-level INFO             # Logging level (DEBUG, INFO, WARNING, ERROR)
--log-file training.log      # Log file path (default: stdout only)
--version 1.1.0              # Model version identifier
--quick                      # Quick mode (reduced parameters)
```

## Training Workflow

### Step 1: Configuration Selection

Choose the appropriate configuration based on your use case:

- **First-time training**: Start with `--config development --quick`
- **Performance optimization**: Use `--config production`
- **Clinical validation**: Use `--config interpretability --shap`
- **Early detection focus**: Use `--config early_detection`

### Step 2: Training Execution

```bash
python train_sepsis_model.py --config development --log-level INFO
```

### Step 3: Monitor Training Progress

The CLI provides real-time progress updates:

```
============================================================
SEPSIS ML MODEL TRAINING PIPELINE
============================================================
Model Version: 1.0.0
Training Configuration:
  Patients: 1000
  Optimization: grid_search
  Features: All (76)
  Output: models/
============================================================

INFO:__main__:Generating synthetic data for 1000 patients...
INFO:__main__:Generated 12,393 clinical records
INFO:__main__:Applying feature engineering (21 → 76 features)...
INFO:__main__:Creating patient-level data splits...
INFO:__main__:Training XGBoost model...
INFO:__main__:Evaluating model performance...
INFO:__main__:Registering model in registry...

Training completed successfully! 🎉
```

### Step 4: Review Results

Training completion provides comprehensive results:

```
============================================================
TRAINING RESULTS SUMMARY
============================================================
AUC-ROC:     0.857
Sensitivity: 0.821
Specificity: 0.895
Features:    76
============================================================

✅ Model meets clinical performance thresholds
Model registered at: models/registry/sepsis_xgboost/1.0.0
```

## Advanced Usage

### Custom Training Configuration

For advanced users, create custom training configurations:

```bash
python train_sepsis_model.py \
  --patients 3000 \
  --optimize \
  --cv-folds 5 \
  --max-features 60 \
  --shap \
  --min-sensitivity 0.85 \
  --min-specificity 0.90 \
  --version 2.0.0 \
  --log-level DEBUG
```

### Batch Training for Model Comparison

Train multiple model variants for comparison:

```bash
# Baseline model
python train_sepsis_model.py --config development --version 1.0.0

# Optimized model
python train_sepsis_model.py --config production --version 1.1.0

# Feature-limited model
python train_sepsis_model.py --max-features 30 --version 1.2.0
```

### Integration with Model Registry

Access trained models programmatically:

```python
from app.ml.model_manager import ModelRegistry

# Initialize registry
registry = ModelRegistry("models/registry")

# List available models
models = registry.list_models()
print("Available models:", models)

# Compare model performance
comparison = registry.compare_models([
    ("sepsis_xgboost", "1.0.0"),
    ("sepsis_xgboost", "1.1.0")
], metrics=['auc_roc', 'sensitivity', 'specificity'])
print(comparison)
```

## Performance Optimization

### Training Speed Optimization

For faster training iterations:

```bash
# Quick development mode
python train_sepsis_model.py --config development --quick --patients 50

# Parallel processing (utilizes all CPU cores)
# XGBoost automatically uses n_jobs=-1 for parallel training
```

### Memory Optimization

For large datasets:

```bash
# Use streaming data processing (automatically handled)
python train_sepsis_model.py --patients 5000  # Handles large datasets efficiently
```

### Hyperparameter Optimization

Control optimization intensity:

```bash
# Light optimization (faster)
python train_sepsis_model.py --optimize --cv-folds 3

# Full optimization (slower, better performance)
python train_sepsis_model.py --config production  # 5-fold CV with extensive grid search
```

## Model Evaluation

### Performance Metrics

The training pipeline evaluates models using comprehensive metrics:

#### Clinical Metrics
- **Sensitivity**: True positive rate (sepsis detection rate)
- **Specificity**: True negative rate (false alarm reduction)
- **PPV**: Positive predictive value (precision)
- **NPV**: Negative predictive value
- **Accuracy**: Overall classification accuracy

#### ML Metrics
- **AUC-ROC**: Area under ROC curve (discriminative ability)
- **AUC-PR**: Area under precision-recall curve
- **F1-Score**: Harmonic mean of precision and recall
- **Brier Score**: Probability calibration quality

#### Early Detection Metrics
- **Lead Time**: Hours before traditional alert
- **Early AUC**: Performance at different prediction horizons
- **Clinical Impact**: Actionable prediction capability

### Interpretability Analysis

Enable SHAP analysis for clinical validation:

```bash
python train_sepsis_model.py --config interpretability --shap
```

This provides:
- Feature importance rankings
- Clinical category analysis (hemodynamic, respiratory, etc.)
- Individual prediction explanations
- Model behavior insights

## Troubleshooting

### Common Issues

#### Import Errors
```bash
Error: No module named 'matplotlib'
```
**Solution**: Install missing dependencies
```bash
pip install matplotlib seaborn shap joblib
```

#### Memory Issues
```bash
Error: Out of memory during training
```
**Solution**: Reduce dataset size or enable optimization
```bash
python train_sepsis_model.py --patients 500 --quick
```

#### Training Failures
```bash
Error: Model training failed
```
**Solution**: Check logs and try development configuration
```bash
python train_sepsis_model.py --config development --log-level DEBUG
```

### Performance Issues

#### Slow Training
- Use `--quick` flag for development
- Reduce `--patients` count
- Disable `--optimize` for faster iteration

#### Poor Model Performance
- Increase `--patients` for more training data
- Enable `--optimize` for hyperparameter tuning
- Use `--config production` for full training

#### Memory Usage
- Monitor system memory during training
- Use smaller batch sizes for large datasets
- Enable swap space if needed

### Validation Issues

#### Low Performance Metrics
- Check data quality and distribution
- Verify feature engineering pipeline
- Consider different optimization strategies

#### Failed Clinical Thresholds
- Adjust `--min-sensitivity` and `--min-specificity`
- Use `--config early_detection` for specialized tuning
- Enable `--shap` for model interpretation

## Best Practices

### Development Workflow

1. **Start Small**: Begin with `--config development --quick`
2. **Iterate Fast**: Use reduced patient counts for experimentation
3. **Validate Early**: Check performance metrics at each stage
4. **Scale Up**: Move to production configuration when ready

### Production Training

1. **Full Dataset**: Use maximum patient count available
2. **Hyperparameter Optimization**: Enable full grid search
3. **Cross-Validation**: Use 5-fold CV for robust validation
4. **Performance Validation**: Ensure clinical thresholds are met

### Model Management

1. **Version Control**: Use semantic versioning (1.0.0, 1.1.0, etc.)
2. **Performance Tracking**: Compare models using registry
3. **Documentation**: Record training configurations and results
4. **Backup**: Maintain model artifacts and metadata

### Clinical Integration

1. **Interpretability**: Always enable SHAP for clinical models
2. **Validation**: Test against traditional scoring systems
3. **Performance Monitoring**: Track model drift over time
4. **Clinical Review**: Have clinicians validate model behavior

## Output Artifacts

### Training Outputs

Each training run produces comprehensive artifacts:

```
models/
├── registry/                           # Model registry
│   ├── registry.json                  # Registry metadata
│   └── sepsis_xgboost/                # Model family
│       └── 1.0.0/                     # Version directory
│           ├── model.pkl              # Trained XGBoost model
│           ├── metadata.json          # Performance metrics & config
│           ├── feature_config.json    # Feature engineering settings
│           └── feature_importance.csv # Feature importance rankings
└── training_output/                   # Training logs and artifacts
    ├── training_2024.log             # Training logs
    └── evaluation_report.json        # Detailed evaluation results
```

### Model Metadata

Each model includes comprehensive metadata:

```json
{
  "model_id": "sepsis_xgboost",
  "version": "1.0.0",
  "training_timestamp": "2024-01-15T10:30:00",
  "performance_metrics": {
    "auc_roc": 0.857,
    "sensitivity": 0.821,
    "specificity": 0.895
  },
  "feature_count": 76,
  "training_config": {...},
  "clinical_validation": "passed"
}
```

## Integration Examples

### Programmatic Training

```python
from app.ml.ml_model_trainer import SepsisMLTrainer
from app.ml.training_config import PredefinedConfigs

# Initialize trainer
trainer = SepsisMLTrainer(model_version="1.0.0")

# Use predefined configuration
config = PredefinedConfigs.production_config()

# Execute training pipeline
results = trainer.run_complete_training_pipeline(
    n_patients=1000,
    hyperparameter_tuning=True,
    save_artifacts=True
)

print(f"Training success: {results['pipeline_success']}")
print(f"Model AUC-ROC: {results['evaluation_results']['ml_metrics']['auc_roc']:.3f}")
```

### Model Loading and Inference

```python
from app.ml.model_manager import ModelRegistry
from app.ml.feature_engineering import SepsisFeatureEngineer

# Load trained model
registry = ModelRegistry("models/registry")
model, metadata = registry.load_model("sepsis_xgboost", "1.0.0")

# Initialize feature engineering
feature_engineer = SepsisFeatureEngineer()

# Clinical data example
clinical_data = {
    'heart_rate': 110, 'systolic_bp': 95, 'temperature': 38.2,
    'respiratory_rate': 24, 'oxygen_saturation': 92,
    # ... additional parameters
}

# Engineer features and predict
features = feature_engineer.transform_parameters(clinical_data)
prediction = model.predict_proba([list(features.values())])[0][1]

print(f"Sepsis risk probability: {prediction:.3f}")
```

This training guide provides complete instructions for utilizing the ML training pipeline effectively, from basic usage to advanced configuration and integration scenarios.