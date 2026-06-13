"""Tests for StyleMapper suggest_map and aliases."""

from __future__ import annotations

from docx_mcp.adapters.style_mapper import StyleMapper


class TestStyleMapperSuggestMap:
    def test_suggest_map_with_aliases(self) -> None:
        template = ["Normal", "Heading 1", "Heading 2", "ТЕКСТ", "КОД"]
        mapper = StyleMapper(template)
        usage = {
            "Normal": 32,
            "List Paragraph": 5,
            "Heading 1": 8,
            "macro": 1,
        }

        suggested, unmapped, heuristics = mapper.suggest_map(usage)

        assert suggested["List Paragraph"] == "ТЕКСТ"
        assert suggested["macro"] == "КОД"
        assert suggested["Normal"] == "ТЕКСТ"
        assert heuristics["Normal"] is True
        assert unmapped == []

    def test_suggest_map_exact_match(self) -> None:
        mapper = StyleMapper(["Normal", "Heading 1"])
        suggested, unmapped, _ = mapper.suggest_map({"Heading 1": 3})
        assert suggested["Heading 1"] == "Heading 1"
        assert unmapped == []

    def test_map_style_fallback_tracks_unmapped(self) -> None:
        mapper = StyleMapper(["Normal", "Heading 1"])
        assert mapper.map_style("Unknown Style") == "Normal"
        assert "Unknown Style" in mapper.unmapped_styles
