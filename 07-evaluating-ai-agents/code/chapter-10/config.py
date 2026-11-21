"""Read local credentials without putting them in a scenario or command line."""

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    cloudflare_account_id: str
    cloudflare_api_token: str
    jev_model: str = ""


def load_settings(require_jev=False):
    load_dotenv(Path(__file__).parent / ".env", override=False)
    openai_api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    openai_model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini").strip()
    cloudflare_account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    cloudflare_api_token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    jev_model = os.environ.get("JEV_MODEL", "").strip()
    if require_jev and not re.fullmatch(r"@?[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)+", jev_model):
        raise ValueError("Set JEV_MODEL in .env")
    if not openai_api_key:
        raise ValueError("Set OPENAI_API_KEY in the chapter-08 .env file")
    if not openai_model:
        raise ValueError("Set OPENAI_MODEL in the chapter-08 .env file")
    if require_jev and (
        not re.fullmatch(r"[0-9a-fA-F]{32}", cloudflare_account_id)
        or not cloudflare_api_token
    ):
        raise ValueError("Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN in .env")
    return Settings(
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        cloudflare_account_id=cloudflare_account_id,
        cloudflare_api_token=cloudflare_api_token,
        jev_model=jev_model,
    )