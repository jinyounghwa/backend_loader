"""Unit tests for logging configuration"""

import json
import logging
import os
import tempfile
import unittest

from guardian.logging_config import (
    JSONFormatter,
    log_check_result,
    log_remediation,
    setup_logger,
)


class TestJSONFormatter(unittest.TestCase):
    """Unit tests for JSONFormatter"""

    def setUp(self):
        self.formatter = JSONFormatter()

    def test_format_basic_log(self):
        """Test basic log formatting"""
        record = logging.LogRecord(
            name="test-logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = self.formatter.format(record)
        data = json.loads(result)

        self.assertEqual(data["level"], "INFO")
        self.assertEqual(data["logger"], "test-logger")
        self.assertEqual(data["message"], "Test message")
        self.assertIn("timestamp", data)

    def test_format_with_extra_fields(self):
        """Test formatting with extra fields"""
        record = logging.LogRecord(
            name="test-logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Cost anomaly",
            args=(),
            exc_info=None,
        )
        record.action = "check_result"
        record.resource = "cost"
        record.status = "warning"

        result = self.formatter.format(record)
        data = json.loads(result)

        self.assertEqual(data["level"], "WARNING")
        self.assertEqual(data["action"], "check_result")
        self.assertEqual(data["resource"], "cost")
        self.assertEqual(data["status"], "warning")

    def test_format_different_levels(self):
        """Test formatting with different log levels"""
        for level_name, level_val in [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
        ]:
            record = logging.LogRecord(
                name="test",
                level=level_val,
                pathname="test.py",
                lineno=1,
                msg="Test",
                args=(),
                exc_info=None,
            )

            result = self.formatter.format(record)
            data = json.loads(result)

            self.assertEqual(data["level"], level_name)


class TestSetupLogger(unittest.TestCase):
    """Unit tests for setup_logger"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Clean up temp files
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_setup_logger_console_only(self):
        """Test logger setup without file handler"""
        logger = setup_logger("test-logger-1", level=logging.INFO)

        self.assertEqual(logger.name, "test-logger-1")
        self.assertEqual(logger.level, logging.INFO)
        self.assertEqual(len(logger.handlers), 1)  # Only console handler
        self.assertIsInstance(logger.handlers[0], logging.StreamHandler)

    def test_setup_logger_with_file(self):
        """Test logger setup with file handler"""
        log_file = os.path.join(self.temp_dir, "test.log")
        logger = setup_logger("test-logger-2", log_file=log_file, level=logging.DEBUG)

        self.assertEqual(logger.name, "test-logger-2")
        self.assertEqual(len(logger.handlers), 2)  # Console + file handlers

        # Log a message
        logger.info("Test log message")

        # Check file was created
        self.assertTrue(os.path.exists(log_file))

        # Check file contents
        with open(log_file) as f:
            content = f.read()
            data = json.loads(content.strip())
            self.assertEqual(data["message"], "Test log message")

    def test_setup_logger_different_levels(self):
        """Test logger with different log levels"""
        for level_name, level_val in [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
        ]:
            logger = setup_logger(f"test-logger-{level_name}", level=level_val)
            self.assertEqual(logger.level, level_val)


class TestLogFunctions(unittest.TestCase):
    """Unit tests for log helper functions"""

    def setUp(self):
        self.logger = logging.getLogger("test-log-helper")
        self.logger.setLevel(logging.DEBUG)
        self.handler = logging.StreamHandler()
        self.handler.setLevel(logging.DEBUG)
        self.logger.addHandler(self.handler)

    def tearDown(self):
        self.logger.handlers.clear()

    def test_log_check_result(self):
        """Test log_check_result function"""
        # This is a simple test to ensure the function doesn't raise errors
        log_check_result(self.logger, "cost", "ok", "Cost check passed")
        log_check_result(self.logger, "ec2", "warning", "Found exposed instances")

    def test_log_remediation(self):
        """Test log_remediation function"""
        # This is a simple test to ensure the function doesn't raise errors
        log_remediation(self.logger, "stop_ec2", "i-1234567890abcdef0", "success")
        log_remediation(self.logger, "block_s3", "my-bucket", "failed", "Permission denied")


if __name__ == "__main__":
    unittest.main()
