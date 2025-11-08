"""Service for managing monthly therapy summaries."""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
import asyncio

from daily_insights.config import (
    PSYCHOLOGIST_DIR,
    THERAPY_MONTHLY_DIR,
    THERAPY_MONTHLY_PROMPT,
    THERAPY_MONTHLY_MIN_SESSIONS
)
from daily_insights.api.llm_client import generate_summary, generate_summary_async
from daily_insights.utils.file_utils import (
    read_prompt_file, write_file,
    read_prompt_file_async, write_file_async, read_file_async
)


def parse_therapy_filename(filename: str) -> Optional[str]:
    """
    Extract date from therapy session filename.

    Parameters
    ----------
    filename : str
        Therapy filename like "2025-04-01-psychologist.md" or "2025-04-01-psychologist-session1.md"

    Returns
    -------
    str | None
        Date string "2025-04-01" or None if invalid format

    Example
    -------
    >>> parse_therapy_filename("2025-04-01-psychologist.md")
    '2025-04-01'
    >>> parse_therapy_filename("2025-04-15-psychologist-session2.md")
    '2025-04-15'
    """
    # Match YYYY-MM-DD at start of filename
    match = re.match(r'^(\d{4}-\d{2}-\d{2})', filename)
    if match:
        return match.group(1)
    return None


def group_therapy_by_month(therapy_files: List[Path]) -> Dict[str, List[Path]]:
    """
    Group therapy session files by calendar month.

    Parameters
    ----------
    therapy_files : List[Path]
        List of therapy session file paths

    Returns
    -------
    Dict[str, List[Path]]
        Dictionary mapping month strings (YYYY-MM) to lists of therapy files

    Example
    -------
    >>> files = [Path("2025-04-01-psychologist.md"), Path("2025-04-15-psychologist.md")]
    >>> group_therapy_by_month(files)
    {'2025-04': [Path('2025-04-01-psychologist.md'), Path('2025-04-15-psychologist.md')]}
    """
    months_dict = defaultdict(list)

    for therapy_file in therapy_files:
        date_str = parse_therapy_filename(therapy_file.name)
        if date_str:
            # Extract YYYY-MM from YYYY-MM-DD
            month_str = date_str[:7]  # "2025-04-01" -> "2025-04"
            months_dict[month_str].append(therapy_file)

    return dict(months_dict)


def build_therapy_monthly_summaries() -> None:
    """
    Build monthly therapy summaries from individual therapy sessions.

    Algorithm:
    1. Scan PSYCHOLOGIST_DIR for all therapy session files
    2. Group by calendar month using session date
    3. Skip incomplete months (< THERAPY_MONTHLY_MIN_SESSIONS sessions)
    4. For each complete month:
       a. Check if monthly therapy summary already exists
       b. Skip if exists (one-time generation rule)
       c. Load monthly therapy prompt template
       d. Read and combine all therapy sessions for that month
       e. Generate summary via LLM
       f. Save to THERAPY_MONTHLY_DIR/YYYY-MM-therapy.md

    Returns
    -------
    None

    Example
    -------
    >>> build_therapy_monthly_summaries()
    # Creates monthly therapy summary files in therapy_monthly/ directory
    """
    print("\nStarting to build monthly therapy summaries...")

    # Step 1: Discover therapy session files
    all_therapy_files = sorted(Path(PSYCHOLOGIST_DIR).glob("*-psychologist*.md"))

    if not all_therapy_files:
        print("No therapy session files found. Skipping monthly therapy generation.")
        return

    print(f"Found {len(all_therapy_files)} therapy session files")

    # Step 2: Group by month
    months_dict = group_therapy_by_month(all_therapy_files)

    if not months_dict:
        print("No valid therapy files to process.")
        return

    print(f"Grouped into {len(months_dict)} months")

    # Step 3: Process each month
    for month, therapy_files in sorted(months_dict.items()):
        # Skip months with insufficient sessions
        if len(therapy_files) < THERAPY_MONTHLY_MIN_SESSIONS:
            print(f"Skipping month {month}: only {len(therapy_files)} session(s), need {THERAPY_MONTHLY_MIN_SESSIONS}")
            continue

        monthly_filename = os.path.join(THERAPY_MONTHLY_DIR, f"{month}-therapy.md")

        # Step 4: Check if already exists (one-time generation)
        if os.path.exists(monthly_filename):
            print(f"Skipping existing monthly therapy summary: {monthly_filename}")
            continue

        print(f"Building monthly therapy summary for {month} ({len(therapy_files)} sessions)")

        # Step 5: Load prompt
        prompt_text = read_prompt_file(THERAPY_MONTHLY_PROMPT)
        if not prompt_text:
            print(f"Monthly therapy prompt file missing or empty: {THERAPY_MONTHLY_PROMPT}")
            return

        # Step 6: Read and combine therapy sessions
        therapy_contents = []
        for therapy_file in sorted(therapy_files):
            try:
                date_str = parse_therapy_filename(therapy_file.name)
                with open(therapy_file, "r", encoding="utf-8") as f:
                    content = f.read()
                therapy_contents.append(
                    f"# Session: {date_str}\n\n{content}"
                )
            except Exception as e:
                print(f"Error reading {therapy_file.name}: {e}")
                continue

        if not therapy_contents:
            print(f"No valid therapy content for month {month}")
            continue

        # Step 7: Combine prompt with therapy sessions
        combined_input = f"{prompt_text}\n\n" + "\n\n---\n\n".join(therapy_contents)

        # Step 8: Generate summary via LLM
        print(f"Generating monthly therapy summary for {month}...")
        output_text = generate_summary(combined_input)

        # Step 9: Save monthly file
        write_file(monthly_filename, output_text)
        print(f"Saved monthly therapy summary: {monthly_filename}")

    print("Finished building monthly therapy summaries.")


