"""Main entry point for the daily insights system."""

import asyncio

from daily_insights.logging_config import setup_logging, get_logger, shutdown_logging
from daily_insights.config import (
    ensure_directories,
    FETCH_LIFELOGS,
    FETCH_DAILY_INSIGHTS,
    PROCESS_BEE_TRANSCRIPTIONS,
    PROCESS_JOURNAL_ENTRIES,
    PROCESS_THERAPY_SESSIONS,
    CREATE_WEEKLY_SUMMARIES,
    CREATE_MONTHLY_SUMMARIES,
    CREATE_THERAPY_MONTHLY_SUMMARIES,
    LABEL_SPEAKERS,
    LOG_LEVEL,
    LOG_FILE,
    LOG_TO_CONSOLE,
    LOG_TO_FILE,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT
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
from daily_insights.services.therapy_monthly_service import (
    build_therapy_monthly_summaries,
    build_therapy_monthly_summaries_async
)
from daily_insights.services.journal_service import (
    process_journal_entries,
    process_journal_entries_async
)
from daily_insights.utils.pipeline_stats import display_pipeline_summary

# Initialize logging at module level (before any logging occurs)
setup_logging(
    log_level=LOG_LEVEL,
    log_file=LOG_FILE if LOG_TO_FILE else None,
    console_output=LOG_TO_CONSOLE,
    max_bytes=LOG_MAX_BYTES,
    backup_count=LOG_BACKUP_COUNT
)

# Get logger for this module
logger = get_logger(__name__)


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
        logger.info("Skipping lifelog fetching (FETCH_LIFELOGS=False)")

    if FETCH_DAILY_INSIGHTS:
        fetch_and_save_daily_insights()
    else:
        logger.info("Skipping daily insights fetching (FETCH_DAILY_INSIGHTS=False)")

    if PROCESS_BEE_TRANSCRIPTIONS:
        process_bee_transcriptions()
    else:
        logger.info("Skipping bee transcription processing (PROCESS_BEE_TRANSCRIPTIONS=False)")

    if PROCESS_JOURNAL_ENTRIES:
        process_journal_entries()
    else:
        logger.info("Skipping journal entry processing (PROCESS_JOURNAL_ENTRIES=False)")

    if CREATE_WEEKLY_SUMMARIES:
        build_weekly_summaries()
    else:
        logger.info("Skipping weekly summaries (CREATE_WEEKLY_SUMMARIES=False)")

    if CREATE_MONTHLY_SUMMARIES:
        build_monthly_summaries()
    else:
        logger.info("Skipping monthly summaries (CREATE_MONTHLY_SUMMARIES=False)")

    if CREATE_THERAPY_MONTHLY_SUMMARIES:
        build_therapy_monthly_summaries()
    else:
        logger.info("Skipping therapy monthly summaries (CREATE_THERAPY_MONTHLY_SUMMARIES=False)")

    if PROCESS_THERAPY_SESSIONS:
        process_therapy_sessions()
    else:
        logger.info("Skipping therapy session processing (PROCESS_THERAPY_SESSIONS=False)")

    # Display comprehensive pipeline statistics
    logger.info("Pipeline execution completed")
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

    logger.info("=" * 70)
    logger.info("Starting Async Daily Insights Pipeline")
    logger.info("=" * 70)

    # Stage 1: Fetch data in parallel
    logger.info("[Stage 1] Fetching data from APIs")
    fetch_tasks = []
    if FETCH_LIFELOGS:
        fetch_tasks.append(fetch_and_save_lifelogs_async())
    else:
        logger.info("Skipping lifelog fetching (FETCH_LIFELOGS=False)")

    if FETCH_DAILY_INSIGHTS:
        fetch_tasks.append(fetch_and_save_daily_insights_async())
    else:
        logger.info("Skipping daily insights fetching (FETCH_DAILY_INSIGHTS=False)")

    if fetch_tasks:
        await asyncio.gather(*fetch_tasks)

    # Stage 2: Process files in parallel (independent operations)
    logger.info("[Stage 2] Processing transcription files")
    process_tasks = []

    if PROCESS_BEE_TRANSCRIPTIONS:
        process_tasks.append(process_bee_transcriptions_async())
    else:
        logger.info("Skipping bee transcription processing (PROCESS_BEE_TRANSCRIPTIONS=False)")

    if PROCESS_JOURNAL_ENTRIES:
        process_tasks.append(process_journal_entries_async())
    else:
        logger.info("Skipping journal entry processing (PROCESS_JOURNAL_ENTRIES=False)")

    if PROCESS_THERAPY_SESSIONS:
        process_tasks.append(process_therapy_sessions_async())
    else:
        logger.info("Skipping therapy session processing (PROCESS_THERAPY_SESSIONS=False)")

    if process_tasks:
        await asyncio.gather(*process_tasks)

    # Stage 3: Generate summaries in parallel (depend on daily files existing)
    logger.info("[Stage 3] Generating summaries")
    summary_tasks = []

    if CREATE_WEEKLY_SUMMARIES:
        summary_tasks.append(build_weekly_summaries_async())
    else:
        logger.info("Skipping weekly summaries (CREATE_WEEKLY_SUMMARIES=False)")

    if CREATE_MONTHLY_SUMMARIES:
        summary_tasks.append(build_monthly_summaries_async())
    else:
        logger.info("Skipping monthly summaries (CREATE_MONTHLY_SUMMARIES=False)")

    if CREATE_THERAPY_MONTHLY_SUMMARIES:
        summary_tasks.append(build_therapy_monthly_summaries_async())
    else:
        logger.info("Skipping therapy monthly summaries (CREATE_THERAPY_MONTHLY_SUMMARIES=False)")

    if summary_tasks:
        await asyncio.gather(*summary_tasks)

    # Display comprehensive pipeline statistics
    logger.info("=" * 70)
    display_pipeline_summary()
    logger.info("=" * 70)
    logger.info("Async pipeline completed successfully")


if __name__ == "__main__":
    # Use async version by default for better performance
    # To use sync version: main()
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user (Ctrl+C)")
    except Exception as e:
        logger.critical("Pipeline failed with unexpected error", exc_info=True)
        raise
    finally:
        # Ensure all logs are flushed to disk
        shutdown_logging()
