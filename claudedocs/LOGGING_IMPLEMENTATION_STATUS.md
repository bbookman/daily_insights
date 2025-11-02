# Logging Framework Implementation Status

**Date**: November 2, 2025
**Phase**: Foundation Complete - Ready for Module Migration
**Status**: ✅ Phase 1 Complete (Infrastructure) | 🔄 Phase 2 In Progress (Migration)

---

## ✅ Phase 1 Complete: Foundation (100%)

### What Was Implemented

1. **✅ Logging Configuration Module** (`daily_insights/logging_config.py`)
   - Complete implementation with 200+ lines of documentation
   - `setup_logging()` - Initialize logging with console + file handlers
   - `get_logger()` - Get module-specific loggers
   - `shutdown_logging()` - Graceful shutdown
   - `set_log_level()` - Runtime log level changes
   - `reset_logging()` - Testing support
   - Automatic log rotation (10MB files, keep 5 backups)
   - Thread-safe and async-safe by default

2. **✅ Configuration Updates** (`daily_insights/config.py`)
   - Added logging configuration section
   - 7 new configuration variables:
     - `LOG_LEVEL` - Log verbosity (DEBUG/INFO/WARNING/ERROR/CRITICAL)
     - `LOG_TO_CONSOLE` - Enable console output
     - `LOG_TO_FILE` - Enable file logging
     - `LOG_DIR` - Log directory path
     - `LOG_FILE` - Log file name
     - `LOG_MAX_BYTES` - File size before rotation (10MB default)
     - `LOG_BACKUP_COUNT` - Number of backups (5 default)
   - Updated `ensure_directories()` to create logs directory
   - Moved `_parse_bool()` before usage (fixed function order)

3. **✅ Environment Configuration** (`.env.example`)
   - Added comprehensive logging section with documentation
   - Example values for all logging variables
   - Usage guidance and recommendations
   - Examples for different log file sizes

4. **✅ Infrastructure Setup**
   - Created `logs/` directory with `.gitkeep`
   - Updated `.gitignore` to exclude log files:
     - `logs/*.log` - Current log files
     - `logs/*.log.*` - Rotated backup files

### Quick Test

To verify the logging framework works:

```python
# Test in Python REPL
from pathlib import Path
from daily_insights.logging_config import setup_logging, get_logger

# Initialize logging
setup_logging(log_level="INFO", log_file=Path("logs/test.log"))

# Get logger and test
logger = get_logger(__name__)
logger.info("Test message - INFO level")
logger.warning("Test warning")
logger.error("Test error")

# Check logs directory
import os
print(os.listdir("logs/"))  # Should show test.log
```

---

## 🔄 Phase 2: Module Migration (Remaining Work)

### Migration Priority & Effort Estimate

**Total**: 373 print() statements across 19 files

| Priority | Files | Print Statements | Effort | Status |
|----------|-------|------------------|--------|--------|
| **P1: Entry Point** | main.py (1 file) | ~20 | 30 min | ⏳ Not Started |
| **P2: API Clients** | 5 files | ~80 | 2 hours | ⏳ Not Started |
| **P3: Services** | 6 files | ~200 | 3 hours | ⏳ Not Started |
| **P4: Models/Utils** | 5 files | ~50 | 1.5 hours | ⏳ Not Started |
| **P5: CLI Commands** | 2 files | ~23 (selective) | 1 hour | ⏳ Not Started |
| **Total** | **19 files** | **373 total** | **8 hours** | **0% Complete** |

### Migration Pattern (Copy-Paste Template)

**At top of each file**:
```python
from daily_insights.logging_config import get_logger

logger = get_logger(__name__)
```

**Replace print() statements**:
```python
# BEFORE
print("Starting process...")
print(f"Processing {count} items")
print(f"Warning: {message}")
print(f"Error: {e}")

# AFTER
logger.info("Starting process")
logger.info("Processing %d items", count)
logger.warning("%s", message)
logger.error("Operation failed: %s", e, exc_info=True)
```

### Files To Migrate (Detailed Checklist)

#### P1: Main Entry Point (30 minutes)
- [ ] `main.py` - Initialize logging, migrate 20 print statements

#### P2: API Clients (2 hours)
- [ ] `api/limitless_client.py` - 30 print statements
- [ ] `api/openai_client.py` - 6 print statements
- [ ] `api/ollama_client.py` - 12 print statements
- [ ] `api/llm_client.py` - 8 print statements
- [ ] `api/speaker_llm_client.py` - 9 print statements

#### P3: Services (3 hours)
- [ ] `services/lifelog_service.py` - 25 print statements
- [ ] `services/insights_service.py` - 18 print statements
- [ ] `services/bee_service.py` - 42 print statements
- [ ] `services/therapy_service.py` - 29 print statements
- [ ] `services/monthly_service.py` - 30 print statements
- [ ] `services/speaker_service.py` - 13 print statements

