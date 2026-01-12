"""Unit tests for logger module"""

import unittest
import logging
from pathlib import Path
from webradio.logger import get_logger, WebRadioLogger


class TestLogger(unittest.TestCase):
    """Test logger functionality"""

    def test_get_logger(self):
        """Test getting a logger instance"""
        logger = get_logger('test_module')
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, 'webradio.test_module')

    def test_logger_singleton(self):
        """Test that WebRadioLogger is a singleton"""
        logger1 = WebRadioLogger()
        logger2 = WebRadioLogger()
        self.assertIs(logger1, logger2)

    def test_logger_levels(self):
        """Test that logger has correct levels"""
        logger = get_logger('test_levels')

        # Should not raise exceptions
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

    def test_log_file_created(self):
        """Test that log file is created"""
        log_dir = Path.home() / '.local' / 'share' / 'webradio' / 'logs'
        log_file = log_dir / 'webradio.log'

        # Initialize logger
        get_logger('test_file_creation')

        # Log file should exist
        self.assertTrue(log_file.exists())


if __name__ == '__main__':
    unittest.main()
