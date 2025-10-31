"""Service for managing lifelogs from the Limitless API."""

import re
from pathlib import Path
from typing import Dict, List, Set
from dateutil import parser
import asyncio

from daily_insights.config import LIFELOGS_DIR
from daily_insights.api.limitless_client import fetch_new_lifelogs, fetch_new_lifelogs_async
from daily_insights.utils.file_utils import append_file_async, write_file_async
from daily_insights.services.speaker_service import (
    identify_speakers_async,
    apply_speaker_labels,
    mark_file_processed
)


def get_existing_lifelog_dates() -> Set[str]:
    """
    Get set of dates from existing lifelog markdown files.

    Returns
    -------
    Set of date strings in YYYY-MM-DD format

    Example
    -------
    >>> dates = get_existing_lifelog_dates()
    >>> print(len(dates))
    42
    """
    print("Scanning for existing lifelog dates...")
    dates = set()
    pattern = re.compile(r"(\d{4}-\d{2}-\d{2}).md")
    for file_path in Path(LIFELOGS_DIR).glob("*.md"):
        match = pattern.search(file_path.name)
        if match:
            dates.add(match.group(1))
    print(f"Found {len(dates)} existing lifelog files.")
    return dates


def save_lifelogs(lifelogs: List[Dict]) -> None:
    """
    Group lifelogs by date and save them to markdown files.

    Args
    ----
    lifelogs: List of lifelog dictionaries from API

    Returns
    -------
    None

    Example
    -------
    >>> lifelogs = [{"startTime": "2025-10-28T14:30:00Z", ...}]
    >>> save_lifelogs(lifelogs)
    # Creates markdown files in lifelogs directory
    """
    if not lifelogs:
        print("No new lifelogs to save.")
        return

    print("\nSaving new lifelogs to markdown files...")
    lifelogs_by_date = {}
    for log in lifelogs:
        try:
            date_str = parser.parse(log["startTime"]).strftime("%Y-%m-%d")
            if date_str not in lifelogs_by_date:
                lifelogs_by_date[date_str] = []
            lifelogs_by_date[date_str].append(log)
        except (KeyError, ValueError):
            print(
                f"Could not process lifelog due to missing/invalid "
                f"startTime: {log.get('id')}"
            )

    files_created_or_updated = set()
    for date_str, logs_for_day in lifelogs_by_date.items():
        logs_for_day.sort(key=lambda x: x["startTime"])
        print(f"Processing {len(logs_for_day)} new lifelogs for {date_str}")

        filename = f"{date_str}.md"
        filepath = Path(LIFELOGS_DIR) / filename

        is_new_file = not filepath.exists()
        with open(filepath, "a", encoding="utf-8") as f:
            if is_new_file:
                file_date = parser.parse(date_str)
                date_header = f"# {file_date.strftime('%A, %B %d, %Y')}\n"
                f.write(date_header)

            for lifelog in logs_for_day:
                start_time = parser.parse(lifelog["startTime"])
                time_str = start_time.strftime("%H:%M")
                content = lifelog.get("markdown", "").strip().replace(
                    "- You", "- Bruce"
                )
                if content:
                    entry_content = (
                        f"\n\n---\n\n### {time_str}\n\n{content}"
                    )
                    f.write(entry_content)

        files_created_or_updated.add(filepath.name)

    if files_created_or_updated:
        print(
            f"Lifelog export complete. {len(files_created_or_updated)} "
            f"files created/updated in {LIFELOGS_DIR}"
        )
    else:
        print("No new lifelogs were saved.")


def fetch_and_save_lifelogs() -> None:
    """
    Fetch new lifelogs from API and save them to disk.

    Returns
    -------
    None

    Example
    -------
    >>> fetch_and_save_lifelogs()
    # Fetches and saves new lifelogs
    """
    existing_dates = get_existing_lifelog_dates()
    new_lifelogs = fetch_new_lifelogs(existing_dates)
    save_lifelogs(new_lifelogs)


# ============================================================================
# Async Service Functions
# ============================================================================

