#!/usr/bin/env python3
"""
Bandwidth Saturation Detector
Monitors bandwidth usage on Master PC, Firewall, and Switches
Based on bsd_1.py but uses database for configuration
"""

import re
import time
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.diagnostics.base_detector import BaseDetector
from app.core.diagnostics.models import Fault, FAULT_BANDWIDTH_SATURATION


class BandwidthDetector(BaseDetector):
    """Monitor bandwidth usage across network components"""
    
    THRESHOLDS = {
        'warning': 80,   # % utilization
        'critical': 95,  # % utilization
    }
    
    def __init__(self, session_id: int):
        super().__init__(session_id)
        self.components = []
        
    def discover_components(self) -> List[Dict]:
        """Discover all components to monitor"""
        components = []
        
        # Add firewall
        components.append({
            'name': 'Firewall',
            'type': 'firewall',
            'ip': self.firewall_ip,
            'username': self.firewall_user,
            'password': self.firewall_pass,
            'interfaces': [iface['name'] for iface in self.firewall_interfaces if iface['name']]
        })
        
        # Add switches
        for switch in self.switches:
            components.append({
                'name': f"Switch_{switch['ip']}",
                'type': 'switch',
                'ip': switch['ip'],
                'username': switch['username'],
                'password': switch['password'],
                'sudo_password': switch.get('sudo_password'),
                'interfaces': []  # Will discover dynamically
            })
        
        # Add master PC
        components.append({
            'name': 'Master_PC',
            'type': 'master',
            'ip': self.master_pc['ip'],
            'local': True,
            'interfaces': [self.master_pc['mgmt_iface']]
        })
        
        return components
    
    def get_interface_stats(self, component: Dict, interface: str, duration: int = 3) -> Dict:
        """Get bandwidth statistics for an interface"""
        
        if component.get('local', False):
            # Local monitoring
            try:
                with open('/proc/net/dev', 'r') as f:
                    lines = f.readlines()
                
                stats1 = self._parse_proc_net_dev(lines, interface)
                time1 = time.time()
                
                time.sleep(duration)
                
                with open('/proc/net/dev', 'r') as f:
                    lines = f.readlines()
                stats2 = self._parse_proc_net_dev(lines, interface)
                time2 = time.time()
                
            except Exception as e:
                return {'error': str(e)}
        else:
            # Remote via SSH
            if not self.ssh_connect(component['ip'], component['username'], component['password']):
                return {'error': 'SSH connection failed'}
            
            output1 = self.ssh_exec(component['ip'], "cat /proc/net/dev")
            stats1 = self._parse_proc_net_dev(output1.split('\n'), interface)
            time1 = time.time()
            
            time.sleep(duration)
            
            output2 = self.ssh_exec(component['ip'], "cat /proc/net/dev")
            stats2 = self._parse_proc_net_dev(output2.split('\n'), interface)
            time2 = time.time()
        
        time_delta = time2 - time1
        if time_delta <= 0 or not stats1 or not stats2:
            return {'error': 'Invalid stats'}
        
        # Calculate bandwidth
        rx_bytes_delta = stats2['rx_bytes'] - stats1['rx_bytes']
        tx_bytes_delta = stats2['tx_bytes'] - stats1['tx_bytes']
        
        rx_mbps = (rx_bytes_delta * 8) / (time_delta * 1000000)
        tx_mbps = (tx_bytes_delta * 8) / (time_delta * 1000000)
        total_mbps = rx_mbps + tx_mbps
        
        # Estimate interface speed (default 1000 Mbps)
        speed_mbps = 1000
        
        utilization = (total_mbps / speed_mbps) * 100 if speed_mbps > 0 else 0
        
        return {
            'interface': interface,
            'rx_mbps': round(rx_mbps, 2),
            'tx_mbps': round(tx_mbps, 2),
            'total_mbps': round(total_mbps, 2),
            'utilization': round(utilization, 1),
            'rx_packets': stats2['rx_packets'] - stats1['rx_packets'],
            'tx_packets': stats2['tx_packets'] - stats1['tx_packets'],
            'rx_errors': stats2['rx_errors'] - stats1['rx_errors'],
            'tx_errors': stats2['tx_errors'] - stats1['tx_errors']
        }
    
    def _parse_proc_net_dev(self, lines: List[str], interface: str) -> Optional[Dict]:
        """Parse /proc/net/dev output for an interface"""
        for line in lines:
            if interface in line:
                parts = line.split()
                # Format: interface: rx_bytes rx_packets rx_errs ... tx_bytes ...
                if len(parts) >= 17:
                    return {
                        'rx_bytes': int(parts[1]),
                        'rx_packets': int(parts[2]),
                        'rx_errors': int(parts[3]),
                        'tx_bytes': int(parts[9]),
                        'tx_packets': int(parts[10]),
                        'tx_errors': int(parts[11]),
                    }
        return None
    
    def monitor_interface(self, component: Dict, interface: str) -> Optional[Fault]:
        """Monitor a single interface for bandwidth saturation"""
        result = self.get_interface_stats(component, interface)
        
        if 'error' in result:
            self.log(f"  Error monitoring {component['name']}/{interface}: {result['error']}", 'WARNING')
            return None
        
        utilization = result['utilization']
        
        if utilization >= self.THRESHOLDS['critical']:
            status = 'CRITICAL'
            severity = 'high'
            message = f"Bandwidth saturated: {utilization}%"
        elif utilization >= self.THRESHOLDS['warning']:
            status = 'WARNING'
            severity = 'medium'
            message = f"Bandwidth congestion: {utilization}%"
        else:
            return None  # No fault
        
        steps = self.get_troubleshooting_steps('BANDWIDTH_SATURATION')
        
        fault = Fault(
            session_id=self.session_id,
            fault_type='BANDWIDTH_SATURATION',
            severity=severity,
            description=f"{status}: {component['name']} interface {interface} - {message}",
            affected_ips=[component['ip']] if component.get('ip') else [],
            evidence={
                'component': component['name'],
                'interface': interface,
                'utilization': utilization,
                'rx_mbps': result['rx_mbps'],
                'tx_mbps': result['tx_mbps'],
                'total_mbps': result['total_mbps'],
                'thresholds': self.THRESHOLDS
            },
            troubleshooting_steps=steps
        )
        
        return fault
    
    def detect(self) -> List[Fault]:
        """Monitor bandwidth across all components"""
        self.log("=" * 60)
        self.log("BANDWIDTH SATURATION DETECTOR")
        self.log("=" * 60)
        
        faults = []
        
        # Discover components
        self.components = self.discover_components()
        self.log(f"Monitoring {len(self.components)} components")
        
        # Monitor each component
        for component in self.components:
            self.log(f"  Monitoring {component['name']}...")
            
            # Get interfaces to monitor
            interfaces = component.get('interfaces', [])
            if not interfaces and component['type'] == 'switch':
                # Try to discover interfaces
                if self.ssh_connect(component['ip'], component['username'], component['password']):
                    output = self.ssh_exec(component['ip'], "ip link show | grep -E '^[0-9]+: ens' | cut -d: -f2 | tr -d ' '")
                    interfaces = output.split('\n')
            
            for iface in interfaces[:3]:  # Limit to first 3 interfaces
                try:
                    fault = self.monitor_interface(component, iface)
                    if fault:
                        faults.append(fault)
                        self.add_fault(
                            'BANDWIDTH_SATURATION',
                            fault.severity,
                            f"{fault.severity.upper()}: {component['name']}/{iface} at {fault.evidence['utilization']}%",
                            affected_ips=[component['ip']] if component.get('ip') else [],
                            evidence=fault.evidence
                        )
                        self.log(f"    {iface}: {fault.evidence['utilization']}% - {fault.severity}")
                    else:
                        self.log(f"    {iface}: OK")
                except Exception as e:
                    self.log(f"    Error monitoring {iface}: {e}", 'ERROR')
        
        self.log(f"Bandwidth detection complete: {len(faults)} faults")
        return faults
