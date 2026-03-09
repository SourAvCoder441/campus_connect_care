#!/usr/bin/env python3
"""
IP Conflict Detector
Detects IP conflicts from DHCP leases, ARP table, and MAC tables
Based on ipc1.py but uses database for configuration
"""

import re
import time
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

from app.core.diagnostics.base_detector import BaseDetector
from app.core.diagnostics.models import Fault, FAULT_IP_CONFLICT


class IPConflictDetector(BaseDetector):
    """Detect IP conflicts from multiple sources"""
    
    def __init__(self, session_id: int):
        super().__init__(session_id)
        self.mappings = []  # List of all IP-MAC mappings
        self.conflicts = []
        
    def get_dhcp_mappings(self) -> List[Dict]:
        """Get IP-MAC mappings from DHCP leases"""
        if not self.ssh_connect(self.firewall_ip, self.firewall_user, self.firewall_pass):
            return []
        
        output = self.ssh_exec(self.firewall_ip,
                              "cat /var/dhcpd/var/db/dhcpd.leases 2>/dev/null | head -1000")
        
        mappings = []
        seen_macs = set()
        
        for m in re.finditer(r"lease\s+([\d.]+)\s*\{([^}]+)\}", output, re.DOTALL):
            ip, block = m.group(1), m.group(2)
            
            mac_match = re.search(r"hardware\s+ethernet\s+([0-9a-f:]{17})", block, re.I)
            if not mac_match:
                continue
                
            mac = mac_match.group(1).lower()
            
            if mac in seen_macs:
                continue
            
            # Extract hostname
            hostname = "Unknown"
            for pattern in [r'client-hostname\s+"([^"]+)"', r'hostname\s+"([^"]+)"']:
                match = re.search(pattern, block, re.I)
                if match:
                    hostname = match.group(1).strip()
                    break
            
            mappings.append({
                'ip': ip,
                'mac': mac,
                'source': 'dhcp',
                'timestamp': time.time(),
                'hostname': hostname
            })
            seen_macs.add(mac)
        
        self.log(f"Found {len(mappings)} DHCP mappings")
        return mappings
    
    def get_arp_mappings(self) -> List[Dict]:
        """Get IP-MAC mappings from ARP table"""
        output = self.ssh_exec(self.firewall_ip, "arp -an 2>/dev/null | head -200")
        
        mappings = []
        
        for line in output.split('\n'):
            ip_match = re.search(r'\(?(\d+\.\d+\.\d+\.\d+)\)?', line)
            mac_match = re.search(r'([0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2})', line, re.I)
            
            if ip_match and mac_match:
                ip = ip_match.group(1)
                mac = mac_match.group(1).lower()
                
                if mac in ["00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff", "(incomplete)"]:
                    continue
                
                mappings.append({
                    'ip': ip,
                    'mac': mac,
                    'source': 'arp',
                    'timestamp': time.time()
                })
        
        self.log(f"Found {len(mappings)} ARP mappings")
        return mappings
    
    def get_switch_mappings(self) -> List[Dict]:
        """Get MAC addresses from switch (no IPs)"""
        mappings = []
        
        for switch in self.switches:
            if not self.ssh_connect(switch['ip'], switch['username'], switch['password']):
                continue
            
            if 'Open' in switch['type'] or 'ovs' in switch['type'].lower():
                output = self.ssh_exec(switch['ip'],
                                      f"sudo ovs-appctl fdb/show br0 2>/dev/null | head -200",
                                      use_sudo=True)
            else:
                output = self.ssh_exec(switch['ip'], "brctl showmacs br0 2>/dev/null | head -200")
            
            for line in output.split('\n'):
                parts = line.split()
                if len(parts) >= 4:
                    mac_candidate = parts[2] if 'Open' in switch['type'] else parts[1]
                    if re.match(r'^([0-9a-f]{2}:){5}[0-9a-f]{2}$', mac_candidate, re.I):
                        mac = mac_candidate.lower()
                        port = parts[0] if 'Open' in switch['type'] else parts[3]
                        
                        mappings.append({
                            'ip': 'N/A',
                            'mac': mac,
                            'source': 'mac_table',
                            'timestamp': time.time(),
                            'switch': switch['ip'],
                            'port': port
                        })
        
        self.log(f"Found {len(mappings)} MAC table entries")
        return mappings
    
    def detect(self) -> List[Fault]:
        """Detect IP conflicts"""
        self.log("=" * 60)
        self.log("IP CONFLICT DETECTOR")
        self.log("=" * 60)
        
        faults = []
        
        # Collect data from all sources
        dhcp = self.get_dhcp_mappings()
        arp = self.get_arp_mappings()
        mac = self.get_switch_mappings()
        
        self.mappings = dhcp + arp
        
        # Build IP to MACs mapping
        ip_to_macs = defaultdict(set)
        mac_to_ips = defaultdict(set)
        
        for m in self.mappings:
            ip_to_macs[m['ip']].add(m['mac'])
            mac_to_ips[m['mac']].add(m['ip'])
        
        # 1. Direct conflicts: Same IP, different MACs
        for ip, macs in ip_to_macs.items():
            if len(macs) > 1:
                self.log(f"Direct conflict: {ip} used by {len(macs)} MACs")
                
                # Collect evidence
                evidence = []
                for m in self.mappings:
                    if m['ip'] == ip:
                        evidence.append({
                            'mac': m['mac'],
                            'source': m['source'],
                            'timestamp': m.get('timestamp')
                        })
                
                steps = self.get_troubleshooting_steps('IP_CONFLICT')
                
                fault = Fault(
                    session_id=self.session_id,
                    fault_type='IP_CONFLICT',
                    severity='critical',
                    description=f"IP {ip} is used by {len(macs)} different devices",
                    affected_ips=[ip],
                    affected_macs=list(macs),
                    evidence={'mappings': evidence, 'conflicting_macs': list(macs)},
                    troubleshooting_steps=steps
                )
                faults.append(fault)
                
                self.add_fault(
                    'IP_CONFLICT', 'critical',
                    f"IP {ip} used by {len(macs)} devices: {', '.join(macs)}",
                    affected_ips=[ip],
                    affected_macs=list(macs),
                    evidence={'conflicting_macs': list(macs)}
                )
        
        # 2. MAC in switch but not in DHCP/ARP (static IP suspected)
        for m in mac:
            mac_addr = m['mac']
            if mac_addr not in mac_to_ips:
                steps = self.get_troubleshooting_steps('NEW_DEVICE_DETECTED')
                
                fault = Fault(
                    session_id=self.session_id,
                    fault_type='NEW_DEVICE_DETECTED',
                    severity='info',
                    description=f"MAC {mac_addr} active on switch but not in DHCP/ARP (possible static IP)",
                    affected_macs=[mac_addr],
                    evidence={'switch': m['switch'], 'port': m['port']},
                    troubleshooting_steps=steps
                )
                faults.append(fault)
        
        self.log(f"IP conflict detection complete: {len(faults)} faults")
        return faults
