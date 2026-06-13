"""Extract domain blocks from python-docx documents."""

from __future__ import annotations

from typing import Iterator

from docx.document import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from docx_mcp.domain.models import (
    DocumentBlock,
    DocumentModel,
    ParagraphBlock,
    RunFormat,
    StyleHint,
    TableBlock,
    TableCellBlock,
)


def iter_block_items(parent: DocxDocument | _Cell) -> Iterator[Paragraph | Table]:
    """Yield paragraphs and tables in document order."""
    if isinstance(parent, DocxDocument):
        parent_elm = parent.element.body
    else:
        parent_elm = parent._tc

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


class ContentExtractor:
    def extract(self, document: DocxDocument, source_path: str | None = None) -> DocumentModel:
        blocks: list[DocumentBlock] = []
        for item in iter_block_items(document):
            if isinstance(item, Paragraph):
                blocks.append(self._extract_paragraph(item))
            elif isinstance(item, Table):
                blocks.append(self._extract_table(item))
        return DocumentModel(blocks=blocks, source_path=source_path)

    def _extract_paragraph(self, paragraph: Paragraph) -> ParagraphBlock:
        style: StyleHint | None = None
        if paragraph.style and paragraph.style.name:
            style = StyleHint(name=paragraph.style.name)

        runs: list[RunFormat] = []
        for run in paragraph.runs:
            font = run.font
            runs.append(
                RunFormat(
                    text=run.text,
                    bold=font.bold,
                    italic=font.italic,
                    font_name=font.name,
                    font_size_pt=font.size.pt if font.size else None,
                )
            )

        if not runs and paragraph.text:
            runs.append(RunFormat(text=paragraph.text))

        return ParagraphBlock(runs=runs, style=style)

    def _extract_table(self, table: Table) -> TableBlock:
        rows: list[list[TableCellBlock]] = []
        for row in table.rows:
            cells: list[TableCellBlock] = []
            for cell in row.cells:
                paragraphs = [self._extract_paragraph(p) for p in cell.paragraphs]
                cells.append(TableCellBlock(paragraphs=paragraphs))
            rows.append(cells)
        return TableBlock(rows=rows)