#### P4: Models/Utils (1.5 hours)
- [ ] `models/conversation_parser.py` - 8 print statements
- [ ] `models/therapy_detection.py` - 13 print statements
- [ ] `utils/date_utils.py` - 3 print statements
- [ ] `utils/file_utils.py` - 5 print statements
- [ ] `utils/pipeline_stats.py` - 1 print statement (keep most for user output)

#### P5: CLI Commands (1 hour - Selective)
- [ ] `cli/speaker_commands.py` - 96 print statements (KEEP user interaction ones)

**Note on CLI**: Keep print() statements for user interaction (prompts, menus, output displays). Only migrate internal logging/debugging print statements.

---

## Migration Guidelines

### When to Use Each Log Level

| Level | Use For | Examples |
|-------|---------|----------|
| **DEBUG** | Detailed diagnostic info | Variable values, API request/response details, loop iterations |
| **INFO** | General application flow | "Processing file X", "Fetched N items", "Saved to Y" |
| **WARNING** | Potentially harmful situations | Missing files, using defaults, retries, deprecated features |
| **ERROR** | Error events (continues running) | API failures, file I/O errors, validation failures |
| **CRITICAL** | Severe errors (may abort) | Database corruption, out of memory, critical service down |

### Special Cases

1. **CLI User Output** (KEEP print statements):
   ```python
   # KEEP these - they're user interface, not logs
   print("=== Menu Options ===")
   print("Enter your choice: ")
   input_value = input()  # Keep this interaction
   ```

2. **Pipeline Statistics** (KEEP print statements):
   ```python
   # In utils/pipeline_stats.py
   # KEEP formatted output displays for user
   print("Pipeline Statistics:")
   print(f"  Lifelogs: {count}")
   ```

3. **Exception Logging** (Add exc_info=True):
   ```python
   # BEFORE
   except Exception as e:
       print(f"Error: {e}")

   # AFTER
   except Exception as e:
       logger.error("Operation failed", exc_info=True)
   ```

4. **Lazy String Formatting** (Use %s placeholders):
   ```python
   # GOOD - string only formatted if logged
   logger.info("Processing %d items from %s", count, source)

   # AVOID - string always formatted
   logger.info(f"Processing {count} items from {source}")
   ```

---

## Quick Start Example: Migrating main.py

Here's exactly what needs to be done for main.py:

```python
"""Main entry point for the daily insights system."""

import asyncio

# ADD THESE IMPORTS
from daily_insights.logging_config import setup_logging, get_logger, shutdown_logging

from daily_insights.config import (
    ensure_directories,
    # ADD THESE
    LOG_LEVEL,
    LOG_FILE,
    LOG_TO_CONSOLE,
    LOG_TO_FILE,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
    # ... other imports
)

# ADD THIS - Initialize logging FIRST
setup_logging(
    log_level=LOG_LEVEL,
    log_file=LOG_FILE if LOG_TO_FILE else None,
    console_output=LOG_TO_CONSOLE,
    max_bytes=LOG_MAX_BYTES,
    backup_count=LOG_BACKUP_COUNT
)

# ADD THIS - Get logger
logger = get_logger(__name__)


async def main_async() -> None:
    """Run the complete daily insights pipeline (asynchronous version)."""
    # REPLACE: print("=" * 70)
    # REPLACE: print("Starting Async Daily Insights Pipeline")
    # REPLACE: print("=" * 70)
    logger.info("=" * 70)
    logger.info("Starting Async Daily Insights Pipeline")
    logger.info("=" * 70)

    ensure_directories()

    # Stage 1: Fetch data in parallel
    # REPLACE: print("\n[Stage 1] Fetching data from APIs...")
    logger.info("[Stage 1] Fetching data from APIs")

    fetch_tasks = []
    if FETCH_LIFELOGS:
        fetch_tasks.append(fetch_and_save_lifelogs_async())
    else:
        # REPLACE: print("⏭️  Skipping lifelog fetching (FETCH_LIFELOGS=False)")
        logger.info("Skipping lifelog fetching (FETCH_LIFELOGS=False)")

    # ... repeat for all print statements ...

    logger.info("=" * 70)
    display_pipeline_summary()  # This keeps print() for formatted output
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

## Testing Strategy

### After Each File Migration

1. **Syntax Check**:
   ```bash
   python3 -m py_compile daily_insights/[migrated_file].py
   ```

2. **Import Test**:
   ```python
   python3 -c "from daily_insights.[module] import *"
   ```

### After P1-P2 Complete (Entry + API)

Run a simple test to verify logging works end-to-end:
```bash
# Set DEBUG level to see all messages
export LOG_LEVEL=DEBUG
python3 -m daily_insights.main

