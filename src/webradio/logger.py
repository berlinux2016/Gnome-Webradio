"""Centralized logging configuration for WebRadio Player"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
import sys


class WebRadioLogger:
    """Centralized logger for WebRadio application"""

    _instance: Optional['WebRadioLogger'] = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not WebRadioLogger._initialized:
            self._setup_logging()
            WebRadioLogger._initialized = True

    def _setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory
        log_dir = Path.home() / '.local' / 'share' / 'webradio' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / 'webradio.log'

        # Create root logger
        self.logger = logging.getLogger('webradio')
        self.logger.setLevel(logging.DEBUG)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Console handler (INFO and above)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)

        # File handler with rotation (DEBUG and above)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

        self.logger.info("=" * 60)
        self.logger.info("WebRadio Player - Logging initialized")
        self.logger.info(f"Log file: {log_file}")
        self.logger.info("=" * 60)

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance for a specific module"""
        return logging.getLogger(f'webradio.{name}')

    def set_level(self, level: str):
        """Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"""
        numeric_level = getattr(logging, level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f'Invalid log level: {level}')
        self.logger.setLevel(numeric_level)
        self.logger.info(f"Log level set to: {level.upper()}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module

    Usage:
        from webradio.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Message")
    """
    # Initialize WebRadioLogger singleton
    WebRadioLogger()
    return logging.getLogger(f'webradio.{name}')


# Initialize logging on module import
WebRadioLogger()
