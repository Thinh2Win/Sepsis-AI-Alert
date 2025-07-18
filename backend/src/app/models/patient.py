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

class HumanName(BaseModel):
    family: Optional[str] = None
    given: List[str] = Field(default_factory=list)
    prefix: List[str] = Field(default_factory=list)
    suffix: List[str] = Field(default_factory=list)
    use: Optional[str] = None
    text: Optional[str] = None

class Telecom(BaseModel):
    system: Optional[str] = None
    value: Optional[str] = None
    use: Optional[str] = None

class Identifier(BaseModel):
    use: Optional[str] = None
    type: Optional[Dict[str, Any]] = None
    system: Optional[str] = None
    value: Optional[str] = None

class PatientDemographics(BaseModel):
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    bmi_category: Optional[str] = None
    
    @computed_field
    @property
    def calculated_bmi(self) -> Optional[float]:
        if self.height_cm and self.weight_kg:
            return calculate_bmi(self.height_cm, self.weight_kg)
        return self.bmi
    
    @computed_field
    @property
    def calculated_bmi_category(self) -> Optional[str]:
        bmi_value = self.calculated_bmi or self.bmi
        if bmi_value:
            return categorize_bmi(bmi_value)
        return self.bmi_category

class PatientResponse(BaseModel):
    id: str
    active: Optional[bool] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = Field(None, alias="birthDate")
    address: List[Address] = Field(default_factory=list)
    marital_status: Optional[Dict[str, Any]] = Field(None, alias="maritalStatus")
    demographics: Optional[PatientDemographics] = None
    
    # Direct fields for computed data
    primary_name_data: Optional[str] = None
    primary_phone_data: Optional[str] = None
    
    @computed_field
    @property
    def age(self) -> Optional[int]:
        if self.birth_date:
            return calculate_age(self.birth_date)
        return None
    
    @computed_field
    @property
    def primary_name(self) -> Optional[str]:
        return self.primary_name_data
    
    @computed_field
    @property
    def primary_phone(self) -> Optional[str]:
        return self.primary_phone_data
    
    @computed_field
    @property
    def primary_address(self) -> Optional[str]:
        if self.address:
            addr = self.address[0]
            parts = []
            if addr.line:
                parts.extend(addr.line)
            if addr.city:
                parts.append(addr.city)
            if addr.state:
                parts.append(addr.state)
            if addr.postal_code:
                parts.append(addr.postal_code)
            return ", ".join(parts)
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

class PatientSummary(BaseModel):
    """Simplified patient summary for lists and quick reference"""
    id: str
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    mrn: Optional[str] = None
    
class PatientListResponse(BaseModel):
    patients: List[PatientSummary] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20