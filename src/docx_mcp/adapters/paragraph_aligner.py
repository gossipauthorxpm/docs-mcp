"""Copy paragraph-level alignment overrides from a template onto an output document.

The template (format.docx) defines centering as direct paragraph formatting on the
title and conclusions headings rather than in the style catalog (issue RC-3). Style
migration alone cannot transfer this, so we match output paragraphs to template
overrides by style name plus the leading keyword of the heading text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from docx.document import Document as DocxDocument
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

from docx_mcp.adapters.style_extractor import _extract_alignment

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

_NAME_TO_WD: dict[str, WD_PARAGRAPH_ALIGNMENT] = {
    "left": WD_PARAGRAPH_ALIGNMENT.LEFT,
    "center": WD_PARAGRAPH_ALIGNMENT.CENTER,
    "right": WD_PARAGRAPH_ALIGNMENT.RIGHT,
    "justify": WD_PARAGRAPH_ALIGNMENT.JUSTIFY,
    "distribute": WD_PARAGRAPH_ALIGNMENT.DISTRIBUTE,
}


@dataclass(frozen=True)
class AlignmentOverride:
    style_name: str
    keyword: str
    alignment: WD_PARAGRAPH_ALIGNMENT


class ParagraphAligner:
    def extract_overrides(self, template: DocxDocument) -> list[AlignmentOverride]:
        overrides: list[AlignmentOverride] = []
        seen: set[tuple[str, str]] = set()
        for paragraph in template.paragraphs:
            alignment_name = _extract_alignment(paragraph.paragraph_format)
            if alignment_name is None:
                continue
            wd_alignment = _NAME_TO_WD.get(alignment_name)
            if wd_alignment is None:
                continue
            key = self._key(paragraph)
            if key is None or key in seen:
                continue
            seen.add(key)
            overrides.append(AlignmentOverride(key[0], key[1], wd_alignment))
        return overrides

    def apply(self, output: DocxDocument, overrides: list[AlignmentOverride]) -> int:
        index = {(o.style_name, o.keyword): o.alignment for o in overrides}
        applied = 0
        for paragraph in output.paragraphs:
            key = self._key(paragraph)
            if key is None:
                continue
            alignment = index.get(key)
            if alignment is not None:
                paragraph.paragraph_format.alignment = alignment
                applied += 1
        return applied

    @staticmethod
    def _key(paragraph: object) -> tuple[str, str] | None:
        style = paragraph.style  # type: ignore[attr-defined]
        if style is None or style.name is None:
            return None
        match = _WORD_RE.search(paragraph.text)  # type: ignore[attr-defined]
        if match is None:
            return None
        return (style.name, match.group(0).upper())
