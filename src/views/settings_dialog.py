#!/usr/bin/env python3
"""Settings dialog for Hydrus Sub Monitor configuration"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                            QWidget, QLabel, QLineEdit, QPushButton, QSpinBox,
                            QCheckBox, QGroupBox, QFormLayout, QMessageBox)
from PyQt6.QtCore import Qt
from typing import Optional

from ..models.config import AppConfig
from ..utils.validators import validate_api_key, validate_url, validate_timeout
from ..utils.logger import logger


class SettingsDialog(QDialog):
    """Configuration settings dialog"""
    
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(500, 400)
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup the settings dialog UI"""
        layout = QVBoxLayout(self)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # API settings tab
        self.api_tab = self.create_api_tab()
        self.tab_widget.addTab(self.api_tab, "API")
        
        # Database settings tab
        self.database_tab = self.create_database_tab()
        self.tab_widget.addTab(self.database_tab, "Database")
        
        # UI settings tab
        self.ui_tab = self.create_ui_tab()
        self.tab_widget.addTab(self.ui_tab, "Interface")
        
        layout.addWidget(self.tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("Test API Connection")
        self.test_button.clicked.connect(self.test_api_connection)
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.test_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def create_api_tab(self) -> QWidget:
        """Create API settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # API group
        api_group = QGroupBox("API Configuration")
        api_layout = QFormLayout(api_group)
        
        self.api_enabled_cb = QCheckBox("Enable API")
        api_layout.addRow("Status:", self.api_enabled_cb)
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("API Key:", self.api_key_edit)
        
        self.base_url_edit = QLineEdit()
        api_layout.addRow("Base URL:", self.base_url_edit)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 300)
        self.timeout_spin.setSuffix(" seconds")
        api_layout.addRow("Timeout:", self.timeout_spin)
        
        layout.addWidget(api_group)
        layout.addStretch()
        
        return widget
    
    def create_database_tab(self) -> QWidget:
        """Create database settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Database group
        db_group = QGroupBox("Database Configuration")
        db_layout = QFormLayout(db_group)
        
        self.db_path_edit = QLineEdit()
        db_layout.addRow("Database Path:", self.db_path_edit)
        
        self.backup_enabled_cb = QCheckBox("Enable Backups")
        db_layout.addRow("Backup:", self.backup_enabled_cb)
        
        self.backup_count_spin = QSpinBox()
        self.backup_count_spin.setRange(1, 20)
        db_layout.addRow("Backup Count:", self.backup_count_spin)
        
        layout.addWidget(db_group)
        layout.addStretch()
        
        return widget
    
    def create_ui_tab(self) -> QWidget:
        """Create UI settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # UI group
        ui_group = QGroupBox("Interface Configuration")
        ui_layout = QFormLayout(ui_group)
        
        self.default_ack_days_spin = QSpinBox()
        self.default_ack_days_spin.setRange(1, 365)
        self.default_ack_days_spin.setSuffix(" days")
        ui_layout.addRow("Default Ack Days:", self.default_ack_days_spin)
        
        self.auto_refresh_spin = QSpinBox()
        self.auto_refresh_spin.setRange(0, 3600)
        self.auto_refresh_spin.setSuffix(" seconds (0 = disabled)")
        ui_layout.addRow("Auto Refresh:", self.auto_refresh_spin)
        
        layout.addWidget(ui_group)
        layout.addStretch()
        
        return widget    
  
  def load_settings(self):
        """Load current settings into the dialog"""
        # API settings
        self.api_enabled_cb.setChecked(self.config.api.enabled)
        self.api_key_edit.setText(self.config.api.api_key)
        self.base_url_edit.setText(self.config.api.base_url)
        self.timeout_spin.setValue(self.config.api.timeout)
        
        # Database settings
        self.db_path_edit.setText(self.config.database.db_path)
        self.backup_enabled_cb.setChecked(self.config.database.backup_enabled)
        self.backup_count_spin.setValue(self.config.database.backup_count)
        
        # UI settings
        self.default_ack_days_spin.setValue(self.config.ui.default_ack_days)
        self.auto_refresh_spin.setValue(self.config.ui.auto_refresh_interval)
    
    def save_settings(self):
        """Save settings and close dialog"""
        # Validate inputs
        if not self.validate_inputs():
            return
        
        # Update config
        self.config.api.enabled = self.api_enabled_cb.isChecked()
        self.config.api.api_key = self.api_key_edit.text().strip()
        self.config.api.base_url = self.base_url_edit.text().strip()
        self.config.api.timeout = self.timeout_spin.value()
        
        self.config.database.db_path = self.db_path_edit.text().strip()
        self.config.database.backup_enabled = self.backup_enabled_cb.isChecked()
        self.config.database.backup_count = self.backup_count_spin.value()
        
        self.config.ui.default_ack_days = self.default_ack_days_spin.value()
        self.config.ui.auto_refresh_interval = self.auto_refresh_spin.value()
        
        # Save to file
        if self.config.save_to_file():
            logger.info("Settings saved successfully")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Failed to save settings to file")
    
    def validate_inputs(self) -> bool:
        """Validate all input fields"""
        # Validate API key if API is enabled
        if self.api_enabled_cb.isChecked():
            api_key = self.api_key_edit.text().strip()
            valid, error = validate_api_key(api_key)
            if not valid:
                QMessageBox.warning(self, "Invalid API Key", error)
                return False
            
            # Validate base URL
            base_url = self.base_url_edit.text().strip()
            valid, error = validate_url(base_url)
            if not valid:
                QMessageBox.warning(self, "Invalid URL", error)
                return False
            
            # Validate timeout
            timeout = self.timeout_spin.value()
            valid, error = validate_timeout(timeout)
            if not valid:
                QMessageBox.warning(self, "Invalid Timeout", error)
                return False
        
        # Validate database path
        db_path = self.db_path_edit.text().strip()
        if not db_path:
            QMessageBox.warning(self, "Invalid Database Path", "Database path cannot be empty")
            return False
        
        return True
    
    def test_api_connection(self):
        """Test the API connection with current settings"""
        if not self.api_enabled_cb.isChecked():
            QMessageBox.information(self, "API Disabled", "API is currently disabled")
            return
        
        # Validate inputs first
        api_key = self.api_key_edit.text().strip()
        valid, error = validate_api_key(api_key)
        if not valid:
            QMessageBox.warning(self, "Invalid API Key", error)
            return
        
        base_url = self.base_url_edit.text().strip()
        valid, error = validate_url(base_url)
        if not valid:
            QMessageBox.warning(self, "Invalid URL", error)
            return
        
        # Create temporary API config for testing
        from ..models.config import ApiConfig
        from ..controllers.api_controller import ApiController
        from ..models.database import DatabaseManager
        
        temp_config = ApiConfig(
            api_key=api_key,
            base_url=base_url,
            timeout=self.timeout_spin.value(),
            enabled=True
        )
        
        # Test connection
        temp_db = DatabaseManager()  # Temporary database manager
        api_controller = ApiController(temp_db, temp_config)
        
        success, error_msg = api_controller.test_connection()
        
        if success:
            QMessageBox.information(self, "Connection Test", "API connection successful!")
        else:
            QMessageBox.warning(self, "Connection Test Failed", f"Connection failed: {error_msg}")