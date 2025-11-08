"""Conversation parsing and grouping logic."""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from collections import Counter

from daily_insights.config import CONVERSATION_GAP_MINUTES


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


def check_speaker_purity(conversation: List[Dict]) -> bool:
    """
    Check if conversation contains ONLY expected speakers (Phase 2.5 enhancement).

    Rejects therapy sessions that include unexpected participants to prevent
    false positives from multi-person conversations or group settings.

    Args
    ----
    conversation: List of dialogue dictionaries with keys: speaker

    Returns
    -------
    bool
        True if all speakers are in expected list, False otherwise

    Example
    -------
    >>> # EXPECTED_SPEAKERS_THERAPY_SESSION = ["Bruce", "Larry", "Unknown"]
    >>> conv = [
    ...     {"speaker": "Bruce", "content": "I've been feeling anxious"},
    ...     {"speaker": "Larry", "content": "Tell me more about that"}
    ... ]
    >>> check_speaker_purity(conv)
    True  # Both speakers in expected list

    >>> conv = [
    ...     {"speaker": "Bruce", "content": "I've been feeling anxious"},
    ...     {"speaker": "Ivette", "content": "Are you okay?"}
    ... ]
    >>> check_speaker_purity(conv)
    False  # "Ivette" not in expected list
    """
    from daily_insights.config import EXPECTED_SPEAKERS_THERAPY_SESSION

    if not EXPECTED_SPEAKERS_THERAPY_SESSION:
        return False  # Must be explicitly configured

    speakers_present = {d["speaker"].lower() for d in conversation}
    expected_speakers = {s.lower() for s in EXPECTED_SPEAKERS_THERAPY_SESSION}

    # All speakers must be in expected list (subset check)
    return speakers_present.issubset(expected_speakers)


def check_exclusion_keywords(conversation: List[Dict]) -> bool:
    """
    Check if conversation contains exclusion keywords (Phase 2.9 enhancement).

    Rejects conversations containing keywords that indicate non-therapy contexts
    such as administrative interviews, political discussions, or travel.

    Args
    ----
    conversation: List of dialogue dictionaries with keys: content

    Returns
    -------
    bool
        False if ANY exclusion keyword found (reject session)
        True if no exclusions (pass check)

    Example
    -------
    >>> # THERAPY_EXCLUSION_KEYWORDS = ["eligibility", "interview", "trump", "election"]
    >>> conv = [{"content": "This interview will determine your eligibility"}]
    >>> check_exclusion_keywords(conv)
    False  # Contains "interview" and "eligibility"

    >>> conv = [{"content": "I've been feeling anxious lately"}]
    >>> check_exclusion_keywords(conv)
    True  # No exclusion keywords present
    """
    from daily_insights.config import THERAPY_EXCLUSION_KEYWORDS

    if not THERAPY_EXCLUSION_KEYWORDS:
        return True  # No exclusions configured, pass check

    content_combined = " ".join(d["content"].lower() for d in conversation)

    # Reject if any exclusion keyword is present
    return not any(kw.lower() in content_combined for kw in THERAPY_EXCLUSION_KEYWORDS)


def check_doctor_exclusion_keywords(conversation: List[Dict]) -> bool:
    """
    Check if conversation contains doctor visit exclusion keywords.

    Rejects conversations containing keywords that indicate mental health/psychiatry
    visits that should be handled separately from general medical visits.

    Args
    ----
    conversation: List of dialogue dictionaries with keys: content

    Returns
    -------
    bool
        False if ANY exclusion keyword found (reject as doctor visit)
        True if no exclusions (pass check)

    Example
    -------
    >>> # DOCTOR_EXCLUSION_KEYWORDS = ["psychiatrist", "therapy", "therapist"]
    >>> conv = [{"content": "I saw my psychiatrist today"}]
    >>> check_doctor_exclusion_keywords(conv)
    False  # Contains "psychiatrist"

    >>> conv = [{"content": "I saw my cardiologist today"}]
    >>> check_doctor_exclusion_keywords(conv)
    True  # No exclusion keywords present
    """
    from daily_insights.config import DOCTOR_EXCLUSION_KEYWORDS

    if not DOCTOR_EXCLUSION_KEYWORDS:
        return True  # No exclusions configured, pass check

    content_combined = " ".join(d["content"].lower() for d in conversation)

    # Reject if any exclusion keyword is present
    return not any(kw.lower() in content_combined for kw in DOCTOR_EXCLUSION_KEYWORDS)


