from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
import math

class DeviceBase(BaseModel):
    ip: str
    mac: Optional[str] = None
    vendor: Optional[str] = None
    hostname: Optional[str] = None
    device_type: Optional[str] = None
    os_info: Optional[str] = None
    status: str = "unknown"
    risk_level: Optional[str] = None
    source: str = "discovered"

class DeviceCreate(DeviceBase):
    pass

class DeviceOut(DeviceBase):
    id: int
    name: Optional[str] = None
    confirmed: bool = False
    deleted_at: Optional[datetime] = None
    subnet: Optional[str] = None
    gateway: Optional[str] = None
    dns: Optional[str] = None
    interface_count: int = 0
    first_seen: datetime
    last_seen: datetime
    class Config:
        from_attributes = True

class NetworkInterfaceOut(BaseModel):
    id: int
    device_id: Optional[int] = None
    ip: str
    mac: Optional[str] = None
    prefix_length: Optional[int] = None
    netmask: Optional[str] = None
    subnet: Optional[str] = None
    gateway: Optional[str] = None
    dns: Optional[str] = None
    interface_name: Optional[str] = None
    interface_type: Optional[str] = None
    status: str = "unknown"
    is_primary: bool = False
    source: Optional[str] = None
    first_seen: datetime
    last_seen: datetime
    class Config:
        from_attributes = True

class DeviceDetail(DeviceOut):
    interfaces: list[NetworkInterfaceOut] = []

class SoftwareOut(BaseModel):
    id: int
    device_id: Optional[int] = None
    name: str
    version: Optional[str] = None
    source: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class SecurityAssessmentIn(BaseModel):
    device_id: int
    firewall: Optional[str] = None
    antivirus: Optional[str] = None
    pending_updates: int = 0
    os_age_months: Optional[int] = None
    outdated_software: int = 0
    vulnerable_apps: int = 0
    excessive_permissions: bool = False
    unnecessary_services: int = 0
    unverified_signatures: int = 0

class InferenceIn(BaseModel):
    features: List[float]

class AlertOut(BaseModel):
    id: int
    device_id: Optional[int] = None
    severity: str
    message: str
    resolved: bool
    created_at: datetime
    class Config:
        from_attributes = True

class VulnerabilityOut(BaseModel):
    id: int
    device_id: Optional[int] = None
    cve_id: str
    software: Optional[str] = None
    version: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None
    recommendation: Optional[str] = None
    fixed_version: Optional[str] = None
    verification_level: str
    class Config:
        from_attributes = True

class TelemetryIn(BaseModel):
    local_ip: Optional[str] = None
    device_id: Optional[int] = None
    timestamp: datetime
    conn_count: int = Field(ge=0)
    conn_freq: float = Field(ge=0)
    ports: int = Field(ge=0)
    bytes_sent: float = Field(ge=0)
    bytes_recv: float = Field(ge=0)
    duration: float = Field(ge=0)
    activity_var: float = Field(ge=0)
    comm_freq: float = Field(ge=0)
    window_seconds: int = Field(default=10, ge=1, le=3600)
    is_complete: bool = True

    @field_validator("conn_count", "ports", mode="before")
    @classmethod
    def validate_int_fields(cls, v):
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError("Se esperaba un entero")
        return v

    @field_validator("conn_freq", "bytes_sent", "bytes_recv", "duration", "activity_var", "comm_freq", mode="before")
    @classmethod
    def validate_float_fields(cls, v):
        if isinstance(v, bool) or isinstance(v, str):
            raise ValueError("Se esperaba un número")
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            raise ValueError("Valor no finito")
        return v