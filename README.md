# Daily Insights

Automated pipeline for fetching, processing, and generating insights from Limitless AI lifelogs and transcriptions.

## Features

- **Lifelog Management** - Fetch and organize daily lifelogs from Limitless API with automatic pagination
- **Daily Insights** - Retrieve and store AI-generated daily summaries from Limitless chats
- **Speaker Identification** - LLM-based speaker labeling in transcripts with configurable profiles
- **Bee Transcription Processing** - Convert raw Bee transcriptions into structured daily insights
- **Journal Entry Formatting** - Transform raw journal transcripts into structured, well-formatted markdown entries
- **Therapy Session Detection** - Automatically identify and analyze therapy sessions in lifelogs
- **Weekly Summaries** - Aggregate 7 days of insights into comprehensive weekly reports
- **Monthly Summaries** - Generate monthly overview reports from daily data
- **Async Pipeline** - Parallel processing for improved performance (3-stage architecture)
- **Feature Toggles** - Granular control over pipeline operations via environment variables

## Installation

```bash
# Clone repository
git clone <repository-url>
cd daily_insights

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and preferences
```

## Configuration (.env)

### Required Settings

```bash
# Limitless API
LIMITLESS_API_KEY=your_limitless_api_key_here
LIMITLESS_CHATS_API_BASE=https://api.limitless.ai/v1/chats
LIMITLESS_LIFELOGS_API_BASE=https://api.limitless.ai/v1/lifelogs

# LLM Provider (choose one)
LLM_PROVIDER=openai  # or 'ollama'

# OpenAI Configuration (if LLM_PROVIDER=openai)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4

# Ollama Configuration (if LLM_PROVIDER=ollama)
OLLAMA_MODEL=llama3.2
```

### Feature Toggles

Control which pipeline operations execute. Accepts: `true/false`, `yes/no`, `1/0`, `on/off` (case-insensitive).

```bash
# Fetch operations
FETCH_LIFELOGS=true              # Fetch new lifelogs from API
FETCH_DAILY_INSIGHTS=true        # Fetch daily insights/chats from API

# Processing operations
PROCESS_BEE_TRANSCRIPTIONS=true  # Process Bee transcription files
PROCESS_JOURNAL_ENTRIES=true     # Format and process journal entries
PROCESS_THERAPY_SESSIONS=true    # Detect and analyze therapy sessions
CREATE_WEEKLY_SUMMARIES=true     # Generate weekly summary reports
CREATE_MONTHLY_SUMMARIES=true    # Generate monthly summary reports
LABEL_SPEAKERS=true              # Identify and label speakers in transcripts
```

**Use Cases:**
- Development: Disable `FETCH_LIFELOGS` and `FETCH_DAILY_INSIGHTS` to avoid API calls
- Cost optimization: Disable `LABEL_SPEAKERS`, `PROCESS_BEE_TRANSCRIPTIONS`, or `PROCESS_JOURNAL_ENTRIES` to reduce LLM API costs
- Faster processing: Disable summaries if only daily data is needed
- Skip features: Disable `PROCESS_BEE_TRANSCRIPTIONS` or `PROCESS_JOURNAL_ENTRIES` if not using those features

### Directory Paths

```bash
LIFELOGS_DIR=lifelogs                # Raw lifelog transcripts
INSIGHTS_DIR=daily                   # Daily insights and bee processing
WEEKLY_INSIGHTS_DIR=weekly           # Weekly summary reports
MONTHLY_INSIGHTS_DIR=monthly         # Monthly summary reports
BEE_DIR=bee                          # Bee transcription files
PSYCHOLOGIST_DIR=psychologist        # Therapy session analyses
JOURNAL_DIR=journal                  # Journal entries
```

### Therapy Detection (Optional)

Fine-tune therapy session detection with scoring parameters. See `.env.example` for full list.

```bash
CONFIDENCE_THRESHOLD=50       # Minimum score to classify as therapy session
CONVERSATION_GAP_MINUTES=15   # Max gap between messages in same conversation
MIN_DURATION=30               # Minimum session duration (minutes)
MAX_DURATION=75               # Maximum session duration (minutes)
```

## Usage

### Run Full Pipeline

```bash
# Async version (recommended - faster with parallel processing)
python run_daily_insights.py

# Or from module
python -m daily_insights.main
```

### Pipeline Stages

The async pipeline executes in 3 optimized stages:

1. **Data Fetching** - Parallel API calls for lifelogs and insights
2. **File Processing** - Concurrent bee transcription and therapy session analysis
3. **Summary Generation** - Parallel weekly and monthly aggregation

Each stage respects feature toggles for granular control.

## Major Features

### 1. Lifelog Fetching

Fetches conversation logs from Limitless API with smart pagination (stops when existing dates are found).

**Output:** `lifelogs/YYYY-MM-DD.md` - Organized by date with time-stamped entries

### 2. Daily Insights

Retrieves AI-generated summaries from Limitless chats API.

**Output:** `daily/YYYY-MM-DD.md` - Daily summary insights

### 3. Bee Transcription Processing

Processes raw Bee transcription files into structured insights using LLM.

**Setup:**
1. Create prompt file: `prompts/bee_daily.txt`
2. Place transcription files in `bee/` directory
3. Pipeline automatically detects and processes new files

