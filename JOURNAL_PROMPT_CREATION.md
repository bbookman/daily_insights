# Journal Entry Formatter Prompt - Creation Summary

## ✅ Task Complete: journal.txt Prompt Created

The `prompts/journal.txt` file has been created with a comprehensive prompt for formatting raw journal entries into clean, well-structured markdown documents.

---

## 📋 Prompt Overview

### Purpose
Transform raw, transcribed journal entries into clean, well-structured markdown while preserving:
- Authentic voice and conversational style
- Emotional depth and truth
- Personal reflections and insights
- Natural speech patterns and hesitations

### Key Principles

1. **Authenticity First** - Never sacrifice the speaker's voice for polish
2. **Emotional Truth** - Preserve emotional reality, even if messy or contradictory
3. **Conversational Style** - Keep the natural, spoken-word quality
4. **No Judgment** - Format without editorializing or adding interpretation
5. **Preserve Nuance** - Keep hesitations, uncertainties, and emotional complexity

---

## 📐 Formatting Guidelines

### Structure & Organization
- Use markdown headers to organize thoughts by theme or topic
- Group related reflections together logically
- Preserve chronological flow when it matters
- Use subheadings to separate distinct ideas or emotional moments

### Tone & Voice
- Keep authentic voice and conversational style
- Preserve colloquialisms, hesitations, natural speech patterns
- Maintain emotional authenticity—don't sanitize or over-polish
- Keep personal, reflective quality intact

### Formatting Elements
- **Bold** for key insights, realizations, important statements
- *Italics* for emotional asides or internal reflections
- Blockquotes (`>`) for particularly poignant or important quotes
- Bullet points to organize lists of thoughts, concerns, achievements
- Line breaks to create breathing room between distinct thoughts

### Content Handling
- Remove redundant repetitions (keep only meaningful ones that show emphasis)
- Clean up transcription artifacts while preserving voice
- Preserve meaningful pauses and hesitations that convey emotion
- Keep all substantive content—nothing should be lost

### Clarity Improvements
- Fix obvious transcription errors while preserving voice
- Clarify pronouns when context is unclear
- Add brief context notes in [brackets] only when necessary
- Ensure sentences flow naturally while maintaining authenticity

---

## 📝 Output Structure

The prompt specifies this structure for formatted journal entries:

```
# Journal Entry — [Date]

## [Primary Theme/Topic]

[Opening paragraph with context and emotional tone]

### Key Reflections

[Organized thoughts and reflections]

### Emotional Insights

[Deeper emotional processing and realizations]

### Achievements & Self-Recognition

[Things the speaker is proud of or recognizing about themselves]

### Concerns & Ongoing Thoughts

[Worries, questions, or unresolved thoughts]

### Closing Reflection

[Final thoughts or takeaways from the entry]
```

---

## 🔄 Processing Steps

1. **Read** the entire journal entry to understand the overall emotional arc
2. **Identify** the main themes and topics
3. **Organize** thoughts into logical sections
4. **Format** using the guidelines
5. **Preserve** the speaker's voice throughout
6. **Review** to ensure authenticity is maintained

---

## 📊 Example Transformation

### Raw Input (from 2025-08-13.md)
```
All right, journal entry today. I'll congratulate myself that um I've mostly been making this kind of entry uh at least every day that I'm going to work, which is great. And I'm hoping that it's therapeutic. Uh just had a really interesting experience uh Russell and Ivette. Russell had the desire to transfer some money to Ivette and needed her phone number for some reason. And Ivette just exploded.
```

### Formatted Output
```
# Journal Entry — August 13, 2025

## Family Dynamics & Financial Concerns

I want to start by congratulating myself—I've been making these journal entries almost every day that I'm working, and that feels great. I'm hoping this practice is therapeutic for me.

### Today's Situation

I just had a really interesting experience with Russell and Ivette. Russell wanted to transfer some money to Ivette and needed her phone number. Ivette just exploded. I think she was worried he'd done something similar before and lost money. There was some confusion about an account being linked to Carlos, which wasn't what he was doing at all—that's a Zelle thing. But she freaked out, got really angry, and started yelling.

### My Response

I tried to counsel Russell:
- First, just walk away from the situation
- Second, explain it to me so I can help him find alternatives

I'm hoping one solution is for him to get checks and write her a check instead.
```

