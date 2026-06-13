"""Tests for StyleProfile union null-reset semantics and font_color inheritance."""

from __future__ import annotations

from docx_mcp.domain.style_profile import ParagraphStyleInfo, StyleProfile


class TestUnionNullSemantics:
    def test_union_master_replaces_entire_style_on_name_conflict(self) -> None:
        draft = StyleProfile(
            paragraph_styles=[
                ParagraphStyleInfo(
                    name="Heading 1",
                    bold=True,
                    font_color="365F91",
                    space_before_pt=24.0,
                ),
            ]
        )
        template = StyleProfile(
            paragraph_styles=[
                ParagraphStyleInfo(
                    name="Heading 1",
                    bold=None,
                    font_color=None,
                    space_before_pt=18.0,
                ),
            ]
        )

        merged = draft.union_with(template, master="other")

        heading = merged.get_paragraph_style("Heading 1")
        assert heading is not None
        assert heading.bold is None
        assert heading.font_color is None
        assert heading.space_before_pt == 18.0

    def test_union_preserves_slave_only_styles(self) -> None:
        draft = StyleProfile(
            paragraph_styles=[
                ParagraphStyleInfo(name="Heading 1", bold=True),
                ParagraphStyleInfo(name="macro", font_name="Courier New"),
            ]
        )
        template = StyleProfile(
            paragraph_styles=[ParagraphStyleInfo(name="Heading 1", bold=None)]
        )

        merged = draft.union_with(template, master="other")

        assert merged.get_paragraph_style("macro") is not None
        assert "macro" in merged.style_names()


class TestResolveInheritedFontColor:
    def test_resolve_inherited_font_color_from_base(self) -> None:
        profile = StyleProfile(
            paragraph_styles=[
                ParagraphStyleInfo(name="Normal", font_color="000000"),
                ParagraphStyleInfo(name="Heading 1", base_style="Normal", font_color=None),
            ]
        )

        resolved = profile.resolve_inherited()

        heading = resolved.get_paragraph_style("Heading 1")
        assert heading is not None
        assert heading.font_color == "000000"

    def test_resolve_inherited_font_color_override_wins(self) -> None:
        profile = StyleProfile(
            paragraph_styles=[
                ParagraphStyleInfo(name="Normal", font_color="000000"),
                ParagraphStyleInfo(name="Heading 1", base_style="Normal", font_color="365F91"),
            ]
        )

        resolved = profile.resolve_inherited()

        heading = resolved.get_paragraph_style("Heading 1")
        assert heading is not None
        assert heading.font_color == "365F91"

    def test_font_color_roundtrips_through_dict(self) -> None:
        info = ParagraphStyleInfo(name="Heading 1", font_color="365F91")
        restored = ParagraphStyleInfo.from_dict(info.to_dict())
        assert restored.font_color == "365F91"
