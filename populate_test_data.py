#!/usr/bin/env python3
"""
Test data population script for Hydrus Sub Monitor
Uses the MVC database model for consistency
"""
import sqlite3
import json
import datetime
import random

from src.models.database import DatabaseManager

def add_20_new_queries_and_update_times():
    """Add 20 new queries and update all last file times with random values"""
    
    # Use the MVC database manager
    db_manager = DatabaseManager()
    conn = sqlite3.connect(db_manager.db_path)
    cursor = conn.cursor()
    
    # Additional query templates for the new rows
    additional_queries = [
        {"query": "watercolor", "human": "Watercolor Art"},
        {"query": "steampunk", "human": "Steampunk Design"},
        {"query": "neon", "human": "Neon Aesthetics"},
        {"query": "retro", "human": "Retro Style"},
        {"query": "gothic", "human": "Gothic Art"},
        {"query": "pixel art", "human": "Pixel Art"},
        {"query": "oil painting", "human": "Oil Paintings"},
        {"query": "sketch", "human": "Sketches"},
        {"query": "graffiti", "human": "Graffiti Art"},
        {"query": "sculpture", "human": "Sculptures"},
        {"query": "tattoo", "human": "Tattoo Designs"},
        {"query": "comic", "human": "Comic Art"},
        {"query": "surreal", "human": "Surreal Art"},
        {"query": "geometric", "human": "Geometric Patterns"},
        {"query": "botanical", "human": "Botanical Art"},
        {"query": "industrial", "human": "Industrial Design"},
        {"query": "pastel", "human": "Pastel Colors"},
        {"query": "monochrome", "human": "Monochrome Art"},
        {"query": "texture", "human": "Texture Studies"},
        {"query": "lighting", "human": "Lighting Effects"}
    ]
    
    # Status messages for variety
    status_messages = [
        "checking in 2 hours 15 minutes",
        "paused, but would be imminent", 
        "paused, but would be in 30 minutes",
        "checking in 1 day 5 hours",
        "paused, but would be in 45 minutes",
        "checking in 6 hours 30 minutes",
        "paused, but would be in 2 hours",
        "checking in 12 hours",
        "paused, but would be in 1 hour 20 minutes",
        "checking in 3 days"
    ]
    
    # File velocity examples
    file_velocities = [
        [[50, 3600], "50 files in previous hour"],
        [[100, 7200], "100 files in previous 2 hours"],
        [[25, 1800], "25 files in previous 30 minutes"],
        [[200, 86400], "200 files in previous day"],
        [[0, 15552000], "no files yet"],
        [[75, 10800], "75 files in previous 3 hours"],
        [[150, 43200], "150 files in previous 12 hours"],
        [[10, 900], "10 files in previous 15 minutes"],
        [[300, 172800], "300 files in previous 2 days"],
        [[5, 300], "5 files in previous 5 minutes"]
    ]
    
    cache_statuses = [
        "45 successful, 2 ignored",
        "120 successful, 5 ignored, 1 failed", 
        "78 successful",
        "200 successful, 10 ignored",
        "15 successful, 1 ignored",
        "89 successful, 3 ignored",
        "156 successful, 8 ignored, 2 failed",
        "67 successful, 1 ignored",
        "234 successful, 15 ignored",
        ""
    ]
    
    try:
        # Get existing subscriptions to add queries to
        cursor.execute("SELECT id FROM subscriptions")
        subscription_ids = [row[0] for row in cursor.fetchall()]
        
        if not subscription_ids:
            print("No subscriptions found. Run populate_test_data() first.")
            return
        
        now = int(datetime.datetime.now().timestamp())
        
        # Add 20 new queries
        print("Adding 20 new queries...")
        for i in range(20):
            query_data = additional_queries[i]
            sub_id = random.choice(subscription_ids)
            
            # Generate realistic timestamps
            last_check = now - random.randint(3600, 86400 * 7)  # 1 hour to 7 days ago
            next_check = now + random.randint(1800, 86400 * 2)  # 30 min to 2 days from now
            
            # Random status
            is_paused = random.choice([True, False, False, False])  # 25% chance paused
            is_dead = random.choice([True, False, False, False, False, False])  # ~17% chance dead
            is_checking = random.choice([True, False, False, False, False])  # 20% chance checking
            
            # Generate last file time
            last_file_time = 0 if is_dead else random.randint(last_check, now)
            
            cursor.execute('''
                INSERT INTO queries (
                    subscription_id, query_text, human_name, display_name,
                    last_check_time, next_check_time, next_check_status,
                    paused, dead, checking_now, can_check_now, checker_status,
                    file_velocity_data, file_seed_cache_status, last_file_time, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sub_id,
                query_data["query"],
                query_data["human"],
                None,
                0 if is_dead else last_check,
                0 if is_dead else next_check,
                random.choice(status_messages),
                is_paused,
                is_dead,
                is_checking,
                not is_dead,
                random.randint(0, 3),
                json.dumps(random.choice(file_velocities)),
                random.choice(cache_statuses),
                last_file_time,
                datetime.datetime.now()
            ))
        
        # Now update ALL queries with new random last file times
        print("Updating all queries with new random last file times...")
        cursor.execute("SELECT id, last_check_time, dead FROM queries")
        all_queries = cursor.fetchall()
        
        for query_id, last_check_time, is_dead in all_queries:
            if is_dead:
                # Dead queries have no last file time
                last_file_time = 0
            else:
                # Generate completely random last file time
                if last_check_time and last_check_time > 0:
                    # Random time between last check and now
                    last_file_time = random.randint(last_check_time, now)
                else:
                    # Random recent time
                    last_file_time = now - random.randint(3600, 86400 * 7)  # 1 hour to 7 days ago
            
            cursor.execute(
                "UPDATE queries SET last_file_time = ? WHERE id = ?",
                (last_file_time, query_id)
            )
        
        conn.commit()
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM queries")
        total_queries = cursor.fetchone()[0]
        
        print(f"Successfully added 20 new queries!")
        print(f"Updated all {total_queries} queries with random last file times!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error adding queries and updating times: {e}")
    finally:
        conn.close()

def update_last_file_times():
    """Update existing queries with last file times without adding new items"""
    
    # Use the MVC database manager
    db_manager = DatabaseManager()
    conn = sqlite3.connect(db_manager.db_path)
    cursor = conn.cursor()
    
    try:
        # Get all existing queries
        cursor.execute("SELECT id, last_check_time, dead FROM queries")
        queries = cursor.fetchall()
        
        if not queries:
            print("No existing queries found. Run populate_test_data() first.")
            return
        
        now = int(datetime.datetime.now().timestamp())
        updated_count = 0
        
        for query_id, last_check_time, is_dead in queries:
            if is_dead:
                # Dead queries have no last file time
                last_file_time = 0
                print(f"Query {query_id}: Dead - setting last_file_time to 0")
            else:
                # Generate realistic last file time
                if last_check_time and last_check_time > 0:
                    # Random time between last check and now
                    last_file_time = random.randint(last_check_time, now)
                    print(f"Query {query_id}: Active - setting last_file_time to {last_file_time} (between {last_check_time} and {now})")
                else:
                    # If no last check time, generate something recent
                    last_file_time = now - random.randint(3600, 86400 * 7)  # 1 hour to 7 days ago
                    print(f"Query {query_id}: No last_check - setting last_file_time to {last_file_time}")
            
            cursor.execute(
                "UPDATE queries SET last_file_time = ? WHERE id = ?",
                (last_file_time, query_id)
            )
            updated_count += 1
        
        conn.commit()
        print(f"Successfully updated {updated_count} queries with last file times!")
        
        # Verify the updates
        cursor.execute("SELECT COUNT(*) FROM queries WHERE last_file_time > 0")
        non_zero_count = cursor.fetchone()[0]
        print(f"Queries with non-zero last_file_time: {non_zero_count}")
        
    except Exception as e:
        conn.rollback()
        print(f"Error updating last file times: {e}")
    finally:
        conn.close()

def populate_test_data():
    """Populate the database with test subscription data"""
    
    # Use the MVC database manager
    db_manager = DatabaseManager()
    conn = sqlite3.connect(db_manager.db_path)
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            gug_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
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
    
    # Clear existing data
    cursor.execute("DELETE FROM queries")
    cursor.execute("DELETE FROM subscriptions")
    
    # Test subscription data - exactly 4 subscriptions
    subscriptions_data = [
        {"name": "Anime Collection", "gug_name": "danbooru tag search"},
        {"name": "Photography", "gug_name": "flickr search"},
        {"name": "Digital Art", "gug_name": "deviantart search"},
        {"name": "Nature Photos", "gug_name": "unsplash search"}
    ]
    
    # Query templates with various realistic data
    query_templates = [
        {"query": "landscape", "human": "Beautiful Landscapes"},
        {"query": "portrait", "human": "Portrait Photography"},
        {"query": "anime girl", "human": "Anime Characters"},
        {"query": "cyberpunk", "human": "Cyberpunk Art"},
        {"query": "fantasy", "human": "Fantasy Artwork"},
        {"query": "nature", "human": "Nature Photography"},
        {"query": "abstract", "human": "Abstract Art"},
        {"query": "vintage", "human": "Vintage Style"},
        {"query": "minimalist", "human": "Minimalist Design"},
        {"query": "street art", "human": "Street Art"},
        {"query": "digital painting", "human": "Digital Paintings"},
        {"query": "black and white", "human": "B&W Photography"},
        {"query": "sunset", "human": "Sunset Photos"},
        {"query": "architecture", "human": "Architecture"},
        {"query": "macro", "human": "Macro Photography"},
        {"query": "space", "human": "Space Images"},
        {"query": "ocean", "human": "Ocean Photography"},
        {"query": "forest", "human": "Forest Scenes"},
        {"query": "city", "human": "City Photography"},
        {"query": "mountains", "human": "Mountain Landscapes"},
        {"query": "flowers", "human": "Flower Photography"},
        {"query": "animals", "human": "Animal Photos"},
        {"query": "cars", "human": "Car Photography"},
        {"query": "food", "human": "Food Photography"}
    ]
    
    # Status messages for variety
    status_messages = [
        "checking in 2 hours 15 minutes",
        "paused, but would be imminent",
        "paused, but would be in 30 minutes",
        "checking in 1 day 5 hours",
        "paused, but would be in 45 minutes",
        "checking in 6 hours 30 minutes",
        "paused, but would be in 2 hours",
        "checking in 12 hours",
        "paused, but would be in 1 hour 20 minutes",
        "checking in 3 days"
    ]
    
    # File velocity examples
    file_velocities = [
        [[50, 3600], "50 files in previous hour"],
        [[100, 7200], "100 files in previous 2 hours"],
        [[25, 1800], "25 files in previous 30 minutes"],
        [[200, 86400], "200 files in previous day"],
        [[0, 15552000], "no files yet"],
        [[75, 10800], "75 files in previous 3 hours"],
        [[150, 43200], "150 files in previous 12 hours"],
        [[10, 900], "10 files in previous 15 minutes"],
        [[300, 172800], "300 files in previous 2 days"],
        [[5, 300], "5 files in previous 5 minutes"]
    ]
    
    cache_statuses = [
        "45 successful, 2 ignored",
        "120 successful, 5 ignored, 1 failed",
        "78 successful",
        "200 successful, 10 ignored",
        "15 successful, 1 ignored",
        "89 successful, 3 ignored",
        "156 successful, 8 ignored, 2 failed",
        "67 successful, 1 ignored",
        "234 successful, 15 ignored",
        ""
    ]
    
    now = int(datetime.datetime.now().timestamp())
    
    try:
        # Insert subscriptions and their queries
        for i, sub_data in enumerate(subscriptions_data):
            # Insert subscription
            cursor.execute('''
                INSERT INTO subscriptions (name, gug_name, updated_at)
                VALUES (?, ?, ?)
            ''', (
                sub_data["name"],
                sub_data["gug_name"],
                datetime.datetime.now()
            ))
            
            sub_id = cursor.lastrowid
            
            # Add exactly 5 queries per subscription
            num_queries = 5
            used_queries = set()
            
            for j in range(num_queries):
                # Pick a unique query for this subscription
                while True:
                    query_template = random.choice(query_templates)
                    if query_template["query"] not in used_queries:
                        used_queries.add(query_template["query"])
                        break
                
                # Generate realistic timestamps
                last_check = now - random.randint(3600, 86400 * 7)  # 1 hour to 7 days ago
                next_check = now + random.randint(1800, 86400 * 2)  # 30 min to 2 days from now
                
                # Random status
                is_paused = random.choice([True, False, False, False])  # 25% chance paused
                is_dead = random.choice([True, False, False, False, False, False])  # ~17% chance dead
                is_checking = random.choice([True, False, False, False, False])  # 20% chance checking
                
                # Generate last file time (some time between last check and now)
                last_file_time = 0 if is_dead else random.randint(last_check, now)
                
                cursor.execute('''
                    INSERT INTO queries (
                        subscription_id, query_text, human_name, display_name,
                        last_check_time, next_check_time, next_check_status,
                        paused, dead, checking_now, can_check_now, checker_status,
                        file_velocity_data, file_seed_cache_status, last_file_time,
                        acknowledged, acknowledged_time, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    sub_id,
                    query_template["query"],
                    query_template["human"],
                    None,
                    0 if is_dead else last_check,
                    0 if is_dead else next_check,
                    random.choice(status_messages),
                    is_paused,
                    is_dead,
                    is_checking,
                    not is_dead,
                    random.randint(0, 3),
                    json.dumps(random.choice(file_velocities)),
                    random.choice(cache_statuses),
                    last_file_time,
                    False,  # acknowledged
                    0,      # acknowledged_time
                    datetime.datetime.now()
                ))
        
        conn.commit()
        print(f"Successfully populated database with {len(subscriptions_data)} subscriptions and their queries!")
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM subscriptions")
        sub_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM queries")
        query_count = cursor.fetchone()[0]
        
        print(f"Database now contains:")
        print(f"  - {sub_count} subscriptions")
        print(f"  - {query_count} queries")
        
    except Exception as e:
        conn.rollback()
        print(f"Error populating database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Clearing database and creating fresh test data...")
    print("Creating 4 subscriptions with 5 queries each...")
    populate_test_data()