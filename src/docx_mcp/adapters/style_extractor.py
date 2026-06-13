"""Extract document-level style catalog from python-docx documents."""

from __future__ import annotations

from docx.document import Document as DocxDocument
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

from docx_mcp.domain.style_profile import ParagraphStyleInfo, SectionSetup, StyleProfile

_ALIGNMENT_NAMES: dict[int | None, str | None] = {
    WD_PARAGRAPH_ALIGNMENT.LEFT: "left",
    WD_PARAGRAPH_ALIGNMENT.CENTER: "center",
    WD_PARAGRAPH_ALIGNMENT.RIGHT: "right",
    WD_PARAGRAPH_ALIGNMENT.JUSTIFY: "justify",
    WD_PARAGRAPH_ALIGNMENT.DISTRIBUTE: "distribute",
    None: None,
}


class StyleExtractor:
    def extract(self, document: DocxDocument, source_path: str | None = None) -> StyleProfile:
        paragraph_styles: list[ParagraphStyleInfo] = []
        for style in document.styles:
            if not _is_paragraph_style(style):
                continue
            paragraph_styles.append(_extract_paragraph_style(style))

        return StyleProfile(
            paragraph_styles=paragraph_styles,
            section=_extract_section_setup(document),
            source_path=source_path,
        )


def _extract_paragraph_style(style: object) -> ParagraphStyleInfo:
    font = style.font  # type: ignore[attr-defined]
    pf = style.paragraph_format  # type: ignore[attr-defined]
    base = style.base_style.name if style.base_style else None  # type: ignore[attr-defined]

    return ParagraphStyleInfo(
        name=style.name,  # type: ignore[attr-defined]
        base_style=base,
        font_name=font.name,
        font_size_pt=_to_pt(font.size),
        bold=font.bold,
        italic=font.italic,
        alignment=_alignment_name(pf.alignment),
        line_spacing=_line_spacing(pf.line_spacing),
        space_before_pt=_to_pt(pf.space_before),
        space_after_pt=_to_pt(pf.space_after),
        left_indent_cm=_to_cm(pf.left_indent),
        right_indent_cm=_to_cm(pf.right_indent),
        first_line_indent_cm=_to_cm(pf.first_line_indent),
    )


def _extract_section_setup(document: DocxDocument) -> SectionSetup | None:
    if not document.sections:
        return None
    section = document.sections[0]
    return SectionSetup(
        page_width_cm=_to_cm(section.page_width),
        page_height_cm=_to_cm(section.page_height),
        left_margin_cm=_to_cm(section.left_margin),
        right_margin_cm=_to_cm(section.right_margin),
        top_margin_cm=_to_cm(section.top_margin),
        bottom_margin_cm=_to_cm(section.bottom_margin),
    )


def _is_paragraph_style(style: object) -> bool:
    style_type = getattr(style, "type", None)
    if style_type is None:
        return True
    try:
        return style_type == WD_STYLE_TYPE.PARAGRAPH
    except (AttributeError, ValueError):
        return style_type == 1


def _alignment_name(alignment: object) -> str | None:
    if alignment is None:
        return None
    return _ALIGNMENT_NAMES.get(alignment)  # type: ignore[arg-type]


def _line_spacing(line_spacing: object) -> float | None:
    if line_spacing is None:
        return None
    if isinstance(line_spacing, (int, float)):
        return float(line_spacing)
    pt = getattr(line_spacing, "pt", None)
    return float(pt) if pt is not None else None


def _to_pt(length: object) -> float | None:
    if length is None:
        return None
    pt = getattr(length, "pt", None)
    return float(pt) if pt is not None else None


def _to_cm(length: object) -> float | None:
    if length is None:
        return None
    cm = getattr(length, "cm", None)
    return float(cm) if cm is not None else None
