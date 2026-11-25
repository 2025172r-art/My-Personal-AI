from __future__ import annotations

import os
from typing import Any


def get_setting(name: str, default: Any = None) -> Any:
    """Read a setting from environment variables first, then Streamlit Secrets."""
    value = os.getenv(name)
    if value not in (None, ""):
        return value
    try:
        import streamlit as st
        value = st.secrets.get(name, default)
        return value if value not in (None, "") else default
    except Exception:
        return default


def openai_api_key() -> str | None:
    value = get_setting("OPENAI_API_KEY")
    return str(value).strip() if value else None


def model_name() -> str:
    return str(get_setting("OPENAI_MODEL", "gpt-6.2-sol")).strip()
