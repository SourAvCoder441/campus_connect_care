#!/usr/bin/env python3
"""
DHCP Exhaustion Detector
Checks DHCP pool utilization for all subnets
Based on dhcp_exhaust_1.py but uses database for configuration
"""

import re
from typing import Dict, List, Optional
from collections import defaultdict

from app.core.diagnostics.base_detector import BaseDetector
from app.core.diagnostics.models import Fault, FAULT_DHCP_EXHAUSTION


class DHCPExhaustionDetector(BaseDetector):
    """Detect DHCP pool exhaustion in all subnets"""
    
    THRESHOLDS = {
        'warning': 80,   # % utilized
        'critical': 95,  # % utilized
    }
    
    def __init__(self, session_id: int):
        super().__init__(session_id)
        self.subnet_stats = []
        
    def discover_dhcp_subnets(self) -> List[Dict]:
        """Discover all subnets with DHCP enabled"""
        if not self.ssh_connect(self.firewall_ip, self.firewall_user, self.firewall_pass):
            # Fallback to subnets from firewall_interfaces
            subnets = []
            for iface in self.firewall_interfaces:
                if iface['subnet'] and iface['type'] not in ['WAN', 'LOOPBACK']:
                    subnets.append({
                        'subnet': iface['subnet'],
                        'interface': iface['name'],
                        'gateway': iface['ip'],
                        'pool_size': 101,  # Default
                        'range_start': None,
                        'range_end': None
                    })
            return subnets
        
        # Read DHCP configuration
        config = self.ssh_exec(self.firewall_ip, 'cat /var/dhcpd/etc/dhcpd.conf')
        
        subnets = []
        current_subnet = None
        current_interface = None
        
        for line in config.split('\n'):
            line = line.strip()
            
            # Check for subnet declaration
            subnet_match = re.match(r'subnet\s+(\d+\.\d+\.\d+\.0)\s+netmask\s+(\d+\.\d+\.\d+\.\d+)', line)
            if subnet_match:
                current_subnet = subnet_match.group(1)
                netmask = subnet_match.group(2)
                continue
            
            # Check for interface
            iface_match = re.match(r'interface\s+"?([\w\.]+)"?', line)
            if iface_match and current_subnet:
                current_interface = iface_match.group(1)
            
            # Check for range
            range_match = re.match(r'range\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+);', line)
            if range_match and current_subnet:
                start_ip = range_match.group(1)
                end_ip = range_match.group(2)
                
                # Calculate pool size
                try:
                    start_parts = [int(x) for x in start_ip.split('.')]
                    end_parts = [int(x) for x in end_ip.split('.')]
                    pool_size = (end_parts[3] - start_parts[3]) + 1
                    
                    gateway = current_subnet.rsplit('.', 1)[0] + '.1'
                    
                    subnets.append({
                        'subnet': f"{current_subnet}/24",
                        'interface': current_interface or 'unknown',
                        'gateway': gateway,
                        'range_start': start_ip,
                        'range_end': end_ip,
                        'pool_size': pool_size
                    })
                except:
                    pass
                
                current_subnet = None
                current_interface = None
        
        return subnets
    
    def count_leases_for_subnet(self, subnet: str) -> int:
        """Count DHCP leases belonging to a subnet"""
        output = self.ssh_exec(self.firewall_ip,
                              'cat /var/dhcpd/var/db/dhcpd.leases')
        
        # Extract subnet prefix
        subnet_prefix = subnet.split('/')[0].rsplit('.', 1)[0]
        
        count = 0
        for match in re.finditer(r'lease\s+([\d.]+)\s*\{', output):
            ip = match.group(1)
            if ip.startswith(subnet_prefix):
                count += 1
        
        return count
    
    def detect(self) -> List[Fault]:
        """Check DHCP pool utilization for all subnets"""
        self.log("=" * 60)
        self.log("DHCP EXHAUSTION DETECTOR")
        self.log("=" * 60)
        
        faults = []
        
        # Discover DHCP subnets
        subnets = self.discover_dhcp_subnets()
        self.log(f"Found {len(subnets)} DHCP subnets")
        
        for subnet_info in subnets:
            subnet = subnet_info['subnet']
            pool_size = subnet_info['pool_size']
            
            # Count leases
            leases_used = self.count_leases_for_subnet(subnet)
            utilization = round((leases_used / pool_size) * 100, 1) if pool_size > 0 else 0
            
            self.log(f"  {subnet}: {leases_used}/{pool_size} ({utilization}%)")
            
            # Check thresholds
            if utilization >= self.THRESHOLDS['critical']:
                status = 'CRITICAL'
                severity = 'high'
                message = f"DHCP pool critically full: {leases_used}/{pool_size} ({utilization}%)"
            elif utilization >= self.THRESHOLDS['warning']:
                status = 'WARNING'
                severity = 'medium'
                message = f"DHCP pool nearly full: {leases_used}/{pool_size} ({utilization}%)"
            else:
                status = 'OK'
                continue  # No fault
            
            # Add fault
            steps = self.get_troubleshooting_steps('DHCP_EXHAUSTION')
            
            fault = Fault(
                session_id=self.session_id,
                fault_type='DHCP_EXHAUSTION',
                severity=severity,
                description=message,
                affected_ips=[],
                evidence={
                    'subnet': subnet,
                    'interface': subnet_info.get('interface'),
                    'gateway': subnet_info.get('gateway'),
                    'pool_size': pool_size,
                    'leases_used': leases_used,
                    'utilization': utilization,
                    'range_start': subnet_info.get('range_start'),
                    'range_end': subnet_info.get('range_end')
                },
                troubleshooting_steps=steps
            )
            faults.append(fault)
            
            self.add_fault(
                'DHCP_EXHAUSTION', severity,
                message,
                evidence={
                    'subnet': subnet,
                    'utilization': utilization,
                    'leases_used': leases_used,
                    'pool_size': pool_size
                }
            )
        
        self.log(f"DHCP exhaustion detection complete: {len(faults)} faults")
        return faults
