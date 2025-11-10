"""Service for processing bee transcription files into daily insights."""

import os
from pathlib import Path
from typing import Set, List
import re
import asyncio

from daily_insights.config import BEE_DIR, BEE_PROMPT_FILE, INSIGHTS_DIR
from daily_insights.api.llm_client import generate_summary, generate_summary_async
from daily_insights.utils.file_utils import read_file_async, write_file_async
from daily_insights.utils.date_utils import should_process_date


def get_existing_bee_insight_dates() -> Set[str]:
    """
    Get set of dates that already have bee insights in /daily.

    Checks daily insight files for the presence of bee content section.
    A file contains bee insights if it has the "🐝 Bee Transcription Insights" marker.

    Returns
    -------
    Set[str]
        Set of date strings in YYYY-MM-DD format for files with bee content

    Example
    -------
    >>> dates = get_existing_bee_insight_dates()
    >>> '2025-06-27' in dates
    True
    """
    print("Scanning for files with existing bee insights...")
    dates = set()
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})\.md")
    bee_marker = "🐝 Bee Transcription Insights"

    for file_path in Path(INSIGHTS_DIR).glob("*.md"):
        # Skip weekly/monthly summary files
        if "-weekly" in file_path.name or file_path.name.startswith("20") and len(file_path.stem) == 7:
            continue

        # Extract date from filename
        match = date_pattern.match(file_path.name)
        if match:
            date_str = match.group(1)

            # Check if file contains bee insights marker
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if bee_marker in content:
                        dates.add(date_str)
            except Exception as e:
                print(f"Warning: Could not read {file_path.name}: {e}")
                continue

    print(f"Found {len(dates)} files with existing bee insights.")
    return dates


def find_unprocessed_bee_files() -> List[Path]:
    """
    Find bee transcription files that haven't been processed yet.

    Looks for files matching pattern YYYY-MM-DD_bee.md in /bee directory
    and filters out those that already have corresponding insight files.
    Only includes files dated yesterday or earlier (skips today's incomplete data).

    Returns
    -------
    List[Path]
        List of Path objects for unprocessed bee files, sorted by date

    Example
    -------
    >>> files = find_unprocessed_bee_files()
    >>> len(files)
    5
    """
    print("\nScanning for unprocessed bee transcription files...")

    existing_dates = get_existing_bee_insight_dates()
    unprocessed_files = []
    skipped_today = 0
    pattern = re.compile(r"(\d{4}-\d{2}-\d{2})_bee\.md")

    for file_path in Path(BEE_DIR).glob("*_bee.md"):
        match = pattern.match(file_path.name)
        if match:
            date_str = match.group(1)

            # Skip today's bee files (incomplete data)
            if not should_process_date(date_str):
                skipped_today += 1
                continue

            if date_str not in existing_dates:
                unprocessed_files.append(file_path)
            else:
                print(f"Skipping {file_path.name} - insight already exists")

    # Sort by date (filename naturally sorts correctly)
    unprocessed_files.sort()

    if skipped_today > 0:
        print(f"Skipped {skipped_today} bee file(s) from today (incomplete data)")

    print(f"Found {len(unprocessed_files)} unprocessed bee transcription files.")
    return unprocessed_files


def process_bee_file(bee_file: Path, prompt_text: str) -> str:
    """
    Process a single bee transcription file through LLM.

    Combines the prompt template with the bee transcript content
    and sends to the configured LLM for processing.

    Parameters
    ----------
    bee_file : Path
        Path to the bee transcription markdown file
    prompt_text : str
        The prompt template text from bee_daily.txt

    Returns
    -------
    str
        Generated insight content from LLM

    Raises
    ------
    Exception
        If LLM generation fails

    Example
    -------
    >>> content = process_bee_file(Path("bee/2025-06-27_bee.md"), prompt)
    >>> len(content) > 0
    True
    """
    print(f"Processing {bee_file.name}...")

    # Read bee transcript
    with open(bee_file, "r", encoding="utf-8") as f:
        transcript_content = f.read()

    # Combine prompt with transcript
    full_prompt = f"{prompt_text}\n\n# BEE TRANSCRIPT\n\n{transcript_content}"

    # Generate insight using LLM
    print(f"Sending {bee_file.name} to LLM for analysis...")
    result = generate_summary(full_prompt)

    return result


