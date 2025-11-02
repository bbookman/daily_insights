"""Service for managing monthly summaries."""

import os
from pathlib import Path
from typing import Dict, List
import asyncio

from daily_insights.config import (
    WEEKLY_DIR,
    MONTHLY_DIR,
    MONTHLY_PROMPT_FILE
)
from daily_insights.api.llm_client import generate_summary, generate_summary_async
from daily_insights.utils.date_utils import (
    parse_week_filename,
    group_weeks_by_month,
    should_process_date
)
from daily_insights.utils.file_utils import (
    read_prompt_file, write_file,
    read_prompt_file_async, write_file_async, read_file_async
)


def week_contains_today(week_filename: str) -> bool:
    """
    Check if a weekly file's date range includes today.

    Parameters
    ----------
    week_filename : str
        Weekly filename like "2025-09-03_to_2025-09-10-weekly.md"

    Returns
    -------
    bool
        True if the week's date range includes today, False otherwise
    """
    try:
        start_date, end_date = parse_week_filename(week_filename)
        # If either the start or end date should not be processed (is today or later), skip this week
        return not should_process_date(start_date) or not should_process_date(end_date)
    except ValueError:
        # If we can't parse the filename, default to excluding it
        return True


def build_monthly_summaries() -> None:
    """
    Build monthly summaries from weekly summaries.

    Only includes weekly files dated yesterday or earlier (skips weeks containing today).

    Algorithm:
    1. Scan ./weekly/ for all weekly summary files
    2. Filter out weeks containing today (incomplete data)
    3. Group by calendar month using start_date
    4. Skip incomplete months (< 4 weeks)
    5. For each complete month:
       a. Check if monthly summary already exists
       b. Skip if exists (one-time generation rule)
       c. Load monthly prompt template
       d. Read and combine all weekly summaries for that month
       e. Generate summary via LLM
       f. Save to ./monthly/YYYY-MM.md

    Returns
    -------
    None

    Example
    -------
    >>> build_monthly_summaries()
    # Creates monthly summary files in ./monthly/ directory
    """
    print("\nStarting to build monthly summaries...")

    # Step 1: Discover weekly files and filter out today
    all_weekly_files = sorted(Path(WEEKLY_DIR).glob("*-weekly.md"))
    weekly_files = [f for f in all_weekly_files if not week_contains_today(f.name)]

    if len(all_weekly_files) > len(weekly_files):
        skipped = len(all_weekly_files) - len(weekly_files)
        print(f"Skipped {skipped} weekly file(s) containing today (incomplete data)")

    if not weekly_files:
        print("No weekly summary files found. Skipping monthly generation.")
        return

    print(f"Found {len(weekly_files)} weekly summary files")

    # Step 2: Group by month
    months_dict = group_weeks_by_month(weekly_files)

    if not months_dict:
        print("No valid weekly files to process.")
        return

    print(f"Grouped into {len(months_dict)} months")

    # Step 3: Process each month
    for month, week_files in sorted(months_dict.items()):
        # Skip incomplete months (< 4 weeks)
        if len(week_files) < 4:
            print(f"Skipping incomplete month {month}: only {len(week_files)} weeks")
            continue

        monthly_filename = os.path.join(MONTHLY_DIR, f"{month}.md")

        # Step 4: Check if already exists (one-time generation)
        if os.path.exists(monthly_filename):
            print(f"Skipping existing monthly summary: {monthly_filename}")
            continue

        print(f"Building monthly summary for {month} ({len(week_files)} weeks)")

        # Step 5: Load prompt
        prompt_text = read_prompt_file(MONTHLY_PROMPT_FILE)
        if not prompt_text:
            print(f"Monthly prompt file missing or empty: {MONTHLY_PROMPT_FILE}")
            return

        # Step 6: Read and combine weekly summaries
        weekly_contents = []
        for week_file in sorted(week_files):
            try:
                start_date, end_date = parse_week_filename(week_file.name)
                with open(week_file, "r", encoding="utf-8") as f:
                    content = f.read()
                weekly_contents.append(
                    f"# Week: {start_date} to {end_date}\n\n{content}"
                )
            except Exception as e:
                print(f"Error reading {week_file.name}: {e}")
                continue

        if not weekly_contents:
            print(f"No valid weekly content for month {month}")
            continue

        # Step 7: Combine prompt with weekly content
        combined_input = f"{prompt_text}\n\n" + "\n\n---\n\n".join(weekly_contents)

        # Step 8: Generate summary via LLM
        print(f"Generating monthly summary for {month}...")
        output_text = generate_summary(combined_input)

        # Step 9: Save monthly file
        write_file(monthly_filename, output_text)
        print(f"Saved monthly summary: {monthly_filename}")

    print("Finished building monthly summaries.")


