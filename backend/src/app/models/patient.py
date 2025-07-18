from pydantic import BaseModel, Field, computed_field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from app.utils.calculations import calculate_age, calculate_bmi, categorize_bmi

class Address(BaseModel):
    line: List[str] = Field(default_factory=list)
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = Field(None, alias="postalCode")
    country: Optional[str] = None
    use: Optional[str] = None



class PatientResponse(BaseModel):
    id: str
    active: Optional[bool] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = Field(None, alias="birthDate")
    
    # Flattened address fields
    primary_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    
    # Flattened demographics fields
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    primary_name: Optional[str] = None
    primary_phone: Optional[str] = None
    
    @computed_field
    @property
    def age(self) -> Optional[int]:
        if self.birth_date:
            return calculate_age(self.birth_date)
        return None
    
    @computed_field
    @property
    def bmi(self) -> Optional[float]:
        if self.height_cm and self.weight_kg:
            return calculate_bmi(self.height_cm, self.weight_kg)
        return None
    
    @computed_field
    @property
    def bmi_category(self) -> Optional[str]:
        if self.bmi:
            return categorize_bmi(self.bmi)
        return None
    
    class Config:
        populate_by_name = True

class PatientMatchRequest(BaseModel):
    given: str = Field(..., description="Given name")
    family: str = Field(..., description="Family name")
    birth_date: str = Field(..., alias="birthDate", description="Birth date in YYYY-MM-DD format")
    phone: Optional[str] = Field(None, description="Phone number")
    address: Optional[Address] = Field(None, description="Address information")
    
    class Config:
        populate_by_name = True

class PatientMatchResult(BaseModel):
    resource: PatientResponse
    search: Optional[Dict[str, Any]] = None
    
class PatientMatchResponse(BaseModel):
    resourceType: str = "Bundle"
    total: int = 0
    entry: List[PatientMatchResult] = Field(default_factory=list)

