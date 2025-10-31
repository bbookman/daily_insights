"""LLM client helpers for speaker identification."""

import json
from typing import Dict, List, Optional
from daily_insights.api.llm_client import generate_summary, generate_summary_async


def build_speaker_identification_prompt(
    transcript: str,
    speaker_profiles: Dict,
    training_examples: List[Dict]
) -> str:
    """
    Build LLM prompt for speaker identification.

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
    # Build speaker profiles section
    profiles_text = "# Known Speakers\n\n"
    for name, profile in speaker_profiles.items():
        profiles_text += f"## {name}\n"
        if "relationship" in profile:
            profiles_text += f"- Relationship: {profile['relationship']}\n"

        if "speech_patterns" in profile:
            patterns = profile["speech_patterns"]
            if "vocabulary_level" in patterns:
                profiles_text += f"- Vocabulary: {patterns['vocabulary_level']}\n"
            if "speaking_style" in patterns:
                profiles_text += f"- Style: {patterns['speaking_style']}\n"
            if "common_topics" in patterns:
                topics = patterns["common_topics"]
                if isinstance(topics, list):
                    topics = ", ".join(topics)
                profiles_text += f"- Common topics: {topics}\n"
            if "distinctive_phrases" in patterns and patterns["distinctive_phrases"]:
                phrases = patterns["distinctive_phrases"]
                if isinstance(phrases, list):
                    phrases = ", ".join(phrases)
                profiles_text += f"- Distinctive phrases: {phrases}\n"
        profiles_text += "\n"

    # Build training examples section
    examples_text = ""
    if training_examples:
        examples_text = "# Training Examples\n\n"
        for i, example in enumerate(training_examples[:10], 1):  # Use max 10 examples
            examples_text += f"## Example {i}\n"
            if "snippet" in example:
                examples_text += f"```\n{example['snippet']}\n```\n"
            if "speakers" in example:
                examples_text += f"Speakers: {', '.join(example['speakers'])}\n"
            elif "speaker" in example:
                examples_text += f"Speaker: {example['speaker']}\n"
            if "context" in example:
                examples_text += f"Context: {example['context']}\n"
            examples_text += "\n"

    # Build the main prompt
    prompt = f"""You are analyzing a conversation transcript to identify speakers.

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

    return prompt


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
            print(f"Warning: No JSON found in LLM response")
            return []

        json_str = llm_output[start_idx:end_idx]
        data = json.loads(json_str)

        if "speaker_mappings" in data:
            return data["speaker_mappings"]
        else:
            print(f"Warning: No 'speaker_mappings' key in LLM response")
            return []

    except json.JSONDecodeError as e:
        print(f"Error parsing LLM JSON response: {e}")
        print(f"Response was: {llm_output[:500]}")
        return []
    except Exception as e:
        print(f"Unexpected error parsing speaker response: {e}")
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
