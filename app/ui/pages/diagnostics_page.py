# app/ui/pages/diagnostics_page.py (COMPLETE REDESIGNED VERSION)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTextEdit, QHBoxLayout, QFrame,
    QGraphicsDropShadowEffect, QComboBox,
    QProgressBar, QTreeWidget, QTreeWidgetItem,
    QSplitter, QTabWidget, QHeaderView, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor, QTextCursor, QPalette
import time
from datetime import datetime
from collections import defaultdict

# Import session management
try:
    from app.session.session import get_current_user
except ImportError:
    def get_current_user():
        return {'id': 1, 'username': 'admin', 'role': 'NetworkAdmin'}

# Import detector manager
from app.core.diagnostics.detector_manager import DetectorManager


class DiagnosticWorker(QThread):
    """Background worker for running diagnostics"""
    log = Signal(str)
    progress = Signal(int)
    status = Signal(str)
    finished_signal = Signal(dict)
    
    def __init__(self, user_id, scan_mode, target=None):
        super().__init__()
        self.user_id = user_id
        self.scan_mode = scan_mode
        self.target = target
        self.manager = None
        self.start_time = None
        
    def run(self):
        self.start_time = time.time()
        
        try:
            # Create manager
            self.manager = DetectorManager(self.user_id)
            
            # Create session
            if self.scan_mode == 'full_diagnosis':
                session_id = self.manager.create_session('full', self.target)
                self.log.emit(f"▶ Created full diagnostic session: {session_id}")
            else:
                session_id = self.manager.create_session('scan', self.target)
                self.log.emit(f"▶ Created network scan session: {session_id}")
            
            # Determine which detectors to run
            if self.scan_mode == 'full_diagnosis':
                # Run ALL detectors
                self.status.emit("Running full network diagnosis...")
                self.log.emit("\n" + "="*60)
                self.log.emit("FULL NETWORK DIAGNOSIS")
                self.log.emit("="*60)
                
                detectors = ['device_discovery', 'ip_conflict', 'network_loop', 
                            'high_latency', 'packet_loss', 'dhcp_exhaustion', 'bandwidth']
                
                for i, detector in enumerate(detectors):
                    progress = int((i + 1) * 100 / len(detectors))
                    self.status.emit(f"Running {detector}...")
                    self.log.emit(f"\n[{i+1}/{len(detectors)}] {detector.replace('_', ' ').title()}...")
                    self.manager.run_detectors([detector])
                    self.progress.emit(progress)
                
            else:  # network_scan
                self.status.emit("Performing complete network scan...")
                self.log.emit("\n" + "="*60)
                self.log.emit("COMPLETE NETWORK SCAN")
                self.log.emit("="*60)
                self.log.emit("\n[1/1] Scanning network for all devices...")
                self.manager.run_detectors(['device_discovery'])
                self.progress.emit(100)
            
            # Complete session
            elapsed = time.time() - self.start_time
            self.manager.complete_session(f"Completed in {elapsed:.1f}s")
            
            # Get all results
            results = self.manager.get_results()
            results['elapsed_time'] = elapsed
            results['session_id'] = session_id
            
            self.log.emit(f"\n{'='*60}")
            self.log.emit(f"✅ DIAGNOSTIC COMPLETE in {elapsed:.1f} seconds")
            self.log.emit(f"{'='*60}")
            
            self.finished_signal.emit(results)
            
        except Exception as e:
            self.log.emit(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            if self.manager:
                self.manager.fail_session(str(e))
            self.finished_signal.emit({'error': str(e)})


class DiagnosticsPage(QWidget):
    def __init__(self):
        super().__init__()
        try:
            self.current_user = get_current_user()
        except:
            self.current_user = {'id': 1, 'username': 'admin', 'role': 'NetworkAdmin'}
        
        self.current_session_id = None
        self.worker = None
        self.init_ui()
        
        # Show initial message
        self.log_message(f"Campus Connect-Care Diagnostic Console v2.0")
        self.log_message(f"{'='*60}")
        self.log_message(f"User: {self.current_user.get('username', 'Unknown')} (Role: {self.current_user.get('role', 'Unknown')})")
        self.log_message(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_message(f"{'='*60}")
        self.log_message("\nSelect scan mode and click EXECUTE to begin.\n")
        self.log_message("• FULL DIAGNOSIS: Detects all network faults (IP conflicts, loops, latency, packet loss, DHCP exhaustion, bandwidth)")
        self.log_message("• NETWORK SCAN: Discovers all devices and determines their status (active/powered_off/cable_failure)\n")

    def init_ui(self):
        # Main layout - no margins for maximum space
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)

        # === CONTROL PANEL ===
        control_card = self.create_control_panel()
        main_layout.addWidget(control_card)

        # === MAIN SPLITTER (FULLY ADJUSTABLE) ===
        # This splitter divides the space between tabs and details panel
        # User can drag the handle to resize both sections
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #cbd5e1;
                height: 4px;
                margin: 2px 0;
            }
            QSplitter::handle:hover {
                background-color: #0ea5e9;
            }
            QSplitter::handle:pressed {
                background-color: #0284c7;
            }
        """)
        self.main_splitter.setHandleWidth(8)
        self.main_splitter.setChildrenCollapsible(False)

        # === TOP SECTION: TABS (CONSOLE, SUMMARY, DEVICES) ===
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
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
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 3px solid #0ea5e9;
                color: #0ea5e9;
            }
            QTabBar::tab:hover:!selected {
                background: #e2e8f0;
            }
        """)

        # === CONSOLE TAB ===
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
                line-height: 1.5;
            }
        """)
        console_layout.addWidget(self.console)

        self.tabs.addTab(console_widget, "📟 CONSOLE")

        # === SUMMARY TAB ===
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
                background-color: #0ea5e9;
                color: white;
            }
            QTreeWidget::item:selected:!active {
                background-color: #94a3b8;
                color: white;
            }
            QTreeWidget::branch:selected {
                background-color: #0ea5e9;
            }
            QHeaderView::section {
                background-color: #f1f5f9;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #cbd5e1;
                font-weight: bold;
            }
        """)
        self.summary_tree.setAlternatingRowColors(True)
        self.summary_tree.setColumnWidth(0, 250)
        self.summary_tree.setColumnWidth(1, 100)
        self.summary_tree.header().setStretchLastSection(True)
        self.summary_tree.itemClicked.connect(self.on_summary_item_clicked)
        summary_layout.addWidget(self.summary_tree)

        self.tabs.addTab(summary_widget, "📊 SUMMARY")

        # === DEVICES TAB ===
        devices_widget = QWidget()
        devices_layout = QVBoxLayout(devices_widget)
        devices_layout.setContentsMargins(0, 0, 0, 0)

        self.devices_tree = QTreeWidget()
        self.devices_tree.setHeaderLabels(["Hostname", "IP Address", "MAC Address", "Status", "Switch Port"])
        self.devices_tree.setStyleSheet("""
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
                background-color: #0ea5e9;
                color: white;
            }
            QTreeWidget::item:selected:!active {
                background-color: #94a3b8;
                color: white;
            }
            QTreeWidget::branch:selected {
                background-color: #0ea5e9;
            }
            QHeaderView::section {
                background-color: #f1f5f9;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #cbd5e1;
                font-weight: bold;
            }
        """)
        self.devices_tree.setAlternatingRowColors(True)
        self.devices_tree.setColumnWidth(0, 200)
        self.devices_tree.setColumnWidth(1, 130)
        self.devices_tree.setColumnWidth(2, 160)
        self.devices_tree.setColumnWidth(3, 120)
        self.devices_tree.setColumnWidth(4, 100)
        self.devices_tree.itemClicked.connect(self.on_device_selected)
        devices_layout.addWidget(self.devices_tree)

        self.tabs.addTab(devices_widget, "💻 DEVICES")

        # Add tabs to main splitter (top section)
        self.main_splitter.addWidget(self.tabs)

        # === BOTTOM SECTION: DETAILS PANEL (FULLY ADJUSTABLE) ===
        self.details_frame = self.create_details_panel()
        self.main_splitter.addWidget(self.details_frame)
        
        # Set initial sizes (70% tabs, 30% details) - user can drag to adjust
        self.main_splitter.setSizes([700, 300])

        main_layout.addWidget(self.main_splitter, stretch=1)
        self.setLayout(main_layout)

    def create_control_panel(self):
        control_card = QFrame()
        control_card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }
        """)
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(15, 23, 42, 25))
        shadow.setOffset(0, 4)
        control_card.setGraphicsEffect(shadow)

        control_layout = QVBoxLayout(control_card)
        control_layout.setContentsMargins(25, 20, 25, 20)
        control_layout.setSpacing(15)

        # Header
        header = QLabel("◈ NETWORK DIAGNOSTIC TOOLS")
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        header.setStyleSheet("color: #0f172a;")
        control_layout.addWidget(header)

        # Scan Mode Selection
        mode_layout = QHBoxLayout()
        mode_label = QLabel("SCAN MODE:")
        mode_label.setFont(QFont("Consolas", 10))
        mode_label.setStyleSheet("color: #64748b; font-weight: bold;")
        mode_layout.addWidget(mode_label)
        
        self.scan_mode = QComboBox()
        self.scan_mode.addItems([
            "FULL DIAGNOSIS - Detect All Faults",
            "NETWORK SCAN - Discover All Devices"
        ])
        self.scan_mode.setFixedHeight(40)
        self.scan_mode.setStyleSheet("""
            QComboBox {
                padding: 0 15px;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                background-color: #f8fafc;
                font-size: 13px;
                font-weight: bold;
            }
            QComboBox:focus {
                border: 2px solid #0ea5e9;
            }
            QComboBox:hover {
                border: 2px solid #94a3b8;
            }
        """)
        mode_layout.addWidget(self.scan_mode, stretch=1)
        control_layout.addLayout(mode_layout)

        # Target Input
        target_layout = QHBoxLayout()
        target_label = QLabel("TARGET (optional):")
        target_label.setFont(QFont("Consolas", 10))
        target_label.setStyleSheet("color: #64748b;")
        target_layout.addWidget(target_label)
        
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("IP address or subnet - leave blank for full network")
        self.target_input.setFixedHeight(40)
        self.target_input.setStyleSheet("""
            QLineEdit {
                padding: 0 15px;
                font-size: 13px;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                background-color: #f8fafc;
            }
            QLineEdit:focus {
                border: 2px solid #0ea5e9;
                background-color: white;
            }
            QLineEdit:hover {
                border: 2px solid #94a3b8;
            }
        """)
        target_layout.addWidget(self.target_input, stretch=1)
        control_layout.addLayout(target_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.execute_btn = QPushButton("▶ EXECUTE DIAGNOSTIC")
        self.execute_btn.setFixedHeight(50)
        self.execute_btn.setCursor(Qt.PointingHandCursor)
        self.execute_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0ea5e9, stop:1 #0284c7);
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0284c7, stop:1 #0369a1);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0369a1, stop:1 #075985);
            }
            QPushButton:disabled {
                background-color: #cbd5e1;
                color: #64748b;
            }
        """)
        self.execute_btn.clicked.connect(self.run_diagnostic)
        btn_layout.addWidget(self.execute_btn)

        self.clear_btn = QPushButton("CLEAR CONSOLE")
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
            QPushButton:pressed {
                background-color: #e2e8f0;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_console)
        btn_layout.addWidget(self.clear_btn)

        control_layout.addLayout(btn_layout)

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
                background-color: #0ea5e9;
                border-radius: 5px;
            }
        """)
        control_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #64748b; font-family: Consolas; font-size: 12px;")
        control_layout.addWidget(self.status_label)

        return control_card

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
        header.setStyleSheet("color: #0f172a; padding: 5px 0;")
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
                font-size: 11px;
            }
        """)
        layout.addWidget(self.details_text)

        return frame

    def log_message(self, text, error=False):
        """Add text to console"""
        if error:
            self.console.append(f"<span style='color: #ef4444;'>❌ {text}</span>")
        elif "✓" in text or "✅" in text:
            self.console.append(f"<span style='color: #10b981;'>{text}</span>")
        elif "▶" in text or "=" in text:
            self.console.append(f"<span style='color: #0ea5e9; font-weight: bold;'>{text}</span>")
        else:
            self.console.append(f"<span style='color: #e2e8f0;'>{text}</span>")
        
        # Auto-scroll to bottom
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.console.setTextCursor(cursor)

    def run_diagnostic(self):
        """Start diagnostic in background thread"""
        scan_mode_text = self.scan_mode.currentText()
        target = self.target_input.text().strip() or None
        
        scan_mode = 'full_diagnosis' if "FULL DIAGNOSIS" in scan_mode_text else 'network_scan'
        mode_name = "FULL DIAGNOSIS" if scan_mode == 'full_diagnosis' else "NETWORK SCAN"
        
        self.execute_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Starting {mode_name}...")
        
        # Clear previous results
        self.summary_tree.clear()
        self.devices_tree.clear()
        self.details_text.clear()
        
        self.log_message(f"\n{'='*60}")
        self.log_message(f"▶ STARTING {mode_name}")
        self.log_message(f"{'='*60}")
        self.log_message(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if target:
            self.log_message(f"Target: {target}")
        self.log_message("")
        
        self.worker = DiagnosticWorker(
            self.current_user.get('id', 1),
            scan_mode,
            target
        )
        self.worker.log.connect(self.log_message)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished_signal.connect(self.on_diagnostic_finished)
        self.worker.start()

    def on_diagnostic_finished(self, results):
        """Handle diagnostic completion"""
        self.execute_btn.setEnabled(True)
        self.status_label.setText("Ready")
        
        if 'error' in results:
            self.log_message(f"DIAGNOSTIC FAILED: {results['error']}", error=True)
            return
        
        self.current_session_id = results.get('session_id')
        
        # Update summary and devices
        self.update_summary(results)
        self.update_devices()
        
        # Switch to Summary tab
        self.tabs.setCurrentIndex(1)
        
        if 'elapsed_time' in results:
            self.log_message(f"\n✅ Scan completed in {results['elapsed_time']:.1f} seconds")

    def update_summary(self, results):
        """Update summary tree with results"""
        self.summary_tree.clear()
        
        # === SESSION INFO ===
        session = results.get('session', [])
        if session and len(session) > 0:
            session_item = QTreeWidgetItem(["📌 SESSION INFORMATION", "", ""])
            session_item.setFont(0, QFont("Segoe UI", 11, QFont.Bold))
            session_item.setForeground(0, QColor(15, 23, 42))
            session_item.setBackground(0, QColor(241, 245, 249))
            
            QTreeWidgetItem(session_item, ["Session ID", str(session[0]), ""])
            QTreeWidgetItem(session_item, ["Scan Type", session[4] if len(session) > 4 else 'unknown', ""])
            QTreeWidgetItem(session_item, ["Start Time", str(session[2]) if len(session) > 2 else 'unknown', ""])
            if 'elapsed_time' in results:
                QTreeWidgetItem(session_item, ["Duration", f"{results['elapsed_time']:.1f} seconds", ""])
            
            self.summary_tree.addTopLevelItem(session_item)
        
        # === FAULT SUMMARY ===
        faults = results.get('faults', [])
        if faults:
            # Count faults by severity
            severity_counts = defaultdict(int)
            fault_details = defaultdict(list)
            
            for fault in faults:
                severity = fault[3] if len(fault) > 3 and fault[3] else 'info'
                severity = severity.lower()
                severity_counts[severity] += 1
                
                # Store fault details for later
                fault_type = fault[2] or 'Unknown'
                description = fault[4] or 'No description'
                affected_ips = fault[5] if len(fault) > 5 and fault[5] else []
                fault_details[severity].append({
                    'type': fault_type,
                    'desc': description,
                    'ips': affected_ips,
                    'data': fault
                })
            
            faults_item = QTreeWidgetItem(["⚠️ FAULTS DETECTED", str(len(faults)), ""])
            faults_item.setFont(0, QFont("Segoe UI", 11, QFont.Bold))
            faults_item.setForeground(0, QColor(239, 68, 68))
            faults_item.setBackground(0, QColor(254, 242, 242))
            
            # Add severity breakdown
            for severity in ['critical', 'high', 'medium', 'low', 'info']:
                if severity in severity_counts:
                    color = {
                        'critical': QColor(239, 68, 68),
                        'high': QColor(249, 115, 22),
                        'medium': QColor(245, 158, 11),
                        'info': QColor(59, 130, 246)
                    }.get(severity, QColor(100, 116, 139))
                    
                    sev_item = QTreeWidgetItem([f"  {severity.upper()}", str(severity_counts[severity]), ""])
                    sev_item.setForeground(0, color)
                    faults_item.addChild(sev_item)
                    
                    # Add individual faults under each severity (collapsible)
                    for fault in fault_details[severity]:
                        ip_text = ''
                        if fault['ips']:
                            ip_text = ', '.join(str(ip) for ip in fault['ips'][:2])
                            if len(fault['ips']) > 2:
                                ip_text += f" (+{len(fault['ips'])-2})"
                        
                        fault_item = QTreeWidgetItem([
                            f"    {fault['type']}", 
                            "", 
                            f"{fault['desc'][:60]}..." if len(fault['desc']) > 60 else fault['desc']
                        ])
                        fault_item.setData(0, Qt.UserRole, fault['data'])
                        sev_item.addChild(fault_item)
            
            self.summary_tree.addTopLevelItem(faults_item)
        
        # === NETWORK STATISTICS ===
        stats = results.get('statistics', [])
        if stats:
            stats_item = QTreeWidgetItem(["📊 NETWORK STATISTICS", "", ""])
            stats_item.setFont(0, QFont("Segoe UI", 11, QFont.Bold))
            stats_item.setForeground(0, QColor(15, 23, 42))
            stats_item.setBackground(0, QColor(241, 245, 249))
            
            total_devices = 0
            active = 0
            
            for stat in stats:
                if len(stat) > 2:
                    subnet = stat[1] if len(stat) > 1 else 'unknown'
                    devices = stat[2] if stat[2] else 0
                    active_count = stat[3] if len(stat) > 3 and stat[3] else 0
                    
                    total_devices += devices
                    active += active_count
                    
                    subnet_item = QTreeWidgetItem([f"  Subnet: {subnet}", f"{devices} devices", f"{active_count} active"])
                    stats_item.addChild(subnet_item)
            
            # Add totals
            QTreeWidgetItem(stats_item, ["  TOTAL", f"{total_devices} devices", f"{active} active"])
            
            self.summary_tree.addTopLevelItem(stats_item)
        
        # Expand all to show details
        self.summary_tree.expandAll()

    def update_devices(self):
        """Update devices tree with discovered devices"""
        self.devices_tree.clear()
        
        if not self.current_session_id:
            item = QTreeWidgetItem(["No session data", "", "", "", ""])
            self.devices_tree.addTopLevelItem(item)
            return
        
        # Fetch devices from database
        try:
            from app.db.connection import get_connection
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT hostname, ip_address, mac_address, status, switch_port,
                       evidence_sources, response_time_ms
                FROM diagnostic_devices 
                WHERE session_id = %s 
                ORDER BY 
                    CASE status
                        WHEN 'active' THEN 1
                        WHEN 'new' THEN 2
                        WHEN 'powered_off' THEN 3
                        WHEN 'cable_failure' THEN 4
                        WHEN 'removed' THEN 5
                        ELSE 6
                    END,
                    ip_address
            """, (self.current_session_id,))
            devices = cur.fetchall()
            cur.close()
            conn.close()
            
            if not devices:
                item = QTreeWidgetItem(["No devices discovered", "", "", "", ""])
                self.devices_tree.addTopLevelItem(item)
                return
            
            # Group devices by status
            status_groups = {}
            for status in ['active', 'new', 'powered_off', 'cable_failure', 'removed', 'unknown']:
                group_text = {
                    'active': '✅ ACTIVE DEVICES',
                    'new': '🆕 NEW DEVICES',
                    'powered_off': '⏻ POWERED OFF',
                    'cable_failure': '🔌 CABLE FAILURES',
                    'removed': '❌ REMOVED DEVICES',
                    'unknown': '❓ UNKNOWN STATUS'
                }.get(status, status.upper())
                
                group = QTreeWidgetItem([group_text, "", "", "", ""])
                group.setFont(0, QFont("Segoe UI", 10, QFont.Bold))
                
                # Set colors
                if status == 'active':
                    group.setForeground(0, QColor(16, 185, 129))
                    group.setBackground(0, QColor(240, 253, 244))
                elif status == 'new':
                    group.setForeground(0, QColor(59, 130, 246))
                    group.setBackground(0, QColor(239, 246, 255))
                elif status == 'powered_off':
                    group.setForeground(0, QColor(239, 68, 68))
                    group.setBackground(0, QColor(254, 242, 242))
                elif status == 'cable_failure':
                    group.setForeground(0, QColor(249, 115, 22))
                    group.setBackground(0, QColor(255, 247, 237))
                elif status == 'removed':
                    group.setForeground(0, QColor(156, 163, 175))
                    group.setBackground(0, QColor(243, 244, 246))
                
                status_groups[status] = group
            
            # Add devices to groups
            for device in devices:
                hostname = device[0] or 'Unknown'
                ip = device[1] or 'N/A'
                mac = device[2] or 'N/A'
                status = device[3] or 'unknown'
                switch_port = device[4] or 'N/A'
                
                if len(hostname) > 25:
                    hostname = hostname[:22] + '...'
                
                item = QTreeWidgetItem([hostname, ip, mac, status.upper(), switch_port])
                item.setData(0, Qt.UserRole, device)
                
                # Color status text
                if status == 'active':
                    item.setForeground(3, QColor(16, 185, 129))
                elif status == 'powered_off':
                    item.setForeground(3, QColor(239, 68, 68))
                elif status == 'cable_failure':
                    item.setForeground(3, QColor(249, 115, 22))
                elif status == 'new':
                    item.setForeground(3, QColor(59, 130, 246))
                
                if status in status_groups:
                    status_groups[status].addChild(item)
                else:
                    status_groups['unknown'].addChild(item)
            
            # Add groups that have children to the tree
            for status, group in status_groups.items():
                if group.childCount() > 0:
                    group.setText(1, f"({group.childCount()})")
                    self.devices_tree.addTopLevelItem(group)
            
            self.devices_tree.expandAll()
            
        except Exception as e:
            self.log_message(f"Error loading devices: {e}", True)
            item = QTreeWidgetItem([f"Error loading devices: {str(e)}", "", "", "", ""])
            self.devices_tree.addTopLevelItem(item)

    def on_summary_item_clicked(self, item, column):
        """Show fault details when clicked in summary"""
        fault_data = item.data(0, Qt.UserRole)
        if fault_data and isinstance(fault_data, (list, tuple)):
            self.show_fault_details(fault_data)

    def on_device_selected(self, item, column):
        """Show device details when selected"""
        device_data = item.data(0, Qt.UserRole)
        if device_data and isinstance(device_data, (list, tuple)):
            self.show_device_details(device_data)

    def show_fault_details(self, fault):
        """Display fault details in details panel"""
        if len(fault) < 5:
            return
        
        text = "🔴 FAULT DETAILS\n"
        text += "="*60 + "\n\n"
        text += f"📌 Fault ID: {fault[0]}\n"
        text += f"⚠️ Type: {fault[2] or 'Unknown'}\n"
        text += f"🔥 Severity: {fault[3].upper() if fault[3] else 'UNKNOWN'}\n"
        text += f"📝 Description: {fault[4] or 'No description'}\n"
        
        if len(fault) > 5 and fault[5]:
            affected_ips = fault[5]
            if affected_ips:
                text += f"\n🌐 Affected IPs:\n"
                for ip in affected_ips:
                    text += f"  • {ip}\n"
        
        if len(fault) > 11 and fault[11]:
            text += f"\n📋 Troubleshooting Steps:\n"
            for i, step in enumerate(fault[11], 1):
                text += f"\n  {i}. {step}\n"
        
        self.details_text.setText(text)

    def show_device_details(self, device):
        """Display device details in details panel"""
        if len(device) < 7:
            return
        
        hostname = device[0] or 'Unknown'
        ip = device[1] or 'N/A'
        mac = device[2] or 'N/A'
        status = device[3] or 'unknown'
        switch_port = device[4] or 'N/A'
        evidence = device[5] if len(device) > 5 else []
        response_time = device[6] if len(device) > 6 else None
        
        text = "💻 DEVICE DETAILS\n"
        text += "="*60 + "\n\n"
        text += f"📌 Hostname: {hostname}\n"
        text += f"🌐 IP Address: {ip}\n"
        text += f"🔢 MAC Address: {mac}\n"
        text += f"📊 Status: {status.upper()}\n"
        text += f"🔌 Switch Port: {switch_port}\n"
        
        if response_time:
            text += f"⏱️ Response Time: {response_time:.3f} ms\n"
        
        if evidence:
            text += f"\n📡 Evidence Sources:\n"
            for src in evidence:
                text += f"  • {src}\n"
        
        self.details_text.setText(text)

    def clear_console(self):
        """Clear console output"""
        self.console.clear()
        self.log_message("Console cleared. System ready.")
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")
        self.details_text.clear()
