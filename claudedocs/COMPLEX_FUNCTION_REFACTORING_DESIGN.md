# Complex Function Refactoring Design

**Design Date**: November 2, 2025
**Target**: Break down high-complexity functions identified in code smell review
**Impact**: Improve maintainability, testability, and readability
**Status**: Design Phase - Ready for Implementation

---

## Executive Summary

### Problem Statement
The codebase contains several functions with excessive complexity that violate Single Responsibility Principle and hinder maintainability:

| Function | File | Complexity | Variables | Statements | Branches |
|----------|------|------------|-----------|------------|----------|
| `label_training_transcript()` | cli/speaker_commands.py:21 | D/29 | 45 | 112 | 29 |
| `score_conversation()` | models/therapy_detection.py:35 | C/19 | 10 | 77 | 22 |
| `fetch_new_lifelogs()` | api/limitless_client.py:60 | C/13 | 17 | 55 | 12 |
| `build_speaker_identification_prompt()` | api/speaker_llm_client.py:8 | C/17 | 8 | 60 | 15 |
| `find_speaker_in_transcripts()` | cli/speaker_commands.py:357 | C/13 | 12 | 48 | 13 |

### Design Goals
1. **Reduce Complexity**: Target max complexity of 10 (B rating)
2. **Limit Variables**: Maximum 15 local variables per function
3. **Reduce Statements**: Maximum 50 statements per function
4. **Single Responsibility**: Each function does one thing well
5. **Improve Testability**: Smaller functions easier to unit test

### Implementation Phases
- **Phase 1**: Refactor `label_training_transcript()` (Critical - D/29 complexity)
- **Phase 2**: Refactor `score_conversation()` (High - C/19 complexity)
- **Phase 3**: Refactor remaining C-rated functions
- **Total Effort**: 2-3 days

---

## Phase 1: `label_training_transcript()` Refactoring

### Current State Analysis

**Complexity Metrics**:
- Cyclomatic Complexity: D/29 (Critical)
- Local Variables: 45 (!) - far exceeds recommended 15
- Statements: 112
- Branches: 29
- Nesting Depth: 6 levels

**Responsibility Violations**:
1. File I/O (loading transcript)
2. Profile validation (checking known speakers)
3. Instance extraction and filtering
4. Example grouping logic
5. User interaction loop
6. Training data persistence
7. Example deduplication
8. Statistics tracking and reporting

### Refactored Design

#### Architecture Overview
```
label_training_transcript()  [Main orchestrator - Complexity ~8]
├─ load_transcript_file()  [File I/O]
├─ validate_speaker_profiles()  [Validation]
├─ extract_and_filter_instances()  [Data preparation]
│  ├─ extract_speaker_instances()  [Existing]
│  └─ filter_substantial_utterances()  [New]
├─ group_instances_by_speaker()  [Data organization]
├─ interactive_labeling_session()  [User interaction loop]
│  ├─ display_speaker_examples()  [Display]
│  ├─ get_user_speaker_choice()  [Input]
│  └─ create_training_examples()  [Data creation]
└─ save_training_session()  [Persistence]
   ├─ deduplicate_examples()  [Existing]
   └─ report_session_statistics()  [New]
```

#### Component Specifications

##### 1. `load_transcript_file(transcript_file: str) -> Optional[str]`
**Responsibility**: Load and validate transcript file
**Returns**: Transcript content or None if error
**Complexity**: 3 (Simple)

```python
def load_transcript_file(transcript_file: str) -> Optional[str]:
    """
    Load and validate transcript file.

    Parameters
    ----------
    transcript_file : str
        Path to transcript markdown file

    Returns
    -------
    Optional[str]
        Transcript content if successful, None otherwise

    Example
    -------
    >>> content = load_transcript_file("lifelogs/2025-03-01.md")
    >>> content is not None
    True
    """
    file_path = Path(transcript_file)

    if not file_path.exists():
        logger.error("File not found: %s", transcript_file)
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error("Error reading file: %s", transcript_file, exc_info=True)
        return None
```

**Metrics**: Variables: 2, Statements: 8, Branches: 2, Complexity: 3

---

##### 2. `validate_speaker_profiles() -> Optional[List[str]]`
**Responsibility**: Validate speaker profiles exist and return known speakers
**Returns**: List of known speaker names or None if invalid
**Complexity**: 3

