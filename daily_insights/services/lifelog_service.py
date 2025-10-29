"""Service for managing lifelogs from the Limitless API."""

import re
from pathlib import Path
from typing import Dict, List, Set
from dateutil import parser

from daily_insights.config import LIFELOGS_DIR
from daily_insights.api.limitless_client import fetch_new_lifelogs


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
