"""
Model Persistence and Versioning Manager for Sepsis ML Models

Comprehensive model lifecycle management including:
- Model serialization and deserialization
- Version control and metadata tracking
- Model registry and artifact management
- Production deployment support
- Model performance monitoring setup
- Rollback and model comparison capabilities
"""

import os
import json
import pickle
import joblib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import hashlib
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict

# Model tracking imports
try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    logging.warning("MLflow not available. Using local model registry only.")

logger = logging.getLogger(__name__)

@dataclass
class ModelMetadata:
    """Model metadata for tracking and versioning."""
    model_id: str
    version: str
    model_type: str
    training_timestamp: str
    performance_metrics: Dict[str, float]
    feature_count: int
    feature_names: List[str]
    training_config: Dict[str, Any]
    data_config: Dict[str, Any]
    model_size_mb: float
    checksum: str
    tags: List[str]
    description: str
    created_by: str = "SepsisMLTrainer"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelMetadata':
        """Create from dictionary."""
        return cls(**data)

class ModelArtifact:
    """Container for model artifacts and associated files."""
    
    def __init__(self, 
                 model_path: str,
                 metadata: ModelMetadata,
                 feature_config_path: Optional[str] = None,
                 preprocessing_pipeline_path: Optional[str] = None,
                 evaluation_report_path: Optional[str] = None):
        
        self.model_path = model_path
        self.metadata = metadata
        self.feature_config_path = feature_config_path
        self.preprocessing_pipeline_path = preprocessing_pipeline_path
        self.evaluation_report_path = evaluation_report_path
        
        # Validate paths exist
        self._validate_paths()
    
    def _validate_paths(self):
        """Validate that artifact paths exist."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        optional_paths = [
            self.feature_config_path,
            self.preprocessing_pipeline_path, 
            self.evaluation_report_path
        ]
        
        for path in optional_paths:
            if path is not None and not os.path.exists(path):
                logger.warning(f"Optional artifact not found: {path}")

class ModelRegistry:
    """
    Model registry for tracking and managing trained models.
    Supports local filesystem and MLflow backends.
    """
    
    def __init__(self, 
                 registry_path: str = "model_registry",
                 use_mlflow: bool = False,
                 mlflow_tracking_uri: Optional[str] = None):
        
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(exist_ok=True, parents=True)
        
        self.use_mlflow = use_mlflow and MLFLOW_AVAILABLE
        
        if self.use_mlflow:
            if mlflow_tracking_uri:
                mlflow.set_tracking_uri(mlflow_tracking_uri)
            mlflow.set_experiment("sepsis-prediction")
        
        # Initialize registry metadata
        self.registry_file = self.registry_path / "registry.json"
        self._initialize_registry()
        
        logger.info(f"ModelRegistry initialized at {self.registry_path}")
        if self.use_mlflow:
            logger.info("MLflow tracking enabled")
    
    def _initialize_registry(self):
        """Initialize registry metadata file."""
        if not self.registry_file.exists():
            registry_data = {
                'created_at': datetime.now().isoformat(),
                'models': {},
                'latest_versions': {},
                'metadata_version': '1.0.0'
            }
            
            with open(self.registry_file, 'w') as f:
                json.dump(registry_data, f, indent=2)
    
    def _load_registry(self) -> Dict[str, Any]:
        """Load registry metadata."""
        with open(self.registry_file, 'r') as f:
            return json.load(f)
    
    def _save_registry(self, registry_data: Dict[str, Any]):
        """Save registry metadata."""
        registry_data['updated_at'] = datetime.now().isoformat()
        with open(self.registry_file, 'w') as f:
            json.dump(registry_data, f, indent=2)
    
    def register_model(self,
                      model,
                      metadata: ModelMetadata,
                      artifacts: Optional[Dict[str, str]] = None) -> str:
        """
        Register a new model in the registry.
        
        Args:
            model: Trained model object
            metadata: Model metadata
            artifacts: Dictionary of artifact paths
            
        Returns:
            Registry path for the model
        """
        logger.info(f"Registering model {metadata.model_id} v{metadata.version}")
        
        # Create model directory
        model_dir = self.registry_path / metadata.model_id / metadata.version
        model_dir.mkdir(exist_ok=True, parents=True)
        
        # Save model
        model_path = model_dir / "model.pkl"
        joblib.dump(model, model_path)
        
        # Calculate model file size and checksum
        model_size_mb = os.path.getsize(model_path) / (1024 * 1024)
        checksum = self._calculate_checksum(model_path)
        
        # Update metadata with actual values
        metadata.model_size_mb = model_size_mb
        metadata.checksum = checksum
        
        # Save metadata
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)
        
        # Save additional artifacts
        artifact_paths = {'model': str(model_path), 'metadata': str(metadata_path)}
        
        if artifacts:
            for name, source_path in artifacts.items():
                if os.path.exists(source_path):
                    dest_path = model_dir / f"{name}.json" if name.endswith('config') else model_dir / f"{name}.pkl"
                    shutil.copy2(source_path, dest_path)
                    artifact_paths[name] = str(dest_path)
        
        # Update registry
        registry_data = self._load_registry()
        
        if metadata.model_id not in registry_data['models']:
            registry_data['models'][metadata.model_id] = {}
        
        registry_data['models'][metadata.model_id][metadata.version] = {
            'registered_at': datetime.now().isoformat(),
            'model_path': str(model_path),
            'metadata_path': str(metadata_path),
            'artifact_paths': artifact_paths,
            'performance_summary': {
                'auc_roc': metadata.performance_metrics.get('auc_roc', 0),
                'sensitivity': metadata.performance_metrics.get('sensitivity', 0),
                'specificity': metadata.performance_metrics.get('specificity', 0)
            }
        }
        
        # Update latest version
        registry_data['latest_versions'][metadata.model_id] = metadata.version
        
        self._save_registry(registry_data)
        
        # Register with MLflow if available
        if self.use_mlflow:
            self._register_with_mlflow(model, metadata, artifact_paths)
        
        logger.info(f"Model registered successfully at {model_dir}")
        return str(model_dir)
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _register_with_mlflow(self, 
                            model, 
                            metadata: ModelMetadata,
                            artifact_paths: Dict[str, str]):
        """Register model with MLflow."""
        try:
            with mlflow.start_run():
                # Log parameters
                mlflow.log_params({
                    'model_type': metadata.model_type,
                    'feature_count': metadata.feature_count,
                    'model_version': metadata.version
                })
                
                # Log metrics
                mlflow.log_metrics(metadata.performance_metrics)
                
                # Log model
                mlflow.sklearn.log_model(
                    model, 
                    "model",
                    registered_model_name=f"sepsis-{metadata.model_id}"
                )
                
                # Log artifacts
                for name, path in artifact_paths.items():
                    if name != 'model':  # Model already logged above
                        mlflow.log_artifact(path, name)
                
                # Add tags
                mlflow.set_tags({tag: "true" for tag in metadata.tags})
                mlflow.set_tag("description", metadata.description)
                
        except Exception as e:
            logger.warning(f"MLflow registration failed: {str(e)}")
    
    def load_model(self, 
                  model_id: str, 
                  version: Optional[str] = None) -> Tuple[Any, ModelMetadata]:
        """
        Load model and metadata from registry.
        
        Args:
            model_id: Model identifier
            version: Model version (latest if None)
            
        Returns:
            Tuple of (model, metadata)
        """
        registry_data = self._load_registry()
        
        if model_id not in registry_data['models']:
            raise ValueError(f"Model {model_id} not found in registry")
        
        if version is None:
            version = registry_data['latest_versions'].get(model_id)
            if version is None:
                raise ValueError(f"No versions found for model {model_id}")
        
        model_versions = registry_data['models'][model_id]
        if version not in model_versions:
            available_versions = list(model_versions.keys())
            raise ValueError(f"Version {version} not found. Available: {available_versions}")
        
        model_info = model_versions[version]
        
        # Load model
        model_path = model_info['model_path']
        model = joblib.load(model_path)
        
        # Load metadata
        metadata_path = model_info['metadata_path']
        with open(metadata_path, 'r') as f:
            metadata_dict = json.load(f)
        metadata = ModelMetadata.from_dict(metadata_dict)
        
        logger.info(f"Loaded model {model_id} v{version}")
        return model, metadata
    
    def list_models(self) -> Dict[str, List[str]]:
        """List all models and their versions."""
        registry_data = self._load_registry()
        return {
            model_id: list(versions.keys())
            for model_id, versions in registry_data['models'].items()
        }
    
    def get_model_info(self, model_id: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed information about a model."""
        registry_data = self._load_registry()
        
        if model_id not in registry_data['models']:
            raise ValueError(f"Model {model_id} not found")
        
        if version is None:
            version = registry_data['latest_versions'].get(model_id)
        
        model_info = registry_data['models'][model_id][version]
        
        # Load metadata
        with open(model_info['metadata_path'], 'r') as f:
            metadata = json.load(f)
        
        return {
            'model_id': model_id,
            'version': version,
            'registry_info': model_info,
            'metadata': metadata
        }
    
    def compare_models(self, 
                      model_comparisons: List[Tuple[str, str]],
                      metrics: List[str] = ['auc_roc', 'sensitivity', 'specificity']) -> pd.DataFrame:
        """
        Compare performance of multiple models.
        
        Args:
            model_comparisons: List of (model_id, version) tuples
            metrics: Metrics to compare
            
        Returns:
            Comparison DataFrame
        """
        comparison_data = []
        
        for model_id, version in model_comparisons:
            try:
                model_info = self.get_model_info(model_id, version)
                metadata = model_info['metadata']
                
                row = {
                    'model_id': model_id,
                    'version': version,
                    'training_date': metadata['training_timestamp'][:10]  # Date only
                }
                
                # Add performance metrics
                for metric in metrics:
                    row[metric] = metadata['performance_metrics'].get(metric, None)
                
                # Add additional info
                row['feature_count'] = metadata['feature_count']
                row['model_size_mb'] = metadata['model_size_mb']
                
                comparison_data.append(row)
                
            except Exception as e:
                logger.warning(f"Failed to load {model_id} v{version}: {str(e)}")
        
        return pd.DataFrame(comparison_data)
    
    def promote_model(self, 
                     model_id: str, 
                     version: str, 
                     stage: str = "production") -> bool:
        """
        Promote model to a specific stage.
        
        Args:
            model_id: Model identifier
            version: Model version
            stage: Target stage ('staging', 'production', 'archived')
            
        Returns:
            Success status
        """
        try:
            registry_data = self._load_registry()
            
            if 'model_stages' not in registry_data:
                registry_data['model_stages'] = {}
            
            if model_id not in registry_data['model_stages']:
                registry_data['model_stages'][model_id] = {}
            
            # Update stage
            old_stage = registry_data['model_stages'][model_id].get(version, 'development')
            registry_data['model_stages'][model_id][version] = stage
            
            # If promoting to production, demote current production model
            if stage == 'production':
                for ver, st in registry_data['model_stages'][model_id].items():
                    if ver != version and st == 'production':
                        registry_data['model_stages'][model_id][ver] = 'staging'
            
            self._save_registry(registry_data)
            
            logger.info(f"Promoted {model_id} v{version} from {old_stage} to {stage}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to promote model: {str(e)}")
            return False
    
    def delete_model(self, model_id: str, version: str) -> bool:
        """
        Delete a model version from registry.
        
        Args:
            model_id: Model identifier
            version: Version to delete
            
        Returns:
            Success status
        """
        try:
            registry_data = self._load_registry()
            
            if model_id not in registry_data['models']:
                raise ValueError(f"Model {model_id} not found")
            
            if version not in registry_data['models'][model_id]:
                raise ValueError(f"Version {version} not found")
            
            # Get model info before deletion
            model_info = registry_data['models'][model_id][version]
            
            # Delete files
            model_dir = Path(model_info['model_path']).parent
            if model_dir.exists():
                shutil.rmtree(model_dir)
            
            # Remove from registry
            del registry_data['models'][model_id][version]
            
            # Update latest version if necessary
            if registry_data['latest_versions'].get(model_id) == version:
                remaining_versions = list(registry_data['models'][model_id].keys())
                if remaining_versions:
                    # Set latest to most recent remaining version
                    registry_data['latest_versions'][model_id] = max(remaining_versions)
                else:
                    # No versions left, remove model entirely
                    del registry_data['models'][model_id]
                    del registry_data['latest_versions'][model_id]
            
            self._save_registry(registry_data)
            
            logger.info(f"Deleted {model_id} v{version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete model: {str(e)}")
            return False