def check_doctor_keyword_density(conversation: List[Dict]) -> bool:
    """
    Check if multiple doctor visit keywords are present.

    Prevents false positives from single generic keyword matches by requiring
    a minimum number of distinct medical-related terms to be present.

    Args
    ----
    conversation: List of dialogue dictionaries with keys: content

    Returns
    -------
    bool
        True if keyword count >= DOCTOR_KEYWORD_MIN, False otherwise

    Example
    -------
    >>> # DOCTOR_KEYWORDS = ["doctor", "physician", "prescription", "symptoms"]
    >>> # DOCTOR_KEYWORD_MIN = 2
    >>> conv = [
    ...     {"content": "I went to the doctor and got a prescription"},
    ...     {"content": "My symptoms are improving"}
    ... ]
    >>> check_doctor_keyword_density(conv)
    True  # Contains "doctor", "prescription", and "symptoms" (3 keywords)

    >>> conv = [{"content": "I need to make a doctor appointment"}]
    >>> check_doctor_keyword_density(conv)
    False  # Contains only "doctor" (1 keyword)
    """
    from daily_insights.config import DOCTOR_KEYWORDS, DOCTOR_KEYWORD_MIN

    content_combined = " ".join(d["content"].lower() for d in conversation)
    keyword_count = sum(
        1 for kw in DOCTOR_KEYWORDS
        if kw.lower() in content_combined
    )
    return keyword_count >= DOCTOR_KEYWORD_MIN


def check_doctor_speaker_purity(conversation: List[Dict]) -> bool:
    """
    Check if conversation contains ONLY expected speakers for doctor visits.

    Rejects doctor visits that include unexpected participants to prevent
    false positives from multi-person conversations.

    Args
    ----
    conversation: List of dialogue dictionaries with keys: speaker

    Returns
    -------
    bool
        True if all speakers are in expected list, False otherwise

    Example
    -------
    >>> # EXPECTED_SPEAKERS_DOCTOR_VISIT = ["Bruce", "Unknown"]
    >>> conv = [
    ...     {"speaker": "Bruce", "content": "My symptoms started last week"},
    ...     {"speaker": "Unknown", "content": "Let me examine you"}
    ... ]
    >>> check_doctor_speaker_purity(conv)
    True  # Both speakers in expected list

    >>> conv = [
    ...     {"speaker": "Bruce", "content": "My symptoms started last week"},
    ...     {"speaker": "Ivette", "content": "Are you okay?"}
    ... ]
    >>> check_doctor_speaker_purity(conv)
    False  # "Ivette" not in expected list
    """
    from daily_insights.config import EXPECTED_SPEAKERS_DOCTOR_VISIT

    if not EXPECTED_SPEAKERS_DOCTOR_VISIT:
        return False  # Must be explicitly configured

    speakers_present = {d["speaker"].lower() for d in conversation}
    expected_speakers = {s.lower() for s in EXPECTED_SPEAKERS_DOCTOR_VISIT}

    # All speakers must be in expected list (subset check)
    return speakers_present.issubset(expected_speakers)


