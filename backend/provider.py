"""One Portkey-backed model configuration shared by every agent."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[1]
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
MODEL_ID = "gpt-6-luna"

# Prefer a project-local .env so a standalone clone works; retain the workspace
# root fallback used by the original homework checkout.
load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(REPOSITORY_ROOT / ".env", override=False)


class ProviderConfigurationError(RuntimeError):
    """Raised when the required Portkey credential is missing."""


def create_agent_model() -> OpenAIResponsesModel:
    """Build the required model; there is deliberately no alternate provider."""
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise ProviderConfigurationError(
            "PORTKEY_API_KEY is missing from the root .env or process environment."
        )
    provider = OpenAIProvider(api_key=api_key, base_url=PORTKEY_BASE_URL)
    return OpenAIResponsesModel(MODEL_ID, provider=provider)
