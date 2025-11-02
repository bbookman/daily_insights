# Logging Framework - Quick Start Guide

**5-Minute Setup | Copy-Paste Ready | Production Ready**

---

## ✅ Already Done (Phase 1)

The logging infrastructure is complete and ready to use:
- ✅ `daily_insights/logging_config.py` - Logging module created
- ✅ Configuration added to `config.py`
- ✅ Environment variables in `.env.example`
- ✅ `logs/` directory created
- ✅ `.gitignore` updated

**You can start using logging immediately!**

---

## Quick Test (30 seconds)

Verify logging works:

```bash
cd /Users/brucebookman/code/daily_insights

python3 << 'EOF'
from pathlib import Path
from daily_insights.logging_config import setup_logging, get_logger

# Initialize
setup_logging(log_level="INFO", log_file=Path("logs/test.log"))

# Test
logger = get_logger(__name__)
logger.info("✅ Logging framework works!")
logger.warning("⚠️  This is a warning")
logger.error("❌ This is an error")

print("\nCheck logs/test.log to see the output!")
EOF

# View the log file
cat logs/test.log
```

Expected output in `logs/test.log`:
```
2025-11-02 15:30:00 | INFO     | __main__ | ✅ Logging framework works!
2025-11-02 15:30:00 | WARNING  | __main__ | ⚠️  This is a warning
2025-11-02 15:30:00 | ERROR    | __main__ | ❌ This is an error
```

---

## Migrating A File (3 Steps)

### Step 1: Add Import (Top of File)

```python
from daily_insights.logging_config import get_logger

logger = get_logger(__name__)
```

### Step 2: Replace print() Statements

```python
# BEFORE
print("Starting process...")
print(f"Processing {count} items from {source}")
print(f"Warning: File not found: {filename}")
print(f"Error: {error_message}")

# AFTER
logger.info("Starting process")
logger.info("Processing %d items from %s", count, source)
logger.warning("File not found: %s", filename)
logger.error("Operation failed: %s", error_message)
```

### Step 3: Test The File

```bash
# Syntax check
python3 -m py_compile daily_insights/[file].py

# Import test
python3 -c "from daily_insights.[module] import *"
```

**That's it! Takes 2-5 minutes per file.**

---

## Search & Replace Patterns

Use your editor's find/replace to speed up migration:

### Pattern 1: Simple Messages
```
Find:    print\("([^"]+)"\)
Replace: logger.info("\1")
```

### Pattern 2: F-Strings with One Variable
```
Find:    print\(f"([^{]+)\{(\w+)\}([^"]+)"\)
Replace: logger.info("\1%s\3", \2)
```

### Pattern 3: Warning Messages
```
Find:    print\(f?"Warning: ([^"]+)"\)
Replace: logger.warning("\1")
```

### Pattern 4: Error Messages
```
Find:    print\(f?"Error: ([^"]+)"\)
Replace: logger.error("\1")
```

---

## Log Level Decision Tree

```
Is it diagnostic/debug info? → logger.debug()
Is it normal operation info?  → logger.info()
Is it a potential problem?    → logger.warning()
Did an error occur?           → logger.error()
Is it a critical failure?     → logger.critical()
```

---

## Common Patterns

### Pattern: Progress Updates
```python
# BEFORE
print(f"Processing {filename}...")
print(f"Saved {count} records")

# AFTER
logger.info("Processing %s", filename)
logger.info("Saved %d records", count)
```

### Pattern: Skip/Ignore Messages
```python
# BEFORE
print(f"Skipping existing file: {filename}")

# AFTER (use DEBUG for routine skips)
logger.debug("Skipping existing file: %s", filename)
```

### Pattern: API Operations
```python
# BEFORE
print("Fetching data from API...")
print(f"Retrieved {len(results)} items")

# AFTER
logger.info("Fetching data from API")
logger.info("Retrieved %d items", len(results))
```

