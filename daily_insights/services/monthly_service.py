"""Service for managing monthly summaries."""

import os
from pathlib import Path
from typing import Dict, List

from daily_insights.config import (
    WEEKLY_DIR,
    MONTHLY_DIR,
    MONTHLY_PROMPT_FILE
)
from daily_insights.api.llm_client import generate_summary
from daily_insights.utils.date_utils import (
    parse_week_filename,
    group_weeks_by_month
)
from daily_insights.utils.file_utils import read_prompt_file, write_file


def build_monthly_summaries() -> None:
    """
    Build monthly summaries from weekly summaries.

    Algorithm:
    1. Scan ./weekly/ for all weekly summary files
    2. Group by calendar month using start_date
    3. Skip incomplete months (< 4 weeks)
    4. For each complete month:
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

    # Step 1: Discover weekly files
    weekly_files = sorted(Path(WEEKLY_DIR).glob("*-weekly.md"))

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
