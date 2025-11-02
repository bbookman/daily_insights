"""LLM client helpers for speaker identification."""

import json
from typing import Dict, List, Optional

from daily_insights.logging_config import get_logger
from daily_insights.api.llm_client import generate_summary, generate_summary_async

logger = get_logger(__name__)


# ============================================================================
# Helper Functions for Prompt Building
# ============================================================================

def _format_list_field(value, default: str = "") -> str:
    """
    Format a field that might be a list or string.

    Parameters
    ----------
    value
        Field value (list or string)
    default : str
        Default value if empty

    Returns
    -------
    str
        Comma-separated string

    Example
    -------
    >>> _format_list_field(["topic1", "topic2"])
    'topic1, topic2'
    >>> _format_list_field("single")
    'single'
    """
    if isinstance(value, list):
        return ", ".join(value) if value else default
    return str(value) if value else default


def _build_speech_patterns_section(patterns: Dict) -> str:
    """
    Build speech patterns section for a speaker profile.

    Parameters
    ----------
    patterns : Dict
        Speech patterns dictionary

    Returns
    -------
    str
        Formatted speech patterns text

    Example
    -------
    >>> patterns = {"vocabulary_level": "college", "speaking_style": "analytical"}
    >>> text = _build_speech_patterns_section(patterns)
    >>> "Vocabulary: college" in text
    True
    """
    lines = []

    if "vocabulary_level" in patterns:
        lines.append(f"- Vocabulary: {patterns['vocabulary_level']}")

    if "speaking_style" in patterns:
        lines.append(f"- Style: {patterns['speaking_style']}")

    if "common_topics" in patterns:
        topics = _format_list_field(patterns["common_topics"])
        if topics:
            lines.append(f"- Common topics: {topics}")

    if "distinctive_phrases" in patterns and patterns["distinctive_phrases"]:
        phrases = _format_list_field(patterns["distinctive_phrases"])
        if phrases:
            lines.append(f"- Distinctive phrases: {phrases}")

    return "\n".join(lines)


def _build_speaker_profile(name: str, profile: Dict) -> str:
    """
    Build formatted text for a single speaker profile.

    Parameters
    ----------
    name : str
        Speaker name
    profile : Dict
        Speaker profile data

    Returns
    -------
    str
        Formatted profile text

    Example
    -------
    >>> profile = {"relationship": "friend", "speech_patterns": {...}}
    >>> text = _build_speaker_profile("Bruce", profile)
    >>> "## Bruce" in text
    True
    """
    lines = [f"## {name}"]

    if "relationship" in profile:
        lines.append(f"- Relationship: {profile['relationship']}")

    if "speech_patterns" in profile:
        pattern_text = _build_speech_patterns_section(profile["speech_patterns"])
        if pattern_text:
            lines.append(pattern_text)

    return "\n".join(lines)


def _build_profiles_section(speaker_profiles: Dict) -> str:
    """
    Build the known speakers section of the prompt.

    Parameters
    ----------
    speaker_profiles : Dict
        Dictionary of speaker profiles

    Returns
    -------
    str
        Formatted profiles section

    Example
    -------
    >>> profiles = {"Bruce": {...}, "Ivette": {...}}
    >>> text = _build_profiles_section(profiles)
    >>> "# Known Speakers" in text
    True
    """
    if not speaker_profiles:
        return ""

    lines = ["# Known Speakers", ""]

    for name, profile in speaker_profiles.items():
        lines.append(_build_speaker_profile(name, profile))
        lines.append("")  # Blank line between profiles

    return "\n".join(lines)


def _build_training_example(index: int, example: Dict) -> str:
    """
    Build formatted text for a single training example.

    Parameters
    ----------
    index : int
        Example number (1-indexed)
    example : Dict
        Training example data

    Returns
    -------
    str
        Formatted example text

    Example
    -------
    >>> example = {"snippet": "Hello", "speaker": "Bruce"}
    >>> text = _build_training_example(1, example)
    >>> "## Example 1" in text
    True
    """
    lines = [f"## Example {index}"]

    if "snippet" in example:
        lines.append(f"```\n{example['snippet']}\n```")

    if "speakers" in example:
        lines.append(f"Speakers: {', '.join(example['speakers'])}")
    elif "speaker" in example:
        lines.append(f"Speaker: {example['speaker']}")

    if "context" in example:
        lines.append(f"Context: {example['context']}")

    return "\n".join(lines)


def _build_examples_section(training_examples: List[Dict], max_examples: int = 10) -> str:
    """
    Build the training examples section of the prompt.

    Parameters
    ----------
    training_examples : List[Dict]
        List of training examples
    max_examples : int
        Maximum number of examples to include

    Returns
    -------
    str
        Formatted examples section

    Example
    -------
    >>> examples = [{"snippet": "...", "speaker": "Bruce"}]
    >>> text = _build_examples_section(examples)
    >>> "# Training Examples" in text
    True
    """
    if not training_examples:
        return ""

    lines = ["# Training Examples", ""]

    for i, example in enumerate(training_examples[:max_examples], 1):
        lines.append(_build_training_example(i, example))
        lines.append("")  # Blank line between examples

    return "\n".join(lines)


