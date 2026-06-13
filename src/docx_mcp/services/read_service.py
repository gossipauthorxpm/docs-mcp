"""Read-side service — paginated content and style batches."""

from __future__ import annotations

from pathlib import Path

from docx_mcp.adapters.docx_adapter import DocxAdapter
from docx_mcp.errors import DocxMcpError, internal_error

MAX_LIMIT = 200


class ReadService:
    def __init__(self, adapter: DocxAdapter) -> None:
        self._adapter = adapter

    def get_contents(
        self,
        file_path: str,
        offset: int = 0,
        limit: int = 50,
    ) -> dict:
        self._validate_pagination(offset, limit)
        try:
            document = self._adapter.read_document(file_path)
            total = len(document.blocks)
            items = [
                block.to_dict()
                for block in document.blocks[offset : offset + limit]
            ]
            return {
                "items": items,
                "total": total,
                "offset": offset,
                "limit": limit,
                "has_more": offset + limit < total,
                "source_path": str(Path(file_path).resolve()),
            }
        except DocxMcpError:
            raise
        except Exception as exc:
            raise internal_error(str(exc)) from exc

    def get_styles(
        self,
        file_path: str,
        offset: int = 0,
        limit: int = 50,
    ) -> dict:
        self._validate_pagination(offset, limit)
        try:
            profile = self._adapter.inspect_styles(file_path)
            total = len(profile.paragraph_styles)
            response: dict = {
                "paragraph_styles": [
                    style.to_dict()
                    for style in profile.paragraph_styles[offset : offset + limit]
                ],
                "total": total,
                "offset": offset,
                "limit": limit,
                "has_more": offset + limit < total,
                "source_path": str(Path(file_path).resolve()),
            }
            if offset == 0 and profile.section is not None:
                response["section"] = profile.section.to_dict()
            return response
        except DocxMcpError:
            raise
        except Exception as exc:
            raise internal_error(str(exc)) from exc

    @staticmethod
    def _validate_offset(offset: int) -> None:
        if offset < 0:
            raise DocxMcpError(
                code="INVALID_PATH",
                message="offset must be >= 0",
                details={"offset": offset},
            )

    @staticmethod
    def _validate_pagination(offset: int, limit: int) -> None:
        ReadService._validate_offset(offset)
        if limit <= 0:
            raise DocxMcpError(
                code="INVALID_PATH",
                message="limit must be > 0",
                details={"limit": limit},
            )
        if limit > MAX_LIMIT:
            raise DocxMcpError(
                code="INVALID_PATH",
                message=f"limit must be <= {MAX_LIMIT}",
                details={"limit": limit, "max_limit": MAX_LIMIT},
            )
