#!/usr/bin/env python3
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QTextEdit, QTreeWidget, 
                            QTreeWidgetItem, QSplitter, QMessageBox, QScrollArea, QComboBox, QDialog)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QColor
from typing import List, Optional
import datetime

from ..controllers.main_controller import MainController
from ..models.config import AppConfig
from ..utils.logger import logger
from ..utils.formatters import format_timestamp, get_color_for_age, get_status_color
from .widgets.subscription_panel import SubscriptionPanel
from .widgets.query_tree import QueryTreeWidget


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, config: Optional[AppConfig] = None):
        super().__init__()
        self.setWindowTitle("Hydrus Sub Monitor")
        
        # Load or use provided configuration
        self.config = config or AppConfig.load_from_file()
        
        # Initialize settings for window size persistence
        self.settings = QSettings("HydrusSubMonitor", "MainWindow")
        
        # Restore window geometry or set default
        self.restoreGeometry(self.settings.value("geometry", self.saveGeometry()))
        if not self.settings.value("geometry"):
            self.setGeometry(100, 100, 1200, 800)
        
        # Initialize MVC components
        self.controller = MainController(self.config)
        
        logger.info("Main window initialized")
        
        # Setup UI
        self.setup_ui()
        
        # Track subscription names to detect changes
        self._current_subscription_names = set()
        
        # Load data from database on startup
        self.load_initial_data()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Create menu bar
        self.create_menu_bar()
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create main horizontal splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel for subscription buttons
        self.subscription_panel = SubscriptionPanel()
        self.subscription_panel.subscription_selected.connect(self.filter_by_subscription)
        self.subscription_panel.show_all_requested.connect(self.show_all_queries)
        
        # Right panel for queries and log
        right_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Query tree widget
        self.query_tree = QueryTreeWidget()
        self.query_tree.selection_changed.connect(self.on_selection_changed)
        self.query_tree.acknowledge_requested.connect(self.acknowledge_queries_with_days)
        self.query_tree.acknowledge_default_requested.connect(self.acknowledge_queries_default)
        self.query_tree.unacknowledge_requested.connect(self.unacknowledge_queries_from_context)
        
        # Log area
        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText("Log messages will appear here...")
        self.text_area.setMinimumWidth(300)
        
        right_splitter.addWidget(self.query_tree)
        right_splitter.addWidget(self.text_area)
        right_splitter.setSizes([700, 300])
        
        # Add panels to main splitter
        main_splitter.addWidget(self.subscription_panel)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([200, 1000])
        
        # Button layout at bottom
        button_layout = self.create_button_layout()
        
        # Add widgets to layout
        layout.addWidget(main_splitter)
        layout.addLayout(button_layout)
    
    def create_menu_bar(self):
        """Create the application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        # Settings action
        settings_action = file_menu.addAction('Settings...')
        settings_action.triggered.connect(self.show_settings)
        
        file_menu.addSeparator()
        
        # Backup management action
        backup_action = file_menu.addAction('Manage Backups...')
        backup_action.triggered.connect(self.show_backup_dialog)
        
        # API backup restore action
        api_backup_action = file_menu.addAction('Restore from API Backup...')
        api_backup_action.triggered.connect(self.show_api_backup_dialog)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = file_menu.addAction('Exit')
        exit_action.triggered.connect(self.close)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        # About action
        about_action = help_menu.addAction('About')
        about_action.triggered.connect(self.show_about)
    
    def show_settings(self):
        """Show the settings dialog"""
        from .settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Settings were saved, update UI accordingly
            self.update_ui_from_config()
            logger.info("Settings updated")
    
    def show_backup_dialog(self):
        """Show the backup management dialog"""
        from .backup_dialog import BackupDialog
        
        dialog = BackupDialog(self.controller, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Backup was restored, refresh the display
            self.display_subscriptions()
            logger.info("Display refreshed after backup restore")
    
    def show_api_backup_dialog(self):
        """Show the API backup restore dialog"""
        from .api_backup_dialog import ApiBackupDialog
        
        dialog = ApiBackupDialog(self.controller, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Backup was restored, refresh the display
            self.display_subscriptions()
            # Update subscription names tracking
            self._current_subscription_names = {sub.name for sub in self.controller.subscription_data.subscriptions}
            logger.info("Display refreshed after backup restore")
    
    def show_about(self):
        """Show the about dialog"""
        QMessageBox.about(self, "About Hydrus Sub Monitor", 
                         "Hydrus Sub Monitor v2.0\n\n"
                         "A PyQt6 application for monitoring Hydrus subscription queries.\n"
                         "Built with MVC architecture for better maintainability.")
    
    def update_ui_from_config(self):
        """Update UI elements based on current configuration"""
        # Update API button
        api_button_text = "Update from API" if self.config.api.enabled else "Update from API (Disabled)"
        self.refresh_button.setText(api_button_text)
        self.refresh_button.setEnabled(self.config.api.enabled)
        
        # Update default ack days
        self.ack_days_combo.setCurrentText(str(self.config.ui.default_ack_days))
    
    def create_button_layout(self) -> QHBoxLayout:
        """Create the bottom button layout"""
        button_layout = QHBoxLayout()
        
        # API buttons
        api_button_text = "Update from API" if self.config.api.enabled else "Update from API (Disabled)"
        self.refresh_button = QPushButton(api_button_text)
        self.refresh_button.setEnabled(self.config.api.enabled)
        self.refresh_button.clicked.connect(self.fetch_subscriptions)
        
        button_layout.addWidget(self.refresh_button)
        
        # Acknowledgment controls
        ack_label = QLabel("Ack Days:")
        self.ack_days_combo = QComboBox()
        self.ack_days_combo.addItems(["10", "30", "60", "90"])
        self.ack_days_combo.setCurrentText(str(self.config.ui.default_ack_days))
        
        self.ack_button = QPushButton("Acknowledge Selected")
        self.ack_button.clicked.connect(self.acknowledge_selected)
        self.ack_button.setEnabled(False)
        
        self.unack_button = QPushButton("Unacknowledge Selected")
        self.unack_button.clicked.connect(self.unacknowledge_selected)
        self.unack_button.setEnabled(False)
        
        button_layout.addWidget(ack_label)
        button_layout.addWidget(self.ack_days_combo)
        button_layout.addWidget(self.ack_button)
        button_layout.addWidget(self.unack_button)
        button_layout.addStretch()
        
        return button_layout
    
    def fetch_subscriptions(self):
        """Fetch subscriptions from API with confirmation"""
        if not self.config.api.enabled:
            self.handle_api_error("API is disabled in configuration")
            return
            
        if hasattr(self, 'api_worker') and self.api_worker and self.api_worker.isRunning():
            return
        
        # Show confirmation dialog
        reply = QMessageBox.question(
            self, 
            "Update from API", 
            "This will fetch fresh data from Hydrus API and overwrite your current data.\n\n"
            "A backup will be created automatically before updating.\n\n"
            "Do you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Create backup before API update
        try:
            backup_path = self.controller.create_api_backup()
            self.text_area.append(f"Backup created: {backup_path}")
        except Exception as e:
            logger.error(f"Failed to create backup: {str(e)}")
            self.text_area.append(f"Warning: Failed to create backup: {str(e)}")
            
            # Ask if user wants to continue without backup
            reply = QMessageBox.question(
                self,
                "Backup Failed",
                "Failed to create backup before API update.\n\n"
                "Do you want to continue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
        self.refresh_button.setEnabled(False)
        self.text_area.append("Fetching subscription data from Hydrus API...")
        logger.info("Starting API fetch")
        
        # Create API controller
        self.api_worker = self.controller.create_api_controller()
        self.api_worker.data_received.connect(self.on_api_data_received)
        self.api_worker.error_occurred.connect(self.handle_api_error)
        self.api_worker.progress_updated.connect(self.on_progress_update)
        self.api_worker.finished.connect(lambda: self.refresh_button.setEnabled(True))
        self.api_worker.start()
    
    def on_progress_update(self, message: str):
        """Handle progress updates from API controller"""
        self.text_area.append(message)
    
    def load_initial_data(self):
        """Load subscription data from database on startup"""
        try:
            self.text_area.append("Loading subscription data from database...")
            
            subscription_data = self.controller.load_from_database()
            self.display_subscriptions()
            
            # Track current subscription names
            self._current_subscription_names = {sub.name for sub in subscription_data.subscriptions}
            
            if subscription_data.subscriptions:
                self.text_area.append("Successfully loaded data from database")
            else:
                self.text_area.append("No data found in database - use 'Update from API' to fetch fresh data")
                
        except Exception as e:
            self.handle_api_error(f"Database error: {str(e)}")
    
    def on_api_data_received(self, data):
        """Handle data received from API"""
        self.controller.set_subscription_data(data)
        
        # Check if subscription names changed
        new_subscription_names = {sub.name for sub in self.controller.subscription_data.subscriptions}
        
        if new_subscription_names != self._current_subscription_names:
            # Subscriptions changed - rebuild everything
            self.display_subscriptions()
            self._current_subscription_names = new_subscription_names
            self.text_area.append("Data updated from API with subscription changes")
        else:
            # Same subscriptions - only refresh queries to avoid moving buttons
            self.display_queries_only()
            self.text_area.append("Data updated from API (queries refreshed)")
        
        self.text_area.append("Data saved to database")
    
    def display_subscriptions(self):
        """Display subscription data in UI (full refresh including subscription panel)"""
        try:
            # Update subscription panel
            self.subscription_panel.update_subscriptions(self.controller.subscription_data.subscriptions)
            
            total_queries = self.controller.get_total_queries()
            subscription_count = self.controller.get_subscription_count()
            
            if subscription_count > 0:
                self.text_area.append(f"Successfully loaded {subscription_count} subscriptions with {total_queries} total queries")
            
            # Show all queries by default
            self.show_all_queries()
            
        except Exception as e:
            self.handle_api_error(f"Error displaying subscription data: {str(e)}")
    
    def display_queries_only(self):
        """Display only the query data without updating subscription panel"""
        try:
            # Just refresh the current filtered view
            self.display_filtered_queries()
            
        except Exception as e:
            self.handle_api_error(f"Error displaying queries: {str(e)}")
    
    def filter_by_subscription(self, subscription_name: str):
        """Filter queries to show only those from the specified subscription"""
        self.controller.set_filter(subscription_name)
        self.display_filtered_queries()
        
        # Update subscription panel styling
        self.subscription_panel.set_active_filter(subscription_name)
    
    def show_all_queries(self):
        """Show all queries from all subscriptions"""
        self.controller.set_filter(None)
        self.display_filtered_queries()
        
        # Update subscription panel styling
        self.subscription_panel.set_active_filter(None)
    
    def display_filtered_queries(self):
        """Display queries based on current filter"""
        all_queries = self.controller.get_all_queries_sorted()
        self.query_tree.populate_queries(all_queries)
    
    def on_selection_changed(self, has_selection: bool):
        """Handle selection change in query tree"""
        self.ack_button.setEnabled(has_selection)
        self.unack_button.setEnabled(has_selection)
    
    def acknowledge_selected(self):
        """Acknowledge selected queries"""
        selected_items = self.query_tree.get_selected_items()
        if not selected_items:
            return
        
        ack_days = int(self.ack_days_combo.currentText())
        updated_count = self.controller.acknowledge_queries(selected_items, ack_days)
        
        if updated_count > 0:
            self.text_area.append(f"Acknowledged {updated_count} queries for {ack_days} days")
            # Refresh only the query display, not the entire subscription data
            self.refresh_query_display()
        else:
            self.text_area.append("No queries were acknowledged")
    
    def unacknowledge_selected(self):
        """Unacknowledge selected queries"""
        selected_items = self.query_tree.get_selected_items()
        if not selected_items:
            return
        
        updated_count = self.controller.unacknowledge_queries(selected_items)
        
        if updated_count > 0:
            self.text_area.append(f"Unacknowledged {updated_count} queries")
            # Refresh only the query display, not the entire subscription data
            self.refresh_query_display()
        else:
            self.text_area.append("No queries were unacknowledged")
    
    def refresh_query_display(self):
        """Refresh the query display after acknowledge/unacknowledge operations"""
        try:
            # Reload data from database to get updated acknowledgment status
            self.controller.load_from_database()
            
            # Update the query tree, keeping the current filter
            self.display_filtered_queries()
            
            logger.info("Query display refreshed")
        except Exception as e:
            logger.error(f"Failed to refresh query display: {str(e)}")
            self.handle_api_error(f"Error refreshing display: {str(e)}")
    
    def acknowledge_queries_with_days(self, selected_items: List, ack_days: int):
        """Acknowledge queries from context menu with specific days"""
        if not selected_items:
            return
        
        updated_count = self.controller.acknowledge_queries(selected_items, ack_days)
        
        if updated_count > 0:
            self.text_area.append(f"Acknowledged {updated_count} queries for {ack_days} days")
            self.refresh_query_display()
        else:
            self.text_area.append("No queries were acknowledged")
    
    def acknowledge_queries_default(self, selected_items: List):
        """Acknowledge queries from context menu using default days from dropdown"""
        if not selected_items:
            return
        
        # Get the current value from the dropdown
        ack_days = int(self.ack_days_combo.currentText())
        updated_count = self.controller.acknowledge_queries(selected_items, ack_days)
        
        if updated_count > 0:
            self.text_area.append(f"Acknowledged {updated_count} queries for {ack_days} days (default)")
            self.refresh_query_display()
        else:
            self.text_area.append("No queries were acknowledged")
    
    def unacknowledge_queries_from_context(self, selected_items: List):
        """Unacknowledge queries from context menu"""
        if not selected_items:
            return
        
        updated_count = self.controller.unacknowledge_queries(selected_items)
        
        if updated_count > 0:
            self.text_area.append(f"Unacknowledged {updated_count} queries")
            self.refresh_query_display()
        else:
            self.text_area.append("No queries were unacknowledged")
    

    
    def handle_api_error(self, error_message: str):
        """Handle API errors"""
        self.text_area.append(f"ERROR: {error_message}")
        
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("API Error")
        msg_box.setText(error_message)
        msg_box.exec()
    
    def closeEvent(self, event):
        """Save window geometry on close"""
        self.settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)