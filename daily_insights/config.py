"""Configuration management using environment variables."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / '.env', override=True)

# ============================================================================
# API Configuration
# ============================================================================

# Limitless API
API_KEY = os.getenv('LIMITLESS_API_KEY', '')
CHATS_API_BASE = os.getenv('LIMITLESS_CHATS_API_BASE', 'https://api.limitless.ai/v1/chats')
LIFELOGS_API_BASE = os.getenv('LIMITLESS_LIFELOGS_API_BASE', 'https://api.limitless.ai/v1/lifelogs')

# LLM Provider Configuration
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'openai')

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')

# Ollama Configuration
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2')

# ============================================================================
# Directory Paths
# ============================================================================

LIFELOGS_DIR = PROJECT_ROOT / os.getenv('LIFELOGS_DIR', 'lifelogs')
INSIGHTS_DIR = PROJECT_ROOT / os.getenv('INSIGHTS_DIR', 'daily')
WEEKLY_DIR = PROJECT_ROOT / os.getenv('WEEKLY_DIR', 'weekly')
MONTHLY_DIR = PROJECT_ROOT / os.getenv('MONTHLY_DIR', 'monthly')
BEE_DIR = PROJECT_ROOT / os.getenv('BEE_DIR', 'bee')
PSYCHOLOGIST_DIR = PROJECT_ROOT / os.getenv('PSYCHOLOGIST_DIR', 'psychologist')
JOURNAL_DIR = PROJECT_ROOT / os.getenv('JOURNAL_DIR', 'journal')

# ============================================================================
# Prompt File Paths
# ============================================================================

WEEKLY_PROMPT_FILE = PROJECT_ROOT / os.getenv('WEEKLY_PROMPT_FILE', 'prompts/weekly_prompt.txt')
MONTHLY_PROMPT_FILE = PROJECT_ROOT / os.getenv('MONTHLY_PROMPT_FILE', 'prompts/monthly.txt')
BEE_PROMPT_FILE = PROJECT_ROOT / os.getenv('BEE_PROMPT_FILE', 'prompts/bee_daily.txt')
PSYCHOLOGIST_PROMPT_FILE = PROJECT_ROOT / os.getenv('PSYCHOLOGIST_PROMPT_FILE', 'prompts/psycho_analysis.txt')

# ============================================================================
# Therapy Detection Parameters
# ============================================================================

# Keywords for therapy session detection
THERAPY_KEYWORDS = [k.strip() for k in os.getenv('THERAPY_KEYWORDS', '').split(',') if k.strip()]
NON_THERAPY_KEYWORDS = [k.strip() for k in os.getenv('NON_THERAPY_KEYWORDS', '').split(',') if k.strip()]

# Conversation grouping
CONVERSATION_GAP_MINUTES = int(os.getenv('CONVERSATION_GAP_MINUTES', '15'))

# Scoring parameters for therapy detection
SCORE_DURATION_MATCH = int(os.getenv('SCORE_DURATION_MATCH', '30'))
SCORE_AFTERNOON = int(os.getenv('SCORE_AFTERNOON', '10'))
SCORE_KEYWORD = int(os.getenv('SCORE_KEYWORD', '15'))
SCORE_SPEAKER_NAMES = int(os.getenv('SCORE_SPEAKER_NAMES', '20'))
SCORE_BACK_AND_FORTH = int(os.getenv('SCORE_BACK_AND_FORTH', '15'))

# Penalty parameters for therapy detection
PENALTY_TOO_MANY_SPEAKERS = int(os.getenv('PENALTY_TOO_MANY_SPEAKERS', '-20'))
PENALTY_TOO_LONG = int(os.getenv('PENALTY_TOO_LONG', '-15'))
PENALTY_TOO_SHORT = int(os.getenv('PENALTY_TOO_SHORT', '-20'))
PENALTY_TOO_MANY_MESSAGES = int(os.getenv('PENALTY_TOO_MANY_MESSAGES', '-10'))
PENALTY_JOURNAL = int(os.getenv('PENALTY_JOURNAL', '-30'))
PENALTY_NON_THERAPY = int(os.getenv('PENALTY_NON_THERAPY', '-25'))

# Confidence threshold for therapy session detection
CONFIDENCE_THRESHOLD = int(os.getenv('CONFIDENCE_THRESHOLD', '50'))

# Therapy session duration thresholds (in minutes)
MAX_DURATION = int(os.getenv('MAX_DURATION', '75'))
MIN_DURATION = int(os.getenv('MIN_DURATION', '30'))

# Message count thresholds for therapy sessions
MIN_MESSAGES = int(os.getenv('MIN_MESSAGES', '8'))
MAX_MESSAGES = int(os.getenv('MAX_MESSAGES', '100'))

# Maximum number of speakers in a therapy session
MAX_SPEAKERS = int(os.getenv('MAX_SPEAKERS', '3'))

# ============================================================================
# Utility Functions
# ============================================================================

def ensure_directories():
    """Create all required directories if they don't exist."""
    directories = [
        LIFELOGS_DIR,
        INSIGHTS_DIR,
        WEEKLY_DIR,
        MONTHLY_DIR,
        BEE_DIR,
        PSYCHOLOGIST_DIR,
        JOURNAL_DIR
    ]

    for dir_path in directories:
        dir_path.mkdir(parents=True, exist_ok=True)

    # Also ensure prompt directory exists
    prompts_dir = PROJECT_ROOT / 'prompts'
    prompts_dir.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Validation (Optional - warns about missing critical config)
# ============================================================================

def validate_config():
    """Validate that required configuration is present."""
    warnings = []

    if not API_KEY:
        warnings.append("LIMITLESS_API_KEY is not set")

    if LLM_PROVIDER == 'openai' and not OPENAI_API_KEY:
        warnings.append("OPENAI_API_KEY is not set (required when LLM_PROVIDER=openai)")

    if warnings:
        print("⚠️  Configuration warnings:")
        for warning in warnings:
            print(f"  - {warning}")
        print("  Set these values in your .env file\n")


# Run validation on import (can be disabled if needed)
if os.getenv('SKIP_CONFIG_VALIDATION', '').lower() != 'true':
    validate_config()
