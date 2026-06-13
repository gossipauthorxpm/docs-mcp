"""Extract document-level style catalog from python-docx documents."""

from __future__ import annotations

from docx.document import Document as DocxDocument
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn

from docx_mcp.domain.style_profile import ParagraphStyleInfo, SectionSetup, StyleProfile

_ALIGNMENT_NAMES: dict[int | None, str | None] = {
    WD_PARAGRAPH_ALIGNMENT.LEFT: "left",
    WD_PARAGRAPH_ALIGNMENT.CENTER: "center",
    WD_PARAGRAPH_ALIGNMENT.RIGHT: "right",
    WD_PARAGRAPH_ALIGNMENT.JUSTIFY: "justify",
    WD_PARAGRAPH_ALIGNMENT.DISTRIBUTE: "distribute",
    None: None,
}

# OOXML jc values; Word 2013+ uses start/end instead of left/right.
_JC_XML_TO_NAME: dict[str, str] = {
    "left": "left",
    "center": "center",
    "right": "right",
    "both": "justify",
    "justify": "justify",
    "distribute": "distribute",
    "start": "left",
    "end": "right",
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
        font_name=_font_name(font),
        font_size_pt=_font_size_pt(font),
        font_color=_font_color(font),
        bold=font.bold,
        italic=font.italic,
        alignment=_extract_alignment(pf),
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


def _font_name(font: object) -> str | None:
    name = getattr(font, "name", None)
    if name:
        return name
    r_pr = _style_r_pr(font)
    if r_pr is None:
        return None
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        return None
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        value = r_fonts.get(qn(attr))
        if value:
            return value
    return None


def _font_size_pt(font: object) -> float | None:
    size_pt = _to_pt(getattr(font, "size", None))
    if size_pt is not None:
        return size_pt
    r_pr = _style_r_pr(font)
    if r_pr is None:
        return None
    sz_cs = r_pr.find(qn("w:szCs"))
    if sz_cs is None:
        return None
    half_points = sz_cs.get(qn("w:val"))
    if half_points is None:
        return None
    return int(half_points) / 2.0


def _style_r_pr(font: object) -> object | None:
    element = getattr(font, "_element", None)
    if element is None:
        return None
    return getattr(element, "rPr", None)


def _font_color(font: object) -> str | None:
    color = getattr(font, "color", None)
    if color is None:
        return None
    try:
        rgb = color.rgb
    except (AttributeError, ValueError):
        return None
    return str(rgb) if rgb is not None else None


def _extract_alignment(pf: object) -> str | None:
    try:
        api_value = pf.alignment  # type: ignore[attr-defined]
    except ValueError:
        api_value = None
    if api_value is not None:
        return _alignment_name(api_value)
    element = getattr(pf, "_element", None)
    return _alignment_from_p_pr(element)


def _alignment_from_p_pr(p_pr: object | None) -> str | None:
    if p_pr is None:
        return None
    jc = p_pr.find(qn("w:jc"))  # type: ignore[attr-defined]
    if jc is None:
        return None
    xml_value = jc.get(qn("w:val"))
    if xml_value is None:
        return None
    return _JC_XML_TO_NAME.get(xml_value)


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
