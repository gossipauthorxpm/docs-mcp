"""Apply domain StyleProfile definitions to python-docx documents."""

from __future__ import annotations

from docx.document import Document as DocxDocument
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from docx_mcp.adapters.style_extractor import _extract_paragraph_style, _is_paragraph_style
from docx_mcp.domain.style_profile import ParagraphStyleInfo, SectionSetup, StyleProfile

_ALIGNMENT_FROM_NAME: dict[str, WD_PARAGRAPH_ALIGNMENT] = {
    "left": WD_PARAGRAPH_ALIGNMENT.LEFT,
    "center": WD_PARAGRAPH_ALIGNMENT.CENTER,
    "right": WD_PARAGRAPH_ALIGNMENT.RIGHT,
    "justify": WD_PARAGRAPH_ALIGNMENT.JUSTIFY,
    "distribute": WD_PARAGRAPH_ALIGNMENT.DISTRIBUTE,
}


class StyleMigrator:
    def apply(self, document: DocxDocument, profile: StyleProfile) -> tuple[int, int, int]:
        added = 0
        updated = 0
        unchanged = 0

        resolved_profile = profile.resolve_inherited()

        if resolved_profile.section is not None:
            self._apply_section(document, resolved_profile.section)

        existing_names = {
            style.name for style in document.styles if _is_paragraph_style(style)
        }

        for style_info in resolved_profile.paragraph_styles:
            if style_info.name in existing_names:
                docx_style = document.styles[style_info.name]
                current = _extract_paragraph_style(docx_style)
                if current.to_dict() != style_info.to_dict():
                    self._apply_paragraph_style(docx_style, style_info)
                    updated += 1
                else:
                    unchanged += 1
            else:
                docx_style = document.styles.add_style(
                    style_info.name,
                    WD_STYLE_TYPE.PARAGRAPH,
                )
                if style_info.base_style:
                    try:
                        docx_style.base_style = document.styles[style_info.base_style]
                    except KeyError:
                        pass
                self._apply_paragraph_style(docx_style, style_info)
                added += 1

        return added, updated, unchanged

    def _apply_section(self, document: DocxDocument, section_setup: SectionSetup) -> None:
        if not document.sections:
            return
        section = document.sections[0]
        if section_setup.page_width_cm is not None:
            section.page_width = Cm(section_setup.page_width_cm)
        if section_setup.page_height_cm is not None:
            section.page_height = Cm(section_setup.page_height_cm)
        if section_setup.left_margin_cm is not None:
            section.left_margin = Cm(section_setup.left_margin_cm)
        if section_setup.right_margin_cm is not None:
            section.right_margin = Cm(section_setup.right_margin_cm)
        if section_setup.top_margin_cm is not None:
            section.top_margin = Cm(section_setup.top_margin_cm)
        if section_setup.bottom_margin_cm is not None:
            section.bottom_margin = Cm(section_setup.bottom_margin_cm)

    def _apply_paragraph_style(self, style: object, info: ParagraphStyleInfo) -> None:
        font = style.font  # type: ignore[attr-defined]
        if info.font_name is not None:
            font.name = info.font_name
        if info.font_size_pt is not None:
            font.size = Pt(info.font_size_pt)
        # bold/italic/color use null = explicit reset: clear draft theme overrides
        font.bold = info.bold
        font.italic = info.italic
        if info.font_color is not None:
            font.color.rgb = RGBColor.from_string(info.font_color)
        else:
            _clear_font_color(font)

        pf = style.paragraph_format  # type: ignore[attr-defined]
        if info.alignment is not None:
            pf.alignment = _ALIGNMENT_FROM_NAME.get(info.alignment)
        if info.line_spacing is not None:
            pf.line_spacing = info.line_spacing
        if info.space_before_pt is not None:
            pf.space_before = Pt(info.space_before_pt)
        if info.space_after_pt is not None:
            pf.space_after = Pt(info.space_after_pt)
        if info.left_indent_cm is not None:
            pf.left_indent = Cm(info.left_indent_cm)
        if info.right_indent_cm is not None:
            pf.right_indent = Cm(info.right_indent_cm)
        if info.first_line_indent_cm is not None:
            pf.first_line_indent = Cm(info.first_line_indent_cm)


def _clear_font_color(font: object) -> None:
    rPr = font.element.find(qn("w:rPr"))  # type: ignore[attr-defined]
    if rPr is None:
        return
    color = rPr.find(qn("w:color"))
    if color is not None:
        rPr.remove(color)
