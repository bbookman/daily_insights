# Journal Entry Extraction Feature - Implementation Plan

## 1. Feature Overview

Extract journal entries from lifelog files and generate formatted markdown documents. This feature will:
- Detect journal entries in lifelog markdown files
- Extract complete journal entry text
- Process through LLM using existing prompt template
- Generate formatted markdown output with duplicate prevention

---

## 2. Architecture & Integration Points

### 2.1 Module Location
**File:** `daily_insights.py` (add new functions to existing file)

**Rationale:** Follows existing pattern of feature functions (`fetch_new_lifelogs()`, `fetch_chats()`, `build_weekly_summaries()`)

### 2.2 Directory Structure
```
/journal/                          # NEW: Output directory for journal files
  YYYY-MM-DD_journal.md           # Format: date_journal.md
/lifelogs/                         # EXISTING: Source lifelog files
  YYYY-MM-DD.md                   # Input source
/prompts/
  journal.txt                      # EXISTING: LLM prompt template
```

### 2.3 Configuration Constants (add to `daily_insights.py`)
```python
JOURNAL_DIR = "./journal"
JOURNAL_PROMPT_FILE = os.path.join(PROMPTS_DIR, "journal.txt")

# Add to os.makedirs() section:
os.makedirs(JOURNAL_DIR, exist_ok=True)
```

---

## 3. Implementation Steps

### Step 1: Journal Entry Detection Function
**Function Name:** `detect_journal_entries(lifelog_content: str) -> List[Tuple[int, int]]`

**Purpose:** Find start and end positions of journal entries in lifelog text

**Logic:**
1. Search for "journal entry" (case-insensitive) to find START marker
2. From each start position, search forward for END marker:
   - Pattern: phrases containing "end", "journal", "entry" (e.g., "end journal entry")
   - OR: Time hints (pause to next log section, indicated by `### HH:MM` markers)
3. Return list of (start_pos, end_pos) tuples

**Error Handling:**
- If start found but no end: log warning, use end of file as fallback
- If no entries found: return empty list

**Return Type:** `List[Tuple[int, int]]` (character positions)

---

### Step 2: Journal Extraction Function
**Function Name:** `extract_journal_text(lifelog_content: str, start_pos: int, end_pos: int) -> str`

**Purpose:** Extract and clean journal text between markers, preserving contextual headers

**Logic:**
1. Extract substring between start_pos and end_pos
2. Clean up strategically:
   - **KEEP:** Time markers (`### HH:MM`) - shows when journal started
   - **KEEP:** Topic headers (`## Topic Name`) - provides context/theme
   - **REMOVE:** Auto-generated descriptive headers (e.g., `### The speaker records a journal entry about...`)
   - **REMOVE:** Speaker attribution format (e.g., `- Bruce (3/1/25 9:39 AM):`)
   - **KEEP:** Actual journal content (the spoken text)
3. Convert speaker attribution to clean text:
   - Input: `- Bruce (3/1/25 9:39 AM): I am stepping down because...`
   - Output: `I am stepping down because...`
4. Strip leading/trailing whitespace

**Header Removal Strategy:**
- Remove lines matching: `^### (The speaker|The user|Unknown|Bruce|Russell).*`
- Keep lines matching: `^### \d{2}:\d{2}` (time markers)
- Keep lines matching: `^## ` (topic headers)

**Return Type:** `str` (cleaned journal text with preserved context)

---

### Step 3: Date Extraction Function
**Function Name:** `extract_date_from_lifelog_filename(filename: str) -> Optional[str]`

**Purpose:** Parse date from lifelog filename

**Logic:**
1. Use regex: `r"(\d{4}-\d{2}-\d{2})\.md"`
2. Extract YYYY-MM-DD format
3. Validate date is valid (use `dateutil.parser.parse()`)

**Error Handling:**
- If date invalid/unparseable: log error, return None
- If filename doesn't match pattern: return None

**Return Type:** `Optional[str]` (YYYY-MM-DD or None)

---

### Step 4: Duplicate Prevention Function
**Function Name:** `journal_file_exists(date_str: str) -> bool`

**Purpose:** Check if journal file already exists for given date

**Logic:**
1. Construct expected filename: `{date_str}_journal.md`
2. Check if file exists in JOURNAL_DIR
3. Return boolean

**Return Type:** `bool`

---

### Step 5: LLM Processing Function
**Function Name:** `process_journal_with_llm(journal_text: str) -> str`

**Purpose:** Send journal text to LLM using existing prompt template

**Logic:**
1. Load prompt from `JOURNAL_PROMPT_FILE`
2. Combine: `{prompt_text}\n\n{journal_text}`
3. Call Ollama API (reuse pattern from `build_weekly_summaries()`)
4. Collect streamed response
5. Return formatted markdown

**Error Handling:**
- If prompt file missing: log error, raise exception
- If LLM request fails: log error, raise exception
- If response empty: log warning, return empty string

**Return Type:** `str` (formatted markdown)

---

### Step 6: Main Orchestration Function
**Function Name:** `extract_and_process_journals()`

**Purpose:** Main entry point for journal extraction feature