**Output:** Appends "🐝 Bee Transcription Insights" section to daily insights

### 4. Weekly Summaries

Aggregates 7 consecutive days of insights into weekly reports.

**Setup:**
1. Create prompt file: `prompts/weekly_prompt.txt`
2. Enable with `CREATE_WEEKLY_SUMMARIES=true`

**Output:** `weekly/YYYY-MM-DD_to_YYYY-MM-DD-weekly.md`

### 5. Monthly Summaries

Generates monthly overview reports from all daily insights.

**Setup:**
1. Create prompt file: `prompts/monthly.txt`
2. Enable with `CREATE_MONTHLY_SUMMARIES=true`

**Output:** `monthly/YYYY-MM-monthly.md`

### 6. Journal Entry Formatting

Transforms raw journal transcripts into clean, well-structured markdown documents while preserving authentic voice.

**Setup:**
1. Create prompt file: `prompts/journal.txt`
2. Place journal transcripts in appropriate location
3. Enable with `PROCESS_JOURNAL_ENTRIES=true`

**Output:** `journal/YYYY-MM-DD-journal.md` - Formatted journal entries

**Features:**
- Preserves authentic voice and emotional truth
- Adds structure with markdown headers and formatting
- Cleans up filler words and transcription artifacts
- Organizes by themes: reflections, insights, achievements, concerns
- Maintains conversational, personal tone

**Note:** Journal monologues are automatically detected and excluded from therapy session analysis.

### 7. Therapy Session Detection

Automatically identifies therapy sessions in lifelogs using scoring algorithm.

**Setup:**
1. Create prompt file: `prompts/psycho_analysis.txt`
2. Configure detection parameters in `.env`
3. Enable with `PROCESS_THERAPY_SESSIONS=true`

**Output:** `psychologist/YYYY-MM-DD-psychologist.md` - Analyzed session transcripts

**Algorithm:** Scores conversations based on:
- Duration (30-75 minutes optimal)
- Timing (afternoon weighting)
- Keywords (therapy-related terms)
- Speaker patterns (back-and-forth dialogue)
- Penalties (journal entries, non-therapy indicators)

### 8. Speaker Identification

LLM-based speaker labeling system that identifies and replaces generic speaker labels with actual names.

**Features:**
- Configurable speaker profiles with voice characteristics
- Training examples for improved accuracy
- Batch processing with async support
- Backfill capability for existing files

**Documentation:**
- Quick start: [`supporting_docs/QUICKSTART_SPEAKER_IDENTIFICATION.md`](supporting_docs/QUICKSTART_SPEAKER_IDENTIFICATION.md)
- Backfilling existing files: [`supporting_docs/SPEAKER_BACKFILL_GUIDE.md`](supporting_docs/SPEAKER_BACKFILL_GUIDE.md)

**Configuration:**
- Enable/disable: `LABEL_SPEAKERS=true` in `.env`
- Reduces processing time and LLM costs when disabled

## Project Structure

```
daily_insights/
├── daily_insights/           # Main package
│   ├── api/                  # API clients (Limitless, OpenAI, Ollama)
│   ├── services/             # Business logic
│   │   ├── lifelog_service.py
│   │   ├── insights_service.py
│   │   ├── bee_service.py
│   │   ├── therapy_service.py
│   │   ├── monthly_service.py
│   │   └── speaker_service.py
│   ├── models/               # Data models
│   ├── utils/                # Utilities
│   ├── config.py             # Configuration management
│   └── main.py               # Pipeline entry point
├── prompts/                  # LLM prompt templates
├── supporting_docs/          # Additional documentation
├── .env.example              # Environment configuration template
└── requirements.txt          # Python dependencies
```

## Output Directories

All output directories are created automatically on first run:

- `lifelogs/` - Daily conversation transcripts
- `daily/` - Daily insights (Limitless + Bee combined)
- `weekly/` - Weekly summary reports
- `monthly/` - Monthly summary reports
- `psychologist/` - Therapy session analyses
- `journal/` - Journal entries
- `bee/` - Raw Bee transcription files (input)

## LLM Provider Configuration

See [`supporting_docs/LLM_PROVIDER_GUIDE.md`](supporting_docs/LLM_PROVIDER_GUIDE.md) for detailed setup instructions for OpenAI and Ollama.

**Quick Reference:**
- **OpenAI:** Fast, high quality, API costs
- **Ollama:** Free, runs locally, requires more resources

## Development

### Running Tests

```bash
# Run specific features only
FETCH_LIFELOGS=false \
FETCH_DAILY_INSIGHTS=false \
CREATE_WEEKLY_SUMMARIES=true \
python run_daily_insights.py
```

### Async vs Sync

Default mode is async for better performance. To use synchronous version:

```python
from daily_insights.main import main
main()  # Synchronous execution
```

## Troubleshooting

**Missing API Key Warnings:**
- Configure `LIMITLESS_API_KEY` in `.env`
- Set `OPENAI_API_KEY` if using OpenAI provider
- Disable validation: `SKIP_CONFIG_VALIDATION=true`

**No New Data:**
- Pipeline skips existing dates automatically
- Check date filtering in service logs
- Verify API key has proper permissions

**LLM Errors:**
- Verify LLM provider is running (Ollama) or API key is valid (OpenAI)
- Check model names match available models
- Review prompt file formatting

## License

[Your License Here]
