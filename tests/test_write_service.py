"""Tests for WriteService — file I/O write operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from docx_mcp.errors import DocxMcpError, FILE_NOT_FOUND
from docx_mcp.services.write_service import WriteService
from tests.conftest import FORMAT_DOCX, PLAIN_DOCX, collect_all_contents, collect_all_styles


class TestWriteServiceContents:
    def test_write_contents_creates_new_file(
        self,
        write_service: WriteService,
        read_service,
        tmp_path: Path,
    ) -> None:
        contents = collect_all_contents(read_service, str(PLAIN_DOCX))
        output = tmp_path / "output.docx"

        result = write_service.write_contents(str(output), contents)

        assert result["created"] is True
        assert result["blocks_written"] == len(contents)
        assert result["total"] == len(contents)
        assert result["offset"] == 0
        assert result["file_path"] == str(output.resolve())
        assert output.exists()

        written = read_service.get_contents(str(output))
        assert written["total"] == len(contents)

    def test_write_contents_replaces_existing_body(
        self,
        write_service: WriteService,
        read_service,
        tmp_path: Path,
    ) -> None:
        output = tmp_path / "existing.docx"
        write_service.write_contents(str(output), [{"block_type": "paragraph", "runs": [{"text": "old"}]}])

        contents = collect_all_contents(read_service, str(PLAIN_DOCX))
        result = write_service.write_contents(str(output), contents)

        assert result["created"] is False
        assert result["blocks_written"] == len(contents)

        written = read_service.get_contents(str(output))
        assert written["total"] == len(contents)
        assert written["items"][0]["runs"][0]["text"] != "old"

    def test_write_contents_batch_append(
        self,
        write_service: WriteService,
        read_service,
        tmp_path: Path,
    ) -> None:
        all_contents = collect_all_contents(read_service, str(PLAIN_DOCX), limit=3)
        assert len(all_contents) > 3

        output = tmp_path / "batched.docx"
        first_batch = all_contents[:3]
        second_batch = all_contents[3:]

        first = write_service.write_contents(str(output), first_batch, offset=0)
        assert first["created"] is True
        assert first["blocks_written"] == 3
        assert first["total"] == 3

        second = write_service.write_contents(str(output), second_batch, offset=3)
        assert second["created"] is False
        assert second["blocks_written"] == len(second_batch)
        assert second["total"] == len(all_contents)

        written = read_service.get_contents(str(output), offset=0, limit=200)
        assert written["total"] == len(all_contents)

    def test_write_contents_applies_style_map(
        self,
        write_service: WriteService,
        read_service,
        tmp_path: Path,
    ) -> None:
        output = tmp_path / "mapped.docx"
        contents = [
            {
                "block_type": "paragraph",
                "runs": [{"text": "item"}],
                "style": {"name": "List Paragraph"},
            }
        ]

        result = write_service.write_contents(
            str(output),
            contents,
            style_map={"List Paragraph": "ТЕКСТ"},
        )

        assert result["styles_remapped"] == 1
        written = read_service.get_contents(str(output))
        assert written["items"][0]["style"]["name"] == "ТЕКСТ"

    def test_write_contents_wrong_offset_returns_error(
        self,
        write_service: WriteService,
        tmp_path: Path,
    ) -> None:
        output = tmp_path / "bad_offset.docx"
        write_service.write_contents(
            str(output),
            [{"block_type": "paragraph", "runs": [{"text": "a"}]}],
            offset=0,
        )

        with pytest.raises(DocxMcpError) as exc_info:
            write_service.write_contents(
                str(output),
                [{"block_type": "paragraph", "runs": [{"text": "b"}]}],
                offset=5,
            )
        assert exc_info.value.code == "INVALID_PATH"


class TestWriteServiceStyles:
    def test_write_styles_unions_incoming_as_master(
        self,
        write_service: WriteService,
        read_service,
        adapter,
        tmp_path: Path,
    ) -> None:
        output = tmp_path / "styled.docx"
        write_service.write_contents(
            str(output),
            [{"block_type": "paragraph", "runs": [{"text": "x"}], "style": {"name": "Normal"}}],
        )

        format_styles = collect_all_styles(read_service, str(FORMAT_DOCX))
        result = write_service.write_styles(str(output), format_styles)

        assert result["styles_added"] >= 0
        assert result["styles_updated"] >= 0
        assert result["file_path"] == str(output.resolve())

        profile = adapter.inspect_styles(output)
        heading = profile.get_paragraph_style("Heading 1")
        assert heading is not None
        assert heading.space_before_pt == 16.0

        normal = profile.get_paragraph_style("Normal")
        assert normal is not None
        assert normal.font_name == "Times New Roman"

    def test_write_styles_batch(
        self,
        write_service: WriteService,
        read_service,
        adapter,
        tmp_path: Path,
    ) -> None:
        output = tmp_path / "batched_styles.docx"
        write_service.write_contents(
            str(output),
            [{"block_type": "paragraph", "runs": [{"text": "x"}], "style": {"name": "Normal"}}],
        )

        all_styles = collect_all_styles(read_service, str(FORMAT_DOCX), limit=5)
        styles_list = all_styles["paragraph_styles"]
        assert len(styles_list) > 5

        first_batch = {
            "paragraph_styles": styles_list[:5],
            "section": all_styles.get("section"),
        }
        second_batch = {"paragraph_styles": styles_list[5:]}

        write_service.write_styles(str(output), first_batch, offset=0)
        result = write_service.write_styles(str(output), second_batch, offset=5)

        profile = adapter.inspect_styles(output)
        template_names = {s["name"] for s in styles_list}
        for name in template_names:
            assert profile.get_paragraph_style(name) is not None, f"Missing style {name!r}"
        heading = profile.get_paragraph_style("Heading 1")
        assert heading is not None
        assert heading.space_before_pt == 16.0

    def test_write_styles_requires_existing_file(self, write_service: WriteService) -> None:
        with pytest.raises(DocxMcpError) as exc_info:
            write_service.write_styles("/nonexistent/output.docx", {"paragraph_styles": []})
        assert exc_info.value.code == FILE_NOT_FOUND
