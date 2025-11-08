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
WEEKLY_INSIGHTS_DIR = PROJECT_ROOT / os.getenv('WEEKLY_INSIGHTS_DIR', 'weekly')
MONTHLY_INSIGHTS_DIR = PROJECT_ROOT / os.getenv('MONTHLY_INSIGHTS_DIR', 'monthly')
BEE_DIR = PROJECT_ROOT / os.getenv('BEE_DIR', 'bee')
THERAPY_DIR = PROJECT_ROOT / os.getenv('THERAPY_DIR', 'psychologist')
THERAPY_MONTHLY_DIR = PROJECT_ROOT / os.getenv('THERAPY_MONTHLY_DIR', 'therapy_monthly')
JOURNAL_DIR = PROJECT_ROOT / os.getenv('JOURNAL_DIR', 'journal')
DOCTOR_DIR = PROJECT_ROOT / os.getenv('DOCTOR_DIR', 'doctor')

# ============================================================================
# Prompt File Paths
# ============================================================================

WEEKLY_INSIGHTS_PROMPT = PROJECT_ROOT / os.getenv('WEEKLY_INSIGHTS_PROMPT', 'prompts/weekly_prompt.txt')
MONTHLY_INSIGHTS_PROMPT = PROJECT_ROOT / os.getenv('MONTHLY_INSIGHTS_PROMPT', 'prompts/monthly.txt')
BEE_PROMPT_FILE = PROJECT_ROOT / os.getenv('BEE_PROMPT_FILE', 'prompts/bee_daily.txt')
THERAPY_PROMPT = PROJECT_ROOT / os.getenv('THERAPY_PROMPT', 'prompts/psycho_analysis.txt')
THERAPY_MONTHLY_PROMPT = PROJECT_ROOT / os.getenv('THERAPY_MONTHLY_PROMPT', 'prompts/therapy_monthly.txt')
DOCTOR_PROMPT = PROJECT_ROOT / os.getenv('DOCTOR_PROMPT', 'prompts/doctor_visit.txt')

# ============================================================================
# Therapy Detection Parameters (MVP Phase 0 + Enhancements)
# ============================================================================

# Phase 2.5: Speaker purity validation
# Comma-separated list of ONLY speakers allowed in therapy sessions
# Any conversation with speakers not in this list will be rejected
# Example: "Bruce,Larry,Unknown" or "John,Dr. Smith"
EXPECTED_SPEAKERS_THERAPY_SESSION = [
    k.strip()
    for k in os.getenv('EXPECTED_SPEAKERS_THERAPY_SESSION', '').split(',')
    if k.strip()
]

# Therapy keywords - comma-separated list of therapy-related words
# Example: "therapy,therapist,counseling"
THERAPY_KEYWORDS = [k.strip() for k in os.getenv('THERAPY_KEYWORDS', 'therapy,therapist').split(',') if k.strip()]

# Minimum number of therapy keywords required for detection (Phase 2 enhancement)
# Prevents false positives from single generic keyword matches
# Default: 2 (require multiple therapy-related terms)
THERAPY_KEYWORD_MIN = int(os.getenv('THERAPY_KEYWORD_MIN', '2'))

# Minimum duration (in minutes) for a conversation to be considered therapy
# Default: 30 minutes
THERAPY_MIN_DURATION = int(os.getenv('THERAPY_MIN_DURATION', '30'))

# Maximum duration (in minutes) for a conversation to be considered therapy
# Prevents false positives from very long conversations spanning multiple activities
# Default: 120 minutes (2 hours) - set to 0 to disable
THERAPY_MAX_DURATION = int(os.getenv('THERAPY_MAX_DURATION', '120'))

# Exclusion keywords - reject conversations containing any of these terms
# Prevents false positives from administrative, political, or social contexts
# Comma-separated list of keywords that indicate non-therapy conversations
THERAPY_EXCLUSION_KEYWORDS = [
    kw.strip() for kw in os.getenv(
        'THERAPY_EXCLUSION_KEYWORDS',
        'eligibility,interview,application,appeal,claim,trump,election,protest,voting,airport,customs,border'
    ).split(',') if kw.strip()
]

# ============================================================================
# Doctor Visit Detection Parameters
# ============================================================================

