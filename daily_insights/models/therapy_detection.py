"""Therapy session detection and scoring logic."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from daily_insights.logging_config import get_logger
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
    get_message_count,
    get_average_message_length
)

logger = get_logger(__name__)


# ============================================================================
# Data Classes for Scoring
# ============================================================================

@dataclass
class ConversationMetrics:
    """Extracted metrics from conversation."""
    duration_minutes: int
    start_hour: int
    keyword_count: int
    has_larry: bool
    speaker_changes: int
    speaker_count: int
    message_count: int
    avg_message_length: float


@dataclass
class ScoreComponent:
    """Individual score component with reasoning."""
    name: str
    points: int
    reason: str


@dataclass
class ScoreBreakdown:
    """Complete score breakdown."""
    total_score: int
    components: List[ScoreComponent]
    metrics: ConversationMetrics

    def to_dict(self) -> Dict:
        """
        Convert to dictionary format for compatibility.

        Returns
        -------
        Dict
            Legacy breakdown format with all component scores

        Example
        -------
        >>> breakdown = ScoreBreakdown(85, components, metrics)
        >>> d = breakdown.to_dict()
        >>> d["total_score"]
        85
        """
        result = {"total": self.total_score}
        for comp in self.components:
            result[comp.name] = comp.points

        # Add metric information for compatibility
        result["duration_minutes"] = self.metrics.duration_minutes
        result["keyword_count"] = self.metrics.keyword_count
        result["speaker_count"] = self.metrics.speaker_count
        result["message_count"] = self.metrics.message_count
        result["is_journal"] = any(c.name == "penalty_journal" and c.points < 0 for c in self.components)
        result["is_non_therapy"] = any(c.name == "penalty_non_therapy" and c.points < 0 for c in self.components)

        return result


# ============================================================================
# Helper Functions for Scoring
# ============================================================================

def extract_conversation_metrics(conversation: List[Dict]) -> ConversationMetrics:
    """
    Extract all metrics needed for scoring.

    Parameters
    ----------
    conversation : List[Dict]
        Conversation dialogue list

    Returns
    -------
    ConversationMetrics
        Extracted metrics

    Example
    -------
    >>> metrics = extract_conversation_metrics(conversation)
    >>> metrics.duration_minutes
    55
    """
    duration = calculate_duration_minutes(conversation)
    start_hour = conversation[0]["datetime"].hour

    # Keyword analysis
    content_combined = " ".join(d["content"].lower() for d in conversation)
    keyword_count = sum(
        1 for kw in THERAPY_KEYWORDS if kw.lower() in content_combined
    )

    # Speaker analysis
    has_larry = any(d["speaker"].lower() == "larry" for d in conversation)
    speakers = [d["speaker"] for d in conversation]
    speaker_changes = sum(
        1 for i in range(1, len(speakers))
        if speakers[i] != speakers[i-1]
    ) if len(speakers) >= 2 else 0

    speaker_count = get_speaker_count(conversation)
    message_count = get_message_count(conversation)
    avg_length = get_average_message_length(conversation)

    return ConversationMetrics(
        duration_minutes=duration,
        start_hour=start_hour,
        keyword_count=keyword_count,
        has_larry=has_larry,
        speaker_changes=speaker_changes,
        speaker_count=speaker_count,
        message_count=message_count,
        avg_message_length=avg_length
    )


def score_duration(metrics: ConversationMetrics) -> ScoreComponent:
    """
    Score based on conversation duration.

    Parameters
    ----------
    metrics : ConversationMetrics
        Conversation metrics

    Returns
    -------
    ScoreComponent
        Duration score component

    Example
    -------
    >>> component = score_duration(metrics)
    >>> component.points
    30
    """
    if 45 <= metrics.duration_minutes <= 75:
        return ScoreComponent(
            "duration",
            SCORE_DURATION_MATCH,
            f"Duration {metrics.duration_minutes}min matches therapy session (45-75min)"
        )
    return ScoreComponent(
        "duration",
        0,
        f"Duration {metrics.duration_minutes}min outside typical range"
    )


def score_time_of_day(metrics: ConversationMetrics) -> ScoreComponent:
    """
    Score based on start time.

    Parameters
    ----------
    metrics : ConversationMetrics
        Conversation metrics

    Returns
    -------
    ScoreComponent
        Time of day score component

    Example
    -------
    >>> component = score_time_of_day(metrics)
    >>> component.points
    15
    """
    if 12 <= metrics.start_hour < 18:
        return ScoreComponent(
            "afternoon",
            SCORE_AFTERNOON,
            f"Started at {metrics.start_hour}:00 (afternoon therapy time)"
        )
    return ScoreComponent(
        "afternoon",
        0,
        f"Started at {metrics.start_hour}:00 (outside afternoon)"
    )


def score_keywords(metrics: ConversationMetrics) -> ScoreComponent:
    """
    Score based on therapy keyword matches.

    Parameters
    ----------
    metrics : ConversationMetrics
        Conversation metrics

    Returns
    -------
    ScoreComponent
        Keyword score component

    Example
    -------
    >>> component = score_keywords(metrics)
    >>> component.points
    25
    """
    keyword_score = min(metrics.keyword_count * SCORE_KEYWORD, 50)
    return ScoreComponent(
        "keywords",
        keyword_score,
        f"Found {metrics.keyword_count} therapy keywords"
    )


def score_speaker_names(metrics: ConversationMetrics) -> ScoreComponent:
    """
    Score based on presence of Larry.

    Parameters
    ----------
    metrics : ConversationMetrics
        Conversation metrics

    Returns
    -------
    ScoreComponent
        Speaker name score component

    Example
    -------
    >>> component = score_speaker_names(metrics)
    >>> component.points
    20
    """
    if metrics.has_larry:
        return ScoreComponent(
            "speaker_names",
            SCORE_SPEAKER_NAMES,
            "Larry (therapist) is a speaker"
        )
    return ScoreComponent(
        "speaker_names",
        0,
        "Larry not detected as speaker"
    )


def score_conversation_dynamics(metrics: ConversationMetrics) -> ScoreComponent:
    """
    Score based on back-and-forth conversation pattern.

    Parameters
    ----------
    metrics : ConversationMetrics
        Conversation metrics

    Returns
    -------
    ScoreComponent
        Conversation dynamics score component

    Example
    -------
    >>> component = score_conversation_dynamics(metrics)
    >>> component.points
    10
    """
    if metrics.speaker_changes >= 5:
        return ScoreComponent(
            "back_and_forth",
            SCORE_BACK_AND_FORTH,
            f"{metrics.speaker_changes} speaker changes indicates dialogue"
        )
    return ScoreComponent(
        "back_and_forth",
        0,
        f"Only {metrics.speaker_changes} speaker changes"
    )


def calculate_penalties(metrics: ConversationMetrics, conversation: List[Dict]) -> List[ScoreComponent]:
    """
    Calculate all applicable penalties.

    Parameters
    ----------
    metrics : ConversationMetrics
        Conversation metrics
    conversation : List[Dict]
        Original conversation data for journal/non-therapy checks

    Returns
    -------
    List[ScoreComponent]
        List of penalty components

    Example
    -------
    >>> penalties = calculate_penalties(metrics, conversation)
    >>> sum(p.points for p in penalties)
    -25
    """
    penalties = []

    # Too many speakers
    if metrics.speaker_count > MAX_SPEAKERS:
        penalties.append(ScoreComponent(
            "penalty_speakers",
            PENALTY_TOO_MANY_SPEAKERS,
            f"{metrics.speaker_count} speakers (max {MAX_SPEAKERS} for therapy)"
        ))

    # Duration penalties
    if metrics.duration_minutes > 90:
        penalties.append(ScoreComponent(
            "penalty_too_long",
            PENALTY_TOO_LONG,
            f"Duration {metrics.duration_minutes}min too long (>90min)"
        ))

    if metrics.duration_minutes < 30:
        penalties.append(ScoreComponent(
            "penalty_too_short",
            PENALTY_TOO_SHORT,
            f"Duration {metrics.duration_minutes}min too short (<30min)"
        ))

    # Too many messages
    if metrics.message_count > MAX_SPEAKERS:
        penalties.append(ScoreComponent(
            "penalty_messages",
            PENALTY_TOO_MANY_MESSAGES,
            f"{metrics.message_count} messages indicates fragmented conversation"
        ))

    # Journal session
    if is_journal_session(conversation):
        penalties.append(ScoreComponent(
            "penalty_journal",
            PENALTY_JOURNAL,
            "Detected as journal/monologue session"
        ))

    # Non-therapy session
    if is_non_therapy_session(conversation):
        penalties.append(ScoreComponent(
            "penalty_non_therapy",
            PENALTY_NON_THERAPY,
            "Detected as non-therapy conversation"
        ))

    return penalties


def build_score_breakdown(
    metrics: ConversationMetrics,
    positive_components: List[ScoreComponent],
    penalties: List[ScoreComponent]
) -> ScoreBreakdown:
    """
    Build complete score breakdown from components.

    Parameters
    ----------
    metrics : ConversationMetrics
        Conversation metrics
    positive_components : List[ScoreComponent]
        List of positive score components
    penalties : List[ScoreComponent]
        List of penalty components

    Returns
    -------
    ScoreBreakdown
        Complete score breakdown with total

    Example
    -------
    >>> breakdown = build_score_breakdown(metrics, positives, penalties)
    >>> breakdown.total_score
    85
    """
    all_components = positive_components + penalties
    total_score = sum(comp.points for comp in all_components)

    logger.debug(
        "Score breakdown: %d points from %d components",
        total_score,
        len(all_components)
    )

    return ScoreBreakdown(
        total_score=total_score,
        components=all_components,
        metrics=metrics
    )


def score_conversation(conversation: List[Dict]) -> Tuple[int, Dict]:
    """
    Score a conversation for likelihood of being a therapy session.

    Orchestrates the complete scoring workflow:
    1. Extract conversation metrics
    2. Calculate positive scores
    3. Calculate penalties
    4. Build complete breakdown

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
    # Step 1: Extract metrics
    metrics = extract_conversation_metrics(conversation)

    # Step 2: Calculate positive score components
    positive_components = [
        score_duration(metrics),
        score_time_of_day(metrics),
        score_keywords(metrics),
        score_speaker_names(metrics),
        score_conversation_dynamics(metrics)
    ]

    # Step 3: Calculate penalties
    penalties = calculate_penalties(metrics, conversation)

    # Step 4: Build breakdown
    breakdown_obj = build_score_breakdown(metrics, positive_components, penalties)

    # Convert to legacy format
    return breakdown_obj.total_score, breakdown_obj.to_dict()


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
