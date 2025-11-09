"""Service for managing monthly journal summaries."""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
import asyncio

from daily_insights.config import (
    JOURNAL_DIR,
    JOURNAL_MONTHLY_DIR,
    JOURNAL_MONTHLY_PROMPT
)
from daily_insights.api.llm_client import generate_summary, generate_summary_async
from daily_insights.utils.file_utils import (
    read_prompt_file, write_file,
    read_prompt_file_async, write_file_async, read_file_async
)


def parse_journal_filename(filename: str) -> Optional[str]:
    """
    Extract date from journal entry filename.

    Parameters
    ----------
    filename : str
        Journal filename like "2025-03-22_journal.md"

    Returns
    -------
    str | None
        Date string "2025-03-22" or None if invalid format

    Example
    -------
    >>> parse_journal_filename("2025-03-22_journal.md")
    '2025-03-22'
    >>> parse_journal_filename("2025-04-15_journal.md")
    '2025-04-15'
    """
    # Match YYYY-MM-DD_journal.md pattern
    match = re.match(r'^(\d{4}-\d{2}-\d{2})_journal\.md$', filename)
    if match:
        return match.group(1)
    return None


def group_journals_by_month(journal_files: List[Path]) -> Dict[str, List[Path]]:
    """
    Group journal entry files by calendar month.

    Parameters
    ----------
    journal_files : List[Path]
        List of journal entry file paths

    Returns
    -------
    Dict[str, List[Path]]
        Dictionary mapping month strings (YYYY-MM) to lists of journal files

    Example
    -------
    >>> files = [Path("2025-03-22_journal.md"), Path("2025-03-28_journal.md")]
    >>> group_journals_by_month(files)
    {'2025-03': [Path('2025-03-22_journal.md'), Path('2025-03-28_journal.md')]}
    """
    months_dict = defaultdict(list)

    for journal_file in journal_files:
        date_str = parse_journal_filename(journal_file.name)
        if date_str:
            # Extract YYYY-MM from YYYY-MM-DD
            month_str = date_str[:7]  # "2025-03-22" -> "2025-03"
            months_dict[month_str].append(journal_file)

    return dict(months_dict)


def build_journal_monthly_summaries() -> None:
    """
    Build monthly summaries from daily journal entries.

    Algorithm:
    1. Scan JOURNAL_DIR for all journal entry files
    2. Group by calendar month using entry date
    3. For each month with entries:
       a. Check if monthly summary already exists
       b. Skip if exists (one-time generation rule)
       c. Load monthly journal prompt template
       d. Read and combine all journal entries for that month
       e. Generate summary via LLM
       f. Save to JOURNAL_MONTHLY_DIR/YYYY-MM.md

    Returns
    -------
    None

    Example
    -------
    >>> build_journal_monthly_summaries()
    # Creates monthly journal summary files in journal_monthly/ directory
    """
    print("\nStarting to build monthly journal summaries...")

    # Step 1: Discover journal entry files
    all_journal_files = sorted(Path(JOURNAL_DIR).glob("*_journal.md"))

    if not all_journal_files:
        print("No journal entry files found. Skipping monthly journal generation.")
        return

    print(f"Found {len(all_journal_files)} journal entry files")

    # Step 2: Group by month
    months_dict = group_journals_by_month(all_journal_files)

    if not months_dict:
        print("No valid journal files to process.")
        return

    print(f"Grouped into {len(months_dict)} months")

    # Step 3: Process each month
    for month, journal_files in sorted(months_dict.items()):
        monthly_filename = os.path.join(JOURNAL_MONTHLY_DIR, f"{month}.md")

        # Step 4: Check if already exists (one-time generation)
        if os.path.exists(monthly_filename):
            print(f"Skipping existing monthly journal summary: {monthly_filename}")
            continue

        print(f"Building monthly journal summary for {month} ({len(journal_files)} entries)")

        # Step 5: Load prompt
        prompt_text = read_prompt_file(JOURNAL_MONTHLY_PROMPT)
        if not prompt_text:
            print(f"Monthly journal prompt file missing or empty: {JOURNAL_MONTHLY_PROMPT}")
            return

        # Step 6: Read and combine journal entries
        journal_contents = []
        for journal_file in sorted(journal_files):
            try:
                date_str = parse_journal_filename(journal_file.name)
                with open(journal_file, "r", encoding="utf-8") as f:
                    content = f.read()
                journal_contents.append(
                    f"# Entry: {date_str}\n\n{content}"
                )
            except Exception as e:
                print(f"Error reading {journal_file.name}: {e}")
                continue

        if not journal_contents:
            print(f"No valid journal content for month {month}")
            continue

        # Step 7: Combine prompt with journal entries
        combined_input = f"{prompt_text}\n\n" + "\n\n---\n\n".join(journal_contents)

        # Step 8: Generate summary via LLM
        print(f"Generating monthly journal summary for {month}...")
        output_text = generate_summary(combined_input)

        # Step 9: Save monthly file
        write_file(monthly_filename, output_text)
        print(f"Saved monthly journal summary: {monthly_filename}")

    print("Finished building monthly journal summaries.")