# Expected speakers for doctor visits - comma-separated list
# Example: "Bruce,Unknown" or "John,Dr. Smith"
EXPECTED_SPEAKERS_DOCTOR_VISIT = [
    k.strip()
    for k in os.getenv('EXPECTED_SPEAKERS_DOCTOR_VISIT', 'Bruce,Unknown').split(',')
    if k.strip()
]

# Doctor visit keywords - comma-separated list of medical-related words
DOCTOR_KEYWORDS = [
    k.strip()
    for k in os.getenv(
        'DOCTOR_KEYWORDS',
        'doctor,physician,specialist,appointment,checkup,prescription,symptoms,diagnosis,medical,clinic,hospital'
    ).split(',')
    if k.strip()
]

# Minimum number of doctor keywords required for detection
# Prevents false positives from single generic keyword matches
DOCTOR_KEYWORD_MIN = int(os.getenv('DOCTOR_KEYWORD_MIN', '2'))

# Minimum duration (in minutes) for a conversation to be considered a doctor visit
# Default: 10 minutes
DOCTOR_MIN_DURATION = int(os.getenv('DOCTOR_MIN_DURATION', '10'))

# Maximum duration (in minutes) for a conversation to be considered a doctor visit
# Prevents false positives from very long conversations
# Default: 90 minutes - set to 0 to disable
DOCTOR_MAX_DURATION = int(os.getenv('DOCTOR_MAX_DURATION', '90'))

# Exclusion keywords - reject conversations containing any of these terms
# Prevents false positives from mental health/psychiatry visits
DOCTOR_EXCLUSION_KEYWORDS = [
    kw.strip() for kw in os.getenv(
        'DOCTOR_EXCLUSION_KEYWORDS',
        'psychiatrist,therapy,therapist,counseling,psychologist,mental health'
    ).split(',') if kw.strip()
]

# ============================================================================
# Doctor Visit Confidence Scoring Weights
# ============================================================================

# Weight for examination-specific keywords (physical exam, diagnostic terms)
# Positive indicator of actual doctor visit vs. casual health discussion
DOCTOR_CONFIDENCE_WEIGHT_EXAMINATION = float(os.getenv('DOCTOR_CONFIDENCE_WEIGHT_EXAMINATION', '0.3'))

# Weight for health metrics keywords (weight, blood pressure, glucose)
# Negative indicator - often appears in personal logging, not actual visits
DOCTOR_CONFIDENCE_WEIGHT_HEALTH_METRICS = float(os.getenv('DOCTOR_CONFIDENCE_WEIGHT_HEALTH_METRICS', '-0.2'))

# Weight for discussion pattern keywords (e.g., "doctor said", "appointment with")
# Negative indicator - discussing visits rather than being in a visit
DOCTOR_CONFIDENCE_WEIGHT_DISCUSSION_PATTERN = float(os.getenv('DOCTOR_CONFIDENCE_WEIGHT_DISCUSSION_PATTERN', '-0.3'))

# Weight for bidirectional Q&A patterns (patient and provider both asking/answering)
# Positive indicator of actual clinical conversation vs. one-way advice
DOCTOR_CONFIDENCE_WEIGHT_BIDIRECTIONAL_QA = float(os.getenv('DOCTOR_CONFIDENCE_WEIGHT_BIDIRECTIONAL_QA', '0.3'))

# Weight for duration in optimal range (sweet spot based on DOCTOR_MIN_DURATION and DOCTOR_MAX_DURATION)
# Positive indicator when duration is in typical doctor visit range
DOCTOR_CONFIDENCE_WEIGHT_DURATION_OPTIMAL = float(os.getenv('DOCTOR_CONFIDENCE_WEIGHT_DURATION_OPTIMAL', '0.2'))

# ============================================================================
# Conversation Grouping (Used by multiple features)
# ============================================================================

# Maximum time gap (in minutes) between messages to group them as same conversation
CONVERSATION_GAP_MINUTES = int(os.getenv('CONVERSATION_GAP_MINUTES', '15'))

# ============================================================================
# Journal Detection Parameters
# ============================================================================

# Minimum messages after "journal" keyword for sustained content
JOURNAL_MIN_MESSAGES = int(os.getenv('JOURNAL_MIN_MESSAGES', '5'))

# Minimum word count for journal session
JOURNAL_MIN_WORDS = int(os.getenv('JOURNAL_MIN_WORDS', '100'))

