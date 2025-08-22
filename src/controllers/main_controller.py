#!/usr/bin/env python3
import datetime
from typing import List, Optional, Dict, Any
from PyQt6.QtWidgets import QTreeWidgetItem

from ..models.database import DatabaseManager
from ..models.subscription import SubscriptionData, Query
from ..models.config import AppConfig
from ..utils.logger import logger
from .api_controller import ApiController


class MainController:
    """Main controller coordinating between models and views"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.db_manager = DatabaseManager(
            config.database.db_path,
            config.database.backup_enabled,
            config.database.backup_count
        )
        self.subscription_data: Optional[SubscriptionData] = None
        self.current_filter: Optional[str] = None
        self.api_controller: Optional[ApiController] = None
        
        logger.info("Main controller initialized")
    
    def load_from_database(self) -> SubscriptionData:
        """Load subscription data from database"""
        logger.info("Loading subscription data from database")
        try:
            data_dict = self.db_manager.load_subscription_data()
            self.subscription_data = SubscriptionData.from_dict(data_dict)
            logger.info(f"Loaded {len(self.subscription_data.subscriptions)} subscriptions")
            return self.subscription_data
        except Exception as e:
            logger.error(f"Failed to load from database: {str(e)}")
            # Return empty data on error
            self.subscription_data = SubscriptionData([], 0, "Database Error")
            return self.subscription_data
    
    def create_api_controller(self) -> ApiController:
        """Create and return API controller"""
        self.api_controller = ApiController(self.db_manager, self.config.api)
        return self.api_controller
    
    def set_subscription_data(self, data_dict: dict) -> None:
        """Set subscription data from API response"""
        self.subscription_data = SubscriptionData.from_dict(data_dict)
    
    def create_api_backup(self) -> str:
        """Create a backup before API update"""
        return self.db_manager.create_api_backup()
    
    def get_api_backups(self) -> List:
        """Get list of available API backups"""
        return self.db_manager.get_api_backups()
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore database from backup"""
        success = self.db_manager.restore_from_backup(backup_path)
        if success:
            # Reload data after restore
            self.load_from_database()
        return success
    
    def cleanup_incompatible_backups(self) -> int:
        """Clean up incompatible backup files"""
        return self.db_manager.cleanup_incompatible_backups()
    
    def get_filtered_subscriptions(self) -> List:
        """Get subscriptions based on current filter"""
        if not self.subscription_data:
            return []
        
        if self.current_filter:
            filtered_sub = self.subscription_data.get_subscription_by_name(self.current_filter)
            return [filtered_sub] if filtered_sub else []
        
        return self.subscription_data.subscriptions
    
    def set_filter(self, subscription_name: Optional[str]) -> None:
        """Set the current subscription filter"""
        self.current_filter = subscription_name
    
    def get_all_queries_sorted(self) -> List[tuple[str, Query]]:
        """Get all queries sorted by priority"""
        if not self.subscription_data:
            return []
        
        subscriptions_to_show = self.get_filtered_subscriptions()
        all_queries = []
        
        for sub in subscriptions_to_show:
            for query in sub.queries:
                all_queries.append((sub.name, query))
        
        # Sort queries with three tiers:
        # 1. Normal queries (have last_file_time > 0) - sorted by last_file_time (oldest first)
        # 2. "Never" queries (last_file_time = 0) - at bottom but above acknowledged
        # 3. Acknowledged queries - at very bottom
        def sort_key(item):
            query = item[1]
            acknowledged = query.acknowledged
            last_file_time = query.last_file_time
            
            if acknowledged:
                return (2, last_file_time)  # Tier 2: Acknowledged (very bottom)
            elif last_file_time == 0:
                return (1, 0)  # Tier 1: Never files (bottom but above acknowledged)
            else:
                return (0, last_file_time)  # Tier 0: Normal files (top, oldest first)
        
        all_queries.sort(key=sort_key)
        return all_queries
    
    def acknowledge_queries(self, selected_items: List[QTreeWidgetItem], ack_days: int) -> int:
        """Acknowledge selected queries for specified number of days"""
        ack_until_timestamp = int(datetime.datetime.now().timestamp()) + (ack_days * 24 * 3600)
        updated_count = 0
        
        for item in selected_items:
            # Get query ID from the item data
            query_id = item.data(0, 257)  # Qt.ItemDataRole.UserRole + 1
            
            if query_id:
                if self.db_manager.update_query_acknowledgment(query_id, True, ack_until_timestamp):
                    updated_count += 1
            else:
                # Try to find query by matching text if ID not found
                query_text = item.text(2)  # Query Text column
                human_name = item.text(1)  # Human Name column
                subscription_name = item.text(0)  # Subscription column
                
                if self.db_manager.update_queries_by_text(
                    query_text, human_name, subscription_name, True, ack_until_timestamp
                ):
                    updated_count += 1
        
        return updated_count
    
    def unacknowledge_queries(self, selected_items: List[QTreeWidgetItem]) -> int:
        """Unacknowledge selected queries"""
        updated_count = 0
        
        for item in selected_items:
            # Get query ID from the item data
            query_id = item.data(0, 257)  # Qt.ItemDataRole.UserRole + 1
            
            if query_id:
                if self.db_manager.update_query_acknowledgment(query_id, False, 0):
                    updated_count += 1
            else:
                # Try to find query by matching text if ID not found
                query_text = item.text(2)  # Query Text column
                human_name = item.text(1)  # Human Name column
                subscription_name = item.text(0)  # Subscription column
                
                if self.db_manager.update_queries_by_text(
                    query_text, human_name, subscription_name, False, 0
                ):
                    updated_count += 1
        
        return updated_count
    
    def get_subscription_count(self) -> int:
        """Get total number of subscriptions"""
        return len(self.subscription_data.subscriptions) if self.subscription_data else 0
    
    def get_total_queries(self) -> int:
        """Get total number of queries"""
        return self.subscription_data.total_queries if self.subscription_data else 0
    
    def get_filtered_query_count(self) -> int:
        """Get number of queries in current filter"""
        subscriptions = self.get_filtered_subscriptions()
        return sum(sub.query_count for sub in subscriptions)
    
    def get_backup_files(self) -> List[Dict[str, Any]]:
        """Get list of available backup files"""
        return self.db_manager.get_backup_files()
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore database from backup file"""
        success = self.db_manager.restore_from_backup(backup_path)
        if success:
            # Reload data after restore
            self.load_from_database()
        return success
    
    def create_manual_backup(self) -> Optional[str]:
        """Create a manual backup of the database"""
        return self.db_manager.create_backup()