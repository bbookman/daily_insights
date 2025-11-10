"""Service for processing journal entries from lifelogs into formatted documents."""

import os
import re
import asyncio
from pathlib import Path
from typing import Set, List, Dict
from datetime import datetime

from daily_insights.config import JOURNAL_DIR, LIFELOGS_DIR
from daily_insights.config import PROJECT_ROOT
from daily_insights.api.llm_client import generate_summary, generate_summary_async
from daily_insights.utils.file_utils import read_file_async, write_file_async
from daily_insights.utils.date_utils import should_process_date
from daily_insights.models.conversation_parser import (
    parse_lifelog_dialogue,
    group_into_conversations,
    is_journal_session,
    extract_transcript
)


# ============================================================================
# Constants
# ============================================================================

JOURNAL_PROMPT_FILE = PROJECT_ROOT / 'prompts' / 'journal.txt'


# ============================================================================
# Synchronous Service Functions
# ============================================================================

def get_existing_journal_dates() -> Set[str]:
    """
    Get set of dates that already have journal entries in /journal.

    Returns
    -------
    Set[str]
        Set of date strings in YYYY-MM-DD format for existing journal files

    Example
    -------
    >>> dates = get_existing_journal_dates()
    >>> '2025-06-27' in dates
    True
    """
    print("Scanning for existing journal entries...")
    dates = set()
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})_journal\.md")

    for file_path in Path(JOURNAL_DIR).glob("*_journal.md"):
        match = date_pattern.match(file_path.name)
        if match:
            dates.add(match.group(1))

    print(f"Found {len(dates)} existing journal entries.")
    return dates


def find_all_journal_entries() -> List[tuple]:
    """
    Find ALL journal entries in lifelogs (including already processed ones).

    Scans lifelog files for journal sessions (single-speaker conversations
    with journal indicators) and returns all found entries.

    Returns
    -------
    List[tuple]
        List of (date_str, lifelog_path, conversation) tuples for all journal entries

    Example
    -------
    >>> entries = find_all_journal_entries()
    >>> len(entries)
    45
    """
    print("\nScanning lifelogs for all journal entries...")

    all_entries = []
    skipped_today = 0
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})\.md")

    for lifelog_path in sorted(Path(LIFELOGS_DIR).glob("*.md")):
        match = date_pattern.match(lifelog_path.name)
        if not match:
            continue

        date_str = match.group(1)

        # Skip today's lifelogs (incomplete data)
        if not should_process_date(date_str):
            skipped_today += 1
            continue

        # Parse lifelog and find journal sessions
        try:
            dialogues = parse_lifelog_dialogue(lifelog_path)
            if not dialogues:
                continue

            conversations = group_into_conversations(dialogues)

            # Find journal sessions (single-speaker, monologue-style)
            for conversation in conversations:
                if is_journal_session(conversation):
                    all_entries.append((date_str, lifelog_path, conversation))
                    print(f"Found journal session in {lifelog_path.name}")
                    break  # Only take first journal session per day

        except Exception as e:
            print(f"Warning: Error parsing {lifelog_path.name}: {e}")
            continue

    if skipped_today > 0:
        print(f"Skipped {skipped_today} lifelog(s) from today (incomplete data)")

    print(f"Found {len(all_entries)} journal entries total.")
    return all_entries