# ============================================================================
# Async Service Functions
# ============================================================================

async def build_monthly_summaries_async() -> None:
    """
    Async version: Build monthly summaries from weekly summaries.

    Only includes weekly files dated yesterday or earlier (skips weeks containing today).

    Algorithm:
    1. Scan ./weekly/ for all weekly summary files
    2. Filter out weeks containing today (incomplete data)
    3. Group by calendar month using start_date
    4. Skip incomplete months (< 4 weeks)
    5. For each complete month:
       a. Check if monthly summary already exists
       b. Skip if exists (one-time generation rule)
       c. Load monthly prompt template
       d. Read and combine all weekly summaries for that month (in parallel)
       e. Generate summary via LLM
       f. Save to ./monthly/YYYY-MM.md

    Returns
    -------
    None

    Example
    -------
    >>> await build_monthly_summaries_async()
    # Creates monthly summary files in ./monthly/ directory
    """
    print("\nStarting to build monthly summaries (async)...")

    # Step 1: Discover weekly files and filter out today
    all_weekly_files = sorted(Path(WEEKLY_DIR).glob("*-weekly.md"))
    weekly_files = [f for f in all_weekly_files if not week_contains_today(f.name)]

    if len(all_weekly_files) > len(weekly_files):
        skipped = len(all_weekly_files) - len(weekly_files)
        print(f"Skipped {skipped} weekly file(s) containing today (incomplete data)")

    if not weekly_files:
        print("No weekly summary files found. Skipping monthly generation.")
        return

    print(f"Found {len(weekly_files)} weekly summary files")

    # Step 2: Group by month
    months_dict = group_weeks_by_month(weekly_files)

    if not months_dict:
        print("No valid weekly files to process.")
        return

    print(f"Grouped into {len(months_dict)} months")

    # Step 3: Load prompt once
    prompt_text = await read_prompt_file_async(MONTHLY_PROMPT_FILE)
    if not prompt_text:
        print(f"Monthly prompt file missing or empty: {MONTHLY_PROMPT_FILE}")
        return

    # Step 4: Process each month
    async def process_month(month: str, week_files: List[Path]) -> None:
        # Skip incomplete months (< 4 weeks)
        if len(week_files) < 4:
            print(f"Skipping incomplete month {month}: only {len(week_files)} weeks")
            return

        monthly_filename = os.path.join(MONTHLY_DIR, f"{month}.md")

        # Check if already exists (one-time generation)
        if os.path.exists(monthly_filename):
            print(f"Skipping existing monthly summary: {monthly_filename}")
            return

        print(f"Building monthly summary for {month} ({len(week_files)} weeks)")

        # Read all weekly files concurrently
        async def read_weekly(week_file: Path) -> str | None:
            try:
                start_date, end_date = parse_week_filename(week_file.name)
                content = await read_file_async(str(week_file))
                return f"# Week: {start_date} to {end_date}\n\n{content}"
            except Exception as e:
                print(f"Error reading {week_file.name}: {e}")
                return None

        weekly_contents = await asyncio.gather(*[read_weekly(wf) for wf in sorted(week_files)])
        weekly_contents = [wc for wc in weekly_contents if wc is not None]

        if not weekly_contents:
            print(f"No valid weekly content for month {month}")
            return

        # Combine prompt with weekly content
        combined_input = f"{prompt_text}\n\n" + "\n\n---\n\n".join(weekly_contents)

        # Generate summary via LLM
        print(f"Generating monthly summary for {month}...")
        output_text = await generate_summary_async(combined_input)

        # Save monthly file
        await write_file_async(monthly_filename, output_text)
        print(f"Saved monthly summary: {monthly_filename}")

    # Process all months concurrently
    await asyncio.gather(*[
        process_month(month, week_files)
        for month, week_files in sorted(months_dict.items())
    ])

    print("Finished building monthly summaries.")
