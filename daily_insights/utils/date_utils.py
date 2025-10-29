"""Date and time utilities for the daily insights system."""

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from dateutil import parser


def parse_iso_date(date_string: str) -> datetime:
    """
    Parse an ISO format date string to datetime object.

    Args
    ----
    date_string: ISO format date string

    Returns
    -------
    Parsed datetime object

    Raises
    ------
    ValueError: If date string cannot be parsed

    Example
    -------
    >>> dt = parse_iso_date("2025-10-28T14:30:00Z")
    >>> print(dt.year)
    2025
    """
    return parser.parse(date_string)


def format_date(dt: datetime, fmt: str = "%Y-%m-%d") -> str:
    """
    Format a datetime object as a string.

    Args
    ----
    dt: Datetime object to format
    fmt: Format string (default: YYYY-MM-DD)

    Returns
    -------
    Formatted date string

    Example
    -------
    >>> from datetime import datetime
    >>> dt = datetime(2025, 10, 28)
    >>> format_date(dt)
    '2025-10-28'
    """
    return dt.strftime(fmt)


def parse_week_filename(filename: str) -> Tuple[str, str]:
    """
    Extract start and end dates from weekly filename.

    Args
    ----
    filename: e.g., "2025-09-03_to_2025-09-10-weekly.md"

    Returns
    -------
    Tuple of (start_date, end_date) as strings: ("2025-09-03", "2025-09-10")

    Raises
    ------
    ValueError: If filename format is invalid

    Example
    -------
    >>> parse_week_filename("2025-09-03_to_2025-09-10-weekly.md")
    ('2025-09-03', '2025-09-10')
    """
    pattern = r"(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})-weekly\.md"
    match = re.match(pattern, filename)
    if not match:
        raise ValueError(f"Invalid weekly filename format: {filename}")
    return match.group(1), match.group(2)


def get_month_from_date(date_str: str) -> str:
    """
    Extract YYYY-MM from date string.

    Args
    ----
    date_str: Date in YYYY-MM-DD format

    Returns
    -------
    Month string in YYYY-MM format

    Example
    -------
    >>> get_month_from_date("2025-09-15")
    '2025-09'
    """
    return date_str[:7]  # Extract YYYY-MM from YYYY-MM-DD


def group_weeks_by_month(weekly_files: List[Path]) -> Dict[str, List[Path]]:
    """
    Group weekly summary files by their calendar month using start_date.

    Weeks that span two months are assigned to the month of their start_date.

    Args
    ----
    weekly_files: List of Path objects for weekly summaries

    Returns
    -------
    Dict mapping "YYYY-MM" to list of weekly file paths in that month

    Example
    -------
    >>> files = [Path("2025-09-03_to_2025-09-10-weekly.md")]
    >>> group_weeks_by_month(files)
    {'2025-09': [Path('2025-09-03_to_2025-09-10-weekly.md')]}
    """
    months: Dict[str, List[Path]] = defaultdict(list)

    for file_path in weekly_files:
        try:
            start_date, _ = parse_week_filename(file_path.name)
            month = get_month_from_date(start_date)
            months[month].append(file_path)
        except ValueError as e:
            print(f"Warning: Skipping invalid filename {file_path.name}: {e}")
            continue

    return dict(months)
