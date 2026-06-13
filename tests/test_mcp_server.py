"""Tests for MCP server tool registration and delegation."""

from __future__ import annotations

import json
from pathlib import Path

from docx_mcp.errors import FILE_NOT_FOUND
from docx_mcp.server import (
    get_contents_from_docx,
    get_styles_from_docx,
    mcp,
    write_contents_to_docx,
    write_styles_to_docx,
)
from docx_mcp.services.read_service import ReadService
from tests.conftest import FORMAT_DOCX, PLAIN_DOCX, collect_all_contents, collect_all_styles


class TestMcpToolRegistration:
    def test_all_tools_registered(self) -> None:
        tool_names = {tool.name for tool in mcp._tool_manager.list_tools()}
        assert tool_names == {
            "get_contents_from_docx",
            "write_contents_to_docx",
            "get_styles_from_docx",
            "write_styles_to_docx",
        }


class TestMcpReadTools:
    def test_get_contents_returns_blocks(self) -> None:
        result = get_contents_from_docx(str(PLAIN_DOCX))

        assert "code" not in result
        assert result["total"] > 0
        assert len(result["items"]) <= 10
        assert result["has_more"] is (result["total"] > 10)
        json.dumps(result)

    def test_get_contents_pagination(self) -> None:
        first = get_contents_from_docx(str(FORMAT_DOCX), offset=0, limit=1)
        assert first["has_more"] is True
        assert len(first["items"]) == 1

    def test_get_contents_missing_file_returns_structured_error(self) -> None:
        result = get_contents_from_docx("/nonexistent/path/missing.docx")

        assert result["code"] == FILE_NOT_FOUND
        assert "message" in result
        assert "details" in result

    def test_get_styles_first_batch_includes_section(self) -> None:
        result = get_styles_from_docx(str(FORMAT_DOCX))

        assert "code" not in result
        assert result["total"] > 0
        assert "section" in result
        json.dumps(result)


class TestMcpWriteTools:
    def test_write_contents_creates_file(
        self,
        read_service: ReadService,
        tmp_path: Path,
    ) -> None:
        contents = collect_all_contents(read_service, str(PLAIN_DOCX))
        output = tmp_path / "output.docx"

        result = write_contents_to_docx(str(output), contents)

        assert "code" not in result
        assert result["created"] is True
        assert output.exists()
        json.dumps(result)

    def test_write_styles_requires_existing_file(self) -> None:
        result = write_styles_to_docx(
            "/nonexistent/output.docx",
            {"paragraph_styles": []},
        )

        assert result["code"] == FILE_NOT_FOUND

    def test_write_styles_unions_onto_existing_file(
        self,
        read_service: ReadService,
        tmp_path: Path,
    ) -> None:
        output = tmp_path / "styled.docx"
        write_contents_to_docx(
            str(output),
            [
                {
                    "block_type": "paragraph",
                    "runs": [{"text": "x"}],
                    "style": {"name": "Normal"},
                }
            ],
        )

        format_styles = collect_all_styles(read_service, str(FORMAT_DOCX))
        result = write_styles_to_docx(str(output), format_styles)

        assert "code" not in result
        assert result["file_path"] == str(output.resolve())
        json.dumps(result)
