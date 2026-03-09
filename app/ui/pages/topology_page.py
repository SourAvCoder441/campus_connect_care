# app/ui/pages/topology_page.py (PROPER TD4.PY INTEGRATION)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, 
    QFrame, QHBoxLayout, QGraphicsDropShadowEffect,
    QTreeWidget, QTreeWidgetItem, QSplitter,
    QTextEdit, QMessageBox, QProgressBar,
    QTabWidget, QHeaderView
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor, QTextCursor
import time
from datetime import datetime
from collections import defaultdict
import subprocess
import paramiko
import re
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.db.connection import get_connection
from app.core.diagnostics.detector_manager import DetectorManager

# Try to import session management with fallback
try:
    from app.session.session import get_current_user
except ImportError:
    def get_current_user():
        return {'id': 1, 'username': 'admin', 'role': 'NetworkAdmin'}


class TopologyDiscoveryWorker(QThread):
    """Background worker for topology discovery - Based on td4.py"""
    log = Signal(str)
    progress = Signal(int)
    status = Signal(str)
    finished_signal = Signal(dict)
    
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.manager = None
        self.start_time = None
        self.health_warning = False
        self.critical_faults_list = []
        
        # Configuration from td4.py
        self.PFSENSE_IP = "192.168.10.1"
        self.PFSENSE_USER = "admin"
        self.PFSENSE_PASS = "pfsense"
        
        self.OVS_IP = "192.168.10.2"
        self.OVS_USER = "sourav"
        self.OVS_PASS = "exam"
        self.OVS_BRIDGE = "br0"
        
        self.BLOCKED_DEVICES = ["gns3vm", "LAPTOP-AEVCKH57"]
        
        self.PORT_TO_INTERFACE = {
            "1": "ens33",
            "2": "ens40", 
            "4": "ens37",
            "5": "ens38",
            "6": "ens39"
        }
        
        self.PING_TIMEOUT = 2
        self.PING_RETRIES = 2
        self.RETRY_DELAY = 0.5
        self.MAX_PING_THREADS = 15
        
        self.CLEAR_ARP_CACHE = True
        self.CLEAR_MAC_TABLE = True
        self.WAIT_AFTER_CLEAR = 2
        
    def ssh_exec(self, host, user, password, command, timeout=10):
        """Execute SSH command and return output"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=host,
                username=user,
                password=password,
                look_for_keys=False,
                allow_agent=False,
                timeout=timeout
            )
            _, stdout, _ = ssh.exec_command(command)
            output = stdout.read().decode()
            ssh.close()
            return output.strip()
        except Exception as e:
            self.log.emit(f"[SSH ERROR {host}] {e}")
            return ""
    
    def test_ssh_connection(self, host, user, password):
        """Test if SSH connection is possible"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=host,
                username=user,
                password=password,
                look_for_keys=False,
                allow_agent=False,
                timeout=5
            )
            ssh.close()
            return True
        except:
            return False
    
    def clear_firewall_arp_cache(self):
        """Clear firewall ARP cache for fresh evidence - from td4.py"""
        if not self.CLEAR_ARP_CACHE:
            self.log.emit("  Skipping ARP cache clear (disabled)")
            return False
        
        self.log.emit("  Clearing firewall ARP cache...")
        
        try:
            arp_output = self.ssh_exec(
                self.PFSENSE_IP, self.PFSENSE_USER, self.PFSENSE_PASS,
                "arp -an | grep -v 'incomplete' | awk '{print $2}' | tr -d '()'"
            )
            
            cleared_count = 0
            for ip in arp_output.split('\n'):
                if ip.strip() and not ip.startswith('192.168.99.1'):
                    self.ssh_exec(
                        self.PFSENSE_IP, self.PFSENSE_USER, self.PFSENSE_PASS,
                        f"arp -d {ip} 2>/dev/null || true"
                    )
                    cleared_count += 1
            
            self.log.emit(f"  Cleared {cleared_count} ARP entries")
            time.sleep(self.WAIT_AFTER_CLEAR)
            return True
            
        except Exception as e:
            self.log.emit(f"  Warning: Could not clear ARP cache: {e}")
            return False
    
    def clear_switch_mac_table(self):
        """Clear switch MAC table for fresh evidence - from td4.py"""
        if not self.CLEAR_MAC_TABLE:
            self.log.emit("  Skipping MAC table clear (disabled)")
            return False
        
        self.log.emit("  Clearing switch MAC table...")
        
        try:
            result = self.ssh_exec(
                self.OVS_IP, self.OVS_USER, self.OVS_PASS,
                f"sudo ovs-appctl fdb/flush {self.OVS_BRIDGE} 2>/dev/null"
            )
            
            if "fdb/flush" in result or not result:
                self.log.emit("  MAC table cleared successfully")
            else:
                self.log.emit(f"  MAC table clear result: {result}")
            
            time.sleep(self.WAIT_AFTER_CLEAR)
            return True
            
        except Exception as e:
            self.log.emit(f"  Warning: Could not clear MAC table: {e}")
            return False
    
    def get_fresh_arp_table(self):
        """Get fresh ARP table after clearing cache - from td4.py"""
        self.log.emit("  Getting fresh ARP table...")
        time.sleep(1)
        
        arp_output = self.ssh_exec(
            self.PFSENSE_IP, self.PFSENSE_USER, self.PFSENSE_PASS,
            "arp -an | awk '{print $2, $4}' | tr -d '()'"
        )
        
        arp_table = {}
        for line in arp_output.split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    ip = parts[0]
                    mac = parts[1].lower()
                    if mac != "(incomplete)":
                        arp_table[ip] = mac
        
        self.log.emit(f"  Fresh ARP table has {len(arp_table)} entries")
        return arp_table
    
    def get_fresh_mac_table(self):
        """Get fresh MAC table after clearing - from td4.py"""
        self.log.emit("  Getting fresh MAC table...")
        time.sleep(1)
        
        mac_table_output = self.ssh_exec(
            self.OVS_IP, self.OVS_USER, self.OVS_PASS,
            f"sudo ovs-appctl fdb/show {self.OVS_BRIDGE} 2>/dev/null"
        )
        
        mac_table = defaultdict(list)
        mac_to_port = {}
        
        for line in mac_table_output.splitlines():
            parts = line.split()
            if len(parts) >= 4 and re.match(r'^([0-9a-f]{2}:){5}[0-9a-f]{2}$', parts[2], re.I):
                port = parts[0]
                mac = parts[2].lower()
                
                mac_table[port].append(mac)
                mac_to_port[mac] = port
        
        self.log.emit(f"  Fresh MAC table has {len(mac_to_port)} entries")
        return mac_table, mac_to_port
    
    def parse_dhcp_leases(self):
        """Parse DHCP leases from firewall - from td4.py"""
        self.log.emit("Fetching DHCP leases...")
        
        raw_dhcp = self.ssh_exec(
            self.PFSENSE_IP, self.PFSENSE_USER, self.PFSENSE_PASS,
            "cat /var/dhcpd/var/db/dhcpd.leases 2>/dev/null"
        )
        
        if not raw_dhcp:
            self.log.emit("  ERROR: Could not fetch DHCP leases")
            return [], set()
        
        devices = []
        seen_macs = set()
        blocked_macs = set()
        
        for m in re.finditer(r"lease\s+([\d.]+)\s*\{([^}]+)\}", raw_dhcp, re.DOTALL):
            ip, block = m.group(1), m.group(2)
            
            mac_match = re.search(r"hardware\s+ethernet\s+([0-9a-f:]{17})", block, re.I)
            if not mac_match:
                continue
                
            mac = mac_match.group(1).lower()
            
            if mac in seen_macs:
                continue
            
            hostname = None
            for pattern in [r'client-hostname\s+"([^"]+)"', 
                           r'hostname\s+"([^"]+)"',
                           r'ddns-hostname\s+"([^"]+)"']:
                match = re.search(pattern, block, re.I)
                if match:
                    hostname = match.group(1).strip()
                    break
            
            should_block = False
            if hostname:
                for blocked in self.BLOCKED_DEVICES:
                    if blocked.lower() in hostname.lower():
                        should_block = True
                        blocked_macs.add(mac)
                        break
            
            if should_block:
                continue
                
            if not hostname:
                continue
            
            if hostname.startswith("dhcp-") or hostname == ip:
                hostname = f"PC-{mac[-6:].replace(':', '')}"
            
            device = {
                'name': hostname,
                'ip': ip,
                'mac': mac,
                'subnet': ".".join(ip.split('.')[:3]) + ".0/24"
            }
            
            devices.append(device)
            seen_macs.add(mac)
        
        self.log.emit(f"  Found {len(devices)} devices from DHCP")
        self.log.emit(f"  Blocked {len(blocked_macs)} infrastructure MACs")
        
        return devices, blocked_macs
    
    def ping_device(self, ip):
        """Ping a single device with timeout - from td4.py"""
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', str(self.PING_TIMEOUT), ip],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.PING_TIMEOUT + 1
            )
            return result.returncode == 0
        except:
            return False
    
    def enhanced_ping_device(self, ip):
        """Enhanced ping with retries - from td4.py"""
        for attempt in range(self.PING_RETRIES):
            success = self.ping_device(ip)
            if success:
                return True, attempt + 1
            if attempt < self.PING_RETRIES - 1:
                time.sleep(self.RETRY_DELAY)
        return False, self.PING_RETRIES
    
    def parallel_ping_devices(self, ip_list):
        """Ping multiple devices in parallel - from td4.py"""
        self.log.emit(f"  Pinging {len(ip_list)} devices with {self.PING_RETRIES} retries each...")
        
        ping_results = {}
        ping_attempts = {}
        
        with ThreadPoolExecutor(max_workers=self.MAX_PING_THREADS) as executor:
            future_to_ip = {executor.submit(self.enhanced_ping_device, ip): ip for ip in ip_list}
            
            for i, future in enumerate(as_completed(future_to_ip)):
                ip = future_to_ip[future]
                try:
                    success, attempts = future.result(timeout=(self.PING_TIMEOUT + 2) * self.PING_RETRIES)
                    ping_results[ip] = success
                    ping_attempts[ip] = attempts
                except:
                    ping_results[ip] = False
                    ping_attempts[ip] = self.PING_RETRIES
        
        success_count = sum(ping_results.values())
        self.log.emit(f"  Ping results: {success_count}/{len(ping_results)} devices responded")
        return ping_results, ping_attempts
    
    def run(self):
        self.start_time = time.time()
        
        try:
            self.manager = DetectorManager(self.user_id)
            session_id = self.manager.create_session('topology', None)
            
            self.log.emit("=" * 60)
            self.log.emit("NETWORK TOPOLOGY DISCOVERY (td4.py Engine)")
            self.log.emit("=" * 60)
            
            # Step 1: Check network health first
            self.status.emit("Checking network health...")
            self.log.emit("\n[1/6] Running pre-discovery health check...")
            
            health_results = self.manager.run_detectors(['device_discovery', 'ip_conflict'])
            
            # Store critical faults for display
            self.critical_faults_list = [f for f in health_results if hasattr(f, 'severity') and f.severity in ['critical', 'high']]
            
            if self.critical_faults_list:
                self.log.emit(f"\n⚠️ WARNING: Found {len(self.critical_faults_list)} critical/high severity issues")
                self.log.emit("Topology data may be unreliable until these are resolved:")
                for i, fault in enumerate(self.critical_faults_list[:5]):
                    fault_desc = getattr(fault, 'description', 'Unknown issue')
                    self.log.emit(f"  {i+1}. {fault_desc[:100]}")
                self.health_warning = True
            else:
                self.log.emit("  ✓ Network health check passed")
                self.health_warning = False
            
            self.progress.emit(15)
            
            # Step 2: Clear caches for fresh data (from td4.py)
            self.status.emit("Clearing network caches...")
            self.log.emit("\n[2/6] Clearing ARP and MAC caches for fresh data...")
            self.clear_firewall_arp_cache()
            self.clear_switch_mac_table()
            self.progress.emit(30)
            
            # Step 3: Get fresh ARP and MAC tables
            self.status.emit("Collecting fresh network tables...")
            self.log.emit("\n[3/6] Collecting fresh ARP and MAC tables...")
            fresh_arp = self.get_fresh_arp_table()
            fresh_mac_table, fresh_mac_to_port = self.get_fresh_mac_table()
            self.progress.emit(45)
            
            # Step 4: Get DHCP leases and ping devices
            self.status.emit("Discovering devices...")
            self.log.emit("\n[4/6] Discovering devices from DHCP...")
            dhcp_devices, blocked_macs = self.parse_dhcp_leases()
            
            # Ping all discovered devices
            if dhcp_devices:
                ips_to_ping = [d['ip'] for d in dhcp_devices]
                ping_results, ping_attempts = self.parallel_ping_devices(ips_to_ping)
                
                # Get post-ping MAC table
                self.log.emit("\n  Getting post-ping MAC table...")
                time.sleep(2)
                post_ping_mac_table, post_ping_mac_to_port = self.get_fresh_mac_table()
            else:
                ping_results = {}
                ping_attempts = {}
                post_ping_mac_table, post_ping_mac_to_port = {}, {}
            
            self.progress.emit(60)
            
            # Step 5: Build connection map
            self.status.emit("Mapping connections...")
            self.log.emit("\n[5/6] Building connection topology...")
            
            connections = []
            devices_with_ports = []
            
            # Use post-ping MAC table for most accurate results
            final_mac_to_port = post_ping_mac_to_port if post_ping_mac_to_port else fresh_mac_to_port
            
            for device in dhcp_devices:
                mac = device['mac']
                ip = device['ip']
                responds = ping_results.get(ip, False)
                
                device_info = {
                    'hostname': device['name'],
                    'ip': ip,
                    'mac': mac,
                    'status': 'active' if responds else 'powered_off',
                    'switch_port': final_mac_to_port.get(mac, 'N/A'),
                    'switch_ip': self.OVS_IP if mac in final_mac_to_port else None,
                    'responds': responds
                }
                devices_with_ports.append(device_info)
                
                if mac in final_mac_to_port:
                    port = final_mac_to_port[mac]
                    connections.append({
                        'device': device['name'],
                        'port': port,
                        'mac': mac
                    })
                    self.log.emit(f"  {device['name']} → Port {port}")
            
            # Detect unmanaged switches (ports with multiple devices)
            port_device_count = defaultdict(list)
            for conn in connections:
                port_device_count[conn['port']].append(conn['device'])
            
            unmanaged_switches = []
            for port, devices in port_device_count.items():
                if len(devices) >= 2:
                    unmanaged_switches.append({
                        'port': port,
                        'devices': devices,
                        'count': len(devices)
                    })
                    self.log.emit(f"  ⚡ Unmanaged switch detected on Port {port} with {len(devices)} devices")
            
            self.progress.emit(80)
            
            # Step 6: Analyze topology type
            self.status.emit("Analyzing topology...")
            self.log.emit("\n[6/6] Determining topology type...")
            
            # Calculate topology type based on patterns
            total_ports = len(port_device_count)
            ports_with_multiple = len(unmanaged_switches)
            
            if ports_with_multiple == 1 and total_ports > 1:
                topology_type = "STAR"
                reason = "One central switch with multiple devices"
            elif ports_with_multiple >= 2:
                topology_type = "TREE"
                reason = f"Multiple switches/hubs detected ({ports_with_multiple} ports with multiple devices)"
            elif len(connections) <= 2:
                topology_type = "BUS"
                reason = "Linear connection pattern"
            else:
                topology_type = "HYBRID"
                reason = "Mixed connection patterns"
            
            self.log.emit(f"  → Topology Type: {topology_type}")
            self.log.emit(f"  → Reason: {reason}")
            self.log.emit(f"  → Total devices: {len(dhcp_devices)}")
            self.log.emit(f"  → Connected devices: {len(connections)}")
            self.log.emit(f"  → Unmanaged switches: {len(unmanaged_switches)}")
            
            self.progress.emit(100)
            
            # Save to database
            for device in devices_with_ports:
                self.save_device_to_db(session_id, device)
            
            elapsed = time.time() - self.start_time
            self.manager.complete_session(f"Topology discovered in {elapsed:.1f}s")
            
            results = {
                'session_id': session_id,
                'elapsed_time': elapsed,
                'health_warning': self.health_warning,
                'critical_faults': len(self.critical_faults_list),
                'critical_faults_list': self.critical_faults_list[:5],
                'topology_type': topology_type,
                'topology_reason': reason,
                'devices': devices_with_ports,
                'connections': connections,
                'unmanaged_switches': unmanaged_switches,
                'total_devices': len(devices_with_ports),
                'connected_devices': len(connections),
                'unmanaged_count': len(unmanaged_switches)
            }
            
            self.log.emit(f"\n{'='*60}")
            self.log.emit(f"✅ TOPOLOGY DISCOVERY COMPLETE in {elapsed:.1f} seconds")
            self.log.emit(f"   Topology Type: {topology_type}")
            self.log.emit(f"   Devices Found: {len(devices_with_ports)}")
            self.log.emit(f"   Connected: {len(connections)}")
            self.log.emit(f"{'='*60}")
            
            self.finished_signal.emit(results)
            
        except Exception as e:
            self.log.emit(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            self.finished_signal.emit({'error': str(e)})
    
    def save_device_to_db(self, session_id, device):
        """Save device to database"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO diagnostic_devices 
                (session_id, hostname, ip_address, mac_address, status, switch_port, switch_ip)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                session_id,
                device['hostname'],
                device['ip'],
                device['mac'],
                device['status'],
                device['switch_port'],
                device['switch_ip']
            ))
            
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error saving device: {e}")


class TopologyPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_session_id = None
        self.worker = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)

        # Control Panel
        control_card = self.create_control_panel()
        main_layout.addWidget(control_card)

        # Main Splitter
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #cbd5e1;
                height: 4px;
                margin: 2px 0;
            }
            QSplitter::handle:hover {
                background-color: #8b5cf6;
            }
        """)
        self.main_splitter.setHandleWidth(8)
        self.main_splitter.setChildrenCollapsible(False)

        # Top Section: Results Tabs
        self.tabs = self.create_tabs()
        self.main_splitter.addWidget(self.tabs)

        # Bottom Section: Details Panel
        self.details_frame = self.create_details_panel()
        self.main_splitter.addWidget(self.details_frame)
        
        self.main_splitter.setSizes([700, 300])

        main_layout.addWidget(self.main_splitter, stretch=1)
        self.setLayout(main_layout)

    def create_control_panel(self):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(15, 23, 42, 25))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("◈ NETWORK TOPOLOGY DISCOVERY")
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        header.setStyleSheet("color: #0f172a;")
        layout.addWidget(header)

        # Info message
        info = QLabel(
            "This tool discovers network topology by analyzing:\n"
            "• DHCP leases and ARP tables from firewall\n"
            "• MAC address tables from managed switches\n"
            "• Device connectivity and port mappings\n"
            "• Unmanaged switch detection\n\n"
            "⚠️ Note: Run Full Diagnosis first if you suspect network issues."
        )
        info.setFont(QFont("Segoe UI", 11))
        info.setStyleSheet("color: #475569; background-color: #f8fafc; padding: 15px; border-radius: 8px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.discover_btn = QPushButton("▶ DISCOVER TOPOLOGY")
        self.discover_btn.setFixedHeight(50)
        self.discover_btn.setCursor(Qt.PointingHandCursor)
        self.discover_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8b5cf6, stop:1 #7c3aed);
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c3aed, stop:1 #6d28d9);
            }
            QPushButton:disabled {
                background-color: #cbd5e1;
                color: #64748b;
            }
        """)
        self.discover_btn.clicked.connect(self.run_discovery)
        btn_layout.addWidget(self.discover_btn)

        self.clear_btn = QPushButton("CLEAR")
        self.clear_btn.setFixedHeight(50)
        self.clear_btn.setFixedWidth(150)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748b;
                font-size: 13px;
                font-weight: bold;
                border: 2px solid #cbd5e1;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
                border-color: #94a3b8;
                color: #475569;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_results)
        btn_layout.addWidget(self.clear_btn)

        layout.addLayout(btn_layout)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #e2e8f0;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #8b5cf6;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #64748b; font-family: Consolas; font-size: 12px;")
        layout.addWidget(self.status_label)

        return card

    def create_tabs(self):
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                background: white;
            }
            QTabBar::tab {
                background: #f1f5f9;
                padding: 12px 25px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 3px solid #8b5cf6;
                color: #8b5cf6;
            }
        """)

        # Console Tab
        console_widget = QWidget()
        console_layout = QVBoxLayout(console_widget)
        console_layout.setContentsMargins(0, 0, 0, 0)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 11))
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        console_layout.addWidget(self.console)

        tabs.addTab(console_widget, "📟 CONSOLE")

        # Topology Summary Tab
        summary_widget = QWidget()
        summary_layout = QVBoxLayout(summary_widget)
        summary_layout.setContentsMargins(0, 0, 0, 0)

        self.summary_tree = QTreeWidget()
        self.summary_tree.setHeaderLabels(["Category", "Value", "Details"])
        self.summary_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                background: white;
                font-size: 12px;
                alternate-background-color: #f8fafc;
            }
            QTreeWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f1f5f9;
            }
            QTreeWidget::item:selected {
                background-color: #8b5cf6;
                color: white;
            }
            QHeaderView::section {
                background-color: #f1f5f9;
                padding: 8px;
                font-weight: bold;
            }
        """)
        self.summary_tree.setAlternatingRowColors(True)
        self.summary_tree.setColumnWidth(0, 250)
        self.summary_tree.setColumnWidth(1, 150)
        self.summary_tree.header().setStretchLastSection(True)
        self.summary_tree.itemClicked.connect(self.on_summary_item_clicked)
        summary_layout.addWidget(self.summary_tree)

        tabs.addTab(summary_widget, "📊 TOPOLOGY SUMMARY")

        # Connections Tab
        connections_widget = QWidget()
        connections_layout = QVBoxLayout(connections_widget)
        connections_layout.setContentsMargins(0, 0, 0, 0)

        self.connections_tree = QTreeWidget()
        self.connections_tree.setHeaderLabels(["Device", "IP Address", "MAC Address", "Connected To", "Port", "Status"])
        self.connections_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                background: white;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f1f5f9;
            }
            QTreeWidget::item:selected {
                background-color: #8b5cf6;
                color: white;
            }
            QHeaderView::section {
                background-color: #f1f5f9;
                padding: 8px;
                font-weight: bold;
            }
        """)
        self.connections_tree.setColumnWidth(0, 180)
        self.connections_tree.setColumnWidth(1, 120)
        self.connections_tree.setColumnWidth(2, 150)
        self.connections_tree.setColumnWidth(3, 150)
        self.connections_tree.setColumnWidth(4, 80)
        self.connections_tree.setColumnWidth(5, 100)
        self.connections_tree.itemClicked.connect(self.on_device_selected)
        connections_layout.addWidget(self.connections_tree)

        tabs.addTab(connections_widget, "🔌 CONNECTIONS")

        # Unmanaged Switches Tab
        switches_widget = QWidget()
        switches_layout = QVBoxLayout(switches_widget)
        switches_layout.setContentsMargins(0, 0, 0, 0)

        self.switches_tree = QTreeWidget()
        self.switches_tree.setHeaderLabels(["Switch Port", "Connected Devices", "Device Count"])
        self.switches_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                background: white;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f1f5f9;
            }
            QTreeWidget::item:selected {
                background-color: #8b5cf6;
                color: white;
            }
        """)
        self.switches_tree.setColumnWidth(0, 150)
        self.switches_tree.setColumnWidth(1, 300)
        self.switches_tree.header().setStretchLastSection(True)
        switches_layout.addWidget(self.switches_tree)

        tabs.addTab(switches_widget, "🔀 UNMANAGED SWITCHES")

        return tabs

    def create_details_panel(self):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 10, 15, 10)

        header = QLabel("📋 DETAILS")
        header.setFont(QFont("Segoe UI", 11, QFont.Bold))
        header.setStyleSheet("color: #0f172a;")
        layout.addWidget(header)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Consolas", 10))
        self.details_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.details_text)

        return frame

    def log_message(self, text, error=False):
        """Add text to console with proper cursor handling"""
        if error:
            self.console.append(f"<span style='color: #ef4444;'>❌ {text}</span>")
        elif "✓" in text or "✅" in text:
            self.console.append(f"<span style='color: #10b981;'>{text}</span>")
        elif "⚠️" in text:
            self.console.append(f"<span style='color: #f59e0b;'>{text}</span>")
        elif "▶" in text or "=" in text:
            self.console.append(f"<span style='color: #8b5cf6; font-weight: bold;'>{text}</span>")
        else:
            self.console.append(f"<span style='color: #e2e8f0;'>{text}</span>")
        
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.console.setTextCursor(cursor)
        self.console.ensureCursorVisible()

    def run_discovery(self):
        """Start topology discovery"""
        reply = QMessageBox.question(
            self, 
            "Confirm Discovery",
            "For accurate topology discovery, the network should be healthy.\n\n"
            "Have you run Full Diagnosis and resolved any critical issues?\n\n"
            "Select Yes to continue, or No to go to Diagnostics page.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.No:
            parent = self.parent()
            while parent and not hasattr(parent, 'navigate_to'):
                parent = parent.parent()
            if parent and hasattr(parent, 'navigate_to'):
                parent.navigate_to("Network Diag")
            return
        
        self.discover_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting topology discovery...")
        
        # Clear previous results
        self.summary_tree.clear()
        self.connections_tree.clear()
        self.switches_tree.clear()
        self.details_text.clear()
        self.console.clear()
        
        self.log_message(f"\n{'='*60}")
        self.log_message("▶ STARTING TOPOLOGY DISCOVERY (td4.py Engine)")
        self.log_message(f"{'='*60}")
        self.log_message(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        user = get_current_user()
        
        self.worker = TopologyDiscoveryWorker(user.get('id', 1))
        self.worker.log.connect(self.log_message)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished_signal.connect(self.on_discovery_finished)
        self.worker.start()

    def on_discovery_finished(self, results):
        """Handle discovery completion"""
        self.discover_btn.setEnabled(True)
        self.status_label.setText("Ready")
        
        if 'error' in results:
            self.log_message(f"❌ DISCOVERY FAILED: {results['error']}", error=True)
            return
        
        self.current_session_id = results.get('session_id')
        
        # Show warning if network issues were found
        if results.get('health_warning'):
            self.log_message("\n⚠️ WARNING: Network issues detected during pre-check")
            self.log_message("   Topology data may be incomplete or inaccurate.\n")
        
        # Update UI
        self.update_summary(results)
        self.update_connections(results)
        self.update_switches(results)
        
        # Switch to summary tab
        self.tabs.setCurrentIndex(1)
        
        self.log_message(f"\n✅ Discovery completed in {results['elapsed_time']:.1f} seconds")

    def update_summary(self, results):
        """Update topology summary"""
        self.summary_tree.clear()
        
        # Topology Info
        topo_item = QTreeWidgetItem(["📌 TOPOLOGY INFORMATION", "", ""])
        topo_item.setFont(0, QFont("Segoe UI", 11, QFont.Bold))
        topo_item.setForeground(0, QColor(139, 92, 246))
        
        QTreeWidgetItem(topo_item, ["Topology Type", results.get('topology_type', 'Unknown'), results.get('topology_reason', '')])
        QTreeWidgetItem(topo_item, ["Session ID", str(results.get('session_id', 'N/A')), ""])
        QTreeWidgetItem(topo_item, ["Duration", f"{results.get('elapsed_time', 0):.1f} seconds", ""])
        
        self.summary_tree.addTopLevelItem(topo_item)
        
        # Device Statistics
        dev_item = QTreeWidgetItem(["💻 DEVICE STATISTICS", "", ""])
        dev_item.setFont(0, QFont("Segoe UI", 11, QFont.Bold))
        
        QTreeWidgetItem(dev_item, ["Total Devices", str(results.get('total_devices', 0)), ""])
        QTreeWidgetItem(dev_item, ["Connected to Switch", str(results.get('connected_devices', 0)), ""])
        QTreeWidgetItem(dev_item, ["Unmanaged Switches", str(results.get('unmanaged_count', 0)), ""])
        
        self.summary_tree.addTopLevelItem(dev_item)
        
        # Health Warning with details
        if results.get('health_warning'):
            warn_item = QTreeWidgetItem(["⚠️ HEALTH WARNING", "", ""])
            warn_item.setFont(0, QFont("Segoe UI", 11, QFont.Bold))
            warn_item.setForeground(0, QColor(245, 158, 11))
            
            QTreeWidgetItem(warn_item, ["Critical Faults", str(results.get('critical_faults', 0)), "May affect accuracy"])
            
            # Add individual faults as children
            fault_list = results.get('critical_faults_list', [])
            for fault in fault_list:
                fault_desc = getattr(fault, 'description', 'Unknown issue')[:100]
                fault_type = getattr(fault, 'fault_type', 'Unknown')
                fault_item = QTreeWidgetItem(["", fault_type, fault_desc])
                warn_item.addChild(fault_item)
            
            self.summary_tree.addTopLevelItem(warn_item)
        
        self.summary_tree.expandAll()

    def update_connections(self, results):
        """Update connections tree"""
        self.connections_tree.clear()
        
        devices = results.get('devices', [])
        if not devices:
            item = QTreeWidgetItem(["No devices discovered", "", "", "", "", ""])
            self.connections_tree.addTopLevelItem(item)
            return
        
        # Use a set to track unique devices (by MAC address)
        seen_macs = set()
        unique_devices = []
        
        for device in devices:
            mac = device.get('mac', '')
            if mac not in seen_macs:
                seen_macs.add(mac)
                unique_devices.append(device)
        
        for device in unique_devices:
            hostname = device.get('hostname', 'Unknown')
            ip = device.get('ip', 'N/A')
            mac = device.get('mac', 'N/A')
            status = device.get('status', 'unknown')
            switch_port = device.get('switch_port', 'N/A')
            switch_ip = device.get('switch_ip', 'N/A')
            
            if switch_port != 'N/A':
                connected_to = f"Switch ({switch_ip})"
                port_display = switch_port
            else:
                connected_to = "Not connected"
                port_display = "—"
            
            item = QTreeWidgetItem([hostname, ip, mac, connected_to, port_display, status.upper()])
            
            # Color status
            if status == 'active':
                item.setForeground(5, QColor(16, 185, 129))
            elif status == 'powered_off':
                item.setForeground(5, QColor(239, 68, 68))
            
            item.setData(0, Qt.UserRole, device)
            self.connections_tree.addTopLevelItem(item)

    def update_switches(self, results):
        """Update unmanaged switches tree"""
        self.switches_tree.clear()
        
        unmanaged = results.get('unmanaged_switches', [])
        if not unmanaged:
            item = QTreeWidgetItem(["No unmanaged switches detected", "", ""])
            self.switches_tree.addTopLevelItem(item)
            return
        
        for switch in unmanaged:
            port = switch.get('port', 'Unknown')
            devices = switch.get('devices', [])
            count = switch.get('count', 0)
            
            item = QTreeWidgetItem([f"Port {port}", ", ".join(devices[:3]), str(count)])
            if count > 2:
                item.setForeground(0, QColor(245, 158, 11))
            
            self.switches_tree.addTopLevelItem(item)

    def on_summary_item_clicked(self, item, column):
        """Handle summary item clicks"""
        if item.childCount() == 0 and item.parent():
            text = f"Selected: {item.text(0)}\n"
            text += f"Value: {item.text(1)}\n"
            if item.text(2):
                text += f"Details: {item.text(2)}"
            self.details_text.setText(text)

    def on_device_selected(self, item, column):
        """Show device details"""
        device = item.data(0, Qt.UserRole)
        if not device:
            return
        
        text = f"💻 DEVICE DETAILS\n"
        text += "="*50 + "\n\n"
        text += f"Hostname: {device.get('hostname', 'Unknown')}\n"
        text += f"IP Address: {device.get('ip', 'N/A')}\n"
        text += f"MAC Address: {device.get('mac', 'N/A')}\n"
        text += f"Status: {device.get('status', 'unknown').upper()}\n"
        
        switch_port = device.get('switch_port', 'N/A')
        if switch_port != 'N/A':
            text += f"\n🔌 CONNECTION INFO:\n"
            text += f"Connected to: Switch ({device.get('switch_ip', 'N/A')})\n"
            text += f"Switch Port: {switch_port}\n"
            text += f"Responds to Ping: {'Yes' if device.get('responds', False) else 'No'}\n"
        else:
            text += f"\n🔌 Not connected to any switch\n"
        
        self.details_text.setText(text)

    def clear_results(self):
        """Clear all results"""
        self.console.clear()
        self.summary_tree.clear()
        self.connections_tree.clear()
        self.switches_tree.clear()
        self.details_text.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")
        self.log_message("Console cleared. Ready for new discovery.")
