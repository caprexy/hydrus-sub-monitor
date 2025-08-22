#!/usr/bin/env python3
import sys
import requests
import json
import sqlite3
import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QTextEdit, QTreeWidget, 
                            QTreeWidgetItem, QSplitter, QMessageBox, QScrollArea, QFrame, QComboBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import QColor

class DatabaseManager:
    def __init__(self, db_path="hydrus_subscriptions.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
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
        try:
            cursor.execute("ALTER TABLE queries ADD COLUMN last_file_time INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE queries ADD COLUMN acknowledged BOOLEAN DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE queries ADD COLUMN acknowledged_time INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        
        conn.commit()
        conn.close()
    
    def save_subscription_data(self, data):
        """Save API data to database"""
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
    
    def load_subscription_data(self):
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

class ApiWorker(QThread):
    data_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, db_manager):
        super().__init__()
        self.api_key = "80d06c01ec7f96ba3fcf22493acdccd0e899d2f87767c80e1bc46acaa0887eec"
        self.db_manager = db_manager
    
    def run(self):
        try:
            headers = {"Hydrus-Client-API-Access-Key": self.api_key}
            response = requests.get(
                'http://127.0.0.1:45869/get_subscriptions',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                # Save to database
                self.db_manager.save_subscription_data(data)
                self.data_received.emit(data)
            else:
                self.error_occurred.emit(f"API returned status code: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            self.error_occurred.emit("Could not connect to Hydrus client. Make sure it's running and API is enabled.")
        except Exception as e:
            self.error_occurred.emit(f"Unexpected error: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hydrus Sub Monitor")
        
        # Initialize settings for window size persistence
        self.settings = QSettings("HydrusSubMonitor", "MainWindow")
        
        # Restore window geometry or set default
        self.restoreGeometry(self.settings.value("geometry", self.saveGeometry()))
        if not self.settings.value("geometry"):
            self.setGeometry(100, 100, 1200, 800)
        
        # Initialize database
        self.db_manager = DatabaseManager()
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        

        
        # Button layout
        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Update from API (Disabled)")
        self.refresh_button.setEnabled(False)  # Temporarily disabled
        self.refresh_button.clicked.connect(self.fetch_subscriptions)
        
        self.load_button = QPushButton("Load from Database")
        self.load_button.clicked.connect(self.load_from_database)
        
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.load_button)
        
        # Acknowledgment controls
        ack_label = QLabel("Ack Days:")
        self.ack_days_combo = QComboBox()
        self.ack_days_combo.addItems(["10", "30", "60", "90"])
        self.ack_days_combo.setCurrentText("30")  # Default to 30 days
        
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
        

        
        # Create main horizontal splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel for subscription buttons
        left_panel = QWidget()
        left_panel.setMaximumWidth(250)
        left_panel.setMinimumWidth(200)
        left_layout = QVBoxLayout(left_panel)
        
        # Subscription selector label
        sub_label = QLabel("Subscriptions")
        sub_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 5px;")
        left_layout.addWidget(sub_label)
        
        # Scroll area for subscription buttons
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.subscription_buttons_widget = QWidget()
        self.subscription_buttons_layout = QVBoxLayout(self.subscription_buttons_widget)
        self.subscription_buttons_layout.setSpacing(2)
        
        scroll_area.setWidget(self.subscription_buttons_widget)
        left_layout.addWidget(scroll_area)
        
        # "Show All" button
        self.show_all_button = QPushButton("Show All Queries")
        self.show_all_button.setStyleSheet("font-weight: bold; background-color: #e3f2fd; border: 2px solid #2196f3;")
        self.show_all_button.clicked.connect(self.show_all_queries)
        left_layout.addWidget(self.show_all_button)
        
        # Right panel for queries and log
        right_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Subscription tree (now shows flat list of queries)
        self.subscription_tree = QTreeWidget()
        self.subscription_tree.setHeaderLabels(["Subscription", "Human Name", "Query Text", "Last File Time", "Acknowledged", "Ack Until", "Last Check", "Next Check", "Next Check Status", "File Cache Status", "Paused", "Dead"])
        self.subscription_tree.setMinimumWidth(800)
        self.subscription_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        
        # Remove indentation since we're using it as a flat list, not a tree
        self.subscription_tree.setIndentation(0)
        # Hide the root decoration (expand/collapse arrows)
        self.subscription_tree.setRootIsDecorated(False)
        
        # Connect selection change to enable/disable buttons
        self.subscription_tree.itemSelectionChanged.connect(self.on_selection_changed)
        
        # Enable sorting
        self.subscription_tree.setSortingEnabled(True)
        # Set initial sort by Last File Time column (index 3) in ascending order (oldest first)
        self.subscription_tree.sortByColumn(3, Qt.SortOrder.AscendingOrder)
        
        # Log area
        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText("Log messages will appear here...")
        self.text_area.setMinimumWidth(300)
        
        right_splitter.addWidget(self.subscription_tree)
        right_splitter.addWidget(self.text_area)
        right_splitter.setSizes([700, 300])
        
        # Add panels to main splitter
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([200, 1000])
        
        # Store subscription data for filtering
        self.all_subscriptions_data = []
        self.current_filter = None
        
        # Add widgets to layout
        layout.addWidget(main_splitter)
        layout.addLayout(button_layout)
        
        self.api_worker = None
        
        # Load data from database on startup
        self.load_from_database()
    
    def fetch_subscriptions(self):
        if self.api_worker and self.api_worker.isRunning():
            return
            
        self.refresh_button.setEnabled(False)
        self.text_area.append("Fetching subscription data from Hydrus API...")
        
        self.api_worker = ApiWorker(self.db_manager)
        self.api_worker.data_received.connect(self.on_api_data_received)
        self.api_worker.error_occurred.connect(self.handle_api_error)
        self.api_worker.finished.connect(lambda: self.refresh_button.setEnabled(True))
        self.api_worker.start()
    
    def load_from_database(self):
        """Load subscription data from database"""
        try:
            self.text_area.append("Loading subscription data from database...")
            
            data = self.db_manager.load_subscription_data()
            self.display_subscriptions(data)
            
            if data['subscriptions']:
                self.text_area.append("Successfully loaded data from database")
            else:
                self.text_area.append("No data found in database - use 'Update from API' to fetch fresh data")
                
        except Exception as e:
            self.handle_api_error(f"Database error: {str(e)}")
    
    def on_api_data_received(self, data):
        """Handle data received from API (already saved to database)"""
        self.display_subscriptions(data)
        self.text_area.append("Data updated from API and saved to database")
    
    def create_subscription_buttons(self, subscriptions):
        """Create buttons for each subscription"""
        # Clear existing buttons
        for i in reversed(range(self.subscription_buttons_layout.count())):
            child = self.subscription_buttons_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Create button for each subscription
        for sub in subscriptions:
            sub_name = sub.get('name', 'Unknown')
            query_count = len(sub.get('queries', []))
            
            button = QPushButton(f"{sub_name}\n({query_count} queries)")
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
            button.clicked.connect(lambda checked, name=sub_name: self.filter_by_subscription(name))
            self.subscription_buttons_layout.addWidget(button)
        
        # Add stretch to push buttons to top
        self.subscription_buttons_layout.addStretch()
    
    def filter_by_subscription(self, subscription_name):
        """Filter queries to show only those from the specified subscription"""
        self.current_filter = subscription_name
        self.display_filtered_queries()
        
        # Update show all button style
        self.show_all_button.setStyleSheet("font-weight: normal; background-color: #f9f9f9; border: 1px solid #ccc;")
        
        # Update status
        filtered_count = sum(len(sub.get('queries', [])) for sub in self.all_subscriptions_data if sub.get('name') == subscription_name)
    
    def show_all_queries(self):
        """Show all queries from all subscriptions"""
        self.current_filter = None
        self.display_filtered_queries()
        
        # Update show all button style
        self.show_all_button.setStyleSheet("font-weight: bold; background-color: #e3f2fd; border: 2px solid #2196f3;")
        
        # Update status
        total_queries = sum(len(sub.get('queries', [])) for sub in self.all_subscriptions_data)
    
    def display_filtered_queries(self):
        """Display queries based on current filter"""
        # Disable sorting during data population
        self.subscription_tree.setSortingEnabled(False)
        self.subscription_tree.clear()
        
        subscriptions_to_show = self.all_subscriptions_data
        if self.current_filter:
            subscriptions_to_show = [sub for sub in self.all_subscriptions_data if sub.get('name') == self.current_filter]
        
        self.populate_query_table(subscriptions_to_show)
        
        # Keep sorting disabled to maintain our custom acknowledged-to-bottom order
        # Users can still manually sort by clicking headers if needed
        self.subscription_tree.setSortingEnabled(False)
    
    def get_orange_color_for_age(self, last_file_time, min_time, max_time):
        """Calculate orange color based on file age - darker orange for older files"""
        if last_file_time == 0:
            # Dead/never files get a neutral gray
            return QColor(240, 240, 240)
        
        if min_time == max_time:
            # All files have same timestamp, use medium orange
            return QColor(255, 220, 180)
        
        # Calculate age ratio (0 = newest, 1 = oldest)
        age_ratio = (max_time - last_file_time) / (max_time - min_time)
        
        # Orange gradient: newer files = light orange, older files = dark orange
        # Light orange: RGB(255, 240, 200) 
        # Dark orange: RGB(255, 140, 60)
        
        red = 255  # Keep red constant
        green = int(240 - (age_ratio * 100))  # 240 -> 140
        blue = int(200 - (age_ratio * 140))   # 200 -> 60
        
        return QColor(red, green, blue)

    def populate_query_table(self, subscriptions):
        """Populate the table with queries from given subscriptions"""
        # Collect all queries first to determine min/max last_file_time for color scaling
        all_queries = []
        for sub in subscriptions:
            sub_name = sub.get('name', 'Unknown')
            queries = sub.get('queries', [])
            for query in queries:
                all_queries.append((sub_name, query))
        
        # Debug: Print acknowledgment status before sorting
        for sub_name, query in all_queries:
            ack_status = query.get('acknowledged', False)
            query_text = query.get('query_text', 'Unknown')
            print(f"Query: {query_text}, Acknowledged: {ack_status}")
        
        # Sort queries with three tiers:
        # 1. Normal queries (have last_file_time > 0) - sorted by last_file_time (oldest first)
        # 2. "Never" queries (last_file_time = 0) - at bottom but above acknowledged
        # 3. Acknowledged queries - at very bottom
        def sort_key(item):
            query = item[1]
            acknowledged = query.get('acknowledged', False)
            last_file_time = query.get('last_file_time', 0)
            
            if acknowledged:
                return (2, last_file_time)  # Tier 2: Acknowledged (very bottom)
            elif last_file_time == 0:
                return (1, 0)  # Tier 1: Never files (bottom but above acknowledged)
            else:
                return (0, last_file_time)  # Tier 0: Normal files (top, oldest first)
        
        all_queries.sort(key=sort_key)
        
        # Debug: Print order after sorting
        print("After sorting:")
        for i, (sub_name, query) in enumerate(all_queries):
            ack_status = query.get('acknowledged', False)
            query_text = query.get('query_text', 'Unknown')
            print(f"{i}: {query_text}, Acknowledged: {ack_status}")
        
        # Find min and max last_file_time for color scaling ONLY from currently displayed queries (excluding 0/never and acknowledged)
        valid_times = [q[1].get('last_file_time', 0) for q in all_queries 
                      if q[1].get('last_file_time', 0) > 0 and not q[1].get('acknowledged', False)]
        if valid_times:
            min_time = min(valid_times)
            max_time = max(valid_times)
        else:
            min_time = max_time = 0
        
        row_index = 0
        now = int(datetime.datetime.now().timestamp())
        
        for sub_name, query in all_queries:
            # Format timestamps
            last_check = query.get('last_check_time', 0)
            next_check = query.get('next_check_time', 0)
            last_file = query.get('last_file_time', 0)
            
            last_check_str = "Never" if last_check == 0 else self.format_timestamp(last_check)
            next_check_str = "Never" if next_check == 0 else self.format_timestamp(next_check)
            last_file_str = "Never" if last_file == 0 else self.format_timestamp(last_file)
            
            # Format acknowledgment info
            acknowledged = query.get('acknowledged', False)
            ack_time = query.get('acknowledged_time', 0)
            
            ack_str = "Yes" if acknowledged else "No"
            if acknowledged and ack_time > 0:
                if ack_time > now:
                    ack_until_str = self.format_timestamp(ack_time)
                else:
                    ack_until_str = "Expired"
            else:
                ack_until_str = "N/A"
            
            query_item = QTreeWidgetItem([
                sub_name,                                                       # Subscription
                query.get('human_name', '') or query.get('query_text', ''),    # Human Name
                query.get('query_text', ''),                                   # Query Text
                last_file_str,                                                 # Last File Time
                ack_str,                                                       # Acknowledged
                ack_until_str,                                                 # Ack Until
                last_check_str,                                                # Last Check
                next_check_str,                                                # Next Check
                query.get('next_check_status', 'Unknown'),                     # Next Check Status
                query.get('file_seed_cache_status', ''),                       # File Cache Status
                "Yes" if query.get('paused', False) else "No",                # Paused
                "Yes" if query.get('dead', False) else "No"                   # Dead
            ])
            
            # Store query ID for acknowledgment operations
            query_id = query.get('id')
            query_item.setData(0, Qt.ItemDataRole.UserRole + 1, query_id)
            
            # Store acknowledgment status for custom sorting (acknowledged items should always be at bottom)
            sort_key = (1 if acknowledged else 0, last_file)  # Acknowledged=1 goes to bottom, then by last_file_time
            query_item.setData(0, Qt.ItemDataRole.UserRole + 2, sort_key)
            
            # Debug: Also store in a tooltip for verification
            query_item.setToolTip(0, f"Query ID: {query_id}, Ack: {acknowledged}")
            
            # Set raw timestamp data for proper sorting
            query_item.setData(3, Qt.ItemDataRole.UserRole, last_file)   # Last File Time
            query_item.setData(6, Qt.ItemDataRole.UserRole, last_check)  # Last Check
            query_item.setData(7, Qt.ItemDataRole.UserRole, next_check)  # Next Check
            
            # Color code based on status and last file time
            if acknowledged and (ack_time == 0 or ack_time > now):
                # Acknowledged queries get green color
                final_color = QColor(200, 255, 200)  # Light green
            elif query.get('dead', False):
                # Dead queries get red color
                final_color = QColor(255, 200, 200)  # Light red
            elif query.get('paused', False):
                # Paused queries get gray color
                final_color = QColor(230, 230, 230)  # Light gray
            else:
                # Active queries get orange gradient based on last file time
                final_color = self.get_orange_color_for_age(last_file, min_time, max_time)
            
            for col in range(12):  # Updated to 12 columns
                query_item.setBackground(col, final_color)
            
            self.subscription_tree.addTopLevelItem(query_item)
            row_index += 1
        
        # Resize columns
        for i in range(12):
            self.subscription_tree.resizeColumnToContents(i)

    def display_subscriptions(self, data):
        try:
            subscriptions = data.get('subscriptions', [])
            hydrus_version = data.get('hydrus_version', 'Unknown')
            
            # Store data for filtering
            self.all_subscriptions_data = subscriptions
            
            # Create subscription buttons
            self.create_subscription_buttons(subscriptions)
            
            total_queries = sum(len(sub.get('queries', [])) for sub in subscriptions)
            self.text_area.append(f"Successfully loaded {len(subscriptions)} subscriptions with {total_queries} total queries")
            
            # Show all queries by default
            self.show_all_queries()
            

            
        except Exception as e:
            self.handle_api_error(f"Error parsing subscription data: {str(e)}")
    
    def format_timestamp(self, timestamp):
        """Convert Unix timestamp to readable format"""
        try:
            import datetime
            dt = datetime.datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M")
        except:
            return str(timestamp)
    
    def handle_api_error(self, error_message):
        self.text_area.append(f"ERROR: {error_message}")
        
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("API Error")
        msg_box.setText(error_message)
        msg_box.exec()
    
    def on_selection_changed(self):
        """Enable/disable acknowledge buttons based on selection"""
        selected_items = self.subscription_tree.selectedItems()
        has_selection = len(selected_items) > 0
        self.ack_button.setEnabled(has_selection)
        self.unack_button.setEnabled(has_selection)
    
    def acknowledge_selected(self):
        """Acknowledge selected queries"""
        selected_items = self.subscription_tree.selectedItems()
        if not selected_items:
            self.text_area.append("No items selected for acknowledgment")
            return
        
        ack_days = int(self.ack_days_combo.currentText())
        ack_until_timestamp = int(datetime.datetime.now().timestamp()) + (ack_days * 24 * 3600)
        
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        try:
            updated_count = 0
            for item in selected_items:
                # Get query ID from the item data
                query_id = item.data(0, Qt.ItemDataRole.UserRole + 1)
                self.text_area.append(f"Processing item with query_id: {query_id}")
                
                if query_id:
                    cursor.execute(
                        "UPDATE queries SET acknowledged = 1, acknowledged_time = ? WHERE id = ?",
                        (ack_until_timestamp, query_id)
                    )
                    if cursor.rowcount > 0:
                        updated_count += 1
                        self.text_area.append(f"Updated query ID {query_id} in database")
                    else:
                        self.text_area.append(f"No rows updated for query ID {query_id}")
                else:
                    # Try to find query by matching text if ID not found
                    query_text = item.text(2)  # Query Text column
                    human_name = item.text(1)  # Human Name column
                    subscription_name = item.text(0)  # Subscription column
                    
                    cursor.execute('''
                        UPDATE queries SET acknowledged = 1, acknowledged_time = ? 
                        WHERE query_text = ? AND human_name = ? 
                        AND subscription_id = (SELECT id FROM subscriptions WHERE name = ?)
                    ''', (ack_until_timestamp, query_text, human_name, subscription_name))
                    
                    if cursor.rowcount > 0:
                        updated_count += 1
                        self.text_area.append(f"Updated by text match: {query_text}")
            
            conn.commit()
            self.text_area.append(f"Successfully acknowledged {updated_count} queries for {ack_days} days")
            
            # Reload data from database and refresh display
            data = self.db_manager.load_subscription_data()
            self.all_subscriptions_data = data.get('subscriptions', [])
            self.display_filtered_queries()
            
        except Exception as e:
            conn.rollback()
            self.text_area.append(f"Error acknowledging queries: {str(e)}")
            import traceback
            self.text_area.append(f"Traceback: {traceback.format_exc()}")
        finally:
            conn.close()
    
    def unacknowledge_selected(self):
        """Unacknowledge selected queries"""
        selected_items = self.subscription_tree.selectedItems()
        if not selected_items:
            self.text_area.append("No items selected for unacknowledgment")
            return
        
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        try:
            updated_count = 0
            for item in selected_items:
                # Get query ID from the item data
                query_id = item.data(0, Qt.ItemDataRole.UserRole + 1)
                
                if query_id:
                    cursor.execute(
                        "UPDATE queries SET acknowledged = 0, acknowledged_time = 0 WHERE id = ?",
                        (query_id,)
                    )
                    updated_count += 1
                else:
                    # Try to find query by matching text if ID not found
                    query_text = item.text(2)  # Query Text column
                    human_name = item.text(1)  # Human Name column
                    subscription_name = item.text(0)  # Subscription column
                    
                    cursor.execute('''
                        UPDATE queries SET acknowledged = 0, acknowledged_time = 0 
                        WHERE query_text = ? AND human_name = ? 
                        AND subscription_id = (SELECT id FROM subscriptions WHERE name = ?)
                    ''', (query_text, human_name, subscription_name))
                    
                    if cursor.rowcount > 0:
                        updated_count += 1
            
            conn.commit()
            self.text_area.append(f"Successfully unacknowledged {updated_count} queries")
            
            # Reload data from database and refresh display
            data = self.db_manager.load_subscription_data()
            self.all_subscriptions_data = data.get('subscriptions', [])
            self.display_filtered_queries()
            
        except Exception as e:
            conn.rollback()
            self.text_area.append(f"Error unacknowledging queries: {str(e)}")
            import traceback
            self.text_area.append(f"Traceback: {traceback.format_exc()}")
        finally:
            conn.close()


    def on_selection_changed(self):
        """Handle selection change in the tree widget"""
        selected_items = self.subscription_tree.selectedItems()
        has_selection = len(selected_items) > 0
        
        # Enable/disable acknowledgment buttons based on selection
        self.ack_button.setEnabled(has_selection)
        self.unack_button.setEnabled(has_selection)
    
    def closeEvent(self, event):
        """Save window geometry when closing"""
        self.settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()