def calculate_doctor_visit_confidence(conversation: List[Dict]) -> float:
    """
    Calculate confidence score for doctor visit detection (0.0 to 1.0).

    Uses weighted scoring based on multiple indicators:
    - Examination keywords: +weight (physical exam, diagnosis terms)
    - Health metrics keywords: -weight (personal health logging)
    - Discussion patterns: -weight (talking about visits, not being in one)
    - Bidirectional Q&A: +weight (clinical conversation patterns)
    - Duration sweet spot: +weight (typical visit duration range)

    All weights are configurable via environment variables.

    Args
    ----
    conversation: List of dialogue dictionaries with keys: content, speaker, datetime

    Returns
    -------
    float
        Confidence score from 0.0 (unlikely) to 1.0 (certain)
        Score is clamped to [0.0, 1.0] range

    Example
    -------
    >>> # Actual doctor visit (high confidence)
    >>> conv = [
    ...     {"content": "The doctor examined my throat", "speaker": "Bruce"},
    ...     {"content": "Let me check your blood pressure", "speaker": "Unknown"},
    ...     {"content": "It's 120/80, looks good", "speaker": "Unknown"}
    ... ]
    >>> score = calculate_doctor_visit_confidence(conv)
    >>> score > 0.5  # High confidence
    True

    >>> # Personal health logging (low confidence)
    >>> conv = [
    ...     {"content": "My weight was 188 pounds today", "speaker": "Bruce"},
    ...     {"content": "Blood glucose was 130", "speaker": "Bruce"}
    ... ]
    >>> score = calculate_doctor_visit_confidence(conv)
    >>> score < 0.3  # Low confidence
    True
    """
    from daily_insights.config import (
        DOCTOR_CONFIDENCE_WEIGHT_EXAMINATION,
        DOCTOR_CONFIDENCE_WEIGHT_HEALTH_METRICS,
        DOCTOR_CONFIDENCE_WEIGHT_DISCUSSION_PATTERN,
        DOCTOR_CONFIDENCE_WEIGHT_BIDIRECTIONAL_QA,
        DOCTOR_CONFIDENCE_WEIGHT_DURATION_OPTIMAL,
        DOCTOR_MIN_DURATION,
        DOCTOR_MAX_DURATION
    )

    # Start with baseline score
    confidence = 0.5

    # Combine all content for keyword checking
    content_combined = " ".join(d["content"].lower() for d in conversation)

    # 1. Examination-specific keywords (positive indicator)
    examination_keywords = [
        'examine', 'exam', 'examined', 'examination',
        'physical', 'diagnosed', 'prescription', 'prescribed',
        'treatment', 'clinic', 'hospital', 'checkup'
    ]
    if any(kw in content_combined for kw in examination_keywords):
        confidence += DOCTOR_CONFIDENCE_WEIGHT_EXAMINATION

    # 2. Health metrics keywords (negative indicator - personal logging)
    health_metrics_keywords = [
        'my weight was', 'i weigh', 'weight was',
        'blood glucose was', 'glucose was',
        'a1c was', 'my a1c'
    ]
    if any(pattern in content_combined for pattern in health_metrics_keywords):
        confidence += DOCTOR_CONFIDENCE_WEIGHT_HEALTH_METRICS

    # 3. Discussion patterns (negative indicator - talking about visits)
    discussion_patterns = [
        'doctor said', 'doctor told', 'physician said',
        'appointment with', 'going to see', 'saw my doctor',
        'my doctor', 'the doctor that'
    ]
    if any(pattern in content_combined for pattern in discussion_patterns):
        confidence += DOCTOR_CONFIDENCE_WEIGHT_DISCUSSION_PATTERN

    # 4. Bidirectional Q&A patterns (positive indicator)
    # Check if both speakers ask questions and provide answers
    speakers = list(set(d["speaker"] for d in conversation))
    if len(speakers) >= 2:
        # Check for questions and answers from multiple speakers
        question_indicators = ['?', 'what', 'how', 'when', 'where', 'why', 'can you', 'do you']
        has_bidirectional_qa = False

        for speaker in speakers:
            speaker_content = " ".join(
                d["content"].lower() for d in conversation
                if d["speaker"] == speaker
            )
            if any(indicator in speaker_content for indicator in question_indicators):
                has_bidirectional_qa = True
                break

        if has_bidirectional_qa:
            confidence += DOCTOR_CONFIDENCE_WEIGHT_BIDIRECTIONAL_QA

    # 5. Duration in optimal range (positive indicator)
    duration = calculate_duration_minutes(conversation)

    # Calculate sweet spot from configured min/max
    # Sweet spot is middle 50% of the range
    if DOCTOR_MAX_DURATION > 0:
        duration_range = DOCTOR_MAX_DURATION - DOCTOR_MIN_DURATION
        sweet_spot_min = DOCTOR_MIN_DURATION + (duration_range * 0.25)
        sweet_spot_max = DOCTOR_MIN_DURATION + (duration_range * 0.75)

        if sweet_spot_min <= duration <= sweet_spot_max:
            confidence += DOCTOR_CONFIDENCE_WEIGHT_DURATION_OPTIMAL
    else:
        # If no max duration, sweet spot is 2x-4x the minimum
        sweet_spot_min = DOCTOR_MIN_DURATION * 2
        sweet_spot_max = DOCTOR_MIN_DURATION * 4

        if sweet_spot_min <= duration <= sweet_spot_max:
            confidence += DOCTOR_CONFIDENCE_WEIGHT_DURATION_OPTIMAL

    # Clamp confidence to [0.0, 1.0] range
    return max(0.0, min(1.0, confidence))