def _build_prompt_template(profiles_text: str, examples_text: str, transcript: str) -> str:
    """
    Build the complete prompt template with all sections.

    Parameters
    ----------
    profiles_text : str
        Formatted speaker profiles section
    examples_text : str
        Formatted training examples section
    transcript : str
        Conversation transcript to analyze

    Returns
    -------
    str
        Complete formatted prompt

    Example
    -------
    >>> prompt = _build_prompt_template("# Speakers", "# Examples", "transcript")
    >>> "You are analyzing" in prompt
    True
    """
    return f"""You are analyzing a conversation transcript to identify speakers.

{profiles_text}

{examples_text}

# Task

Analyze the following transcript and identify which known speaker corresponds to each generic speaker label ("Speaker 1", "Speaker 2", "Unknown", etc.).

For each speaker label found in the transcript, provide:
1. The identified person's name from the known speakers list
2. A confidence score (0.0 to 1.0)
3. Brief reasoning for your identification

Return your response as a JSON object with this structure:
{{
  "speaker_mappings": [
    {{
      "original_label": "Speaker 1",
      "identified_as": "Bruce",
      "confidence": 0.95,
      "reasoning": "Uses logical, analytical language. Mentions pets Peach and Grape. College-level vocabulary."
    }},
    {{
      "original_label": "Speaker 2",
      "identified_as": "Ivette",
      "confidence": 0.88,
      "reasoning": "Direct, emphatic speaking style. Protective statements about pets match profile."
    }}
  ]
}}

If you cannot confidently identify a speaker (confidence < 0.60), use "Unknown" as the identified_as value.

# Transcript to Analyze

```
{transcript}
```

Provide your analysis as JSON:"""


def build_speaker_identification_prompt(
    transcript: str,
    speaker_profiles: Dict,
    training_examples: List[Dict]
) -> str:
    """
    Build LLM prompt for speaker identification.

    Orchestrates prompt construction in clear steps:
    1. Build speaker profiles section
    2. Build training examples section
    3. Assemble complete prompt template

    Parameters
    ----------
    transcript : str
        The conversation transcript with generic speaker labels
    speaker_profiles : Dict
        Dictionary of known speakers and their characteristics
    training_examples : List[Dict]
        List of example conversations with correct speaker labels

    Returns
    -------
    str
        Formatted prompt for LLM speaker identification

    Example
    -------
    >>> prompt = build_speaker_identification_prompt(
    ...     "Speaker 1: Hi there\nSpeaker 2: Hello",
    ...     {"Bruce": {"speech_patterns": {...}}},
    ...     [{"snippet": "...", "speaker": "Bruce"}]
    ... )
    """
    # Step 1: Build speaker profiles section
    profiles_text = _build_profiles_section(speaker_profiles)

    # Step 2: Build training examples section
    examples_text = _build_examples_section(training_examples)

    # Step 3: Assemble complete prompt
    return _build_prompt_template(profiles_text, examples_text, transcript)


def parse_speaker_response(llm_output: str) -> List[Dict]:
    """
    Parse LLM response for speaker identifications.

    Parameters
    ----------
    llm_output : str
        Raw output from LLM

    Returns
    -------
    List[Dict]
        List of speaker identification dictionaries with keys:
        - original_label: str (e.g., "Speaker 1")
        - identified_as: str (e.g., "Bruce")
        - confidence: float (0.0 to 1.0)
        - reasoning: str

    Example
    -------
    >>> result = parse_speaker_response(llm_json_output)
    >>> result[0]
    {'original_label': 'Speaker 1', 'identified_as': 'Bruce', 'confidence': 0.95, ...}
    """
    try:
        # Try to find JSON in the response
        # LLMs sometimes add extra text before/after JSON
        start_idx = llm_output.find('{')
        end_idx = llm_output.rfind('}') + 1

        if start_idx == -1 or end_idx == 0:
            logger.warning("No JSON found in LLM response")
            return []

        json_str = llm_output[start_idx:end_idx]
        data = json.loads(json_str)

        if "speaker_mappings" in data:
            return data["speaker_mappings"]
        else:
            logger.warning("No 'speaker_mappings' key in LLM response")
            return []

    except json.JSONDecodeError as e:
        logger.error("Error parsing LLM JSON response. Response: %s", llm_output[:500], exc_info=True)
        return []
    except Exception as e:
        logger.error("Unexpected error parsing speaker response", exc_info=True)
        return []


