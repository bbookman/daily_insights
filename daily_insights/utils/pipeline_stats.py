"""Pipeline statistics collection and reporting utilities."""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from daily_insights.config import (
    LIFELOGS_DIR,
    INSIGHTS_DIR,
    WEEKLY_DIR,
    MONTHLY_DIR,
    PSYCHOLOGIST_DIR
)
from daily_insights.utils.date_utils import (
    parse_week_filename,
    get_month_from_date,
    group_weeks_by_month
)


class PipelineStatistics:
    """Collect and display comprehensive pipeline statistics."""

    def __init__(self):
        """Initialize statistics collector."""
        self.stats = {
            "lifelogs": {},
            "daily_insights": {},
            "weekly_summaries": {},
            "monthly_summaries": {},
            "therapy_sessions": {}
        }

    def collect_lifelog_stats(self) -> Dict:
        """
        Collect statistics for lifelogs.

        Returns
        -------
        Dict with lifelog statistics
        """
        lifelog_files = list(Path(LIFELOGS_DIR).glob("*.md"))

        if not lifelog_files:
            return {
                "total": 0,
                "new": 0,
                "date_range": None,
                "coverage_days": 0
            }

        # Extract dates from filenames (YYYY-MM-DD.md)
        dates = []
        for f in lifelog_files:
            try:
                date_str = f.stem
                dates.append(datetime.strptime(date_str, "%Y-%m-%d"))
            except ValueError:
                continue

        dates.sort()

        return {
            "total": len(lifelog_files),
            "new": 0,  # Tracked externally by fetch process
            "date_range": (
                dates[0].strftime("%b %d, %Y"),
                dates[-1].strftime("%b %d, %Y")
            ) if dates else None,
            "coverage_days": len(dates)
        }

    def collect_daily_insights_stats(self) -> Dict:
        """
        Collect statistics for daily insights.

        Returns
        -------
        Dict with daily insights statistics
        """
        daily_files = list(Path(INSIGHTS_DIR).glob("*.md"))
        daily_files = [f for f in daily_files if not f.stem.endswith("-weekly")]

        if not daily_files:
            return {
                "total": 0,
                "new": 0,
                "coverage_days": 0
            }

        return {
            "total": len(daily_files),
            "new": 0,  # Tracked externally by fetch process
            "coverage_days": len(daily_files)
        }

    def collect_weekly_summary_stats(self) -> Dict:
        """
        Collect statistics for weekly summaries.

        Returns
        -------
        Dict with weekly summary statistics
        """
        weekly_files = sorted(Path(WEEKLY_DIR).glob("*-weekly.md"))

        if not weekly_files:
            return {
                "total": 0,
                "new": 0,
                "complete": 0,
                "incomplete": 0,
                "latest": None
            }

        # Get the latest week
        latest_file = weekly_files[-1]
        try:
            start_date, end_date = parse_week_filename(latest_file.name)
            latest = f"{start_date} to {end_date}"
        except ValueError:
            latest = None

        return {
            "total": len(weekly_files),
            "new": 0,  # Tracked externally
            "complete": len(weekly_files),
            "incomplete": 0,  # Would need to check daily files
            "latest": latest
        }

    def collect_monthly_summary_stats(self) -> Dict:
        """
        Collect statistics for monthly summaries.

        Returns
        -------
        Dict with monthly summary statistics
        """
        monthly_files = list(Path(MONTHLY_DIR).glob("*.md"))

        # Group weekly files to determine pending months
        weekly_files = sorted(Path(WEEKLY_DIR).glob("*-weekly.md"))
        months_dict = group_weeks_by_month(weekly_files)

        complete_months = len(monthly_files)
        pending_months = []

        for month, week_files in sorted(months_dict.items()):
            monthly_file = Path(MONTHLY_DIR) / f"{month}.md"
            if not monthly_file.exists() and len(week_files) < 4:
                weeks_needed = 4 - len(week_files)
                pending_months.append((month, len(week_files), weeks_needed))

        return {
            "total": complete_months,
            "new": 0,  # Tracked externally
            "complete": complete_months,
            "pending": pending_months
        }

    def collect_therapy_session_stats(self) -> Dict:
        """
        Collect statistics for therapy sessions.

        Returns
        -------
        Dict with therapy session statistics
        """
        session_files = list(Path(PSYCHOLOGIST_DIR).glob("*-psychologist*.md"))

        # Calculate detection rate
        lifelog_count = len(list(Path(LIFELOGS_DIR).glob("*.md")))
        detection_rate = (len(session_files) / lifelog_count * 100) if lifelog_count > 0 else 0

        return {
            "total": len(session_files),
            "new": 0,  # Tracked externally
            "detection_rate": detection_rate
        }

    def collect_all_stats(self) -> Dict:
        """
        Collect statistics for all pipeline stages.

        Returns
        -------
        Dict with all pipeline statistics
        """
        return {
            "lifelogs": self.collect_lifelog_stats(),
            "daily_insights": self.collect_daily_insights_stats(),
            "weekly_summaries": self.collect_weekly_summary_stats(),
            "monthly_summaries": self.collect_monthly_summary_stats(),
            "therapy_sessions": self.collect_therapy_session_stats()
        }

    def format_summary(self, stats: Optional[Dict] = None) -> str:
        """
        Format statistics into Option C hierarchical detail format.

        Args
        ----
        stats: Statistics dict (if None, collects fresh stats)

        Returns
        -------
        Formatted statistics string
        """
        if stats is None:
            stats = self.collect_all_stats()

        lines = []
        lines.append("📊 Pipeline Execution Summary")
        lines.append("══════════════════════════════")
        lines.append("")

        # Lifelogs
        lf = stats["lifelogs"]
        lines.append("📁 LIFELOGS")
        lines.append(f"  • Total: {lf['total']} files")
        lines.append(f"  • New: {lf['new']} files")
        if lf["date_range"]:
            lines.append(f"  • Date Range: {lf['date_range'][0]} - {lf['date_range'][1]}")
            lines.append(f"  • Coverage: {lf['coverage_days']} days")
        lines.append("")

        # Daily Insights
        di = stats["daily_insights"]
        lines.append("📝 DAILY INSIGHTS")
        lines.append(f"  • Total: {di['total']} files")
        lines.append(f"  • New: {di['new']} files")
        if lf["total"] > 0:
            coverage_pct = (di["total"] / lf["total"] * 100)
            lines.append(f"  • Coverage: {di['total']}/{lf['total']} lifelogs ({coverage_pct:.1f}%)")
        lines.append("")

        # Weekly Summaries
        ws = stats["weekly_summaries"]
        lines.append("📅 WEEKLY SUMMARIES")
        lines.append(f"  • Total: {ws['total']} files")
        lines.append(f"  • New: {ws['new']} files")
        lines.append(f"  • Complete: {ws['complete']} weeks")
        if ws["incomplete"] > 0:
            lines.append(f"  • Incomplete: {ws['incomplete']} weeks (< 7 days)")
        if ws["latest"]:
            lines.append(f"  • Latest: {ws['latest']}")
        lines.append("")

        # Monthly Summaries
        ms = stats["monthly_summaries"]
        lines.append("📆 MONTHLY SUMMARIES ⭐")
        lines.append(f"  • Total: {ms['total']} files")
        lines.append(f"  • New: {ms['new']} files")
        lines.append(f"  • Complete: {ms['complete']} months")

        if ms["pending"]:
            for month, weeks_have, weeks_need in ms["pending"]:
                lines.append(f"  • Pending: {month} ({weeks_have} weeks, need {weeks_need} more)")
        lines.append("")

        # Therapy Sessions
        ts = stats["therapy_sessions"]
        lines.append("🏥 THERAPY SESSIONS")
        lines.append(f"  • Total: {ts['total']} sessions")
        lines.append(f"  • New: {ts['new']} sessions")
        if ts["detection_rate"] > 0:
            lines.append(f"  • Detection Rate: {ts['detection_rate']:.1f}% of lifelogs")
        lines.append("")

        return "\n".join(lines)

    def display_summary(self, stats: Optional[Dict] = None) -> None:
        """
        Display formatted statistics summary.

        Args
        ----
        stats: Statistics dict (if None, collects fresh stats)

        Returns
        -------
        None
        """
        print(self.format_summary(stats))


def display_pipeline_summary() -> None:
    """
    Collect and display comprehensive pipeline statistics.

    Returns
    -------
    None

    Example
    -------
    >>> display_pipeline_summary()
    # Displays formatted statistics for all pipeline stages
    """
    collector = PipelineStatistics()
    collector.display_summary()
