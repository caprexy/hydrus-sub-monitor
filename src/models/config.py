#!/usr/bin/env python3
"""Configuration management for Hydrus Sub Monitor"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import json
import os
from pathlib import Path


@dataclass
class ApiConfig:
    """API configuration settings"""
    api_key: str = "80d06c01ec7f96ba3fcf22493acdccd0e899d2f87767c80e1bc46acaa0887eec"
    base_url: str = "http://127.0.0.1:45869"
    timeout: int = 10
    enabled: bool = True  # Enabled by default


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    db_path: str = "hydrus_subscriptions.db"
    backup_enabled: bool = True
    backup_count: int = 5


@dataclass
class UIConfig:
    """UI configuration settings"""
    default_ack_days: int = 30
    auto_refresh_interval: int = 0  # 0 = disabled
    window_geometry: Optional[bytes] = None
    column_widths: Dict[str, int] = field(default_factory=dict)


@dataclass
class AppConfig:
    """Main application configuration"""
    api: ApiConfig = field(default_factory=ApiConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    
    @classmethod
    def load_from_file(cls, config_path: str = "config.json") -> 'AppConfig':
        """Load configuration from JSON file"""
        if not os.path.exists(config_path):
            # Create default config file
            config = cls()
            config.save_to_file(config_path)
            return config
        
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            
            return cls(
                api=ApiConfig(**data.get('api', {})),
                database=DatabaseConfig(**data.get('database', {})),
                ui=UIConfig(**data.get('ui', {}))
            )
        except Exception:
            # Return default config if loading fails
            return cls()
    
    def save_to_file(self, config_path: str = "config.json") -> bool:
        """Save configuration to JSON file"""
        try:
            data = {
                'api': {
                    'api_key': self.api.api_key,
                    'base_url': self.api.base_url,
                    'timeout': self.api.timeout,
                    'enabled': self.api.enabled
                },
                'database': {
                    'db_path': self.database.db_path,
                    'backup_enabled': self.database.backup_enabled,
                    'backup_count': self.database.backup_count
                },
                'ui': {
                    'default_ack_days': self.ui.default_ack_days,
                    'auto_refresh_interval': self.ui.auto_refresh_interval,
                    'column_widths': self.ui.column_widths
                }
            }
            
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False
    
    @property
    def subscriptions_api_url(self) -> str:
        """Get the full subscriptions API URL"""
        return f"{self.api.base_url}/manage_subscriptions/get_subscriptions"