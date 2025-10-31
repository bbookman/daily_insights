# Speaker Identification - Future Enhancements

## Pending Integrations

### ⚠️ HIGH PRIORITY: Integrate Speaker Identification with Bee Service

**Status:** Not yet implemented
**Requested:** 2025-10-30
**Target:** Phase 2 or later

**What needs to be done:**
- Modify `daily_insights/services/bee_service.py`
- Add speaker identification to `save_bee_insight_async()` function (around line 430-490)
- Mirror the implementation from `lifelog_service.py:233-246`

**Implementation snippet:**
```python
# In bee_service.py, add to save_bee_insight_async():
from daily_insights.services.speaker_service import (
    identify_speakers_async,
    apply_speaker_labels,
    mark_file_processed
)

# Before saving content:
try:
    speaker_mappings = await identify_speakers_async(content)
    if speaker_mappings:
        content = apply_speaker_labels(content, speaker_mappings)
except Exception as e:
    print(f"Warning: Speaker identification failed: {e}")

# After saving:
mark_file_processed(f"bee/{filename}")
```

**Benefits:**
- Bee transcripts get automatic speaker identification
- Consistent labeling across lifelogs and bee files
- Better AI insights with identified speakers in bee data
- Searchable speaker index will include bee conversations

---

## Phase 2 Features (Planned)

### Interactive Speaker Profile Initialization
- Command: `python -m daily_insights speaker init`
- Conversational LLM-powered setup
- Create speaker profiles naturally

### Speaker Candidate Discovery
- Automatically detect potential new speakers
- Non-blocking async discovery
- Review tool to approve/reject candidates

### Speaker Search Index
- JSON-based searchable index
- Find all conversations with specific people
- Bidirectional lookup (speaker→conversations, conversation→speakers)

---

## Phase 3 Features (Planned)

### Historical Backfilling
- Process old transcripts backward in time
- Progressive enhancement of archive
- Batch processing with rate limiting

### Learning & Optimization
- Rolling training dataset (20 best examples)
- Learn from high-confidence predictions
- Continuous improvement cycle

---

## Phase 4 Features (Planned)

### Additional Management Tools
- `speaker add` - Add single speaker
- `speaker edit` - Modify profiles
- `speaker list` - View all speakers
- `speaker add-examples` - Enhance training

---

## Phase 5 Features (Future)

### Extensible Processor Architecture
- Pipeline for multiple transcript enhancements
- Transcription error correction
- Punctuation improvement
- Other future processors

---

## Notes

Remember to check this file when planning next development sessions!
