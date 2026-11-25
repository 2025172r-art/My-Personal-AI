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


def text_to_speech(client: Any, text: str) -> bytes:
    safe_text = text.strip()[:4000]
    if not safe_text:
        raise ValueError("読み上げる文章がありません。")
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="coral",
        input=safe_text,
        instructions="日本語で、落ち着いて聞き取りやすく話してください。",
        response_format="mp3",
    ) as response:
        return response.read()