async def get_existing_lifelog_dates_async() -> Set[str]:
    """
    Async version: Get set of dates from existing lifelog markdown files.

    Returns
    -------
    Set of date strings in YYYY-MM-DD format

    Example
    -------
    >>> dates = await get_existing_lifelog_dates_async()
    >>> print(len(dates))
    42
    """
    print("Scanning for existing lifelog dates...")
    dates = set()
    pattern = re.compile(r"(\d{4}-\d{2}-\d{2}).md")
    for file_path in Path(LIFELOGS_DIR).glob("*.md"):
        match = pattern.search(file_path.name)
        if match:
            dates.add(match.group(1))
    print(f"Found {len(dates)} existing lifelog files.")
    return dates


async def save_lifelogs_async(lifelogs: List[Dict]) -> None:
    """
    Async version: Group lifelogs by date and save them to markdown files.

    Args
    ----
    lifelogs: List of lifelog dictionaries from API

    Returns
    -------
    None

    Example
    -------
    >>> lifelogs = [{"startTime": "2025-10-28T14:30:00Z", ...}]
    >>> await save_lifelogs_async(lifelogs)
    # Creates markdown files in lifelogs directory
    """
    if not lifelogs:
        print("No new lifelogs to save.")
        return

    print("\nSaving new lifelogs to markdown files...")
    lifelogs_by_date = {}
    for log in lifelogs:
        try:
            date_str = parser.parse(log["startTime"]).strftime("%Y-%m-%d")
            if date_str not in lifelogs_by_date:
                lifelogs_by_date[date_str] = []
            lifelogs_by_date[date_str].append(log)
        except (KeyError, ValueError):
            print(
                f"Could not process lifelog due to missing/invalid "
                f"startTime: {log.get('id')}"
            )

    files_created_or_updated = set()

    # Process each date's lifelogs concurrently
    async def process_date(date_str: str, logs_for_day: List[Dict]) -> None:
        logs_for_day.sort(key=lambda x: x["startTime"])
        print(f"Processing {len(logs_for_day)} new lifelogs for {date_str}")

        filename = f"{date_str}.md"
        filepath = Path(LIFELOGS_DIR) / filename

        is_new_file = not filepath.exists()

        # Build all content for this date
        content_parts = []

        if is_new_file:
            file_date = parser.parse(date_str)
            date_header = f"# {file_date.strftime('%A, %B %d, %Y')}\n"
            content_parts.append(date_header)

        for lifelog in logs_for_day:
            start_time = parser.parse(lifelog["startTime"])
            time_str = start_time.strftime("%H:%M")
            content = lifelog.get("markdown", "").strip().replace(
                "- You", "- Bruce"
            )
            if content:
                entry_content = f"\n\n---\n\n### {time_str}\n\n{content}"
                content_parts.append(entry_content)

        combined_content = "".join(content_parts)

        # Apply speaker identification
        try:
            print(f"Identifying speakers in {date_str}...")
            speaker_mappings = await identify_speakers_async(combined_content)

            if speaker_mappings:
                print(f"Found {len(speaker_mappings)} speaker mappings for {date_str}")
                combined_content = apply_speaker_labels(combined_content, speaker_mappings)
            else:
                print(f"No speaker mappings generated for {date_str}")

        except Exception as e:
            print(f"Warning: Speaker identification failed for {date_str}: {e}")
            # Continue with original content if speaker identification fails

        # Write or append based on whether file exists
        if is_new_file:
            await write_file_async(str(filepath), combined_content)
        else:
            await append_file_async(str(filepath), combined_content)

        # Mark file as processed
        mark_file_processed(f"lifelogs/{filepath.name}")

        files_created_or_updated.add(filepath.name)

    # Process all dates concurrently
    tasks = [
        process_date(date_str, logs_for_day)
        for date_str, logs_for_day in lifelogs_by_date.items()
    ]
    await asyncio.gather(*tasks)

    if files_created_or_updated:
        print(
            f"Lifelog export complete. {len(files_created_or_updated)} "
            f"files created/updated in {LIFELOGS_DIR}"
        )
    else:
        print("No new lifelogs were saved.")


async def fetch_and_save_lifelogs_async() -> None:
    """
    Async version: Fetch new lifelogs from API and save them to disk.

    Returns
    -------
    None

    Example
    -------
    >>> await fetch_and_save_lifelogs_async()
    # Fetches and saves new lifelogs
    """
    existing_dates = await get_existing_lifelog_dates_async()
    new_lifelogs = await fetch_new_lifelogs_async(existing_dates)
    await save_lifelogs_async(new_lifelogs)
