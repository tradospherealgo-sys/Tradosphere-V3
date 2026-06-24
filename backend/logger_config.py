"""
Centralized Logging Configuration for Tradosphere V3.1
Provides structured logging with timestamps, levels, and Sentry integration
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Environment
ENV = os.getenv("FLASK_ENV", "development")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Log file path
LOG_FILE = LOGS_DIR / f"tradosphere_{datetime.now().strftime('%Y%m%d')}.log"
ERROR_LOG_FILE = LOGS_DIR / f"tradosphere_errors_{datetime.now().strftime('%Y%m%d')}.log"


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[41m',   # Red background
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        if ENV == 'development':
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logging():
    """Setup logging configuration for the application"""

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if ENV == 'development' else logging.INFO)

    # Remove default handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 1. Console Handler (for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if DEBUG else logging.INFO)

    console_formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 2. File Handler (for all logs)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=7  # Keep 7 days of logs
    )
    file_handler.setLevel(logging.DEBUG)

    file_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # 3. Error File Handler (only errors)
    error_handler = logging.handlers.RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=7
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)

    # 4. Sentry Integration (for production errors)
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_dsn = os.getenv("SENTRY_DSN")
        if sentry_dsn and ENV == "production":
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[
                    FlaskIntegration(),
                    SqlalchemyIntegration(),
                ],
                traces_sample_rate=0.1,
                environment=ENV,
                release=os.getenv("APP_VERSION", "3.1"),
                send_default_pii=False  # Don't send user data by default
            )
            root_logger.info("✅ Sentry error tracking initialized")
    except ImportError:
        pass  # Sentry not installed
    except Exception as e:
        root_logger.warning(f"Failed to initialize Sentry: {e}")

    root_logger.info(f"✅ Logging initialized | Environment: {ENV} | Level: {'DEBUG' if DEBUG else 'INFO'}")
    return root_logger


def get_logger(name):
    """Get a logger instance with the given name"""
    setup_logging()
    return logging.getLogger(name)


# Initialize logging when module is imported
logger = setup_logging()
