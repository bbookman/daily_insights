"""
Service for managing biographical documentation system.

Provides functionality for:
- Detecting biographical content in transcripts
- Extracting biographical information
- Managing biography master files
- Synthesizing accumulated knowledge
"""

from pathlib import Path
from typing import Optional, Dict, List
from enum import Enum
from datetime import datetime

from daily_insights.utils.biography_utils import (
    sanitize_biography_filename,
    parse_biography_file,
    format_chronological_entry,
    mark_for_synthesis,
    needs_synthesis,
    remove_synthesis_marker
)


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


# Note: These imports will be added when config is updated
# from daily_insights.config import (
#     BIOGRAPHIES_DIR,
#     BIOGRAPHY_PROMPT,
#     BIOGRAPHY_LIGHT_PROMPT,
#     BIOGRAPHY_SYNTHESIS_PROMPT,
#     BIOGRAPHY_DETECTION_PROMPT,
#     PROCESS_BIOGRAPHIES
# )
# from daily_insights.api.llm_client import generate_summary, generate_summary_async


# ============================================================================
# File Management Functions
# ============================================================================

def get_biography_filepath(
    subject_name: str,
    category: BiographyCategory,
    biographies_dir: Path
) -> Path:
    """
    Get filepath for biography.

    Parameters
    ----------
    subject_name : str
        Name of person/place/object
    category : BiographyCategory
        Subject category
    biographies_dir : Path
        Base biographies directory

    Returns
    -------
    Path
        Full path to biography file
    """
    sanitized_name = sanitize_biography_filename(subject_name)
    filename = f"{sanitized_name}.md"
    return biographies_dir / category.value / filename


def biography_exists(
    subject_name: str,
    category: BiographyCategory,
    biographies_dir: Path
) -> bool:
    """
    Check if biography file exists.

    Parameters
    ----------
    subject_name : str
        Name of subject
    category : BiographyCategory
        Subject category
    biographies_dir : Path
        Base biographies directory

    Returns
    -------
    bool
        True if biography file exists
    """
    filepath = get_biography_filepath(subject_name, category, biographies_dir)
    return filepath.exists()


