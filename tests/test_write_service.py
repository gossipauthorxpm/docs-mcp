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
        assert heading.space_before_pt == 18.0

        normal = profile.get_paragraph_style("Normal")
        assert normal is not None
        assert normal.font_name == "Times New Roman"

    def test_write_styles_requires_existing_file(self, write_service: WriteService) -> None:
        with pytest.raises(DocxMcpError) as exc_info:
            write_service.write_styles("/nonexistent/output.docx", {"paragraph_styles": []})
        assert exc_info.value.code == FILE_NOT_FOUND
