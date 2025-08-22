#!/usr/bin/env python3
import requests
from PyQt6.QtCore import QThread, pyqtSignal
from typing import Dict, Any, Optional
from ..models.database import DatabaseManager
from ..models.config import ApiConfig
from ..utils.logger import logger
from ..utils.validators import validate_api_key, validate_url


class ApiController(QThread):
    """Controller for handling Hydrus API communication"""
    
    data_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(str)
    
    def __init__(self, db_manager: DatabaseManager, api_config: ApiConfig):
        super().__init__()
        self.db_manager = db_manager
        self.api_config = api_config
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate API configuration"""
        valid, error = validate_api_key(self.api_config.api_key)
        if not valid:
            logger.error(f"Invalid API key: {error}")
        
        valid, error = validate_url(self.api_config.base_url)
        if not valid:
            logger.error(f"Invalid base URL: {error}")
    
    def run(self) -> None:
        """Fetch subscription data from Hydrus API"""
        logger.info("Starting API data fetch")
        self.progress_updated.emit("Connecting to Hydrus API...")
        
        try:
            headers = {"Hydrus-Client-API-Access-Key": self.api_config.api_key}
            api_url = f"{self.api_config.base_url}/manage_subscriptions/get_subscriptions"
            
            logger.info(f"API URL: {api_url}")
            logger.info(f"API Key: {self.api_config.api_key[:8]}...{self.api_config.api_key[-8:]}")
            logger.info(f"Timeout: {self.api_config.timeout}s")
            
            self.progress_updated.emit("Fetching subscription data...")
            logger.info("Sending GET request to Hydrus API...")
            
            response = requests.get(
                api_url, 
                headers=headers, 
                timeout=self.api_config.timeout
            )
            
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            if response.text:
                logger.info(f"Response content length: {len(response.text)} characters")
                if len(response.text) < 500:  # Log short responses completely
                    logger.info(f"Response content: {response.text}")
                else:
                    logger.info(f"Response content (first 200 chars): {response.text[:200]}...")
            
            if response.status_code == 200:
                self.progress_updated.emit("Processing response data...")
                logger.info("Successfully received 200 response, parsing JSON...")
                
                try:
                    data = response.json()
                    logger.info(f"JSON parsed successfully. Keys: {list(data.keys())}")
                    
                    if 'subscriptions' in data:
                        sub_count = len(data['subscriptions'])
                        logger.info(f"Found {sub_count} subscriptions in response")
                        
                        # Log first subscription for debugging
                        if sub_count > 0:
                            first_sub = data['subscriptions'][0]
                            logger.info(f"First subscription: {first_sub.get('name', 'Unknown')} with {len(first_sub.get('queries', []))} queries")
                    
                except Exception as json_error:
                    logger.error(f"Failed to parse JSON response: {str(json_error)}")
                    self.error_occurred.emit(f"Invalid JSON response: {str(json_error)}")
                    return
                
                # Validate response structure
                if not self._validate_response(data):
                    logger.error("Response validation failed")
                    self.error_occurred.emit("Invalid response format from API")
                    return
                
                self.progress_updated.emit("Saving to database...")
                logger.info("Attempting to save data to database...")
                
                # Save to database
                if self.db_manager.save_subscription_data(data):
                    total_queries = sum(len(sub.get('queries', [])) for sub in data.get('subscriptions', []))
                    logger.info(f"Successfully saved {len(data.get('subscriptions', []))} subscriptions with {total_queries} total queries to database")
                    self.data_received.emit(data)
                else:
                    logger.error("Database save operation failed")
                    self.error_occurred.emit("Failed to save data to database")
            else:
                error_msg = f"API returned status code: {response.status_code}"
                if response.status_code == 401:
                    error_msg += " (Invalid API key)"
                elif response.status_code == 403:
                    error_msg += " (Access forbidden - check API permissions)"
                elif response.status_code == 404:
                    error_msg += " (Endpoint not found - check Hydrus version)"
                
                logger.error(f"{error_msg}. Response: {response.text}")
                self.error_occurred.emit(error_msg)
                
        except requests.exceptions.ConnectionError as e:
            error_msg = "Could not connect to Hydrus client. Make sure it's running and API is enabled."
            logger.error(f"Connection error details: {str(e)}")
            logger.error(f"Attempted URL: {api_url}")
            self.error_occurred.emit(error_msg)
        except requests.exceptions.Timeout as e:
            error_msg = f"Request timed out after {self.api_config.timeout} seconds"
            logger.error(f"Timeout error details: {str(e)}")
            logger.error(f"Attempted URL: {api_url}")
            self.error_occurred.emit(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {str(e)}"
            logger.error(f"Request error details: {str(e)}")
            logger.error(f"Attempted URL: {api_url}")
            self.error_occurred.emit(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error details: {str(e)}")
            logger.error(f"Attempted URL: {api_url}")
            self.error_occurred.emit(error_msg)
    
    def _validate_response(self, data: Dict[str, Any]) -> bool:
        """Validate API response structure"""
        if not isinstance(data, dict):
            return False
        
        if 'subscriptions' not in data:
            return False
        
        if not isinstance(data['subscriptions'], list):
            return False
        
        return True
    
    def test_connection(self) -> tuple[bool, Optional[str]]:
        """Test if the API connection is working"""
        try:
            headers = {"Hydrus-Client-API-Access-Key": self.api_config.api_key}
            test_url = f"{self.api_config.base_url}/api_version"
            
            logger.info(f"Testing connection to: {test_url}")
            logger.info(f"Using API key: {self.api_config.api_key[:8]}...{self.api_config.api_key[-8:]}")
            
            response = requests.get(test_url, headers=headers, timeout=5)
            
            logger.info(f"Test connection response: {response.status_code}")
            logger.info(f"Test response content: {response.text}")
            
            if response.status_code == 200:
                return True, None
            elif response.status_code == 401:
                return False, "Invalid API key"
            elif response.status_code == 403:
                return False, "Access forbidden - check API permissions"
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False, "Cannot connect to Hydrus client"
        except requests.exceptions.Timeout as e:
            logger.error(f"Connection test timeout: {str(e)}")
            return False, "Connection timeout"
        except Exception as e:
            logger.error(f"Connection test error: {str(e)}")
            return False, f"Error: {str(e)}"