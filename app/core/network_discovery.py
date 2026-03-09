#!/usr/bin/env python3
"""
Network Discovery Module for Initial Setup
Detects firewall interfaces, validates connectivity, and discovers topology
"""

import subprocess
import re
import socket
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

import paramiko

from app.db.connection import get_connection


@dataclass
class NetworkInterface:
    name: str  # em0, em1, ens33, em3.20 (VLAN)
    ip_address: str
    subnet_mask: str = "255.255.255.0"
    interface_type: str = "UNKNOWN"  # WAN, LAN, OPT1, VLAN, etc.
    is_dhcp_enabled: bool = False
    subnet_cidr: str = ""
    parent_interface: Optional[str] = None  # For VLANs: em3
    vlan_id: Optional[int] = None  # For VLANs: 20
    
    def __post_init__(self):
        if self.ip_address and not self.subnet_cidr:
            self.subnet_cidr = self._calculate_cidr()
    
    def _calculate_cidr(self) -> str:
        """Calculate CIDR from IP and mask"""
        try:
            ip_parts = self.ip_address.split('.')
            mask_parts = self.subnet_mask.split('.')
            network = '.'.join(str(int(ip_parts[i]) & int(mask_parts[i])) for i in range(4))
            bits = sum(bin(int(x)).count('1') for x in mask_parts)
            return f"{network}/{bits}"
        except:
            return f"{self.ip_address}/24"


@dataclass
class LocalNetworkInfo:
    ip_address: str
    interface: str
    gateway: str
    is_dhcp: bool
    dns_servers: List[str]
    diagnostic_ip: Optional[str] = None
    diagnostic_interface: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)