def save_bee_insight(date: str, content: str) -> Path:
    """
    Save generated bee insight to /daily directory.

    If a daily insight file already exists for this date, the bee content
    will be appended with a clear section divider. If no file exists,
    a new file will be created with the bee content.

    Parameters
    ----------
    date : str
        Date string in YYYY-MM-DD format
    content : str
        Generated insight content to save

    Returns
    -------
    Path
        Path to the saved file

    Example
    -------
    >>> path = save_bee_insight("2025-06-27", "# Daily Summary...")
    >>> path.exists()
    True
    """
    # Use standard daily filename (not -bee suffix)
    filename = f"{date}.md"
    filepath = Path(INSIGHTS_DIR) / filename

    # Check if regular daily insight already exists
    if filepath.exists():
        # MERGE: Read existing content and append bee insights
        with open(filepath, "r", encoding="utf-8") as f:
            existing_content = f.read()

        # Create merged content with clear section divider
        merged_content = f"""{existing_content}

---

## 🐝 Bee Transcription Insights

{content}
"""
        # Write merged content
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(merged_content)

        print(f"Merged bee insights into existing daily file: {filepath}")
    else:
        # No existing daily insight - create new file with bee content
        header_content = f"""# Daily Insights - {date}

## 🐝 Bee Transcription Insights

{content}
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(header_content)

        print(f"Created new daily insight file with bee content: {filepath}")

    return filepath


def process_bee_transcriptions() -> None:
    """
    Main function to process all unprocessed bee transcription files.

    Workflow:
    1. Check for prompt file existence
    2. Find unprocessed bee files
    3. Process each file through LLM
    4. Save generated insights to /daily directory
    5. Report processing statistics

    Returns
    -------
    None

    Example
    -------
    >>> process_bee_transcriptions()
    # Processing bee transcriptions...
    # Found 3 unprocessed files
    # Processed 3 files successfully
    """
    print("\nStarting bee transcription processing...")

    # Check if prompt file exists
    if not os.path.exists(BEE_PROMPT_FILE):
        print(f"ERROR: Bee prompt file missing: {BEE_PROMPT_FILE}")
        print("Please create the prompt file before processing bee transcriptions.")
        return

    # Read prompt template
    with open(BEE_PROMPT_FILE, "r", encoding="utf-8") as f:
        prompt_text = f.read()

    # Find unprocessed files
    unprocessed_files = find_unprocessed_bee_files()

    if not unprocessed_files:
        print("No new bee transcription files to process.")
        return

    # Process each file
    files_processed = 0
    files_failed = 0

    for bee_file in unprocessed_files:
        try:
            # Extract date from filename (YYYY-MM-DD_bee.md)
            match = re.match(r"(\d{4}-\d{2}-\d{2})_bee\.md", bee_file.name)
            if not match:
                print(f"WARNING: Invalid filename format: {bee_file.name}")
                files_failed += 1
                continue

            date_str = match.group(1)

            # Process through LLM
            insight_content = process_bee_file(bee_file, prompt_text)

            # Save result
            save_bee_insight(date_str, insight_content)

            files_processed += 1

        except Exception as e:
            print(f"ERROR processing {bee_file.name}: {e}")
            files_failed += 1
            continue

    # Report statistics
    print(f"\nBee transcription processing complete:")
    print(f"  Files processed: {files_processed}")
    print(f"  Files failed: {files_failed}")
    print(f"  Total files checked: {len(unprocessed_files)}")


# ============================================================================
# Async Service Functions
# ============================================================================

async def get_existing_bee_insight_dates_async() -> Set[str]:
    """
    Async version: Get set of dates that already have bee insights in /daily.

    Checks daily insight files for the presence of bee content section.
    A file contains bee insights if it has the "🐝 Bee Transcription Insights" marker.

    Returns
    -------
    Set[str]
        Set of date strings in YYYY-MM-DD format for files with bee content

    Example
    -------
    >>> dates = await get_existing_bee_insight_dates_async()
    >>> '2025-06-27' in dates
    True
    """
    print("Scanning for files with existing bee insights...")
    dates = set()
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})\.md")
    bee_marker = "🐝 Bee Transcription Insights"

    async def check_file(file_path: Path) -> Optional[str]:
        # Skip weekly/monthly summary files
        if "-weekly" in file_path.name or file_path.name.startswith("20") and len(file_path.stem) == 7:
            return None

        # Extract date from filename
        match = date_pattern.match(file_path.name)
        if match:
            date_str = match.group(1)

            # Check if file contains bee insights marker
            try:
                content = await read_file_async(str(file_path))
                if bee_marker in content:
                    return date_str
            except Exception as e:
                print(f"Warning: Could not read {file_path.name}: {e}")
                return None
        return None

    # Check all files concurrently
    file_paths = list(Path(INSIGHTS_DIR).glob("*.md"))
    results = await asyncio.gather(*[check_file(fp) for fp in file_paths])
    dates = {r for r in results if r is not None}

    print(f"Found {len(dates)} files with existing bee insights.")
    return dates


async def find_unprocessed_bee_files_async() -> List[Path]:
    """
    Async version: Find bee transcription files that haven't been processed yet.

    Looks for files matching pattern YYYY-MM-DD_bee.md in /bee directory
    and filters out those that already have corresponding insight files.
    Only includes files dated yesterday or earlier (skips today's incomplete data).

    Returns
    -------
    List[Path]
        List of Path objects for unprocessed bee files, sorted by date

    Example
    -------
    >>> files = await find_unprocessed_bee_files_async()
    >>> len(files)
    5
    """
    print("\nScanning for unprocessed bee transcription files...")

    existing_dates = await get_existing_bee_insight_dates_async()
    unprocessed_files = []
    skipped_today = 0
    pattern = re.compile(r"(\d{4}-\d{2}-\d{2})_bee\.md")

    for file_path in Path(BEE_DIR).glob("*_bee.md"):
        match = pattern.match(file_path.name)
        if match:
            date_str = match.group(1)

            # Skip today's bee files (incomplete data)
            if not should_process_date(date_str):
                skipped_today += 1
                continue

            if date_str not in existing_dates:
                unprocessed_files.append(file_path)
            else:
                print(f"Skipping {file_path.name} - insight already exists")

    # Sort by date (filename naturally sorts correctly)
    unprocessed_files.sort()

    if skipped_today > 0:
        print(f"Skipped {skipped_today} bee file(s) from today (incomplete data)")

    print(f"Found {len(unprocessed_files)} unprocessed bee transcription files.")
    return unprocessed_files


async def process_bee_file_async(bee_file: Path, prompt_text: str) -> str:
    """
    Async version: Process a single bee transcription file through LLM.

    Combines the prompt template with the bee transcript content
    and sends to the configured LLM for processing.

    Parameters
    ----------
    bee_file : Path
        Path to the bee transcription markdown file
    prompt_text : str
        The prompt template text from bee_daily.txt

    Returns
    -------
    str
        Generated insight content from LLM

    Raises
    ------
    Exception
        If LLM generation fails

    Example
    -------
    >>> content = await process_bee_file_async(Path("bee/2025-06-27_bee.md"), prompt)
    >>> len(content) > 0
    True
    """
    print(f"Processing {bee_file.name}...")

    # Read bee transcript
    transcript_content = await read_file_async(str(bee_file))

    # Combine prompt with transcript
    full_prompt = f"{prompt_text}\n\n# BEE TRANSCRIPT\n\n{transcript_content}"

    # Generate insight using LLM
    print(f"Sending {bee_file.name} to LLM for analysis...")
    result = await generate_summary_async(full_prompt)

    return result


async def save_bee_insight_async(date: str, content: str) -> Path:
    """
    Async version: Save generated bee insight to /daily directory.

    If a daily insight file already exists for this date, the bee content
    will be appended with a clear section divider. If no file exists,
    a new file will be created with the bee content.

    Parameters
    ----------
    date : str
        Date string in YYYY-MM-DD format
    content : str
        Generated insight content to save

    Returns
    -------
    Path
        Path to the saved file

    Example
    -------
    >>> path = await save_bee_insight_async("2025-06-27", "# Daily Summary...")
    >>> path.exists()
    True
    """
    # Use standard daily filename (not -bee suffix)
    filename = f"{date}.md"
    filepath = Path(INSIGHTS_DIR) / filename

    # Check if regular daily insight already exists
    if filepath.exists():
        # MERGE: Read existing content and append bee insights
        existing_content = await read_file_async(str(filepath))

        # Create merged content with clear section divider
        merged_content = f"""{existing_content}

---

## 🐝 Bee Transcription Insights

{content}
"""
        # Write merged content
        await write_file_async(str(filepath), merged_content)

        print(f"Merged bee insights into existing daily file: {filepath}")
    else:
        # No existing daily insight - create new file with bee content
        header_content = f"""# Daily Insights - {date}

## 🐝 Bee Transcription Insights

{content}
"""
        await write_file_async(str(filepath), header_content)

        print(f"Created new daily insight file with bee content: {filepath}")

    return filepath


async def process_bee_transcriptions_async() -> None:
    """
    Async version: Main function to process all unprocessed bee transcription files.

    Workflow:
    1. Check for prompt file existence
    2. Find unprocessed bee files
    3. Process each file through LLM (in parallel)
    4. Save generated insights to /daily directory
    5. Report processing statistics

    Returns
    -------
    None

    Example
    -------
    >>> await process_bee_transcriptions_async()
    # Processing bee transcriptions...
    # Found 3 unprocessed files
    # Processed 3 files successfully
    """
    print("\nStarting bee transcription processing (async)...")

    # Check if prompt file exists
    if not os.path.exists(BEE_PROMPT_FILE):
        print(f"ERROR: Bee prompt file missing: {BEE_PROMPT_FILE}")
        print("Please create the prompt file before processing bee transcriptions.")
        return

    # Read prompt template
    prompt_text = await read_file_async(BEE_PROMPT_FILE)

    # Find unprocessed files
    unprocessed_files = await find_unprocessed_bee_files_async()

    if not unprocessed_files:
        print("No new bee transcription files to process.")
        return

    # Process files concurrently with semaphore to limit parallel LLM calls
    semaphore = asyncio.Semaphore(3)  # Max 3 concurrent LLM calls
    files_processed = 0
    files_failed = 0

    async def process_single_file(bee_file: Path) -> None:
        nonlocal files_processed, files_failed

        async with semaphore:
            try:
                # Extract date from filename (YYYY-MM-DD_bee.md)
                match = re.match(r"(\d{4}-\d{2}-\d{2})_bee\.md", bee_file.name)
                if not match:
                    print(f"WARNING: Invalid filename format: {bee_file.name}")
                    files_failed += 1
                    return

                date_str = match.group(1)

                # Process through LLM
                insight_content = await process_bee_file_async(bee_file, prompt_text)

                # Save result
                await save_bee_insight_async(date_str, insight_content)

                files_processed += 1

            except Exception as e:
                print(f"ERROR processing {bee_file.name}: {e}")
                files_failed += 1

    # Process all files concurrently (with semaphore limiting)
    await asyncio.gather(*[process_single_file(bf) for bf in unprocessed_files])

    # Report statistics
    print(f"\nBee transcription processing complete:")
    print(f"  Files processed: {files_processed}")
    print(f"  Files failed: {files_failed}")
    print(f"  Total files checked: {len(unprocessed_files)}")