```python
def validate_speaker_profiles() -> Optional[List[str]]:
    """
    Validate that speaker profiles exist and are configured.

    Returns
    -------
    Optional[List[str]]
        List of known speaker names if valid, None otherwise

    Example
    -------
    >>> speakers = validate_speaker_profiles()
    >>> isinstance(speakers, list)
    True
    """
    profiles_data = load_speaker_profiles()
    known_speakers = list(profiles_data.get("speakers", {}).keys())

    if not known_speakers:
        logger.error(
            "No speaker profiles found. Create profiles in %s",
            SPEAKER_PROFILES_FILE
        )
        return None

    return known_speakers
```

**Metrics**: Variables: 2, Statements: 6, Branches: 1, Complexity: 2

---

##### 3. `filter_substantial_utterances(instances: List[Tuple[str, str]], min_words: int = 6) -> Tuple[List[Tuple[str, str]], Dict]`
**Responsibility**: Filter utterances by word count and return statistics
**Returns**: Filtered instances and statistics dictionary
**Complexity**: 4

```python
@dataclass
class FilterStatistics:
    """Statistics from utterance filtering."""
    original_count: int
    filtered_count: int
    skipped_count: int

    def __str__(self) -> str:
        return (
            f"Found {self.original_count} instances. "
            f"Filtered to {self.filtered_count} substantial (≥{MIN_UTTERANCE_WORDS} words). "
            f"Skipped {self.skipped_count} brief utterances."
        )


def filter_substantial_utterances(
    instances: List[Tuple[str, str]],
    min_words: int = MIN_UTTERANCE_WORDS
) -> Tuple[List[Tuple[str, str]], FilterStatistics]:
    """
    Filter speaker instances to keep only substantial utterances.

    Parameters
    ----------
    instances : List[Tuple[str, str]]
        List of (speaker_label, utterance) tuples
    min_words : int, default=6
        Minimum word count for substantial utterances

    Returns
    -------
    Tuple[List[Tuple[str, str]], FilterStatistics]
        Filtered instances and statistics

    Example
    -------
    >>> instances = [("Speaker 1", "Yes"), ("Speaker 2", "I agree with that")]
    >>> filtered, stats = filter_substantial_utterances(instances, min_words=3)
    >>> len(filtered)
    1
    """
    filtered_instances = [
        (speaker_label, utterance)
        for speaker_label, utterance in instances
        if len(utterance.split()) >= min_words
    ]

    stats = FilterStatistics(
        original_count=len(instances),
        filtered_count=len(filtered_instances),
        skipped_count=len(instances) - len(filtered_instances)
    )

    return filtered_instances, stats
```

**Metrics**: Variables: 3, Statements: 8, Branches: 1, Complexity: 2

---

##### 4. `group_instances_by_speaker(instances: List[Tuple[str, str]]) -> SpeakerGroups`
**Responsibility**: Group instances by speaker label with index tracking
**Returns**: SpeakerGroups data class
**Complexity**: 4

```python
@dataclass
class SpeakerGroups:
    """Grouped speaker instances with metadata."""
    grouped: Dict[str, List[str]]  # speaker_label -> utterances
    indices: Dict[str, List[int]]  # speaker_label -> indices in filtered list
    labels: List[str]  # sorted unique speaker labels

    @property
    def speaker_count(self) -> int:
        """Number of unique speaker labels."""
        return len(self.labels)


def group_instances_by_speaker(
    instances: List[Tuple[str, str]]
) -> SpeakerGroups:
    """
    Group instances by speaker label with index tracking.

    Parameters
    ----------
    instances : List[Tuple[str, str]]
        List of (speaker_label, utterance) tuples

    Returns
    -------
    SpeakerGroups
        Grouped instances with metadata

    Example
    -------
    >>> instances = [("Speaker 1", "Hello"), ("Speaker 2", "Hi")]
    >>> groups = group_instances_by_speaker(instances)
    >>> groups.speaker_count
    2
    """
    grouped: Dict[str, List[str]] = {}
    indices: Dict[str, List[int]] = {}

    for idx, (speaker_label, utterance) in enumerate(instances):
        if speaker_label not in grouped:
            grouped[speaker_label] = []
            indices[speaker_label] = []
        grouped[speaker_label].append(utterance)
        indices[speaker_label].append(idx)

    return SpeakerGroups(
        grouped=grouped,
        indices=indices,
        labels=sorted(grouped.keys())
    )
```

**Metrics**: Variables: 3, Statements: 12, Branches: 2, Complexity: 3

---

