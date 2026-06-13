"""MCP server — thin tool handlers over ReadService and WriteService."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from docx_mcp.adapters.docx_adapter import DocxAdapter
from docx_mcp.errors import DocxMcpError, internal_error
from docx_mcp.services.read_service import ReadService
from docx_mcp.services.write_service import WriteService

mcp = FastMCP("docs-mcp")

_adapter = DocxAdapter()
_read_service = ReadService(_adapter)
_write_service = WriteService(_adapter)

# Cursor reads parameter descriptions from inputSchema.properties.*.description.
# Pydantic adds a "title" per property that can hide descriptions in some MCP UIs;
# patch listed schemas to MCP-spec shape (type + description only on properties).
_TOOL_INPUT_SCHEMAS: dict[str, dict[str, Any]] = {
    "get_contents_from_docx": {
        "type": "object",
        "additionalProperties": False,
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "properties": {
            "file_path": {
                "type": "string",
                "description": (
                    "Path to the .docx file. Provided by the MCP client in each tool call, "
                    "not in server build or MCP host config."
                ),
            },
            "offset": {
                "type": "integer",
                "default": 0,
                "description": "Zero-based index of the first content block to return.",
            },
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum blocks per batch (1-200, default 10).",
            },
        },
        "required": ["file_path"],
    },
    "write_contents_to_docx": {
        "type": "object",
        "additionalProperties": False,
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "properties": {
            "file_path": {
                "type": "string",
                "description": (
                    "Output path for the .docx file. Provided by the MCP client in each tool call."
                ),
            },
            "contents": {
                "type": "array",
                "description": (
                    "Content blocks to write (paragraph/table dicts from get_contents_from_docx)."
                ),
                "items": {"type": "object", "additionalProperties": True},
            },
        },
        "required": ["file_path", "contents"],
    },
    "get_styles_from_docx": {
        "type": "object",
        "additionalProperties": False,
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "properties": {
            "file_path": {
                "type": "string",
                "description": (
                    "Path to the template or source .docx file. Provided by the MCP client."
                ),
            },
            "offset": {
                "type": "integer",
                "default": 0,
                "description": "Zero-based index of the first paragraph style to return.",
            },
            "limit": {
                "type": "integer",
                "default": 25,
                "description": "Maximum styles per batch (1-200, default 25).",
            },
        },
        "required": ["file_path"],
    },
    "write_styles_to_docx": {
        "type": "object",
        "additionalProperties": False,
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "properties": {
            "file_path": {
                "type": "string",
                "description": (
                    "Path to an existing .docx file. Provided by the MCP client. "
                    "File must exist (call write_contents_to_docx first)."
                ),
            },
            "styles": {
                "type": "object",
                "description": (
                    "Style profile: paragraph_styles list and optional section "
                    "(page size and margins) from get_styles_from_docx."
                ),
                "additionalProperties": True,
            },
        },
        "required": ["file_path", "styles"],
    },
}


def _patch_tool_input_schemas() -> None:
    for internal in mcp._tool_manager.list_tools():
        schema = _TOOL_INPUT_SCHEMAS.get(internal.name)
        if schema is not None:
            internal.parameters = schema


def _safe_call(operation: Callable[[], dict]) -> dict:
    try:
        return operation()
    except DocxMcpError as exc:
        return exc.to_dict()
    except Exception as exc:
        return internal_error(str(exc)).to_dict()


@mcp.tool(
    title="Get DOCX contents",
    description=(
        "Read a paginated batch of content blocks (paragraphs and tables) from a .docx file. "
        "Returns items, total, offset, limit, and has_more — loop with increasing offset until "
        "has_more is false. Blocks carry style name references only; use get_styles_from_docx "
        "for full style definitions."
    ),
    annotations=ToolAnnotations(
        title="Get DOCX contents",
        readOnlyHint=True,
        openWorldHint=False,
    ),
)
def get_contents_from_docx(
    file_path: Annotated[
        str,
        Field(description="Path to the .docx file (provided by the MCP client in each tool call)."),
    ],
    offset: Annotated[
        int,
        Field(description="Zero-based index of the first block to return."),
    ] = 0,
    limit: Annotated[
        int,
        Field(description="Maximum number of blocks per batch (1-200, default 10)."),
    ] = 10,
) -> dict:
    return _safe_call(
        lambda: _read_service.get_contents(file_path, offset, limit)
    )


@mcp.tool(
    title="Write DOCX contents",
    description=(
        "Write content blocks to a .docx file. Creates a new file if the path does not exist; "
        "replaces the document body if it already exists. Pass blocks collected from "
        "get_contents_from_docx. Call before write_styles_to_docx when reformatting."
    ),
    annotations=ToolAnnotations(
        title="Write DOCX contents",
        readOnlyHint=False,
        destructiveHint=True,
        openWorldHint=False,
    ),
)
def write_contents_to_docx(
    file_path: Annotated[
        str,
        Field(description="Output path for the .docx file (provided by the MCP client)."),
    ],
    contents: Annotated[
        list[dict],
        Field(
            description="List of paragraph or table block dicts from get_contents_from_docx."
        ),
    ],
) -> dict:
    return _safe_call(
        lambda: _write_service.write_contents(file_path, contents)
    )


@mcp.tool(
    title="Get DOCX styles",
    description=(
        "Read a paginated batch of paragraph style definitions from a .docx file. "
        "Returns paragraph_styles, total, offset, limit, and has_more. The section field "
        "(page size and margins) is included only in the first batch (offset=0). "
        "Merge all batches client-side before calling write_styles_to_docx."
    ),
    annotations=ToolAnnotations(
        title="Get DOCX styles",
        readOnlyHint=True,
        openWorldHint=False,
    ),
)
def get_styles_from_docx(
    file_path: Annotated[
        str,
        Field(description="Path to the template or source .docx file (provided by the MCP client)."),
    ],
    offset: Annotated[
        int,
        Field(description="Zero-based index of the first style to return."),
    ] = 0,
    limit: Annotated[
        int,
        Field(description="Maximum number of styles per batch (1-200, default 25)."),
    ] = 25,
) -> dict:
    return _safe_call(
        lambda: _read_service.get_styles(file_path, offset, limit)
    )


@mcp.tool(
    title="Write DOCX styles",
    description=(
        "Union paragraph style definitions onto an existing .docx file. The target file must "
        "already exist — call write_contents_to_docx first. Incoming styles win on name "
        "conflict. Pass a StyleProfile dict with paragraph_styles and optional section from "
        "get_styles_from_docx batches."
    ),
    annotations=ToolAnnotations(
        title="Write DOCX styles",
        readOnlyHint=False,
        destructiveHint=False,
        openWorldHint=False,
    ),
)
def write_styles_to_docx(
    file_path: Annotated[
        str,
        Field(description="Path to an existing .docx file (provided by the MCP client)."),
    ],
    styles: Annotated[
        dict,
        Field(
            description=(
                "Style profile with paragraph_styles list and optional section "
                "(page size and margins)."
            )
        ),
    ],
) -> dict:
    return _safe_call(
        lambda: _write_service.write_styles(file_path, styles)
    )


_patch_tool_input_schemas()


def main() -> None:
    mcp.run(transport="stdio")
