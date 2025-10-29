"""Conversation parsing and grouping logic."""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from collections import Counter

from daily_insights.config import (
    CONVERSATION_GAP_MINUTES,
    NON_THERAPY_KEYWORDS
)


def parse_lifelog_dialogue(filepath: Path) -> List[Dict]:
    """
    Parse dialogue lines from a lifelog markdown file.

    Args
    ----
    filepath: Path to the lifelog markdown file

    Returns
    -------
    List of dicts with: speaker, time_str, content, datetime

    Example
    -------
    >>> from pathlib import Path
    >>> dialogues = parse_lifelog_dialogue(Path("lifelogs/2025-10-28.md"))
    >>> print(len(dialogues))
    42
    """
    dialogues = []
    pattern = re.compile(
        r"^- (.+?) \((\d+/\d+/\d+) (\d+:\d+ (?:AM|PM))\): (.+)"
    )

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                speaker = match.group(1)
                date_str = match.group(2)
                time_str = match.group(3)
                content = match.group(4)

                datetime_str = f"{date_str} {time_str}"
                try:
                    dt = datetime.strptime(datetime_str, "%m/%d/%y %I:%M %p")
                except ValueError:
                    continue

                dialogues.append({
                    "speaker": speaker,
                    "time_str": time_str,
                    "content": content,
                    "datetime": dt
                })

    return dialogues


def group_into_conversations(
    dialogues: List[Dict],
    max_gap_minutes: int = CONVERSATION_GAP_MINUTES
) -> List[List[Dict]]:
    """
    Group dialogue lines into conversations based on time gaps.

    Args
    ----
    dialogues: List of dialogue dictionaries
    max_gap_minutes: Maximum gap in minutes to consider same conversation

    Returns
    -------
    List of conversation groups (each is a list of dialogues)

    Example
    -------
    >>> dialogues = [{"datetime": dt1, ...}, {"datetime": dt2, ...}]
    >>> conversations = group_into_conversations(dialogues)
    >>> print(len(conversations))
    3
    """
    if not dialogues:
        return []

    conversations = []
    current_conversation = [dialogues[0]]

    for i in range(1, len(dialogues)):
        prev_time = dialogues[i - 1]["datetime"]
        curr_time = dialogues[i]["datetime"]
        gap_minutes = (curr_time - prev_time).total_seconds() / 60

        if gap_minutes <= max_gap_minutes:
            current_conversation.append(dialogues[i])
        else:
            conversations.append(current_conversation)
            current_conversation = [dialogues[i]]

    if current_conversation:
        conversations.append(current_conversation)

    return conversations


def calculate_duration_minutes(conversation: List[Dict]) -> float:
    """
    Calculate duration of conversation in minutes.

    Args
    ----
    conversation: List of dialogue dictionaries

    Returns
    -------
    Duration in minutes

    Example
    -------
    >>> conversation = [{"datetime": start_dt}, {"datetime": end_dt}]
    >>> duration = calculate_duration_minutes(conversation)
    >>> print(duration)
    45.5
    """
    if len(conversation) < 2:
        return 0.0
    start = conversation[0]["datetime"]
    end = conversation[-1]["datetime"]
    return (end - start).total_seconds() / 60


def is_journal_session(conversation: List[Dict]) -> bool:
    """
    Check if conversation is a journal session (monologue).

    Args
    ----
    conversation: List of dialogue dictionaries

    Returns
    -------
    True if conversation appears to be a journal session

    Example
    -------
    >>> conversation = [{"speaker": "Bruce", "content": "journal..."}]
    >>> is_journal = is_journal_session(conversation)
    >>> print(is_journal)
    True
    """
    content_combined = " ".join(d["content"].lower() for d in conversation)
    if "journal" in content_combined:
        return True

    speakers = [d["speaker"] for d in conversation]
    if not speakers:
        return False

    speaker_counts = Counter(speakers)
    max_speaker_count = max(speaker_counts.values())

    if max_speaker_count / len(speakers) > 0.8:
        return True

    return False


def is_non_therapy_session(conversation: List[Dict]) -> bool:
    """
    Check if conversation contains non-therapy indicators.

    Args
    ----
    conversation: List of dialogue dictionaries

    Returns
    -------
    True if conversation contains non-therapy keywords

    Example
    -------
    >>> conversation = [{"content": "alexa stop playing music"}]
    >>> is_non_therapy = is_non_therapy_session(conversation)
    >>> print(is_non_therapy)
    True
    """
    content_combined = " ".join(d["content"].lower() for d in conversation)

    for keyword in NON_THERAPY_KEYWORDS:
        if keyword.lower() in content_combined:
            return True

    return False


def get_speaker_count(conversation: List[Dict]) -> int:
    """
    Get number of unique speakers in conversation.

    Args
    ----
    conversation: List of dialogue dictionaries

    Returns
    -------
    Number of unique speakers

    Example
    -------
    >>> conversation = [{"speaker": "A"}, {"speaker": "B"}, {"speaker": "A"}]
    >>> count = get_speaker_count(conversation)
    >>> print(count)
    2
    """
    speakers = set(d["speaker"] for d in conversation)
    return len(speakers)


def get_message_count(conversation: List[Dict]) -> int:
    """
    Get total number of messages in conversation.

    Args
    ----
    conversation: List of dialogue dictionaries

    Returns
    -------
    Total message count

    Example
    -------
    >>> conversation = [{"content": "hi"}, {"content": "hello"}]
    >>> count = get_message_count(conversation)
    >>> print(count)
    2
    """
    return len(conversation)


def extract_transcript(conversation: List[Dict]) -> str:
    """
    Extract formatted transcript from conversation.

    Args
    ----
    conversation: List of dialogue dictionaries

    Returns
    -------
    Formatted transcript as string

    Example
    -------
    >>> conversation = [{"speaker": "A", "time_str": "2:00 PM", ...}]
    >>> transcript = extract_transcript(conversation)
    >>> print(transcript[:50])
    '- A (2:00 PM): Hello, how are you?'
    """
    lines = []
    for dialogue in conversation:
        speaker = dialogue["speaker"]
        time = dialogue["time_str"]
        content = dialogue["content"]
        lines.append(f"- {speaker} ({time}): {content}")
    return "\n".join(lines)
