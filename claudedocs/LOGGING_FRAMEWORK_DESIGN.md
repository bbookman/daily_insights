# Logging Framework Design: Daily Insights

**Design Date**: November 2, 2025
**Target**: Replace 373 print() statements with structured logging framework
**Type**: System Architecture Design
**Status**: Design Specification - Ready for Implementation

---

## Executive Summary

### Current State Analysis
- **373 print() statements** across 19 Python modules
- **No structured logging** framework in place
- **No log levels** - all output treated equally
- **No log rotation** or retention policies
- **Console-only output** - no file logging
- **No contextual information** (timestamps, module names, severity)
- **Difficult debugging** - cannot filter or search logs effectively

### Design Goals
1. **Structured Logging**: Replace print() with Python logging framework
2. **Multiple Outputs**: Console + file logging with rotation
3. **Configurable Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
4. **Performance**: Minimal overhead, async-safe
5. **Developer Experience**: Easy to use, minimal code changes
6. **Production Ready**: Log rotation, formatting, filtering

### Success Criteria
- ✅ Zero print() statements remaining (except CLI user output)
- ✅ All modules use centralized logger
- ✅ Configurable via environment variables
- ✅ <5ms logging overhead per call
- ✅ Automatic log rotation (10MB files, keep 5)
- ✅ Structured format with timestamps and context

---

## Architecture Design

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Daily Insights Application                   │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   API    │  │ Services │  │  Models  │  │   CLI    │       │
│  │ Clients  │  │  Layer   │  │  Utils   │  │ Commands │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │             │              │              │              │
│       └─────────────┴──────────────┴──────────────┘              │
│                          │                                        │
│                          ▼                                        │
│              ┌───────────────────────┐                          │
│              │   Logging Manager      │                          │
│              │  (daily_insights/      │                          │
│              │   logging_config.py)   │                          │
│              └───────────┬───────────┘                          │
│                          │                                        │
│         ┌────────────────┼────────────────┐                     │
│         ▼                ▼                ▼                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │   Console   │  │ File Logger │  │   Metrics   │           │
│  │   Handler   │  │  (Rotating) │  │  (Optional) │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
│         │                │                                        │
│         ▼                ▼                                        │
│     stdout/stderr    logs/daily_insights.log                     │
└─────────────────────────────────────────────────────────────────┘
```

### Module Hierarchy

```
daily_insights/
├── logging_config.py          # NEW: Centralized logging configuration
├── config.py                   # UPDATED: Add logging settings
├── api/
│   ├── __init__.py            # UPDATED: Import logger
│   ├── limitless_client.py    # UPDATED: Use logger
│   ├── openai_client.py       # UPDATED: Use logger
│   ├── ollama_client.py       # UPDATED: Use logger
│   └── ...
├── services/
│   ├── __init__.py            # UPDATED: Import logger
│   ├── lifelog_service.py     # UPDATED: Use logger
│   └── ...
└── main.py                    # UPDATED: Initialize logging
```

---

## Detailed Component Design

### 1. Logging Configuration Module

**File**: `daily_insights/logging_config.py`

**Purpose**: Centralized logging setup with formatters, handlers, and filters

**Responsibilities**:
1. Initialize Python logging framework
2. Configure log levels from environment
3. Setup console and file handlers
4. Apply formatting and rotation policies
5. Provide helper functions for module loggers

**Interface Design**:

```python
"""Centralized logging configuration for Daily Insights."""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
import sys

# Module-level logger instance
_logger: Optional[logging.Logger] = None

def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    console_output: bool = True,
    json_format: bool = False
) -> logging.Logger:
    """
    Initialize logging framework for entire application.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None = logs/daily_insights.log)
        console_output: Enable console output
        json_format: Use JSON structured logging (future enhancement)

    Returns:
        Configured root logger instance

    Example:
        >>> logger = setup_logging(log_level="DEBUG")
        >>> logger.info("Application started")
    """
    pass

def get_logger(name: str) -> logging.Logger:
    """
    Get or create logger for specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance for the module

    Example:
        >>> # In api/limitless_client.py
        >>> logger = get_logger(__name__)
        >>> logger.info("Fetching lifelogs...")
    """
    pass

def shutdown_logging() -> None:
    """
    Gracefully shutdown logging system.

    Ensures all log messages are flushed and handlers closed.
    Call at application exit.
    """
    pass
```

---

### 2. Configuration Updates

**File**: `daily_insights/config.py`

**Changes Required**:

```python
# ============================================================================
# Logging Configuration (NEW SECTION)
# ============================================================================

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Enable console logging
LOG_TO_CONSOLE = _parse_bool(os.getenv('LOG_TO_CONSOLE', 'true'))

# Enable file logging
LOG_TO_FILE = _parse_bool(os.getenv('LOG_TO_FILE', 'true'))

