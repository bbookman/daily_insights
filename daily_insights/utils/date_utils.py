"""Date and time utilities for the daily insights system."""

from datetime import datetime
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
