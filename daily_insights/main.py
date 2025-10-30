"""Main entry point for the daily insights system."""

import asyncio

from daily_insights.config import ensure_directories
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

    fetch_and_save_lifelogs()

    fetch_and_save_daily_insights()

    process_bee_transcriptions()

    build_weekly_summaries()

    build_monthly_summaries()

    process_therapy_sessions()

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
    await asyncio.gather(
        fetch_and_save_lifelogs_async(),
        fetch_and_save_daily_insights_async()
    )

    # Stage 2: Process files in parallel (independent operations)
    print("\n[Stage 2] Processing transcription files...")
    await asyncio.gather(
        process_bee_transcriptions_async(),
        process_therapy_sessions_async()
    )

    # Stage 3: Generate summaries in parallel (depend on daily files existing)
    print("\n[Stage 3] Generating summaries...")
    await asyncio.gather(
        build_weekly_summaries_async(),
        build_monthly_summaries_async()
    )

    # Display comprehensive pipeline statistics
    print("\n")
    print("=" * 70)
    display_pipeline_summary()
    print("=" * 70)


if __name__ == "__main__":
    # Use async version by default for better performance
    # To use sync version: main()
    asyncio.run(main_async())