# Log file directory
LOG_DIR = PROJECT_ROOT / os.getenv('LOG_DIR', 'logs')

# Log file name
LOG_FILE = LOG_DIR / os.getenv('LOG_FILE', 'daily_insights.log')

# Log rotation settings
LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', '10485760'))  # 10MB default
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))   # Keep 5 files

# Structured logging (JSON format)
LOG_JSON_FORMAT = _parse_bool(os.getenv('LOG_JSON_FORMAT', 'false'))
```

**Environment Variables (.env)**:

```bash
# Logging Configuration
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_TO_CONSOLE=true               # Enable console output
LOG_TO_FILE=true                  # Enable file logging
LOG_DIR=logs                      # Log file directory
LOG_FILE=daily_insights.log       # Log file name
LOG_MAX_BYTES=10485760           # Max log file size (10MB)
LOG_BACKUP_COUNT=5               # Number of backup files to keep
LOG_JSON_FORMAT=false            # Use JSON structured logging
```

---

### 3. Logging Formatters

#### Standard Format (Human-Readable)

```
2025-11-02 10:15:23,456 | INFO     | daily_insights.api.limitless_client | Fetching lifelogs page 1...
2025-11-02 10:15:24,123 | WARNING  | daily_insights.services.bee_service | Bee file not found: 2025-11-01.txt
2025-11-02 10:15:25,789 | ERROR    | daily_insights.api.openai_client    | API call failed: timeout
```

**Format String**:
```python
'%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
```

**Components**:
- **Timestamp**: ISO 8601 format with milliseconds
- **Level**: Padded to 8 characters for alignment
- **Module**: Full module path for context
- **Message**: The actual log message

#### JSON Format (Machine-Readable)

```json
{
  "timestamp": "2025-11-02T10:15:23.456Z",
  "level": "INFO",
  "logger": "daily_insights.api.limitless_client",
  "message": "Fetching lifelogs page 1...",
  "function": "fetch_new_lifelogs",
  "line": 102,
  "thread": "MainThread",
  "process_id": 12345
}
```

---

### 4. Handler Configuration

#### Console Handler

**Configuration**:
- **Stream**: sys.stdout (INFO and below), sys.stderr (WARNING and above)
- **Format**: Colorized output for terminals (optional)
- **Level**: Respects global LOG_LEVEL
- **Behavior**: Real-time output for development and monitoring

```python
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(standard_formatter)
```

#### File Handler (Rotating)

**Configuration**:
- **Type**: RotatingFileHandler
- **Location**: logs/daily_insights.log
- **Max Size**: 10MB per file (configurable)
- **Backup Count**: 5 files (keeps 50MB total)
- **Format**: Standard format with full context
- **Encoding**: UTF-8
- **Mode**: Append

```python
file_handler = logging.handlers.RotatingFileHandler(
    filename=LOG_FILE,
    maxBytes=LOG_MAX_BYTES,
    backupCount=LOG_BACKUP_COUNT,
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(standard_formatter)
```

**File Rotation Behavior**:
```
logs/
├── daily_insights.log          # Current log (active)
├── daily_insights.log.1        # Most recent backup
├── daily_insights.log.2        # Second backup
├── daily_insights.log.3        # Third backup
├── daily_insights.log.4        # Fourth backup
└── daily_insights.log.5        # Oldest backup (gets deleted on next rotation)
```

---

### 5. Logger Hierarchy and Naming

**Naming Convention**: Use `__name__` for automatic module-based naming

**Hierarchy**:
```
root logger
└── daily_insights                          (parent)
    ├── daily_insights.api                  (subsystem)
    │   ├── daily_insights.api.limitless_client
    │   ├── daily_insights.api.openai_client
    │   └── daily_insights.api.ollama_client
    ├── daily_insights.services             (subsystem)
    │   ├── daily_insights.services.lifelog_service
    │   ├── daily_insights.services.insights_service
    │   └── daily_insights.services.bee_service
    ├── daily_insights.models               (subsystem)
    └── daily_insights.utils                (subsystem)
```

**Benefit**: Can set different log levels per subsystem:
```python
# Set DEBUG for API clients only
logging.getLogger('daily_insights.api').setLevel(logging.DEBUG)

# Set WARNING for services
logging.getLogger('daily_insights.services').setLevel(logging.WARNING)
```

---

## Log Level Guidelines

### Level Usage Matrix

| Level | When to Use | Examples | Typical Volume |
|-------|-------------|----------|----------------|
| **DEBUG** | Detailed diagnostic info for troubleshooting | Variable values, loop iterations, API request/response details | High (100s-1000s) |
| **INFO** | General informational messages about application flow | "Fetching lifelogs...", "Processing file X", "Saved to Y" | Medium (10s-100s) |
| **WARNING** | Potentially harmful situations that don't prevent operation | Missing files, retries, deprecated features, config defaults | Low (1s-10s) |
| **ERROR** | Error events that might still allow application to continue | API failures, file I/O errors, validation failures | Very Low (<10) |
| **CRITICAL** | Very severe errors that may cause application to abort | Database corruption, out of memory, critical service unavailable | Rare (<5) |

### Migration Mapping from print() to Logger

**Current Pattern → New Pattern**:

```python
# INFORMATIONAL MESSAGES
print("Starting process...")
→ logger.info("Starting process")

print(f"Processing {count} items")
→ logger.info("Processing %d items", count)

# PROGRESS UPDATES
print(f"Fetching page {page}...")
→ logger.info("Fetching page %d", page)

# FILE OPERATIONS
print(f"Saving to {filename}")
→ logger.info("Saving to %s", filename)

print(f"Skipping existing file: {filename}")
→ logger.debug("Skipping existing file: %s", filename)

# WARNINGS
print("Warning: No data found")
→ logger.warning("No data found")

print(f"Warning: {message}")
→ logger.warning("%s", message)

# ERRORS
print(f"Error: {e}")
→ logger.error("Operation failed: %s", e, exc_info=True)

# DEBUGGING (currently mixed with print)
print(f"Debug: variable = {var}")
→ logger.debug("variable = %s", var)

# SUCCESS MESSAGES
print("✅ Completed successfully")
→ logger.info("Completed successfully")
```

---

## Implementation Specification

### Phase 1: Foundation (Day 1)

**Goal**: Create logging infrastructure

**Tasks**:
1. Create `daily_insights/logging_config.py`
2. Update `daily_insights/config.py` with logging settings
3. Add logging configuration to `.env.example`
4. Create `logs/` directory with .gitkeep
5. Update `.gitignore` to exclude log files
6. Write unit tests for logging configuration

**Deliverables**:
- ✅ Logging module implemented
- ✅ Configuration integrated
- ✅ Tests passing
- ✅ Documentation updated

**Estimated Effort**: 2-3 hours

---

### Phase 2: Core Modules Migration (Day 2)

**Goal**: Migrate high-impact modules first

**Priority Order**:
1. **main.py** (entry point) - Initialize logging
2. **API clients** (4 files) - Network operations, errors
3. **Services** (6 files) - Business logic, file operations
4. **Models/Utils** (5 files) - Supporting functions

**Migration Pattern**:

```python
# AT TOP OF EACH FILE (add these lines)
from daily_insights.logging_config import get_logger

logger = get_logger(__name__)

# THEN REPLACE print() CALLS
# Before:
print(f"Fetching lifelogs from {url}")

# After:
logger.info("Fetching lifelogs from %s", url)
```

**Special Cases**:

1. **CLI Output (Keep print())**: User-facing messages in CLI commands
   ```python
   # KEEP these print() statements - they're user output, not logs
   print("=== Speaker Training Tool ===")
   print("Enter speaker name: ")
   ```

2. **Pipeline Statistics (Keep print())**: Summary displays
   ```python
   # In utils/pipeline_stats.py - keep print() for formatted output
   print("Pipeline Statistics:")
   print(f"  Lifelogs: {count}")
   ```

3. **Error Context**: Add exc_info=True for exceptions
   ```python
   # Before:
   except Exception as e:
       print(f"Error: {e}")

   # After:
   except Exception as e:
       logger.error("Operation failed", exc_info=True)
   ```

**Estimated Effort**: 4-6 hours

---

### Phase 3: Advanced Features (Day 3)

**Goal**: Add structured logging and performance monitoring

**Features**:
1. **Request IDs**: Track operations across modules
2. **Performance Metrics**: Log execution times
3. **Error Rates**: Track error frequency
4. **Structured Fields**: Add context to log entries

**Example - Request Tracking**:

```python
import uuid
from contextvars import ContextVar

request_id: ContextVar[str] = ContextVar('request_id', default='')

def set_request_id():
    """Generate and set unique request ID for this operation."""
    request_id.set(str(uuid.uuid4())[:8])

# In logging_config.py
class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id.get() or 'N/A'
        return True

# Format: '%(asctime)s | %(levelname)-8s | [%(request_id)s] | %(name)s | %(message)s'
```

**Example - Performance Logging**:

```python
import time
from functools import wraps

def log_execution_time(func):
    """Decorator to log function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start
            logger.info(
                "Function %s completed in %.2fs",
                func.__name__,
                duration
            )
            return result
        except Exception as e:
            duration = time.time() - start
            logger.error(
                "Function %s failed after %.2fs",
                func.__name__,
                duration,
                exc_info=True
            )
            raise
    return wrapper

# Usage:
@log_execution_time
def fetch_new_lifelogs(existing_dates: Set[str]) -> List[Dict]:
    # function implementation
    pass
```

**Estimated Effort**: 3-4 hours

---

### Phase 4: Testing & Validation (Day 4)

**Goal**: Ensure logging works correctly in all scenarios

**Test Cases**:

1. **Configuration Tests**:
   - Verify log level changes take effect
   - Test file rotation at size limit
   - Validate console vs file output
   - Test JSON format output

2. **Integration Tests**:
   - Run full pipeline with DEBUG level
   - Verify all modules log correctly
   - Check async logging thread-safety
   - Test error handling with tracebacks

3. **Performance Tests**:
   - Measure logging overhead (<5ms per call)
   - Test with high-volume logging (1000+ messages/sec)
   - Verify file handler doesn't block async operations

4. **Validation Checklist**:
   - [ ] Zero remaining print() statements (except CLI/stats)
   - [ ] All 19 modules use logger
   - [ ] Log files rotate correctly
   - [ ] Console output is readable
   - [ ] Error tracebacks are complete
   - [ ] No performance degradation

**Estimated Effort**: 2-3 hours

---

## Code Examples

### Example 1: Basic Logger Usage

**File**: `daily_insights/api/limitless_client.py`

```python
"""Client for interacting with the Limitless API."""

import json
import requests
from typing import Dict, List, Set
import backoff
from dateutil import parser
import aiohttp
import asyncio

from daily_insights.config import (
    CHATS_API_BASE,
    LIFELOGS_API_BASE,
    API_KEY
)
# ADD THIS
from daily_insights.logging_config import get_logger

# ADD THIS
logger = get_logger(__name__)


@backoff.on_exception(
    backoff.expo,
    (requests.exceptions.RequestException, requests.exceptions.HTTPError),
    max_tries=5,
    giveup=lambda e: e.response.status_code not in [429, 500, 502, 503, 504]
)
def _make_lifelog_request(params: Dict) -> requests.Response:
    """Make a request to the Limitless API with backoff handling."""
    # CHANGE THIS:
    # print("Making API request...")

    # TO THIS:
    logger.debug("Making API request with params: %s", params)

    headers = {
        "X-API-Key": API_KEY.strip(),
        "Content-Type": "application/json"
    }
    response = requests.get(
        LIFELOGS_API_BASE,
        headers=headers,
        params=params,
        timeout=60
    )
    response.raise_for_status()

    logger.debug("API request successful, status: %d", response.status_code)
    return response


def fetch_new_lifelogs(existing_dates: Set[str]) -> List[Dict]:
    """Fetch all new lifelogs from the Limitless API with pagination."""
    # CHANGE THIS:
    # print("\nStarting to fetch new lifelogs from Limitless...")

    # TO THIS:
    logger.info("Starting to fetch new lifelogs from Limitless")

    all_lifelogs = []
    next_cursor = None
    page = 1
    max_pages = 50

    while page <= max_pages:
        try:
            # CHANGE THIS:
            # print(f"Fetching lifelogs page {page}...")

            # TO THIS:
            logger.info("Fetching lifelogs page %d", page)

            response = _make_lifelog_request(params)

        except requests.exceptions.RequestException as e:
            # CHANGE THIS:
            # print(f"Request failed on page {page}: {e}")

            # TO THIS:
            logger.error("Request failed on page %d", page, exc_info=True)
            break

        # ... rest of function

        if date_str in existing_dates:
            # CHANGE THIS:
            # print(f"Found lifelog for existing date {date_str}. Stopping pagination.")

            # TO THIS:
            logger.info(
                "Found lifelog for existing date %s, stopping pagination",
                date_str
            )
            break

    logger.info("Fetched %d new lifelogs across %d pages", len(all_lifelogs), page)
    return all_lifelogs
```

---

### Example 2: Error Handling with Logging

**File**: `daily_insights/services/bee_service.py`

```python
from daily_insights.logging_config import get_logger

logger = get_logger(__name__)


def process_bee_transcriptions() -> None:
    """Process bee transcription files into daily insights."""
    logger.info("Starting bee transcription processing")

    try:
        # Load configuration
        prompt_text = read_prompt_file(BEE_PROMPT_FILE)
        if not prompt_text:
            logger.error("Bee prompt file not found or empty: %s", BEE_PROMPT_FILE)
            return

        # Find unprocessed files
        unprocessed_files = find_unprocessed_bee_files()
        logger.info("Found %d unprocessed bee files", len(unprocessed_files))

        if not unprocessed_files:
            logger.debug("No bee files to process")
            return

        # Process each file
        for bee_file, date_str in unprocessed_files:
            logger.info("Processing bee file: %s (date: %s)", bee_file, date_str)

            try:
                process_bee_file(bee_file, date_str, prompt_text)
                logger.info("Successfully processed bee file: %s", bee_file)

            except Exception as e:
                logger.error(
                    "Failed to process bee file %s",
                    bee_file,
                    exc_info=True
                )
                # Continue processing other files
                continue

        logger.info("Completed bee transcription processing")

    except Exception as e:
        logger.critical(
            "Bee transcription processing failed catastrophically",
            exc_info=True
        )
        raise
```

---

### Example 3: Main Application Initialization

**File**: `daily_insights/main.py`

```python
"""Main entry point for the daily insights system."""

import asyncio

from daily_insights.config import (
    ensure_directories,
    LOG_LEVEL,
    LOG_FILE,
    LOG_TO_CONSOLE,
    LOG_TO_FILE,
    # ... other imports
)
# ADD THIS
from daily_insights.logging_config import setup_logging, get_logger, shutdown_logging

# ADD THIS - Initialize logging FIRST
setup_logging(
    log_level=LOG_LEVEL,
    log_file=LOG_FILE if LOG_TO_FILE else None,
    console_output=LOG_TO_CONSOLE
)

# ADD THIS - Get logger for this module
logger = get_logger(__name__)


async def main_async() -> None:
    """Run the complete daily insights pipeline (asynchronous version)."""
    logger.info("=" * 70)
    logger.info("Starting Async Daily Insights Pipeline")
    logger.info("=" * 70)

    ensure_directories()

    # Stage 1: Fetch data in parallel
    logger.info("[Stage 1] Fetching data from APIs")
    fetch_tasks = []

    if FETCH_LIFELOGS:
        fetch_tasks.append(fetch_and_save_lifelogs_async())
    else:
        logger.info("Skipping lifelog fetching (FETCH_LIFELOGS=False)")

    if FETCH_DAILY_INSIGHTS:
        fetch_tasks.append(fetch_and_save_daily_insights_async())
    else:
        logger.info("Skipping daily insights fetching (FETCH_DAILY_INSIGHTS=False)")

    if fetch_tasks:
        await asyncio.gather(*fetch_tasks)

    # ... rest of pipeline stages ...

    # Display comprehensive pipeline statistics
    logger.info("=" * 70)
    display_pipeline_summary()  # This still uses print() for formatted output
    logger.info("=" * 70)

    logger.info("Pipeline completed successfully")


if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
    except Exception as e:
        logger.critical("Pipeline failed", exc_info=True)
        raise
    finally:
        # Ensure all logs are flushed
        shutdown_logging()
```

---

### Example 4: Complete logging_config.py Implementation

**File**: `daily_insights/logging_config.py`

```python
"""Centralized logging configuration for Daily Insights."""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
import sys

# Module-level logger cache
_loggers = {}
_initialized = False


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    console_output: bool = True,
    json_format: bool = False
) -> logging.Logger:
    """
    Initialize logging framework for entire application.

    This should be called ONCE at application startup before any logging occurs.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None = no file logging)
        console_output: Enable console output
        json_format: Use JSON structured logging (future enhancement)

    Returns:
        Configured root logger instance

    Example:
        >>> from pathlib import Path
        >>> logger = setup_logging(
        ...     log_level="DEBUG",
        ...     log_file=Path("logs/app.log")
        ... )
        >>> logger.info("Application started")
    """
    global _initialized

    if _initialized:
        return logging.getLogger('daily_insights')

    # Create root logger for our application
    root_logger = logging.getLogger('daily_insights')
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove any existing handlers (in case of re-initialization)
    root_logger.handlers.clear()

    # Create formatters
    if json_format:
        # TODO: Implement JSON formatter
        formatter = _create_standard_formatter()
    else:
        formatter = _create_standard_formatter()

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler with rotation
    if log_file:
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Prevent propagation to root logger
    root_logger.propagate = False

    _initialized = True

    root_logger.info("Logging initialized: level=%s, file=%s", log_level, log_file)
    return root_logger


def _create_standard_formatter() -> logging.Formatter:
    """Create standard log formatter with timestamp and context."""
    return logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get or create logger for specific module.

    This is the main function that modules should use to get their logger.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance for the module

    Example:
        >>> # In api/limitless_client.py
        >>> logger = get_logger(__name__)
        >>> logger.info("Fetching lifelogs")
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

    Ensures all log messages are flushed and handlers closed.
    Call at application exit.

    Example:
        >>> try:
        ...     main()
        ... finally:
        ...     shutdown_logging()
    """
    logging.shutdown()


