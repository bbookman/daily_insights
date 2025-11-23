# Entity Management & Transcript Standardization System

**Created**: 2025-11-23
**Status**: Implementation In Progress

## Problem Statement

The biography service creates near-duplicate files due to:
1. **STT misspellings**: TV Pal vs TV Pow, Joel Gilmet vs Joel Guillerme, Crape vs Grape
2. **Name standardization**: Matt vs Matt Bookman, Joel vs Joel Guilmet
3. **Cross-category confusion**: Voice Farm appearing in people/, places/, AND objects/

### Examples of Duplicates Found

| Duplicates | Same Subject |
|------------|--------------|
| `TV-Pal.md`, `TV-Pow.md` | TV Pow (TV show) |
| `Joel.md`, `Joel-Gilmet.md`, `Joel-Guillerme.md` | Joel Guilmet (friend) |
| `Matt.md`, `Matt-Bookman.md` | Matt Bookman (brother) |
| `Mike-Rable.md`, `Mike-Rabel.md` | Mike Rabel (friend) |
| `Suzanne-Mallary.md`, `Suzanne-Mallory.md` | Suzanne Mallory |

## Solution: Fix at Source, Then Fresh Start

Rather than complex merge tooling, we:
1. Fix STT errors at the transcript level (earliest intervention)
2. Create unified entity registry for both speakers AND biography subjects
3. Delete existing biographies and regenerate with standardized names

---

## Phase 0: Unified Entity Registry

### Schema: `config/entity_profiles.json`

Expands the existing `speaker_profiles.json` to serve both speaker labeling AND biography subject resolution.

```json
{
  "version": "2.0",
  "entities": {
    "Matt Bookman": {
      "canonical_name": "Matt Bookman",
      "entity_type": "person",
      "is_speaker": true,
      "is_biographical_subject": true,
      "aliases": ["Matt", "Matthew", "Matthew Bookman"],
      "stt_corrections": {
        "Mat": "Matt",
        "Mat Bookman": "Matt Bookman",
        "Mathew": "Matt"
      },
      "relationship": "brother",
      "relationships": {
        "Bruce": "brother",
        "Linda": "spouse"
      },
      "biographical_context": "Stanford grad, bioinformatics, works at Verily",
      "languages": { "English": "fluent" },
      "speech_patterns": { ... }
    },
    "Grape": {
      "canonical_name": "Grape",
      "entity_type": "pet",
      "is_speaker": false,
      "is_biographical_subject": true,
      "aliases": [],
      "stt_corrections": {
        "Crape": "Grape",
        "Gray": "Grape"
      },
      "relationship": "pet",
      "biographical_context": "Family cat"
    },
    "TV Pow": {
      "canonical_name": "TV Pow",
      "entity_type": "object",
      "is_speaker": false,
      "is_biographical_subject": true,
      "aliases": ["TV Power"],
      "stt_corrections": {
        "TV Pal": "TV Pow",
        "TV Paul": "TV Pow"
      },
      "biographical_context": "Interactive TV show from late 1970s"
    }
  }
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `canonical_name` | string | Yes | Authoritative name used for file naming |
| `entity_type` | enum | Yes | person, place, object, pet, device |
| `is_speaker` | bool | Yes | Can appear as speaker in transcripts |
| `is_biographical_subject` | bool | Yes | Should have biography file |
| `aliases` | list | Yes | Known alternate names (intentional variations) |
| `stt_corrections` | dict | Yes | Map of STT errors → correct spelling |
| `relationship` | string | No | Relationship to primary user |
| `relationships` | dict | No | Relationships to other entities |
| `biographical_context` | string | No | Brief description for LLM disambiguation |
| `languages` | dict | No | Languages spoken (speakers only) |
| `speech_patterns` | dict | No | Speech characteristics (speakers only) |

### New Service: `services/entity_registry.py`

```python
def load_entity_registry() -> Dict
def save_entity_registry(data: Dict) -> None
def get_entity(name: str) -> Optional[Dict]
def get_speakers() -> Dict  # Filter by is_speaker=True
def get_biographical_subjects() -> Dict  # Filter by is_biographical_subject=True
def get_all_stt_corrections() -> Dict[str, str]  # Aggregated corrections map
def add_entity(name: str, entity_data: Dict) -> bool
def add_stt_correction(wrong: str, right: str, entity_name: str) -> bool
```

---

## Phase 1: Transcript Standardization

### Processing Pipeline Position

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Raw Lifelog │ --> │ Standardizer     │ --> │ Speaker Labeling│
│ from API    │     │ (STT corrections)│     │ Journal Detect  │
└─────────────┘     └──────────────────┘     │ Biography Detect│
                                              └─────────────────┘
```