### Pattern: Error Handling
```python
# BEFORE
except Exception as e:
    print(f"Error: {e}")

# AFTER (exc_info=True adds full traceback)
except Exception as e:
    logger.error("Operation failed", exc_info=True)
```

### Pattern: File Operations
```python
# BEFORE
print(f"Reading file: {filepath}")
print(f"File not found: {filepath}")

# AFTER
logger.debug("Reading file: %s", filepath)
logger.warning("File not found: %s", filepath)
```

---

## Special Cases

### Keep print() For User Output

```python
# CLI user interaction - KEEP print()
print("=== Speaker Training Tool ===")
print("Known speakers:", ", ".join(speakers))
choice = input("Enter choice: ")  # Keep this

# Internal logging - USE logger
logger.info("User selected option: %s", choice)
```

### Keep print() For Formatted Displays

```python
# Pipeline statistics display - KEEP print()
print("\nPipeline Statistics:")
print(f"  Lifelogs Processed: {count}")
print(f"  Total Time: {duration}s")

# But log completion internally
logger.info("Pipeline completed: processed %d lifelogs in %.2fs", count, duration)
```

---

## Example: Full File Migration

**Before** (`api/limitless_client.py`):
```python
"""Client for interacting with the Limitless API."""
import requests

def fetch_new_lifelogs(existing_dates):
    print("\nStarting to fetch new lifelogs from Limitless...")

    page = 1
    while page <= max_pages:
        print(f"Fetching lifelogs page {page}...")

        try:
            response = _make_request(params)
        except requests.exceptions.RequestException as e:
            print(f"Request failed on page {page}: {e}")
            break

        if date_str in existing_dates:
            print(f"Found lifelog for existing date {date_str}. Stopping.")
            break

    print(f"Fetched {len(all_lifelogs)} new lifelogs")
    return all_lifelogs
```

**After** (`api/limitless_client.py`):
```python
"""Client for interacting with the Limitless API."""
import requests
from daily_insights.logging_config import get_logger

logger = get_logger(__name__)


def fetch_new_lifelogs(existing_dates):
    logger.info("Starting to fetch new lifelogs from Limitless")

    page = 1
    while page <= max_pages:
        logger.info("Fetching lifelogs page %d", page)

        try:
            response = _make_request(params)
        except requests.exceptions.RequestException as e:
            logger.error("Request failed on page %d", page, exc_info=True)
            break

        if date_str in existing_dates:
            logger.info("Found lifelog for existing date %s, stopping", date_str)
            break

    logger.info("Fetched %d new lifelogs", len(all_lifelogs))
    return all_lifelogs
```

**Changes Made**:
1. Added logger import and initialization (2 lines)
2. Replaced 5 print() statements with logger calls
3. Added `exc_info=True` for exception logging
4. Used lazy formatting (%d, %s) instead of f-strings

---

## Testing Your Changes

### After Migrating Each File

```bash
# 1. Syntax check
python3 -m py_compile daily_insights/api/limitless_client.py

# 2. Import test
python3 -c "from daily_insights.api.limitless_client import *"

# 3. Quick function test (if possible)
python3 << 'EOF'
from daily_insights.logging_config import setup_logging, get_logger
from pathlib import Path
setup_logging(log_level="DEBUG", log_file=Path("logs/test.log"))

# Import and test your migrated module
from daily_insights.api import limitless_client
# Test a function if safe to do so
EOF
```

### After Migrating Multiple Files

```bash
# Run the full pipeline
export LOG_LEVEL=DEBUG
python run_daily_insights.py

# Watch logs in real-time
tail -f logs/daily_insights.log
```

---

## Troubleshooting

### "No logs appearing"

**Check 1**: Is logging initialized?
```python
# In main.py, should be at the top
from daily_insights.logging_config import setup_logging
setup_logging(...)
```

**Check 2**: Is log level too high?
```bash
export LOG_LEVEL=DEBUG  # Show everything
```

