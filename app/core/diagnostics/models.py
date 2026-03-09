#!/usr/bin/env python3
"""
Data models for diagnostic system
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime
import json


@dataclass
class DiagnosticSession:
    """Diagnostic session information"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    status: str = 'running'
    scan_type: str = 'full'
    target_subnet: Optional[str] = None
    target_device: Optional[str] = None
    summary: Optional[str] = None
    
    total_devices_found: int = 0
    total_faults_detected: int = 0
    critical_faults: int = 0
    high_faults: int = 0
    medium_faults: int = 0
    low_faults: int = 0
    info_faults: int = 0
    
    def to_dict(self):
        """Convert to dictionary"""
        d = asdict(self)
        d['start_time'] = self.start_time.isoformat() if self.start_time else None
        d['end_time'] = self.end_time.isoformat() if self.end_time else None
        return d


@dataclass
class DiscoveredDevice:
    """Device discovered during diagnostic session"""
    id: Optional[int] = None
    session_id: Optional[int] = None
    
    # Identification
    hostname: Optional[str] = None
    ip_address: str = ''
    mac_address: Optional[str] = None
    subnet: Optional[str] = None
    
    # Switch info
    switch_ip: Optional[str] = None
    switch_port: Optional[str] = None
    port_age: Optional[str] = None
    
    # Status
    status: str = 'unknown'  # active, powered_off, cable_failure, removed, new
    confidence_score: float = 0.0
    evidence_sources: List[str] = field(default_factory=list)
    
    # Evidence
    in_dhcp: bool = False
    in_arp: bool = False
    responds_to_ping: bool = False
    in_mac_table: bool = False
    
    # Additional
    device_type: str = 'unknown'
    manufacturer: Optional[str] = None
    open_ports: List[int] = field(default_factory=list)
    response_time_ms: Optional[float] = None
    
    # Timestamps
    first_seen: Optional[datetime] = None
    last_seen: datetime = field(default_factory=datetime.now)
    
    def to_dict(self):
        """Convert to dictionary"""
        d = asdict(self)
        d['first_seen'] = self.first_seen.isoformat() if self.first_seen else None
        d['last_seen'] = self.last_seen.isoformat() if self.last_seen else None
        return d


@dataclass
class Fault:
    """Network fault detected during diagnostic"""
    id: Optional[int] = None
    session_id: Optional[int] = None
    
    # Fault identification
    fault_type: str = ''
    severity: str = 'medium'
    
    # Affected devices
    primary_device_id: Optional[int] = None
    secondary_device_id: Optional[int] = None
    affected_ips: List[str] = field(default_factory=list)
    affected_macs: List[str] = field(default_factory=list)
    
    # Description and evidence
    description: str = ''
    evidence: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    
    # Troubleshooting
    troubleshooting_steps: List[str] = field(default_factory=list)
    
    # Resolution
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    resolution_notes: Optional[str] = None
    
    detected_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self):
        """Convert to dictionary"""
        d = asdict(self)
        d['detected_at'] = self.detected_at.isoformat() if self.detected_at else None
        d['resolved_at'] = self.resolved_at.isoformat() if self.resolved_at else None
        return d


@dataclass
class NetworkStatistics:
    """Network statistics per subnet"""
    id: Optional[int] = None
    session_id: Optional[int] = None
    subnet: Optional[str] = None
    
    total_devices: int = 0
    active_devices: int = 0
    powered_off_devices: int = 0
    cable_failures: int = 0
    new_devices: int = 0
    removed_devices: int = 0
    
    ip_conflicts: int = 0
    network_loops: int = 0
    high_latency_devices: int = 0
    packet_loss_devices: int = 0
    dhcp_exhaustion: int = 0
    bandwidth_saturation: int = 0
    
    avg_response_time_ms: Optional[float] = None
    scan_duration_seconds: Optional[int] = None
    
    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)


# Status constants
DEVICE_STATUS_ACTIVE = "active"
DEVICE_STATUS_POWERED_OFF = "powered_off"
DEVICE_STATUS_CABLE_FAILURE = "cable_failure"
DEVICE_STATUS_REMOVED = "removed"
DEVICE_STATUS_NEW = "new"

# Severity constants
SEVERITY_CRITICAL = "critical"
SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"
SEVERITY_INFO = "info"

# Fault type constants
FAULT_IP_CONFLICT = "IP_CONFLICT"
FAULT_NETWORK_LOOP = "NETWORK_LOOP"
FAULT_DEVICE_UNREACHABLE = "DEVICE_UNREACHABLE"
FAULT_CABLE_FAILURE = "CABLE_FAILURE"
FAULT_HIGH_LATENCY = "HIGH_LATENCY"
FAULT_PACKET_LOSS = "PACKET_LOSS"
FAULT_DHCP_EXHAUSTION = "DHCP_EXHAUSTION"
FAULT_BANDWIDTH_SATURATION = "BANDWIDTH_SATURATION"
FAULT_SWITCH_PORT_ERRORS = "SWITCH_PORT_ERRORS"
FAULT_HIGH_TRAFFIC = "HIGH_TRAFFIC"
FAULT_DEVICE_POWERED_OFF = "DEVICE_POWERED_OFF"
FAULT_NEW_DEVICE = "NEW_DEVICE_DETECTED"
FAULT_DEVICE_REMOVED = "DEVICE_REMOVED"
