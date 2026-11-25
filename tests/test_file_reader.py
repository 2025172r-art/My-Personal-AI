from tools.file_reader import extract_uploaded_file


def test_reads_utf8_text():
    result = extract_uploaded_file("note.txt", "こんにちは".encode("utf-8"))
    assert result == "こんにちは"


def test_rejects_unsupported_file():
    try:
        extract_uploaded_file("script.py", b"print('no')")
    except ValueError as exc:
        assert "未対応" in str(exc)
    else:
        raise AssertionError("Unsupported files should be rejected")