**Logic:**
1. Scan all lifelog files in LIFELOGS_DIR
2. For each lifelog file:
   a. Extract date from filename
   b. Check if journal already exists (skip if yes, log message)
   c. Read lifelog content
   d. Detect journal entries
   e. For each journal entry found:
      - Extract text
      - Process with LLM
      - Save to `{date}_journal.md`
      - Log success
3. Print summary statistics

**Error Handling:**
- Wrap each file processing in try-except
- Log all errors but continue processing
- Report summary: files processed, journals created, errors encountered

---

## 4. Error Handling Strategy

| Scenario | Handling |
|----------|----------|
| Journal start found, no end | Use end of file; log warning |
| Date unparseable from filename | Skip file; log error |
| Journal file already exists | Skip; log "Skipping duplicate" |
| Prompt file missing | Log error; raise exception |
| LLM request fails | Log error; raise exception |
| Empty LLM response | Log warning; save empty file or skip |
| Malformed lifelog content | Log error; continue to next file |
| No headers to preserve | Still extract content; headers are optional |
| Extraction produces empty text | Log warning; skip LLM processing |

---

## 5. Header Preservation Strategy (Critical Detail)

### Why Headers Matter

Lifelog files contain **three types of headers** with different purposes:

```
### 09:44                                    ← TIME MARKER (KEEP)
## Work difficulties                         ← TOPIC HEADER (KEEP)
### The speaker records a journal entry...   ← AUTO-GENERATED SUMMARY (REMOVE)
- Bruce (8/13/25 9:38 AM): All right...     ← SPEAKER ATTRIBUTION (REMOVE)
```

### Header Handling Rules

| Header Pattern | Example | Action | Reason |
|---|---|---|---|
| `^### \d{2}:\d{2}` | `### 09:44` | **KEEP** | Shows when journal started |
| `^## [A-Z]` | `## Work difficulties` | **KEEP** | Provides topic/theme context |
| `^### (The speaker\|The user)` | `### The speaker records...` | **REMOVE** | Auto-generated, redundant |
| `^- [A-Za-z]+ \(\d{1,2}/\d{1,2}` | `- Bruce (8/13/25 9:38 AM):` | **REMOVE** | Extract text only |

---

## 6. LLM Prompt Structure

**File:** `prompts/journal.txt` ✅ **CREATED**

**Status:** Complete and ready for use

**Key Features:**
- Comprehensive formatting guidelines for journal entries
- Emphasis on preserving authentic voice and emotional truth
- Specific markdown formatting conventions
- Output structure template
- Processing steps and quality checklist
- Real example transformation

**See:** `JOURNAL_PROMPT_CREATION.md` for detailed documentation

---

## 7. Integration with Main Pipeline

**Current main() flow:**
```python
if __name__ == "__main__":
    new_lifelogs = fetch_new_lifelogs()
    save_lifelogs(new_lifelogs)
    fetch_chats()
    build_weekly_summaries()
```

**Proposed addition:**
```python
if __name__ == "__main__":
    new_lifelogs = fetch_new_lifelogs()
    save_lifelogs(new_lifelogs)
    fetch_chats()
    extract_and_process_journals()  # NEW
    build_weekly_summaries()
```

---

## 8. Testing Strategy

**Unit Tests Needed:**
1. `test_detect_journal_entries()` - Various entry patterns
2. `test_extract_journal_text()` - Text cleaning
3. `test_extract_date_from_lifelog_filename()` - Date parsing
4. `test_journal_file_exists()` - Duplicate detection
5. `test_process_journal_with_llm()` - LLM integration
6. `test_extract_and_process_journals()` - End-to-end flow

**Test Data:** Use sample lifelog files from `lifelogs/` directory

---

## 9. Implementation Order

1. ✅ Create `extract_date_from_lifelog_filename()` (simplest)
2. ✅ Create `journal_file_exists()` (simple file check)
3. ✅ Create `detect_journal_entries()` (core logic)
4. ✅ Create `extract_journal_text()` (text processing)
5. ✅ Create `process_journal_with_llm()` (LLM integration)
6. ✅ Create `extract_and_process_journals()` (orchestration)
7. ✅ Update `main()` to call new function
8. ✅ Write comprehensive tests
9. ✅ Validate with real lifelog data

---

## 10. Key Reusable Patterns from Codebase

| Pattern | Source | Reuse |
|---------|--------|-------|
| Date parsing | `save_lifelogs()` | Use `dateutil.parser.parse()` |
| File scanning | `get_existing_lifelog_dates()` | Use `Path.glob()` pattern |
| LLM streaming | `build_weekly_summaries()` | Reuse Ollama request pattern |
| Prompt loading | `build_weekly_summaries()` | Load from file, combine with content |
| Error handling | Throughout | Use try-except with logging |

---

## 11. Success Criteria

- ✅ All journal entries detected correctly
- ✅ Duplicate files skipped with logging
- ✅ LLM processing produces valid markdown
- ✅ Output files saved to `/journal/` with correct naming
- ✅ All error cases handled gracefully
- ✅ Comprehensive test coverage
- ✅ Integration with main pipeline

