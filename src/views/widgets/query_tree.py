#!/usr/bin/env python3
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QAction
from typing import List, Tuple
import datetime

from ...models.subscription import Query
from ...utils.formatters import format_timestamp, get_color_for_age, get_status_color


class QueryTreeWidget(QTreeWidget):
    """Tree widget for displaying subscription queries"""
    
    selection_changed = pyqtSignal(bool)
    acknowledge_requested = pyqtSignal(list, int)  # selected_items, days
    acknowledge_default_requested = pyqtSignal(list)  # selected_items (use default days)
    unacknowledge_requested = pyqtSignal(list)     # selected_items
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the tree widget"""
        self.setHeaderLabels([
            "Subscription", "Human Name", "Query Text", "Last File Time", 
            "Acknowledged", "Ack Until", "Last Check", "Next Check", 
            "Next Check Status", "File Cache Status", "Paused", "Dead"
        ])
        self.setMinimumWidth(800)
        self.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        
        # Remove indentation since we're using it as a flat list, not a tree
        self.setIndentation(0)
        # Hide the root decoration (expand/collapse arrows)
        self.setRootIsDecorated(False)
        
        # Connect selection change
        self.itemSelectionChanged.connect(self._on_selection_changed)
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # Disable sorting to maintain custom order
        self.setSortingEnabled(False)
    
    def _on_selection_changed(self):
        """Handle internal selection change"""
        selected_items = self.selectedItems()
        self.selection_changed.emit(len(selected_items) > 0)
    
    def get_selected_items(self) -> List[QTreeWidgetItem]:
        """Get currently selected items"""
        return self.selectedItems()
    
    def populate_queries(self, queries: List[Tuple[str, Query]]):
        """Populate the tree with queries"""
        # Disable sorting during data population
        self.setSortingEnabled(False)
        self.clear()
        
        if not queries:
            return
        
        # Find min and max last_file_time for color scaling
        valid_times = [q[1].last_file_time for q in queries 
                      if q[1].last_file_time > 0 and not q[1].acknowledged]
        if valid_times:
            min_time = min(valid_times)
            max_time = max(valid_times)
        else:
            min_time = max_time = 0
        
        now = int(datetime.datetime.now().timestamp())
        
        for sub_name, query in queries:
            item = self._create_query_item(sub_name, query, now, min_time, max_time)
            self.addTopLevelItem(item)
        
        # Resize columns
        for i in range(12):
            self.resizeColumnToContents(i) 
   
    def _create_query_item(self, sub_name: str, query: Query, now: int, 
                          min_time: int, max_time: int) -> QTreeWidgetItem:
        """Create a tree widget item for a query"""
        # Format timestamps
        last_check_str = "Never" if query.last_check_time == 0 else format_timestamp(query.last_check_time)
        next_check_str = "Never" if query.next_check_time == 0 else format_timestamp(query.next_check_time)
        last_file_str = "Never" if query.last_file_time == 0 else format_timestamp(query.last_file_time)
        
        # Format acknowledgment info
        ack_str = "Yes" if query.acknowledged else "No"
        if query.acknowledged and query.acknowledged_time > 0:
            if query.acknowledged_time > now:
                ack_until_str = format_timestamp(query.acknowledged_time)
            else:
                ack_until_str = "Expired"
        else:
            ack_until_str = "N/A"
        
        # Create tree item
        query_item = QTreeWidgetItem([
            sub_name,                                           # Subscription
            query.human_name or query.query_text,              # Human Name
            query.query_text,                                  # Query Text
            last_file_str,                                     # Last File Time
            ack_str,                                           # Acknowledged
            ack_until_str,                                     # Ack Until
            last_check_str,                                    # Last Check
            next_check_str,                                    # Next Check
            query.next_check_status,                           # Next Check Status
            query.file_seed_cache_status,                      # File Cache Status
            "Yes" if query.paused else "No",                  # Paused
            "Yes" if query.dead else "No"                     # Dead
        ])
        
        # Store query ID for acknowledgment operations
        query_item.setData(0, Qt.ItemDataRole.UserRole + 1, query.id)
        
        # Store acknowledgment status for custom sorting
        sort_key = (1 if query.acknowledged else 0, query.last_file_time)
        query_item.setData(0, Qt.ItemDataRole.UserRole + 2, sort_key)
        
        # Set raw timestamp data for proper sorting
        query_item.setData(3, Qt.ItemDataRole.UserRole, query.last_file_time)   # Last File Time
        query_item.setData(6, Qt.ItemDataRole.UserRole, query.last_check_time)  # Last Check
        query_item.setData(7, Qt.ItemDataRole.UserRole, query.next_check_time)  # Next Check
        
        # Set colors
        final_color = get_status_color(query, query.acknowledged_time, now)
        if final_color is None:
            # Use age-based coloring for active queries
            final_color = get_color_for_age(query.last_file_time, min_time, max_time)
        
        for col in range(12):
            query_item.setBackground(col, final_color)
        
        return query_item
    
    def _show_context_menu(self, position):
        """Show context menu at the given position"""
        item = self.itemAt(position)
        if not item:
            return
        
        # Get selected items
        selected_items = self.selectedItems()
        if not selected_items:
            return
        
        # Create context menu
        menu = QMenu(self)
        
        # Quick acknowledge action (uses default days from dropdown)
        quick_ack_action = QAction("Acknowledge (default days)", self)
        quick_ack_action.triggered.connect(lambda: self.acknowledge_default_requested.emit(selected_items))
        menu.addAction(quick_ack_action)
        
        # Acknowledge submenu for specific days
        ack_menu = menu.addMenu("Acknowledge for...")
        
        # Acknowledge options
        ack_days_options = [10, 30, 60, 90]
        for days in ack_days_options:
            action = QAction(f"{days} days", self)
            action.triggered.connect(lambda checked, d=days: self.acknowledge_requested.emit(selected_items, d))
            ack_menu.addAction(action)
        
        menu.addSeparator()
        
        # Unacknowledge action
        unack_action = QAction("Unacknowledge", self)
        unack_action.triggered.connect(lambda: self.unacknowledge_requested.emit(selected_items))
        menu.addAction(unack_action)
        
        # Show menu
        menu.exec(self.mapToGlobal(position))