##### 5. `display_speaker_examples(speaker_label: str, utterances: List[str], indices: List[int], all_instances: List[Tuple[str, str]], max_samples: int = 3) -> None`
**Responsibility**: Display speaker examples with context
**Complexity**: 6

```python
@dataclass
class DisplayConfig:
    """Configuration for example display."""
    max_samples: int = 3
    context_before: int = 4
    context_after: int = 4
    separator_width: int = 70


def display_speaker_examples(
    speaker_label: str,
    utterances: List[str],
    indices: List[int],
    all_instances: List[Tuple[str, str]],
    config: DisplayConfig = DisplayConfig()
) -> None:
    """
    Display speaker examples with surrounding context.

    Parameters
    ----------
    speaker_label : str
        Speaker label being displayed
    utterances : List[str]
        List of utterances for this speaker
    indices : List[int]
        Indices of utterances in full instance list
    all_instances : List[Tuple[str, str]]
        Complete list of all filtered instances
    config : DisplayConfig
        Display configuration settings

    Example
    -------
    >>> display_speaker_examples("Speaker 1", ["Hello world"], [0], instances)
    --- Speaker Label: Speaker 1 ---
    Number of utterances: 1
    ...
    """
    print(f"\n--- Speaker Label: {speaker_label} ---")
    print(f"Number of utterances: {len(utterances)}")
    print("\nSample utterances with context:")

    num_samples = min(config.max_samples, len(utterances))

    for sample_num in range(num_samples):
        _display_single_example(
            sample_num,
            utterances[sample_num],
            indices[sample_num],
            speaker_label,
            all_instances,
            config
        )

    if len(utterances) > num_samples:
        print(f"\n  ... and {len(utterances) - num_samples} more utterances")


def _display_single_example(
    sample_num: int,
    utterance: str,
    utterance_idx: int,
    speaker_label: str,
    all_instances: List[Tuple[str, str]],
    config: DisplayConfig
) -> None:
    """Display a single example with context."""
    print(f"\n  Example {sample_num + 1}:")
    print("  " + "-" * config.separator_width)

    # Context before
    context_start = max(0, utterance_idx - config.context_before)
    for ctx_idx in range(context_start, utterance_idx):
        ctx_speaker, ctx_utterance = all_instances[ctx_idx]
        print(f"     {ctx_speaker}: {ctx_utterance}")

    # Target line (highlighted)
    print(f"  -> {speaker_label}: {utterance}")

    # Context after
    context_end = min(len(all_instances), utterance_idx + config.context_after + 1)
    for ctx_idx in range(utterance_idx + 1, context_end):
        ctx_speaker, ctx_utterance = all_instances[ctx_idx]
        print(f"     {ctx_speaker}: {ctx_utterance}")

    print("  " + "-" * config.separator_width)
```

**Metrics**: Variables: 6 per function, Statements: ~15 each, Complexity: 4-5

---

##### 6. `get_user_speaker_choice(speaker_label: str, known_speakers: List[str], suggestion: Optional[str] = None) -> Optional[str]`
**Responsibility**: Get user's speaker identification choice
**Returns**: Chosen speaker name, "skip", or None for quit
**Complexity**: 6

```python
@dataclass
class UserChoice:
    """Result of user choice input."""
    choice: str  # speaker name, "skip", or "quit"
    is_quit: bool
    is_skip: bool

    @property
    def is_valid_speaker(self) -> bool:
        """Check if choice is a valid speaker name."""
        return not self.is_quit and not self.is_skip


def get_user_speaker_choice(
    speaker_label: str,
    known_speakers: List[str],
    suggestion: Optional[str] = None
) -> UserChoice:
    """
    Prompt user to identify speaker with numbered menu.

    Parameters
    ----------
    speaker_label : str
        Generic speaker label to identify
    known_speakers : List[str]
        List of known speaker names
    suggestion : Optional[str]
        Suggested speaker based on heuristics

    Returns
    -------
    UserChoice
        User's choice with metadata

    Example
    -------
    >>> choice = get_user_speaker_choice("Speaker 1", ["Bruce", "Ivette"])
    >>> choice.is_valid_speaker
    True
    """
    print(f"\nWho is '{speaker_label}'?")
    if suggestion:
        print(f"(Suggested: {suggestion})")

    print("\nOptions:")
    for idx, speaker in enumerate(known_speakers, 1):
        marker = " *" if speaker == suggestion else ""
        print(f"  {idx}. {speaker}{marker}")
    print("  s. Skip")
    print("  q. Quit")

    while True:
        user_input = input(f"\nEnter choice (1-{len(known_speakers)}, s, q): ").strip().lower()

        if user_input == 'q':
            return UserChoice(choice="quit", is_quit=True, is_skip=False)

        if user_input == 's':
            return UserChoice(choice="skip", is_quit=False, is_skip=True)

        try:
            choice_num = int(user_input)
            if 1 <= choice_num <= len(known_speakers):
                chosen_speaker = known_speakers[choice_num - 1]
                return UserChoice(choice=chosen_speaker, is_quit=False, is_skip=False)
        except ValueError:
            pass

        print("Invalid choice. Please try again.")
```

