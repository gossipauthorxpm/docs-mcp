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
    assert_docx_style_field,
    assert_blocks_equal,
    assert_paragraph_style_field,
    assert_style_field_explicit,
    collect_all_contents,
    collect_all_styles,
    run_reformat_pipeline,
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

        format_styles = adapter.inspect_styles(FORMAT_DOCX)
        actual_profile = adapter._style_extractor.extract(output_doc)
        resolved = actual_profile.resolve_inherited()
        format_resolved = format_styles.resolve_inherited()

        for name in ["Heading 1", "Heading 2", "Normal", "КОД"]:
            expected = format_resolved.get_paragraph_style(name)
            actual = resolved.get_paragraph_style(name)
            assert expected is not None, f"Template missing style {name!r}"
            assert actual is not None, f"Output missing style {name!r}"
            for field in ("font_name", "font_size_pt", "bold", "alignment", "space_before_pt", "space_after_pt"):
                assert getattr(actual, field) == getattr(expected, field), (
                    f"Style {name!r}.{field}: {getattr(actual, field)!r} != {getattr(expected, field)!r}"
                )

    def test_reformat_heading_styles_match_template(self, adapter, read_service) -> None:
        output_doc = run_reformat_pipeline(adapter, read_service)

        assert_docx_style_field(output_doc, "Heading 1", bold=True, font_color=None)
        assert_docx_style_field(output_doc, "Heading 2", bold=None, font_color=None)

        resolved = adapter._style_extractor.extract(output_doc).resolve_inherited()
        assert_style_field_explicit(
            resolved,
            "Heading 1",
            space_before_pt=16.0,
            font_name="Times New Roman",
            bold=True,
            font_color=None,
            alignment="center",
        )

    def test_reformat_heading_style_centered(self, adapter, read_service) -> None:
        output_doc = run_reformat_pipeline(adapter, read_service)

        h1 = adapter._style_extractor.extract(output_doc).get_paragraph_style("Heading 1")
        assert h1 is not None
        assert h1.alignment == "center"
        assert h1.bold is True
