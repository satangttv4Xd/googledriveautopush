"""
Application Logger with sensitive credential masking.
"""
import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from config.constants import DEFAULT_LOG_PATH


class SensitiveFilter(logging.Filter):
    """Masks authorization tokens, client secrets, and sensitive queries."""
    
    PATTERNS = [
        (re.compile(r'("?(?:client_secret|access_token|refresh_token)"?\s*[:=]\s*)"([^"]+)"', re.IGNORECASE), r'\1"***REDACTED***"'),
        (re.compile(r'(Bearer\s+)[A-Za-z0-9_\-\.]+', re.IGNORECASE), r'\1***REDACTED***'),
        (re.compile(r'(ya29\.[A-Za-z0-9_\-]+)', re.IGNORECASE), r'ya29.***REDACTED***'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True


def setup_logger(name: str = "autopush", log_file: Path = DEFAULT_LOG_PATH) -> logging.Logger:
    """Configures and returns a thread-safe logger."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Format
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(threadName)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    sensitive_filter = SensitiveFilter()

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(sensitive_filter)
    logger.addHandler(console_handler)

    # File Handler
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            str(log_file),
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not initialize file log handler: {e}")

    return logger


logger = setup_logger()
