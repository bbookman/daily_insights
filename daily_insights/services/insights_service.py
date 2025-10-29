"""Service for managing daily insights and weekly summaries."""

import os
from pathlib import Path
from typing import Dict, List

from daily_insights.config import (
    INSIGHTS_DIR,
    WEEKLY_DIR,
    WEEKLY_PROMPT_FILE
)
from daily_insights.api.limitless_client import fetch_chats
from daily_insights.api.llm_client import generate_summary
from daily_insights.utils.file_utils import read_prompt_file, write_file


def save_daily_insights(chats: List[Dict]) -> None:
    """
    Save daily insights from chats to markdown files.

    Args
    ----
    chats: List of chat dictionaries from API

    Returns
    -------
    None

    Example
    -------
    >>> chats = [{"summary": "Daily insights", "createdAt": "2025-10-28"}]
    >>> save_daily_insights(chats)
    # Saves insights to daily_insights directory
    """
    for chat in chats:
        if chat.get("summary") == "Daily insights":
            created_at = chat.get("createdAt")
            if not created_at:
                continue
            date_str = created_at.split("T")[0]
            filename = os.path.join(INSIGHTS_DIR, f"{date_str}.md")

            if os.path.exists(filename):
                print(f"Skipping existing insight: {filename}")
                continue

            print(f"Saving new insight: {filename}")
            messages = chat.get("messages", [])
            if len(messages) > 1 and "text" in messages[1]:
                text_content = messages[1]["text"]
                write_file(filename, text_content)


def fetch_and_save_daily_insights() -> None:
    """
    Fetch daily insights from chats API and save them.

    Returns
    -------
    None

    Example
    -------
    >>> fetch_and_save_daily_insights()
    # Fetches and saves daily insights
    """
    chats = fetch_chats()
    save_daily_insights(chats)


def build_weekly_summaries() -> None:
    """
    Build weekly summaries from daily insights.

    Returns
    -------
    None

    Example
    -------
    >>> build_weekly_summaries()
    # Creates weekly summary files
    """
    print("\nStarting to build weekly summaries...")
    daily_files = sorted(Path(INSIGHTS_DIR).glob("*.md"))
    daily_dates = [
        f.stem for f in daily_files if not f.stem.endswith("-weekly")
    ]

    for i in range(0, len(daily_dates), 7):
        week = daily_dates[i:i+7]
        if len(week) < 7:
            print(f"Skipping incomplete week: {week[0]} to {week[-1]}")
            continue

        start_date = week[0]
        end_date = week[-1]
        weekly_filename = os.path.join(
            WEEKLY_DIR, f"{start_date}_to_{end_date}-weekly.md"
        )

        if os.path.exists(weekly_filename):
            print(f"Skipping existing weekly summary: {weekly_filename}")
            continue

        print(f"Building weekly summary for: {start_date} to {end_date}")

        prompt_text = read_prompt_file(WEEKLY_PROMPT_FILE)
        if not prompt_text:
            return

        daily_contents = []
        for date in week:
            file_path = os.path.join(INSIGHTS_DIR, f"{date}.md")
            with open(file_path, "r", encoding="utf-8") as f:
                daily_contents.append(f"# {date}\n\n{f.read()}")

        combined_input = f"{prompt_text}\n\n" + "\n\n".join(daily_contents)

        output_text = generate_summary(combined_input)

        write_file(weekly_filename, output_text)
        print(f"Saved weekly summary: {weekly_filename}")

    print("Finished building weekly summaries.")