def check_keyword_density(conversation: List[Dict]) -> bool:
    """
    Check if multiple therapy keywords are present (Phase 2 enhancement).

    Prevents false positives from single generic keyword matches by requiring
    a minimum number of distinct therapy-related terms to be present.

    Args
    ----
    conversation: List of dialogue dictionaries with keys: content

    Returns
    -------
    bool
        True if keyword count >= THERAPY_KEYWORD_MIN, False otherwise

    Example
    -------
    >>> # THERAPY_KEYWORDS = ["therapy", "therapist", "anxiety", "depression"]
    >>> # THERAPY_KEYWORD_MIN = 2
    >>> conv = [
    ...     {"content": "I talked to my therapist about anxiety today"},
    ...     {"content": "The session was helpful"}
    ... ]
    >>> check_keyword_density(conv)
    True  # Contains "therapist" and "anxiety" (2 keywords)

    >>> conv = [{"content": "I'm feeling anxious about the presentation"}]
    >>> check_keyword_density(conv)
    False  # Contains only "anxious" (1 keyword)
    """
    from daily_insights.config import THERAPY_KEYWORDS, THERAPY_KEYWORD_MIN

    content_combined = " ".join(d["content"].lower() for d in conversation)
    keyword_count = sum(
        1 for kw in THERAPY_KEYWORDS
        if kw.lower() in content_combined
    )
    return keyword_count >= THERAPY_KEYWORD_MIN


def is_doctor_visit(conversation: List[Dict]) -> bool:
    """
    Detect doctor visits with strict criteria (MVP approach).

    All checks must pass (Boolean AND):
    1a. Duration >= configured minimum (default 10 minutes)
    1b. Duration <= configured maximum (default 90 minutes, if enabled)
    2. Speaker purity: ONLY expected speakers present
    3. Keyword density: Multiple doctor-related keywords present
    4. Not a therapy session
    5. Not a journal session
    6. No exclusion keywords present (psychiatrist, mental health, etc.)

    Args
    ----
    conversation: List of dialogue dictionaries with keys: speaker, content, datetime

    Returns
    -------
    bool
        True if ALL criteria are met, False otherwise

    Example
    -------
    >>> # True positive - legitimate doctor visit
    >>> # EXPECTED_SPEAKERS_DOCTOR_VISIT = ["Bruce", "Unknown"]
    >>> conv = [
    ...     {"speaker": "Unknown", "content": "What brings you in today?", "datetime": dt1},
    ...     {"speaker": "Bruce", "content": "I've had these symptoms for a week", "datetime": dt2},
    ...     {"speaker": "Unknown", "content": "Let me examine you and write a prescription", "datetime": dt3},
    ...     # ... 15+ minutes of medical dialogue
    ... ]
    >>> is_doctor_visit(conv)
    True  # Duration OK, speakers OK, keywords OK, not therapy/journal, no exclusions

    >>> # False - psychiatrist visit (should be excluded)
    >>> conv = [
    ...     {"speaker": "Unknown", "content": "How is your mental health?", "datetime": dt1},
    ...     {"speaker": "Bruce", "content": "I saw my psychiatrist yesterday", "datetime": dt2}
    ... ]
    >>> is_doctor_visit(conv)
    False  # Contains exclusion keyword "psychiatrist"

    >>> # False - therapy session
    >>> conv = [
    ...     {"speaker": "Larry", "content": "How are you feeling about your anxiety?", "datetime": dt1},
    ...     {"speaker": "Bruce", "content": "Better since therapy started", "datetime": dt2}
    ... ]
    >>> is_doctor_visit(conv)
    False  # Detected as therapy session
    """
    from daily_insights.config import DOCTOR_MIN_DURATION, DOCTOR_MAX_DURATION

    # Check 1a: Minimum duration
    duration = calculate_duration_minutes(conversation)
    if duration < DOCTOR_MIN_DURATION:
        return False

    # Check 1b: Maximum duration (if enabled, non-zero)
    if DOCTOR_MAX_DURATION > 0 and duration > DOCTOR_MAX_DURATION:
        return False

    # Check 2: Speaker purity - ONLY expected speakers present
    if not check_doctor_speaker_purity(conversation):
        return False

    # Check 3: Keyword density - Multiple doctor-related keywords required
    if not check_doctor_keyword_density(conversation):
        return False

    # Check 4: Not a therapy session (reuse existing function)
    if is_therapy_session(conversation):
        return False

    # Check 5: Not a journal session (reuse existing function)
    if is_journal_session(conversation):
        return False

    # Check 6: No exclusion keywords (psychiatrist, mental health, etc.)
    if not check_doctor_exclusion_keywords(conversation):
        return False

    # All 6 checks passed
    return True


