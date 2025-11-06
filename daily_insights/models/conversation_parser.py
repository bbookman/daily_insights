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
    Check if conversation is a journal session with strict validation.

    NEW LOGIC (v2.0): Requires ALL conditions to be met:
    1. Contains "journal" keyword (mandatory entry point)
    2. Sustained content after keyword (min messages + words)
    3. Valid speaker identity (configured speaker labels)
    4. High speaker dominance (>90% monologue)

    This replaces the previous permissive OR-logic that caused 90% false positives.

    Args
    ----
    conversation: List of dialogue dictionaries with keys: speaker, content, datetime

    Returns
    -------
    bool
        True if ALL journal criteria are met, False otherwise

    Example
    -------
    >>> # True positive - legitimate journal entry
    >>> conv = [
    ...     {"speaker": "Bruce", "content": "Journal entry for today", "datetime": dt},
    ...     {"speaker": "Bruce", "content": "I want to reflect on my week", "datetime": dt},
    ...     # ... 8 more messages totaling 150 words
    ... ]
    >>> is_journal_session(conv)
    True

    >>> # False positive (old logic would flag) - brief utterance
    >>> conv = [{"speaker": "Bruce", "content": "Hmm.", "datetime": dt}]
    >>> is_journal_session(conv)
    False  # No "journal" keyword

    >>> # False positive (old logic would flag) - keyword mention in conversation
    >>> conv = [
    ...     {"speaker": "Bruce", "content": "I wanted to journal about that", "datetime": dt},
    ...     {"speaker": "Alice", "content": "That sounds good", "datetime": dt}
    ... ]
    >>> is_journal_session(conv)
    False  # Wrong speaker or insufficient content
    """
    from daily_insights.config import (
        JOURNAL_MIN_MESSAGES,
        JOURNAL_MIN_WORDS,
        JOURNAL_VALID_SPEAKERS,
        JOURNAL_END_MARKERS
    )

    # STEP 1: Mandatory keyword check
    content_combined = " ".join(d["content"].lower() for d in conversation)
    if "journal" not in content_combined:
        return False  # Hard requirement - no keyword, no journal

    # STEP 2: Find journal start position (first occurrence of "journal")
    journal_start_index = 0
    for i, msg in enumerate(conversation):
        if "journal" in msg["content"].lower():
            journal_start_index = i
            break

    # STEP 3: Extract and validate sustained content
    journal_content = conversation[journal_start_index:]

    if len(journal_content) < JOURNAL_MIN_MESSAGES:
        return False  # Insufficient consecutive messages

    total_words = count_words(journal_content)
    if total_words < JOURNAL_MIN_WORDS:
        return False  # Content too brief

    # STEP 4: Validate speaker identity
    primary_speaker = get_primary_speaker(journal_content)
    if primary_speaker not in JOURNAL_VALID_SPEAKERS:
        return False  # Wrong speaker

    speaker_counts = Counter(d["speaker"] for d in journal_content)
    speaker_ratio = speaker_counts[primary_speaker] / len(journal_content)
    if speaker_ratio < 0.90:  # Very high threshold (90%)
        return False  # Not clearly a monologue

    # STEP 5: Optional end marker detection (for logging/confidence)
    if JOURNAL_END_MARKERS:
        has_end_marker = detect_end_marker(conversation, JOURNAL_END_MARKERS)
        # Could log this for debugging/confidence assessment
        # Currently not used to block detection

    # STEP 6: All checks passed
    return True


def is_therapy_session(conversation: List[Dict]) -> bool:
    """
    MVP: Detect therapy sessions with minimal criteria.

    Phase 0 implementation with only 3 checks:
    1. Duration >= configured minimum (default 30 minutes)
    2. Therapist name OR therapy keywords present
    3. Not a journal session (reuse existing function)

    Args
    ----
    conversation: List of dialogue dictionaries with keys: speaker, content, datetime

    Returns
    -------
    bool
        True if all MVP therapy criteria are met, False otherwise

    Example
    -------
    >>> # True positive - legitimate therapy session
    >>> conv = [
    ...     {"speaker": "Larry", "content": "How are you feeling today?", "datetime": dt1},
    ...     {"speaker": "Bruce", "content": "I've been thinking about my anxiety", "datetime": dt2},
    ...     # ... 40+ minutes of back-and-forth dialogue
    ... ]
    >>> is_therapy_session(conv)
    True

    >>> # False - too short
    >>> conv = [{"speaker": "Larry", "content": "Quick check-in", "datetime": dt}]
    >>> is_therapy_session(conv)
    False

    >>> # False - journal entry (excluded)
    >>> conv = [{"speaker": "Bruce", "content": "Journal: Today I talked to my therapist", "datetime": dt}]
    >>> is_therapy_session(conv)
    False
    """
    from daily_insights.config import (
        THERAPIST_NAMES,
        THERAPY_KEYWORDS,
        THERAPY_MIN_DURATION
    )

    # Check 1: Minimum duration
    duration = calculate_duration_minutes(conversation)
    if duration < THERAPY_MIN_DURATION:
        return False

    # Check 2: Therapist indicator (name OR keyword)
    speakers = {d["speaker"].lower() for d in conversation}
    has_therapist_name = any(name.lower() in speakers for name in THERAPIST_NAMES)

    if not has_therapist_name:
        content = " ".join(d["content"].lower() for d in conversation)
        has_keyword = any(kw.lower() in content for kw in THERAPY_KEYWORDS)
        if not has_keyword:
            return False

    # Check 3: Not a journal (reuse existing function)
    if is_journal_session(conversation):
        return False

    # Passed all MVP checks
    return True


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


def get_average_message_length(conversation: List[Dict]) -> float:
    """
    Calculate average message length in conversation.

    Args
    ----
    conversation: List of dialogue dictionaries

    Returns
    -------
    Average character length of messages

    Example
    -------
    >>> conversation = [{"content": "Hello"}, {"content": "Hi there!"}]
    >>> avg = get_average_message_length(conversation)
    >>> avg
    6.5
    """
    if not conversation:
        return 0.0

    total_length = sum(len(d.get("content", "")) for d in conversation)
    return total_length / len(conversation)


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


def count_words(conversation: List[Dict]) -> int:
    """
    Count total words across all messages in conversation.

    Args
    ----
    conversation: List of dialogue dictionaries

    Returns
    -------
    int
        Total word count

    Example
    -------
    >>> conv = [{"content": "Hello world"}, {"content": "How are you"}]
    >>> count_words(conv)
    5
    """
    total = 0
    for msg in conversation:
        content = msg.get("content", "")
        words = content.split()
        total += len(words)
    return total


def get_primary_speaker(conversation: List[Dict]) -> str:
    """
    Identify the speaker who talks most in conversation.

    Args
    ----
    conversation: List of dialogue dictionaries

    Returns
    -------
    str
        Name of primary speaker

    Example
    -------
    >>> conv = [{"speaker": "A"}, {"speaker": "B"}, {"speaker": "A"}]
    >>> get_primary_speaker(conv)
    'A'
    """
    speaker_counts = Counter(d["speaker"] for d in conversation)
    if not speaker_counts:
        return ""
    primary_speaker, _ = speaker_counts.most_common(1)[0]
    return primary_speaker


def detect_end_marker(conversation: List[Dict], marker_phrases: List[str]) -> bool:
    """
    Detect if conversation ends with any configured end marker phrase.

    Uses flexible regex matching to handle natural speech variations.
    Examines the last 20% of conversation or minimum 5 messages.

    Args
    ----
    conversation: List of dialogue dictionaries
    marker_phrases: List of end marker phrases (e.g., ["end journal", "journal end"])

    Returns
    -------
    bool
        True if any marker phrase detected in conversation tail, False otherwise

    Example
    -------
    >>> conv = [
    ...     {"content": "Journal entry about my day"},
    ...     {"content": "That's all for today"},
    ...     {"content": "Okay end journal"}
    ... ]
    >>> detect_end_marker(conv, ["end journal", "journal end"])
    True

    >>> conv = [{"content": "Just some random thoughts"}]
    >>> detect_end_marker(conv, ["end journal"])
    False
    """
    import re

    # Examine last 20% of conversation or minimum 5 messages
    tail_size = max(5, int(len(conversation) * 0.2))
    tail_messages = conversation[-tail_size:]

    # Combine tail into single text
    tail_text = " ".join(msg["content"] for msg in tail_messages)
    tail_text = tail_text.lower()

    # Check each configured phrase
    for phrase in marker_phrases:
        if not phrase:
            continue

        words = phrase.lower().split()
        if not words:
            continue

        # Build bidirectional regex (phrase can appear in either order)
        # Example: "end journal" matches both:
        #   - "okay end of my journal entry"
        #   - "journal entry is at an end"
        forward_pattern = r'\b' + r'\b.*\b'.join(re.escape(w) for w in words) + r'\b'
        reverse_pattern = r'\b' + r'\b.*\b'.join(re.escape(w) for w in reversed(words)) + r'\b'

        # Check if either pattern matches
        if re.search(forward_pattern, tail_text):
            return True
        if re.search(reverse_pattern, tail_text):
            return True

    return False
