# Hydrus Sub Monitor

A PyQt6 application for monitoring Hydrus subscription queries with a clean MVC architecture.

## Features

- **MVC Architecture**: Clean separation of concerns with Models, Views, and Controllers
- **Configuration Management**: JSON-based configuration with validation
- **Logging**: Comprehensive logging to file and console
- **Settings Dialog**: User-friendly configuration interface
- **API Integration**: Connect to Hydrus client API (optional)
- **Database Storage**: SQLite database for persistent data
- **Query Management**: Acknowledge/unacknowledge queries with time limits
- **Color-coded Display**: Visual indicators for query status and age
- **Filtering**: Filter queries by subscription

## Architecture

### Models (`src/models/`)
- `config.py`: Configuration management with validation
- `database.py`: Database operations and schema management
- `subscription.py`: Data models for subscriptions and queries

### Views (`src/views/`)
- `main_window.py`: Main application window
- `settings_dialog.py`: Configuration settings dialog
- `widgets/`: Reusable UI components
  - `subscription_panel.py`: Subscription filter panel
  - `query_tree.py`: Query display tree widget

### Controllers (`src/controllers/`)
- `main_controller.py`: Main application logic coordinator
- `api_controller.py`: Hydrus API communication

### Utils (`src/utils/`)
- `formatters.py`: Data formatting utilities
- `logger.py`: Centralized logging
- `validators.py`: Input validation functions

## Installation

1. Install Python 3.8+ and PyQt6:
   ```bash
   pip install PyQt6 requests
   ```

2. Run the application:
   ```bash
   python app.py
   ```

## Configuration

The application creates a `config.json` file on first run with default settings:

```json
{
  "api": {
    "api_key": "your_hydrus_api_key_here",
    "base_url": "http://127.0.0.1:45869",
    "timeout": 10,
    "enabled": false
  },
  "database": {
    "db_path": "hydrus_subscriptions.db",
    "backup_enabled": true,
    "backup_count": 5
  },
  "ui": {
    "default_ack_days": 30,
    "auto_refresh_interval": 0,
    "column_widths": {}
  }
}
```

### API Configuration

1. Enable API in Hydrus client
2. Get your API key from Hydrus
3. Open Settings dialog (File → Settings)
4. Enter your API key and enable API
5. Test connection before saving

## Usage

### Basic Operations

- **Load from Database**: Load previously saved subscription data
- **Update from API**: Fetch fresh data from Hydrus (requires API setup)
- **Filter by Subscription**: Click subscription buttons to filter queries
- **Acknowledge Queries**: Select queries and set acknowledgment period
- **Sort Queries**: Custom sorting with acknowledged queries at bottom

### Query Status Colors

- **Green**: Acknowledged queries
- **Red**: Dead queries
- **Gray**: Paused queries
- **Orange Gradient**: Active queries (darker = older files)

### Acknowledgment System

Queries can be acknowledged for a specified number of days:
- Acknowledged queries are moved to the bottom of the list
- Green highlighting indicates acknowledged status
- Acknowledgment expires automatically after the set period

## Development

### Adding New Features

1. **Models**: Add data structures in `src/models/`
2. **Views**: Create UI components in `src/views/`
3. **Controllers**: Add business logic in `src/controllers/`
4. **Utils**: Add helper functions in `src/utils/`

### Testing

Use the test data population script:
```bash
python populate_test_data.py
```

This creates sample subscriptions and queries for testing.

### Logging

Logs are written to `logs/app.log` with different levels:
- DEBUG: Detailed information for debugging
- INFO: General application flow
- WARNING: Potential issues
- ERROR: Error conditions
- CRITICAL: Serious errors

## File Structure

```
hydrus-sub-monitor/
├── app.py                          # Main application entry point
├── config.json                     # Configuration file (auto-generated)
├── hydrus_subscriptions.db         # SQLite database
├── populate_test_data.py           # Test data generation
├── logs/                           # Log files
│   └── app.log
└── src/
    ├── models/                     # Data models
    │   ├── config.py
    │   ├── database.py
    │   └── subscription.py
    ├── views/                      # User interface
    │   ├── main_window.py
    │   ├── settings_dialog.py
    │   └── widgets/
    │       ├── subscription_panel.py
    │       └── query_tree.py
    ├── controllers/                # Business logic
    │   ├── main_controller.py
    │   └── api_controller.py
    └── utils/                      # Utilities
        ├── formatters.py
        ├── logger.py
        └── validators.py
```

## License

This project is open source. Feel free to modify and distribute.