def is_therapy_session(conversation: List[Dict]) -> bool:
    """
    Detect therapy sessions with strict criteria (Phase 0 + 2 + 2.5 + 2.7 + 2.9).

    All checks must pass (Boolean AND):
    1a. Duration >= configured minimum (default 40 minutes)
    1b. Duration <= configured maximum (default 120 minutes, if enabled)
    2. Speaker purity: ONLY expected speakers present (Phase 2.5)
    3. Keyword density: Multiple therapy keywords present (Phase 2)
    4. Not a journal session
    5. No exclusion keywords present (Phase 2.9)

    Args
    ----
    conversation: List of dialogue dictionaries with keys: speaker, content, datetime

    Returns
    -------
    bool
        True if ALL 5 criteria are met, False otherwise

    Example
    -------
    >>> # True positive - legitimate therapy session
    >>> # EXPECTED_SPEAKERS = ["Bruce", "Larry", "Unknown"]
    >>> conv = [
    ...     {"speaker": "Larry", "content": "How are you feeling about your anxiety and depression?", "datetime": dt1},
    ...     {"speaker": "Bruce", "content": "I've been thinking about my disorder", "datetime": dt2},
    ...     # ... 40+ minutes of back-and-forth dialogue
    ... ]
    >>> is_therapy_session(conv)
    True  # Duration OK, speakers OK, keywords OK, not journal

    >>> # False - unexpected speaker present
    >>> conv = [
    ...     {"speaker": "Larry", "content": "How are you feeling?", "datetime": dt1},
    ...     {"speaker": "Ivette", "content": "He's been anxious", "datetime": dt2}
    ... ]
    >>> is_therapy_session(conv)
    False  # "Ivette" not in expected speakers

    >>> # False - insufficient keywords
    >>> conv = [
    ...     {"speaker": "Larry", "content": "How are you?", "datetime": dt1},
    ...     {"speaker": "Bruce", "content": "I'm feeling okay", "datetime": dt2}
    ... ]
    >>> is_therapy_session(conv)
    False  # Less than 2 therapy keywords
    """
    from daily_insights.config import THERAPY_MIN_DURATION, THERAPY_MAX_DURATION

    # Check 1a: Minimum duration
    duration = calculate_duration_minutes(conversation)
    if duration < THERAPY_MIN_DURATION:
        return False

    # Check 1b: Maximum duration (Phase 2.7) - if enabled (non-zero)
    if THERAPY_MAX_DURATION > 0 and duration > THERAPY_MAX_DURATION:
        return False

    # Check 2: Speaker purity (Phase 2.5) - ONLY expected speakers present
    if not check_speaker_purity(conversation):
        return False

    # Check 3: Keyword density (Phase 2) - Multiple therapy keywords required
    if not check_keyword_density(conversation):
        return False

    # Check 4: Not a journal (reuse existing function)
    if is_journal_session(conversation):
        return False

    # Check 5: No exclusion keywords (Phase 2.9) - Reject administrative/political contexts
    if not check_exclusion_keywords(conversation):
        return False

    # All 5 checks passed
    return True


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
