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
import json
import logging

from daily_insights.utils.biography_utils import (
    sanitize_biography_filename,
    parse_biography_file,
    format_chronological_entry,
    mark_for_synthesis,
    needs_synthesis,
    remove_synthesis_marker
)

logger = logging.getLogger(__name__)


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
    try:
        # Combine detection prompt with raw transcript
        combined_input = f"{detection_prompt}\n\n=== TRANSCRIPT TO ANALYZE ===\n\n{raw_transcript}"

        # Send to LLM for detection
        logger.info(f"Detecting biographical content in {source_type} from {date}")
        response = llm_function(combined_input)

        # Parse JSON response
        # The LLM should return pure JSON, but we'll handle potential markdown wrapping
        response_text = response.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]  # Remove ```json
        if response_text.startswith("```"):
            response_text = response_text[3:]  # Remove ```
        if response_text.endswith("```"):
            response_text = response_text[:-3]  # Remove trailing ```

        response_text = response_text.strip()

        # Parse JSON
        detection_result = json.loads(response_text)

        # Check if biographical content was detected
        if not detection_result.get('is_biographical', False):
            logger.info(f"No biographical content detected: {detection_result.get('reasoning', 'No reason given')}")
            return None

        # Validate required fields
        required_fields = ['subject_name', 'category', 'depth']
        for field in required_fields:
            if field not in detection_result:
                logger.warning(f"Missing required field '{field}' in detection result")
                return None

        # Validate category
        valid_categories = ['person', 'place', 'object']
        if detection_result['category'] not in valid_categories:
            logger.warning(f"Invalid category: {detection_result['category']}")
            return None

        # Validate depth
        valid_depths = ['full', 'lightweight']
        if detection_result['depth'] not in valid_depths:
            logger.warning(f"Invalid depth: {detection_result['depth']}")
            return None

        # Return biographical content info with additional metadata
        result = {
            'subject_name': detection_result['subject_name'],
            'category': detection_result['category'],
            'depth': detection_result['depth'],
            'date': date,
            'source_type': source_type,
            'confidence': detection_result.get('confidence', 0.0),
            'reasoning': detection_result.get('reasoning', '')
        }

        logger.info(f"Biographical content detected: {result['subject_name']} "
                   f"({result['category']}, {result['depth']}) - "
                   f"confidence: {result['confidence']}")

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response from LLM: {e}")
        logger.debug(f"Raw response: {response[:500]}")
        return None
    except Exception as e:
        logger.error(f"Error detecting biographical content: {e}")
        return None


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
    try:
        # Combine extraction prompt with raw transcript
        combined_input = f"{prompt_text}\n\n=== RAW TRANSCRIPT ===\n\n{raw_transcript}"

        # Send to LLM for extraction
        logger.info(f"Extracting biographical content (depth: {depth.value})")
        extracted_content = llm_function(combined_input)

        # Return the extracted content (LLM will format according to prompt)
        logger.info(f"Successfully extracted biographical content ({len(extracted_content)} characters)")
        return extracted_content.strip()

    except Exception as e:
        logger.error(f"Error extracting biographical content: {e}")
        raise


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
    try:
        logger.info(f"Processing biographical extraction for {source_type} from {date}")

        # Step 1: Detect biographical content
        detection_result = detect_biographical_content(
            raw_transcript,
            source_type,
            date,
            detection_prompt,
            llm_function
        )

        # If no biographical content detected, return early
        if detection_result is None:
            logger.info(f"No biographical content detected in {source_type} from {date}")
            return

        # Step 2: Extract biographical content using appropriate prompt
        subject_name = detection_result['subject_name']
        category_str = detection_result['category']
        depth_str = detection_result['depth']

        logger.info(f"Extracting biographical content for '{subject_name}' "
                   f"({category_str}, {depth_str})")

        # Select appropriate extraction prompt based on depth
        if depth_str == 'full':
            extraction_prompt = full_prompt
            depth_enum = ContentDepth.FULL
        else:  # lightweight
            extraction_prompt = light_prompt
            depth_enum = ContentDepth.LIGHTWEIGHT

        # Extract the biographical content
        extracted_content = extract_biographical_content(
            raw_transcript,
            depth_enum,
            extraction_prompt,
            llm_function
        )

        # Step 3: Create or append to biography file
        category_enum = BiographyCategory(category_str)

        # Check if biography already exists
        if biography_exists(subject_name, category_enum, biographies_dir):
            # Append to existing biography
            logger.info(f"Appending to existing biography for '{subject_name}'")
            append_to_biography(
                subject_name,
                category_enum,
                extracted_content,
                date,
                source_type,
                biographies_dir
            )
        else:
            # Create new biography
            logger.info(f"Creating new biography for '{subject_name}'")
            create_biography_file(
                subject_name,
                category_enum,
                extracted_content,
                date,
                source_type,
                biographies_dir
            )

        logger.info(f"Successfully processed biographical content for '{subject_name}'")

    except Exception as e:
        logger.error(f"Error processing biographical extraction: {e}")
        raise


