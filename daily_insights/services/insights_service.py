"""Service for managing daily insights and weekly summaries."""

import os
from pathlib import Path
from typing import Dict, List
import asyncio

from daily_insights.config import (
    INSIGHTS_DIR,
    WEEKLY_DIR,
    WEEKLY_PROMPT_FILE
)
from daily_insights.api.limitless_client import fetch_chats, fetch_chats_async
from daily_insights.api.llm_client import generate_summary, generate_summary_async
from daily_insights.utils.file_utils import (
    read_prompt_file, write_file,
    read_prompt_file_async, write_file_async, read_file_async
)
from daily_insights.utils.date_utils import should_process_date


def save_daily_insights(chats: List[Dict]) -> None:
    """
    Save daily insights from chats to markdown files.

    Only processes insights dated yesterday or earlier (skips today's incomplete data).

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
    skipped_today = 0
    for chat in chats:
        if chat.get("summary") == "Daily insights":
            created_at = chat.get("createdAt")
            if not created_at:
                continue
            date_str = created_at.split("T")[0]

            # Skip today's insights (incomplete data)
            if not should_process_date(date_str):
                skipped_today += 1
                continue

            filename = os.path.join(INSIGHTS_DIR, f"{date_str}.md")

            if os.path.exists(filename):
                print(f"Skipping existing insight: {filename}")
                continue

            print(f"Saving new insight: {filename}")
            messages = chat.get("messages", [])
            if len(messages) > 1 and "text" in messages[1]:
                text_content = messages[1]["text"]
                write_file(filename, text_content)

    if skipped_today > 0:
        print(f"Skipped {skipped_today} insight(s) from today (incomplete data)")


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

    Only includes daily files dated yesterday or earlier (skips today's incomplete data).

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
    # Filter out today's file and non-daily files
    daily_dates = [
        f.stem for f in daily_files
        if not f.stem.endswith("-weekly") and should_process_date(f.stem)
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


# ============================================================================
# Async Service Functions
# ============================================================================

async def save_daily_insights_async(chats: List[Dict]) -> None:
    """
    Async version: Save daily insights from chats to markdown files.

    Only processes insights dated yesterday or earlier (skips today's incomplete data).

    Args
    ----
    chats: List of chat dictionaries from API

    Returns
    -------
    None

    Example
    -------
    >>> chats = [{"summary": "Daily insights", "createdAt": "2025-10-28"}]
    >>> await save_daily_insights_async(chats)
    # Saves insights to daily_insights directory
    """
    skipped_today = 0

    async def save_single_insight(chat: Dict) -> bool:
        nonlocal skipped_today
        if chat.get("summary") == "Daily insights":
            created_at = chat.get("createdAt")
            if not created_at:
                return False
            date_str = created_at.split("T")[0]

            # Skip today's insights (incomplete data)
            if not should_process_date(date_str):
                skipped_today += 1
                return False

            filename = os.path.join(INSIGHTS_DIR, f"{date_str}.md")

            if os.path.exists(filename):
                print(f"Skipping existing insight: {filename}")
                return False

            print(f"Saving new insight: {filename}")
            messages = chat.get("messages", [])
            if len(messages) > 1 and "text" in messages[1]:
                text_content = messages[1]["text"]
                await write_file_async(filename, text_content)
                return True
        return False

    # Process all chats concurrently
    tasks = [save_single_insight(chat) for chat in chats]
    await asyncio.gather(*tasks)

    if skipped_today > 0:
        print(f"Skipped {skipped_today} insight(s) from today (incomplete data)")


async def fetch_and_save_daily_insights_async() -> None:
    """
    Async version: Fetch daily insights from chats API and save them.

    Returns
    -------
    None

    Example
    -------
    >>> await fetch_and_save_daily_insights_async()
    # Fetches and saves daily insights
    """
    chats = await fetch_chats_async()
    await save_daily_insights_async(chats)


async def build_weekly_summaries_async() -> None:
    """
    Async version: Build weekly summaries from daily insights.

    Only includes daily files dated yesterday or earlier (skips today's incomplete data).

    Returns
    -------
    None

    Example
    -------
    >>> await build_weekly_summaries_async()
    # Creates weekly summary files
    """
    print("\nStarting to build weekly summaries (async)...")
    daily_files = sorted(Path(INSIGHTS_DIR).glob("*.md"))
    # Filter out today's file and non-daily files
    daily_dates = [
        f.stem for f in daily_files
        if not f.stem.endswith("-weekly") and should_process_date(f.stem)
    ]

    async def build_single_weekly(week: List[str]) -> None:
        if len(week) < 7:
            print(f"Skipping incomplete week: {week[0]} to {week[-1]}")
            return

        start_date = week[0]
        end_date = week[-1]
        weekly_filename = os.path.join(
            WEEKLY_DIR, f"{start_date}_to_{end_date}-weekly.md"
        )

        if os.path.exists(weekly_filename):
            print(f"Skipping existing weekly summary: {weekly_filename}")
            return

        print(f"Building weekly summary for: {start_date} to {end_date}")

        prompt_text = await read_prompt_file_async(WEEKLY_PROMPT_FILE)
        if not prompt_text:
            return

        # Read all daily files concurrently
        async def read_daily_file(date: str) -> str:
            file_path = os.path.join(INSIGHTS_DIR, f"{date}.md")
            content = await read_file_async(file_path)
            return f"# {date}\n\n{content}"

        daily_contents = await asyncio.gather(*[read_daily_file(date) for date in week])

        combined_input = f"{prompt_text}\n\n" + "\n\n".join(daily_contents)

        output_text = await generate_summary_async(combined_input)

        await write_file_async(weekly_filename, output_text)
        print(f"Saved weekly summary: {weekly_filename}")

    # Build all weekly summaries concurrently
    weeks = [daily_dates[i:i+7] for i in range(0, len(daily_dates), 7)]
    await asyncio.gather(*[build_single_weekly(week) for week in weeks])

    print("Finished building weekly summaries.")
