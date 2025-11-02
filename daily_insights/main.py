"""Main entry point for the daily insights system."""

import asyncio

from daily_insights.config import (
    ensure_directories,
    FETCH_LIFELOGS,
    FETCH_DAILY_INSIGHTS,
    PROCESS_BEE_TRANSCRIPTIONS,
    PROCESS_JOURNAL_ENTRIES,
    PROCESS_THERAPY_SESSIONS,
    CREATE_WEEKLY_SUMMARIES,
    CREATE_MONTHLY_SUMMARIES,
    LABEL_SPEAKERS
)
from daily_insights.services.lifelog_service import (
    fetch_and_save_lifelogs,
    fetch_and_save_lifelogs_async
)
from daily_insights.services.insights_service import (
    fetch_and_save_daily_insights,
    build_weekly_summaries,
    fetch_and_save_daily_insights_async,
    build_weekly_summaries_async
)
from daily_insights.services.bee_service import (
    process_bee_transcriptions,
    process_bee_transcriptions_async
)
from daily_insights.services.monthly_service import (
    build_monthly_summaries,
    build_monthly_summaries_async
)
from daily_insights.services.therapy_service import (
    process_therapy_sessions,
    process_therapy_sessions_async
)
from daily_insights.utils.pipeline_stats import display_pipeline_summary


def main() -> None:
    """
    Run the complete daily insights pipeline (synchronous version).

    Returns
    -------
    None

    Example
    -------
    >>> main()
    # Executes full pipeline: lifelogs, insights, bee processing, weekly/monthly summaries, therapy
    """
    ensure_directories()

    if FETCH_LIFELOGS:
        fetch_and_save_lifelogs()
    else:
        print("⏭️  Skipping lifelog fetching (FETCH_LIFELOGS=False)")

    if FETCH_DAILY_INSIGHTS:
        fetch_and_save_daily_insights()
    else:
        print("⏭️  Skipping daily insights fetching (FETCH_DAILY_INSIGHTS=False)")

    if PROCESS_BEE_TRANSCRIPTIONS:
        process_bee_transcriptions()
    else:
        print("⏭️  Skipping bee transcription processing (PROCESS_BEE_TRANSCRIPTIONS=False)")

    if CREATE_WEEKLY_SUMMARIES:
        build_weekly_summaries()
    else:
        print("⏭️  Skipping weekly summaries (CREATE_WEEKLY_SUMMARIES=False)")

    if CREATE_MONTHLY_SUMMARIES:
        build_monthly_summaries()
    else:
        print("⏭️  Skipping monthly summaries (CREATE_MONTHLY_SUMMARIES=False)")

    if PROCESS_THERAPY_SESSIONS:
        process_therapy_sessions()
    else:
        print("⏭️  Skipping therapy session processing (PROCESS_THERAPY_SESSIONS=False)")

    # Display comprehensive pipeline statistics
    print("\n")
    display_pipeline_summary()


async def main_async() -> None:
    """
    Run the complete daily insights pipeline (asynchronous version).

    Uses hybrid approach for optimal performance:
    - Stage 1: Fetch data in parallel (lifelogs + insights)
    - Stage 2: Process files in parallel (bee + therapy)
    - Stage 3: Generate summaries in parallel (weekly + monthly)

    Returns
    -------
    None

    Example
    -------
    >>> asyncio.run(main_async())
    # Executes full pipeline with parallel operations for improved performance
    """
    ensure_directories()

    print("=" * 70)
    print("Starting Async Daily Insights Pipeline")
    print("=" * 70)

    # Stage 1: Fetch data in parallel
    print("\n[Stage 1] Fetching data from APIs...")
    fetch_tasks = []
    if FETCH_LIFELOGS:
        fetch_tasks.append(fetch_and_save_lifelogs_async())
    else:
        print("⏭️  Skipping lifelog fetching (FETCH_LIFELOGS=False)")

    if FETCH_DAILY_INSIGHTS:
        fetch_tasks.append(fetch_and_save_daily_insights_async())
    else:
        print("⏭️  Skipping daily insights fetching (FETCH_DAILY_INSIGHTS=False)")

    if fetch_tasks:
        await asyncio.gather(*fetch_tasks)

    # Stage 2: Process files in parallel (independent operations)
    print("\n[Stage 2] Processing transcription files...")
    process_tasks = []

    if PROCESS_BEE_TRANSCRIPTIONS:
        process_tasks.append(process_bee_transcriptions_async())
    else:
        print("⏭️  Skipping bee transcription processing (PROCESS_BEE_TRANSCRIPTIONS=False)")

    if PROCESS_THERAPY_SESSIONS:
        process_tasks.append(process_therapy_sessions_async())
    else:
        print("⏭️  Skipping therapy session processing (PROCESS_THERAPY_SESSIONS=False)")

    if process_tasks:
        await asyncio.gather(*process_tasks)

    # Stage 3: Generate summaries in parallel (depend on daily files existing)
    print("\n[Stage 3] Generating summaries...")
    summary_tasks = []

    if CREATE_WEEKLY_SUMMARIES:
        summary_tasks.append(build_weekly_summaries_async())
    else:
        print("⏭️  Skipping weekly summaries (CREATE_WEEKLY_SUMMARIES=False)")

    if CREATE_MONTHLY_SUMMARIES:
        summary_tasks.append(build_monthly_summaries_async())
    else:
        print("⏭️  Skipping monthly summaries (CREATE_MONTHLY_SUMMARIES=False)")

    if summary_tasks:
        await asyncio.gather(*summary_tasks)

    # Display comprehensive pipeline statistics
    print("\n")
    print("=" * 70)
    display_pipeline_summary()
    print("=" * 70)


if __name__ == "__main__":
    # Use async version by default for better performance
    # To use sync version: main()
    asyncio.run(main_async())