def find_unprocessed_journal_entries() -> List[tuple]:
    """
    Find journal entries in lifelogs that haven't been processed yet.

    Scans lifelog files for journal sessions (single-speaker conversations
    with journal indicators) and returns those not yet processed.

    Returns
    -------
    List[tuple]
        List of (date_str, lifelog_path, conversation) tuples for unprocessed entries

    Example
    -------
    >>> entries = find_unprocessed_journal_entries()
    >>> len(entries)
    3
    """
    print("\nScanning lifelogs for journal entries...")

    existing_dates = get_existing_journal_dates()
    unprocessed_entries = []
    skipped_today = 0
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})\.md")

    for lifelog_path in sorted(Path(LIFELOGS_DIR).glob("*.md")):
        match = date_pattern.match(lifelog_path.name)
        if not match:
            continue

        date_str = match.group(1)

        # Skip today's lifelogs (incomplete data)
        if not should_process_date(date_str):
            skipped_today += 1
            continue

        # Skip if already processed
        if date_str in existing_dates:
            print(f"Skipping {lifelog_path.name} - journal already exists")
            continue

        # Parse lifelog and find journal sessions
        try:
            dialogues = parse_lifelog_dialogue(lifelog_path)
            if not dialogues:
                continue

            conversations = group_into_conversations(dialogues)

            # Find journal sessions (single-speaker, monologue-style)
            for conversation in conversations:
                if is_journal_session(conversation):
                    unprocessed_entries.append((date_str, lifelog_path, conversation))
                    print(f"Found journal session in {lifelog_path.name}")
                    break  # Only take first journal session per day

        except Exception as e:
            print(f"Warning: Error parsing {lifelog_path.name}: {e}")
            continue

    if skipped_today > 0:
        print(f"Skipped {skipped_today} lifelog(s) from today (incomplete data)")

    print(f"Found {len(unprocessed_entries)} unprocessed journal entries.")
    return unprocessed_entries


def process_journal_entry(conversation: List[Dict], prompt_text: str, date_str: str) -> str:
    """
    Process a journal conversation through LLM for formatting.

    Combines the prompt template with the journal transcript
    and sends to the configured LLM for formatting.

    Parameters
    ----------
    conversation : List[Dict]
        Parsed conversation data (list of dialogue dicts)
    prompt_text : str
        The prompt template text from journal.txt
    date_str : str
        Date of the journal entry (YYYY-MM-DD format)

    Returns
    -------
    str
        Formatted journal entry content from LLM

    Raises
    ------
    Exception
        If LLM generation fails

    Example
    -------
    >>> content = process_journal_entry(conversation, prompt, "2025-06-27")
    >>> len(content) > 0
    True
    """
    print(f"Processing journal entry for {date_str}...")

    # Extract transcript from conversation
    transcript = extract_transcript(conversation)

    # Combine prompt with transcript
    full_prompt = f"""{prompt_text}

# RAW JOURNAL TRANSCRIPT - {date_str}

{transcript}
"""

    # Generate formatted entry using LLM
    print(f"Sending journal entry for {date_str} to LLM for formatting...")
    result = generate_summary(full_prompt)

    return result


def save_journal_entry(date_str: str, content: str) -> Path:
    """
    Save formatted journal entry to /journal directory.

    Parameters
    ----------
    date_str : str
        Date string in YYYY-MM-DD format
    content : str
        Formatted journal entry content to save

    Returns
    -------
    Path
        Path to the saved file

    Example
    -------
    >>> path = save_journal_entry("2025-06-27", "# Journal Entry...")
    >>> path.exists()
    True
    """
    filename = f"{date_str}_journal.md"
    filepath = Path(JOURNAL_DIR) / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Saved journal entry: {filepath}")
    return filepath


