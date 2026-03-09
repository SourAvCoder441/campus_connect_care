# app/core/diagnostics/detectors/device_discovery.py (CORRECTED)

#!/usr/bin/env python3
"""
Device Discovery Detector
Discovers devices from DHCP leases, maps them to switch ports, determines status
Based on sl8.py (proven working script)
"""

import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from app.core.diagnostics.base_detector import BaseDetector
from app.core.diagnostics.models import (
    DiscoveredDevice, Fault, DEVICE_STATUS_ACTIVE, DEVICE_STATUS_POWERED_OFF,
    DEVICE_STATUS_CABLE_FAILURE, DEVICE_STATUS_NEW, DEVICE_STATUS_REMOVED,
    FAULT_DEVICE_UNREACHABLE, FAULT_CABLE_FAILURE, FAULT_DEVICE_POWERED_OFF,
    FAULT_NEW_DEVICE, FAULT_DEVICE_REMOVED
)


class DeviceDiscoveryDetector(BaseDetector):
    """
    Device discovery from DHCP leases, ARP table, MAC tables
    Determines device status (active, powered_off, cable_failure, new, removed)
    Based on sl8.py proven logic
    """
    
    # Port to interface mapping (same as sl8.py)
    PORT_TO_INTERFACE = {
        "1": "ens33",
        "2": "ens40", 
        "4": "ens37",
        "5": "ens38",
        "6": "ens39"
    }
    
    # Ping configuration (same as sl8.py)
    PING_TIMEOUT = 3
    PING_RETRIES = 2
    RETRY_DELAY = 0.5
    
    def __init__(self, session_id: int):
        super().__init__(session_id)
        self.devices = []
        self.removed_devices = []
        self.mac_tables = {}  # switch_ip -> {mac: {port, age}}
        self.port_macs = {}   # switch_ip -> {port: [macs]}
        self.arp_table = {}
        
    def get_dhcp_leases(self) -> List[Dict]:
        """Fetch DHCP leases from firewall - same as sl8.py"""
        self.log("Fetching DHCP leases from firewall...")
        
        if not self.ssh_connect(self.firewall_ip, self.firewall_user, self.firewall_pass):
            self.log("Could not connect to firewall for DHCP leases", 'WARNING')
            return []
        
        output = self.ssh_exec(self.firewall_ip,
                              "cat /var/dhcpd/var/db/dhcpd.leases 2>/dev/null")
        
        if not output:
            self.log("No DHCP lease data retrieved", 'WARNING')
            return []
        
        return self._parse_dhcp_leases(output)
    
    def _parse_dhcp_leases(self, raw: str) -> List[Dict]:
        """Parse DHCP leases from pfSense - exact same as sl8.py"""
        leases = {}  # keyed by MAC to avoid duplicates
        
        for m in re.finditer(r"lease\s+([\d.]+)\s*\{([^}]+)\}", raw, re.DOTALL):
            ip, block = m.group(1), m.group(2)
            
            # Extract MAC address
            mac_m = re.search(r"hardware\s+ethernet\s+([0-9a-f:]{17})", block, re.I)
            if not mac_m:
                continue
                
            mac = mac_m.group(1).lower()
            
            # Extract hostname
            hostname = self._extract_hostname(block)
            
            # Skip infrastructure devices (same as sl8.py)
            blocked_names = ["gns3vm", "laptop"]
            if hostname and any(x in hostname.lower() for x in blocked_names):
                continue
            
            # Generate display name if generic (same as sl8.py)
            if hostname and (hostname.startswith("dhcp-") or hostname == ip):
                hostname = f"Device-{mac[-6:].replace(':', '')}"
            
            # Handle duplicates - PREFER ENTRIES WITH HOSTNAMES (same as sl8.py)
            if mac in leases:
                current = leases[mac]
                current_hostname = current.get("hostname")
                
                if not current_hostname and hostname:
                    # Current has no hostname, new one has hostname - REPLACE
                    leases[mac] = {
                        'ip': ip,
                        'mac': mac,
                        'hostname': hostname,
                        'subnet': '.'.join(ip.split('.')[:3]) + '.0/24'
                    }
                # Otherwise keep current
            else:
                if hostname:  # Only add if has hostname
                    leases[mac] = {
                        'ip': ip,
                        'mac': mac,
                        'hostname': hostname,
                        'subnet': '.'.join(ip.split('.')[:3]) + '.0/24'
                    }
        
        return list(leases.values())
    
    def _extract_hostname(self, block: str) -> Optional[str]:
        """Extract hostname from DHCP lease block - same as sl8.py"""
        for pattern in [
            r'client-hostname\s+"([^"]+)"',
            r'hostname\s+"([^"]+)"',
            r'ddns-hostname\s+"([^"]+)"'
        ]:
            m = re.search(pattern, block, re.I)
            if m:
                return m.group(1).strip()
        return None
    
    def get_arp_table(self) -> Dict[str, str]:
        """Get ARP table from firewall"""
        self.log("Fetching ARP table from firewall...")
        
        output = self.ssh_exec(self.firewall_ip, "arp -an")
        
        arp = {}
        for line in output.split('\n'):
            # Parse: ? (192.168.10.100) at aa:bb:cc:dd:ee:ff on em1
            ip_match = re.search(r'\((\d+\.\d+\.\d+\.\d+)\)', line)
            mac_match = re.search(r'([0-9a-f:]{17})', line, re.I)
            
            if ip_match and mac_match:
                ip = ip_match.group(1)
                mac = mac_match.group(1).lower()
                if mac != '(incomplete)':
                    arp[ip] = mac
        
        return arp
    
    def get_switch_mac_tables(self):
        """Get MAC tables from all managed switches - same as sl8.py"""
        self.log("Fetching MAC tables from switches...")
        
        for switch in self.switches:
            if not self.ssh_connect(switch['ip'], switch['username'], switch['password']):
                continue
            
            # For OVS switches (same as sl8.py)
            if 'Open' in switch['type'] or 'ovs' in switch['type'].lower():
                output = self.ssh_exec(switch['ip'],
                                      f"sudo ovs-appctl fdb/show br0",
                                      use_sudo=True)
                
                macs, port_macs = self._parse_ovs_mac_table(output)
                self.mac_tables[switch['ip']] = macs
                self.port_macs[switch['ip']] = port_macs
                
                self.log(f"  Switch {switch['ip']}: {len(macs)} MAC entries")
    
    def _parse_ovs_mac_table(self, output: str) -> Tuple[Dict, Dict]:
        """Parse OVS MAC table output - exact same as sl8.py"""
        macs = {}
        port_macs = defaultdict(list)
        
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 4 and re.match(r'^([0-9a-f]{2}:){5}[0-9a-f]{2}$', parts[2], re.I):
                mac = parts[2].lower()
                port = parts[0]
                age = parts[3]
                
                macs[mac] = {'port': port, 'age': age}
                port_macs[port].append(mac)
        
        return macs, port_macs
    
    def ping_device(self, ip: str) -> bool:
        """Ping device with retry logic - exact same as sl8.py"""
        for attempt in range(self.PING_RETRIES):
            try:
                import subprocess
                result = subprocess.run(
                    ['ping', '-c', '1', '-W', str(self.PING_TIMEOUT), ip],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=self.PING_TIMEOUT + 1
                )
                
                if result.returncode == 0:
                    return True
                    
                if attempt < self.PING_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                    
            except subprocess.TimeoutExpired:
                if attempt < self.PING_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                    continue
            except Exception:
                if attempt < self.PING_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                    continue
        
        return False
    
    def check_interface_status(self, switch_ip: str, port: str) -> bool:
        """Check if switch interface is UP - same as sl8.py"""
        # Get interface name from port number
        interface_name = self.PORT_TO_INTERFACE.get(port)
        if not interface_name:
            return False
        
        # Check if interface exists and is UP
        output = self.ssh_exec(switch_ip,
                              f"ip link show {interface_name} 2>/dev/null | grep -o 'state [A-Z]*' | cut -d' ' -f2",
                              use_sudo=True)
        
        return output.upper() == "UP"
    
    def determine_device_status(self, device: Dict, 
                               prev_devices: Dict[str, Dict],
                               switch_accessible: bool) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Determine device status based on sl8.py logic:
        - Ping success = ACTIVE (get current port from switch)
        - Ping failure + no previous port = POWERED_OFF
        - Ping failure + has previous port:
            - Interface DOWN = CABLE_FAILURE
            - Interface UP = POWERED_OFF (keep same port)
        """
        ip = device['ip']
        mac = device.get('mac', '')
        is_new = device.get('is_new', False)
        
        # Default values
        status = DEVICE_STATUS_NEW if is_new else DEVICE_STATUS_ACTIVE
        switch_ip = None
        switch_port = "N/A"
        port_age = "N/A"
        prev_port = "N/A"
        
        # Check if device existed in previous data
        prev_device = None
        if not is_new:
            if device.get('hostname') and device['hostname'] in prev_devices:
                prev_device = prev_devices[device['hostname']]
            elif mac and mac in prev_devices:
                prev_device = prev_devices[mac]
        
        # Get previous port if available
        if prev_device:
            prev_port = prev_device.get('switch_port', "N/A")
            switch_port = prev_port
        
        # STEP 1: Ping device with retries
        ping_success = self.ping_device(ip)
        device['responds_to_ping'] = ping_success
        
        # Find device in current MAC tables
        found_switch = None
        found_port = None
        found_age = None
        
        for sw_ip, mac_table in self.mac_tables.items():
            if mac in mac_table:
                found_switch = sw_ip
                found_port = mac_table[mac]['port']
                found_age = mac_table[mac]['age']
                break
        
        # CASE 1: PING SUCCESS - Device is ACTIVE
        if ping_success:
            status = DEVICE_STATUS_ACTIVE
            
            # For active devices, get current port from switch MAC table
            if found_switch:
                switch_ip = found_switch
                switch_port = found_port
                port_age = found_age
            elif prev_port != "N/A":
                switch_ip = prev_device.get('switch_ip')
                switch_port = prev_port
                port_age = "N/A"
            
            return status, switch_ip, switch_port, port_age
        
        # CASE 2: PING FAILS - Device is not responding
        if prev_port == "N/A" or not prev_device:
            # Device never had a port, just mark as powered off
            status = DEVICE_STATUS_POWERED_OFF if not is_new else DEVICE_STATUS_NEW
            return status, None, "N/A", "N/A"
        
        # Device has a previous port, check interface status
        if not switch_accessible or not prev_device.get('switch_ip'):
            # Switch not reachable, can't check interface
            status = DEVICE_STATUS_POWERED_OFF
            switch_ip = prev_device.get('switch_ip')
            switch_port = prev_port
            return status, switch_ip, switch_port, "N/A"
        
        # Check interface status on the switch
        is_interface_up = self.check_interface_status(prev_device['switch_ip'], prev_port)
        
        if not is_interface_up:
            # Interface is DOWN = CABLE FAILURE
            status = DEVICE_STATUS_CABLE_FAILURE
            switch_ip = prev_device.get('switch_ip')
            switch_port = prev_port
        else:
            # Interface is UP = Device is powered off
            status = DEVICE_STATUS_POWERED_OFF
            switch_ip = prev_device.get('switch_ip')
            switch_port = prev_port
        
        return status, switch_ip, switch_port, "N/A"
    
    def get_previous_devices(self) -> Dict[str, Dict]:
        """Get devices from previous diagnostic session for comparison"""
        from app.db.connection import get_connection
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Get most recent completed session before this one
        cur.execute("""
            SELECT dd.hostname, dd.ip_address, dd.mac_address, 
                   dd.switch_ip, dd.switch_port, dd.status
            FROM diagnostic_devices dd
            JOIN diagnostic_sessions ds ON dd.session_id = ds.id
            WHERE ds.status = 'completed' 
              AND ds.id < %s
            ORDER BY ds.id DESC
            LIMIT 100
        """, (self.session_id,))
        
        prev = {}
        for row in cur.fetchall():
            hostname, ip, mac, switch_ip, switch_port, status = row
            if hostname:
                prev[hostname] = {
                    'ip': ip,
                    'mac': mac,
                    'switch_ip': switch_ip,
                    'switch_port': switch_port,
                    'status': status
                }
            if mac:
                prev[mac] = {
                    'ip': ip,
                    'hostname': hostname,
                    'switch_ip': switch_ip,
                    'switch_port': switch_port,
                    'status': status
                }
        
        cur.close()
        conn.close()
        return prev
    
    def find_removed_devices(self, current_devices: List[Dict],
                            prev_devices: Dict[str, Dict]) -> List[Dict]:
        """Find devices that were in previous session but not in current - same as sl8.py"""
        removed = []
        
        # Get current identifiers
        current_hostnames = {d['hostname'] for d in current_devices if d.get('hostname')}
        current_macs = {d['mac'] for d in current_devices if d.get('mac')}
        
        # Check previous devices
        for key, prev in prev_devices.items():
            # Skip if this is a MAC or hostname that's still present
            if key in current_hostnames or key in current_macs:
                continue
            
            # This device is missing
            if isinstance(key, str) and (len(key) == 17 or ':' in key):  # MAC
                removed.append({
                    'hostname': prev.get('hostname', 'Unknown'),
                    'ip': prev.get('ip', 'N/A'),
                    'mac': key if len(key) == 17 else None,
                    'last_seen': prev.get('status', 'unknown'),
                    'switch_port': prev.get('switch_port')
                })
        
        return removed
    
    def detect(self) -> List[Fault]:
        """Main device discovery and status detection - based on sl8.py"""
        self.log("=" * 60)
        self.log("DEVICE DISCOVERY DETECTOR")
        self.log("=" * 60)
        
        faults = []
        
        # Get previous devices for comparison
        prev_devices = self.get_previous_devices()
        
        # Step 1: Get DHCP leases
        dhcp_devices = self.get_dhcp_leases()
        self.log(f"Found {len(dhcp_devices)} devices in DHCP leases")
        
        # Step 2: Get ARP table (for additional evidence)
        self.arp_table = self.get_arp_table()
        self.log(f"Found {len(self.arp_table)} ARP entries")
        
        # Step 3: Get MAC tables from switches
        self.get_switch_mac_tables()
        switch_accessible = len(self.mac_tables) > 0
        
        # Step 4: Classify devices as NEW or EXISTING
        self.log("Classifying devices...")
        for device in dhcp_devices:
            hostname = device.get('hostname', '')
            mac = device.get('mac', '')
            
            is_new = True
            if hostname and hostname in prev_devices:
                is_new = False
            elif mac and mac in prev_devices:
                is_new = False
            
            device['is_new'] = is_new
        
        # Step 5: Find removed devices
        removed = self.find_removed_devices(dhcp_devices, prev_devices)
        self.log(f"Found {len(removed)} removed devices")
        
        # Step 6: Determine status for each device
        self.log("Determining device status...")
        
        for device in dhcp_devices:
            # Add ARP info
            device['in_arp'] = device['ip'] in self.arp_table
            
            # Check if in MAC table
            mac = device.get('mac', '')
            device['in_mac_table'] = any(mac in mt for mt in self.mac_tables.values())
            
            # Determine status using sl8.py logic
            status, switch_ip, switch_port, port_age = self.determine_device_status(
                device, prev_devices, switch_accessible
            )
            
            device['status'] = status
            device['switch_ip'] = switch_ip
            device['switch_port'] = switch_port
            device['port_age'] = port_age
            
            # Add evidence sources
            sources = ['dhcp']
            if device['in_arp']:
                sources.append('arp')
            if device['responds_to_ping']:
                sources.append('ping')
            if device['in_mac_table']:
                sources.append('mac_table')
            device['evidence_sources'] = sources
            
            # Calculate confidence
            confidence = 0.2  # Base from DHCP
            if device['responds_to_ping']:
                confidence += 0.5
            if device['in_arp']:
                confidence += 0.2
            if device['in_mac_table']:
                confidence += 0.3
            device['confidence'] = min(confidence, 1.0)
            
            # Save to database
            device_id = self.save_device(device)
            device['id'] = device_id
            
            # Check if this is a new device that's active
            if device.get('is_new') and device['responds_to_ping']:
                steps = self.get_troubleshooting_steps('NEW_DEVICE_DETECTED')
                fault = Fault(
                    session_id=self.session_id,
                    fault_type='NEW_DEVICE_DETECTED',
                    severity='info',
                    description=f"New device detected: {device.get('hostname', 'Unknown')} ({device['ip']})",
                    affected_ips=[device['ip']],
                    affected_macs=[mac] if mac else [],
                    evidence=device,
                    troubleshooting_steps=steps
                )
                faults.append(fault)
        
        # Step 7: Add faults for removed devices
        for dev in removed:
            steps = self.get_troubleshooting_steps('DEVICE_REMOVED')
            fault = Fault(
                session_id=self.session_id,
                fault_type='DEVICE_REMOVED',
                severity='info',
                description=f"Device removed: {dev.get('hostname', 'Unknown')} ({dev.get('ip', 'N/A')})",
                affected_ips=[dev['ip']] if dev['ip'] != 'N/A' else [],
                affected_macs=[dev['mac']] if dev.get('mac') else [],
                evidence=dev,
                troubleshooting_steps=steps
            )
            faults.append(fault)
        
        # Step 8: Add faults for unreachable devices (that have evidence but no ping)
        for device in dhcp_devices:
            if not device['responds_to_ping']:
                if device.get('in_arp') or device.get('in_mac_table'):
                    # Device was seen recently but doesn't ping
                    if device['status'] == DEVICE_STATUS_CABLE_FAILURE:
                        fault_type = 'CABLE_FAILURE'
                        severity = 'high'
                        desc = f"Cable failure detected on port {device['switch_port']}"
                    else:
                        fault_type = 'DEVICE_UNREACHABLE'
                        severity = 'critical'
                        desc = f"Device unreachable"
                    
                    steps = self.get_troubleshooting_steps(fault_type)
                    fault = Fault(
                        session_id=self.session_id,
                        fault_type=fault_type,
                        severity=severity,
                        description=f"{desc}: {device.get('hostname', 'Unknown')} ({device['ip']})",
                        affected_ips=[device['ip']],
                        affected_macs=[device.get('mac')] if device.get('mac') else [],
                        evidence=device,
                        troubleshooting_steps=steps
                    )
                    faults.append(fault)
        
        self.log(f"Device discovery complete: {len(dhcp_devices)} devices, {len(faults)} faults")
        return faults
    
    def save_device(self, device: Dict) -> int:
        """Save device to database"""
        from app.db.connection import get_connection
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO diagnostic_devices 
            (session_id, hostname, ip_address, mac_address, subnet,
             switch_ip, switch_port, port_age, status, confidence_score,
             evidence_sources, in_dhcp, in_arp, responds_to_ping, in_mac_table,
             device_type, response_time_ms, last_seen)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            self.session_id,
            device.get('hostname'),
            device.get('ip'),
            device.get('mac'),
            device.get('subnet'),
            device.get('switch_ip'),
            device.get('switch_port'),
            device.get('port_age'),
            device.get('status', 'unknown'),
            device.get('confidence', 0.5),
            device.get('evidence_sources', []),
            True,  # in_dhcp (always True since from DHCP)
            device.get('in_arp', False),
            device.get('responds_to_ping', False),
            device.get('in_mac_table', False),
            'unknown',  # device_type
            device.get('response_time_ms'),
            datetime.now()
        ))
        
        device_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return device_id
