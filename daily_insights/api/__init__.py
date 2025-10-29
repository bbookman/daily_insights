"""API client modules for external services."""

from daily_insights.api.llm_client import (
    generate_clinical_notes,
    generate_summary
)
from daily_insights.api.ollama_client import (
    generate_summary as ollama_generate_summary,
    generate_with_chat as ollama_generate_chat
)

__all__ = [
    "generate_clinical_notes",
    "generate_summary",
    "ollama_generate_summary",
    "ollama_generate_chat"
]