# ============================================================================
# Async Service Functions
# ============================================================================

async def build_therapy_monthly_summaries_async() -> None:
    """
    Async version: Build monthly therapy summaries from individual therapy sessions.

    Algorithm:
    1. Scan PSYCHOLOGIST_DIR for all therapy session files
    2. Group by calendar month using session date
    3. Skip incomplete months (< THERAPY_MONTHLY_MIN_SESSIONS sessions)
    4. For each complete month:
       a. Check if monthly therapy summary already exists
       b. Skip if exists (one-time generation rule)
       c. Load monthly therapy prompt template
       d. Read and combine all therapy sessions for that month (in parallel)
       e. Generate summary via LLM
       f. Save to THERAPY_MONTHLY_DIR/YYYY-MM-therapy.md

    Returns
    -------
    None

    Example
    -------
    >>> await build_therapy_monthly_summaries_async()
    # Creates monthly therapy summary files in therapy_monthly/ directory
    """
    print("\nStarting to build monthly therapy summaries (async)...")

    # Step 1: Discover therapy session files
    all_therapy_files = sorted(Path(PSYCHOLOGIST_DIR).glob("*-psychologist*.md"))

    if not all_therapy_files:
        print("No therapy session files found. Skipping monthly therapy generation.")
        return

    print(f"Found {len(all_therapy_files)} therapy session files")

    # Step 2: Group by month
    months_dict = group_therapy_by_month(all_therapy_files)

    if not months_dict:
        print("No valid therapy files to process.")
        return

    print(f"Grouped into {len(months_dict)} months")

    # Step 3: Load prompt once
    prompt_text = await read_prompt_file_async(THERAPY_MONTHLY_PROMPT)
    if not prompt_text:
        print(f"Monthly therapy prompt file missing or empty: {THERAPY_MONTHLY_PROMPT}")
        return

    # Step 4: Process each month
    async def process_month(month: str, therapy_files: List[Path]) -> None:
        # Skip months with insufficient sessions
        if len(therapy_files) < THERAPY_MONTHLY_MIN_SESSIONS:
            print(f"Skipping month {month}: only {len(therapy_files)} session(s), need {THERAPY_MONTHLY_MIN_SESSIONS}")
            return

        monthly_filename = os.path.join(THERAPY_MONTHLY_DIR, f"{month}-therapy.md")

        # Check if already exists (one-time generation)
        if os.path.exists(monthly_filename):
            print(f"Skipping existing monthly therapy summary: {monthly_filename}")
            return

        print(f"Building monthly therapy summary for {month} ({len(therapy_files)} sessions)")

        # Read all therapy files concurrently
        async def read_therapy_session(therapy_file: Path) -> Optional[str]:
            try:
                date_str = parse_therapy_filename(therapy_file.name)
                content = await read_file_async(str(therapy_file))
                return f"# Session: {date_str}\n\n{content}"
            except Exception as e:
                print(f"Error reading {therapy_file.name}: {e}")
                return None

        therapy_contents = await asyncio.gather(*[read_therapy_session(tf) for tf in sorted(therapy_files)])
        therapy_contents = [tc for tc in therapy_contents if tc is not None]

        if not therapy_contents:
            print(f"No valid therapy content for month {month}")
            return

        # Combine prompt with therapy sessions
        combined_input = f"{prompt_text}\n\n" + "\n\n---\n\n".join(therapy_contents)

        # Generate summary via LLM
        print(f"Generating monthly therapy summary for {month}...")
        output_text = await generate_summary_async(combined_input)

        # Save monthly file
        await write_file_async(monthly_filename, output_text)
        print(f"Saved monthly therapy summary: {monthly_filename}")

    # Process all months concurrently
    await asyncio.gather(*[
        process_month(month, therapy_files)
        for month, therapy_files in sorted(months_dict.items())
    ])

    print("Finished building monthly therapy summaries.")
