"""Tests for StyleExtractor font_color extraction (F-1 read path)."""

from __future__ import annotations

from tests.conftest import FORMAT_DOCX, PLAIN_DOCX, adapter  # noqa: F401


class TestExtractHeadingColor:
    def test_extract_heading_color_from_plain(self, adapter) -> None:
        document = adapter.open(PLAIN_DOCX)
        profile = adapter._style_extractor.extract(document)

        h1 = profile.get_paragraph_style("Heading 1")
        h2 = profile.get_paragraph_style("Heading 2")
        assert h1 is not None and h2 is not None
        assert h1.font_color == "365F91"
        assert h2.font_color == "4F81BD"

    def test_extract_heading_bold_from_plain(self, adapter) -> None:
        document = adapter.open(PLAIN_DOCX)
        profile = adapter._style_extractor.extract(document)

        h1 = profile.get_paragraph_style("Heading 1")
        h2 = profile.get_paragraph_style("Heading 2")
        assert h1 is not None and h2 is not None
        assert h1.bold is True
        assert h2.bold is True

    def test_extract_heading_color_from_format(self, adapter) -> None:
        document = adapter.open(FORMAT_DOCX)
        profile = adapter._style_extractor.extract(document)

        h1 = profile.get_paragraph_style("Heading 1")
        h2 = profile.get_paragraph_style("Heading 2")
        assert h1 is not None and h2 is not None
        assert h1.font_color is None
        assert h2.font_color is None

    def test_extract_heading_bold_from_format(self, adapter) -> None:
        document = adapter.open(FORMAT_DOCX)
        profile = adapter._style_extractor.extract(document)

        h1 = profile.get_paragraph_style("Heading 1")
        h2 = profile.get_paragraph_style("Heading 2")
        assert h1 is not None and h2 is not None
        assert h1.bold is True
        assert h2.bold is None

    def test_extract_heading_alignment_from_format(self, adapter) -> None:
        document = adapter.open(FORMAT_DOCX)
        profile = adapter._style_extractor.extract(document)

        h1 = profile.get_paragraph_style("Heading 1")
        text_style = profile.get_paragraph_style("ТЕКСТ")
        assert h1 is not None and text_style is not None
        assert h1.alignment == "center"
        assert text_style.alignment == "justify"

    def test_extract_heading_size_from_format(self, adapter) -> None:
        document = adapter.open(FORMAT_DOCX)
        profile = adapter._style_extractor.extract(document)

        h1 = profile.get_paragraph_style("Heading 1")
        h2 = profile.get_paragraph_style("Heading 2")
        assert h1 is not None and h2 is not None
        assert h1.font_size_pt == 14.0
        assert h2.font_size_pt == 14.0