def process_journal_entries() -> None:
    """
    Main function to process all unprocessed journal entries.

    Workflow:
    1. Check for prompt file existence
    2. Find unprocessed journal entries in lifelogs
    3. Process each entry through LLM for formatting
    4. Save formatted entries to /journal directory
    5. Report processing statistics

    Returns
    -------
    None

    Example
    -------
    >>> process_journal_entries()
    # Processing journal entries...
    # Found 2 unprocessed entries
    # Processed 2 entries successfully
    """
    print("\nStarting journal entry processing...")

    # Check if prompt file exists
    if not os.path.exists(JOURNAL_PROMPT_FILE):
        print(f"ERROR: Journal prompt file missing: {JOURNAL_PROMPT_FILE}")
        print("Please create the prompt file before processing journal entries.")
        return

    # Read prompt template
    with open(JOURNAL_PROMPT_FILE, "r", encoding="utf-8") as f:
        prompt_text = f.read()

    # Find unprocessed entries
    unprocessed_entries = find_unprocessed_journal_entries()

    if not unprocessed_entries:
        print("No new journal entries to process.")
        return

    # Process each entry
    entries_processed = 0
    entries_failed = 0

    for date_str, lifelog_path, conversation in unprocessed_entries:
        try:
            # Process through LLM
            formatted_content = process_journal_entry(conversation, prompt_text, date_str)

            # Save result
            save_journal_entry(date_str, formatted_content)

            entries_processed += 1

        except Exception as e:
            print(f"ERROR processing journal entry for {date_str}: {e}")
            entries_failed += 1
            continue

    # Report statistics
    print(f"\nJournal entry processing complete:")
    print(f"  Entries processed: {entries_processed}")
    print(f"  Entries failed: {entries_failed}")
    print(f"  Total entries checked: {len(unprocessed_entries)}")


# ============================================================================
# Async Service Functions
# ============================================================================

async def get_existing_journal_dates_async() -> Set[str]:
    """
    Async version: Get set of dates that already have journal entries.

    Returns
    -------
    Set[str]
        Set of date strings in YYYY-MM-DD format for existing journal files

    Example
    -------
    >>> dates = await get_existing_journal_dates_async()
    >>> '2025-06-27' in dates
    True
    """
    print("Scanning for existing journal entries...")
    dates = set()
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})_journal\.md")

    for file_path in Path(JOURNAL_DIR).glob("*_journal.md"):
        match = date_pattern.match(file_path.name)
        if match:
            dates.add(match.group(1))

    print(f"Found {len(dates)} existing journal entries.")
    return dates


async def find_unprocessed_journal_entries_async() -> List[tuple]:
    """
    Async version: Find journal entries in lifelogs that haven't been processed.

    Returns
    -------
    List[tuple]
        List of (date_str, lifelog_path, conversation) tuples for unprocessed entries

    Example
    -------
    >>> entries = await find_unprocessed_journal_entries_async()
    >>> len(entries)
    3
    """
    print("\nScanning lifelogs for journal entries...")

    existing_dates = await get_existing_journal_dates_async()
    unprocessed_entries = []
    skipped_today = 0
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})\.md")

    for lifelog_path in sorted(Path(LIFELOGS_DIR).glob("*.md")):
        match = date_pattern.match(lifelog_path.name)
        if not match:
            continue

        date_str = match.group(1)

        # Skip today's lifelogs (incomplete data)
        if not should_process_date(date_str):
            skipped_today += 1
            continue

        # Skip if already processed
        if date_str in existing_dates:
            print(f"Skipping {lifelog_path.name} - journal already exists")
            continue

        # Parse lifelog and find journal sessions
        try:
            dialogues = parse_lifelog_dialogue(lifelog_path)
            if not dialogues:
                continue

            conversations = group_into_conversations(dialogues)

            # Find journal sessions (single-speaker, monologue-style)
            for conversation in conversations:
                if is_journal_session(conversation):
                    unprocessed_entries.append((date_str, lifelog_path, conversation))
                    print(f"Found journal session in {lifelog_path.name}")
                    break  # Only take first journal session per day

        except Exception as e:
            print(f"Warning: Error parsing {lifelog_path.name}: {e}")
            continue

    if skipped_today > 0:
        print(f"Skipped {skipped_today} lifelog(s) from today (incomplete data)")

    print(f"Found {len(unprocessed_entries)} unprocessed journal entries.")
    return unprocessed_entries


