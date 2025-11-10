# Biographical System - Requirements Specification

**Created**: 2025-11-09
**Status**: Requirements Discovery Complete

---

## Executive Summary

Transform the person/place/thing feature from one-time biographical journal entries into a **living biographical database** that accumulates and synthesizes knowledge over time from multiple transcript sources.

**Core Vision**: Create master biography files that grow richer as more details emerge across daily transcripts, while preserving the chronological evolution of understanding.

---

## 1. Architecture Pattern

**Requirement**: Aggregated Biography Files as Source of Truth

**Implementation**:
- Master biography files stored in configured directory: `BIOGRAPHIES_DIR`
- Each person/place/object gets ONE master file that accumulates all knowledge
- Files continuously enriched as new biographical content is detected
- Structure supports both current synthesis and historical timeline

**Rationale**: Living documents that capture evolving understanding over time, rather than scattered one-time entries.

---

## 2. Update Strategy

**Requirement**: Append New Sections with Chronological Timeline

**Implementation**:
- Master biography files maintain chronological sections
- New biographical content appends as dated entries
- "Current Understanding" synthesis section updated during batch processing
- Preserves historical evolution while maintaining current best understanding

**File Structure**:
```markdown
# [Name] - Biographical Profile

**Last Updated**: YYYY-MM-DD

---

## Current Understanding (Auto-synthesized)

### Portrait
[Synthesized description from all accumulated knowledge]

### Memory and Moments
[Synthesized key stories across all entries]

### Meaning and Impact
[Synthesized overall significance and learning]

---

## Chronological Insights

### YYYY-MM-DD (Source Type)
[Biographical content from that date/source]

### YYYY-MM-DD (Source Type)
[Biographical content from that date/source]
```

**Rationale**: See both "who they are to me now" and "how my understanding evolved over time".

---

## 3. Speaker Labeling Integration

**Requirement**: Biography on Demand with Speaker-Aware Detection

**Implementation**:
- Speaker labeling system provides "known people" reference list
- Biography files ONLY created when explicit biographical content is detected
- Speaker labeling helps detection logic identify relevant people
- No automatic biography file creation for every identified speaker

**Detection Flow**:
1. Speaker labeling identifies people in transcripts (existing functionality)
2. Biographical detection scans for deep focus on specific people/places/objects
3. When biographical criteria met → create or update biography file
4. Speaker names help match detected content to existing biographies

**Rationale**: Intentional documentation - you control who gets biographical treatment, but system is aware of known people for better detection.

---

## 4. Source Processing

**Requirement**: Multiple Transcript Sources EXCEPT Clinical Contexts

**Sources Included**:
- ✅ Journal entries (primary source)
- ✅ Lifelogs (daily general transcripts)
- ✅ Bee transcriptions

**Sources Excluded**:
- ❌ Therapy sessions (clinical context - keep separate)
- ❌ Doctor visits (medical context - keep separate)

**Processing Strategy**: Dual-Pass on Raw Transcripts
- **Pass 1** (existing): Raw transcript → LLM → formatted output (journal/daily insight)
- **Pass 2** (new): Raw transcript → LLM → biographical extraction

**Rationale**:
- Clinical/medical contexts should not feed biographical documentation
- Process raw transcripts directly to preserve details that formatting might "wash out"
- Accept additional LLM costs for thoroughness and detail preservation

---

## 5. Extraction Method

**Requirement**: Smart Tiering Based on Content Depth

**Implementation**:
- **Full 3-Paragraph Treatment**: When content meets biographical depth criteria
  - Substantial focus (10+ sentences or ~150+ words)
  - Deep exploration and storytelling intent
  - Rich detail about person/place/object
  - Uses `person_place_thing.txt` prompt

- **Lightweight Extraction**: When content has brief but meaningful mentions
  - Key facts, memorable moments, new insights
  - Bullet-point format
  - Factual accumulation rather than narrative
  - Uses simplified extraction prompt