class NetworkDiscovery:
    def __init__(self):
        self.local_info: Optional[LocalNetworkInfo] = None
        self.firewall_interfaces: List[NetworkInterface] = []
        self.vlan_interfaces: List[NetworkInterface] = []
        self.errors: List[str] = []
        
    def discover_local_network(self) -> Tuple[bool, str]:
        """
        Discover local PC network configuration
        Returns: (success, message)
        """
        try:
            # Get IP and Gateway
            result = subprocess.run(
                ['ip', 'route', 'get', '1.1.1.1'],
                capture_output=True, text=True, timeout=5
            )
            
            ip_address = None
            interface = None
            gateway = None
            
            for line in result.stdout.split('\n'):
                if 'src' in line:
                    match = re.search(r'src\s+(\d+\.\d+\.\d+\.\d+)', line)
                    if match:
                        ip_address = match.group(1)
                    match = re.search(r'dev\s+(\S+)', line)
                    if match:
                        interface = match.group(1)
            
            # Get default gateway
            result = subprocess.run(
                ['ip', 'route'], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split('\n'):
                if 'default via' in line:
                    match = re.search(r'default via\s+(\d+\.\d+\.\d+\.\d+)', line)
                    if match:
                        gateway = match.group(1)
                        break
            
            if not gateway:
                return False, "NO_GATEWAY"
            
            if not ip_address:
                return False, "NO_IP_ADDRESS"
            
            # Check if DHCP or Static
            is_dhcp = self._check_dhcp_status(interface)
            
            # Get DNS
            dns_servers = self._get_dns_servers()
            
            self.local_info = LocalNetworkInfo(
                ip_address=ip_address,
                interface=interface,
                gateway=gateway,
                is_dhcp=is_dhcp,
                dns_servers=dns_servers
            )
            
            return True, "SUCCESS"
            
        except Exception as e:
            self.errors.append(f"Local discovery error: {str(e)}")
            return False, f"ERROR: {str(e)}"
    
    def discover_all_local_interfaces(self) -> Tuple[bool, str]:
        """
        Discover ALL local interfaces, not just the default gateway one.
        This finds the diagnostic interface (ens38) even if it's not the default route.
        """
        try:
            if not self.local_info:
                return False, "Local info not discovered yet"
            
            # Get all interfaces with their IPs
            result = subprocess.run(
                ['ip', '-o', 'addr', 'show'], capture_output=True, text=True, timeout=5
            )
            
            management_iface = self.local_info.interface
            management_ip = self.local_info.ip_address
            
            # Extract subnet prefixes
            mgmt_subnet = '.'.join(management_ip.split('.')[:3])  # e.g., 192.168.10
            
            # Look for other interfaces in different subnets
            for line in result.stdout.split('\n'):
                # Parse: 2: ens33 inet 192.168.10.112/24 brd 192.168.10.255 scope global dynamic ens33
                match = re.search(r'\d+:\s+(\w+)\s+inet\s+(\d+\.\d+\.\d+\.\d+)/\d+', line)
                if match:
                    iface = match.group(1)
                    ip = match.group(2)
                    
                    # Skip loopback
                    if iface == 'lo':
                        continue
                    
                    # Skip the management interface (already recorded)
                    if iface == management_iface:
                        continue
                    
                    # Skip if same IP as management
                    if ip == management_ip:
                        continue
                    
                    # Check if this is a different subnet
                    ip_subnet = '.'.join(ip.split('.')[:3])
                    
                    # If different subnet, consider it as diagnostic interface
                    if ip_subnet != mgmt_subnet:
                        self.local_info.diagnostic_interface = iface
                        self.local_info.diagnostic_ip = ip
                        return True, f"Found diagnostic interface: {iface} ({ip}) in subnet {ip_subnet}"
            
            # If no separate diagnostic interface found, use management interface as diagnostic too
            self.local_info.diagnostic_interface = management_iface
            self.local_info.diagnostic_ip = management_ip
            
            return False, "No separate diagnostic interface found - using management interface"
            
        except Exception as e:
            return False, f"ERROR: {str(e)}"
    
    def _check_dhcp_status(self, interface: str) -> bool:
        """Check if interface uses DHCP"""
        try:
            result = subprocess.run(
                ['cat', f'/var/lib/dhcp/dhclient.{interface}.leases'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                return True
        except:
            pass
        
        try:
            result = subprocess.run(
                ['ip', 'addr', 'show', interface],
                capture_output=True, text=True, timeout=2
            )
            if 'dynamic' in result.stdout:
                return True
        except:
            pass
        
        return False
    
    def _get_dns_servers(self) -> List[str]:
        """Get DNS servers from resolv.conf"""
        dns = []
        try:
            with open('/etc/resolv.conf', 'r') as f:
                for line in f:
                    if line.startswith('nameserver'):
                        parts = line.split()
                        if len(parts) >= 2:
                            dns.append(parts[1])
        except:
            pass
        return dns
    
    def ping_test(self, host: str, timeout: int = 3) -> bool:
        """Test if host is reachable"""
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', str(timeout), host],
                capture_output=True, timeout=timeout + 2
            )
            return result.returncode == 0
        except:
            return False
    
    def discover_firewall_interfaces(
        self, 
        firewall_ip: str, 
        username: str, 
        password: str
    ) -> Tuple[bool, str]:
        """
        SSH to pfSense and discover all interfaces including VLANs
        """
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=firewall_ip,
                username=username,
                password=password,
                look_for_keys=False,
                allow_agent=False,
                timeout=10
            )
            
            # Get detailed interface configuration
            stdin, stdout, stderr = ssh.exec_command('ifconfig -a')
            ifconfig_output = stdout.read().decode()
            
            # Parse interfaces (including VLANs)
            self.firewall_interfaces, self.vlan_interfaces = self._parse_ifconfig_vlans(ifconfig_output)
            
            # Get DHCP server status
            self._check_dhcp_status_on_interfaces(ssh)
            
            ssh.close()
            
            if not self.firewall_interfaces:
                return False, "NO_INTERFACES_FOUND"
            
            return True, f"Found {len(self.firewall_interfaces)} interfaces, {len(self.vlan_interfaces)} VLANs"
            
        except paramiko.AuthenticationException:
            return False, "AUTH_FAILED"
        except paramiko.SSHException as e:
            return False, f"SSH_ERROR: {str(e)}"
        except Exception as e:
            self.errors.append(f"Firewall discovery error: {str(e)}")
            return False, f"ERROR: {str(e)}"
    
    def _parse_ifconfig_vlans(self, output: str) -> Tuple[List[NetworkInterface], List[NetworkInterface]]:
        """
        Parse ifconfig output to extract interfaces and VLANs
        Returns: (main_interfaces, vlan_interfaces)
        """
        main_interfaces = []
        vlan_interfaces = []
        
        # Split by interface blocks
        blocks = re.split(r'\n(?=\w+[\.\w]*:)', output)
        
        for block in blocks:
            lines = block.strip().split('\n')
            if not lines:
                continue
            
            # First line has interface name and flags
            first_line = lines[0]
            
            # Match interface names including VLANs: em0, em1, em3.20, em3.50
            iface_match = re.match(r'^([\w\.]+):', first_line)
            if not iface_match:
                continue
            
            iface_name = iface_match.group(1)
            
            # Skip loopback
            if iface_name == 'lo0' or iface_name == 'lo':
                continue
            
            # Check if it's a VLAN interface (contains dot)
            is_vlan = '.' in iface_name
            parent_iface = None
            vlan_id = None
            
            if is_vlan:
                parts = iface_name.split('.')
                parent_iface = parts[0]
                try:
                    vlan_id = int(parts[1])
                except:
                    pass
            
            # Find IP address and netmask
            ip_address = None
            subnet_mask = "255.255.255.0"
            
            for line in lines:
                # IPv4 address
                inet_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', line)
                if inet_match:
                    ip_address = inet_match.group(1)
                
                # Netmask (hex format)
                mask_match = re.search(r'netmask\s+(0x[0-9a-f]+)', line, re.I)
                if mask_match:
                    hex_mask = mask_match.group(1)
                    mask_int = int(hex_mask, 16)
                    subnet_mask = '.'.join(str((mask_int >> (8 * i)) & 0xFF) for i in [3, 2, 1, 0])
            
            # Skip interfaces without IP (unless they're parent of VLANs)
            if not ip_address and not is_vlan:
                continue
            
            # Determine type
            iface_type = self._classify_interface(iface_name, ip_address)
            
            interface = NetworkInterface(
                name=iface_name,
                ip_address=ip_address if ip_address else "",
                subnet_mask=subnet_mask,
                interface_type=iface_type,
                parent_interface=parent_iface,
                vlan_id=vlan_id
            )
            
            if is_vlan:
                vlan_interfaces.append(interface)
            else:
                main_interfaces.append(interface)
        
        # Link VLANs to their parent interfaces
        parent_map = {iface.name: iface for iface in main_interfaces}
        for vlan in vlan_interfaces:
            if vlan.parent_interface in parent_map:
                parent = parent_map[vlan.parent_interface]
                # Inherit type from parent if not set
                if vlan.interface_type == "UNKNOWN" and parent.interface_type != "UNKNOWN":
                    vlan.interface_type = f"{parent.interface_type}_VLAN"
        
        return main_interfaces, vlan_interfaces
    
    def _classify_interface(self, name: str, ip: str) -> str:
        """Classify interface as WAN, LAN, OPT1, VLAN, etc."""
        name_lower = name.lower()
        
        # VLAN interfaces
        if '.' in name_lower:
            base_name = name_lower.split('.')[0]
            if 'wan' in base_name or base_name == 'em0':
                return 'WAN_VLAN'
            elif 'lan' in base_name or base_name == 'em1':
                return 'LAN_VLAN'
            elif 'opt1' in base_name or base_name == 'em2':
                return 'OPT1_VLAN'
            elif 'opt2' in base_name or base_name == 'em3':
                return 'OPT2_VLAN'
            elif 'mgmt' in base_name:
                return 'MGMT_VLAN'
            elif 'data' in base_name:
                return 'DATA_VLAN'
            else:
                return 'VLAN'
        
        # Main interfaces
        if 'wan' in name_lower or name_lower == 'em0':
            return 'WAN'
        elif 'lan' in name_lower or name_lower == 'em1':
            return 'LAN'
        elif 'opt1' in name_lower or name_lower == 'em2':
            return 'OPT1'
        elif 'opt2' in name_lower or name_lower == 'em3':
            return 'OPT2'
        elif ip and ip.startswith('127.'):
            return 'LOOPBACK'
        else:
            return 'UNKNOWN'
    
    def _check_dhcp_status_on_interfaces(self, ssh):
        """Check which interfaces have DHCP server enabled"""
        try:
            stdin, stdout, stderr = ssh.exec_command('cat /var/dhcpd/var/db/dhcpd.leases | head -5')
            dhcpd_running = len(stdout.read().decode().strip()) > 0
            
            for iface in self.firewall_interfaces:
                if iface.interface_type in ['LAN', 'OPT1', 'OPT2', 'MGMT', 'DATA']:
                    iface.is_dhcp_enabled = dhcpd_running
            
            # Also mark VLANs if parent has DHCP
            for vlan in self.vlan_interfaces:
                if 'LAN' in vlan.interface_type or 'OPT' in vlan.interface_type or 'MGMT' in vlan.interface_type or 'DATA' in vlan.interface_type:
                    vlan.is_dhcp_enabled = dhcpd_running
        except:
            pass
    
    def validate_pc_in_firewall(self, firewall_ip: str, username: str, password: str) -> Tuple[bool, str]:
        """Check if Master PC IP appears in firewall DHCP leases"""
        if not self.local_info:
            return False, "Local info not discovered"
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=firewall_ip,
                username=username,
                password=password,
                look_for_keys=False,
                allow_agent=False,
                timeout=10
            )
            
            stdin, stdout, stderr = ssh.exec_command(
                'cat /var/dhcpd/var/db/dhcpd.leases'
            )
            leases_output = stdout.read().decode()
            ssh.close()
            
            # Check both management and diagnostic IPs
            ips_to_check = [self.local_info.ip_address]
            if self.local_info.diagnostic_ip:
                ips_to_check.append(self.local_info.diagnostic_ip)
            
            found_ips = []
            for pc_ip in ips_to_check:
                ip_pattern = rf'lease\s+{re.escape(pc_ip)}\s+{{'
                if re.search(ip_pattern, leases_output):
                    found_ips.append(pc_ip)
            
            if found_ips:
                return True, f"PC found in DHCP leases: {', '.join(found_ips)}"
            else:
                return False, "PC not found in DHCP leases (Static IP suspected)"
                
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def test_switch_connectivity(
        self, 
        switch_ip: str, 
        username: str, 
        password: str,
        sudo_password: Optional[str] = None
    ) -> Tuple[bool, str, dict]:
        """
        Test SSH connectivity to switch and detect type
        Returns: (success, switch_type, details)
        """
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=switch_ip,
                username=username,
                password=password,
                look_for_keys=False,
                allow_agent=False,
                timeout=10
            )
            
            # Try Open vSwitch command with sudo
            if sudo_password:
                # Use sudo with password
                stdin, stdout, stderr = ssh.exec_command(f'echo "{sudo_password}" | sudo -S ovs-vsctl show')
            else:
                stdin, stdout, stderr = ssh.exec_command('sudo ovs-vsctl show')
            
            ovs_output = stdout.read().decode()
            ovs_error = stderr.read().decode()
            
            if ovs_output and 'Bridge' in ovs_output:
                bridge_name = self._parse_ovs_bridge(ovs_output)
                ssh.close()
                return True, "Open vSwitch", {
                    "bridge": bridge_name,
                    "raw_output": ovs_output[:500]
                }
            
            # If sudo failed, try without sudo (maybe already root)
            if "password" in ovs_error.lower() or "sorry" in ovs_error.lower():
                stdin, stdout, stderr = ssh.exec_command('ovs-vsctl show')
                ovs_output = stdout.read().decode()
                
                if ovs_output and 'Bridge' in ovs_output:
                    bridge_name = self._parse_ovs_bridge(ovs_output)
                    ssh.close()
                    return True, "Open vSwitch", {
                        "bridge": bridge_name,
                        "raw_output": ovs_output[:500]
                    }
            
            # Try Cisco-style command
            stdin, stdout, stderr = ssh.exec_command('show version')
            version_output = stdout.read().decode()
            
            if 'Cisco' in version_output or 'IOS' in version_output:
                ssh.close()
                return True, "Cisco", {"version": version_output[:200]}
            
            # Generic Linux bridge
            stdin, stdout, stderr = ssh.exec_command('brctl show')
            brctl_output = stdout.read().decode()
            
            if brctl_output and 'bridge' in brctl_output:
                ssh.close()
                return True, "Linux Bridge", {"output": brctl_output[:200]}
            
            ssh.close()
            return True, "Unknown", {}
            
        except paramiko.AuthenticationException:
            return False, "AUTH_FAILED", {}
        except Exception as e:
            return False, f"ERROR: {str(e)}", {}
    
    def _parse_ovs_bridge(self, output: str) -> str:
        """Extract bridge name from ovs-vsctl show output"""
        match = re.search(r'Bridge\s+"?(\w+)"?', output)
        return match.group(1) if match else "unknown"
    
    def save_to_database(self, sudo_password: Optional[str] = None) -> bool:
        """Save discovered configuration to database"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Clear old data
            cur.execute("DELETE FROM managed_switches")
            cur.execute("DELETE FROM firewall_interfaces")
            cur.execute("DELETE FROM network_setup")
            
            # Save network setup
            if self.local_info:
                cur.execute("""
                    INSERT INTO network_setup 
                    (setup_completed, master_pc_ip, master_pc_interface, gateway_ip,
                     diagnostic_interface, diagnostic_ip, switch_sudo_password, setup_timestamp)
                    VALUES (TRUE, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    RETURNING id
                """, (
                    self.local_info.ip_address,
                    self.local_info.interface,
                    self.local_info.gateway,
                    self.local_info.diagnostic_interface,
                    self.local_info.diagnostic_ip,
                    sudo_password
                ))
                setup_id = cur.fetchone()[0]
                print(f"Saved network setup with ID: {setup_id}")
            
            # Save ALL interfaces (including VLANs) to firewall_interfaces
            interface_id_map = {}
            
            # Save main interfaces first
            for iface in self.firewall_interfaces:
                cur.execute("""
                    INSERT INTO firewall_interfaces 
                    (interface_name, interface_type, ip_address, subnet_mask, 
                     is_dhcp_enabled, subnet_cidr, parent_interface, vlan_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    iface.name,
                    iface.interface_type,
                    iface.ip_address,
                    iface.subnet_mask,
                    iface.is_dhcp_enabled,
                    iface.subnet_cidr,
                    None,  # No parent for main interfaces
                    None   # No VLAN ID for main interfaces
                ))
                iface_id = cur.fetchone()[0]
                interface_id_map[iface.name] = iface_id
                interface_id_map[iface.interface_type] = iface_id
                print(f"Saved interface {iface.name} ({iface.interface_type}) with ID: {iface_id}")
            
            # Save VLAN interfaces (also to firewall_interfaces)
            for vlan in self.vlan_interfaces:
                cur.execute("""
                    INSERT INTO firewall_interfaces 
                    (interface_name, interface_type, ip_address, subnet_mask, 
                     is_dhcp_enabled, subnet_cidr, parent_interface, vlan_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    vlan.name,
                    vlan.interface_type,
                    vlan.ip_address,
                    vlan.subnet_mask,
                    vlan.is_dhcp_enabled,
                    vlan.subnet_cidr,
                    vlan.parent_interface,
                    vlan.vlan_id
                ))
                vlan_id = cur.fetchone()[0]
                interface_id_map[vlan.name] = vlan_id
                interface_id_map[vlan.interface_type] = vlan_id
                print(f"Saved VLAN {vlan.name} ({vlan.interface_type}) with ID: {vlan_id} (parent: {vlan.parent_interface})")
            
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"Database save complete: {len(self.firewall_interfaces) + len(self.vlan_interfaces)} total interfaces")
            return True
            
        except Exception as e:
            self.errors.append(f"Database save error: {str(e)}")
            print(f"ERROR saving to database: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_from_database(self) -> bool:
        """Load configuration from database"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Load network setup
            cur.execute("""
                SELECT setup_completed, master_pc_ip, master_pc_interface, gateway_ip,
                       diagnostic_interface, diagnostic_ip
                FROM network_setup 
                ORDER BY setup_timestamp DESC
                LIMIT 1
            """)
            setup_row = cur.fetchone()
            
            if not setup_row or not setup_row[0]:
                print("No completed network setup found")
                return False
            
            self.local_info = LocalNetworkInfo(
                ip_address=setup_row[1],
                interface=setup_row[2],
                gateway=setup_row[3],
                is_dhcp=False,
                dns_servers=[],
                diagnostic_interface=setup_row[4],
                diagnostic_ip=setup_row[5]
            )
            
            # Load ALL interfaces from firewall_interfaces
            cur.execute("""
                SELECT interface_name, interface_type, ip_address, subnet_mask, 
                       is_dhcp_enabled, subnet_cidr, parent_interface, vlan_id, id
                FROM firewall_interfaces
                ORDER BY 
                    CASE 
                        WHEN parent_interface IS NULL THEN 0 
                        ELSE 1 
                    END,
                    interface_name
            """)
            rows = cur.fetchall()
            
            self.firewall_interfaces = []
            self.vlan_interfaces = []
            
            for row in rows:
                iface = NetworkInterface(
                    name=row[0],
                    interface_type=row[1],
                    ip_address=row[2] if row[2] else "",
                    subnet_mask=row[3] if row[3] else "255.255.255.0",
                    is_dhcp_enabled=row[4],
                    subnet_cidr=row[5] if row[5] else "",
                    parent_interface=row[6],
                    vlan_id=row[7]
                )
                
                # Separate main interfaces and VLANs
                if iface.vlan_id is not None or (iface.parent_interface is not None):
                    self.vlan_interfaces.append(iface)
                else:
                    self.firewall_interfaces.append(iface)
            
            cur.close()
            conn.close()
            
            print(f"Loaded {len(self.firewall_interfaces)} main interfaces and {len(self.vlan_interfaces)} VLANs")
            return True
            
        except Exception as e:
            self.errors.append(f"Database load error: {str(e)}")
            print(f"ERROR loading from database: {str(e)}")
            return False
    
    def is_setup_complete(self) -> bool:
        """Check if network setup is already done"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT setup_completed FROM network_setup ORDER BY setup_timestamp DESC LIMIT 1")
            row = cur.fetchone()
            cur.close()
            conn.close()
            return row is not None and row[0] is True
        except Exception as e:
            print(f"Error checking setup completion: {str(e)}")
            return False


# Singleton instance
network_discovery = NetworkDiscovery()