# Check log file was created
ls -lh logs/
cat logs/daily_insights.log
```

### Final Integration Test (After All Migration)

1. **Full Pipeline with File Logging**:
   ```bash
   # Run full pipeline
   python run_daily_insights.py

   # Verify logs
   tail -f logs/daily_insights.log
   ```

2. **Verify No print() Remains** (except CLI/stats):
   ```bash
   # Should show only CLI and stats files
   grep -r "print(" daily_insights/ --include="*.py" | \
     grep -v "speaker_commands.py" | \
     grep -v "pipeline_stats.py"
   ```

3. **Test Log Rotation**:
   ```bash
   # Set small file size for testing
   export LOG_MAX_BYTES=1048576  # 1MB

   # Run pipeline multiple times
   for i in {1..5}; do python run_daily_insights.py; done

   # Check rotation happened
   ls -lh logs/
   # Should see: daily_insights.log, daily_insights.log.1, etc.
   ```

---

## Current Configuration Values

Based on `.env.example`, the default logging configuration is:

```bash
LOG_LEVEL=INFO                 # Show INFO and above
LOG_TO_CONSOLE=true            # Yes, show in terminal
LOG_TO_FILE=true               # Yes, save to file
LOG_DIR=logs                   # Directory: logs/
LOG_FILE=daily_insights.log    # Filename
LOG_MAX_BYTES=10485760        # 10MB file size
LOG_BACKUP_COUNT=5            # Keep 5 backups (50MB total)
```

This means:
- Logs will appear in terminal AND be saved to files
- File rotates at 10MB
- Keeps 50MB total (10MB × 5 files)
- INFO level and above (INFO, WARNING, ERROR, CRITICAL)

---

## Next Steps

### Immediate (Phase 2a: Entry Point)

1. Migrate `main.py` following the example above
2. Test that logging initializes correctly
3. Run a simple pipeline test

**Time**: 30 minutes

### Short-Term (Phase 2b: API Clients)

1. Migrate all 5 API client files
2. Use search/replace for common patterns:
   - Find: `print(f"`
   - Consider: `logger.info("`
3. Test API operations work with logging

**Time**: 2 hours

### Medium-Term (Phase 2c-d: Services & Models)

1. Migrate services layer (6 files, highest volume)
2. Migrate models and utilities (5 files)
3. Run full integration tests

**Time**: 4.5 hours

### Final (Phase 2e: CLI)

1. Selectively migrate CLI commands (keep user-facing print())
2. Final validation
3. Create unit tests

**Time**: 1 hour

### Phase 3: Testing & Documentation

1. Create comprehensive unit tests for logging_config.py
2. Run full pipeline multiple times
3. Update README.md with logging section
4. Document troubleshooting tips

**Time**: 2-3 hours

---

## Success Criteria

- [ ] Zero print() statements in business logic (except CLI user output and pipeline stats)
- [ ] All 19 modules import and use logger
- [ ] Logging framework initializes without errors
- [ ] Console output shows structured logs with timestamps
- [ ] Log files created in logs/ directory
- [ ] Log rotation works correctly (test with small file size)
- [ ] Full pipeline runs successfully with logging
- [ ] No performance degradation
- [ ] Unit tests pass for logging_config.py

---

## Troubleshooting

### Issue: "NameError: name 'logger' is not defined"

**Solution**: Add logger import at top of file:
```python
from daily_insights.logging_config import get_logger
logger = get_logger(__name__)
```

### Issue: No log file created

**Solution**: Check configuration and directory:
```python
from daily_insights.config import LOG_FILE, LOG_DIR
print(f"Log directory: {LOG_DIR}")
print(f"Log file: {LOG_FILE}")
print(f"Directory exists: {LOG_DIR.exists()}")
```

### Issue: Logs not appearing in console

**Solution**: Check log level and console setting:
```bash
export LOG_LEVEL=DEBUG
export LOG_TO_CONSOLE=true
```

---

## Benefits Achieved (Phase 1)

✅ **Infrastructure Complete**: Production-ready logging framework
✅ **Configurable**: All settings via environment variables
✅ **Persistent**: Logs saved to files with automatic rotation
✅ **Structured**: Timestamps, module names, log levels
✅ **Professional**: Industry-standard Python logging module
✅ **Documented**: Comprehensive examples and guidelines

## Remaining Benefits (After Phase 2)

🔄 **No print() statements**: Clean, professional codebase
🔄 **Easy Debugging**: Filter and search logs by level, module, time
🔄 **Production Ready**: Monitoring and troubleshooting capabilities
🔄 **Maintainable**: Clear separation of logging vs user output

---

**Status Summary**:
- ✅ **Phase 1**: 100% Complete (Infrastructure ready)
- 🔄 **Phase 2**: 0% Complete (373 print statements remaining)
- ⏳ **Phase 3**: Not Started (Testing & documentation)

**Estimated Total Time Remaining**: 10-12 hours

**Priority**: HIGH (Critical code smell fix)

**Next Action**: Start with migrating `main.py` (30 minutes, high impact)