def identify_speakers_with_llm(
    transcript: str,
    speaker_profiles: Dict,
    training_examples: List[Dict]
) -> List[Dict]:
    """
    Synchronous speaker identification using LLM.

    Parameters
    ----------
    transcript : str
        Conversation transcript to analyze
    speaker_profiles : Dict
        Known speaker profiles
    training_examples : List[Dict]
        Training examples for pattern learning

    Returns
    -------
    List[Dict]
        Speaker identification results

    Example
    -------
    >>> results = identify_speakers_with_llm(transcript, profiles, examples)
    >>> len(results)
    2
    """
    prompt = build_speaker_identification_prompt(
        transcript, speaker_profiles, training_examples
    )

    llm_output = generate_summary(prompt)
    return parse_speaker_response(llm_output)


async def identify_speakers_with_llm_async(
    transcript: str,
    speaker_profiles: Dict,
    training_examples: List[Dict]
) -> List[Dict]:
    """
    Async speaker identification using LLM.

    Parameters
    ----------
    transcript : str
        Conversation transcript to analyze
    speaker_profiles : Dict
        Known speaker profiles
    training_examples : List[Dict]
        Training examples for pattern learning

    Returns
    -------
    List[Dict]
        Speaker identification results

    Example
    -------
    >>> results = await identify_speakers_with_llm_async(transcript, profiles, examples)
    >>> len(results)
    2
    """
    prompt = build_speaker_identification_prompt(
        transcript, speaker_profiles, training_examples
    )

    llm_output = await generate_summary_async(prompt)
    return parse_speaker_response(llm_output)


def analyze_speaker_patterns_with_llm(speaker_name: str, excerpts: List[str]) -> Optional[Dict]:
    """
    Analyze transcript excerpts to suggest speech patterns for a speaker.

    Uses LLM to analyze conversation samples and suggest vocabulary level,
    speaking style, common topics, and distinctive phrases.

    Parameters
    ----------
    speaker_name : str
        Name of the speaker being analyzed
    excerpts : List[str]
        List of conversation excerpts featuring this speaker

    Returns
    -------
    Optional[Dict]
        Suggested speech patterns with keys:
        - vocabulary_level: str (child-like, conversational, college, technical)
        - speaking_style: str (comma-separated adjectives)
        - common_topics: List[str] (5-7 topics)
        - distinctive_phrases: List[str] (3-5 characteristic phrases)
        Returns None if analysis fails.

    Example
    -------
    >>> excerpts = ["Bruce: I need to analyze the system architecture...", ...]
    >>> patterns = analyze_speaker_patterns_with_llm("Bruce", excerpts)
    >>> patterns["vocabulary_level"]
    'college'
    """
    if not excerpts:
        return None

    # Combine excerpts for analysis (limit to avoid token overflow)
    combined_text = "\n".join(excerpts[:20])  # Max 20 excerpts

    prompt = f"""Analyze these conversation excerpts from {speaker_name} and suggest their speech patterns.

# Conversation Excerpts

```
{combined_text}
```

# Task

Based on these excerpts, suggest:

1. **Vocabulary Level** - Choose ONE:
   - "child-like" - Simple words, short sentences, basic concepts
   - "conversational" - Everyday language, normal speaking patterns
   - "college" - Sophisticated vocabulary, complex sentences
   - "technical" - Specialized terminology, domain-specific language

2. **Speaking Style** - Provide 3-5 adjectives describing their communication style
   Examples: analytical, emotional, direct, humorous, formal, casual, etc.

3. **Common Topics** - List 5-7 topics they frequently discuss
   Examples: work, family, technology, sports, etc.

4. **Distinctive Phrases** - List 3-5 phrases they use repeatedly or characteristically
   Examples: "just a second", "you know what I mean", specific greetings, etc.

Return your analysis as JSON:

{{
  "vocabulary_level": "conversational",
  "speaking_style": "direct, analytical, organized",
  "common_topics": ["work", "family", "pets", "technology", "home"],
  "distinctive_phrases": ["just a second", "let me think", "does that make sense"]
}}

Provide only the JSON response:"""

    try:
        llm_output = generate_summary(prompt)

        # Extract JSON from response
        start_idx = llm_output.find('{')
        end_idx = llm_output.rfind('}') + 1

        if start_idx == -1 or end_idx == 0:
            logger.warning("No JSON found in pattern analysis response")
            return None

        json_str = llm_output[start_idx:end_idx]
        patterns = json.loads(json_str)

        # Validate required fields
        required_fields = ["vocabulary_level", "speaking_style", "common_topics", "distinctive_phrases"]
        if all(field in patterns for field in required_fields):
            return patterns
        else:
            logger.warning("Missing required fields in pattern analysis")
            return None

    except json.JSONDecodeError as e:
        logger.error("Error parsing pattern analysis JSON", exc_info=True)
        return None
    except Exception as e:
        logger.error("Error during pattern analysis", exc_info=True)
        return None
