#!/usr/bin/env python3
"""
Base Detector Class - All detectors inherit from this
Provides common functionality: SSH, DB access, logging, fault recording
"""

import paramiko
import time
import json
import subprocess
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from app.db.connection import get_connection
from app.core.diagnostics.models import DiagnosticSession, DiscoveredDevice, Fault


class BaseDetector(ABC):
    """Base class for all fault detectors"""
    
    def __init__(self, session_id: int):
        self.session_id = session_id
        self.ssh_connections: Dict[str, paramiko.SSHClient] = {}
        self.faults_detected: List[Fault] = []
        self.devices_discovered: List[DiscoveredDevice] = []
        self.start_time = time.time()
        
        # Load infrastructure from database
        self.load_infrastructure()
    
    def load_infrastructure(self):
        """Load network infrastructure from database (no hardcoding!)"""
        conn = get_connection()
        cur = conn.cursor()
        
        # Get network setup
        cur.execute("""
            SELECT master_pc_ip, master_pc_interface, gateway_ip,
                   diagnostic_interface, diagnostic_ip, switch_sudo_password
            FROM network_setup 
            ORDER BY setup_timestamp DESC 
            LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            self.master_pc = {
                'ip': row[0],
                'mgmt_iface': row[1],
                'gateway': row[2],
                'diag_iface': row[3],
                'diag_ip': row[4],
                'sudo_password': row[5]
            }
        else:
            self.master_pc = {
                'ip': '127.0.0.1',
                'mgmt_iface': 'lo',
                'gateway': None,
                'diag_iface': None,
                'diag_ip': None,
                'sudo_password': None
            }
        
        # Get firewall interfaces (all subnets)
        cur.execute("""
            SELECT interface_name, interface_type, ip_address, subnet_cidr,
                   parent_interface, vlan_id
            FROM firewall_interfaces
            WHERE interface_type != 'WAN'
            ORDER BY interface_type
        """)
        self.firewall_interfaces = []
        for row in cur.fetchall():
            self.firewall_interfaces.append({
                'name': row[0],
                'type': row[1],
                'ip': row[2],
                'subnet': row[3],
                'parent': row[4],
                'vlan_id': row[5]
            })
        
        # Get firewall credentials
        cur.execute("""
            SELECT ip_address FROM firewall_interfaces 
            WHERE interface_type = 'LAN' OR interface_type = 'MGMT'
            LIMIT 1
        """)
        row = cur.fetchone()
        self.firewall_ip = row[0] if row else self.master_pc.get('gateway')
        
        # Default firewall credentials (should be stored encrypted in production)
        self.firewall_user = 'admin'
        self.firewall_pass = 'pfsense'
        
        # Get all managed switches
        cur.execute("""
            SELECT ms.switch_ip, ms.ssh_username, ms.ssh_password_encrypted,
                   ms.sudo_password, ms.switch_type, fi.subnet_cidr,
                   fi.interface_type, fi.id as subnet_id
            FROM managed_switches ms
            JOIN firewall_interfaces fi ON ms.subnet_id = fi.id
            WHERE ms.last_seen > NOW() - INTERVAL '30 days'
        """)
        self.switches = []
        for row in cur.fetchall():
            # Decrypt password (simplified - use proper encryption in production)
            password = row[2].replace('ENCRYPTED:', '') if row[2] else None
            self.switches.append({
                'ip': row[0],
                'username': row[1],
                'password': password,
                'sudo_password': row[3],
                'type': row[4],
                'subnet': row[5],
                'interface_type': row[6],
                'subnet_id': row[7]
            })
        
        cur.close()
        conn.close()
    
    def ssh_connect(self, host: str, username: str, password: str, 
                    sudo_password: Optional[str] = None, timeout: int = 10) -> bool:
        """Establish SSH connection to a host"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=host,
                username=username,
                password=password,
                look_for_keys=False,
                allow_agent=False,
                timeout=timeout,
                banner_timeout=timeout,
                auth_timeout=timeout
            )
            self.ssh_connections[host] = ssh
            return True
        except Exception as e:
            self.log(f"SSH connection failed to {host}: {e}", 'ERROR')
            return False
    
    def ssh_exec(self, host: str, command: str, use_sudo: bool = False) -> str:
        """Execute command on host via SSH"""
        ssh = self.ssh_connections.get(host)
        if not ssh:
            return ""
        
        try:
            if use_sudo:
                # Find sudo password for this host
                sudo_pass = None
                if host == self.master_pc.get('ip'):
                    sudo_pass = self.master_pc.get('sudo_password')
                else:
                    for switch in self.switches:
                        if switch['ip'] == host:
                            sudo_pass = switch.get('sudo_password')
                            break
                
                if sudo_pass:
                    # Use sudo with password via stdin
                    cmd = f'echo "{sudo_pass}" | sudo -S {command}'
                else:
                    cmd = f'sudo {command}'
            else:
                cmd = command
            
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')
            
            if error and 'password' not in error.lower():
                self.log(f"Command stderr on {host}: {error[:100]}", 'WARNING')
            
            return output.strip()
        except Exception as e:
            self.log(f"Command failed on {host}: {e}", 'ERROR')
            return ""
    
    def disconnect_all(self):
        """Close all SSH connections"""
        for host, ssh in self.ssh_connections.items():
            try:
                ssh.close()
                self.log(f"Disconnected from {host}", 'DEBUG')
            except:
                pass
        self.ssh_connections.clear()
    
    def ping(self, ip: str, count: int = 1, timeout: int = 2) -> Tuple[bool, float]:
        """
        Ping a device
        Returns: (success, response_time_ms)
        """
        try:
            start = time.time()
            result = subprocess.run(
                ['ping', '-c', str(count), '-W', str(timeout), ip],
                capture_output=True,
                text=True,
                timeout=timeout + 1
            )
            elapsed = (time.time() - start) * 1000  # Convert to ms
            
            if result.returncode == 0:
                # Extract average time if available
                import re
                match = re.search(r'time=(\d+\.?\d*)', result.stdout)
                if match:
                    response_time = float(match.group(1))
                else:
                    response_time = elapsed / count
                return True, response_time
            return False, 0
        except Exception:
            return False, 0
    
    def log(self, message: str, level: str = 'INFO'):
        """Log message to database"""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO system_logs (log_level, component, session_id, message)
            VALUES (%s, %s, %s, %s)
        """, (level, self.__class__.__name__, self.session_id, message))
        conn.commit()
        cur.close()
        conn.close()
        
        # Also print to console for debugging
        print(f"[{level}] {self.__class__.__name__}: {message}")
    
    def add_fault(self, fault_type: str, severity: str, description: str,
                  affected_ips: List[str] = None, affected_macs: List[str] = None,
                  evidence: Dict = None, device_ids: List[int] = None) -> int:
        """
        Add detected fault to database
        Returns: fault_id
        """
        if affected_ips is None:
            affected_ips = []
        if affected_macs is None:
            affected_macs = []
        if evidence is None:
            evidence = {}
        
        # Get troubleshooting steps from fault_categories
        steps = self.get_troubleshooting_steps(fault_type)
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO detected_faults 
            (session_id, fault_type, severity, description, affected_ips, 
             affected_macs, evidence, troubleshooting_steps, detected_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            self.session_id, fault_type, severity, description,
            affected_ips, affected_macs, json.dumps(evidence), steps,
            datetime.now()
        ))
        
        fault_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        self.log(f"Added fault: {fault_type} - {description[:50]}...", 'INFO')
        return fault_id
    
    def get_troubleshooting_steps(self, fault_name: str) -> List[str]:
        """Get troubleshooting steps from fault_categories table"""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT troubleshooting_steps FROM fault_categories 
            WHERE fault_name = %s
        """, (fault_name,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row:
            return row[0]
        else:
            # Default steps
            return [
                "Check physical connections",
                "Verify device configuration",
                "Check logs for errors",
                "Restart device if necessary",
                "Contact network administrator"
            ]
    
    def save_device(self, device: Dict) -> int:
        """
        Save discovered device to database
        Returns: device_id
        """
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO diagnostic_devices 
            (session_id, hostname, ip_address, mac_address, subnet,
             switch_ip, switch_port, status, confidence_score,
             evidence_sources, in_dhcp, in_arp, responds_to_ping, in_mac_table,
             device_type, response_time_ms, last_seen)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            self.session_id,
            device.get('hostname'),
            device.get('ip'),
            device.get('mac'),
            device.get('subnet'),
            device.get('switch_ip'),
            device.get('switch_port'),
            device.get('status', 'unknown'),
            device.get('confidence', 0.5),
            device.get('evidence_sources', []),
            device.get('in_dhcp', False),
            device.get('in_arp', False),
            device.get('responds_to_ping', False),
            device.get('in_mac_table', False),
            device.get('device_type', 'unknown'),
            device.get('response_time_ms'),
            datetime.now()
        ))
        
        device_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return device_id
    
    def update_session_stats(self, devices_count: int = None, faults_count: int = None):
        """Update diagnostic session statistics"""
        conn = get_connection()
        cur = conn.cursor()
        
        if devices_count is not None:
            cur.execute("""
                UPDATE diagnostic_sessions 
                SET total_devices_found = %s
                WHERE id = %s
            """, (devices_count, self.session_id))
        
        if faults_count is not None:
            # Count by severity
            cur.execute("""
                SELECT severity, COUNT(*) 
                FROM detected_faults 
                WHERE session_id = %s 
                GROUP BY severity
            """, (self.session_id,))
            
            stats = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
            for row in cur.fetchall():
                stats[row[0].lower()] = row[1]
            
            cur.execute("""
                UPDATE diagnostic_sessions 
                SET total_faults_detected = %s,
                    critical_faults = %s,
                    high_faults = %s,
                    medium_faults = %s,
                    low_faults = %s,
                    info_faults = %s
                WHERE id = %s
            """, (
                faults_count,
                stats.get('critical', 0),
                stats.get('high', 0),
                stats.get('medium', 0),
                stats.get('low', 0),
                stats.get('info', 0),
                self.session_id
            ))
        
        conn.commit()
        cur.close()
        conn.close()
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        return time.time() - self.start_time
    
    @abstractmethod
    def detect(self) -> List[Fault]:
        """Main detection method - to be implemented by each detector"""
        pass
