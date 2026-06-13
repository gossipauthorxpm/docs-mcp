"""End-to-end reformat pipeline test — in-memory, no output file on disk."""

from __future__ import annotations

from docx_mcp.adapters.content_writer import ContentWriter
from docx_mcp.adapters.style_migrator import StyleMigrator
from docx_mcp.domain.models import ParagraphBlock, TableBlock
from docx_mcp.domain.style_profile import StyleProfile
from docx_mcp.services.write_service import WriteService
from tests.conftest import (
    FORMAT_DOCX,
    PLAIN_DOCX,
    assert_blocks_equal,
    assert_paragraph_style_field,
    assert_styles_equal,
    collect_all_contents,
    collect_all_styles,
)


def _blocks_from_dicts(items: list[dict]) -> list[ParagraphBlock | TableBlock]:
    return [WriteService._block_from_dict(item) for item in items]


class TestReformatAssetPipeline:
    def test_asset_files_exist(self) -> None:
        assert PLAIN_DOCX.exists(), f"Missing fixture: {PLAIN_DOCX}"
        assert FORMAT_DOCX.exists(), f"Missing fixture: {FORMAT_DOCX}"

    def test_reformat_pipeline_end_to_end(self, adapter, read_service) -> None:
        contents = collect_all_contents(read_service, str(PLAIN_DOCX))
        format_styles_dict = collect_all_styles(read_service, str(FORMAT_DOCX))

        output_doc = adapter.create_document()
        blocks = _blocks_from_dicts(contents)

        content_writer = ContentWriter()
        blocks_written = content_writer.write(output_doc, blocks, replace=True)
        assert blocks_written == len(contents)

        existing = adapter._style_extractor.extract(output_doc)
        incoming = StyleProfile.from_dict(format_styles_dict)
        merged = existing.union_with(incoming, master="other")

        style_migrator = StyleMigrator()
        style_migrator.apply(output_doc, merged)

        expected_doc = adapter.read_document(PLAIN_DOCX)
        actual_blocks = adapter._extractor.extract(output_doc, source_path=None).blocks
        assert_blocks_equal(actual_blocks, expected_doc.blocks)

        simple_styles = adapter.inspect_styles(PLAIN_DOCX)
        format_styles = adapter.inspect_styles(FORMAT_DOCX)
        expected_profile = simple_styles.union_with(format_styles, master="other")
        actual_profile = adapter._style_extractor.extract(output_doc)
        assert_styles_equal(
            actual_profile.resolve_inherited(),
            expected_profile.resolve_inherited(),
        )

        resolved = actual_profile.resolve_inherited()
        assert_paragraph_style_field(resolved, "Heading 1", space_before_pt=18.0)
        assert_paragraph_style_field(resolved, "Normal", font_name="Times New Roman")
        assert resolved.get_paragraph_style("КОД") is not None
        assert resolved.get_paragraph_style("macro") is not None
