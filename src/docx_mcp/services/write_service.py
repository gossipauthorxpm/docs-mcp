"""Write-side service — paginated content write and style union."""

from __future__ import annotations

import copy
from pathlib import Path

from docx_mcp.adapters.docx_adapter import DocxAdapter
from docx_mcp.domain.models import DocumentBlock, ParagraphBlock, TableBlock
from docx_mcp.domain.style_profile import StyleProfile
from docx_mcp.errors import DocxMcpError, internal_error
from docx_mcp.services.read_service import MAX_LIMIT, ReadService


class WriteService:
    def __init__(self, adapter: DocxAdapter) -> None:
        self._adapter = adapter

    def write_contents(
        self,
        file_path: str,
        contents: list[dict],
        offset: int = 0,
        style_map: dict[str, str] | None = None,
    ) -> dict:
        ReadService._validate_offset(offset)
        if len(contents) > MAX_LIMIT:
            raise DocxMcpError(
                code="INVALID_PATH",
                message=f"contents batch size must be <= {MAX_LIMIT}",
                details={"batch_size": len(contents), "max_limit": MAX_LIMIT},
            )
        try:
            remapped_contents, styles_remapped, style_map_warnings = _apply_style_map(
                contents, style_map
            )
            blocks = [self._block_from_dict(item) for item in remapped_contents]
            resolved = Path(file_path).resolve()

            if offset == 0:
                created = not resolved.exists()
                replace = True
            else:
                if not resolved.exists():
                    raise DocxMcpError(
                        code="FILE_NOT_FOUND",
                        message=(
                            f"File not found for append at offset {offset}: {resolved}. "
                            "Write offset=0 first."
                        ),
                        details={"path": str(resolved), "offset": offset},
                    )
                current_total = len(self._adapter.read_document(resolved).blocks)
                if current_total != offset:
                    raise DocxMcpError(
                        code="INVALID_PATH",
                        message=(
                            f"Expected offset {current_total} for next batch, got {offset}"
                        ),
                        details={
                            "offset": offset,
                            "expected_offset": current_total,
                            "path": str(resolved),
                        },
                    )
                created = False
                replace = False

            blocks_written = self._adapter.write_contents(
                resolved, blocks, replace=replace
            )
            total = len(self._adapter.read_document(resolved).blocks)
            return {
                "file_path": str(resolved),
                "blocks_written": blocks_written,
                "total": total,
                "offset": offset,
                "has_more": False,
                "created": created,
                "styles_remapped": styles_remapped,
                "style_map_warnings": style_map_warnings,
            }
        except DocxMcpError:
            raise
        except Exception as exc:
            raise internal_error(str(exc)) from exc

    def write_styles(
        self,
        file_path: str,
        styles: dict,
        offset: int = 0,
    ) -> dict:
        paragraph_styles = styles.get("paragraph_styles", [])
        if not isinstance(paragraph_styles, list):
            raise DocxMcpError(
                code="INVALID_PATH",
                message="styles.paragraph_styles must be a list",
                details={"field": "paragraph_styles"},
            )
        ReadService._validate_offset(offset)
        if len(paragraph_styles) > MAX_LIMIT:
            raise DocxMcpError(
                code="INVALID_PATH",
                message=f"paragraph_styles batch size must be <= {MAX_LIMIT}",
                details={"batch_size": len(paragraph_styles), "max_limit": MAX_LIMIT},
            )
        if offset > 0 and styles.get("section") is not None:
            raise DocxMcpError(
                code="INVALID_PATH",
                message="section may only be included in the first batch (offset=0)",
                details={"offset": offset},
            )
        try:
            incoming_data: dict = {"paragraph_styles": paragraph_styles}
            if offset == 0 and styles.get("section") is not None:
                incoming_data["section"] = styles["section"]
            incoming = StyleProfile.from_dict(incoming_data)
            resolved = Path(file_path).resolve()
            added, updated, unchanged = self._adapter.write_styles(resolved, incoming)
            profile = self._adapter.inspect_styles(resolved)
            total = len(profile.paragraph_styles)
            return {
                "file_path": str(resolved),
                "styles_added": added,
                "styles_updated": updated,
                "styles_unchanged": unchanged,
                "total": total,
                "offset": offset,
                "has_more": False,
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


def _apply_style_map(
    contents: list[dict],
    style_map: dict[str, str] | None,
) -> tuple[list[dict], int, list[str]]:
    if not style_map:
        return contents, 0, []

    remapped_contents: list[dict] = []
    styles_remapped = 0
    matched_keys: set[str] = set()
    warnings: list[str] = []

    for item in contents:
        item_copy = copy.deepcopy(item)
        if item_copy.get("block_type") == "paragraph":
            style = item_copy.get("style")
            if isinstance(style, dict):
                source_name = style.get("name")
                if source_name and source_name in style_map:
                    style["name"] = style_map[source_name]
                    styles_remapped += 1
                    matched_keys.add(source_name)
        remapped_contents.append(item_copy)

    for key in style_map:
        if key not in matched_keys:
            warnings.append(
                f"style_map key {key!r} was not used in this contents batch"
            )

    return remapped_contents, styles_remapped, warnings