def process_biographies_from_journals() -> None:
    """
    Process biographical content from journal entries.

    This function scans journal entries and processes any biographical
    content found in them. It's designed to run after journal formatting.

    The function will:
    1. Find processed journal entries
    2. For each entry, extract raw transcript from original lifelog
    3. Run biographical detection and extraction
    4. Create or update biography files as needed
    """
    from daily_insights.config import (
        BIOGRAPHIES_DIR,
        BIOGRAPHY_DETECTION_PROMPT,
        BIOGRAPHY_PROMPT,
        BIOGRAPHY_LIGHT_PROMPT,
        JOURNAL_DIR
    )
    from daily_insights.api.llm_client import generate_summary
    from daily_insights.services.journal_service import extract_transcript

    try:
        logger.info("Starting biographical processing from journal entries...")

        # Load prompts
        if not BIOGRAPHY_DETECTION_PROMPT.exists():
            logger.warning(f"Detection prompt not found: {BIOGRAPHY_DETECTION_PROMPT}")
            return

        with open(BIOGRAPHY_DETECTION_PROMPT, 'r', encoding='utf-8') as f:
            detection_prompt = f.read()

        with open(BIOGRAPHY_PROMPT, 'r', encoding='utf-8') as f:
            full_prompt = f.read()

        with open(BIOGRAPHY_LIGHT_PROMPT, 'r', encoding='utf-8') as f:
            light_prompt = f.read()

        # Get list of journal entries
        from daily_insights.services.journal_service import find_all_journal_entries

        # Process ALL journal conversations (not just unprocessed)
        # Biographical processing is separate from journal formatting
        # We process all journals each run to catch any new biographical content
        journal_entries = find_all_journal_entries()

        if not journal_entries:
            logger.info("No journal entries found for biographical processing")
            return

        processed_count = 0
        biographical_count = 0

        for date_str, lifelog_path, conversation in journal_entries:
            try:
                # Extract raw transcript
                raw_transcript = extract_transcript(conversation)

                # Process for biographical content
                logger.info(f"Checking journal from {date_str} for biographical content")

                # Note: We pass None to check if biographical content exists
                # The actual processing happens inside process_biographical_extraction
                process_biographical_extraction(
                    raw_transcript,
                    "journal",
                    date_str,
                    BIOGRAPHIES_DIR,
                    detection_prompt,
                    full_prompt,
                    light_prompt,
                    generate_summary
                )

                processed_count += 1
                biographical_count += 1  # This will be updated in future to track actual detections

            except Exception as e:
                logger.error(f"Error processing biographical content for {date_str}: {e}")
                continue

        logger.info(f"Biographical processing complete: {processed_count} journals checked")

    except Exception as e:
        logger.error(f"Error in biographical processing from journals: {e}")
        raise


def process_biographies_from_lifelogs() -> None:
    """
    Process biographical content from lifelogs.

    This function scans lifelog files and processes any biographical
    content found in them. It processes all conversations in lifelogs
    that aren't journal or therapy sessions.
    """
    from daily_insights.config import (
        BIOGRAPHIES_DIR,
        BIOGRAPHY_DETECTION_PROMPT,
        BIOGRAPHY_PROMPT,
        BIOGRAPHY_LIGHT_PROMPT,
        LIFELOGS_DIR
    )
    from daily_insights.api.llm_client import generate_summary
    from daily_insights.models.conversation_parser import (
        parse_lifelog_dialogue,
        group_into_conversations,
        is_journal_session,
        is_therapy_session,
        is_doctor_visit,
        extract_transcript
    )
    from daily_insights.utils.date_utils import should_process_date
    from pathlib import Path
    import re

    try:
        logger.info("Starting biographical processing from lifelogs...")

        # Load prompts
        if not BIOGRAPHY_DETECTION_PROMPT.exists():
            logger.warning(f"Detection prompt not found: {BIOGRAPHY_DETECTION_PROMPT}")
            return

        with open(BIOGRAPHY_DETECTION_PROMPT, 'r', encoding='utf-8') as f:
            detection_prompt = f.read()

        with open(BIOGRAPHY_PROMPT, 'r', encoding='utf-8') as f:
            full_prompt = f.read()

        with open(BIOGRAPHY_LIGHT_PROMPT, 'r', encoding='utf-8') as f:
            light_prompt = f.read()

        # Get all lifelog files
        lifelog_files = sorted(Path(LIFELOGS_DIR).glob("*.md"))
        date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})\.md")

        processed_count = 0
        biographical_count = 0

        for lifelog_path in lifelog_files:
            match = date_pattern.match(lifelog_path.name)
            if not match:
                continue

            date_str = match.group(1)

            # Skip today's lifelogs (incomplete data)
            if not should_process_date(date_str):
                continue

            try:
                # Parse lifelog into conversations
                dialogues = parse_lifelog_dialogue(lifelog_path)
                if not dialogues:
                    continue

                conversations = group_into_conversations(dialogues)

                # Process each conversation (excluding journals, therapy, doctor visits)
                for conversation in conversations:
                    # Skip if it's a journal session, therapy session, or doctor visit
                    if (is_journal_session(conversation) or
                        is_therapy_session(conversation) or
                        is_doctor_visit(conversation)):
                        continue

                    # Extract raw transcript
                    raw_transcript = extract_transcript(conversation)

                    # Process for biographical content
                    logger.info(f"Checking lifelog conversation from {date_str} for biographical content")

                    process_biographical_extraction(
                        raw_transcript,
                        "lifelog",
                        date_str,
                        BIOGRAPHIES_DIR,
                        detection_prompt,
                        full_prompt,
                        light_prompt,
                        generate_summary
                    )

                    processed_count += 1

            except Exception as e:
                logger.error(f"Error processing biographical content for {date_str}: {e}")
                continue

        logger.info(f"Biographical processing complete: {processed_count} lifelog conversations checked")

    except Exception as e:
        logger.error(f"Error in biographical processing from lifelogs: {e}")
        raise


