#!/usr/bin/env python3
"""
Database operations for diagnostic system
"""

import json
from typing import List, Dict, Optional, Any
from datetime import datetime

from app.db.connection import get_connection
from app.core.diagnostics.models import (
    DiagnosticSession, DiscoveredDevice, Fault, NetworkStatistics
)


class DiagnosticDB:
    """Database operations for diagnostics"""
    
    @staticmethod
    def create_session(user_id: int, scan_type: str = 'full',
                       target_subnet: Optional[str] = None,
                       target_device: Optional[str] = None) -> int:
        """Create a new diagnostic session"""
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO diagnostic_sessions 
            (user_id, scan_type, target_subnet, target_device, status, start_time)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (user_id, scan_type, target_subnet, target_device, 'running', datetime.now()))
        
        session_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return session_id
    
    @staticmethod
    def complete_session(session_id: int, summary: Optional[str] = None):
        """Mark session as completed"""
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE diagnostic_sessions 
            SET status = 'completed', end_time = %s, summary = %s
            WHERE id = %s
        """, (datetime.now(), summary, session_id))
        
        conn.commit()
        cur.close()
        conn.close()
    
    @staticmethod
    def fail_session(session_id: int, error: str):
        """Mark session as failed"""
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE diagnostic_sessions 
            SET status = 'failed', end_time = %s, summary = %s
            WHERE id = %s
        """, (datetime.now(), f"Failed: {error}", session_id))
        
        conn.commit()
        cur.close()
        conn.close()
    
    @staticmethod
    def save_device(device: DiscoveredDevice) -> int:
        """Save discovered device"""
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO diagnostic_devices 
            (session_id, hostname, ip_address, mac_address, subnet,
             switch_ip, switch_port, port_age, status, confidence_score,
             evidence_sources, in_dhcp, in_arp, responds_to_ping, in_mac_table,
             device_type, manufacturer, open_ports, response_time_ms,
             first_seen, last_seen)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            device.session_id,
            device.hostname,
            device.ip_address,
            device.mac_address,
            device.subnet,
            device.switch_ip,
            device.switch_port,
            device.port_age,
            device.status,
            device.confidence_score,
            device.evidence_sources,
            device.in_dhcp,
            device.in_arp,
            device.responds_to_ping,
            device.in_mac_table,
            device.device_type,
            device.manufacturer,
            device.open_ports,
            device.response_time_ms,
            device.first_seen,
            device.last_seen
        ))
        
        device_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return device_id
    
    @staticmethod
    def save_fault(fault: Fault) -> int:
        """Save detected fault"""
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO detected_faults 
            (session_id, fault_type, severity, primary_device_id, secondary_device_id,
             affected_ips, affected_macs, description, evidence, confidence,
             troubleshooting_steps, detected_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            fault.session_id,
            fault.fault_type,
            fault.severity,
            fault.primary_device_id,
            fault.secondary_device_id,
            fault.affected_ips,
            fault.affected_macs,
            fault.description,
            json.dumps(fault.evidence),
            fault.confidence,
            fault.troubleshooting_steps,
            fault.detected_at
        ))
        
        fault_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return fault_id
    
    @staticmethod
    def save_statistics(stats: NetworkStatistics) -> int:
        """Save network statistics"""
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO network_statistics 
            (session_id, subnet, total_devices, active_devices, powered_off_devices,
             cable_failures, new_devices, removed_devices, ip_conflicts,
             network_loops, high_latency_devices, packet_loss_devices,
             dhcp_exhaustion, bandwidth_saturation, avg_response_time_ms,
             scan_duration_seconds)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            stats.session_id,
            stats.subnet,
            stats.total_devices,
            stats.active_devices,
            stats.powered_off_devices,
            stats.cable_failures,
            stats.new_devices,
            stats.removed_devices,
            stats.ip_conflicts,
            stats.network_loops,
            stats.high_latency_devices,
            stats.packet_loss_devices,
            stats.dhcp_exhaustion,
            stats.bandwidth_saturation,
            stats.avg_response_time_ms,
            stats.scan_duration_seconds
        ))
        
        stats_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return stats_id
    
    @staticmethod
    def log_event(level: str, component: str, message: str,
                  user_id: Optional[int] = None,
                  session_id: Optional[int] = None,
                  details: Optional[Dict] = None):
        """Log system event"""
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO system_logs 
            (log_level, component, user_id, session_id, message, details)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (level, component, user_id, session_id, message, json.dumps(details) if details else None))
        
        conn.commit()
        cur.close()
        conn.close()
    
    @staticmethod
    def get_session_results(session_id: int) -> Dict:
        """Get complete results for a session"""
        conn = get_connection()
        cur = conn.cursor()
        
        # Get session info
        cur.execute("SELECT * FROM diagnostic_sessions WHERE id = %s", (session_id,))
        session = cur.fetchone()
        
        # Get devices
        cur.execute("SELECT * FROM diagnostic_devices WHERE session_id = %s", (session_id,))
        devices = cur.fetchall()
        
        # Get faults
        cur.execute("SELECT * FROM detected_faults WHERE session_id = %s", (session_id,))
        faults = cur.fetchall()
        
        # Get statistics
        cur.execute("SELECT * FROM network_statistics WHERE session_id = %s", (session_id,))
        stats = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {
            'session': session,
            'devices': devices,
            'faults': faults,
            'statistics': stats
        }
