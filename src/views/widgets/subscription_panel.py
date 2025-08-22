#!/usr/bin/env python3
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                            QScrollArea, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import List, Optional

from ...models.subscription import Subscription


class SubscriptionPanel(QWidget):
    """Left panel containing subscription filter buttons"""
    
    subscription_selected = pyqtSignal(str)
    show_all_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setMaximumWidth(250)
        self.setMinimumWidth(200)
        self.current_filter: Optional[str] = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the subscription panel UI"""
        layout = QVBoxLayout(self)
        
        # Subscription selector label
        sub_label = QLabel("Subscriptions")
        sub_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 5px;")
        layout.addWidget(sub_label)
        
        # Scroll area for subscription buttons
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.subscription_buttons_widget = QWidget()
        self.subscription_buttons_layout = QVBoxLayout(self.subscription_buttons_widget)
        self.subscription_buttons_layout.setSpacing(2)
        
        scroll_area.setWidget(self.subscription_buttons_widget)
        layout.addWidget(scroll_area)
        
        # "Show All" button
        self.show_all_button = QPushButton("Show All Queries")
        self.show_all_button.setStyleSheet(
            "font-weight: bold; background-color: #e3f2fd; border: 2px solid #2196f3;"
        )
        self.show_all_button.clicked.connect(self.show_all_requested.emit)
        layout.addWidget(self.show_all_button) 
   
    def update_subscriptions(self, subscriptions: List[Subscription]):
        """Update the subscription buttons"""
        # Clear existing buttons
        for i in reversed(range(self.subscription_buttons_layout.count())):
            child = self.subscription_buttons_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Create button for each subscription
        for sub in subscriptions:
            query_count = sub.query_count
            
            button = QPushButton(f"{sub.name}\n({query_count} queries)")
            button.setMinimumHeight(50)
            button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px;
                    border: 1px solid #ccc;
                    background-color: #f9f9f9;
                }
                QPushButton:hover {
                    background-color: #e3f2fd;
                    border: 1px solid #2196f3;
                }
                QPushButton:pressed {
                    background-color: #bbdefb;
                }
            """)
            
            # Connect button to filter function
            button.clicked.connect(lambda checked, name=sub.name: self.subscription_selected.emit(name))
            self.subscription_buttons_layout.addWidget(button)
        
        # Add stretch to push buttons to top
        self.subscription_buttons_layout.addStretch()
    
    def set_active_filter(self, filter_name: Optional[str]):
        """Update button styles based on active filter"""
        self.current_filter = filter_name
        
        if filter_name is None:
            # Show all is active
            self.show_all_button.setStyleSheet(
                "font-weight: bold; background-color: #e3f2fd; border: 2px solid #2196f3;"
            )
        else:
            # Specific subscription is active
            self.show_all_button.setStyleSheet(
                "font-weight: normal; background-color: #f9f9f9; border: 1px solid #ccc;"
            )