"""Write-side service — content write and style union."""

from __future__ import annotations

from pathlib import Path

from docx_mcp.adapters.docx_adapter import DocxAdapter
from docx_mcp.domain.models import DocumentBlock, ParagraphBlock, TableBlock
from docx_mcp.domain.style_profile import StyleProfile
from docx_mcp.errors import DocxMcpError, internal_error


class WriteService:
    def __init__(self, adapter: DocxAdapter) -> None:
        self._adapter = adapter

    def write_contents(self, file_path: str, contents: list[dict]) -> dict:
        try:
            blocks = [self._block_from_dict(item) for item in contents]
            resolved = Path(file_path).resolve()
            created = not resolved.exists()
            blocks_written = self._adapter.write_contents(resolved, blocks, replace=True)
            return {
                "file_path": str(resolved),
                "blocks_written": blocks_written,
                "created": created,
            }
        except DocxMcpError:
            raise
        except Exception as exc:
            raise internal_error(str(exc)) from exc

    def write_styles(self, file_path: str, styles: dict) -> dict:
        try:
            incoming = StyleProfile.from_dict(styles)
            resolved = Path(file_path).resolve()
            added, updated, unchanged = self._adapter.write_styles(resolved, incoming)
            return {
                "file_path": str(resolved),
                "styles_added": added,
                "styles_updated": updated,
                "styles_unchanged": unchanged,
            }
        except DocxMcpError:
            raise
        except Exception as exc:
            raise internal_error(str(exc)) from exc

    @staticmethod
    def _block_from_dict(data: dict) -> DocumentBlock:
        block_type = data.get("block_type", "paragraph")
        if block_type == "table":
            return TableBlock.from_dict(data)
        return ParagraphBlock.from_dict(data)
