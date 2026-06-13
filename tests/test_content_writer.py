"""Tests for ContentWriter."""

from __future__ import annotations

from docx_mcp.adapters.content_writer import ContentWriter
from docx_mcp.domain.models import ParagraphBlock, RunFormat, StyleHint, TableBlock, TableCellBlock
from tests.conftest import PLAIN_DOCX, adapter  # noqa: F401 — adapter fixture


class TestContentWriter:
    def test_write_paragraphs_and_table(self, adapter) -> None:
        blocks = [
            ParagraphBlock(
                runs=[RunFormat(text="Title")],
                style=StyleHint(name="Heading 1"),
            ),
            ParagraphBlock(
                runs=[RunFormat(text="Body text")],
                style=StyleHint(name="Normal"),
            ),
            TableBlock(
                rows=[
                    [
                        TableCellBlock(
                            paragraphs=[
                                ParagraphBlock(runs=[RunFormat(text="A1")]),
                            ]
                        ),
                        TableCellBlock(
                            paragraphs=[
                                ParagraphBlock(runs=[RunFormat(text="B1")]),
                            ]
                        ),
                    ]
                ]
            ),
        ]

        document = adapter.create_document()
        writer = ContentWriter()
        count = writer.write(document, blocks, replace=True)

        assert count == 3
        extracted = adapter._extractor.extract(document)
        assert len(extracted.blocks) == 3
        assert extracted.blocks[0].text == "Title"
        assert extracted.blocks[1].text == "Body text"
        assert extracted.blocks[2].rows[0][0].paragraphs[0].text == "A1"

    def test_replace_clears_existing_body(self, adapter) -> None:
        document = adapter.open(PLAIN_DOCX)
        original_count = len(adapter._extractor.extract(document).blocks)

        writer = ContentWriter()
        new_blocks = [ParagraphBlock(runs=[RunFormat(text="Only this")])]
        writer.write(document, new_blocks, replace=True)

        extracted = adapter._extractor.extract(document)
        assert len(extracted.blocks) == 1
        assert extracted.blocks[0].text == "Only this"
        assert original_count > 1
