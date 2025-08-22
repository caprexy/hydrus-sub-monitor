#!/usr/bin/env python3
import datetime
from PyQt6.QtGui import QColor


def format_timestamp(timestamp: int) -> str:
    """Convert Unix timestamp to readable format"""
    try:
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError):
        return str(timestamp)


def get_color_for_age(last_file_time: int, min_time: int, max_time: int) -> QColor:
    """Calculate color based on file age - darker orange for older files"""
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


def get_status_color(query, ack_time: int, now: int) -> QColor:
    """Get color based on query status"""
    if query.acknowledged and (ack_time == 0 or ack_time > now):
        # Acknowledged queries get green color
        return QColor(200, 255, 200)  # Light green
    elif query.dead:
        # Dead queries get red color
        return QColor(255, 200, 200)  # Light red
    elif query.paused:
        # Paused queries get gray color
        return QColor(230, 230, 230)  # Light gray
    else:
        # Will use age-based coloring
        return None