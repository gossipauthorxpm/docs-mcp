"""Tests for ReformatService — plan draft vs template."""

from __future__ import annotations

import pytest

from docx_mcp.errors import DocxMcpError
from docx_mcp.services.reformat_service import ReformatService
from tests.conftest import FORMAT_DOCX, PLAIN_DOCX, adapter  # noqa: F401


class TestReformatServicePlan:
    def test_plan_plain_vs_format(self, adapter) -> None:
        service = ReformatService(adapter)
        result = service.plan(str(PLAIN_DOCX), str(FORMAT_DOCX), sample_blocks=5)

        assert "code" not in result
        assert result["draft_path"] == str(PLAIN_DOCX.resolve())
        assert result["template_path"] == str(FORMAT_DOCX.resolve())

        draft_usage = {u["name"]: u["block_count"] for u in result["draft_style_usage"]}
        assert draft_usage["Normal"] == 32
        assert draft_usage["List Paragraph"] == 5

        suggested = result["suggested_style_map"]
        assert suggested["Heading 1"] == "Heading 1"
        assert suggested["List Paragraph"] == "ТЕКСТ"
        assert suggested["Normal"] == "ТЕКСТ"
        assert result["heuristic_style_map"].get("Normal") is True

        diff = result["style_catalog_diff"]
        assert "ТЕКСТ" in diff["only_in_template"]
        assert "КОД" in diff["only_in_template"]

        assert len(result["sample_draft_blocks"]) <= 5
        assert len(result["sample_template_blocks"]) <= 5
        assert len(result["recommended_actions"]) >= 3

    def test_plan_invalid_sample_blocks(self, adapter) -> None:
        service = ReformatService(adapter)
        with pytest.raises(DocxMcpError) as exc_info:
            service.plan(str(PLAIN_DOCX), str(FORMAT_DOCX), sample_blocks=0)
        assert exc_info.value.code == "INVALID_PATH"
