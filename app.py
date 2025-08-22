#!/usr/bin/env python3
"""
Hydrus Sub Monitor - MVC Version
A PyQt6 application for monitoring Hydrus subscription queries
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication

from src.models.config import AppConfig
from src.views.main_window import MainWindow
from src.utils.logger import logger


def main():
    """Main application entry point"""
    # Set application metadata
    QCoreApplication.setApplicationName("Hydrus Sub Monitor")
    QCoreApplication.setApplicationVersion("2.0")
    QCoreApplication.setOrganizationName("HydrusSubMonitor")
    
    # Load configuration
    config = AppConfig.load_from_file()
    logger.info("Application starting")
    logger.info(f"API enabled: {config.api.enabled}")
    logger.info(f"Database path: {config.database.db_path}")
    
    app = QApplication(sys.argv)
    
    # Create and show main window
    window = MainWindow(config)
    window.show()
    
    logger.info("Main window displayed")
    
    # Run the application
    try:
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Application crashed: {str(e)}")
        raise


if __name__ == "__main__":
    main()