from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
    QFrame, QGridLayout, QGraphicsDropShadowEffect,
    QPushButton, QMessageBox, QScrollArea, QTreeWidget, QTreeWidgetItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from collections import defaultdict

from app.core.network_discovery import network_discovery


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.network_discovery = network_discovery
        self.init_ui()
        self.load_network_config()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)
        
        # Header with Edit button
        header = QFrame()
        header.setStyleSheet("""
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
        header.setGraphicsEffect(shadow)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(25, 20, 25, 20)
        
        title = QLabel("◈ NETWORK TOPOLOGY CONFIGURATION")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #0f172a; letter-spacing: 1px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        edit_btn = QPushButton("EDIT CONFIGURATION")
        edit_btn.setFixedHeight(40)
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #0ea5e9;
                color: white;
                font-size: 12px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #0284c7;
            }
        """)
        edit_btn.clicked.connect(self.edit_configuration)
        header_layout.addWidget(edit_btn)
        
        main_layout.addWidget(header)
        
        # Content Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(15)
        
        scroll.setWidget(self.content_widget)
        main_layout.addWidget(scroll, stretch=1)
        
        self.setLayout(main_layout)
    
    def load_network_config(self):
        """Load and display network configuration from database"""
        # Clear existing
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Force reload from database
        print("Loading network config from database...")
        success = self.network_discovery.load_from_database()
        
        if not success:
            print("Failed to load from database")
            self.show_setup_required()
            return
        
        # Double-check that we have valid data
        if not self.network_discovery.local_info:
            print("No local info found in loaded data")
            self.show_setup_required()
            return
        
        print(f"Dashboard loading: {len(self.network_discovery.firewall_interfaces)} interfaces, {len(self.network_discovery.vlan_interfaces)} VLANs")
        print(f"Main interfaces: {[iface.name for iface in self.network_discovery.firewall_interfaces]}")
        print(f"VLANs: {[vlan.name for vlan in self.network_discovery.vlan_interfaces]}")
        
        # Display Master PC Info - show BOTH interfaces
        self.add_section_header("MASTER PC")
        info = self.network_discovery.local_info
        
        pc_info = f"Management IP: {info.ip_address}\n"
        pc_info += f"Management Interface: {info.interface}\n"
        if info.diagnostic_ip and info.diagnostic_ip != info.ip_address:
            pc_info += f"Diagnostic IP: {info.diagnostic_ip}\n"
            pc_info += f"Diagnostic Interface: {info.diagnostic_interface}\n"
        pc_info += f"Gateway: {info.gateway}\n"
        
        self.add_info_card("Local Machine", pc_info)
        
        # Display Firewall Info with VLANs
        if self.network_discovery.firewall_interfaces or self.network_discovery.vlan_interfaces:
            self.add_section_header("FIREWALL INTERFACES")
            
            # Create a set of all parent interfaces that exist as main interfaces
            existing_parents = {iface.name for iface in self.network_discovery.firewall_interfaces}
            
            # Group VLANs by their parent
            vlan_map = defaultdict(list)
            vlans_without_parents = []
            
            for vlan in self.network_discovery.vlan_interfaces:
                if vlan.parent_interface:
                    if vlan.parent_interface in existing_parents:
                        # Parent exists, group under it
                        vlan_map[vlan.parent_interface].append(vlan)
                    else:
                        # Parent doesn't exist, show as standalone
                        vlans_without_parents.append(vlan)
                else:
                    # No parent specified, show as standalone
                    vlans_without_parents.append(vlan)
            
            # Display main interfaces with their VLANs
            for iface in self.network_discovery.firewall_interfaces:
                self.add_interface_card_with_vlans(iface, vlan_map.get(iface.name, []))
            
            # Display VLANs that couldn't be grouped under any existing parent
            if vlans_without_parents:
                self.add_section_header("VLAN INTERFACES")
                for vlan in vlans_without_parents:
                    self.add_interface_card_with_vlans(vlan, [])
        else:
            self.add_info_card("No Interfaces", "No firewall interfaces found in database")
        
        # Display Managed Switches
        self.add_section_header("MANAGED SWITCHES")
        self.load_switches()
        
        self.content_layout.addStretch()
    
    def add_section_header(self, title: str):
        """Add a section header"""
        label = QLabel(title)
        label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        label.setStyleSheet("color: #64748b; margin-top: 10px; margin-bottom: 5px;")
        self.content_layout.addWidget(label)
    
    def add_info_card(self, title: str, content: str):
        """Add an information card"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
                padding: 5px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title_label.setStyleSheet("color: #0f172a;")
        layout.addWidget(title_label)
        
        content_label = QLabel(content)
        content_label.setStyleSheet("color: #475569; font-family: Consolas; line-height: 1.6;")
        layout.addWidget(content_label)
        
        self.content_layout.addWidget(card)
    
    def add_interface_card_with_vlans(self, iface, vlans):
        """Add firewall interface card with VLAN sub-interfaces"""
        card = QFrame()
        
        # Color coding
        border_colors = {
            'WAN': '#0ea5e9',      # Blue
            'LAN': '#10b981',      # Green
            'OPT1': '#8b5cf6',     # Purple
            'OPT2': '#f59e0b',     # Orange
            'OPT2_VLAN': '#f59e0b', # Orange (for VLANs)
            'MGMT': '#ec4899',     # Pink
            'DATA': '#14b8a6',     # Teal
            'VLAN': '#94a3b8',     # Gray
            'VIRTUAL': '#64748b',  # Dark Gray
            'UNKNOWN': '#64748b'   # Gray
        }
        
        # Get base type for color (e.g., OPT2_VLAN -> OPT2)
        base_type = iface.interface_type.split('_')[0] if '_' in iface.interface_type else iface.interface_type
        border_color = border_colors.get(iface.interface_type, border_colors.get(base_type, '#64748b'))
        
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 8px;
                border-left: 4px solid {border_color};
                border-top: 1px solid #e2e8f0;
                border-right: 1px solid #e2e8f0;
                border-bottom: 1px solid #e2e8f0;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)
        
        # Main interface row
        main_row = QHBoxLayout()
        
        left = QVBoxLayout()
        
        # Show VLAN ID if present
        type_text = iface.interface_type
        if iface.vlan_id:
            type_text = f"{iface.interface_type} (VLAN {iface.vlan_id})"
        
        type_label = QLabel(f"{self._get_interface_icon(iface.interface_type)} {type_text}")
        type_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        type_label.setStyleSheet(f"color: {border_color};")
        left.addWidget(type_label)
        
        name_label = QLabel(f"Interface: {iface.name}")
        name_label.setStyleSheet("color: #64748b; font-size: 11px;")
        left.addWidget(name_label)
        
        # Show parent for VLANs if available
        if iface.parent_interface and iface.vlan_id:
            parent_label = QLabel(f"Parent: {iface.parent_interface}")
            parent_label.setStyleSheet("color: #94a3b8; font-size: 10px;")
            left.addWidget(parent_label)
        
        main_row.addLayout(left)
        main_row.addStretch()
        
        # IP details
        right = QVBoxLayout()
        right.setAlignment(Qt.AlignRight)
        
        if iface.ip_address and iface.ip_address.strip():
            ip_label = QLabel(iface.ip_address)
            ip_label.setFont(QFont("Consolas", 11, QFont.Bold))
            ip_label.setStyleSheet("color: #0f172a;")
            right.addWidget(ip_label)
        
        if iface.subnet_cidr and iface.subnet_cidr.strip():
            cidr_label = QLabel(iface.subnet_cidr)
            cidr_label.setStyleSheet("color: #64748b; font-family: Consolas;")
            right.addWidget(cidr_label)
        
        dhcp_label = QLabel("DHCP: " + ("✓" if iface.is_dhcp_enabled else "✗"))
        dhcp_label.setStyleSheet("color: #64748b;")
        right.addWidget(dhcp_label)
        
        main_row.addLayout(right)
        layout.addLayout(main_row)
        
        # VLAN sub-interfaces (only show if this is a parent and has VLANs)
        if vlans:
            vlan_container = QFrame()
            vlan_container.setStyleSheet("""
                QFrame {
                    background-color: #f8fafc;
                    border-radius: 6px;
                    border: 1px solid #e2e8f0;
                    margin-top: 5px;
                }
            """)
            vlan_layout = QVBoxLayout(vlan_container)
            vlan_layout.setContentsMargins(15, 10, 15, 10)
            vlan_layout.setSpacing(8)
            
            vlan_header = QLabel("VLAN Sub-interfaces:")
            vlan_header.setFont(QFont("Segoe UI", 9, QFont.Bold))
            vlan_header.setStyleSheet("color: #475569;")
            vlan_layout.addWidget(vlan_header)
            
            for vlan in vlans:
                vlan_row = QHBoxLayout()
                
                vlan_name = QLabel(f"  └─ {vlan.name} (VLAN {vlan.vlan_id})")
                vlan_name.setStyleSheet("color: #64748b; font-family: Consolas;")
                vlan_row.addWidget(vlan_name)
                
                vlan_row.addStretch()
                
                if vlan.ip_address and vlan.ip_address.strip():
                    vlan_ip = QLabel(vlan.ip_address)
                    vlan_ip.setStyleSheet("color: #0f172a; font-family: Consolas;")
                    vlan_row.addWidget(vlan_ip)
                
                vlan_layout.addLayout(vlan_row)
            
            layout.addWidget(vlan_container)
        
        self.content_layout.addWidget(card)
    
    def _get_interface_icon(self, iface_type: str) -> str:
        """Get icon for interface type"""
        icons = {
            'WAN': '🌐',
            'LAN': '🔌',
            'OPT1': '🔧',
            'OPT2': '⚙️',
            'OPT2_VLAN': '⚙️',
            'MGMT': '🔐',
            'DATA': '💾',
            'VLAN': '🔀',
            'VIRTUAL': '🧩',
            'UNKNOWN': '❓'
        }
        
        # Get base type
        base_type = iface_type.split('_')[0] if '_' in iface_type else iface_type
        return icons.get(iface_type, icons.get(base_type, '🔌'))
    
    def load_switches(self):
        """Load switches from database with proper type"""
        try:
            from app.db.connection import get_connection
            conn = get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT ms.switch_ip, ms.switch_type, ms.last_seen,
                       fi.interface_type, fi.subnet_cidr, ms.sudo_password,
                       ms.ssh_username
                FROM managed_switches ms
                JOIN firewall_interfaces fi ON ms.subnet_id = fi.id
                ORDER BY fi.interface_type
            """)
            
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            print(f"Found {len(rows)} switches in database")
            
            if not rows:
                self.add_info_card(
                    "No Switches Configured",
                    "No managed switches have been configured.\n"
                    "Click 'Edit Configuration' to add switches."
                )
                return
            
            for row in rows:
                switch_ip, switch_type, last_seen, iface_type, subnet, sudo_pass, ssh_user = row
                self.add_switch_card(switch_ip, switch_type, last_seen, iface_type, subnet, sudo_pass, ssh_user)
                
        except Exception as e:
            print(f"Error loading switches: {e}")
            import traceback
            traceback.print_exc()
            self.add_info_card("Error", f"Could not load switches: {str(e)}")
    
    def add_switch_card(self, ip: str, sw_type: str, last_seen, iface_type: str, subnet: str, sudo_pass: str = None, ssh_user: str = None):
        """Add a switch information card with proper type display"""
        card = QFrame()
        
        # Color based on type
        if sw_type and "Open" in sw_type:
            bg_color = "#f0fdf4"  # Green
            border_color = "#bbf7d0"
            text_color = "#15803d"
            icon = "🖧"
        elif sw_type and "Cisco" in sw_type:
            bg_color = "#eff6ff"  # Blue
            border_color = "#bfdbfe"
            text_color = "#1d4ed8"
            icon = "🌐"
        else:
            bg_color = "#fefce8"  # Yellow (unknown)
            border_color = "#fef08a"
            text_color = "#a16207"
            icon = "❓"
        
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 8px;
                border: 1px solid {border_color};
                padding: 5px;
            }}
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)
        
        left = QVBoxLayout()
        
        title = QLabel(f"{icon} {sw_type if sw_type else 'Unknown Switch'}")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title.setStyleSheet(f"color: {text_color};")
        left.addWidget(title)
        
        subnet_label = QLabel(f"Connected to: {iface_type} ({subnet})")
        subnet_label.setStyleSheet("color: #64748b;")
        left.addWidget(subnet_label)
        
        if ssh_user:
            user_label = QLabel(f"SSH User: {ssh_user}")
            user_label.setStyleSheet("color: #64748b; font-size: 10px;")
            left.addWidget(user_label)
        
        if sudo_pass:
            auth_label = QLabel("🔐 Authentication: Configured")
            auth_label.setStyleSheet("color: #10b981; font-size: 10px;")
            left.addWidget(auth_label)
        
        layout.addLayout(left)
        layout.addStretch()
        
        right = QVBoxLayout()
        right.setAlignment(Qt.AlignRight)
        
        ip_label = QLabel(ip)
        ip_label.setFont(QFont("Consolas", 11, QFont.Bold))
        ip_label.setStyleSheet(f"color: {text_color};")
        right.addWidget(ip_label)
        
        if last_seen:
            # Check if last_seen is recent (within last hour)
            from datetime import datetime, timedelta
            if isinstance(last_seen, datetime):
                time_diff = datetime.now() - last_seen
                if time_diff < timedelta(hours=1):
                    status = QLabel("● Online")
                    status.setStyleSheet("color: #22c55e;")
                else:
                    status = QLabel("● Last seen: " + last_seen.strftime("%H:%M"))
                    status.setStyleSheet("color: #94a3b8;")
            else:
                status = QLabel("● Online")
                status.setStyleSheet("color: #22c55e;")
        else:
            status = QLabel("● Unknown")
            status.setStyleSheet("color: #94a3b8;")
        right.addWidget(status)
        
        layout.addLayout(right)
        
        self.content_layout.addWidget(card)
    
    def show_setup_required(self):
        """Show message when setup is not complete"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #fef2f2;
                border-radius: 12px;
                border: 2px dashed #fecaca;
                padding: 20px;
                margin: 20px;
            }
        """)
        
        layout = QVBoxLayout(card)
        
        icon = QLabel("⚠")
        icon.setFont(QFont("Segoe UI", 48))
        icon.setStyleSheet("color: #ef4444;")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)
        
        title = QLabel("Network Setup Required")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #991b1b;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        desc = QLabel(
            "The network topology has not been configured yet. "
            "Please complete the initial setup to discover your firewall and switches."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #7f1d1d;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        self.content_layout.addWidget(card)
    
    def edit_configuration(self):
        """Open setup wizard to reconfigure"""
        from PySide6.QtWidgets import QDialog
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Network Configuration")
        dialog.setMinimumSize(800, 700)
        
        from app.ui.pages.setup_wizard import SetupWizard
        wizard = SetupWizard(lambda: dialog.accept())
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(wizard)
        
        dialog.exec()
        
        # Reload after edit
        self.load_network_config()
