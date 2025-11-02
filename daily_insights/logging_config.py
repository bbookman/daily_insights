"""Centralized logging configuration for Daily Insights.

This module provides a unified logging framework to replace print() statements
throughout the application with structured, configurable logging.

Features:
    - Centralized configuration with environment variable support
    - Console and file logging with automatic rotation
    - Configurable log levels per module
    - Thread-safe and async-safe logging
    - Structured formatting with timestamps and context

Example:
    >>> from daily_insights.logging_config import setup_logging, get_logger
    >>>
    >>> # Initialize logging (typically in main.py)
    >>> setup_logging(log_level="INFO", log_file=Path("logs/app.log"))
    >>>
    >>> # Get logger in any module
    >>> logger = get_logger(__name__)
    >>> logger.info("Application started")
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
import sys

# Module-level logger cache to avoid creating duplicate loggers
_loggers = {}
_initialized = False


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    console_output: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB default
    backup_count: int = 5
) -> logging.Logger:
    """
    Initialize logging framework for entire application.

    This should be called ONCE at application startup before any logging occurs.
    It configures the root logger for the 'daily_insights' namespace with both
    console and file handlers.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None = no file logging)
        console_output: Enable console output to stdout
        max_bytes: Maximum size of log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)

    Returns:
        Configured root logger instance for 'daily_insights' namespace

    Example:
        >>> from pathlib import Path
        >>> logger = setup_logging(
        ...     log_level="DEBUG",
        ...     log_file=Path("logs/app.log"),
        ...     max_bytes=5 * 1024 * 1024  # 5MB
        ... )
        >>> logger.info("Application started")

    Note:
        Log files will be rotated when they reach max_bytes size.
        Rotated files are named: app.log.1, app.log.2, etc.
        The oldest backup is deleted when backup_count is exceeded.
    """
    global _initialized

    if _initialized:
        return logging.getLogger('daily_insights')

    # Create root logger for our application namespace
    root_logger = logging.getLogger('daily_insights')
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove any existing handlers (in case of re-initialization)
    root_logger.handlers.clear()

    # Create formatter with timestamp and context
    formatter = _create_standard_formatter()

    # Console handler - outputs to stdout
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler with automatic rotation
    if log_file:
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Prevent propagation to Python root logger
    root_logger.propagate = False

    _initialized = True

    root_logger.info(
        "Logging initialized: level=%s, console=%s, file=%s",
        log_level,
        console_output,
        log_file
    )
    return root_logger


def _create_standard_formatter() -> logging.Formatter:
    """
    Create standard log formatter with timestamp and context.

    Format: YYYY-MM-DD HH:MM:SS | LEVEL    | module.name | message

    Returns:
        Configured formatter instance

    Example output:
        2025-11-02 10:15:23 | INFO     | daily_insights.api.limitless | Fetching page 1
        2025-11-02 10:15:24 | WARNING  | daily_insights.services.bee  | File not found
        2025-11-02 10:15:25 | ERROR    | daily_insights.api.openai    | API call failed
    """
    return logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get or create logger for specific module.

    This is the main function that modules should use to get their logger.
    Logger names should typically use __name__ to automatically use the
    module's fully-qualified name.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance for the module

    Example:
        >>> # In api/limitless_client.py
        >>> from daily_insights.logging_config import get_logger
        >>>
        >>> logger = get_logger(__name__)
        >>> logger.info("Fetching lifelogs from API")
        >>> logger.error("Request failed: %s", error_msg)

    Note:
        Loggers are cached to avoid creating duplicates. The same logger
        instance is returned for the same name on subsequent calls.
    """
    if name in _loggers:
        return _loggers[name]

    # Create child logger under our root logger
    logger = logging.getLogger(name)
    _loggers[name] = logger

    return logger


def shutdown_logging() -> None:
    """
    Gracefully shutdown logging system.

    Ensures all log messages are flushed to disk and file handlers are
    properly closed. Should be called at application exit.

    Example:
        >>> try:
        ...     main()
        ... finally:
        ...     shutdown_logging()

    Note:
        This is automatically called on Python exit, but explicit calls
        ensure immediate flushing of any buffered log messages.
    """
    logging.shutdown()


def set_log_level(level: str, logger_name: Optional[str] = None) -> None:
    """
    Change log level at runtime.

    Useful for temporarily enabling debug logging or reducing verbosity
    for specific modules without restarting the application.

    Args:
        level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        logger_name: Specific logger to modify (None = root daily_insights logger)

    Example:
        >>> # Enable debug logging for entire application
        >>> set_log_level("DEBUG")
        >>>
        >>> # Enable debug only for API clients
        >>> set_log_level("DEBUG", "daily_insights.api")
        >>>
        >>> # Reduce services to WARNING only
        >>> set_log_level("WARNING", "daily_insights.services")
    """
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger('daily_insights')

    logger.setLevel(getattr(logging, level.upper()))


def reset_logging() -> None:
    """
    Reset logging configuration (primarily for testing).

    Clears all handlers and resets initialization state. This allows
    tests to configure logging with different settings.

    Warning:
        This is intended for testing only. Do not call in production code.

    Example:
        >>> # In test setup
        >>> def setup_method(self):
        ...     reset_logging()
        ...     setup_logging(log_level="DEBUG")
    """
    global _initialized, _loggers
    _initialized = False
    _loggers.clear()

    # Clear all handlers from our loggers
    logger = logging.getLogger('daily_insights')
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
