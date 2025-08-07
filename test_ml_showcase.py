#!/usr/bin/env python3
"""
Quick test script for ML-enhanced direct sepsis endpoint
Tests ML prediction integration for showcase purposes
"""

import asyncio
import sys
import os
sys.path.append('backend/src')

from app.services.sepsis_scoring_service import SepsisScoringServiceFactory
from app.models.sofa import DirectSepsisScoreRequest
from app.services.fhir_client import FHIRClient

async def test_ml_showcase():
    """Test ML prediction integration with direct endpoint"""
    print("Testing ML-Enhanced Sepsis Detection Showcase")
    print("=" * 60)
    
    # Create FHIR client (not used for direct endpoint)
    try:
        fhir_client = FHIRClient()
    except Exception:
        # Create a minimal mock client for testing
        class MockFHIRClient:
            def __init__(self):
                pass
        fhir_client = MockFHIRClient()
    
    # Create service
    service = SepsisScoringServiceFactory.create_service(fhir_client)
    
    # Test Case 1: Early sepsis (subtle signs)
    print("\nTest Case 1: Early Sepsis (Subtle Signs)")
    print("-" * 50)
    early_sepsis_request = DirectSepsisScoreRequest(
        patient_id="showcase_patient_001", 
        requested_systems=["SOFA", "QSOFA", "NEWS2"],
        # Early sepsis signs that should trigger retrained model
        heart_rate=98,           # Baseline + 10-15 (early tachycardia)
        respiratory_rate=22,     # Baseline + 4-6 (early tachypnea)
        temperature=38.3,        # Low-grade fever (infection sign)
        systolic_bp=108,         # Baseline - 10-15 (early hypotension)
        diastolic_bp=68,         # Proportional decrease
        oxygen_saturation=96,    # Baseline - 2 (subtle hypoxemia)
        glasgow_coma_scale=15,   # Keep normal to avoid qSOFA points
        creatinine=1.4,          # Baseline + 0.3 (early AKI)
        platelets=170,           # Baseline - 15% (mild thrombocytopenia)
        pao2=88,                 # Mild decrease (early respiratory)
        fio2=0.21,               # Room air
        bilirubin=1.6,           # Baseline + 0.8 (early hepatic)
        urine_output_24h=650,    # Slight decrease
        norepinephrine=0.05,     # Very low dose (early intervention)
        supplemental_oxygen=False,
        mechanical_ventilation=False,
    )
    
    try:
        result = await service.calculate_direct_sepsis_score(early_sepsis_request)
        
        print(f"Patient ID: {result.patient_id}")
        print(f"Result type: {type(result)}")
        print("Response structure:")
        if hasattr(result, '__dict__'):
            for key, value in result.__dict__.items():
                print(f"  - {key}: {type(value)}")
        
        # Check if ML prediction was added (this is what we're really testing)
        if hasattr(result, 'ml_prediction'):
            ml = result.ml_prediction
            print(f"\nML Prediction SUCCESS:")
            print(f"  - Sepsis Probability: {ml['sepsis_probability']:.1%}")
            print(f"  - ML Risk Level: {ml['risk_level']}")
            print(f"  - Early Detection: {ml['early_detection_hours']}h advantage")
            print(f"  - Feature Count: {ml['feature_count']}")
            
            if hasattr(result, 'clinical_advantage'):
                print(f"  - Clinical Advantage: {result.clinical_advantage}")
        else:
            print("\nML prediction not available")
            
    except Exception as e:
        print(f"Test failed: {e}")
    
    # Test Case 2: Severe sepsis (obvious signs)
    print("\n\nTest Case 2: Severe Sepsis (Obvious Signs)")
    print("-" * 50)
    severe_sepsis_request = DirectSepsisScoreRequest(
        patient_id="showcase_patient_002",
        requested_systems=["SOFA", "QSOFA", "NEWS2"],
        # Moderate sepsis signs (should trigger both ML and some traditional scores)
        heart_rate=110,          # Baseline + 15-18 (moderate tachycardia)
        respiratory_rate=25,     # Baseline + 6-8 (moderate tachypnea)
        temperature=38.8,        # Moderate fever
        systolic_bp=95,          # Baseline - 20 (moderate hypotension)
        diastolic_bp=60,         # Proportional decrease
        oxygen_saturation=94,    # Baseline - 3-4 (moderate hypoxemia)
        glasgow_coma_scale=15,   # Keep normal for comparison
        creatinine=1.8,          # Baseline + 0.6 (moderate AKI)
        platelets=140,           # Baseline - 25% (moderate thrombocytopenia)
        pao2=82,                 # Moderate decrease
        fio2=0.3,                # Some supplemental oxygen
        bilirubin=2.2,           # Baseline + 1.0 (moderate hepatic)
        urine_output_24h=500,    # More significant decrease
        norepinephrine=0.08,     # Low dose vasopressor
        supplemental_oxygen=True,
        mechanical_ventilation=False,
    )
    
    try:
        result = await service.calculate_direct_sepsis_score(severe_sepsis_request)
        
        print(f"Patient ID: {result.patient_id}")
        
        # Check if ML prediction was added (this is what we're really testing)
        if hasattr(result, 'ml_prediction'):
            ml = result.ml_prediction
            print(f"\nML Prediction SUCCESS:")
            print(f"  - Sepsis Probability: {ml['sepsis_probability']:.1%}")
            print(f"  - ML Risk Level: {ml['risk_level']}")
            print(f"  - Early Detection: {ml['early_detection_hours']}h advantage")
            print(f"  - Feature Count: {ml['feature_count']}")
            
            if hasattr(result, 'clinical_advantage'):
                print(f"  - Clinical Advantage: {result.clinical_advantage}")
        else:
            print("\nML prediction not available")
            
    except Exception as e:
        print(f"Test failed: {e}")
        
    print("\nML Showcase Integration Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_ml_showcase())