**Decision Logic**: LLM automatically decides based on content richness in raw transcript

**Rationale**: Match treatment to content depth - reserve rich narratives for substantial focus, efficiently capture brief mentions.

---

## 6. Synthesis Trigger

**Requirement**: Batch Processing During Scheduled Pipeline Runs

**Implementation**:
- "Current Understanding" synthesis regenerates during batch processing
- NOT real-time on every new entry
- Aligned with existing pipeline architecture (monthly summaries, etc.)
- Configurable via `PROCESS_BIOGRAPHIES` environment flag

**Synthesis Process**:
1. Scan all chronological entries in biography file
2. Send to LLM: "Synthesize current understanding from all accumulated knowledge"
3. Generate 3-paragraph synthesis (Portrait, Memory & Moments, Meaning & Impact)
4. Update "Current Understanding" section
5. Update "Last Updated" timestamp

**Rationale**: Efficient batch processing consistent with existing pipeline patterns.

---

## 7. Directory Structure

**Requirement**: Configured Path with Category Subdirectories

**Structure**:
```
BIOGRAPHIES_DIR=/Users/brucebookman/bruce_vault/Transcripts/biographies/
  people/
    Mike.md
    Larry.md
    Mom.md
  places/
    Dairy-Queen.md
    Childhood-Home.md
  objects/
    Fathers-Watch.md
```

**Configuration**:
- ENV variable: `BIOGRAPHIES_DIR` (default: `biographies`)
- Subdirectories created automatically: `people/`, `places/`, `objects/`
- Filename: sanitized name (e.g., "Dairy Queen" → `Dairy-Queen.md`)

**Rationale**: Consistent with existing directory configuration pattern, organized by category.

---

## 8. Pipeline Integration

**Requirement**: Alongside Daily Processing (After Journal Formatting)

**Pipeline Flow**:
```
1. Fetch lifelogs (existing)
2. Process journal entries - Pass 1 (existing)
3. Process biographical extraction - Pass 2 (NEW) ← Insert here
4. Process therapy sessions (existing)
5. Process doctor visits (existing)
6. Weekly/monthly summaries (existing)
```

**Configuration**:
- ENV flag: `PROCESS_BIOGRAPHIES=true/false`
- Enabled by default in production
- Can be disabled for development/testing

**Rationale**: Keep biographies current with daily content, run alongside existing daily processing.

---

## 9. Detection Criteria

**Requirement**: Automatic Detection Using Existing `person_place_thing.txt` Prompt

**Detection Criteria** (from existing prompt):
1. **Sustained Focus**: 10+ sentences or ~150+ words on single subject
2. **Deep Exploration**: Clearly documenting/capturing essence of someone/somewhere/something
3. **Storytelling Intent**: Mini-biography or character sketch
4. **Rich Detail**: Extensive characteristics, memories, history, significance

**Categories**:
- **PERSON**: Friend, family member, colleague, acquaintance
- **PLACE**: Location with personal meaning
- **OBJECT**: Meaningful item (heirloom, gift, cherished possession)

**Output**:
- If criteria met → biographical content
- If not met → return "NOT_BIOGRAPHICAL" and skip

---

## 10. Metadata Requirements

**Requirement**: Minimal Metadata - Timestamps Only

**Header Format**:
```markdown
# [Name] - Biographical Profile

**Last Updated**: YYYY-MM-DD
```

**No Additional Metadata**:
- ❌ Category (implied by directory structure)
- ❌ First documented date
- ❌ Total entries count
- ❌ Mention tracking

**Rationale**: Clean, minimal, focus on content not metadata.

---

## 11. Configuration Variables

**New Environment Variables**:

```bash
# Enable/disable biographical processing
PROCESS_BIOGRAPHIES=true

# Directory for biography files
BIOGRAPHIES_DIR=/Users/brucebookman/bruce_vault/Transcripts/biographies

# Prompt for biographical extraction
BIOGRAPHY_PROMPT=prompts/person_place_thing.txt

# Prompt for lightweight extraction (brief mentions)
BIOGRAPHY_LIGHT_PROMPT=prompts/biography_light_extraction.txt

# Prompt for synthesis regeneration
BIOGRAPHY_SYNTHESIS_PROMPT=prompts/biography_synthesis.txt
```

---

## 12. Implementation Components

**New Services Required**:

### `biography_service.py`
- `scan_for_biographical_content()` - Process raw transcripts for biographical detection
- `extract_biographical_content()` - Run biographical extraction prompts
- `update_biography_file()` - Append new content to master biography
- `synthesize_biography()` - Regenerate "Current Understanding" section
- Async versions of all functions

### `biography_utils.py`
- `sanitize_biography_filename()` - Clean names for filenames
- `parse_biography_file()` - Extract existing chronological entries
- `detect_category()` - Determine person/place/object from content
- `format_biography_section()` - Format chronological entry with date/source

### New Prompts:
- `prompts/person_place_thing.txt` - ✅ Already exists
- `prompts/biography_light_extraction.txt` - Lightweight mention extraction
- `prompts/biography_synthesis.txt` - Synthesis regeneration from accumulated knowledge

---

## 13. Data Flow

### Daily Processing Flow

```
Raw Lifelog/Bee Transcript
    ↓
[Pass 1] Format journal entry (existing)
    ↓
[Pass 2] Biographical detection (NEW)
    ↓
If biographical content detected:
    ↓
Determine category (person/place/object)
    ↓
Check if biography file exists:
    ├─ YES → Read existing file
    │         Extract chronological entries
    │         Append new entry with date/source
    │         Mark for synthesis regeneration
    │
    └─ NO  → Create new biography file
              Initialize with first entry
              Mark for synthesis regeneration
    ↓
[Batch Synthesis Phase]
For each biography marked for regeneration:
    ↓
Read all chronological entries
    ↓
Send to LLM for synthesis
    ↓
Update "Current Understanding" section
    ↓
Update "Last Updated" timestamp
    ↓
Save updated biography file
```

---

## 14. Success Criteria

**Phase 1 - MVP**:
- ✅ Biographical detection working on journal entries
- ✅ Biography files created in correct directory structure
- ✅ Chronological append functionality working
- ✅ Manual synthesis regeneration functional

**Phase 2 - Integration**:
- ✅ Dual-pass processing on lifelogs
- ✅ Dual-pass processing on bee transcriptions
- ✅ Smart tiering (full vs. lightweight extraction)
- ✅ Batch synthesis during pipeline runs

**Phase 3 - Enhancement**:
- ✅ Speaker labeling integration for detection hints
- ✅ De-duplication logic for redundant information
- ✅ Biography cross-references in monthly summaries

---

## 15. Open Questions for Future Consideration

1. **De-duplication**: How to handle same information appearing in multiple sources?
2. **Cross-references**: Should monthly summaries link to biography files?
3. **Versioning**: Should we keep historical versions of "Current Understanding" synthesis?
4. **Search/Index**: Do we need a biography index or search functionality?
5. **Export**: Any need to export biographies in different formats?

---

## 16. Dependencies

**Existing Systems**:
- Speaker labeling system (for detection hints)
- Journal processing pipeline
- Lifelog fetching and processing
- Bee transcription processing
- LLM client (OpenAI/Ollama)

**New Dependencies**:
- None (uses existing infrastructure)

---

## Next Steps

1. **Review Requirements**: Validate this specification captures your vision
2. **Design Services**: Create detailed service architecture
3. **Implement MVP**: Start with journal-only biographical detection
4. **Test & Iterate**: Validate with real data
5. **Expand Sources**: Add lifelog and bee processing
6. **Optimize**: Refine prompts and synthesis logic

---

**Status**: Ready for implementation planning