# Valid speaker labels for journal entries
JOURNAL_VALID_SPEAKERS = [k.strip() for k in os.getenv('JOURNAL_VALID_SPEAKERS', 'Bruce,Unknown').split(',') if k.strip()]

# End marker phrases for journal completion detection
JOURNAL_END_MARKERS = [k.strip() for k in os.getenv('JOURNAL_END_MARKERS', 'end journal,journal end').split(',') if k.strip()]

# ============================================================================
# Monthly Summary Parameters
# ============================================================================

# Minimum weekly summaries required to generate a monthly summary
# Default: 4 (a complete month typically has 4-5 weeks)
# Set to 3 or lower to generate summaries for months with fewer weeks
MONTHLY_MIN_WEEKS = int(os.getenv('MONTHLY_MIN_WEEKS', '4'))

# ============================================================================
# Therapy Monthly Summary Parameters
# ============================================================================

# Minimum therapy sessions required to generate a monthly summary
# Default: 1 (generate summary even with a single session)
THERAPY_MONTHLY_MIN_SESSIONS = int(os.getenv('THERAPY_MONTHLY_MIN_SESSIONS', '1'))

# ============================================================================
# Utility Functions (Helper functions used by configuration)
# ============================================================================


def _parse_bool(value: str, default: bool = True) -> bool:
    """
    Parse boolean value from environment variable.

    Accepts: true/false, yes/no, 1/0, on/off (case-insensitive)
    """
    if not value:
        return default
    return value.lower() in ('true', 'yes', '1', 'on')


# ============================================================================
# Logging Configuration
# ============================================================================

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Enable console logging
LOG_TO_CONSOLE = _parse_bool(os.getenv('LOG_TO_CONSOLE', 'true'))

# Enable file logging
LOG_TO_FILE = _parse_bool(os.getenv('LOG_TO_FILE', 'true'))

# Log file directory
LOG_DIR = PROJECT_ROOT / os.getenv('LOG_DIR', 'logs')

# Log file name
LOG_FILE = LOG_DIR / os.getenv('LOG_FILE', 'daily_insights.log')

# Log rotation settings
LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', '10485760'))  # 10MB default
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))  # Keep 5 files


# ============================================================================
# Feature Toggles
# ============================================================================

# Pipeline feature flags
FETCH_LIFELOGS = _parse_bool(os.getenv('FETCH_LIFELOGS', 'true'))
FETCH_DAILY_INSIGHTS = _parse_bool(os.getenv('FETCH_DAILY_INSIGHTS', 'true'))
PROCESS_BEE_TRANSCRIPTIONS = _parse_bool(os.getenv('PROCESS_BEE_TRANSCRIPTIONS', 'true'))
PROCESS_JOURNAL_ENTRIES = _parse_bool(os.getenv('PROCESS_JOURNAL_ENTRIES', 'true'))
PROCESS_THERAPY_SESSIONS = _parse_bool(os.getenv('PROCESS_THERAPY_SESSIONS', 'true'))
PROCESS_DOCTOR_VISITS = _parse_bool(os.getenv('PROCESS_DOCTOR_VISITS', 'true'))
CREATE_WEEKLY_SUMMARIES = _parse_bool(os.getenv('CREATE_WEEKLY_SUMMARIES', 'true'))
CREATE_MONTHLY_SUMMARIES = _parse_bool(os.getenv('CREATE_MONTHLY_SUMMARIES', 'true'))
CREATE_THERAPY_MONTHLY_SUMMARIES = _parse_bool(os.getenv('CREATE_THERAPY_MONTHLY_SUMMARIES', 'true'))
LABEL_SPEAKERS = _parse_bool(os.getenv('LABEL_SPEAKERS', 'true'))

# ============================================================================
# Utility Functions
# ============================================================================

def ensure_directories():
    """Create all required directories if they don't exist."""
    directories = [
        LIFELOGS_DIR,
        INSIGHTS_DIR,
        WEEKLY_INSIGHTS_DIR,
        MONTHLY_INSIGHTS_DIR,
        BEE_DIR,
        THERAPY_DIR,
        THERAPY_MONTHLY_DIR,
        JOURNAL_DIR,
        DOCTOR_DIR,
        LOG_DIR  # Add logs directory
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