async def process_journal_entry_async(conversation: List[Dict], prompt_text: str, date_str: str) -> str:
    """
    Async version: Process a journal conversation through LLM for formatting.

    Parameters
    ----------
    conversation : List[Dict]
        Parsed conversation data (list of dialogue dicts)
    prompt_text : str
        The prompt template text from journal.txt
    date_str : str
        Date of the journal entry (YYYY-MM-DD format)

    Returns
    -------
    str
        Formatted journal entry content from LLM

    Example
    -------
    >>> content = await process_journal_entry_async(conversation, prompt, "2025-06-27")
    >>> len(content) > 0
    True
    """
    print(f"Processing journal entry for {date_str}...")

    # Extract transcript from conversation
    transcript = extract_transcript(conversation)

    # Combine prompt with transcript
    full_prompt = f"""{prompt_text}

# RAW JOURNAL TRANSCRIPT - {date_str}

{transcript}
"""

    # Generate formatted entry using LLM
    print(f"Sending journal entry for {date_str} to LLM for formatting...")
    result = await generate_summary_async(full_prompt)

    return result


async def save_journal_entry_async(date_str: str, content: str) -> Path:
    """
    Async version: Save formatted journal entry to /journal directory.

    Parameters
    ----------
    date_str : str
        Date string in YYYY-MM-DD format
    content : str
        Formatted journal entry content to save

    Returns
    -------
    Path
        Path to the saved file

    Example
    -------
    >>> path = await save_journal_entry_async("2025-06-27", "# Journal Entry...")
    >>> path.exists()
    True
    """
    filename = f"{date_str}_journal.md"
    filepath = Path(JOURNAL_DIR) / filename

    await write_file_async(str(filepath), content)

    print(f"Saved journal entry: {filepath}")
    return filepath


async def process_journal_entries_async() -> None:
    """
    Async version: Main function to process all unprocessed journal entries.

    Workflow:
    1. Check for prompt file existence
    2. Find unprocessed journal entries in lifelogs
    3. Process entries through LLM (in parallel with semaphore)
    4. Save formatted entries to /journal directory
    5. Report processing statistics

    Returns
    -------
    None

    Example
    -------
    >>> await process_journal_entries_async()
    # Processing journal entries...
    # Found 2 unprocessed entries
    # Processed 2 entries successfully
    """
    print("\nStarting journal entry processing (async)...")

    # Check if prompt file exists
    if not os.path.exists(JOURNAL_PROMPT_FILE):
        print(f"ERROR: Journal prompt file missing: {JOURNAL_PROMPT_FILE}")
        print("Please create the prompt file before processing journal entries.")
        return

    # Read prompt template
    prompt_text = await read_file_async(str(JOURNAL_PROMPT_FILE))

    # Find unprocessed entries
    unprocessed_entries = await find_unprocessed_journal_entries_async()

    if not unprocessed_entries:
        print("No new journal entries to process.")
        return

    # Process entries concurrently with semaphore to limit parallel LLM calls
    semaphore = asyncio.Semaphore(3)  # Max 3 concurrent LLM calls
    entries_processed = 0
    entries_failed = 0

    async def process_single_entry(date_str: str, lifelog_path: Path, conversation: List[Dict]) -> None:
        nonlocal entries_processed, entries_failed

        async with semaphore:
            try:
                # Process through LLM
                formatted_content = await process_journal_entry_async(conversation, prompt_text, date_str)

                # Save result
                await save_journal_entry_async(date_str, formatted_content)

                entries_processed += 1

            except Exception as e:
                print(f"ERROR processing journal entry for {date_str}: {e}")
                entries_failed += 1

    # Process all entries concurrently (with semaphore limiting)
    await asyncio.gather(*[
        process_single_entry(date_str, lifelog_path, conversation)
        for date_str, lifelog_path, conversation in unprocessed_entries
    ])

    # Report statistics
    print(f"\nJournal entry processing complete:")
    print(f"  Entries processed: {entries_processed}")
    print(f"  Entries failed: {entries_failed}")
    print(f"  Total entries checked: {len(unprocessed_entries)}")