### New Service: `services/transcript_standardizer.py`

```python
def load_stt_corrections() -> Dict[str, str]:
    """Build aggregated correction map from entity registry."""

def standardize_transcript(content: str) -> str:
    """
    Apply STT corrections with word-boundary awareness.
    Corrections sorted by length (longest first) to prevent
    partial replacements.
    """

def report_corrections(content: str) -> List[Dict]:
    """Dry-run: return list of corrections that would be made."""
```

### Correction Logic

```python
def standardize_transcript(content: str, corrections: Dict[str, str]) -> str:
    result = content
    # Sort by length descending to match longest phrases first
    # e.g., "Joel Gilmet" before "Joel"
    sorted_corrections = sorted(corrections.items(), key=lambda x: -len(x[0]))

    for wrong, right in sorted_corrections:
        # Word-boundary aware replacement
        pattern = r'\b' + re.escape(wrong) + r'\b'
        result = re.sub(pattern, right, result, flags=re.IGNORECASE)

    return result
```

---

## Phase 1.5: Clean Slate (Manual Step)

After Phases 0-1 are implemented and tested:

```bash
# 1. Delete all biography files
rm -rf biographies/people/*.md
rm -rf biographies/places/*.md
rm -rf biographies/objects/*.md

# 2. Clear processing state
rm biographies/.biographical_processing_state.json

# 3. Run pipeline - biographies regenerate with standardized names
python -m daily_insights.main
```

---

## Phase 2: Entity Resolution (Safety Net)

### New Service: `services/entity_resolver.py`

```python
def resolve_entity(detected_name: str, category: str) -> Optional[str]:
    """
    Resolve a detected entity name to its canonical form.

    Resolution order:
    1. Exact match in stt_corrections
    2. Exact match in aliases
    3. Fuzzy match against canonical_name (85% threshold)
    4. LLM disambiguation if multiple candidates

    Returns canonical_name or None if new entity.
    """
```

### Integration in biography_service.py

```python
# In process_biographical_extraction(), before file creation:
detected_name = detection_result['subject_name']  # e.g., "Joel Gilmet"
canonical_name = resolve_entity(detected_name, detection_result['category'])

if canonical_name:
    # Use canonical name for file path
    filepath = get_biography_filepath(canonical_name, category, biographies_dir)
else:
    # New entity - use detected name, optionally flag for review
    filepath = get_biography_filepath(detected_name, category, biographies_dir)
```

---

## Phase 3: Unified Entity CLI

### Rename: `cli/speaker_commands.py` → `cli/entity_commands.py`

### Commands

```bash
# Entity management
entity_commands init --type [speaker|person|place|object|pet]
entity_commands list [--type TYPE] [--show-aliases]
entity_commands show <entity_name>

# STT correction management
entity_commands add-correction "wrong" "right" [--entity NAME]
entity_commands list-corrections

# Transcript standardization
entity_commands preview-fixes <file>
entity_commands standardize <file>
entity_commands standardize-all [--dry-run|--apply]

# Resolution testing
entity_commands resolve "detected name"
```

---

## Migration Path

### From speaker_profiles.json to entity_profiles.json

1. Load existing `speaker_profiles.json`
2. For each speaker, add new fields with defaults:
   - `canonical_name`: same as key
   - `entity_type`: "person" (or "device" for Alexa/Siri)
   - `is_speaker`: true
   - `is_biographical_subject`: true (false for devices)
   - `aliases`: extract from relationships if applicable
   - `stt_corrections`: empty initially
3. Add non-speaker entities (pets, places, objects) from known duplicates
4. Save as `entity_profiles.json`

### Backward Compatibility

`speaker_service.py` updated to:
- Load from `entity_profiles.json`
- Filter entities by `is_speaker == true`
- Existing speaker labeling logic unchanged

---

## Benefits

1. **Single source of truth** - One registry for speakers AND biography subjects
2. **Fix at source** - STT corrections prevent duplicates before they happen
3. **Leverages existing data** - Bruce's relationships already list most biography subjects
4. **Backward compatible** - Speaker labeling continues to work
5. **Progressive enhancement** - Add entities/corrections over time as discovered
6. **No complex merge code** - Fresh start approach avoids retroactive cleanup

---

## Files to Create/Modify

### New Files
- `config/entity_profiles.json` - Unified entity registry
- `services/entity_registry.py` - Registry load/save/query functions
- `services/transcript_standardizer.py` - STT correction service
- `services/entity_resolver.py` - Entity name resolution

### Modified Files
- `services/speaker_service.py` - Use entity registry, filter by is_speaker
- `services/biography_service.py` - Add resolver call before file creation
- `cli/speaker_commands.py` → `cli/entity_commands.py` - Expanded CLI