**Metrics**: Variables: 4, Statements: 18, Branches: 6, Complexity: 6

---

##### 7. `create_training_examples_for_speaker(speaker_label: str, utterances: List[str], indices: List[int], all_instances: List[Tuple[str, str]], identified_speaker: str) -> List[Dict]`
**Responsibility**: Create training examples for identified speaker
**Returns**: List of training example dictionaries
**Complexity**: 3

```python
def create_training_examples_for_speaker(
    speaker_label: str,
    utterances: List[str],
    indices: List[int],
    all_instances: List[Tuple[str, str]],
    identified_speaker: str
) -> List[Dict]:
    """
    Create training examples for an identified speaker.

    Parameters
    ----------
    speaker_label : str
        Original generic speaker label
    utterances : List[str]
        Utterances from this speaker
    indices : List[int]
        Indices in full instance list
    all_instances : List[Tuple[str, str]]
        All filtered instances for context
    identified_speaker : str
        The identified speaker name

    Returns
    -------
    List[Dict]
        Training example dictionaries

    Example
    -------
    >>> examples = create_training_examples_for_speaker(
    ...     "Speaker 1", ["Hello"], [0], all_instances, "Bruce"
    ... )
    >>> len(examples)
    1
    """
    examples = []

    for utterance, idx in zip(utterances, indices):
        # Get context (up to 2 before, 2 after)
        context_start = max(0, idx - 2)
        context_end = min(len(all_instances), idx + 3)
        context_snippet = "\n".join(
            f"{spk}: {utt}"
            for spk, utt in all_instances[context_start:context_end]
        )

        examples.append({
            "snippet": context_snippet,
            "speaker": identified_speaker,
            "context": f"Labeling session - {speaker_label}"
        })

    return examples
```

**Metrics**: Variables: 5, Statements: 12, Branches: 0, Complexity: 2

---

##### 8. `interactive_labeling_session(groups: SpeakerGroups, all_instances: List[Tuple[str, str]], known_speakers: List[str]) -> List[Dict]`
**Responsibility**: Run interactive labeling session
**Returns**: List of newly created training examples
**Complexity**: 8

```python
def interactive_labeling_session(
    groups: SpeakerGroups,
    all_instances: List[Tuple[str, str]],
    known_speakers: List[str]
) -> List[Dict]:
    """
    Run interactive session to label speaker instances.

    Parameters
    ----------
    groups : SpeakerGroups
        Grouped speaker instances
    all_instances : List[Tuple[str, str]]
        All filtered instances
    known_speakers : List[str]
        Known speaker names

    Returns
    -------
    List[Dict]
        Newly created training examples

    Example
    -------
    >>> examples = interactive_labeling_session(groups, instances, speakers)
    >>> isinstance(examples, list)
    True
    """
    new_examples = []

    for speaker_label in groups.labels:
        utterances = groups.grouped[speaker_label]
        indices = groups.indices[speaker_label]

        # Display examples
        display_speaker_examples(
            speaker_label, utterances, indices, all_instances
        )

        # Get suggestion
        suggestion = suggest_speaker(utterances, known_speakers)

        # Get user choice
        choice = get_user_speaker_choice(speaker_label, known_speakers, suggestion)

        if choice.is_quit:
            logger.info("User quit labeling session")
            break

        if choice.is_skip:
            logger.info("Skipped speaker label: %s", speaker_label)
            continue

        # Create examples
        examples = create_training_examples_for_speaker(
            speaker_label, utterances, indices, all_instances, choice.choice
        )
        new_examples.extend(examples)

        logger.info(
            "Labeled '%s' as '%s' - created %d training examples",
            speaker_label, choice.choice, len(examples)
        )

    return new_examples
```

**Metrics**: Variables: 8, Statements: 22, Branches: 3, Complexity: 4

---

