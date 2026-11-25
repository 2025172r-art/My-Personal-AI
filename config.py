from __future__ import annotations

import os
from typing import Any


def get_setting(name: str, default: Any = None) -> Any:
    """Read non-AI application settings from environment or Streamlit Secrets."""
    value = os.getenv(name)
    if value not in (None, ""):
        return value
    try:
        import streamlit as st
        value = st.secrets.get(name, default)
        return value if value not in (None, "") else default
    except Exception:
        return default
