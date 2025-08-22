#!/usr/bin/env python3
"""Validation utilities for Hydrus Sub Monitor"""
import re
from typing import Optional, Tuple
from urllib.parse import urlparse


def validate_api_key(api_key: str) -> Tuple[bool, Optional[str]]:
    """Validate Hydrus API key format"""
    if not api_key:
        return False, "API key cannot be empty"
    
    if len(api_key) != 64:
        return False, "API key must be 64 characters long"
    
    if not re.match(r'^[a-f0-9]{64}$', api_key):
        return False, "API key must contain only lowercase hexadecimal characters"
    
    return True, None


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """Validate URL format"""
    if not url:
        return False, "URL cannot be empty"
    
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "URL must include scheme (http/https) and host"
        
        if parsed.scheme not in ['http', 'https']:
            return False, "URL scheme must be http or https"
        
        return True, None
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"


def validate_port(port: int) -> Tuple[bool, Optional[str]]:
    """Validate port number"""
    if not isinstance(port, int):
        return False, "Port must be an integer"
    
    if port < 1 or port > 65535:
        return False, "Port must be between 1 and 65535"
    
    return True, None


def validate_timeout(timeout: int) -> Tuple[bool, Optional[str]]:
    """Validate timeout value"""
    if not isinstance(timeout, int):
        return False, "Timeout must be an integer"
    
    if timeout < 1 or timeout > 300:
        return False, "Timeout must be between 1 and 300 seconds"
    
    return True, None


def validate_ack_days(days: int) -> Tuple[bool, Optional[str]]:
    """Validate acknowledgment days"""
    if not isinstance(days, int):
        return False, "Acknowledgment days must be an integer"
    
    if days < 1 or days > 365:
        return False, "Acknowledgment days must be between 1 and 365"
    
    return True, None