class ProductionModelManager:
    """Manager for production model deployment and monitoring."""
    
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self.production_config_path = self.registry.registry_path / "production_config.json"
        self._initialize_production_config()
    
    def _initialize_production_config(self):
        """Initialize production configuration."""
        if not self.production_config_path.exists():
            config = {
                'active_models': {},
                'deployment_history': [],
                'monitoring_config': {
                    'performance_threshold': 0.75,
                    'data_drift_threshold': 0.1,
                    'alert_email': None
                }
            }
            
            with open(self.production_config_path, 'w') as f:
                json.dump(config, f, indent=2)
    
    def deploy_model(self, 
                    model_id: str, 
                    version: str,
                    deployment_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Deploy model to production.
        
        Args:
            model_id: Model identifier
            version: Model version
            deployment_config: Deployment configuration
            
        Returns:
            Success status
        """
        try:
            # Validate model exists
            model, metadata = self.registry.load_model(model_id, version)
            
            # Load production config
            with open(self.production_config_path, 'r') as f:
                prod_config = json.load(f)
            
            # Create deployment record
            deployment_record = {
                'model_id': model_id,
                'version': version,
                'deployed_at': datetime.now().isoformat(),
                'deployment_config': deployment_config or {},
                'performance_baseline': metadata.performance_metrics
            }
            
            # Update active models
            prod_config['active_models'][model_id] = {
                'version': version,
                'deployed_at': deployment_record['deployed_at'],
                'status': 'active'
            }
            
            # Add to deployment history
            prod_config['deployment_history'].append(deployment_record)
            
            # Save configuration
            with open(self.production_config_path, 'w') as f:
                json.dump(prod_config, f, indent=2)
            
            # Promote model in registry
            self.registry.promote_model(model_id, version, 'production')
            
            logger.info(f"Deployed {model_id} v{version} to production")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deploy model: {str(e)}")
            return False
    
    def get_active_models(self) -> Dict[str, Any]:
        """Get currently active production models."""
        with open(self.production_config_path, 'r') as f:
            prod_config = json.load(f)
        return prod_config['active_models']
    
    def rollback_model(self, model_id: str) -> bool:
        """
        Rollback to previous model version.
        
        Args:
            model_id: Model to rollback
            
        Returns:
            Success status
        """
        try:
            with open(self.production_config_path, 'r') as f:
                prod_config = json.load(f)
            
            # Find previous deployment
            deployments = [d for d in prod_config['deployment_history'] 
                         if d['model_id'] == model_id]
            
            if len(deployments) < 2:
                raise ValueError("No previous version to rollback to")
            
            # Get previous version (second to last deployment)
            previous_deployment = deployments[-2]
            previous_version = previous_deployment['version']
            
            # Deploy previous version
            return self.deploy_model(model_id, previous_version, 
                                   {'rollback': True, 'rollback_from': deployments[-1]['version']})
            
        except Exception as e:
            logger.error(f"Failed to rollback model: {str(e)}")
            return False

if __name__ == "__main__":
    # Example usage
    registry = ModelRegistry("test_registry")
    
    # Create sample metadata
    metadata = ModelMetadata(
        model_id="sepsis_xgboost",
        version="1.0.0",
        model_type="XGBoost",
        training_timestamp=datetime.now().isoformat(),
        performance_metrics={"auc_roc": 0.85, "sensitivity": 0.80},
        feature_count=76,
        feature_names=[f"feature_{i}" for i in range(76)],
        training_config={},
        data_config={},
        model_size_mb=0.0,
        checksum="",
        tags=["baseline", "production-candidate"],
        description="Baseline XGBoost model for sepsis prediction"
    )
    
    print("ModelRegistry initialized successfully")
    print(f"Registry path: {registry.registry_path}")
    print(f"MLflow enabled: {registry.use_mlflow}")