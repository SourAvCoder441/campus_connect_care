from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QTextEdit, 
    QPushButton, QHBoxLayout, QFrame, QGraphicsDropShadowEffect,
    QTreeWidget, QTreeWidgetItem, QSplitter, QComboBox,
    QDateTimeEdit, QLineEdit, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QFont, QColor
import json

from app.db.connection import get_connection


class LogsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_logs()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # Header
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

        title = QLabel("◈ SYSTEM LOGS")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #0f172a;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Logs", "INFO Only", "WARN Only", "ERROR Only", "AUDIT Only"])
        self.filter_combo.setFixedHeight(35)
        self.filter_combo.currentTextChanged.connect(self.apply_filters)
        header_layout.addWidget(self.filter_combo)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search logs...")
        self.search_input.setFixedHeight(35)
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self.apply_filters)
        header_layout.addWidget(self.search_input)

        refresh_btn = QPushButton("REFRESH")
        refresh_btn.setFixedHeight(35)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet("""
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
        refresh_btn.clicked.connect(self.load_logs)
        header_layout.addWidget(refresh_btn)

        main_layout.addWidget(header)

        # Main content with splitter
        splitter = QSplitter(Qt.Vertical)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #e2e8f0;
                height: 2px;
            }
        """)

        # Log tree
        self.log_tree = QTreeWidget()
        self.log_tree.setHeaderLabels(["Time", "Level", "Component", "Message", "User", "Session"])
        self.log_tree.setStyleSheet("""
            QTreeWidget {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 5px;
            }
            QTreeWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f1f5f9;
            }
            QTreeWidget::item:selected {
                background-color: #e0f2fe;
            }
        """)
        self.log_tree.setColumnWidth(0, 180)  # Time
        self.log_tree.setColumnWidth(1, 70)   # Level
        self.log_tree.setColumnWidth(2, 100)  # Component
        self.log_tree.setColumnWidth(3, 400)  # Message
        self.log_tree.setColumnWidth(4, 80)   # User
        self.log_tree.setColumnWidth(5, 70)   # Session
        self.log_tree.itemClicked.connect(self.on_log_selected)

        # Details panel
        details_frame = QFrame()
        details_frame.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
        """)
        details_layout = QVBoxLayout(details_frame)

        details_header = QLabel("LOG DETAILS")
        details_header.setFont(QFont("Segoe UI", 10, QFont.Bold))
        details_header.setStyleSheet("color: #0f172a; padding: 5px;")
        details_layout.addWidget(details_header)

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
        details_layout.addWidget(self.details_text)

        splitter.addWidget(self.log_tree)
        splitter.addWidget(details_frame)
        splitter.setSizes([500, 200])

        main_layout.addWidget(splitter, stretch=1)
        self.setLayout(main_layout)

    def load_logs(self):
        """Load logs from database"""
        self.log_tree.clear()
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Get logs with user and session info
            cur.execute("""
                SELECT 
                    sl.log_time,
                    sl.log_level,
                    sl.component,
                    sl.message,
                    u.username,
                    sl.session_id,
                    sl.details
                FROM system_logs sl
                LEFT JOIN users u ON sl.user_id = u.id
                ORDER BY sl.log_time DESC
                LIMIT 1000
            """)
            
            logs = cur.fetchall()
            cur.close()
            conn.close()
            
            for log in logs:
                log_time, level, component, message, username, session_id, details = log
                
                # Format time
                time_str = log_time.strftime('%Y-%m-%d %H:%M:%S') if log_time else 'Unknown'
                
                item = QTreeWidgetItem([
                    time_str,
                    level,
                    component,
                    message[:100] + '...' if len(message) > 100 else message,
                    username or 'System',
                    str(session_id) if session_id else ''
                ])
                
                # Color based on level
                if level == 'ERROR':
                    item.setForeground(1, QColor(239, 68, 68))  # Red
                elif level == 'WARNING':
                    item.setForeground(1, QColor(245, 158, 11))  # Yellow
                elif level == 'INFO':
                    item.setForeground(1, QColor(16, 185, 129))  # Green
                elif level == 'AUDIT':
                    item.setForeground(1, QColor(139, 92, 246))  # Purple
                
                # Store details for later
                item.setData(0, Qt.UserRole, details)
                
                self.log_tree.addTopLevelItem(item)
            
            self.log_tree.sortItems(0, Qt.DescendingOrder)
            
        except Exception as e:
            error_item = QTreeWidgetItem(["Error", "", "", f"Failed to load logs: {str(e)}", "", ""])
            self.log_tree.addTopLevelItem(error_item)

    def apply_filters(self):
        """Apply level filter and search"""
        filter_text = self.filter_combo.currentText()
        search_text = self.search_input.text().lower()
        
        level_filter = None
        if "INFO Only" in filter_text:
            level_filter = "INFO"
        elif "WARN Only" in filter_text:
            level_filter = "WARNING"
        elif "ERROR Only" in filter_text:
            level_filter = "ERROR"
        elif "AUDIT Only" in filter_text:
            level_filter = "AUDIT"
        
        for i in range(self.log_tree.topLevelItemCount()):
            item = self.log_tree.topLevelItem(i)
            show = True
            
            # Apply level filter
            if level_filter and item.text(1) != level_filter:
                show = False
            
            # Apply search filter
            if search_text:
                matches = False
                for col in range(4):  # Search in time, level, component, message
                    if search_text in item.text(col).lower():
                        matches = True
                        break
                if not matches:
                    show = False
            
            item.setHidden(not show)

    def on_log_selected(self, item, column):
        """Show log details when selected"""
        details = item.data(0, Qt.UserRole)
        
        if details:
            try:
                # Try to parse as JSON
                if isinstance(details, str):
                    details_json = json.loads(details)
                    formatted = json.dumps(details_json, indent=2)
                else:
                    formatted = str(details)
                self.details_text.setText(formatted)
            except:
                self.details_text.setText(str(details))
        else:
            # Show basic info
            text = f"Time: {item.text(0)}\n"
            text += f"Level: {item.text(1)}\n"
            text += f"Component: {item.text(2)}\n"
            text += f"User: {item.text(4)}\n"
            text += f"Session: {item.text(5)}\n"
            text += f"\nMessage:\n{item.text(3)}"
            self.details_text.setText(text)
