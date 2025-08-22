#!/usr/bin/env python3
import sqlite3
import json
import datetime
import shutil
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

from ..utils.logger import logger


class DatabaseManager:
    def __init__(self, db_path: str = "hydrus_subscriptions.db", backup_enabled: bool = True, backup_count: int = 5):
        self.db_path = db_path
        self.backup_enabled = backup_enabled
        self.backup_count = backup_count
        self.backup_dir = Path("backups")
        self.api_backup_dir = Path("api_backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.api_backup_dir.mkdir(exist_ok=True)
        self.init_database()
    
    def init_database(self) -> None:
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create subscriptions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                gug_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create queries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscription_id INTEGER,
                query_text TEXT NOT NULL,
                human_name TEXT,
                display_name TEXT,
                last_check_time INTEGER,
                next_check_time INTEGER,
                next_check_status TEXT,
                paused BOOLEAN,
                dead BOOLEAN,
                checking_now BOOLEAN,
                can_check_now BOOLEAN,
                checker_status INTEGER,
                file_velocity_data TEXT,
                file_seed_cache_status TEXT,
                last_file_time INTEGER,
                acknowledged BOOLEAN DEFAULT 0,
                acknowledged_time INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subscription_id) REFERENCES subscriptions (id)
            )
        ''')
        
        # Add missing columns if they don't exist (for existing databases)
        self._add_missing_columns(cursor)
        
        conn.commit()
        conn.close()
    
    def _add_missing_columns(self, cursor: sqlite3.Cursor) -> None:
        """Add missing columns for database migration"""
        columns_to_add = [
            ("last_file_time", "INTEGER DEFAULT 0"),
            ("acknowledged", "BOOLEAN DEFAULT 0"),
            ("acknowledged_time", "INTEGER DEFAULT 0")
        ]
        
        for column_name, column_def in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE queries ADD COLUMN {column_name} {column_def}")
            except sqlite3.OperationalError:
                pass  # Column already exists
    
    def create_backup(self) -> Optional[str]:
        """Create a backup of the current database"""
        if not self.backup_enabled or not os.path.exists(self.db_path):
            return None
        
        try:
            # Create backup filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"hydrus_subscriptions_backup_{timestamp}.db"
            backup_path = self.backup_dir / backup_filename
            
            # Copy database file
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backup created: {backup_path}")
            
            # Clean up old backups
            self._cleanup_old_backups()
            
            return str(backup_path)
        except Exception as e:
            logger.error(f"Failed to create backup: {str(e)}")
            return None
    
    def _cleanup_old_backups(self):
        """Remove old backup files, keeping only the specified count"""
        try:
            # Get all backup files
            backup_files = list(self.backup_dir.glob("hydrus_subscriptions_backup_*.db"))
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Remove excess backups
            for backup_file in backup_files[self.backup_count:]:
                backup_file.unlink()
                logger.info(f"Removed old backup: {backup_file}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {str(e)}")
    
    def get_backup_files(self) -> List[Dict[str, Any]]:
        """Get list of available backup files with metadata"""
        backup_files = []
        
        try:
            for backup_file in self.backup_dir.glob("hydrus_subscriptions_backup_*.db"):
                stat = backup_file.stat()
                backup_info = {
                    'path': str(backup_file),
                    'filename': backup_file.name,
                    'size': stat.st_size,
                    'created': datetime.datetime.fromtimestamp(stat.st_mtime),
                    'created_str': datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                }
                backup_files.append(backup_info)
            
            # Sort by creation time (newest first)
            backup_files.sort(key=lambda x: x['created'], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get backup files: {str(e)}")
        
        return backup_files
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore database from a backup file"""
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Create a backup of current database before restoring
            current_backup = self.create_backup()
            if current_backup:
                logger.info(f"Current database backed up before restore: {current_backup}")
            
            # Copy backup file to current database location
            shutil.copy2(backup_path, self.db_path)
            logger.info(f"Database restored from backup: {backup_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore from backup: {str(e)}")
            return False

    def save_subscription_data(self, data: Dict[str, Any]) -> bool:
        """Save API data to database"""
        # Create backup before saving new data
        if self.backup_enabled:
            backup_path = self.create_backup()
            if backup_path:
                logger.info(f"Created backup before API update: {backup_path}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Clear existing data
            cursor.execute("DELETE FROM queries")
            cursor.execute("DELETE FROM subscriptions")
            
            subscriptions = data.get('subscriptions', [])
            
            for sub in subscriptions:
                # Insert subscription
                cursor.execute('''
                    INSERT INTO subscriptions (name, gug_name, updated_at)
                    VALUES (?, ?, ?)
                ''', (
                    sub.get('name', 'Unknown'),
                    sub.get('gug_name', ''),
                    datetime.datetime.now()
                ))
                
                sub_id = cursor.lastrowid
                
                # Insert queries for this subscription
                queries = sub.get('queries', [])
                for query in queries:
                    cursor.execute('''
                        INSERT INTO queries (
                            subscription_id, query_text, human_name, display_name,
                            last_check_time, next_check_time, next_check_status,
                            paused, dead, checking_now, can_check_now, checker_status,
                            file_velocity_data, file_seed_cache_status, last_file_time, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        sub_id,
                        query.get('query_text', ''),
                        query.get('human_name', ''),
                        query.get('display_name', ''),
                        query.get('last_check_time', 0),
                        query.get('next_check_time', 0),
                        query.get('next_check_status', ''),
                        query.get('paused', False),
                        query.get('dead', False),
                        query.get('checking_now', False),
                        query.get('can_check_now', False),
                        query.get('checker_status', 0),
                        json.dumps(query.get('file_velocity', [])),
                        query.get('file_seed_cache_status', ''),
                        query.get('last_file_time', 0),
                        datetime.datetime.now()
                    ))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def load_subscription_data(self) -> Dict[str, Any]:
        """Load subscription data from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get all subscriptions with their queries
            cursor.execute('''
                SELECT s.id, s.name, s.gug_name, s.updated_at,
                       q.id, q.query_text, q.human_name, q.display_name,
                       q.last_check_time, q.next_check_time, q.next_check_status,
                       q.paused, q.dead, q.checking_now, q.can_check_now,
                       q.checker_status, q.file_velocity_data, q.file_seed_cache_status, q.last_file_time,
                       q.acknowledged, q.acknowledged_time
                FROM subscriptions s
                LEFT JOIN queries q ON s.id = q.subscription_id
                ORDER BY s.name, q.query_text
            ''')
            
            rows = cursor.fetchall()
            
            # Group data by subscription
            subscriptions_dict = {}
            
            for row in rows:
                sub_id = row[0]
                if sub_id not in subscriptions_dict:
                    subscriptions_dict[sub_id] = {
                        'name': row[1],
                        'gug_name': row[2],
                        'queries': []
                    }
                
                # Add query if it exists (LEFT JOIN might have NULL queries)
                if row[5] is not None:  # query_text
                    query_data = {
                        'id': row[4],
                        'query_text': row[5],
                        'human_name': row[6],
                        'display_name': row[7],
                        'last_check_time': row[8],
                        'next_check_time': row[9],
                        'next_check_status': row[10],
                        'paused': bool(row[11]),
                        'dead': bool(row[12]),
                        'checking_now': bool(row[13]),
                        'can_check_now': bool(row[14]),
                        'checker_status': row[15],
                        'file_velocity': json.loads(row[16]) if row[16] else [],
                        'file_seed_cache_status': row[17],
                        'last_file_time': row[18],
                        'acknowledged': bool(row[19]) if row[19] is not None else False,
                        'acknowledged_time': row[20] if row[20] is not None else 0
                    }
                    subscriptions_dict[sub_id]['queries'].append(query_data)
            
            return {
                'subscriptions': list(subscriptions_dict.values()),
                'version': 80,  # Default version
                'hydrus_version': 'From Database'
            }
            
        except Exception as e:
            return {'subscriptions': [], 'version': 80, 'hydrus_version': 'Database Error'}
        finally:
            conn.close()
    
    def update_query_acknowledgment(self, query_id: int, acknowledged: bool, ack_time: int = 0) -> bool:
        """Update acknowledgment status for a specific query"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE queries SET acknowledged = ?, acknowledged_time = ? WHERE id = ?",
                (acknowledged, ack_time, query_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def update_queries_by_text(self, query_text: str, human_name: str, 
                              subscription_name: str, acknowledged: bool, ack_time: int = 0) -> bool:
        """Update acknowledgment status by matching query text"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE queries SET acknowledged = ?, acknowledged_time = ? 
                WHERE query_text = ? AND human_name = ? 
                AND subscription_id = (SELECT id FROM subscriptions WHERE name = ?)
            ''', (acknowledged, ack_time, query_text, human_name, subscription_name))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def create_api_backup(self) -> str:
        """Create a backup before API update in separate folder"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"api_backup_{timestamp}.db"
        backup_path = self.api_backup_dir / backup_filename
        
        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"API backup created: {backup_path}")
            
            # Clean up old API backups (keep last 10)
            self._cleanup_api_backups()
            
            return str(backup_path)
        except Exception as e:
            logger.error(f"Failed to create API backup: {str(e)}")
            raise
    
    def _cleanup_api_backups(self):
        """Clean up old API backups, keeping only the most recent 10"""
        try:
            backup_files = list(self.api_backup_dir.glob("api_backup_*.db"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Remove old backups beyond the limit
            for old_backup in backup_files[10:]:
                try:
                    old_backup.unlink()
                    logger.info(f"Removed old API backup: {old_backup}")
                except Exception as e:
                    logger.warning(f"Failed to remove old backup {old_backup}: {str(e)}")
        except Exception as e:
            logger.warning(f"Failed to cleanup API backups: {str(e)}")
    
    def get_api_backups(self) -> List[Dict[str, Any]]:
        """Get list of available API backups with metadata"""
        backups = []
        
        try:
            backup_files = list(self.api_backup_dir.glob("api_backup_*.db"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for backup_file in backup_files:
                try:
                    stat = backup_file.stat()
                    
                    # Try to get backup info
                    backup_info = self._get_backup_info(backup_file)
                    
                    backups.append({
                        'path': str(backup_file),
                        'filename': backup_file.name,
                        'created': datetime.datetime.fromtimestamp(stat.st_mtime),
                        'size': stat.st_size,
                        'subscription_count': backup_info.get('subscription_count', 0),
                        'query_count': backup_info.get('query_count', 0),
                        'compatible': backup_info.get('compatible', False)
                    })
                except Exception as e:
                    logger.warning(f"Failed to read backup info for {backup_file}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Failed to list API backups: {str(e)}")
            
        return backups
    
    def _get_backup_info(self, backup_path: Path) -> Dict[str, Any]:
        """Get information about a backup file"""
        try:
            conn = sqlite3.connect(str(backup_path))
            cursor = conn.cursor()
            
            # Check if tables exist (compatibility check)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            compatible = 'subscriptions' in tables and 'queries' in tables
            
            subscription_count = 0
            query_count = 0
            
            if compatible:
                cursor.execute("SELECT COUNT(*) FROM subscriptions")
                subscription_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM queries")
                query_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'compatible': compatible,
                'subscription_count': subscription_count,
                'query_count': query_count
            }
            
        except Exception as e:
            logger.warning(f"Failed to read backup info: {str(e)}")
            return {'compatible': False, 'subscription_count': 0, 'query_count': 0}
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore database from backup"""
        try:
            # Verify backup exists and is compatible
            backup_file = Path(backup_path)
            if not backup_file.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            backup_info = self._get_backup_info(backup_file)
            if not backup_info['compatible']:
                raise ValueError("Backup file is not compatible with current database schema")
            
            # Create a backup of current database before restore
            current_backup = f"{self.db_path}.restore_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(self.db_path, current_backup)
            logger.info(f"Created restore backup: {current_backup}")
            
            # Restore from backup
            shutil.copy2(backup_path, self.db_path)
            logger.info(f"Database restored from: {backup_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore from backup: {str(e)}")
            raise
    
    def cleanup_incompatible_backups(self):
        """Remove incompatible backup files"""
        try:
            backup_files = list(self.api_backup_dir.glob("api_backup_*.db"))
            removed_count = 0
            
            for backup_file in backup_files:
                try:
                    backup_info = self._get_backup_info(backup_file)
                    if not backup_info['compatible']:
                        backup_file.unlink()
                        logger.info(f"Removed incompatible backup: {backup_file}")
                        removed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to check/remove backup {backup_file}: {str(e)}")
            
            logger.info(f"Cleaned up {removed_count} incompatible backups")
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup incompatible backups: {str(e)}")
            return 0