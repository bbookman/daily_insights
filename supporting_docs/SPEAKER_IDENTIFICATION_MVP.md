# Speaker Identification System - MVP (Phase 1)

## Overview

Phase 1 implementation complete! Basic speaker identification is now integrated into the lifelog processing pipeline.

## What's Been Implemented

### Core Components

1. **Speaker Profiles** (`daily_insights/config/speaker_profiles.json`)
   - Stores known speakers with speech patterns
   - Currently includes Bruce and Ivette as examples
   - Extensible JSON structure

2. **Training Examples** (`daily_insights/config/speaker_training_examples.json`)
   - Stores manually labeled conversation examples
   - Used to train the LLM for speaker identification
   - Currently empty - needs manual labeling

3. **Processing Metadata** (`daily_insights/config/processing_metadata.json`)
   - Tracks which files have been speaker-labeled
   - Prevents duplicate processing

4. **Speaker Service** (`daily_insights/services/speaker_service.py`)
   - `load_speaker_profiles()` - Load speaker profiles
   - `identify_speakers()` / `identify_speakers_async()` - LLM-based identification
   - `apply_speaker_labels()` - Replace speaker labels with confidence tiers
   - `mark_file_processed()` - Track processing status

5. **LLM Helper** (`daily_insights/api/speaker_llm_client.py`)
   - `build_speaker_identification_prompt()` - Construct prompts
   - `parse_speaker_response()` - Parse LLM JSON output
   - `identify_speakers_with_llm_async()` - Async LLM calls

6. **Training Tool** (`daily_insights/cli/speaker_commands.py`)
   - Interactive CLI for labeling training transcripts
   - Suggests speakers based on simple heuristics
   - Saves labeled examples for training

### Integration

- **Lifelog Service** (`daily_insights/services/lifelog_service.py`)
  - Automatically identifies speakers when saving new lifelogs
  - Applies tiered confidence labeling
  - Gracefully handles identification failures

## How It Works

### Confidence Tiers

- **High (≥85%)**: Direct replacement
  - `Speaker 1` → `Bruce`

- **Medium (60-85%)**: Labeled with confidence
  - `Speaker 1` → `Bruce [72%]`

- **Low (<60%)**: Left unchanged
  - `Speaker 1` → `Speaker 1`

### Workflow

1. New lifelogs fetched from Limitless API
2. Content grouped by date
3. For each date:
   - Build combined markdown content
   - Call speaker identification (LLM analyzes content)
   - Apply speaker labels based on confidence
   - Save to disk
   - Mark as processed

## Getting Started

### Step 1: Add More Speaker Profiles

Edit `daily_insights/config/speaker_profiles.json`:

```json
{
  "version": "1.0",
  "speakers": {
    "Bruce": { ... },
    "Ivette": { ... },
    "Russell": {
      "relationship": "friend/colleague",
      "speech_patterns": {
        "vocabulary_level": "technical",
        "speaking_style": "analytical, precise",
        "common_topics": ["programming", "system design", "technology"],
        "distinctive_phrases": []
      },
      "added_date": "2025-10-29"
    }
  }
}
```

### Step 2: Label Training Transcripts

Use the interactive training tool to create labeled examples:

```bash
python -m daily_insights.cli.speaker_commands label-training lifelogs/2025-03-01.md
```

The tool will:
- Show you speaker instances from the transcript
- Suggest likely speakers based on content
- Let you confirm or correct
- Save labeled examples to training file
- Optionally update the transcript file

**Recommendation**: Label 10-20 diverse transcripts for best results.

### Step 3: Test Speaker Identification

Run your normal lifelog fetch:

```bash
python -m daily_insights.main  # or however you normally run it
```

The system will automatically:
- Identify speakers in new lifelogs
- Apply confidence-based labeling
- Save results to markdown files

### Step 4: Review Results

Check the saved lifelog files for speaker labels:
- High-confidence labels: Direct names
- Medium-confidence labels: Names with percentages
- Low-confidence: Original generic labels

## Configuration

### Confidence Thresholds

Default thresholds in `speaker_service.py`:
- High: 0.85 (85%)
- Medium: 0.60 (60%)

Can be adjusted in `apply_speaker_labels()` function calls.

### LLM Provider

Uses your existing LLM configuration from `config.py`:
- OpenAI: GPT-4o-mini
- Ollama: llama3.1:8b

## File Structure

```
daily_insights/
├── config/
│   ├── speaker_profiles.json          # Speaker definitions
│   ├── speaker_training_examples.json # Training data
│   └── processing_metadata.json       # Processing state
├── services/
│   ├── speaker_service.py             # Core speaker identification
│   └── lifelog_service.py             # Modified (integrated)
├── api/
│   └── speaker_llm_client.py          # LLM helpers
└── cli/
    └── speaker_commands.py             # Training tool
```

## Known Limitations (MVP)

1. **No historical backfilling yet** - Only processes new lifelogs
2. **Manual profile creation** - No interactive setup tool yet
3. **No speaker index** - Can't search by speaker yet
4. **No candidate discovery** - Won't detect new unknown speakers
5. **Simple training selection** - Doesn't optimize training dataset yet

These will be addressed in Phase 2-4.

## Troubleshooting

### No speaker mappings generated

**Cause**: Empty training examples or LLM not returning valid JSON

**Solution**:
1. Label at least 5-10 training transcripts
2. Check LLM is responding (test with regular daily insights)
3. Check console output for JSON parsing errors

### All labels are low confidence

**Cause**: Training examples don't match current transcript patterns

**Solution**:
- Label more diverse training examples
- Ensure speaker profiles accurately describe speech patterns
- Check that known speakers are actually in the transcript

### Speaker identification fails

**Cause**: LLM API error or timeout

**Solution**:
- System gracefully continues with original labels
- Check LLM provider configuration
- Check API keys and rate limits

## Next Steps (Phase 2)

- Interactive speaker profile initialization tool
- Tiered confidence labeling enhancements
- Better error handling and logging
- Speaker management commands (add, edit, list)

## Testing the System

### Quick Test

1. Add a few speakers to `speaker_profiles.json`
2. Label 1-2 training transcripts
3. Fetch new lifelogs
4. Check output files for speaker labels

### Full Test

1. Add 10+ speakers
2. Label 10-20 diverse transcripts
3. Process multiple days of lifelogs
4. Review accuracy and confidence distributions
5. Refine profiles and training data

## Support

For issues or questions about this implementation, review:
- This document (SPEAKER_IDENTIFICATION_MVP.md)
- Feature specification document
- Code comments in speaker_service.py and speaker_llm_client.py