##### 9. `save_training_session(new_examples: List[Dict], existing_examples: List[Dict]) -> None`
**Responsibility**: Save and report on training session results
**Complexity**: 4

```python
@dataclass
class SessionStatistics:
    """Statistics from training session."""
    new_examples_count: int
    duplicates_removed: int
    unique_examples_added: int
    total_examples: int

    def __str__(self) -> str:
        return (
            f"\nTraining session complete!\n"
            f"New examples created: {self.new_examples_count}\n"
            f"Duplicates removed: {self.duplicates_removed}\n"
            f"Unique examples added: {self.unique_examples_added}\n"
            f"Total training examples: {self.total_examples}"
        )


def save_training_session(
    new_examples: List[Dict],
    existing_examples: List[Dict]
) -> SessionStatistics:
    """
    Save training examples and return statistics.

    Parameters
    ----------
    new_examples : List[Dict]
        Newly created examples from session
    existing_examples : List[Dict]
        Previously existing examples

    Returns
    -------
    SessionStatistics
        Session statistics

    Example
    -------
    >>> stats = save_training_session(new_examples, existing_examples)
    >>> stats.new_examples_count
    10
    """
    if not new_examples:
        logger.info("No new examples to save")
        return SessionStatistics(0, 0, 0, len(existing_examples))

    # Combine and deduplicate
    all_examples = existing_examples + new_examples
    unique_examples = deduplicate_examples(all_examples)

    # Calculate statistics
    duplicates_removed = len(all_examples) - len(unique_examples)
    unique_added = len(unique_examples) - len(existing_examples)

    # Save to file
    save_training_examples(unique_examples)

    stats = SessionStatistics(
        new_examples_count=len(new_examples),
        duplicates_removed=duplicates_removed,
        unique_examples_added=unique_added,
        total_examples=len(unique_examples)
    )

    logger.info(str(stats))
    return stats
```

**Metrics**: Variables: 6, Statements: 16, Branches: 1, Complexity: 2

---

##### 10. `label_training_transcript()` - Refactored Main Function

```python
def label_training_transcript(transcript_file: str) -> None:
    """
    Interactive tool to label speakers in a training transcript.

    Orchestrates the complete labeling workflow:
    1. Load transcript file
    2. Validate speaker profiles
    3. Extract and filter instances
    4. Group instances by speaker
    5. Run interactive labeling session
    6. Save training examples

    Parameters
    ----------
    transcript_file : str
        Path to the transcript markdown file to label

    Example
    -------
    >>> label_training_transcript("lifelogs/2025-03-01.md")
    # Interactive session to label speakers
    """
    # Step 1: Load transcript
    transcript_content = load_transcript_file(transcript_file)
    if transcript_content is None:
        return

    # Step 2: Validate profiles
    known_speakers = validate_speaker_profiles()
    if known_speakers is None:
        return

    # Display header
    print(f"\n=== Speaker Training Tool ===")
    print(f"File: {transcript_file}")
    print(f"Known speakers: {', '.join(known_speakers)}")
    print("\nThis tool will help you label speaker instances to create training data.\n")

    # Step 3: Extract and filter instances
    instances = extract_speaker_instances(transcript_content)
    if not instances:
        logger.warning("No speaker instances found in transcript")
        return

    filtered_instances, filter_stats = filter_substantial_utterances(instances)
    print(str(filter_stats))

    if not filtered_instances:
        logger.warning("No substantial instances after filtering")
        return

    # Step 4: Group instances
    groups = group_instances_by_speaker(filtered_instances)

    # Step 5: Run labeling session
    existing_examples = load_training_examples()
    new_examples = interactive_labeling_session(
        groups, filtered_instances, known_speakers
    )

    # Step 6: Save results
    session_stats = save_training_session(new_examples, existing_examples)
    print(str(session_stats))
```

**Refactored Metrics**:
- Variables: 8 (down from 45)
- Statements: ~35 (down from 112)
- Branches: ~8 (down from 29)
- Complexity: ~8 (down from 29 - B rating!)

---

## Phase 2: `score_conversation()` Refactoring

### Current State Analysis

**Complexity Metrics**:
- Cyclomatic Complexity: C/19
- Local Variables: 10
- Statements: 77
- Branches: 22

**Responsibility Violations**:
1. Duration scoring
2. Time-of-day scoring
3. Keyword scoring
4. Speaker name scoring
5. Conversation dynamics scoring
6. Penalty calculations (3 types)
7. Message length scoring
8. Breakdown dictionary management

### Refactored Design

