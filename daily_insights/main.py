"""Main entry point for the daily insights system."""

from daily_insights.config import ensure_directories
from daily_insights.services.lifelog_service import fetch_and_save_lifelogs
from daily_insights.services.insights_service import (
    fetch_and_save_daily_insights,
    build_weekly_summaries
)
from daily_insights.services.monthly_service import build_monthly_summaries
from daily_insights.services.therapy_service import process_therapy_sessions


def main() -> None:
    """
    Run the complete daily insights pipeline.

    Returns
    -------
    None

    Example
    -------
    >>> main()
    # Executes full pipeline: lifelogs, insights, weekly/monthly summaries, therapy
    """
    ensure_directories()

    fetch_and_save_lifelogs()

    fetch_and_save_daily_insights()

    build_weekly_summaries()

    build_monthly_summaries()

    process_therapy_sessions()


if __name__ == "__main__":
    main()
