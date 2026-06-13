"""Tests for StyleMigrator."""

from __future__ import annotations

import pytest

from docx_mcp.adapters.style_migrator import StyleMigrator
from docx_mcp.domain.style_profile import ParagraphStyleInfo, SectionSetup, StyleProfile
from tests.conftest import FORMAT_DOCX, PLAIN_DOCX, assert_paragraph_style_field, assert_styles_equal, adapter  # noqa: F401


class TestStyleMigrator:
    def test_apply_updates_existing_and_adds_new(self, adapter) -> None:
        document = adapter.open(PLAIN_DOCX)
        existing = adapter._style_extractor.extract(document)

        incoming = StyleProfile(
            paragraph_styles=[
                ParagraphStyleInfo(
                    name="Heading 1",
                    space_before_pt=18.0,
                    space_after_pt=4.0,
                    bold=True,
                    font_size_pt=14.0,
                ),
                ParagraphStyleInfo(name="КОД", font_name="Courier New"),
            ],
            section=SectionSetup(left_margin_cm=2.5),
        )
        merged = existing.union_with(incoming, master="other")

        migrator = StyleMigrator()
        added, updated, unchanged = migrator.apply(document, merged)

        assert added >= 1
        assert updated >= 1
        assert unchanged >= 0

        result = adapter._style_extractor.extract(document)
        assert_paragraph_style_field(result, "Heading 1", space_before_pt=18.0)
        assert result.get_paragraph_style("КОД") is not None
        assert result.section is not None
        assert result.section.left_margin_cm == pytest.approx(2.5, rel=1e-3)

    def test_apply_unchanged_when_definitions_match(self, adapter) -> None:
        document = adapter.open(PLAIN_DOCX)
        profile = adapter._style_extractor.extract(document).resolve_inherited()

        migrator = StyleMigrator()
        migrator.apply(document, profile)

        result = adapter._style_extractor.extract(document).resolve_inherited()
        assert_styles_equal(result, profile)