#### Architecture Overview
```
score_conversation()  [Main orchestrator - Complexity ~6]
├─ score_duration()  [Duration assessment]
├─ score_time_of_day()  [Afternoon check]
├─ score_keywords()  [Keyword matching]
├─ score_speaker_names()  [Larry detection]
├─ score_conversation_dynamics()  [Back-and-forth]
├─ apply_penalties()  [All penalties]
│  ├─ penalty_too_many_speakers()
│  ├─ penalty_duration()
│  └─ penalty_message_length()
└─ build_score_breakdown()  [Result assembly]
```

#### Component Specifications

##### 1. Data Classes for Scoring

```python
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
        """Convert to dictionary format for compatibility."""
        breakdown = {"total_score": self.total_score}
        for comp in self.components:
            breakdown[comp.name] = comp.points
        return breakdown
```

##### 2. Metrics Extraction

```python
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
```

##### 3. Individual Scoring Functions

```python
def score_duration(metrics: ConversationMetrics) -> ScoreComponent:
    """Score based on conversation duration."""
    if 45 <= metrics.duration_minutes <= 75:
        return ScoreComponent(
            "duration",
            SCORE_DURATION_MATCH,
            f"Duration {metrics.duration_minutes}min matches therapy session (45-75min)"
        )
    return ScoreComponent("duration", 0, f"Duration {metrics.duration_minutes}min outside typical range")


def score_time_of_day(metrics: ConversationMetrics) -> ScoreComponent:
    """Score based on start time."""
    if 12 <= metrics.start_hour < 18:
        return ScoreComponent(
            "afternoon",
            SCORE_AFTERNOON,
            f"Started at {metrics.start_hour}:00 (afternoon therapy time)"
        )
    return ScoreComponent("afternoon", 0, f"Started at {metrics.start_hour}:00 (outside afternoon)")


def score_keywords(metrics: ConversationMetrics) -> ScoreComponent:
    """Score based on therapy keyword matches."""
    keyword_score = min(metrics.keyword_count * SCORE_KEYWORD, 50)
    return ScoreComponent(
        "keywords",
        keyword_score,
        f"Found {metrics.keyword_count} therapy keywords"
    )


def score_speaker_names(metrics: ConversationMetrics) -> ScoreComponent:
    """Score based on presence of Larry."""
    if metrics.has_larry:
        return ScoreComponent(
            "speaker_names",
            SCORE_SPEAKER_NAMES,
            "Larry (therapist) is a speaker"
        )
    return ScoreComponent("speaker_names", 0, "Larry not detected as speaker")


def score_conversation_dynamics(metrics: ConversationMetrics) -> ScoreComponent:
    """Score based on back-and-forth conversation pattern."""
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
```

##### 4. Penalty Calculations

```python
def calculate_penalties(metrics: ConversationMetrics) -> List[ScoreComponent]:
    """
    Calculate all applicable penalties.

    Parameters
    ----------
    metrics : ConversationMetrics
        Conversation metrics

    Returns
    -------
    List[ScoreComponent]
        List of penalty components

    Example
    -------
    >>> penalties = calculate_penalties(metrics)
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
            f"{metrics.duration_minutes}min exceeds 90min"
        ))
    elif metrics.duration_minutes < 30:
        penalties.append(ScoreComponent(
            "penalty_too_short",
            PENALTY_TOO_SHORT,
            f"{metrics.duration_minutes}min below 30min"
        ))

    # Message length penalty
    if metrics.avg_message_length < 30:
        penalties.append(ScoreComponent(
            "penalty_short_messages",
            PENALTY_SHORT_MESSAGES,
            f"Avg message {metrics.avg_message_length:.1f} chars (too brief)"
        ))

    return penalties
```

##### 5. Refactored Main Function

```python
def score_conversation(conversation: List[Dict]) -> Tuple[int, Dict]:
    """
    Score a conversation for likelihood of being a therapy session.

    Parameters
    ----------
    conversation : List[Dict]
        List of dialogue dictionaries

    Returns
    -------
    Tuple[int, Dict]
        Total score and breakdown dictionary

    Example
    -------
    >>> conversation = [{"speaker": "Larry", "datetime": dt, ...}]
    >>> score, breakdown = score_conversation(conversation)
    >>> score >= 0
    True
    """
    # Extract metrics
    metrics = extract_conversation_metrics(conversation)

    # Calculate positive scores
    components = [
        score_duration(metrics),
        score_time_of_day(metrics),
        score_keywords(metrics),
        score_speaker_names(metrics),
        score_conversation_dynamics(metrics)
    ]

    # Add penalties
    components.extend(calculate_penalties(metrics))

    # Calculate total
    total_score = sum(comp.points for comp in components)

    # Build breakdown for compatibility
    breakdown = ScoreBreakdown(
        total_score=total_score,
        components=components,
        metrics=metrics
    )

    logger.debug(
        "Conversation scored: %d points (%d positive, %d penalties)",
        total_score,
        sum(c.points for c in components if c.points > 0),
        sum(c.points for c in components if c.points < 0)
    )

    return total_score, breakdown.to_dict()
```

