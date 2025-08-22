#!/usr/bin/env python3
"""API Backup restore dialog for Hydrus Sub Monitor"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTableWidget, QTableWidgetItem, 
                            QMessageBox, QHeaderView, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from typing import Optional, List, Dict, Any
import datetime

from ..utils.logger import logger


class BackupCleanupWorker(QThread):
    """Worker thread for cleaning up incompatible backups"""
    finished = pyqtSignal(int)  # Number of backups cleaned
    error = pyqtSignal(str)
    
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
    
    def run(self):
        try:
            cleaned_count = self.controller.cleanup_incompatible_backups()
            self.finished.emit(cleaned_count)
        except Exception as e:
            self.error.emit(str(e))


class ApiBackupDialog(QDialog):
    """Dialog for managing API backups"""
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.selected_backup = None
        
        self.setWindowTitle("Restore from API Backup")
        self.setModal(True)
        self.resize(800, 500)
        
        self.setup_ui()
        self.load_backups()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Info label
        info_label = QLabel(
            "Select an API backup to restore. This will replace your current data.\n"
            "A backup of your current data will be created before restoring."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Backup table
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(6)
        self.backup_table.setHorizontalHeaderLabels([
            "Date Created", "Subscriptions", "Queries", "Size", "Status", "Filename"
        ])
        
        # Make table read-only and single selection
        self.backup_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.backup_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.backup_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # Connect selection change
        self.backup_table.itemSelectionChanged.connect(self.on_selection_changed)
        
        # Auto-resize columns
        header = self.backup_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.backup_table)
        
        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cleanup_button = QPushButton("Clean Up Incompatible")
        self.cleanup_button.clicked.connect(self.cleanup_incompatible)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_backups)
        
        self.restore_button = QPushButton("Restore Selected")
        self.restore_button.clicked.connect(self.restore_backup)
        self.restore_button.setEnabled(False)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.cleanup_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addStretch()
        button_layout.addWidget(self.restore_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def load_backups(self):
        """Load and display available backups"""
        try:
            backups = self.controller.get_api_backups()
            
            self.backup_table.setRowCount(len(backups))
            
            for row, backup in enumerate(backups):
                # Date created
                date_item = QTableWidgetItem(backup['created'].strftime("%Y-%m-%d %H:%M:%S"))
                self.backup_table.setItem(row, 0, date_item)
                
                # Subscription count
                sub_count_item = QTableWidgetItem(str(backup['subscription_count']))
                self.backup_table.setItem(row, 1, sub_count_item)
                
                # Query count
                query_count_item = QTableWidgetItem(str(backup['query_count']))
                self.backup_table.setItem(row, 2, query_count_item)
                
                # File size
                size_mb = backup['size'] / (1024 * 1024)
                size_item = QTableWidgetItem(f"{size_mb:.1f} MB")
                self.backup_table.setItem(row, 3, size_item)
                
                # Status
                status = "Compatible" if backup['compatible'] else "Incompatible"
                status_item = QTableWidgetItem(status)
                if not backup['compatible']:
                    status_item.setBackground(Qt.GlobalColor.red)
                    status_item.setForeground(Qt.GlobalColor.white)
                self.backup_table.setItem(row, 4, status_item)
                
                # Filename
                filename_item = QTableWidgetItem(backup['filename'])
                self.backup_table.setItem(row, 5, filename_item)
                
                # Store backup data in first column for retrieval
                date_item.setData(Qt.ItemDataRole.UserRole, backup)
            
            if not backups:
                # Show message if no backups
                self.backup_table.setRowCount(1)
                no_backups_item = QTableWidgetItem("No API backups found")
                no_backups_item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.backup_table.setItem(0, 0, no_backups_item)
                self.backup_table.setSpan(0, 0, 1, 6)
                
        except Exception as e:
            logger.error(f"Failed to load backups: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load backups: {str(e)}")
    
    def on_selection_changed(self):
        """Handle backup selection change"""
        selected_rows = self.backup_table.selectionModel().selectedRows()
        
        if selected_rows and self.backup_table.rowCount() > 0:
            row = selected_rows[0].row()
            date_item = self.backup_table.item(row, 0)
            
            if date_item and date_item.data(Qt.ItemDataRole.UserRole):
                backup_data = date_item.data(Qt.ItemDataRole.UserRole)
                self.selected_backup = backup_data
                
                # Only enable restore for compatible backups
                self.restore_button.setEnabled(backup_data['compatible'])
            else:
                self.selected_backup = None
                self.restore_button.setEnabled(False)
        else:
            self.selected_backup = None
            self.restore_button.setEnabled(False)
    
    def restore_backup(self):
        """Restore from selected backup"""
        if not self.selected_backup:
            return
        
        # Confirm restore
        backup_date = self.selected_backup['created'].strftime("%Y-%m-%d %H:%M:%S")
        reply = QMessageBox.question(
            self,
            "Confirm Restore",
            f"Are you sure you want to restore from backup created on {backup_date}?\n\n"
            f"This backup contains:\n"
            f"• {self.selected_backup['subscription_count']} subscriptions\n"
            f"• {self.selected_backup['query_count']} queries\n\n"
            f"Your current data will be backed up before restoring.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Restore from backup
            success = self.controller.restore_from_backup(self.selected_backup['path'])
            
            if success:
                QMessageBox.information(
                    self,
                    "Restore Successful",
                    f"Database successfully restored from backup.\n\n"
                    f"Restored {self.selected_backup['subscription_count']} subscriptions "
                    f"and {self.selected_backup['query_count']} queries."
                )
                self.accept()
            else:
                QMessageBox.critical(self, "Restore Failed", "Failed to restore from backup.")
                
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            QMessageBox.critical(self, "Restore Failed", f"Failed to restore from backup:\n{str(e)}")
    
    def cleanup_incompatible(self):
        """Clean up incompatible backup files"""
        reply = QMessageBox.question(
            self,
            "Clean Up Incompatible Backups",
            "This will permanently delete all incompatible backup files.\n\n"
            "Are you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Disable buttons and show progress
        self.cleanup_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.restore_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Start cleanup worker
        self.cleanup_worker = BackupCleanupWorker(self.controller)
        self.cleanup_worker.finished.connect(self.on_cleanup_finished)
        self.cleanup_worker.error.connect(self.on_cleanup_error)
        self.cleanup_worker.start()
    
    def on_cleanup_finished(self, cleaned_count: int):
        """Handle cleanup completion"""
        # Re-enable buttons and hide progress
        self.cleanup_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.restore_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        # Show result
        if cleaned_count > 0:
            QMessageBox.information(
                self,
                "Cleanup Complete",
                f"Successfully removed {cleaned_count} incompatible backup files."
            )
            # Refresh the backup list
            self.load_backups()
        else:
            QMessageBox.information(
                self,
                "Cleanup Complete",
                "No incompatible backup files found to remove."
            )
    
    def on_cleanup_error(self, error_message: str):
        """Handle cleanup error"""
        # Re-enable buttons and hide progress
        self.cleanup_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.restore_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        QMessageBox.critical(
            self,
            "Cleanup Failed",
            f"Failed to clean up incompatible backups:\n{error_message}"
        )