def process_biographies_from_bee() -> None:
    """
    Process biographical content from bee transcriptions.

    This function scans bee transcription files and processes any biographical
    content found in them.
    """
    from daily_insights.config import (
        BIOGRAPHIES_DIR,
        BIOGRAPHY_DETECTION_PROMPT,
        BIOGRAPHY_PROMPT,
        BIOGRAPHY_LIGHT_PROMPT,
        BEE_DIR
    )
    from daily_insights.api.llm_client import generate_summary
    from daily_insights.utils.date_utils import should_process_date
    from pathlib import Path
    import re

    try:
        logger.info("Starting biographical processing from bee transcriptions...")

        # Load prompts
        if not BIOGRAPHY_DETECTION_PROMPT.exists():
            logger.warning(f"Detection prompt not found: {BIOGRAPHY_DETECTION_PROMPT}")
            return

        with open(BIOGRAPHY_DETECTION_PROMPT, 'r', encoding='utf-8') as f:
            detection_prompt = f.read()

        with open(BIOGRAPHY_PROMPT, 'r', encoding='utf-8') as f:
            full_prompt = f.read()

        with open(BIOGRAPHY_LIGHT_PROMPT, 'r', encoding='utf-8') as f:
            light_prompt = f.read()

        # Get all bee transcription files
        bee_files = sorted(Path(BEE_DIR).glob("*_bee.md"))
        date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})_bee\.md")

        processed_count = 0

        for bee_path in bee_files:
            match = date_pattern.match(bee_path.name)
            if not match:
                continue

            date_str = match.group(1)

            # Skip today's bee files (incomplete data)
            if not should_process_date(date_str):
                continue

            try:
                # Read raw transcript from bee file
                with open(bee_path, 'r', encoding='utf-8') as f:
                    raw_transcript = f.read()

                # Process for biographical content
                logger.info(f"Checking bee transcription from {date_str} for biographical content")

                process_biographical_extraction(
                    raw_transcript,
                    "bee",
                    date_str,
                    BIOGRAPHIES_DIR,
                    detection_prompt,
                    full_prompt,
                    light_prompt,
                    generate_summary
                )

                processed_count += 1

            except Exception as e:
                logger.error(f"Error processing biographical content for {date_str}: {e}")
                continue

        logger.info(f"Biographical processing complete: {processed_count} bee transcriptions checked")

    except Exception as e:
        logger.error(f"Error in biographical processing from bee transcriptions: {e}")
        raise