**Check 3**: Is console output enabled?
```bash
export LOG_TO_CONSOLE=true
```

### "Log file not created"

**Check**: Does logs directory exist?
```bash
ls -la logs/
# If not:
mkdir -p logs
```

**Check**: Configuration correct?
```python
python3 << 'EOF'
from daily_insights.config import LOG_FILE, LOG_DIR
print(f"Log dir: {LOG_DIR}")
print(f"Log file: {LOG_FILE}")
print(f"Exists: {LOG_DIR.exists()}")
EOF
```

### "Import error after migration"

**Check**: Logger initialized in each file?
```python
# Each file needs:
from daily_insights.logging_config import get_logger
logger = get_logger(__name__)
```

---

## Configuration Tips

### Development: See Everything
```bash
export LOG_LEVEL=DEBUG
export LOG_TO_CONSOLE=true
export LOG_TO_FILE=false  # Optional: skip file logging
```

### Production: Normal Operations
```bash
export LOG_LEVEL=INFO
export LOG_TO_CONSOLE=true
export LOG_TO_FILE=true
```

### Debugging Issues: Maximum Detail
```bash
export LOG_LEVEL=DEBUG
export LOG_TO_FILE=true
export LOG_MAX_BYTES=52428800  # 50MB files
```

### Background Jobs: File Only
```bash
export LOG_LEVEL=INFO
export LOG_TO_CONSOLE=false
export LOG_TO_FILE=true
```

---

## Files To Migrate (Priority Order)

### Start Here (P1): 30 minutes
1. `main.py` - Entry point, initialize logging

### Then Do (P2): 2 hours
2. `api/limitless_client.py`
3. `api/openai_client.py`
4. `api/ollama_client.py`
5. `api/llm_client.py`
6. `api/speaker_llm_client.py`

### Next (P3): 3 hours
7. `services/lifelog_service.py`
8. `services/insights_service.py`
9. `services/bee_service.py`
10. `services/therapy_service.py`
11. `services/monthly_service.py`
12. `services/speaker_service.py`

### Then (P4): 1.5 hours
13. `models/conversation_parser.py`
14. `models/therapy_detection.py`
15. `utils/date_utils.py`
16. `utils/file_utils.py`
17. `utils/pipeline_stats.py` (selective)

### Finally (P5): 1 hour
18. `cli/speaker_commands.py` (selective - keep user-facing print())

---

## Quick Command Reference

```bash
# Initialize logging test
python3 -c "from daily_insights.logging_config import setup_logging; setup_logging()"

# Check print statements remaining
grep -r "print(" daily_insights/ --include="*.py" | wc -l

# Syntax check all Python files
find daily_insights -name "*.py" -exec python3 -m py_compile {} \;

# View recent logs
tail -20 logs/daily_insights.log

# Follow logs in real-time
tail -f logs/daily_insights.log

# Search logs for errors
grep "ERROR" logs/daily_insights.log

# Check log file sizes
ls -lh logs/
```

---

## Benefits You'll See

✅ **Immediate**:
- Professional logging instead of print statements
- Timestamps on every log message
- Can filter by severity (DEBUG, INFO, WARNING, ERROR)

✅ **Short-term**:
- Easy debugging (search logs by module, time, level)
- Persistent logs (don't lose output when terminal closes)
- Better troubleshooting (full exception tracebacks)

✅ **Long-term**:
- Production-ready monitoring
- Performance tracking capabilities
- Professional, maintainable codebase

---

## Need Help?

1. **Check design document**: `claudedocs/LOGGING_FRAMEWORK_DESIGN.md`
2. **Check status**: `claudedocs/LOGGING_IMPLEMENTATION_STATUS.md`
3. **Check code smell report**: `claudedocs/CODE_SMELL_REVIEW.md`

---

**Ready to Start?** → Pick main.py and follow the 3-step migration process above!

**Time Investment**: 8-10 hours total for all files
**Impact**: HIGH (resolves critical code smell, production-ready logging)
