# Biographical System - Technical Design Specification

**Created**: 2025-11-09
**Status**: Design Phase
**Prerequisites**: BIOGRAPHICAL_SYSTEM_REQUIREMENTS.md

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Service Design](#2-service-design)
3. [Data Models](#3-data-models)
4. [Processing Pipeline](#4-processing-pipeline)
5. [Prompt Engineering](#5-prompt-engineering)
6. [File Management](#6-file-management)
7. [Integration Points](#7-integration-points)
8. [Error Handling](#8-error-handling)
9. [Performance Considerations](#9-performance-considerations)
10. [Testing Strategy](#10-testing-strategy)

---

## 1. System Architecture

### 1.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Daily Insights Pipeline                      │
└─────────────────────────────────────────────────────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
         ┌──────────┐     ┌──────────┐    ┌──────────┐
         │ Lifelogs │     │ Journals │    │   Bee    │
         │          │     │          │    │ Transcr. │
         └────┬─────┘     └────┬─────┘    └────┬─────┘
              │                │               │
              │  Pass 1        │  Pass 1       │  Pass 1
              │  (Existing)    │  (Existing)   │  (Existing)
              │                │               │
              ▼                ▼               ▼
         ┌──────────┐     ┌──────────┐    ┌──────────┐
         │ Formatted│     │ Formatted│    │ Formatted│
         │ Daily    │     │ Journal  │    │   Bee    │
         │ Insights │     │  Entry   │    │  Entry   │
         └──────────┘     └──────────┘    └──────────┘
              │                │               │
              │  Pass 2 (NEW)  │  Pass 2 (NEW) │  Pass 2 (NEW)
              │                │               │
              └────────────────┼───────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Biographical       │
                    │  Detection Service  │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
         ┌──────────┐   ┌──────────┐  ┌──────────┐
         │  PERSON  │   │  PLACE   │  │  OBJECT  │
         │Detection │   │Detection │  │Detection │
         └────┬─────┘   └────┬─────┘  └────┬─────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                             ▼
                  ┌────────────────────┐
                  │  Biography File    │
                  │  Management        │
                  └──────────┬─────────┘
                             │
                ┌────────────┼────────────┐
                │            │            │
                ▼            ▼            ▼
         ┌──────────┐ ┌──────────┐ ┌──────────┐
         │  Create  │ │  Update  │ │Synthesize│
         │   New    │ │ Existing │ │ Current  │
         │Biography │ │Biography │ │Understanding│
         └──────────┘ └──────────┘ └──────────┘
                             │
                             ▼
                  ┌────────────────────┐
                  │  Biography Files   │
                  │  /people/*.md      │
                  │  /places/*.md      │
                  │  /objects/*.md     │
                  └────────────────────┘
```

### 1.2 Architectural Layers

**Layer 1: Source Processing**
- Existing: Lifelog formatting, journal processing, bee transcription
- New: Pass 2 biographical extraction runs on same raw sources

**Layer 2: Detection & Extraction**
- Biographical content detection using `person_place_thing.txt` prompt
- Smart tiering: full 3-paragraph vs lightweight extraction
- Category classification: person/place/object

**Layer 3: File Management**
- Biography file CRUD operations
- Chronological entry appending
- Synthesis regeneration scheduling

**Layer 4: Storage**
- Organized directory structure
- Master biography files
- Timestamped updates

---

## 2. Service Design

### 2.1 Core Service: `biography_service.py`

```python
"""
Service for managing biographical documentation system.

Provides functionality for:
- Detecting biographical content in transcripts
- Extracting biographical information
- Managing biography master files
- Synthesizing accumulated knowledge
"""

from pathlib import Path
from typing import Optional, Dict, List, Tuple
from enum import Enum
import re
import asyncio

from daily_insights.config import (
    BIOGRAPHIES_DIR,
    BIOGRAPHY_PROMPT,
    BIOGRAPHY_LIGHT_PROMPT,
    BIOGRAPHY_SYNTHESIS_PROMPT,
    PROCESS_BIOGRAPHIES
)
from daily_insights.api.llm_client import generate_summary, generate_summary_async
from daily_insights.utils.file_utils import read_file, write_file, read_file_async, write_file_async
from daily_insights.utils.date_utils import get_current_date


class BiographyCategory(Enum):
    """Biography subject categories."""
    PERSON = "people"
    PLACE = "places"
    OBJECT = "objects"


class ContentDepth(Enum):
    """Depth of biographical content detected."""
    NONE = "none"              # Not biographical
    LIGHTWEIGHT = "lightweight"  # Brief mentions
    FULL = "full"               # Deep biographical focus


# ============================================================================
# Detection Functions
# ============================================================================

def detect_biographical_content(
    raw_transcript: str,
    source_type: str,
    date: str
) -> Optional[Dict]:
    """
    Detect if transcript contains biographical content.

    Parameters
    ----------
    raw_transcript : str
        Raw transcript text to analyze
    source_type : str
        Type of source (journal, lifelog, bee)
    date : str
        Date of transcript (YYYY-MM-DD)

    Returns
    -------
    Optional[Dict]
        Biographical content info or None if not biographical
        {
            'subject_name': str,
            'category': BiographyCategory,
            'depth': ContentDepth,
            'content': str,
            'date': str,
            'source_type': str
        }
    """
    pass


async def detect_biographical_content_async(
    raw_transcript: str,
    source_type: str,
    date: str
) -> Optional[Dict]:
    """Async version of detect_biographical_content."""
    pass


def extract_biographical_content(
    raw_transcript: str,
    depth: ContentDepth,
    prompt_text: str
) -> str:
    """
    Extract biographical content using appropriate prompt.

    Parameters
    ----------
    raw_transcript : str
        Raw transcript to process
    depth : ContentDepth
        FULL or LIGHTWEIGHT extraction
    prompt_text : str
        Prompt template to use

    Returns
    -------
    str
        Extracted biographical content
    """
    pass


async def extract_biographical_content_async(
    raw_transcript: str,
    depth: ContentDepth,
    prompt_text: str
) -> str:
    """Async version of extract_biographical_content."""
    pass


# ============================================================================
# File Management Functions
# ============================================================================

def get_biography_filepath(
    subject_name: str,
    category: BiographyCategory
) -> Path:
    """
    Get filepath for biography.

    Parameters
    ----------
    subject_name : str
        Name of person/place/object
    category : BiographyCategory
        Subject category

    Returns
    -------
    Path
        Full path to biography file
    """
    pass


def biography_exists(
    subject_name: str,
    category: BiographyCategory
) -> bool:
    """Check if biography file exists."""
    pass


def create_biography_file(
    subject_name: str,
    category: BiographyCategory,
    initial_content: str,
    date: str,
    source_type: str
) -> Path:
    """
    Create new biography file with initial content.

    Parameters
    ----------
    subject_name : str
        Name of subject
    category : BiographyCategory
        Subject category
    initial_content : str
        First biographical entry
    date : str
        Date of entry
    source_type : str
        Source type (journal, lifelog, bee)

    Returns
    -------
    Path
        Path to created file
    """
    pass


def append_to_biography(
    subject_name: str,
    category: BiographyCategory,
    new_content: str,
    date: str,
    source_type: str
) -> Path:
    """
    Append new chronological entry to existing biography.

    Parameters
    ----------
    subject_name : str
        Name of subject
    category : BiographyCategory
        Subject category
    new_content : str
        New biographical content
    date : str
        Date of entry
    source_type : str
        Source type

    Returns
    -------
    Path
        Path to updated file
    """
    pass


# ============================================================================
# Synthesis Functions
# ============================================================================

def synthesize_biography(
    subject_name: str,
    category: BiographyCategory
) -> None:
    """
    Regenerate "Current Understanding" synthesis section.

    Parameters
    ----------
    subject_name : str
        Name of subject
    category : BiographyCategory
        Subject category
    """
    pass


async def synthesize_biography_async(
    subject_name: str,
    category: BiographyCategory
) -> None:
    """Async version of synthesize_biography."""
    pass


def batch_synthesize_biographies() -> None:
    """
    Synthesize all biographies marked for update.

    Scans all biography files for update markers
    and regenerates their synthesis sections.
    """
    pass


async def batch_synthesize_biographies_async() -> None:
    """Async version of batch_synthesize_biographies."""
    pass


# ============================================================================
# Main Processing Functions
# ============================================================================

def process_biographical_extraction(
    raw_transcript: str,
    source_type: str,
    date: str
) -> None:
    """
    Process transcript for biographical content.

    Main entry point for biographical extraction.

    Parameters
    ----------
    raw_transcript : str
        Raw transcript text
    source_type : str
        Type of source (journal, lifelog, bee)
    date : str
        Date of transcript
    """
    pass


async def process_biographical_extraction_async(
    raw_transcript: str,
    source_type: str,
    date: str
) -> None:
    """Async version of process_biographical_extraction."""
    pass


def process_all_biographies() -> None:
    """
    Main biographical processing pipeline.

    Workflow:
    1. Scan for unprocessed transcripts
    2. Extract biographical content
    3. Update biography files
    4. Batch synthesize updates
    """
    pass


async def process_all_biographies_async() -> None:
    """Async version of process_all_biographies."""
    pass
```

### 2.2 Utility Module: `biography_utils.py`

```python
"""
Utility functions for biographical system.
"""

from pathlib import Path
from typing import Tuple, Optional, List, Dict
import re


def sanitize_biography_filename(name: str) -> str:
    """
    Sanitize subject name for use as filename.

    Parameters
    ----------
    name : str
        Raw subject name

    Returns
    -------
    str
        Sanitized filename (e.g., "Dairy Queen" → "Dairy-Queen")

    Example
    -------
    >>> sanitize_biography_filename("Mike's Place")
    'Mikes-Place'
    >>> sanitize_biography_filename("Uncle Bob (Dad's brother)")
    'Uncle-Bob-Dads-brother'
    """
    # Remove special characters except spaces and hyphens
    cleaned = re.sub(r'[^\w\s-]', '', name)
    # Replace spaces with hyphens
    cleaned = re.sub(r'\s+', '-', cleaned.strip())
    # Remove multiple consecutive hyphens
    cleaned = re.sub(r'-+', '-', cleaned)
    return cleaned


def parse_biography_file(filepath: Path) -> Dict:
    """
    Parse biography file into structured data.

    Parameters
    ----------
    filepath : Path
        Path to biography file

    Returns
    -------
    Dict
        Parsed biography structure:
        {
            'subject_name': str,
            'last_updated': str,
            'current_understanding': str,
            'chronological_entries': List[Dict[str, str]]
        }
    """
    pass


def extract_chronological_entries(content: str) -> List[Dict]:
    """
    Extract chronological entries from biography content.

    Parameters
    ----------
    content : str
        Biography file content

    Returns
    -------
    List[Dict]
        List of entries with date, source_type, and content
    """
    pass


def format_chronological_entry(
    date: str,
    source_type: str,
    content: str
) -> str:
    """
    Format new chronological entry.

    Parameters
    ----------
    date : str
        Entry date (YYYY-MM-DD)
    source_type : str
        Source type (journal, lifelog, bee)
    content : str
        Biographical content

    Returns
    -------
    str
        Formatted entry for appending
    """
    template = f"""
### {date} ({source_type.title()})

{content}
"""
    return template


def detect_category_from_content(content: str) -> Optional[str]:
    """
    Detect if content is about person/place/object.

    Parameters
    ----------
    content : str
        Biographical content

    Returns
    -------
    Optional[str]
        Category string or None
    """
    pass


def mark_for_synthesis(filepath: Path) -> None:
    """
    Mark biography file for synthesis regeneration.

    Adds marker to file indicating synthesis needed.

    Parameters
    ----------
    filepath : Path
        Biography file path
    """
    pass


def needs_synthesis(filepath: Path) -> bool:
    """
    Check if biography needs synthesis regeneration.

    Parameters
    ----------
    filepath : Path
        Biography file path

    Returns
    -------
    bool
        True if needs synthesis
    """
    pass
```

---

## 3. Data Models

### 3.1 Biography File Format

```markdown
# [Subject Name] - Biographical Profile

**Last Updated**: YYYY-MM-DD

---

## Current Understanding (Auto-synthesized)

### Portrait

[5-10 sentences: Vivid description, defining characteristics, personality/atmosphere/appearance]

### Memory and Moments

[5-10 sentences: Key stories, memorable interactions, significant events]

### Meaning and Impact

[5-10 sentences: Personal significance, lessons learned, emotional connection]

---

## Chronological Insights

### YYYY-MM-DD (Source Type)

[Full biographical content from that date/source]

### YYYY-MM-DD (Source Type)

[Full biographical content from that date/source]
```

### 3.2 Detection Result Structure

```python
{
    'subject_name': 'Mike',
    'category': BiographyCategory.PERSON,
    'depth': ContentDepth.FULL,
    'content': '... extracted biographical narrative ...',
    'date': '2025-03-22',
    'source_type': 'journal'
}
```

### 3.3 Parsed Biography Structure

```python
{
    'subject_name': 'Mike',
    'last_updated': '2025-07-15',
    'current_understanding': {
        'portrait': '...',
        'memory_and_moments': '...',
        'meaning_and_impact': '...'
    },
    'chronological_entries': [
        {
            'date': '2025-03-22',
            'source_type': 'journal',
            'content': '...'
        },
        {
            'date': '2025-07-15',
            'source_type': 'lifelog',
            'content': '...'
        }
    ]
}
```

---

## 4. Processing Pipeline

### 4.1 Daily Processing Flow

```
┌─────────────────────────────────────────────────┐
│ 1. Daily Pipeline Starts                        │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 2. Fetch & Process Sources (Existing)           │
│    - Lifelogs → formatted daily insights        │
│    - Journals → formatted journal entries       │
│    - Bee → formatted bee entries                │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 3. Biographical Processing (NEW)                │
│    IF PROCESS_BIOGRAPHIES=true:                 │
│    For each raw transcript:                     │
│      a. detect_biographical_content()           │
│      b. IF biographical content detected:       │
│         - extract_biographical_content()        │
│         - IF biography exists:                  │
│             append_to_biography()               │
│           ELSE:                                 │
│             create_biography_file()             │
│         - mark_for_synthesis()                  │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 4. Continue Pipeline (Existing)                 │
│    - Therapy sessions                           │
│    - Doctor visits                              │
│    - Weekly summaries                           │
│    - Monthly summaries                          │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 5. Biographical Synthesis (NEW)                 │
│    batch_synthesize_biographies():              │
│    - Scan for biographies marked for synthesis  │
│    - For each marked biography:                 │
│        synthesize_biography()                   │
└─────────────────────────────────────────────────┘
```

### 4.2 Detection Logic Flow

```python
def detect_biographical_content(raw_transcript, source_type, date):
    """
    Detection logic flowchart:

    1. Load biography prompt (person_place_thing.txt)
    2. Combine prompt + raw transcript
    3. Send to LLM with instruction:
       "Detect if this is biographical content.
        Return JSON with:
        - is_biographical: true/false
        - subject_name: str or null
        - category: person/place/object or null
        - depth: full/lightweight or null

        If not biographical, return:
        {'is_biographical': false}

        If biographical, extract and return subject details."

    4. Parse LLM response
    5. If is_biographical=true:
         - Determine ContentDepth (full vs lightweight)
         - Return detection result
       Else:
         - Return None
    """
```

### 4.3 Synthesis Logic Flow

```python
def synthesize_biography(subject_name, category):
    """
    Synthesis logic flowchart:

    1. Load biography file
    2. Parse chronological entries
    3. Extract all biographical content
    4. Load synthesis prompt (biography_synthesis.txt)
    5. Combine prompt + all chronological entries
    6. Send to LLM with instruction:
       "Synthesize a 3-paragraph 'Current Understanding'
        from all accumulated knowledge below.

        Generate:
        ### Portrait
        [synthesis]

        ### Memory and Moments
        [synthesis]

        ### Meaning and Impact
        [synthesis]"

    7. Parse LLM response
    8. Update biography file:
       - Replace "Current Understanding" section
       - Update "Last Updated" timestamp
    9. Remove synthesis marker
    """
```

---

## 5. Prompt Engineering

### 5.1 Existing Prompts

**`prompts/person_place_thing.txt`** (Already Created)
- Purpose: Full biographical extraction
- Detects biographical intent
- Generates 3-paragraph narratives
- Returns "NOT_BIOGRAPHICAL" when criteria not met

### 5.2 New Prompts Required

**`prompts/biography_light_extraction.txt`**
```markdown
# Lightweight Biographical Extraction

You are extracting brief biographical mentions from transcripts.

**Task**: Extract key facts, memorable moments, or new insights about a
specific person/place/object mentioned in the transcript below.

**Output Format**:
- Subject: [Name of person/place/object]
- Category: [Person/Place/Object]
- Key Facts:
  - [Bullet point 1]
  - [Bullet point 2]
  - [Bullet point 3]
- Notable Moments:
  - [Brief description]
- New Insights:
  - [Any new information learned]

**Guidelines**:
- Extract only biographical information, not general content
- Focus on facts, characteristics, memories
- Keep it concise (3-5 bullet points per section)
- If no substantial biographical content, return: "NO_BIOGRAPHICAL_CONTENT"

---

TRANSCRIPT:
[raw transcript here]
```

**`prompts/biography_synthesis.txt`**
```markdown
# Biography Synthesis Prompt

You are synthesizing accumulated biographical knowledge into a cohesive
"Current Understanding" narrative.

**Task**: Read all the chronological biographical entries below and create
a comprehensive 3-paragraph synthesis representing your current, complete
understanding of this person/place/object.

**CRITICAL INSTRUCTIONS**:
- Write in FIRST PERSON, maintaining authentic voice
- Synthesize insights from ALL entries, not just the latest
- Create a cohesive narrative that integrates all accumulated knowledge
- Each paragraph MUST be substantial (5-10 sentences)
- Preserve emotional depth and personal significance

**Output Structure**:

### Portrait

[PARAGRAPH 1 - REQUIRED: 5-10 sentences]
Synthesize all descriptive details accumulated across entries:
- For PERSON: Personality, defining characteristics, presence, evolution
- For PLACE: Physical attributes, atmosphere, how it's changed over time
- For OBJECT: Appearance, physical qualities, how relationship has evolved

MUST paint a vivid, complete picture integrating all observations.

### Memory and Moments

[PARAGRAPH 2 - REQUIRED: 5-10 sentences]
Synthesize all significant stories and moments:
- Key interactions and experiences across all entries
- Memorable moments that define the relationship
- Evolution of experiences over time
- Specific anecdotes that capture the essence

MUST tell the story arc of this relationship/connection.

### Meaning and Impact

[PARAGRAPH 3 - REQUIRED: 5-10 sentences]
Synthesize overall significance and learning:
- How they've shaped you (accumulated over time)
- What you've learned through all interactions
- Deeper meaning and personal significance
- Current reflections on the relationship/connection

MUST reflect deeply on accumulated wisdom and growth.

---

## Chronological Biographical Entries

[All entries will be inserted here, in chronological order]

---

**Remember**: This synthesis represents your COMPLETE, CURRENT understanding
based on ALL accumulated knowledge. Integrate insights from every entry to
create a rich, cohesive portrait.
```

**`prompts/biography_detection.txt`**
```markdown
# Biographical Content Detection

You are analyzing a transcript to detect biographical content.

**Task**: Determine if this transcript contains substantial biographical
content about a specific person, place, or object.

**Biographical Criteria** (ANY of these):
1. Sustained focus: 10+ sentences about one subject
2. Deep exploration: Clearly documenting someone/somewhere/something
3. Storytelling intent: Mini-biography or character sketch
4. Rich detail: Extensive characteristics, memories, significance

**Output JSON Format**:
```json
{
  "is_biographical": true/false,
  "subject_name": "Name or null",
  "category": "person/place/object or null",
  "depth": "full/lightweight or null",
  "confidence": 0.0-1.0
}
```

**Depth Classification**:
- **full**: Meets biographical criteria above (10+ sentences, deep focus)
- **lightweight**: Brief but meaningful mentions (3-9 sentences, some detail)
- **null**: Not biographical

**Examples**:

Input: "Long detailed reflection about Mike and our friendship history..."
Output: {"is_biographical": true, "subject_name": "Mike", "category": "person", "depth": "full", "confidence": 0.95}

Input: "Mentioned seeing Mike briefly at coffee shop"
Output: {"is_biographical": true, "subject_name": "Mike", "category": "person", "depth": "lightweight", "confidence": 0.7}

Input: "General daily activities, various brief mentions"
Output: {"is_biographical": false, "subject_name": null, "category": null, "depth": null, "confidence": 0.9}

---

TRANSCRIPT:
[raw transcript here]
```

---

## 6. File Management

### 6.1 Directory Structure

```
BIOGRAPHIES_DIR/
├── people/
│   ├── Mike.md
│   ├── Larry.md
│   └── Mom.md
├── places/
│   ├── Dairy-Queen.md
│   └── Childhood-Home.md
└── objects/
    └── Fathers-Watch.md
```

### 6.2 File Operations

**Create Biography**:
```python
def create_biography_file(subject_name, category, initial_content, date, source_type):
    """
    1. Sanitize filename
    2. Ensure category directory exists
    3. Create file with structure:
       - Header with last_updated
       - Placeholder "Current Understanding" (synthesis comes later)
       - First chronological entry
    4. Mark for synthesis
    5. Return filepath
    """
```

**Append to Biography**:
```python
def append_to_biography(subject_name, category, new_content, date, source_type):
    """
    1. Read existing biography file
    2. Find "## Chronological Insights" section
    3. Append new formatted entry
    4. Update "Last Updated" timestamp
    5. Mark for synthesis
    6. Write updated file
    """
```

**Synthesize Biography**:
```python
def synthesize_biography(subject_name, category):
    """
    1. Read biography file
    2. Extract all chronological entries
    3. Load synthesis prompt
    4. Combine prompt + all entries
    5. Send to LLM
    6. Parse synthesis result
    7. Update "Current Understanding" section
    8. Update "Last Updated" timestamp
    9. Remove synthesis marker
    10. Write updated file
    """
```

---

## 7. Integration Points

### 7.1 Configuration Integration

**New Config Variables** (`daily_insights/config.py`):
```python
# Biographical System Configuration
PROCESS_BIOGRAPHIES = _parse_bool(os.getenv('PROCESS_BIOGRAPHIES', 'true'))
BIOGRAPHIES_DIR = PROJECT_ROOT / os.getenv('BIOGRAPHIES_DIR', 'biographies')

# Prompt Paths
BIOGRAPHY_PROMPT = PROJECT_ROOT / os.getenv('BIOGRAPHY_PROMPT', 'prompts/person_place_thing.txt')
BIOGRAPHY_LIGHT_PROMPT = PROJECT_ROOT / os.getenv('BIOGRAPHY_LIGHT_PROMPT', 'prompts/biography_light_extraction.txt')
BIOGRAPHY_SYNTHESIS_PROMPT = PROJECT_ROOT / os.getenv('BIOGRAPHY_SYNTHESIS_PROMPT', 'prompts/biography_synthesis.txt')
BIOGRAPHY_DETECTION_PROMPT = PROJECT_ROOT / os.getenv('BIOGRAPHY_DETECTION_PROMPT', 'prompts/biography_detection.txt')

# Ensure directories exist
def ensure_directories():
    """Create necessary directories."""
    directories = [
        # ... existing directories ...
        BIOGRAPHIES_DIR / 'people',
        BIOGRAPHIES_DIR / 'places',
        BIOGRAPHIES_DIR / 'objects',
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
```

### 7.2 Pipeline Integration

**Sync Pipeline** (`daily_insights/main.py`):
```python
def main():
    """Main sync pipeline."""

    # ... existing processing ...

    # Process journal entries (existing)
    if PROCESS_JOURNAL_ENTRIES:
        process_journal_entries()

    # NEW: Biographical processing
    if PROCESS_BIOGRAPHIES:
        logger.info("Processing biographical content...")
        process_all_biographies()
    else:
        logger.info("Skipping biographical processing (PROCESS_BIOGRAPHIES=False)")

    # ... continue existing pipeline ...
```

**Async Pipeline** (`daily_insights/main.py`):
```python
async def main_async():
    """Main async pipeline."""

    # ... existing processing ...

    # NEW: Biographical processing
    if PROCESS_BIOGRAPHIES:
        logger.info("Processing biographical content (async)...")
        await process_all_biographies_async()
    else:
        logger.info("Skipping biographical processing (PROCESS_BIOGRAPHIES=False)")

    # ... continue existing pipeline ...
```

### 7.3 Service Exports

**`daily_insights/services/__init__.py`**:
```python
from .biography_service import (
    process_all_biographies,
    process_all_biographies_async,
    process_biographical_extraction,
    process_biographical_extraction_async,
)

__all__ = [
    # ... existing exports ...
    "process_all_biographies",
    "process_all_biographies_async",
    "process_biographical_extraction",
    "process_biographical_extraction_async",
]
```

---

## 8. Error Handling

### 8.1 Error Categories

**Detection Errors**:
- LLM returns malformed JSON
- LLM cannot determine if biographical
- Transcript too short or empty

**Extraction Errors**:
- LLM fails to extract content
- Extracted content is empty or invalid
- Prompt template missing or corrupted

**File Management Errors**:
- Biography file corrupted or malformed
- Unable to write to biography directory
- Parsing errors in existing biography

**Synthesis Errors**:
- LLM fails to generate synthesis
- Synthesis result is incomplete
- Unable to update biography file

### 8.2 Error Handling Strategy

```python
def process_biographical_extraction(raw_transcript, source_type, date):
    """
    Error handling approach:

    1. Try detection
       - Catch malformed JSON → log warning, skip
       - Catch LLM timeout → retry once, then skip
       - Catch empty response → log info, skip

    2. Try extraction
       - Catch extraction failure → log error, save raw for manual review
       - Catch empty content → log warning, skip

    3. Try file operations
       - Catch file write errors → log error, retry once
       - Catch parsing errors → log error, backup corrupted file, recreate

    4. Log all failures to dedicated biographical_errors.log
    5. Continue processing (don't halt pipeline)
    6. Report statistics at end (X processed, Y failed)
    """
```

### 8.3 Logging Strategy

```python
import logging

logger = logging.getLogger('daily_insights.biography')

# Log levels:
# DEBUG: Detailed detection/extraction steps
# INFO: Biography created/updated, synthesis completed
# WARNING: Skipped content, minor issues
# ERROR: Failed operations, corrupted files
# CRITICAL: System-level failures affecting all biographies
```

---

## 9. Performance Considerations

### 9.1 LLM Call Optimization

**Batch Processing**:
- Process multiple transcripts in parallel (async)
- Limit concurrent LLM calls with semaphore
- Suggested: `semaphore = asyncio.Semaphore(3)`

**Caching Strategy**:
- Cache detection results for same transcript
- Cache prompt templates (load once at startup)
- Don't re-process already-processed transcripts

**Selective Processing**:
- Skip synthesis if no new entries added today
- Only synthesize marked biographies

### 9.2 File I/O Optimization

**Async File Operations**:
- Use `aiofiles` for async file reads/writes
- Batch multiple file operations

**Incremental Updates**:
- Don't re-parse entire biography for append
- Use append mode for chronological entries

### 9.3 Resource Usage

**Estimated LLM Costs**:
- Detection: ~500 tokens per transcript
- Lightweight extraction: ~1K tokens per transcript
- Full extraction: ~2K tokens per transcript
- Synthesis: ~5K-10K tokens per biography

**Daily Processing Estimate**:
- 10 transcripts/day × detection = 5K tokens
- 2 full extractions/day = 4K tokens
- 1 synthesis/day = 7K tokens
- **Total: ~16K tokens/day**

---

## 10. Testing Strategy

### 10.1 Unit Tests

**Test Files**:
```
tests/
  test_biography_service.py
  test_biography_utils.py
  test_biography_integration.py
```

**Key Test Cases**:
```python
# biography_utils tests
def test_sanitize_biography_filename()
def test_parse_biography_file()
def test_format_chronological_entry()

# biography_service tests
def test_detect_biographical_content_person()
def test_detect_biographical_content_place()
def test_detect_biographical_content_object()
def test_detect_not_biographical()
def test_extract_full_biographical_content()
def test_extract_lightweight_biographical_content()
def test_create_biography_file()
def test_append_to_biography()
def test_synthesize_biography()

# integration tests
def test_full_biographical_pipeline()
def test_biography_accumulation_over_time()
def test_synthesis_regeneration()
```

### 10.2 Integration Testing

**Test Scenarios**:
1. **New Biography Creation**: Process transcript → detect → extract → create file
2. **Biography Update**: Process transcript → detect → append to existing
3. **Synthesis**: Multiple entries → synthesis → updated "Current Understanding"
4. **Edge Cases**: Empty transcripts, malformed files, missing prompts

### 10.3 Manual Testing

**Test Data**:
- Create sample transcripts with biographical content
- Test with real journal entries (with permission)
- Validate synthesis quality manually

**Validation Checklist**:
- [ ] Detection accuracy (catches biographical content)
- [ ] Category classification (person/place/object)
- [ ] Depth assessment (full vs lightweight)
- [ ] File creation with correct structure
- [ ] Chronological appending preserves history
- [ ] Synthesis quality and coherence
- [ ] Integration with existing pipeline

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] Create `biography_service.py` skeleton
- [ ] Create `biography_utils.py`
- [ ] Implement file management functions
- [ ] Create new prompts
- [ ] Add configuration variables
- [ ] Unit tests for utilities

### Phase 2: Detection & Extraction (Week 2)
- [ ] Implement `detect_biographical_content()`
- [ ] Implement `extract_biographical_content()`
- [ ] Test detection with sample data
- [ ] Test extraction with sample data
- [ ] Integration tests

### Phase 3: Pipeline Integration (Week 3)
- [ ] Integrate with main pipeline
- [ ] Test with journal entries
- [ ] Test with lifelogs
- [ ] Test with bee transcriptions
- [ ] End-to-end testing

### Phase 4: Synthesis (Week 4)
- [ ] Implement `synthesize_biography()`
- [ ] Implement `batch_synthesize_biographies()`
- [ ] Test synthesis quality
- [ ] Performance optimization
- [ ] Production deployment

---

**Status**: Design complete, ready for implementation
