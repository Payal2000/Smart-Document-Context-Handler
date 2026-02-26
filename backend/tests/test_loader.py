"""Tests for document loader."""
import pytest
from app.core.document_loader import load_document


def test_load_plain_text():
    content = "Hello world. This is a test document."
    doc = load_document(content.encode("utf-8"), "test.txt")
    assert doc.filename == "test.txt"
    assert "Hello world" in doc.raw_text
    assert doc.file_size == len(content.encode("utf-8"))


def test_load_markdown():
    content = "# Title\n\nSome paragraph text here.\n\n## Section 2\nMore content."
    doc = load_document(content.encode("utf-8"), "readme.md")
    assert "Title" in doc.raw_text


def test_load_latin1_text():
    content = "Caf\xe9 au lait"  # é in latin-1
    doc = load_document(content.encode("latin-1"), "file.txt")
    assert "Caf" in doc.raw_text


def test_unsupported_extension():
    with pytest.raises(ValueError, match="Unsupported file type"):
        load_document(b"data", "file.pptx")


def test_load_csv():
    csv_content = "name,age,city\nAlice,30,NYC\nBob,25,LA\n"
    doc = load_document(csv_content.encode("utf-8"), "data.csv")
    assert doc.row_count == 2
    assert "Alice" in doc.raw_text


def test_load_empty_text():
    doc = load_document(b"   ", "empty.txt")
    assert doc.raw_text.strip() == ""
