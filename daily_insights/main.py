"""Main entry point for the daily insights system."""

from daily_insights.config import ensure_directories
from daily_insights.services.lifelog_service import fetch_and_save_lifelogs
from daily_insights.services.insights_service import (
    fetch_and_save_daily_insights,
    build_weekly_summaries
)
from daily_insights.services.bee_service import process_bee_transcriptions
from daily_insights.services.monthly_service import build_monthly_summaries
from daily_insights.services.therapy_service import process_therapy_sessions
from daily_insights.utils.pipeline_stats import display_pipeline_summary


def main() -> None:
    """
    Run the complete daily insights pipeline.

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


if __name__ == "__main__":
    main()