**Refactored Metrics**:
- Variables: 3 (down from 10)
- Statements: ~15 (down from 77)
- Branches: 0 (down from 22)
- Complexity: ~3 (down from 19 - A rating!)

---

## Phase 3: Additional C-Rated Functions

### `fetch_new_lifelogs()` Refactoring

#### Current Issues
- 17 local variables
- Complex pagination logic
- Duplicate code in sync/async versions
- Mixed responsibilities

#### Refactored Design

```python
@dataclass
class PaginationState:
    """State tracker for API pagination."""
    page: int = 1
    max_pages: int = 50
    next_cursor: Optional[str] = None
    stop_paging: bool = False
    seen_ids: Set[str] = field(default_factory=set)

    def should_continue(self) -> bool:
        """Check if pagination should continue."""
        return self.page <= self.max_pages and not self.stop_paging


@dataclass
class LifelogFetchResult:
    """Result of lifelog fetch operation."""
    lifelogs: List[Dict]
    pages_fetched: int
    stopped_early: bool
    stop_reason: Optional[str] = None


def fetch_new_lifelogs(existing_dates: Set[str]) -> List[Dict]:
    """Fetch new lifelogs using pagination."""
    logger.info("Starting to fetch new lifelogs from Limitless")

    base_params = {
        "timezone": "America/New_York",
        "limit": 100,
        "includeMarkdown": "true"
    }

    state = PaginationState()
    all_lifelogs = []

    while state.should_continue():
        # Fetch page
        params = dict(base_params)
        if state.next_cursor:
            params["cursor"] = state.next_cursor

        page_result = fetch_lifelog_page(params, state.page)
        if page_result is None:
            break

        # Process lifelogs
        new_lifelogs, should_stop = process_lifelog_page(
            page_result, existing_dates, state.seen_ids
        )
        all_lifelogs.extend(new_lifelogs)

        if should_stop:
            state.stop_paging = True
            break

        # Update pagination state
        state.next_cursor = page_result.get("meta", {}).get("lifelogs", {}).get("nextCursor")
        if not state.next_cursor:
            logger.info("No more pages, ending pagination")
            break

        state.page += 1

    logger.info("Finished fetching %d total new lifelogs", len(all_lifelogs))
    return all_lifelogs
```

**Refactored Metrics**:
- Variables: 4 (down from 17)
- Complexity: ~8 (down from 13)

---

### `build_speaker_identification_prompt()` Refactoring

#### Current Issues
- 8 local variables
- 60 statements
- Complex string building
- Mixed responsibilities

#### Refactored Design

```python
@dataclass
class PromptComponents:
    """Components of speaker identification prompt."""
    profiles_section: str
    examples_section: str
    task_section: str
    transcript_section: str


def build_speaker_profiles_section(speaker_profiles: Dict) -> str:
    """Build the speaker profiles section of the prompt."""
    # Extract into focused function
    pass


def build_training_examples_section(training_examples: List[Dict]) -> str:
    """Build the training examples section of the prompt."""
    # Extract into focused function
    pass


def build_task_instructions() -> str:
    """Build the task instructions section of the prompt."""
    # Extract into focused function
    pass


def build_speaker_identification_prompt(
    transcript: str,
    speaker_profiles: Dict,
    training_examples: List[Dict]
) -> str:
    """Build LLM prompt for speaker identification."""
    components = PromptComponents(
        profiles_section=build_speaker_profiles_section(speaker_profiles),
        examples_section=build_training_examples_section(training_examples),
        task_section=build_task_instructions(),
        transcript_section=f"```\n{transcript}\n```"
    )

    return f"""You are analyzing a conversation transcript to identify speakers.

{components.profiles_section}

{components.examples_section}

{components.task_section}

# Transcript to Analyze

{components.transcript_section}

Provide your analysis as JSON:"""
```

