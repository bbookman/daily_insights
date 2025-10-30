"""File I/O utilities for the daily insights system."""

import os
from typing import Optional
import aiofiles


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


# ============================================================================
# Async File I/O Functions
# ============================================================================

async def read_prompt_file_async(filepath: str) -> Optional[str]:
    """
    Async version: Read a prompt file and return its contents.

    Args
    ----
    filepath: Path to the prompt file

    Returns
    -------
    File contents as string, or None if file doesn't exist

    Example
    -------
    >>> content = await read_prompt_file_async("prompts/weekly_prompt.txt")
    >>> print(content[:50])
    'Please summarize the following daily insights...'
    """
    if not os.path.exists(filepath):
        print(f"Prompt file missing: {filepath}")
        return None

    async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
        return await f.read()


async def write_file_async(filepath: str, content: str) -> None:
    """
    Async version: Write content to a file.

    Args
    ----
    filepath: Path to the file
    content: Content to write

    Returns
    -------
    None

    Example
    -------
    >>> await write_file_async("output.txt", "Hello, world!")
    # File created with content
    """
    async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
        await f.write(content)


async def read_file_async(filepath: str) -> str:
    """
    Read a file asynchronously and return its contents.

    Args
    ----
    filepath: Path to the file

    Returns
    -------
    File contents as string

    Raises
    ------
    FileNotFoundError: If file doesn't exist

    Example
    -------
    >>> content = await read_file_async("data/2025-10-28.md")
    >>> print(len(content))
    1500
    """
    async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
        return await f.read()


async def append_file_async(filepath: str, content: str) -> None:
    """
    Append content to a file asynchronously.

    Args
    ----
    filepath: Path to the file
    content: Content to append

    Returns
    -------
    None

    Example
    -------
    >>> await append_file_async("log.txt", "New entry\n")
    # Content appended to file
    """
    async with aiofiles.open(filepath, "a", encoding="utf-8") as f:
        await f.write(content)
