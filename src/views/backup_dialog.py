#!/usr/bin/env python3
"""Backup management dialog for Hydrus Sub Monitor"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                            QListWidgetItem, QPushButton, QLabel, QMessageBox,
                            QFileDialog)
from PyQt6.QtCore import Qt
from typing import List, Dict, Optional

from ..controllers.main_controller import MainController
from ..utils.logger import logger


class BackupDialog(QDialog):
    """Dialog for managing database backups"""
    
    def __init__(self, controller: MainController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Database Backups")
        self.setModal(True)
        self.resize(600, 400)
        
        self.setup_ui()
        self.refresh_backup_list()
    
    def setup_ui(self):
        """Setup the backup dialog UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Database Backup Management")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 5px;")
        layout.addWidget(title_label)
        
        # Backup list
        self.backup_list = QListWidget()
        self.backup_list.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.backup_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.create_backup_btn = QPushButton("Create Backup")
        self.create_backup_btn.clicked.connect(self.create_backup)
        
        self.restore_btn = QPushButton("Restore Selected")
        self.restore_btn.clicked.connect(self.restore_backup)
        self.restore_btn.setEnabled(False)
        
        self.import_btn = QPushButton("Import Backup...")
        self.import_btn.clicked.connect(self.import_backup)
        
        self.export_btn = QPushButton("Export Selected...")
        self.export_btn.clicked.connect(self.export_backup)
        self.export_btn.setEnabled(False)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_backup_list)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.create_backup_btn)
        button_layout.addWidget(self.restore_btn)
        button_layout.addWidget(self.import_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def refresh_backup_list(self):
        """Refresh the list of backup files"""
        self.backup_list.clear()
        
        backup_files = self.controller.get_backup_files()
        
        if not backup_files:
            item = QListWidgetItem("No backup files found")
            item.setFlags(Qt.ItemFlag.NoItemFlags)  # Make it non-selectable
            self.backup_list.addItem(item)
            return
        
        for backup_info in backup_files:
            # Format: filename - date - size
            size_mb = backup_info['size'] / (1024 * 1024)
            display_text = f"{backup_info['filename']} - {backup_info['created_str']} - {size_mb:.1f} MB"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, backup_info)
            self.backup_list.addItem(item)
    
    def on_selection_changed(self):
        """Handle selection change in backup list"""
        selected_items = self.backup_list.selectedItems()
        has_selection = len(selected_items) > 0 and selected_items[0].data(Qt.ItemDataRole.UserRole) is not None
        
        self.restore_btn.setEnabled(has_selection)
        self.export_btn.setEnabled(has_selection)
    
    def create_backup(self):
        """Create a new backup"""
        backup_path = self.controller.create_manual_backup()
        
        if backup_path:
            QMessageBox.information(self, "Backup Created", f"Backup created successfully:\n{backup_path}")
            self.refresh_backup_list()
        else:
            QMessageBox.warning(self, "Backup Failed", "Failed to create backup. Check logs for details.")
    
    def restore_backup(self):
        """Restore from selected backup"""
        selected_items = self.backup_list.selectedItems()
        if not selected_items:
            return
        
        backup_info = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if not backup_info:
            return
        
        # Confirm restore
        reply = QMessageBox.question(
            self, "Confirm Restore",
            f"Are you sure you want to restore from this backup?\n\n"
            f"File: {backup_info['filename']}\n"
            f"Date: {backup_info['created_str']}\n\n"
            f"This will replace your current database!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.controller.restore_from_backup(backup_info['path'])
            
            if success:
                QMessageBox.information(self, "Restore Complete", "Database restored successfully!")
                self.accept()  # Close dialog and refresh main window
            else:
                QMessageBox.warning(self, "Restore Failed", "Failed to restore backup. Check logs for details.")
    
    def import_backup(self):
        """Import a backup file from elsewhere"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Backup File", "", "Database Files (*.db);;All Files (*)"
        )
        
        if file_path:
            success = self.controller.restore_from_backup(file_path)
            
            if success:
                QMessageBox.information(self, "Import Complete", "Backup imported and restored successfully!")
                self.accept()  # Close dialog and refresh main window
            else:
                QMessageBox.warning(self, "Import Failed", "Failed to import backup. Check logs for details.")
    
    def export_backup(self):
        """Export selected backup to a chosen location"""
        selected_items = self.backup_list.selectedItems()
        if not selected_items:
            return
        
        backup_info = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if not backup_info:
            return
        
        # Choose export location
        export_path, _ = QFileDialog.getSaveFileName(
            self, "Export Backup", backup_info['filename'], "Database Files (*.db);;All Files (*)"
        )
        
        if export_path:
            try:
                import shutil
                shutil.copy2(backup_info['path'], export_path)
                QMessageBox.information(self, "Export Complete", f"Backup exported to:\n{export_path}")
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", f"Failed to export backup:\n{str(e)}")
                logger.error(f"Failed to export backup: {str(e)}")