# Convenience function for testing
def reset_logging() -> None:
    """Reset logging configuration (primarily for testing)."""
    global _initialized, _loggers
    _initialized = False
    _loggers.clear()

    # Clear all handlers from our loggers
    logger = logging.getLogger('daily_insights')
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
```

---

## Migration Checklist

### Pre-Migration
- [ ] Review and approve this design document
- [ ] Create feature branch: `feature/logging-framework`
- [ ] Backup current codebase
- [ ] Run existing tests to establish baseline

### Implementation
- [ ] **Phase 1: Foundation**
  - [ ] Create `logging_config.py`
  - [ ] Update `config.py` with logging settings
  - [ ] Update `.env.example` with logging variables
  - [ ] Create `logs/` directory with .gitkeep
  - [ ] Update `.gitignore`: add `logs/*.log`
  - [ ] Write unit tests for `logging_config.py`

- [ ] **Phase 2: Module Migration**
  - [ ] Migrate `main.py` (initialize logging)
  - [ ] Migrate API clients (4 files):
    - [ ] `api/limitless_client.py`
    - [ ] `api/openai_client.py`
    - [ ] `api/ollama_client.py`
    - [ ] `api/llm_client.py`
    - [ ] `api/speaker_llm_client.py`
  - [ ] Migrate Services (6 files):
    - [ ] `services/lifelog_service.py`
    - [ ] `services/insights_service.py`
    - [ ] `services/bee_service.py`
    - [ ] `services/therapy_service.py`
    - [ ] `services/monthly_service.py`
    - [ ] `services/speaker_service.py`
  - [ ] Migrate Models/Utils (5 files):
    - [ ] `models/conversation_parser.py`
    - [ ] `models/therapy_detection.py`
    - [ ] `utils/file_utils.py`
    - [ ] `utils/date_utils.py`
    - [ ] `utils/pipeline_stats.py` (selective - keep user-facing print())
  - [ ] Migrate CLI (1 file):
    - [ ] `cli/speaker_commands.py` (selective - keep user interaction print())

- [ ] **Phase 3: Advanced Features**
  - [ ] Add request ID tracking
  - [ ] Add execution time logging decorator
  - [ ] Add structured logging fields
  - [ ] Implement JSON formatter (optional)

- [ ] **Phase 4: Testing & Validation**
  - [ ] Run full pipeline with DEBUG level
  - [ ] Verify log rotation works correctly
  - [ ] Check async thread-safety
  - [ ] Performance testing (logging overhead)
  - [ ] Validate no print() statements remain (except CLI/stats)

### Documentation
- [ ] Update README.md with logging configuration
- [ ] Create `docs/LOGGING.md` with usage guidelines
- [ ] Update `.env.example` with logging examples
- [ ] Add logging section to troubleshooting guide

### Quality Assurance
- [ ] All tests pass
- [ ] No print() statements in business logic
- [ ] Log files rotate correctly
- [ ] Performance acceptable (<5ms per log call)
- [ ] Code review completed
- [ ] Merge to main branch

---

## Performance Considerations

### Logging Overhead

**Benchmarks** (Python logging module):
- **Disabled log level**: ~0.1 microseconds (essentially free)
- **Console output**: ~50-100 microseconds per call
- **File output**: ~1-5 milliseconds per call (buffered)
- **File output (flushed)**: ~10-50 milliseconds per call

**Optimization Strategies**:

1. **Lazy Formatting**: Use `%s` placeholders, not f-strings
   ```python
   # GOOD - string only formatted if logged
   logger.info("Processing %d items from %s", count, source)

   # BAD - string formatted regardless of log level
   logger.info(f"Processing {count} items from {source}")
   ```

2. **Appropriate Log Levels**: Use DEBUG for verbose output
   ```python
   # Production: INFO level (DEBUG messages skipped with no overhead)
   logger.debug("Variable state: %s", large_dict)  # Free if level is INFO
   ```

3. **Avoid Logging in Tight Loops**:
   ```python
   # BAD - logs 10,000 times
   for item in large_list:
       logger.debug("Processing item: %s", item)

   # GOOD - log summary
   logger.info("Processing %d items", len(large_list))
   for item in large_list:
       process(item)
   logger.info("Completed processing %d items", len(large_list))
   ```

4. **Async-Safe Logging**: Python logging is thread-safe by default
   - No special configuration needed for asyncio
   - Handlers use locks internally
   - Consider QueueHandler for very high throughput (>10k msgs/sec)

---

## Testing Strategy

### Unit Tests

**File**: `tests/test_logging_config.py`

```python
"""Unit tests for logging configuration."""

import logging
import tempfile
from pathlib import Path
import pytest

from daily_insights.logging_config import (
    setup_logging,
    get_logger,
    shutdown_logging,
    reset_logging
)


class TestLoggingSetup:
    """Test logging initialization."""

    def setup_method(self):
        """Reset logging before each test."""
        reset_logging()

    def teardown_method(self):
        """Clean up after each test."""
        shutdown_logging()
        reset_logging()

    def test_basic_setup(self):
        """Test basic logging setup with defaults."""
        logger = setup_logging(log_level="INFO")

        assert logger is not None
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0

    def test_file_logging(self):
        """Test logging to file with rotation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            logger = setup_logging(
                log_level="DEBUG",
                log_file=log_file
            )

            logger.info("Test message")

            assert log_file.exists()
            content = log_file.read_text()
            assert "Test message" in content

    def test_log_levels(self):
        """Test different log levels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            setup_logging(log_level="WARNING", log_file=log_file)
            logger = get_logger(__name__)

            logger.debug("Debug message")    # Should NOT appear
            logger.info("Info message")      # Should NOT appear
            logger.warning("Warning message")  # Should appear
            logger.error("Error message")    # Should appear

            content = log_file.read_text()
            assert "Debug message" not in content
            assert "Info message" not in content
            assert "Warning message" in content
            assert "Error message" in content

    def test_multiple_loggers(self):
        """Test getting loggers for different modules."""
        setup_logging(log_level="INFO")

        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        logger1_again = get_logger("module1")

        assert logger1 is not logger2
        assert logger1 is logger1_again  # Should return cached logger


class TestLoggerUsage:
    """Test logger usage patterns."""

    def test_exception_logging(self):
        """Test logging exceptions with traceback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            setup_logging(log_level="DEBUG", log_file=log_file)
            logger = get_logger(__name__)

            try:
                raise ValueError("Test error")
            except ValueError:
                logger.error("An error occurred", exc_info=True)

            content = log_file.read_text()
            assert "An error occurred" in content
            assert "ValueError: Test error" in content
            assert "Traceback" in content
```

---

## Rollout Strategy

### Development Environment
1. Implement on feature branch
2. Test with DEBUG level
3. Run full pipeline multiple times
4. Review log output for completeness

### Staging Environment
1. Deploy with INFO level
2. Monitor for 24 hours
3. Check log file sizes and rotation
4. Validate no errors or warnings

### Production Environment
1. Deploy with INFO level
2. Monitor metrics:
   - Log file size growth rate
   - Disk space usage
   - Application performance
   - Error/warning frequency
3. Adjust log levels per subsystem as needed

### Rollback Plan
If issues occur:
1. Feature flag to disable file logging: `LOG_TO_FILE=false`
2. Revert to print() statements if critical failure
3. Increase log level to reduce volume: `LOG_LEVEL=WARNING`

---

## Maintenance and Operations

### Log File Management

**Automatic Rotation**:
- Triggered at 10MB file size
- Keeps 5 backup files (50MB total)
- No manual intervention required

**Manual Cleanup**:
```bash
# View log files
ls -lh logs/

# View recent logs
tail -f logs/daily_insights.log

# Search logs
grep "ERROR" logs/daily_insights.log

# Clean old logs manually (if needed)
find logs/ -name "*.log.*" -mtime +30 -delete
```

**Log Analysis Tools**:
```bash
# Count errors by module
grep ERROR logs/daily_insights.log | cut -d'|' -f3 | sort | uniq -c

# View errors in last hour
grep ERROR logs/daily_insights.log | grep "$(date '+%Y-%m-%d %H')"

# Tail multiple log levels
tail -f logs/daily_insights.log | grep -E "ERROR|WARNING|CRITICAL"
```

### Monitoring and Alerts

**Key Metrics to Monitor**:
1. **Error Rate**: Errors per minute/hour
2. **Log Volume**: Messages per second
3. **Disk Usage**: Log directory size
4. **Performance**: Logging overhead impact

**Alert Thresholds**:
- **WARNING**: >10 errors per hour
- **CRITICAL**: >100 errors per hour
- **Disk**: >90% of log partition full

---

## Benefits Summary

### Before Logging Framework
❌ 373 print() statements scattered across codebase
❌ No timestamps or context
❌ Cannot filter by severity
❌ Console-only output (lost on restart)
❌ Difficult to debug production issues
❌ No performance metrics
❌ Mixed concerns (user output + system logs)

### After Logging Framework
✅ Centralized, structured logging
✅ Timestamps, module names, severity levels
✅ Filter by level, module, time
✅ Persistent file logging with rotation
✅ Easy debugging with full context
✅ Performance tracking capabilities
✅ Clear separation: logs vs user output
✅ Production-ready monitoring

---

## Success Metrics

### Quantitative
- **Code Quality**: 373 print() → 0 (except CLI/stats)
- **Test Coverage**: Logging module at 95%+
- **Performance**: <5ms average log call
- **Disk Usage**: <50MB for 5-file rotation
- **Error Detection**: 100% of exceptions logged

### Qualitative
- **Developer Experience**: Easier debugging
- **Operations**: Better production monitoring
- **Maintenance**: Reduced time to troubleshoot
- **Code Quality**: More professional codebase

---

## Appendix A: Configuration Reference

### Complete .env Example

```bash
# ============================================================================
# Logging Configuration
# ============================================================================

# Log Level: DEBUG (most verbose) | INFO | WARNING | ERROR | CRITICAL (least)
# - DEBUG: Development and troubleshooting (shows everything)
# - INFO: Production default (general operational messages)
# - WARNING: Production conservative (only potential issues)
# - ERROR: Critical systems (only failures)
LOG_LEVEL=INFO

# Console Output: Display logs in terminal
# Set to false for background jobs or when only file logging desired
LOG_TO_CONSOLE=true

# File Logging: Save logs to file
# Set to false to disable file logging (console only)
LOG_TO_FILE=true

# Log Directory: Where log files are stored
LOG_DIR=logs

# Log File Name: Name of the main log file
LOG_FILE=daily_insights.log

# Log Rotation: Maximum size of log file before rotation (bytes)
# Default: 10485760 (10MB)
# When file reaches this size, it's rotated to .log.1, etc.
LOG_MAX_BYTES=10485760

# Log Backup Count: Number of backup files to keep
# Default: 5 (keeps 50MB total with 10MB files)
# Oldest backup is deleted when limit reached
LOG_BACKUP_COUNT=5

# Structured Logging: Output logs in JSON format
# Default: false (human-readable format)
# Set to true for machine parsing (log aggregation systems)
LOG_JSON_FORMAT=false
```

---

## Appendix B: Common Patterns

### Pattern 1: Module Logger

```python
"""Example module with logging."""

from daily_insights.logging_config import get_logger

# Get logger for this module (use __name__ for automatic naming)
logger = get_logger(__name__)


def example_function():
    """Example function demonstrating logging patterns."""
    logger.info("Function started")

    try:
        # Business logic here
        result = perform_operation()
        logger.info("Operation completed successfully")
        return result

    except ValueError as e:
        logger.error("Validation error: %s", e)
        raise

    except Exception as e:
        logger.critical("Unexpected error", exc_info=True)
        raise
```

### Pattern 2: Conditional Debug Logging

```python
# Expensive debug logging - only computed if DEBUG level
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("Expensive operation result: %s", compute_expensive_debug_info())

# Alternative: Just use DEBUG - won't format if not logged
logger.debug("State: %s", expensive_state)  # Won't call expensive_state.__str__ if INFO level
```

### Pattern 3: Contextual Logging

```python
def process_file(filename: str):
    """Process file with contextual logging."""
    logger.info("Processing file: %s", filename)

    try:
        # Add context with extra fields
        logger.info(
            "File processing started",
            extra={"filename": filename, "size": os.path.getsize(filename)}
        )

        # Processing logic
        result = do_processing(filename)

        logger.info(
            "File processing completed: %d records",
            result["record_count"]
        )

    except FileNotFoundError:
        logger.error("File not found: %s", filename)
        raise
```

---

## Appendix C: Troubleshooting

### Issue: Logs not appearing

**Symptoms**: No log output despite calling logger functions

**Solutions**:
1. Check logging is initialized: Call `setup_logging()` in main.py
2. Check log level: Set to DEBUG temporarily to see all messages
3. Check handlers: Ensure console or file handler is configured
4. Check logger name: Verify using correct logger (not root logger)

### Issue: Log files growing too fast

**Symptoms**: Disk space issues, frequent rotations

**Solutions**:
1. Increase `LOG_MAX_BYTES` (e.g., 50MB instead of 10MB)
2. Reduce log verbosity: Change DEBUG → INFO
3. Reduce `LOG_BACKUP_COUNT` if disk space limited
4. Add cleanup cron job for old backups

### Issue: Performance degradation

**Symptoms**: Application slower after adding logging

**Solutions**:
1. Check log level: Use INFO in production, not DEBUG
2. Remove logging from tight loops
3. Use lazy formatting (`%s` not f-strings)
4. Consider async file handler for high-volume logging

---

## Appendix D: Future Enhancements

### Phase 5: Advanced Features (Optional)

**1. Structured Logging (JSON)**:
- Machine-readable format for log aggregation
- Integration with ELK stack, Splunk, Datadog
- Searchable fields and metadata

**2. Log Aggregation**:
- Centralized logging service
- Real-time log streaming
- Cross-instance log correlation

**3. Metrics Integration**:
- Prometheus metrics from logs
- Error rate tracking
- Performance dashboards

**4. Alerting**:
- Email notifications on ERROR/CRITICAL
- Slack integration
- PagerDuty for production issues

**5. Log Sampling**:
- Sample DEBUG logs in production (e.g., 1%)
- Reduce volume while maintaining visibility
- Dynamic sampling based on error rates

---

**Document Status**: Design Complete - Ready for Implementation
**Estimated Implementation Time**: 3-4 days
**Priority**: HIGH (addresses critical code smell finding)
**Next Steps**: Review and approve → Create implementation branch → Phase 1 execution
