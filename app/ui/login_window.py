from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QMessageBox, QHBoxLayout, 
    QFrame, QCheckBox, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QFont, QColor
import sys

from app.auth.login import login
from app.session.session_log import log_session
from app.session.session_manager import session  # 👈 IMPORT SESSION
from app.ui.main_window import MainWindow
from app.core.network_discovery import network_discovery


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Campus Connect-Care | System Diagnostics")
        self.setMinimumSize(700, 700)
        self.resize(750, 750)
        self.settings = QSettings("CampusConnectCare", "AdminLogin")
        
        # Diagnostic tool styling - Clinical/Technical theme
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f4f8;
                font-family: 'Segoe UI', 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
            }
            QLabel {
                color: #1e293b;
            }
        """)
        
        self.init_ui()
        self.load_remembered_credentials()

    def init_ui(self):
        # Main layout - centered content
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setAlignment(Qt.AlignCenter)

        # Login Container - WIDER fixed width card
        login_card = QFrame()
        login_card.setFixedWidth(580)
        login_card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }
        """)
        
        # Professional shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(15, 23, 42, 40))
        shadow.setOffset(0, 8)
        login_card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(login_card)
        card_layout.setContentsMargins(50, 50, 50, 50)
        card_layout.setSpacing(25)

        # Card Header
        header_icon = QLabel("◈")
        header_icon.setStyleSheet("color: #0ea5e9; font-size: 32px;")
        card_layout.addWidget(header_icon, alignment=Qt.AlignCenter)

        header_title = QLabel("ADMINISTRATOR ACCESS")
        header_title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header_title.setStyleSheet("color: #0f172a; letter-spacing: 1px;")
        header_title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(header_title)

        header_sub = QLabel("Authentication Required")
        header_sub.setFont(QFont("Segoe UI", 11))
        header_sub.setStyleSheet("color: #64748b; margin-bottom: 10px;")
        header_sub.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(header_sub)

        # Separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #e2e8f0; margin-top: 10px; margin-bottom: 10px;")
        card_layout.addWidget(sep)

        # USERNAME FIELD
        user_label = QLabel("USERNAME")
        user_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        user_label.setStyleSheet("color: #475569; letter-spacing: 0.5px;")
        card_layout.addWidget(user_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username...")
        self.username_input.setFixedHeight(50)
        self.username_input.setStyleSheet("""
            QLineEdit {
                padding: 0 16px;
                font-size: 14px;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                background-color: #f8fafc;
                color: #0f172a;
                font-family: 'Consolas', monospace;
            }
            QLineEdit:focus {
                border: 2px solid #0ea5e9;
                background-color: white;
            }
            QLineEdit:hover {
                border: 2px solid #cbd5e1;
            }
        """)
        self.username_input.textChanged.connect(self.clear_validation_error)
        card_layout.addWidget(self.username_input)

        # Username error
        self.username_error = QLabel()
        self.username_error.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 500; font-family: 'Consolas', monospace;")
        self.username_error.hide()
        card_layout.addWidget(self.username_error)

        card_layout.addSpacing(10)

        # PASSWORD FIELD with EYE BUTTON
        pass_label = QLabel("PASSWORD")
        pass_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        pass_label.setStyleSheet("color: #475569; letter-spacing: 0.5px;")
        card_layout.addWidget(pass_label)

        # Password container
        pass_container = QHBoxLayout()
        pass_container.setSpacing(0)
        pass_container.setContentsMargins(0, 0, 0, 0)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password...")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(50)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 0 16px;
                font-size: 14px;
                border: 2px solid #e2e8f0;
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
                border-top-right-radius: 0;
                border-bottom-right-radius: 0;
                border-right: none;
                background-color: #f8fafc;
                color: #0f172a;
                font-family: 'Consolas', monospace;
            }
            QLineEdit:focus {
                border: 2px solid #0ea5e9;
                border-right: none;
                background-color: white;
            }
            QLineEdit:hover {
                border: 2px solid #cbd5e1;
                border-right: none;
            }
        """)
        self.password_input.returnPressed.connect(self.handle_login)
        self.password_input.textChanged.connect(self.clear_validation_error)
        pass_container.addWidget(self.password_input, stretch=1)

        # Eye Button - Technical style
        self.toggle_password_btn = QPushButton("👁")
        self.toggle_password_btn.setFixedWidth(50)
        self.toggle_password_btn.setFixedHeight(50)
        self.toggle_password_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_password_btn.setCheckable(True)
        self.toggle_password_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8fafc;
                border: 2px solid #e2e8f0;
                border-left: none;
                border-top-left-radius: 0;
                border-bottom-left-radius: 0;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                font-size: 18px;
                color: #64748b;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
                color: #0ea5e9;
                border-color: #cbd5e1;
            }
            QPushButton:checked {
                background-color: #e0f2fe;
                color: #0284c7;
                border-color: #0ea5e9;
            }
        """)
        self.toggle_password_btn.clicked.connect(self.toggle_password_visibility)
        pass_container.addWidget(self.toggle_password_btn)

        card_layout.addLayout(pass_container)

        # Password error
        self.password_error = QLabel()
        self.password_error.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 500; font-family: 'Consolas', monospace;")
        self.password_error.hide()
        card_layout.addWidget(self.password_error)

        # Options row
        options_layout = QHBoxLayout()
        
        self.remember_me_checkbox = QCheckBox("Remember Credentials")
        self.remember_me_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 12px;
                color: #64748b;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #cbd5e1;
            }
            QCheckBox::indicator:checked {
                background-color: #0ea5e9;
                border-color: #0ea5e9;
            }
        """)
        options_layout.addWidget(self.remember_me_checkbox)
        
        options_layout.addStretch()
        
        forgot_btn = QPushButton("Forgot Password?")
        forgot_btn.setFlat(True)
        forgot_btn.setCursor(Qt.PointingHandCursor)
        forgot_btn.setStyleSheet("""
            QPushButton {
                color: #0ea5e9;
                font-size: 12px;
                font-weight: 600;
                border: none;
                background: transparent;
                padding: 5px;
                font-family: 'Consolas', monospace;
            }
            QPushButton:hover {
                color: #0284c7;
                text-decoration: underline;
            }
        """)
        forgot_btn.clicked.connect(self.handle_forgot_password)
        options_layout.addWidget(forgot_btn)
        
        card_layout.addLayout(options_layout)

        # AUTHENTICATE Button - Technical/Industrial look
        login_btn = QPushButton("◈ AUTHENTICATE")
        login_btn.setFixedHeight(55)
        login_btn.setCursor(Qt.PointingHandCursor)
        login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0ea5e9, stop:1 #0284c7);
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                letter-spacing: 1px;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0284c7, stop:1 #0369a1);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0369a1, stop:1 #075985);
            }
        """)
        login_btn.clicked.connect(self.handle_login)
        card_layout.addWidget(login_btn)

        # Security footer in card
        security_note = QLabel("🔒 End-to-End Encrypted Connection")
        security_note.setAlignment(Qt.AlignCenter)
        security_note.setStyleSheet("color: #94a3b8; font-size: 11px; margin-top: 15px; font-family: 'Consolas', monospace;")
        card_layout.addWidget(security_note)

        main_layout.addWidget(login_card, alignment=Qt.AlignCenter)
        self.setLayout(main_layout)

    def toggle_password_visibility(self):
        """Toggle password visibility"""
        if self.toggle_password_btn.isChecked():
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.toggle_password_btn.setText("🙈")
            self.password_input.setStyleSheet("""
                QLineEdit {
                    padding: 0 16px;
                    font-size: 14px;
                    border: 2px solid #0ea5e9;
                    border-top-left-radius: 8px;
                    border-bottom-left-radius: 8px;
                    border-top-right-radius: 0;
                    border-bottom-right-radius: 0;
                    border-right: none;
                    background-color: white;
                    color: #0f172a;
                    font-family: 'Consolas', monospace;
                }
                QLineEdit:focus {
                    border: 2px solid #0284c7;
                    border-right: none;
                }
            """)
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.toggle_password_btn.setText("👁")
            self.password_input.setStyleSheet("""
                QLineEdit {
                    padding: 0 16px;
                    font-size: 14px;
                    border: 2px solid #e2e8f0;
                    border-top-left-radius: 8px;
                    border-bottom-left-radius: 8px;
                    border-top-right-radius: 0;
                    border-bottom-right-radius: 0;
                    border-right: none;
                    background-color: #f8fafc;
                    color: #0f172a;
                    font-family: 'Consolas', monospace;
                }
                QLineEdit:focus {
                    border: 2px solid #0ea5e9;
                    border-right: none;
                    background-color: white;
                }
                QLineEdit:hover {
                    border: 2px solid #cbd5e1;
                    border-right: none;
                }
            """)

    def clear_validation_error(self):
        """Clear validation errors"""
        sender = self.sender()
        if sender == self.username_input:
            self.username_error.hide()
            self.username_input.setStyleSheet("""
                QLineEdit {
                    padding: 0 16px;
                    font-size: 14px;
                    border: 2px solid #e2e8f0;
                    border-radius: 8px;
                    background-color: #f8fafc;
                    color: #0f172a;
                    font-family: 'Consolas', monospace;
                }
                QLineEdit:focus {
                    border: 2px solid #0ea5e9;
                    background-color: white;
                }
                QLineEdit:hover {
                    border: 2px solid #cbd5e1;
                }
            """)
        elif sender == self.password_input:
            self.password_error.hide()
            if self.toggle_password_btn.isChecked():
                self.password_input.setStyleSheet("""
                    QLineEdit {
                        padding: 0 16px;
                        font-size: 14px;
                        border: 2px solid #0ea5e9;
                        border-top-left-radius: 8px;
                        border-bottom-left-radius: 8px;
                        border-top-right-radius: 0;
                        border-bottom-right-radius: 0;
                        border-right: none;
                        background-color: white;
                        color: #0f172a;
                        font-family: 'Consolas', monospace;
                    }
                    QLineEdit:focus {
                        border: 2px solid #0284c7;
                        border-right: none;
                    }
                """)
            else:
                self.password_input.setStyleSheet("""
                    QLineEdit {
                        padding: 0 16px;
                        font-size: 14px;
                        border: 2px solid #e2e8f0;
                        border-top-left-radius: 8px;
                        border-bottom-left-radius: 8px;
                        border-top-right-radius: 0;
                        border-bottom-right-radius: 0;
                        border-right: none;
                        background-color: #f8fafc;
                        color: #0f172a;
                        font-family: 'Consolas', monospace;
                    }
                    QLineEdit:focus {
                        border: 2px solid #0ea5e9;
                        border-right: none;
                        background-color: white;
                    }
                    QLineEdit:hover {
                        border: 2px solid #cbd5e1;
                        border-right: none;
                    }
                """)

    def validate_inputs(self):
        """Validate inputs"""
        is_valid = True
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        error_style = """
            QLineEdit {
                padding: 0 16px;
                font-size: 14px;
                border: 2px solid #ef4444;
                border-radius: 8px;
                background-color: #fef2f2;
                color: #dc2626;
                font-family: 'Consolas', monospace;
            }
            QLineEdit:focus {
                border: 2px solid #dc2626;
                background-color: white;
            }
        """
        
        if self.toggle_password_btn.isChecked():
            pass_error_style = """
                QLineEdit {
                    padding: 0 16px;
                    font-size: 14px;
                    border: 2px solid #ef4444;
                    border-top-left-radius: 8px;
                    border-bottom-left-radius: 8px;
                    border-top-right-radius: 0;
                    border-bottom-right-radius: 0;
                    border-right: none;
                    background-color: #fef2f2;
                    color: #dc2626;
                    font-family: 'Consolas', monospace;
                }
                QLineEdit:focus {
                    border: 2px solid #dc2626;
                    border-right: none;
                    background-color: white;
                }
            """
        else:
            pass_error_style = error_style.replace("border-radius: 8px;", 
                "border-top-left-radius: 8px; border-bottom-left-radius: 8px; border-top-right-radius: 0; border-bottom-right-radius: 0; border-right: none;")

        if not username:
            self.username_error.setText("⚠ USERNAME REQUIRED")
            self.username_error.show()
            self.username_input.setStyleSheet(error_style)
            is_valid = False
        elif len(username) < 3:
            self.username_error.setText("⚠ INVALID USERNAME FORMAT")
            self.username_error.show()
            self.username_input.setStyleSheet(error_style)
            is_valid = False

        if not password:
            self.password_error.setText("⚠ PASSWORD REQUIRED")
            self.password_error.show()
            self.password_input.setStyleSheet(pass_error_style)
            is_valid = False
        elif len(password) < 4:
            self.password_error.setText("⚠ PASSWORD TOO SHORT")
            self.password_error.show()
            self.password_input.setStyleSheet(pass_error_style)
            is_valid = False

        return is_valid

    def load_remembered_credentials(self):
        """Load saved credentials"""
        if self.settings.value("remember_me", False, type=bool):
            saved_username = self.settings.value("username", "")
            if saved_username:
                self.username_input.setText(saved_username)
                self.remember_me_checkbox.setChecked(True)
                self.password_input.setFocus()

    def save_credentials(self, username):
        """Save credentials"""
        if self.remember_me_checkbox.isChecked():
            self.settings.setValue("remember_me", True)
            self.settings.setValue("username", username)
        else:
            self.settings.setValue("remember_me", False)
            self.settings.remove("username")

    def handle_forgot_password(self):
        """Handle forgot password"""
        username = self.username_input.text().strip()
        if not username:
            QMessageBox.information(self, "Password Recovery",
                "Please enter your username first to initiate recovery protocol.")
            return
        
        QMessageBox.information(self, "Password Recovery",
            f"Recovery instructions dispatched to associated secure channel.\n\nUsername: {username}\n\nContact System Administrator if not received within 5 minutes.")

    def handle_login(self):
        if not self.validate_inputs():
            return
        
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        # Authenticate user
        user = login(username, password)

        if not user:
            QMessageBox.critical(self, "Authentication Failed",
                "❌ Invalid credentials.\n\nAccess denied. Please verify Username and Password.")
            self.password_input.clear()
            self.password_input.setFocus()
            return

        # 👇 CRITICAL: Set the user in session
        session.login(
            user_id=user['id'],
            username=username,
            role=user['role']
        )

        # Save credentials if requested
        self.save_credentials(username)
        
        # Log session to database
        log_session(user["id"])

        # Check if network setup is required
        if not network_discovery.is_setup_complete():
            self.show_setup_wizard(user["role"])
        else:
            self.show_main_window(user["role"])

    def show_setup_wizard(self, role):
        """Show initial setup wizard"""
        from app.ui.pages.setup_wizard import SetupWizard
        
        self.wizard = SetupWizard(lambda: self.show_main_window(role))
        self.wizard.show()
        self.hide()

    def show_main_window(self, role):
        """Show main application window"""
        # Show success message
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Access Granted")
        msg_box.setText(f"✓ AUTHENTICATION SUCCESSFUL\n\nRole: {role}\n\nInitializing diagnostic interface...")
        msg_box.setIcon(QMessageBox.Information)
        
        # CRITICAL FIXES FOR VM/VIEW ISSUES:
        msg_box.setMinimumWidth(450)
        msg_box.setMaximumWidth(500)
        
        # Make it non-resizable
        msg_box.setWindowFlags(
            Qt.Dialog | 
            Qt.WindowTitleHint | 
            Qt.WindowCloseButtonHint
        )
        
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #f0f4f8;
                border: 2px solid #0ea5e9;
            }
            QLabel {
                color: #0f172a;
                font-size: 13px;
                font-family: 'Consolas', monospace;
                min-width: 350px;
                padding: 10px;
            }
            QPushButton {
                background-color: #0ea5e9;
                color: white;
                border: none;
                padding: 8px 24px;
                border-radius: 6px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #0284c7;
            }
        """)
        
        msg_box.exec()

        self.main_window = MainWindow(role)
        self.main_window.show()
        self.close()


def start_login():
    app = QApplication(sys.argv)
    
    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)
    
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())
