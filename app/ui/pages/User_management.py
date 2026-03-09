from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame, QHBoxLayout,
    QGraphicsDropShadowEffect, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
import re

from app.users.create_it_staff import create_it_staff
from app.utils.email_sender import send_welcome_email


class UserManagementPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # Header Section
        header_card = QFrame()
        header_card.setStyleSheet("""
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
        header_card.setGraphicsEffect(shadow)

        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(30, 25, 30, 25)

        title = QLabel("◈ USER MANAGEMENT MODULE")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #0f172a; letter-spacing: 1px;")
        header_layout.addWidget(title)

        desc = QLabel("Create and manage IT support personnel and administrator accounts")
        desc.setFont(QFont("Segoe UI", 11))
        desc.setStyleSheet("color: #64748b;")
        header_layout.addWidget(desc)

        main_layout.addWidget(header_card)

        # Content Split
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Left: Creation Form
        form_card = QFrame()
        form_card.setFixedWidth(450)
        form_card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }
        """)
        
        form_shadow = QGraphicsDropShadowEffect()
        form_shadow.setBlurRadius(25)
        form_shadow.setColor(QColor(15, 23, 42, 20))
        form_shadow.setOffset(0, 6)
        form_card.setGraphicsEffect(form_shadow)

        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(30, 30, 30, 30)
        form_layout.setSpacing(15)

        form_title = QLabel("NEW PERSONNEL")
        form_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        form_title.setStyleSheet("color: #0ea5e9;")
        form_layout.addWidget(form_title)

        # Username
        user_label = QLabel("OPERATOR USERNAME")
        user_label.setFont(QFont("Consolas", 9))
        user_label.setStyleSheet("color: #64748b;")
        form_layout.addWidget(user_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("e.g., itsupport_01")
        self.username_input.setFixedHeight(45)
        self.username_input.setStyleSheet("""
            QLineEdit {
                padding: 0 15px;
                font-size: 13px;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                background-color: #f8fafc;
                font-family: 'Consolas', monospace;
            }
            QLineEdit:focus {
                border: 2px solid #0ea5e9;
                background-color: white;
            }
        """)
        form_layout.addWidget(self.username_input)

        # Email
        email_label = QLabel("EMAIL ADDRESS")
        email_label.setFont(QFont("Consolas", 9))
        email_label.setStyleSheet("color: #64748b;")
        form_layout.addWidget(email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("e.g., staff@college.edu")
        self.email_input.setFixedHeight(45)
        self.email_input.setStyleSheet("""
            QLineEdit {
                padding: 0 15px;
                font-size: 13px;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                background-color: #f8fafc;
                font-family: 'Consolas', monospace;
            }
            QLineEdit:focus {
                border: 2px solid #0ea5e9;
                background-color: white;
            }
        """)
        form_layout.addWidget(self.email_input)

        # Password
        pass_label = QLabel("ACCESS KEY")
        pass_label.setFont(QFont("Consolas", 9))
        pass_label.setStyleSheet("color: #64748b;")
        form_layout.addWidget(pass_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Minimum 8 characters")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(45)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 0 15px;
                font-size: 13px;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                background-color: #f8fafc;
                font-family: 'Consolas', monospace;
            }
            QLineEdit:focus {
                border: 2px solid #0ea5e9;
                background-color: white;
            }
        """)
        form_layout.addWidget(self.password_input)

        form_layout.addSpacing(10)

        # Create Button
        create_btn = QPushButton("◈ CREATE ACCOUNT")
        create_btn.setFixedHeight(50)
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #059669);
                color: white;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #059669, stop:1 #047857);
            }
        """)
        create_btn.clicked.connect(self.create_user)
        form_layout.addWidget(create_btn)

        form_layout.addStretch()

        # Requirements box
        req_box = QFrame()
        req_box.setStyleSheet("""
            QFrame {
                background-color: #f0f9ff;
                border-radius: 8px;
                border: 1px solid #bae6fd;
            }
        """)
        req_layout = QVBoxLayout(req_box)
        req_layout.setContentsMargins(15, 15, 15, 15)
        
        req_title = QLabel("REQUIREMENTS")
        req_title.setFont(QFont("Consolas", 9, QFont.Bold))
        req_title.setStyleSheet("color: #0284c7;")
        req_layout.addWidget(req_title)
        
        req_text = QLabel("• Alphanumeric username\n• Valid email address\n• 8+ character password\n• Auto-generated access level: IT_SUPPORT")
        req_text.setFont(QFont("Consolas", 9))
        req_text.setStyleSheet("color: #0ea5e9; line-height: 1.6;")
        req_layout.addWidget(req_text)
        
        form_layout.addWidget(req_box)

        content_layout.addWidget(form_card)

        # Right: Personnel List Table
        list_card = QFrame()
        list_card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }
        """)
        
        list_shadow = QGraphicsDropShadowEffect()
        list_shadow.setBlurRadius(25)
        list_shadow.setColor(QColor(15, 23, 42, 20))
        list_shadow.setOffset(0, 6)
        list_card.setGraphicsEffect(list_shadow)

        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(25, 25, 25, 25)

        list_title = QLabel("ACTIVE PERSONNEL")
        list_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        list_title.setStyleSheet("color: #0f172a;")
        list_layout.addWidget(list_title)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "USERNAME", "ROLE", "STATUS"])
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                gridline-color: #e2e8f0;
            }
            QHeaderView::section {
                background-color: #0ea5e9;
                color: white;
                padding: 10px;
                font-weight: bold;
                font-family: 'Consolas', monospace;
                font-size: 11px;
                border: none;
            }
            QTableWidget::item {
                padding: 10px;
                font-family: 'Consolas', monospace;
                color: #0f172a;
            }
            QTableWidget::item:selected {
                background-color: #e0f2fe;
                color: #0284c7;
            }
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        
        # Sample data (replace with database query)
        self.load_user_data()
        
        list_layout.addWidget(self.table)
        content_layout.addWidget(list_card, stretch=1)

        main_layout.addLayout(content_layout, stretch=1)
        self.setLayout(main_layout)

    def load_user_data(self):
        # This should query your database
        sample_data = [
            ("001", "netadmin_1", "ADMINISTRATOR", "● ACTIVE"),
            ("002", "secadmin_I", "SECURITY_ADMIN", "● ACTIVE"),
            ("003", "itsupport_03", "IT_SUPPORT", "● OFFLINE"),
        ]
        
        self.table.setRowCount(len(sample_data))
        for i, (id_, user, role, status) in enumerate(sample_data):
            self.table.setItem(i, 0, QTableWidgetItem(id_))
            self.table.setItem(i, 1, QTableWidgetItem(user))
            self.table.setItem(i, 2, QTableWidgetItem(role))
            
            status_item = QTableWidgetItem(status)
            if "ACTIVE" in status:
                status_item.setForeground(QColor("#10b981"))
            else:
                status_item.setForeground(QColor("#64748b"))
            self.table.setItem(i, 3, status_item)

    def create_user(self):
        u = self.username_input.text().strip()
        e = self.email_input.text().strip().lower()
        p = self.password_input.text().strip()

        if not u or not e or not p:
            QMessageBox.warning(self, "Validation Error", 
                "⚠ All fields required. Please complete the form.")
            return

        if not re.match(r"^[a-zA-Z0-9_]+$", u):
            QMessageBox.warning(self, "Validation Error", 
                "⚠ Username must contain only letters, numbers, and underscore.")
            return

        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", e):
            QMessageBox.warning(self, "Validation Error", 
                "⚠ Invalid email format.")
            return
        
        if len(p) < 8:
            QMessageBox.warning(self, "Validation Error", 
                "⚠ Access key must be at least 8 characters.")
            return

        try:
            create_it_staff(u, p)
            email_warning = None
            try:
                send_welcome_email(
                    to_email=e,
                    username=u,
                    password=p,
                    role="ITSupport"
                )
            except Exception as email_err:
                email_warning = str(email_err)

            QMessageBox.information(self, "Success", 
                f"✓ Personnel account '{u}' created successfully.\n\nAccess level: IT_SUPPORT")
            self.username_input.clear()
            self.email_input.clear()
            self.password_input.clear()
            self.load_user_data()  # Refresh table

            if email_warning:
                QMessageBox.warning(
                    self,
                    "Email Warning",
                    f"Account created, but credentials email could not be sent to {e}.\n\n{email_warning}"
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                f"✗ Account creation failed:\n{str(e)}")
