from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, unique=True, index=True)
    mac = Column(String, nullable=True)
    vendor = Column(String, nullable=True)
    hostname = Column(String, nullable=True)
    name = Column(String, nullable=True)
    device_type = Column(String, nullable=True)
    os_info = Column(String, nullable=True)
    status = Column(String, default="unknown")
    confirmed = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True, index=True)
    risk_level = Column(String, nullable=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    source = Column(String, default="discovered")
    interfaces = relationship("NetworkInterface", back_populates="device", cascade="all, delete-orphan", order_by="NetworkInterface.is_primary.desc()")

class NetworkInterface(Base):
    """Interfaz de red persistida por dispositivo (una máquina puede tener varias)."""
    __tablename__ = "network_interfaces"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), index=True)
    ip = Column(String, index=True)
    mac = Column(String, nullable=True)
    prefix_length = Column(Integer, nullable=True)
    netmask = Column(String, nullable=True)
    subnet = Column(String, nullable=True)
    gateway = Column(String, nullable=True)
    dns = Column(String, nullable=True)
    interface_name = Column(String, nullable=True)
    interface_type = Column(String, nullable=True)
    status = Column(String, default="unknown")
    is_primary = Column(Boolean, default=False)
    source = Column(String, default="agent")
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    device = relationship("Device", back_populates="interfaces")
    __table_args__ = (UniqueConstraint("device_id", "ip", name="uq_network_interface_device_ip"),)

class DeviceHistory(Base):
    __tablename__ = "device_history"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    status = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    note = Column(Text, nullable=True)

class SecurityAssessment(Base):
    __tablename__ = "security_assessments"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    firewall = Column(String, nullable=True)
    antivirus = Column(String, nullable=True)
    pending_updates = Column(Integer, default=0)
    os_age_months = Column(Integer, nullable=True)
    outdated_software = Column(Integer, default=0)
    vulnerable_apps = Column(Integer, default=0)
    excessive_permissions = Column(Boolean, default=False)
    unnecessary_services = Column(Integer, default=0)
    unverified_signatures = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Vulnerability(Base):
    __tablename__ = "vulnerabilities"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    cve_id = Column(String, index=True)
    software = Column(String, nullable=True)
    version = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    fixed_version = Column(String, nullable=True)
    verification_level = Column(String, default="potential")
    created_at = Column(DateTime, default=datetime.utcnow)

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    severity = Column(String, default="info")
    message = Column(Text)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AIResult(Base):
    __tablename__ = "ai_results"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    model_name = Column(String)
    result_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class TrainingInfo(Base):
    __tablename__ = "training_info"
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String)
    dataset = Column(String, nullable=True)
    metrics_json = Column(Text, nullable=True)
    trained_at = Column(DateTime, default=datetime.utcnow)

class EventLog(Base):
    __tablename__ = "event_logs"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class AppSetting(Base):
    __tablename__ = "app_settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(Text)

class SoftwareInventory(Base):
    __tablename__ = "software_inventory"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    name = Column(String)
    version = Column(String, nullable=True)
    source = Column(String, default="agent")
    created_at = Column(DateTime, default=datetime.utcnow)

class AIAnalysis(Base):
    __tablename__ = "ai_analyses"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    model_name = Column(String)
    input_features = Column(Text)
    provenance = Column(Text, nullable=True)
    predicted_class = Column(String)
    probabilities = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    status = Column(String, default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)

class NetworkTelemetry(Base):
    __tablename__ = "network_telemetry"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    identity_key = Column(String, nullable=False, index=True)
    source = Column(String, default="agent")
    local_ip = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    conn_count = Column(Integer, nullable=False)
    conn_freq = Column(Float, nullable=False)
    ports = Column(Integer, nullable=False)
    bytes_sent = Column(Float, nullable=False)
    bytes_recv = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)
    activity_var = Column(Float, nullable=False)
    comm_freq = Column(Float, nullable=False)
    window_seconds = Column(Integer, default=10)
    is_complete = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("identity_key", "timestamp", "window_seconds", name="uq_network_telemetry_identity"),)

class DiscoveryRequest(Base):
    __tablename__ = "discovery_requests"
    id = Column(String, primary_key=True, index=True)
    status = Column(String, default="pending", index=True)
    subnet = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    discovered_count = Column(Integer, default=0)
    received_count = Column(Integer, default=0)
    confirmed_count = Column(Integer, default=0)
    updated_count = Column(Integer, default=0)
    archived_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

class DeletionAudit(Base):
    __tablename__ = "deletion_audit"
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, index=True)
    entity_id = Column(Integer, nullable=True)
    action = Column(String)
    count = Column(Integer, default=0)
    performed_at = Column(DateTime, default=datetime.utcnow)
    details = Column(Text, nullable=True)

class CleanupRun(Base):
    __tablename__ = "cleanup_runs"
    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, default="running")
    execution_type = Column(String, default="scheduled")
    dry_run = Column(Boolean, default=True)
    records_scanned = Column(Integer, default=0)
    records_deleted = Column(Integer, default=0)
    details = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

class CleanupLock(Base):
    __tablename__ = "cleanup_locks"
    lock_key = Column(String, primary_key=True)
    owner = Column(String, nullable=False)
    acquired_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)