def create_biography_file(
    subject_name: str,
    category: BiographyCategory,
    initial_content: str,
    date: str,
    source_type: str,
    biographies_dir: Path
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
        Date of entry (YYYY-MM-DD)
    source_type : str
        Source type (journal, lifelog, bee)
    biographies_dir : Path
        Base biographies directory

    Returns
    -------
    Path
        Path to created file
    """
    filepath = get_biography_filepath(subject_name, category, biographies_dir)

    # Ensure directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Format chronological entry
    chrono_entry = format_chronological_entry(date, source_type, initial_content)

    # Create file content
    content = f"""# {subject_name} - Biographical Profile

**Last Updated**: {date}

---

## Current Understanding (Auto-synthesized)

*Synthesis will be generated during next batch processing.*

---

## Chronological Insights
{chrono_entry}
"""

    # Write file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # Mark for synthesis
    mark_for_synthesis(filepath)

    print(f"Created new biography: {filepath}")
    return filepath


def append_to_biography(
    subject_name: str,
    category: BiographyCategory,
    new_content: str,
    date: str,
    source_type: str,
    biographies_dir: Path
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
        Date of entry (YYYY-MM-DD)
    source_type : str
        Source type (journal, lifelog, bee)
    biographies_dir : Path
        Base biographies directory

    Returns
    -------
    Path
        Path to updated file
    """
    filepath = get_biography_filepath(subject_name, category, biographies_dir)

    if not filepath.exists():
        raise FileNotFoundError(f"Biography file not found: {filepath}")

    # Read existing content
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update last updated date
    content = content.replace(
        f'**Last Updated**: ',
        f'**Last Updated**: {date}\n\n<!-- Previous update: ',
        1
    ).replace('\n\n---', ' -->\n\n---', 1)

    # Format new chronological entry
    new_entry = format_chronological_entry(date, source_type, new_content)

    # Append to end of file
    updated_content = content + new_entry

    # Write updated file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    # Mark for synthesis
    mark_for_synthesis(filepath)

    print(f"Appended to biography: {filepath}")
    return filepath


# ============================================================================
# Detection & Extraction Functions (Stubs for Phase 2)
# ============================================================================

def detect_biographical_content(
    raw_transcript: str,
    source_type: str,
    date: str,
    detection_prompt: str,
    llm_function
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
    detection_prompt : str
        Detection prompt text
    llm_function : callable
        LLM function to use (generate_summary or generate_summary_async)

    Returns
    -------
    Optional[Dict]
        Biographical content info or None if not biographical
        {
            'subject_name': str,
            'category': str,  # 'person', 'place', 'object'
            'depth': str,     # 'full', 'lightweight'
            'date': str,
            'source_type': str
        }
    """
    # TODO: Implement in Phase 2
    # This will:
    # 1. Combine detection prompt + raw transcript
    # 2. Send to LLM
    # 3. Parse JSON response
    # 4. Return detection result or None
    pass


def extract_biographical_content(
    raw_transcript: str,
    depth: ContentDepth,
    prompt_text: str,
    llm_function
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
    llm_function : callable
        LLM function to use

    Returns
    -------
    str
        Extracted biographical content
    """
    # TODO: Implement in Phase 2
    # This will:
    # 1. Combine prompt + raw transcript
    # 2. Send to LLM
    # 3. Return extracted content
    pass


# ============================================================================
# Synthesis Functions (Stubs for Phase 4)
# ============================================================================

def synthesize_biography(
    subject_name: str,
    category: BiographyCategory,
    biographies_dir: Path,
    synthesis_prompt: str,
    llm_function
) -> None:
    """
    Regenerate "Current Understanding" synthesis section.

    Parameters
    ----------
    subject_name : str
        Name of subject
    category : BiographyCategory
        Subject category
    biographies_dir : Path
        Base biographies directory
    synthesis_prompt : str
        Synthesis prompt text
    llm_function : callable
        LLM function to use
    """
    # TODO: Implement in Phase 4
    # This will:
    # 1. Load biography file
    # 2. Extract all chronological entries
    # 3. Combine synthesis prompt + all entries
    # 4. Send to LLM
    # 5. Parse synthesis result
    # 6. Update "Current Understanding" section
    # 7. Remove synthesis marker
    pass


def batch_synthesize_biographies(biographies_dir: Path, synthesis_prompt: str, llm_function) -> None:
    """
    Synthesize all biographies marked for update.

    Parameters
    ----------
    biographies_dir : Path
        Base biographies directory
    synthesis_prompt : str
        Synthesis prompt text
    llm_function : callable
        LLM function to use
    """
    # TODO: Implement in Phase 4
    # This will:
    # 1. Scan all biography files
    # 2. Find files marked for synthesis
    # 3. Call synthesize_biography() for each
    # 4. Report statistics
    pass


# ============================================================================
# Main Processing Functions (Stubs for Phase 3)
# ============================================================================

def process_biographical_extraction(
    raw_transcript: str,
    source_type: str,
    date: str,
    biographies_dir: Path,
    detection_prompt: str,
    full_prompt: str,
    light_prompt: str,
    llm_function
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
        Date of transcript (YYYY-MM-DD)
    biographies_dir : Path
        Base biographies directory
    detection_prompt : str
        Detection prompt text
    full_prompt : str
        Full extraction prompt text
    light_prompt : str
        Lightweight extraction prompt text
    llm_function : callable
        LLM function to use
    """
    # TODO: Implement in Phase 3
    # This will:
    # 1. Detect biographical content
    # 2. If detected, extract content
    # 3. Create or append to biography file
    pass


def process_all_biographies(
    biographies_dir: Path,
    detection_prompt: str,
    full_prompt: str,
    light_prompt: str,
    synthesis_prompt: str,
    llm_function
) -> None:
    """
    Main biographical processing pipeline.

    Workflow:
    1. Scan for unprocessed transcripts
    2. Extract biographical content
    3. Update biography files
    4. Batch synthesize updates
    """
    # TODO: Implement in Phase 3
    # This is the main entry point that will be called from pipeline
    pass
