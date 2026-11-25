from __future__ import annotations

from typing import Any


def speech_to_text(client: Any, audio_bytes: bytes) -> str:
    if not audio_bytes:
        raise ValueError("音声データが空です。")
    result = client.audio.transcriptions.create(
        model="gpt-transcribe",
        file=("recording.wav", audio_bytes, "audio/wav"),
    )
    return str(result.text).strip()