# ============================================================================
# Async Service Functions
# ============================================================================

async def build_journal_monthly_summaries_async() -> None:
    """
    Async version: Build monthly summaries from daily journal entries.

    Algorithm:
    1. Scan JOURNAL_DIR for all journal entry files
    2. Group by calendar month using entry date
    3. For each month with entries:
       a. Check if monthly summary already exists
       b. Skip if exists (one-time generation rule)
       c. Load monthly journal prompt template
       d. Read and combine all journal entries for that month (in parallel)
       e. Generate summary via LLM
       f. Save to JOURNAL_MONTHLY_DIR/YYYY-MM.md

    Returns
    -------
    None

    Example
    -------
    >>> await build_journal_monthly_summaries_async()
    # Creates monthly journal summary files in journal_monthly/ directory
    """
    print("\nStarting to build monthly journal summaries (async)...")

    # Step 1: Discover journal entry files
    all_journal_files = sorted(Path(JOURNAL_DIR).glob("*_journal.md"))

    if not all_journal_files:
        print("No journal entry files found. Skipping monthly journal generation.")
        return

    print(f"Found {len(all_journal_files)} journal entry files")

    # Step 2: Group by month
    months_dict = group_journals_by_month(all_journal_files)

    if not months_dict:
        print("No valid journal files to process.")
        return

    print(f"Grouped into {len(months_dict)} months")

    # Step 3: Load prompt once
    prompt_text = await read_prompt_file_async(JOURNAL_MONTHLY_PROMPT)
    if not prompt_text:
        print(f"Monthly journal prompt file missing or empty: {JOURNAL_MONTHLY_PROMPT}")
        return

    # Step 4: Process each month
    async def process_month(month: str, journal_files: List[Path]) -> None:
        monthly_filename = os.path.join(JOURNAL_MONTHLY_DIR, f"{month}.md")

        # Check if already exists (one-time generation)
        if os.path.exists(monthly_filename):
            print(f"Skipping existing monthly journal summary: {monthly_filename}")
            return

        print(f"Building monthly journal summary for {month} ({len(journal_files)} entries)")

        # Read all journal files concurrently
        async def read_journal_entry(journal_file: Path) -> Optional[str]:
            try:
                date_str = parse_journal_filename(journal_file.name)
                content = await read_file_async(str(journal_file))
                return f"# Entry: {date_str}\n\n{content}"
            except Exception as e:
                print(f"Error reading {journal_file.name}: {e}")
                return None

        journal_contents = await asyncio.gather(*[read_journal_entry(jf) for jf in sorted(journal_files)])
        journal_contents = [jc for jc in journal_contents if jc is not None]

        if not journal_contents:
            print(f"No valid journal content for month {month}")
            return

        # Combine prompt with journal entries
        combined_input = f"{prompt_text}\n\n" + "\n\n---\n\n".join(journal_contents)

        # Generate summary via LLM
        print(f"Generating monthly journal summary for {month}...")
        output_text = await generate_summary_async(combined_input)

        # Save monthly file
        await write_file_async(monthly_filename, output_text)
        print(f"Saved monthly journal summary: {monthly_filename}")

    # Process all months concurrently
    await asyncio.gather(*[
        process_month(month, journal_files)
        for month, journal_files in sorted(months_dict.items())
    ])

    print("Finished building monthly journal summaries.")
