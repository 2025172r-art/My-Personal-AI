from __future__ import annotations

import csv
import io
from pathlib import Path

MAX_EXTRACTED_CHARS = 40_000


def extract_uploaded_file(filename: str, content: bytes) -> str:
    """Extract text from supported document formats; never execute uploaded content."""
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        text = content.decode("utf-8-sig", errors="replace")
    elif suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix == ".docx":
        from docx import Document

        document = Document(io.BytesIO(content))
        text = "\n".join(p.text for p in document.paragraphs)
        for table in document.tables:
            text += "\n" + "\n".join(
                " | ".join(cell.text for cell in row.cells) for row in table.rows
            )
    elif suffix == ".csv":
        decoded = content.decode("utf-8-sig", errors="replace")
        text = "\n".join(" | ".join(row) for row in csv.reader(io.StringIO(decoded)))
    elif suffix == ".xlsx":
        from openpyxl import load_workbook

        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        chunks: list[str] = []
        for sheet in workbook.worksheets:
            chunks.append(f"## シート: {sheet.title}")
            for row in sheet.iter_rows(values_only=True):
                chunks.append(
                    " | ".join("" if value is None else str(value) for value in row)
                )
        text = "\n".join(chunks)
    else:
        raise ValueError(
            "未対応のファイル形式です。PDF、DOCX、TXT、MD、CSV、XLSXを利用してください。"
        )

    text = text.strip()
    if not text:
        raise ValueError(
            "ファイルからテキストを抽出できませんでした。"
            "スキャン画像のみのPDFにはOCRが必要です。"
        )
    if len(text) > MAX_EXTRACTED_CHARS:
        text = text[:MAX_EXTRACTED_CHARS] + "\n\n[文字数上限に達したため、以降を省略しました]"
    return text
