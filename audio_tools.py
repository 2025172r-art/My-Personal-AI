"""Audio helpers for the no-provider-API edition.

Use ChromeOS built-in dictation to enter text. Streamlit uses the browser's
speechSynthesis capability for optional answer read-aloud.
"""


def speech_to_text(*_args, **_kwargs) -> str:
    raise RuntimeError(
        "外部の音声認識APIは使用しません。Chromebookの音声入力でテキストを入力してください。"
    )
