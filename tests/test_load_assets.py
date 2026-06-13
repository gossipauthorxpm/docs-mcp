"""Integration tests loading real fixture documents — useful for debugger inspection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from docx_mcp.adapters.docx_adapter import DocxAdapter
from docx_mcp.domain.models import DocumentModel, ParagraphBlock, TableBlock

ASSETS_DIR = Path(__file__).parent / "assets"
PLAIN_DOCX = ASSETS_DIR / "plain.docx"
FORMAT_DOCX = ASSETS_DIR / "format.docx"


@pytest.fixture
def adapter() -> DocxAdapter:
    return DocxAdapter()


class TestLoadAssetDocuments:
    def test_load_plain_docx(self, adapter: DocxAdapter) -> None:
        doc = adapter.read_document(PLAIN_DOCX)

        assert isinstance(doc, DocumentModel)
        assert doc.source_path == str(PLAIN_DOCX)
        assert len(doc.blocks) > 0
        assert len(doc.styles.paragraph_styles) > 0

        first = doc.blocks[0]
        assert isinstance(first, ParagraphBlock)
        assert first.style is not None
        assert first.style.name == "Heading 1"
        assert "ЛАБОРАТОРНАЯ РАБОТА" in first.text

        heading_style = doc.styles.get_paragraph_style("Heading 1")
        assert heading_style is not None
        assert heading_style.bold is True
        assert heading_style.font_size_pt == 14.0

        assert not any(isinstance(b, TableBlock) for b in doc.blocks)

    def test_load_format_docx(self, adapter: DocxAdapter) -> None:
        doc = adapter.read_document(FORMAT_DOCX)

        assert isinstance(doc, DocumentModel)
        assert doc.source_path == str(FORMAT_DOCX)
        assert len(doc.blocks) > 0
        assert len(doc.styles.paragraph_styles) > 0

        first = doc.blocks[0]
        assert isinstance(first, ParagraphBlock)
        assert first.style is not None
        assert first.style.name == "Heading 1"

        heading_style = doc.styles.get_paragraph_style("Heading 1")
        assert heading_style is not None
        assert heading_style.space_before_pt == 18.0
        assert heading_style.space_after_pt == 4.0

        normal_style = doc.styles.get_paragraph_style("Normal")
        assert normal_style is not None
        assert normal_style.font_name == "Times New Roman"
        assert normal_style.font_size_pt == 14.0

        table_blocks = [b for b in doc.blocks if isinstance(b, TableBlock)]
        assert len(table_blocks) >= 1

    def test_document_styles_match_inspect_styles(self, adapter: DocxAdapter) -> None:
        doc = adapter.read_document(FORMAT_DOCX)
        profile = adapter.inspect_styles(FORMAT_DOCX)

        assert doc.styles.style_names() == profile.style_names()
        assert doc.styles.section == profile.section

    def test_document_model_json_roundtrip(self, adapter: DocxAdapter) -> None:
        doc = adapter.read_document(FORMAT_DOCX)
        restored = DocumentModel.from_dict(json.loads(json.dumps(doc.to_dict())))

        assert restored.styles.style_names() == doc.styles.style_names()
        assert len(restored.blocks) == len(doc.blocks)
        heading = restored.styles.get_paragraph_style("Heading 1")
        assert heading is not None
        assert heading.space_before_pt == 18.0

    def test_both_documents_in_debugger(self, adapter: DocxAdapter) -> None:
        """Load both fixtures — set a breakpoint here to inspect domain objects."""
        plain_doc = adapter.read_document(PLAIN_DOCX)
        format_doc = adapter.read_document(FORMAT_DOCX)

        assert plain_doc.source_path != format_doc.source_path
        assert len(plain_doc.blocks) > 0
        assert len(format_doc.blocks) > 0
        assert len(plain_doc.styles.style_names()) > 0
        assert len(format_doc.styles.style_names()) > 0

        # doc.styles — full style catalog; blocks[].style — name reference only
        plain_heading = plain_doc.styles.get_paragraph_style("Heading 1")
        format_heading = format_doc.styles.get_paragraph_style("Heading 1")
        assert plain_heading is not None
        assert format_heading is not None