def process_biographies_from_therapy() -> None:
    """
    Process biographical content from therapy sessions.

    This function scans therapy session files and processes any biographical
    content found in them. It uses the already-detected therapy sessions
    from the therapy service.
    """
    from daily_insights.config import (
        BIOGRAPHIES_DIR,
        BIOGRAPHY_DETECTION_PROMPT,
        BIOGRAPHY_PROMPT,
        BIOGRAPHY_LIGHT_PROMPT,
        LIFELOGS_DIR
    )
    from daily_insights.api.llm_client import generate_summary
    from daily_insights.services.therapy_service import detect_therapy_sessions_mvp
    from daily_insights.models.conversation_parser import extract_transcript
    from daily_insights.utils.date_utils import should_process_date
    from pathlib import Path
    import re

    try:
        logger.info("Starting biographical processing from therapy sessions...")

        # Load prompts
        if not BIOGRAPHY_DETECTION_PROMPT.exists():
            logger.warning(f"Detection prompt not found: {BIOGRAPHY_DETECTION_PROMPT}")
            return

        with open(BIOGRAPHY_DETECTION_PROMPT, 'r', encoding='utf-8') as f:
            detection_prompt = f.read()

        with open(BIOGRAPHY_PROMPT, 'r', encoding='utf-8') as f:
            full_prompt = f.read()

        with open(BIOGRAPHY_LIGHT_PROMPT, 'r', encoding='utf-8') as f:
            light_prompt = f.read()

        # Get all lifelog files to detect therapy sessions
        lifelog_files = sorted(Path(LIFELOGS_DIR).glob("*.md"))
        date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})\.md")

        processed_count = 0

        for lifelog_path in lifelog_files:
            match = date_pattern.match(lifelog_path.name)
            if not match:
                continue

            date_str = match.group(1)

            # Skip today's lifelogs (incomplete data)
            if not should_process_date(date_str):
                continue

            try:
                # Detect therapy sessions in this lifelog
                therapy_sessions = detect_therapy_sessions_mvp(lifelog_path)

                for session in therapy_sessions:
                    # Extract raw transcript from therapy conversation
                    raw_transcript = extract_transcript(session["conversation"])

                    # Process for biographical content
                    logger.info(f"Checking therapy session from {date_str} for biographical content")

                    process_biographical_extraction(
                        raw_transcript,
                        "therapy",
                        date_str,
                        BIOGRAPHIES_DIR,
                        detection_prompt,
                        full_prompt,
                        light_prompt,
                        generate_summary
                    )

                    processed_count += 1

            except Exception as e:
                logger.error(f"Error processing biographical content for therapy on {date_str}: {e}")
                continue

        logger.info(f"Biographical processing complete: {processed_count} therapy sessions checked")

    except Exception as e:
        logger.error(f"Error in biographical processing from therapy sessions: {e}")
        raise


def process_biographies_from_doctors() -> None:
    """
    Process biographical content from doctor visits.

    This function scans doctor visit files and processes any biographical
    content found in them. It uses the already-detected doctor visits
    from the doctor visit service.
    """
    from daily_insights.config import (
        BIOGRAPHIES_DIR,
        BIOGRAPHY_DETECTION_PROMPT,
        BIOGRAPHY_PROMPT,
        BIOGRAPHY_LIGHT_PROMPT,
        LIFELOGS_DIR
    )
    from daily_insights.api.llm_client import generate_summary
    from daily_insights.services.doctor_visit_service import detect_doctor_visits_mvp
    from daily_insights.models.conversation_parser import extract_transcript
    from daily_insights.utils.date_utils import should_process_date
    from pathlib import Path
    import re

    try:
        logger.info("Starting biographical processing from doctor visits...")

        # Load prompts
        if not BIOGRAPHY_DETECTION_PROMPT.exists():
            logger.warning(f"Detection prompt not found: {BIOGRAPHY_DETECTION_PROMPT}")
            return

        with open(BIOGRAPHY_DETECTION_PROMPT, 'r', encoding='utf-8') as f:
            detection_prompt = f.read()

        with open(BIOGRAPHY_PROMPT, 'r', encoding='utf-8') as f:
            full_prompt = f.read()

        with open(BIOGRAPHY_LIGHT_PROMPT, 'r', encoding='utf-8') as f:
            light_prompt = f.read()

        # Get all lifelog files to detect doctor visits
        lifelog_files = sorted(Path(LIFELOGS_DIR).glob("*.md"))
        date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})\.md")

        processed_count = 0

        for lifelog_path in lifelog_files:
            match = date_pattern.match(lifelog_path.name)
            if not match:
                continue

            date_str = match.group(1)

            # Skip today's lifelogs (incomplete data)
            if not should_process_date(date_str):
                continue

            try:
                # Detect doctor visits in this lifelog
                doctor_visits = detect_doctor_visits_mvp(lifelog_path)

                for visit in doctor_visits:
                    # Extract raw transcript from doctor visit conversation
                    raw_transcript = extract_transcript(visit["conversation"])

                    # Process for biographical content
                    logger.info(f"Checking doctor visit from {date_str} for biographical content")

                    process_biographical_extraction(
                        raw_transcript,
                        "doctor",
                        date_str,
                        BIOGRAPHIES_DIR,
                        detection_prompt,
                        full_prompt,
                        light_prompt,
                        generate_summary
                    )

                    processed_count += 1

            except Exception as e:
                logger.error(f"Error processing biographical content for doctor visit on {date_str}: {e}")
                continue

        logger.info(f"Biographical processing complete: {processed_count} doctor visits checked")

    except Exception as e:
        logger.error(f"Error in biographical processing from doctor visits: {e}")
        raise
