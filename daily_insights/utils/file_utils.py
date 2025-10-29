"""File I/O utilities for the daily insights system."""

import os
from typing import Optional


def read_prompt_file(filepath: str) -> Optional[str]:
    """
    Read a prompt file and return its contents.

    Args
    ----
    filepath: Path to the prompt file

    Returns
    -------
    File contents as string, or None if file doesn't exist

    Example
    -------
    >>> content = read_prompt_file("prompts/weekly_prompt.txt")
    >>> print(content[:50])
    'Please summarize the following daily insights...'
    """
    if not os.path.exists(filepath):
        print(f"Prompt file missing: {filepath}")
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def write_file(filepath: str, content: str) -> None:
    """
    Write content to a file.

    Args
    ----
    filepath: Path to the file
    content: Content to write

    Returns
    -------
    None

    Example
    -------
    >>> write_file("output.txt", "Hello, world!")
    # File created with content
    """
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