**Refactored Metrics**:
- Variables: 4 (down from 8)
- Complexity: ~4 (down from 17)

---

## Implementation Guidelines

### Testing Strategy

#### Unit Tests
```python
# Test individual components
def test_filter_substantial_utterances():
    """Test utterance filtering logic."""
    instances = [
        ("Speaker 1", "Yes"),
        ("Speaker 2", "I think that makes sense")
    ]
    filtered, stats = filter_substantial_utterances(instances, min_words=3)
    assert len(filtered) == 1
    assert stats.skipped_count == 1


def test_score_duration():
    """Test duration scoring component."""
    metrics = ConversationMetrics(duration_minutes=55, ...)
    component = score_duration(metrics)
    assert component.points == SCORE_DURATION_MATCH
    assert "55min" in component.reason
```

#### Integration Tests
```python
def test_label_training_transcript_workflow():
    """Test complete labeling workflow."""
    # Mock user input
    # Verify file creation
    # Check example counts
    pass
```

### Migration Strategy

1. **Create New Functions First**: Write all new helper functions with tests
2. **Update Main Function**: Replace inline logic with helper calls
3. **Test Compatibility**: Ensure behavior matches original
4. **Deprecate Old Version**: Keep old version temporarily with deprecation warning
5. **Remove Old Code**: After validation period, remove original implementation

### Code Review Checklist

- [ ] Each function has single responsibility
- [ ] Complexity ≤ 10 (B rating or better)
- [ ] Variables ≤ 15 per function
- [ ] Statements ≤ 50 per function
- [ ] All functions have docstrings with examples
- [ ] Unit tests cover edge cases
- [ ] Logging added for important operations
- [ ] Type hints on all parameters and returns
- [ ] Data classes used for related parameters (≥4 params)

---

## Success Metrics

### Quantitative Improvements

| Metric | Before | Target | Improvement |
|--------|--------|--------|-------------|
| Avg Complexity | 19 | ≤10 | 47% reduction |
| Max Variables | 45 | ≤15 | 67% reduction |
| Max Statements | 112 | ≤50 | 55% reduction |
| Max Branches | 29 | ≤12 | 59% reduction |

### Qualitative Improvements

1. **Testability**: Each component independently testable
2. **Readability**: Clear function names describe purpose
3. **Maintainability**: Changes localized to specific functions
4. **Reusability**: Components reusable across codebase
5. **Documentation**: Self-documenting through data classes and clear structure

---

## Effort Estimation

### Phase 1: `label_training_transcript()`
- Design Review: 30 minutes
- Implementation: 4 hours
- Testing: 2 hours
- **Total**: 6.5 hours

### Phase 2: `score_conversation()`
- Design Review: 15 minutes
- Implementation: 2 hours
- Testing: 1 hour
- **Total**: 3.25 hours

### Phase 3: Remaining C-Rated Functions
- `fetch_new_lifelogs()`: 2 hours
- `build_speaker_identification_prompt()`: 1.5 hours
- `find_speaker_in_transcripts()`: 1.5 hours
- **Total**: 5 hours

### Overall Total
- **Implementation**: 14.75 hours (~2 days)
- **Documentation**: 2 hours
- **Code Review**: 1 hour
- **Grand Total**: ~18 hours (2.5 days)

---

## Risks and Mitigation

### Risk 1: Breaking Existing Functionality
**Mitigation**:
- Keep original functions temporarily
- Comprehensive integration testing
- Gradual rollout with feature flags

### Risk 2: Performance Regression
**Mitigation**:
- Benchmark before and after
- Profile critical paths
- Optimize hot spots if needed

### Risk 3: User Experience Changes
**Mitigation**:
- Maintain exact same UX for interactive tools
- Test with real users before full deployment

---

## Conclusion

This refactoring design systematically addresses the complexity issues identified in the code smell review by:

1. **Decomposing Monolithic Functions**: Breaking down functions into single-responsibility components
2. **Introducing Data Classes**: Grouping related data to reduce variable count
3. **Separating Concerns**: Isolating I/O, validation, business logic, and presentation
4. **Improving Testability**: Creating independently testable components
5. **Enhancing Maintainability**: Making code easier to understand and modify

The refactored code will achieve:
- **50-70% reduction** in complexity metrics
- **B-rating or better** for all previously C/D-rated functions
- **Production-ready quality** with comprehensive test coverage
- **Improved developer experience** through clear, maintainable code

**Implementation is ready to begin following this design specification.**