---

## ✨ Key Features

### Consistency with Existing Prompts
- Follows the same markdown structure as `weekly_prompt.txt` and `psycho_analysis.txt`
- Uses similar formatting conventions and style
- Maintains the project's documentation standards

### Tailored for Journal Entries
- Focuses on preserving authentic voice (unlike weekly summaries)
- Emphasizes emotional truth and personal reflection
- Designed for single-entry processing (not aggregation)
- Includes specific guidance on handling transcription artifacts

### LLM-Friendly
- Clear, specific instructions
- Concrete examples provided
- Checklist for quality assurance
- Explicit guidelines for tone and voice

---

## 🔗 Integration with Implementation Plan

This prompt is used in the `extract_and_process_journals()` function:

```python
def process_journal_with_llm(
    journal_text: str,
    prompt_file: str = JOURNAL_PROMPT_FILE
) -> str:
    """
    Process journal text through LLM using journal.txt prompt.
    
    Args:
        journal_text: Extracted and cleaned journal text
        prompt_file: Path to journal.txt prompt
    
    Returns:
        Formatted markdown journal entry
    """
    # Load prompt from prompts/journal.txt
    # Combine with journal_text
    # Call Ollama API with streaming
    # Return formatted result
```

---

## 📂 File Location

**Path:** `/Users/brucebookman/code/daily_insights/prompts/journal.txt`

**Size:** ~4.5K

**Status:** ✅ Ready for use

---

## 🎯 Next Steps

1. **Test the prompt** with real journal entries from lifelogs
2. **Refine based on output** - adjust guidelines if needed
3. **Integrate into implementation** - use in `process_journal_with_llm()`
4. **Validate output quality** - ensure formatted entries meet expectations
5. **Iterate if needed** - improve prompt based on real-world results

---

## 💡 Design Decisions

### Why This Approach?

1. **Authenticity Over Polish** - Journal entries are personal; over-formatting would lose their essence
2. **Conversational Preservation** - The speaker's voice is the most valuable part
3. **Emotional Truth** - Messy, contradictory thoughts are more authentic than sanitized versions
4. **Minimal Interpretation** - The LLM formats, not interprets
5. **Structural Clarity** - Markdown headers help organize without changing content

### What Makes It Different from Weekly Summaries?

- **Weekly Prompt:** Aggregates, interprets, adds psychological analysis
- **Journal Prompt:** Formats, preserves, maintains authenticity
- **Weekly Prompt:** Creates new insights and connections
- **Journal Prompt:** Enhances readability of existing content

---

## ✅ Quality Checklist

The prompt includes a final checklist for LLM output validation:

- [ ] Speaker's authentic voice is preserved
- [ ] Emotional truth is maintained
- [ ] Structure is clear and logical
- [ ] Formatting enhances readability
- [ ] No content has been lost or misrepresented
- [ ] The entry feels personal and genuine
- [ ] Conversational tone is intact
- [ ] Key themes are highlighted

---

## 📚 Related Documentation

- **JOURNAL_EXTRACTION_PLAN.md** - Complete implementation plan
- **IMPLEMENTATION_READY.md** - Quick start guide
- **HEADER_HANDLING_EXAMPLES.md** - Real examples from lifelogs
- **prompts/weekly_prompt.txt** - Similar prompt for weekly summaries
- **prompts/psycho_analysis.txt** - Psychological analysis prompt

---

## 🚀 Ready for Implementation

The journal.txt prompt is complete and ready to be integrated into the implementation. It provides clear, specific guidance for the LLM to format journal entries while preserving authenticity and emotional truth.

