# Journal Monthly Summary - Complete Design & Implementation Plan

**Date Created**: 2025-11-09
**Status**: Implemented
**Target Directory**: `./journal_monthly/`
**Output Filename Pattern**: `YYYY-MM.md`

---

## Executive Summary

This document provides a complete design and implementation specification for the journal monthly summary feature in the `daily_insights` system. The feature aggregates daily journal entries into comprehensive monthly reflection summaries using LLM processing.

**Key Design Decisions**:
- **Output filename**: `YYYY-MM.md` (simplified, no `-journal` suffix)
- **No minimum entries**: Process any month with at least 1 journal entry
- **Direct aggregation**: All daily entries → monthly summary (no weekly intermediate)
- **Token budget**: ~5K-9K tokens per month (well within LLM context limits)
- **Architecture pattern**: Follows `therapy_monthly_service.py` structure

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Token Analysis](#token-analysis)
3. [Configuration Specification](#configuration-specification)
4. [Service Implementation](#service-implementation)
5. [Integration Points](#integration-points)
6. [Prompt Template](#prompt-template)
7. [Data Flow](#data-flow)
8. [Testing & Validation](#testing--validation)
9. [Implementation Checklist](#implementation-checklist)
10. [Future Enhancements](#future-enhancements)

---

## Architecture Overview

### System Design Pattern

```
┌────────────────────────────────────────────────────────┐
│         Journal Monthly Summary Pipeline               │
└────────────────────────────────────────────────────────┘

Input Layer:
  ./journal/YYYY-MM-DD_journal.md (daily entries)
         ↓
Processing Layer:
  journal_monthly_service.py
         ↓
LLM Processing:
  - Combine all daily journal entries for month
  - Apply monthly journal prompt template
  - Generate comprehensive monthly summary
         ↓
Output Layer:
  ./journal_monthly/YYYY-MM.md
```

### Architectural Alignment

- **Pattern**: Direct aggregation (similar to `therapy_monthly_service.py`)
- **No intermediate layer**: No weekly summaries (sufficient for 7-8 entries/month)
- **Token efficiency**: ~5K-9K input tokens (well within context windows)
- **Consistency**: Follows existing monthly service conventions
- **Scalability**: Design supports future hierarchical approach if needed

---

## Token Analysis

### Current Data Statistics

Based on analysis of existing journal entries:

**Journal Entry Statistics**:
- **Total entries**: 41 journal files
- **Average entry size**: ~530 words
- **Largest entry**: 1,047 words
- **Typical monthly counts**: 7-8 entries

**Sample Monthly Statistics**:
- March 2025: 8 entries, ~6,000 words
- April 2025: 7 entries, ~3,600 words
- July 2025: 8 entries, ~4,500 words
- October 2025: 7 entries, ~2,700 words

### Token Estimation

**Token Calculation** (1 word ≈ 1.3 tokens):
- **Average month**: 7-8 entries × 530 words = ~3,700-4,200 words = **~4,800-5,500 input tokens**
- **Heavy month**: 8 entries × 750 words = ~6,000 words = **~7,800 input tokens**
- **With prompt overhead**: Add ~500-1,000 tokens for system prompt

**Total Input per Month**: ~5,000-9,000 tokens

### LLM Context Window Analysis

Current system supports:
- **GPT-4**: 8K-128K context window (depending on variant)
- **Ollama (llama3.2)**: Typically 8K-32K context window

**Conclusion**: NO token limit issues. Direct monthly summarization is viable for current and foreseeable journal entry volumes.

---

## Configuration Specification

### Environment Variables

**Added to `daily_insights/config.py`**:

```python
# Directory Paths (line ~41)
JOURNAL_MONTHLY_DIR = PROJECT_ROOT / os.getenv('JOURNAL_MONTHLY_DIR', 'journal_monthly')

# Prompt File Paths (line ~53)
JOURNAL_MONTHLY_PROMPT = PROJECT_ROOT / os.getenv('JOURNAL_MONTHLY_PROMPT', 'prompts/journal_monthly.txt')

# Feature Toggles (line ~260)
CREATE_JOURNAL_MONTHLY_SUMMARIES = _parse_bool(os.getenv('CREATE_JOURNAL_MONTHLY_SUMMARIES', 'true'))
```

**Updated `ensure_directories()` function** (line ~278):

```python
directories = [
    # ... existing directories ...
    JOURNAL_MONTHLY_DIR,  # ADDED
    # ... rest of directories ...
]
```

### .env Configuration

**Added to `.env` and `.env.example`**:

```bash
# Directory Paths
JOURNAL_MONTHLY_DIR=journal_monthly

# Prompt File Paths
JOURNAL_MONTHLY_PROMPT=prompts/journal_monthly.txt

# Feature Toggles
# CREATE_JOURNAL_MONTHLY_SUMMARIES - Generate monthly journal reflection summaries
# When disabled: Skips monthly journal summary generation
# Use case: Disable if not recording journal entries or to reduce LLM API costs
# Note: Requires PROCESS_JOURNAL_ENTRIES to be enabled for journal entries to exist
CREATE_JOURNAL_MONTHLY_SUMMARIES=true
```

---

## Service Implementation

### File: `daily_insights/services/journal_monthly_service.py`

**Core Functions**:

#### 1. `parse_journal_filename(filename: str) -> Optional[str]`

```python
"""
Extract date from journal entry filename.

Input:  "2025-03-22_journal.md"
Output: "2025-03-22"

Purpose: Parse journal filenames to extract dates for grouping
Pattern: Matches YYYY-MM-DD_journal.md format
"""
```

#### 2. `group_journals_by_month(journal_files: List[Path]) -> Dict[str, List[Path]]`

```python
"""
Group journal files by calendar month.

Input:  [Path("2025-03-22_journal.md"), Path("2025-03-28_journal.md")]
Output: {"2025-03": [Path("2025-03-22_journal.md"), Path("2025-03-28_journal.md")]}

Algorithm:
- Extract date from each journal filename
- Convert YYYY-MM-DD → YYYY-MM
- Group files by month string
- Return dict mapping months to file lists
"""
```

#### 3. `build_journal_monthly_summaries() -> None`

```python
"""
Build monthly summaries from daily journal entries (synchronous version).

Algorithm:
1. Scan JOURNAL_DIR for all journal files (YYYY-MM-DD_journal.md)
2. Group by calendar month using entry date
3. For each month with entries:
   a. Check if monthly summary already exists
   b. Skip if exists (one-time generation rule)
   c. Load monthly journal prompt template
   d. Read and combine all journal entries for that month
   e. Generate summary via LLM
   f. Save to JOURNAL_MONTHLY_DIR/YYYY-MM.md

Returns: None

Token Budget:
- Input: ~5K-9K tokens per month (7-8 entries × 600-750 words)
- Well within GPT-4/Llama context windows
- No chunking required
"""
```

#### 4. `build_journal_monthly_summaries_async() -> None`

```python
"""
Async version of build_journal_monthly_summaries.

Same algorithm as sync version but uses:
- read_file_async() for file I/O
- generate_summary_async() for LLM processing
- write_file_async() for output
- asyncio.Semaphore(3) for concurrent LLM calls
- asyncio.gather() for parallel month processing
"""
```

### Implementation Pattern

**Modeled after**: `therapy_monthly_service.py`

**Key similarities**:
- Direct aggregation (no weekly intermediate)
- One-time generation rule (skip existing summaries)
- Month-based grouping with defaultdict
- LLM summary generation
- Both sync and async versions

**Key differences**:
- Source: `JOURNAL_DIR` not `THERAPY_DIR`
- Filename pattern: `YYYY-MM-DD_journal.md` not `YYYY-MM-DD-psychologist.md`
- Output: `YYYY-MM.md` not `YYYY-MM-therapy.md`
- **No minimum entries check** (processes any month with ≥1 entry)

---

## Integration Points

### Main Pipeline Integration

**File: `daily_insights/main.py`**

**Config Imports** (added at line ~17):

```python
from daily_insights.config import (
    # ... existing imports ...
    CREATE_JOURNAL_MONTHLY_SUMMARIES,  # ADDED
)
```

**Service Imports** (added at line ~56):

```python
from daily_insights.services.journal_monthly_service import (
    build_journal_monthly_summaries,
    build_journal_monthly_summaries_async
)
```

**Sync Pipeline** (added after therapy monthly summaries, line ~129):

```python
if CREATE_JOURNAL_MONTHLY_SUMMARIES:
    build_journal_monthly_summaries()
else:
    logger.info("Skipping journal monthly summaries (CREATE_JOURNAL_MONTHLY_SUMMARIES=False)")
```

**Async Pipeline** (added to summary_tasks, line ~235):

```python
if CREATE_JOURNAL_MONTHLY_SUMMARIES:
    summary_tasks.append(build_journal_monthly_summaries_async())
else:
    logger.info("Skipping journal monthly summaries (CREATE_JOURNAL_MONTHLY_SUMMARIES=False)")
```

### Service Exports

**File: `daily_insights/services/__init__.py`**

```python
from .journal_monthly_service import build_journal_monthly_summaries

__all__ = [
    # ... existing exports ...
    "build_journal_monthly_summaries",
]
```

---

## Prompt Template

### File: `prompts/journal_monthly.txt`

**Structure Overview**:

```markdown
# Monthly Journal Reflection Summary

ROLE: Personal journaling assistant creating monthly reflections

TASK: Synthesize daily entries into cohesive monthly narrative

CRITICAL INSTRUCTIONS:
- Write in FIRST PERSON
- Focus on themes, patterns, insights, and growth
- DO NOT summarize chronologically
- Be reflective, introspective, and authentic

SECTIONS:
1. Month Overview (2-3 paragraphs)
2. Dominant Themes & Patterns (4-6 themes)
3. Significant Events & Milestones (3-5 moments)
4. Personal Growth & Insights
5. Challenges & How You Met Them
6. Relationships & Connections
7. Creative Life & Expression
8. Physical & Practical Life
9. Looking Forward
10. Gratitude & Appreciation
11. Month in a Sentence
12. Closing Reflection (2-3 paragraphs)
```

**Key Features**:
- First-person perspective throughout
- Thematic organization (not chronological)
- Emphasis on patterns, growth, and meaning
- Reflective and introspective tone
- Balanced coverage of emotional, practical, and relational domains
- Forward-looking intentions

**Model Parameters**:
- **Temperature**: 0.7 (balanced creativity and coherence)
- **Max output tokens**: 2000-3000
- **Context window**: 8K minimum required

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Flow Architecture                   │
└─────────────────────────────────────────────────────────────┘

Stage 1: Source Discovery
  ./journal/
    ├─ 2025-03-22_journal.md (850 words)
    ├─ 2025-03-23_journal.md (920 words)
    ├─ 2025-03-28_journal.md (1,050 words)
    └─ ... (5 more entries)
         ↓ parse_journal_filename()
         ↓ group_journals_by_month()

Stage 2: Month Grouping
  {"2025-03": [8 journal files]}
         ↓ check existing summaries

Stage 3: Content Aggregation
  Combined content: ~6,000 words
  Token count: ~7,800 input tokens
         ↓ read all journal files
         ↓ combine with prompt template

Stage 4: LLM Processing
  Prompt + Journals → LLM
  Input: 7,800 tokens
  Output: 2,000 tokens
         ↓ generate_summary()

Stage 5: Output
  ./journal_monthly/2025-03.md
  [Saved monthly summary]
```

---

## Testing & Validation

### Test Scenarios

**Scenario 1: Normal Month (7-8 entries)**
```bash
# Expected behavior:
- Successfully groups 7-8 journal entries
- Generates coherent monthly summary
- Token usage: ~5K-9K input tokens
- Processing time: <30s
- Output: ./journal_monthly/YYYY-MM.md
```

**Scenario 2: Light Month (1-3 entries)**
```bash
# Expected behavior:
- Processes month with minimal entries
- Generates proportionate summary
- No minimum entries requirement
- Token usage: ~1K-3K input tokens
```

**Scenario 3: Heavy Month (10+ entries)**
```bash
# Expected behavior:
- Successfully handles larger volume
- Token usage: ~10K-15K input tokens
- Still well within context limits
- May take slightly longer to process
```

**Scenario 4: Existing Summary**
```bash
# Expected behavior:
- Detects existing YYYY-MM.md file
- Skips generation (one-time rule)
- Logs: "Skipping existing monthly journal summary: ..."
```

**Scenario 5: No Journal Entries**
```bash
# Expected behavior:
- Logs: "No journal entry files found. Skipping..."
- Exits gracefully
- No error or crash
```

### Validation Checklist

- [ ] Monthly summaries generated for all complete months
- [ ] Output filenames match pattern: `YYYY-MM.md`
- [ ] Summaries written in first person
- [ ] Thematic organization (not chronological)
- [ ] One-time generation rule working correctly
- [ ] Existing summaries properly skipped
- [ ] Token usage within expected ranges
- [ ] Processing completes without errors
- [ ] Async version processes months in parallel
- [ ] Directory creation automatic on first run

---

## Implementation Checklist

### Phase 1: Configuration ✅

- [x] Add config variables to `config.py`
  - [x] JOURNAL_MONTHLY_DIR
  - [x] JOURNAL_MONTHLY_PROMPT
  - [x] CREATE_JOURNAL_MONTHLY_SUMMARIES
- [x] Update `ensure_directories()` function
- [x] Add environment variables to `.env.example`
  - [x] JOURNAL_MONTHLY_DIR
  - [x] JOURNAL_MONTHLY_PROMPT
  - [x] CREATE_JOURNAL_MONTHLY_SUMMARIES

### Phase 2: Service Development ✅

- [x] Create `journal_monthly_service.py`
- [x] Implement `parse_journal_filename()`
- [x] Implement `group_journals_by_month()`
- [x] Implement `build_journal_monthly_summaries()` (sync)
- [x] Implement `build_journal_monthly_summaries_async()`
- [x] Add docstrings and type hints

### Phase 3: Integration ✅

- [x] Update `main.py` with journal monthly logic
  - [x] Add import for CREATE_JOURNAL_MONTHLY_SUMMARIES
  - [x] Add import for journal monthly service functions
  - [x] Add sync processing logic (after therapy monthly)
  - [x] Add async processing logic (to summary_tasks)
- [x] Update `services/__init__.py` exports

### Phase 4: Prompts ✅

- [x] Create `prompts/journal_monthly.txt`
  - [x] First-person perspective instructions
  - [x] Thematic organization structure
  - [x] Comprehensive section breakdown
  - [x] Reflective and introspective tone

### Phase 5: Documentation ✅

- [x] Create comprehensive design plan (`claudedocs/JOURNAL_MONTHLY_PLAN.md`)
- [x] Document configuration options
- [x] Include token analysis
- [x] Provide implementation details

### Phase 6: Testing (Next Steps)

- [ ] Test with 3 entries (light month)
- [ ] Test with 7-8 entries (typical month)
- [ ] Test with 10+ entries (heavy month)
- [ ] Verify one-time generation rule
- [ ] Verify existing summary skip logic
- [ ] Test async pipeline
- [ ] Review output quality and prompt effectiveness

---

## Configuration Matrix

| Component | Value | Source | Rationale |
|-----------|-------|--------|-----------|
| **Input Directory** | `./journal/` | JOURNAL_DIR | Daily journal entries |
| **Output Directory** | `./journal_monthly/` | JOURNAL_MONTHLY_DIR | Monthly summaries |
| **Filename Pattern** | `YYYY-MM-DD_journal.md` | Existing convention | Match journal_service.py |
| **Output Pattern** | `YYYY-MM.md` | New convention | Simplified, clean naming |
| **Min Entries** | None | Design decision | Process any month with ≥1 entry |
| **Prompt File** | `prompts/journal_monthly.txt` | JOURNAL_MONTHLY_PROMPT | Monthly summary instructions |
| **Feature Flag** | `CREATE_JOURNAL_MONTHLY_SUMMARIES` | .env | Enable/disable processing |
| **Generation Rule** | One-time | Architecture decision | Consistent with other monthlies |

---

## Future Enhancements

### Enhancement 1: Weekly Summaries (Optional)

If journaling frequency increases to >10 entries/month:

**Implementation**:
- Create `journal_weekly_service.py`
- Hierarchical: daily → weekly → monthly
- Similar to insights pipeline architecture

**Benefits**:
- Better token management for high-volume months
- Weekly review checkpoints
- Consistent with insights pipeline

### Enhancement 2: Multi-Month Summaries

Aggregate multiple months into quarterly or yearly summaries:

**Implementation**:
- `journal_quarterly_service.py`
- Input: 3 monthly summaries
- Output: Quarterly reflection

**Benefits**:
- Higher-level pattern recognition
- Long-term growth tracking
- Annual review capabilities

### Enhancement 3: Theme Extraction

Add ML-based theme extraction:

**Features**:
- Automatic recurring topic identification
- Cross-reference themes across months
- Generate theme-based insights
- Trend analysis over time

**Technical Approach**:
- NLP for topic modeling
- Sentiment analysis integration
- Pattern visualization

### Enhancement 4: Personalization

Adapt prompt based on writing style:

**Features**:
- Detect user's journaling style
- Customize prompt tone and focus
- Learn preferred summary structure
- Adjust depth based on entry detail level

---

## Success Metrics

- **Completeness**: 100% of months with entries processed
- **Quality**: Coherent, reflective summaries in first person
- **Performance**: Processing time <30s per month
- **Reliability**: Zero data loss or corruption
- **Maintainability**: Code follows existing patterns
- **User Satisfaction**: Summaries provide meaningful insights

---

## Appendix: Key Design Decisions

### Decision 1: Output Filename Format

**Decision**: Use `YYYY-MM.md` instead of `YYYY-MM-journal.md`

**Rationale**:
- Simpler, cleaner naming
- Consistent with monthly insights pattern
- Directory name (journal_monthly) already provides context
- Easier to type and reference

### Decision 2: No Minimum Entries Requirement

**Decision**: Process any month with ≥1 journal entry (no JOURNAL_MONTHLY_MIN_ENTRIES)

**Rationale**:
- Journals are inherently personal and irregular
- Even single entries can provide valuable monthly context
- Simpler configuration (fewer variables)
- User can control via feature flag if desired
- Therapy sessions need minimums for clinical validity; journals don't

### Decision 3: Direct Monthly Aggregation

**Decision**: Skip weekly intermediate summaries

**Rationale**:
- Current volume (7-8 entries/month) is manageable
- Token budget well within limits (~5K-9K)
- Simpler architecture and maintenance
- Can add weekly layer later if needed
- Preserves detailed context for monthly summary

### Decision 4: One-Time Generation Rule

**Decision**: Generate summaries once, skip if file exists

**Rationale**:
- Consistent with therapy_monthly and monthly_service patterns
- Prevents regeneration costs
- Stable historical record
- Users can manually delete to regenerate if needed

---

## Implementation Notes

**Completed**: 2025-11-09

**Files Created**:
1. `daily_insights/services/journal_monthly_service.py` - Core service logic
2. `prompts/journal_monthly.txt` - LLM prompt template
3. `claudedocs/JOURNAL_MONTHLY_PLAN.md` - This design document

**Files Modified**:
1. `daily_insights/config.py` - Added configuration variables
2. `daily_insights/main.py` - Integrated into pipeline
3. `daily_insights/services/__init__.py` - Added exports
4. `.env.example` - Added environment variable documentation

**Next Steps**:
1. Test with actual journal entries
2. Review generated summary quality
3. Refine prompt based on output
4. Monitor token usage in production
5. Gather user feedback for improvements

---

**Document Version**: 1.0
**Last Updated**: 2025-11-09
**Maintained By**: Claude Code Implementation
