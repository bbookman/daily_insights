"""Therapy session detection and scoring logic."""

from pathlib import Path
from typing import Dict, List, Tuple

from daily_insights.config import (
    THERAPY_KEYWORDS,
    SCORE_DURATION_MATCH,
    SCORE_AFTERNOON,
    SCORE_KEYWORD,
    SCORE_SPEAKER_NAMES,
    SCORE_BACK_AND_FORTH,
    PENALTY_TOO_MANY_SPEAKERS,
    PENALTY_TOO_LONG,
    PENALTY_TOO_SHORT,
    PENALTY_TOO_MANY_MESSAGES,
    PENALTY_JOURNAL,
    PENALTY_NON_THERAPY,
    CONFIDENCE_THRESHOLD,
    MAX_DURATION,
    MIN_DURATION,
    MAX_SPEAKERS
)
from daily_insights.models.conversation_parser import (
    parse_lifelog_dialogue,
    group_into_conversations,
    calculate_duration_minutes,
    is_journal_session,
    is_non_therapy_session,
    get_speaker_count,
    get_message_count
)


def score_conversation(conversation: List[Dict]) -> Tuple[int, Dict]:
    """
    Score a conversation for likelihood of being a therapy session.

    Args
    ----
    conversation: List of dialogue dictionaries

    Returns
    -------
    Tuple of (score, breakdown_dict)

    Example
    -------
    >>> conversation = [{"speaker": "Larry", "datetime": dt, ...}]
    >>> score, breakdown = score_conversation(conversation)
    >>> print(score)
    85
    """
    score = 0
    breakdown = {}

    duration = calculate_duration_minutes(conversation)
    if 45 <= duration <= 75:
        score += SCORE_DURATION_MATCH
        breakdown["duration"] = SCORE_DURATION_MATCH
    else:
        breakdown["duration"] = 0

    start_hour = conversation[0]["datetime"].hour
    if 12 <= start_hour < 18:
        score += SCORE_AFTERNOON
        breakdown["afternoon"] = SCORE_AFTERNOON
    else:
        breakdown["afternoon"] = 0

    content_combined = " ".join(d["content"].lower() for d in conversation)
    keyword_count = sum(
        1 for kw in THERAPY_KEYWORDS if kw.lower() in content_combined
    )
    keyword_score = min(keyword_count * SCORE_KEYWORD, 50)
    score += keyword_score
    breakdown["keywords"] = keyword_score
    breakdown["keyword_count"] = keyword_count

    has_larry_as_speaker = any(
        d["speaker"].lower() == "larry" for d in conversation
    )

    if has_larry_as_speaker:
        score += SCORE_SPEAKER_NAMES
        breakdown["speaker_names"] = SCORE_SPEAKER_NAMES
    else:
        breakdown["speaker_names"] = 0

    speakers = [d["speaker"] for d in conversation]
    if len(speakers) >= 10:
        speaker_changes = sum(
            1 for i in range(1, len(speakers))
            if speakers[i] != speakers[i-1]
        )
        if speaker_changes >= 5:
            score += SCORE_BACK_AND_FORTH
            breakdown["back_and_forth"] = SCORE_BACK_AND_FORTH
        else:
            breakdown["back_and_forth"] = 0
    else:
        breakdown["back_and_forth"] = 0

    speaker_count = get_speaker_count(conversation)
    if speaker_count > MAX_SPEAKERS:
        score += PENALTY_TOO_MANY_SPEAKERS
        breakdown["penalty_speakers"] = PENALTY_TOO_MANY_SPEAKERS
    else:
        breakdown["penalty_speakers"] = 0
    breakdown["speaker_count"] = speaker_count

    if duration > 90:
        score += PENALTY_TOO_LONG
        breakdown["penalty_too_long"] = PENALTY_TOO_LONG
    else:
        breakdown["penalty_too_long"] = 0

    if duration < 30:
        score += PENALTY_TOO_SHORT
        breakdown["penalty_too_short"] = PENALTY_TOO_SHORT
    else:
        breakdown["penalty_too_short"] = 0

    message_count = get_message_count(conversation)
    if message_count > MAX_SPEAKERS:
        score += PENALTY_TOO_MANY_MESSAGES
        breakdown["penalty_messages"] = PENALTY_TOO_MANY_MESSAGES
    else:
        breakdown["penalty_messages"] = 0
    breakdown["message_count"] = message_count

    if is_journal_session(conversation):
        score += PENALTY_JOURNAL
        breakdown["penalty_journal"] = PENALTY_JOURNAL
        breakdown["is_journal"] = True
    else:
        breakdown["penalty_journal"] = 0
        breakdown["is_journal"] = False

    if is_non_therapy_session(conversation):
        score += PENALTY_NON_THERAPY
        breakdown["penalty_non_therapy"] = PENALTY_NON_THERAPY
        breakdown["is_non_therapy"] = True
    else:
        breakdown["penalty_non_therapy"] = 0
        breakdown["is_non_therapy"] = False

    breakdown["total"] = score
    breakdown["duration_minutes"] = duration

    return score, breakdown


def detect_therapy_sessions(
    filepath: Path,
    verbose: bool = False
) -> List[Dict]:
    """
    Detect therapy sessions in a lifelog file.

    Args
    ----
    filepath: Path to the lifelog markdown file
    verbose: Whether to print detailed detection information

    Returns
    -------
    List of detected sessions with metadata

    Example
    -------
    >>> from pathlib import Path
    >>> sessions = detect_therapy_sessions(Path("lifelogs/2025-10-28.md"))
    >>> print(len(sessions))
    1
    """
    if verbose:
        print(f"\nAnalyzing: {filepath.name}")
        print("=" * 60)

    dialogues = parse_lifelog_dialogue(filepath)
    if verbose:
        print(f"Parsed {len(dialogues)} dialogue lines")

    conversations = group_into_conversations(dialogues)
    if verbose:
        print(f"Grouped into {len(conversations)} conversation segments")
        print()

    detected_sessions = []

    for i, conversation in enumerate(conversations, 1):
        start_time = conversation[0]["time_str"]
        end_time = conversation[-1]["time_str"]

        duration = calculate_duration_minutes(conversation)

        if duration > MAX_DURATION:
            if verbose:
                print(
                    f"Conversation #{i}: EXCLUDED "
                    f"(duration {duration:.1f} min > {MAX_DURATION} min)"
                )
            continue

        if duration < MIN_DURATION:
            if verbose:
                print(
                    f"Conversation #{i}: EXCLUDED "
                    f"(duration {duration:.1f} min < {MIN_DURATION} min)"
                )
            continue

        score, breakdown = score_conversation(conversation)

        if score >= CONFIDENCE_THRESHOLD:
            if verbose:
                print(f"Conversation #{i}: DETECTED AS THERAPY SESSION")
                print(f"  Time: {start_time} - {end_time}")
                print(f"  Duration: {duration:.1f} minutes")
                print(f"  Score: {score}")

            detected_sessions.append({
                "start_time": start_time,
                "end_time": end_time,
                "duration_minutes": duration,
                "score": score,
                "breakdown": breakdown,
                "conversation": conversation
            })

    return detected_sessions
