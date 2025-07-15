from typing import Dict, List

class LOINCCodes:
    """LOINC code mappings for sepsis-related observations"""
    
    # Vital Signs
    VITAL_SIGNS = {
        "heart_rate": "8867-4",
        "systolic_bp": "8480-6",
        "diastolic_bp": "8462-4",
        "blood_pressure_panel": "85354-9",
        "body_temperature": "8310-5",
        "respiratory_rate": "9279-1",
        "oxygen_saturation": "2708-6",
        "oxygen_saturation_pulse": "59408-5",
        "glasgow_coma_score": "9269-2"
    }
    
    # Patient Demographics
    DEMOGRAPHICS = {
        "height": "8302-2",
        "weight": "29463-7",
        "bmi": "39156-5"
    }
    
    # Complete Blood Count (CBC)
    CBC = {
        "white_blood_cell_count": "6690-2",
        "red_blood_cell_count": "789-8",
        "hemoglobin": "718-7",
        "hematocrit": "4544-3",
        "platelet_count": "777-3",
        "mean_corpuscular_volume": "787-2",
        "mean_corpuscular_hemoglobin": "785-6",
        "mean_corpuscular_hemoglobin_concentration": "786-4"
    }
    
    # Metabolic Panel
    METABOLIC = {
        "glucose": "2345-7",
        "creatinine": "2160-0",
        "blood_urea_nitrogen": "3094-0",
        "sodium": "2951-2",
        "potassium": "2823-3",
        "chloride": "2075-0",
        "carbon_dioxide": "2028-9",
        "anion_gap": "1863-0"
    }
    
    # Liver Function
    LIVER = {
        "bilirubin_total": "1975-2",
        "bilirubin_direct": "1968-7",
        "albumin": "1751-7",
        "total_protein": "2885-2",
        "alkaline_phosphatase": "6768-6",
        "alanine_aminotransferase": "1742-6",
        "aspartate_aminotransferase": "1920-8",
        "lactate_dehydrogenase": "14804-9"
    }
    
    # Inflammatory Markers
    INFLAMMATORY = {
        "c_reactive_protein": "1988-5",
        "procalcitonin": "75241-0",
        "erythrocyte_sedimentation_rate": "30341-2",
        "interleukin_6": "26881-3"
    }
    
    # Blood Gas and Acid-Base
    BLOOD_GAS = {
        "ph": "2744-1",
        "pco2": "2019-8",
        "po2": "2703-7",
        "lactate": "2524-7",
        "base_excess": "1925-7",
        "bicarbonate": "1963-8",
        "pao2_fio2_ratio": "50984-4"
    }
    
    # Coagulation
    COAGULATION = {
        "prothrombin_time": "5902-2",
        "inr": "6301-6",
        "partial_thromboplastin_time": "14979-9",
        "fibrinogen": "3255-7",
        "d_dimer": "48065-7"
    }
    
    # Fluid Balance
    FLUID_BALANCE = {
        "fluid_intake": "9192-6",
        "urine_output": "9187-6",
        "urine_output_24hr": "9188-4"
    }
    
    # Cardiac Markers
    CARDIAC = {
        "troponin_i": "10839-9",
        "troponin_t": "6598-7",
        "brain_natriuretic_peptide": "30934-4",
        "nt_pro_bnp": "33762-6"
    }
    
    @classmethod
    def get_all_codes(cls) -> Dict[str, str]:
        """Get all LOINC codes as a flat dictionary"""
        all_codes = {}
        for category in [cls.VITAL_SIGNS, cls.DEMOGRAPHICS, cls.CBC, cls.METABOLIC, 
                        cls.LIVER, cls.INFLAMMATORY, cls.BLOOD_GAS, cls.COAGULATION, 
                        cls.FLUID_BALANCE, cls.CARDIAC]:
            all_codes.update(category)
        return all_codes
    
    @classmethod
    def get_codes_by_category(cls, category: str) -> Dict[str, str]:
        """Get LOINC codes for a specific category"""
        category_map = {
            "vital_signs": cls.VITAL_SIGNS,
            "demographics": cls.DEMOGRAPHICS,
            "cbc": cls.CBC,
            "metabolic": cls.METABOLIC,
            "liver": cls.LIVER,
            "inflammatory": cls.INFLAMMATORY,
            "blood_gas": cls.BLOOD_GAS,
            "coagulation": cls.COAGULATION,
            "fluid_balance": cls.FLUID_BALANCE,
            "cardiac": cls.CARDIAC
        }
        return category_map.get(category, {})
    
    @classmethod
    def get_sepsis_critical_codes(cls) -> List[str]:
        """Get LOINC codes for sepsis-critical observations"""
        return [
            cls.VITAL_SIGNS["heart_rate"],
            cls.VITAL_SIGNS["systolic_bp"],
            cls.VITAL_SIGNS["body_temperature"],
            cls.VITAL_SIGNS["respiratory_rate"],
            cls.CBC["white_blood_cell_count"],
            cls.BLOOD_GAS["lactate"],
            cls.INFLAMMATORY["procalcitonin"],
            cls.INFLAMMATORY["c_reactive_protein"],
            cls.METABOLIC["creatinine"],
            cls.LIVER["bilirubin_total"],
            cls.CBC["platelet_count"]
        ]