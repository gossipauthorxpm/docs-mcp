"""Tests for ReadService — paginated content and style batches."""

from __future__ import annotations

import pytest

from docx_mcp.errors import DocxMcpError, FILE_NOT_FOUND
from docx_mcp.services.read_service import MAX_LIMIT, ReadService
from tests.conftest import FORMAT_DOCX, PLAIN_DOCX, collect_all_contents, collect_all_styles


class TestReadServiceContents:
    def test_get_contents_returns_blocks(self, read_service: ReadService) -> None:
        result = read_service.get_contents(str(PLAIN_DOCX))

        assert result["total"] > 0
        assert len(result["items"]) == result["total"]
        assert result["offset"] == 0
        assert result["limit"] == 50
        assert result["has_more"] is False
        assert result["source_path"] == str(PLAIN_DOCX.resolve())

        first = result["items"][0]
        assert first["block_type"] == "paragraph"
        assert first["style"]["name"] == "Heading 1"
        assert "ЛАБОРАТОРНАЯ РАБОТА" in "".join(r["text"] for r in first["runs"])

    def test_get_contents_pagination(self, read_service: ReadService) -> None:
        full = read_service.get_contents(str(FORMAT_DOCX), offset=0, limit=1)
        assert full["total"] > 1
        assert len(full["items"]) == 1
        assert full["has_more"] is True

        second = read_service.get_contents(str(FORMAT_DOCX), offset=1, limit=1)
        assert second["offset"] == 1
        assert len(second["items"]) == 1
        assert second["has_more"] is (second["offset"] + 1 < second["total"])

        last_offset = full["total"] - 1
        last = read_service.get_contents(str(FORMAT_DOCX), offset=last_offset, limit=1)
        assert last["has_more"] is False
        assert len(last["items"]) == 1

    def test_get_contents_includes_table_blocks(self, read_service: ReadService) -> None:
        collected = collect_all_contents(read_service, str(FORMAT_DOCX), limit=200)
        table_items = [item for item in collected if item["block_type"] == "table"]
        assert len(table_items) >= 1
        assert len(table_items[0]["rows"]) > 0

    def test_get_contents_missing_file(self, read_service: ReadService) -> None:
        with pytest.raises(DocxMcpError) as exc_info:
            read_service.get_contents("/nonexistent/path/missing.docx")
        assert exc_info.value.code == FILE_NOT_FOUND


class TestReadServiceStyles:
    def test_get_styles_first_batch_includes_section(self, read_service: ReadService) -> None:
        result = read_service.get_styles(str(FORMAT_DOCX))

        assert result["total"] > 0
        assert len(result["paragraph_styles"]) > 0
        assert "section" in result
        assert result["section"] is not None
        assert result["section"]["left_margin_cm"] is not None

        heading = next(
            s for s in result["paragraph_styles"] if s["name"] == "Heading 1"
        )
        assert heading["space_before_pt"] == 16.0
        assert heading["alignment"] == "center"

    def test_get_styles_later_batch_omits_section(self, read_service: ReadService) -> None:
        first = read_service.get_styles(str(FORMAT_DOCX), offset=0, limit=1)
        if first["total"] <= 1:
            pytest.skip("Not enough styles to test pagination")

        second = read_service.get_styles(str(FORMAT_DOCX), offset=1, limit=1)
        assert "section" not in second
        assert len(second["paragraph_styles"]) == 1
        assert second["has_more"] == (1 + 1 < second["total"])

    def test_get_styles_pagination_collects_all(self, read_service: ReadService) -> None:
        collected = collect_all_styles(read_service, str(FORMAT_DOCX), limit=2)
        single = read_service.get_styles(str(FORMAT_DOCX))

        assert len(collected["paragraph_styles"]) == single["total"]
        assert collected["section"] == single["section"]

    def test_get_styles_missing_file(self, read_service: ReadService) -> None:
        with pytest.raises(DocxMcpError) as exc_info:
            read_service.get_styles("/nonexistent/path/missing.docx")
        assert exc_info.value.code == FILE_NOT_FOUND


class TestReadServiceValidation:
    def test_negative_offset_raises(self, read_service: ReadService) -> None:
        with pytest.raises(DocxMcpError):
            read_service.get_contents(str(PLAIN_DOCX), offset=-1)

    def test_zero_limit_raises(self, read_service: ReadService) -> None:
        with pytest.raises(DocxMcpError):
            read_service.get_styles(str(PLAIN_DOCX), limit=0)

    def test_limit_above_max_raises(self, read_service: ReadService) -> None:
        with pytest.raises(DocxMcpError):
            read_service.get_contents(str(PLAIN_DOCX), limit=MAX_LIMIT + 1)
