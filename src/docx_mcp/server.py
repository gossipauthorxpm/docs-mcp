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
from docx_mcp.services.reformat_service import ReformatService
from docx_mcp.services.write_service import WriteService

mcp = FastMCP("docs-mcp")

_adapter = DocxAdapter()
_read_service = ReadService(_adapter)
_write_service = WriteService(_adapter)
_reformat_service = ReformatService(_adapter)

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
                    "Batch of content blocks (paragraph/table dicts from get_contents_from_docx). "
                    "Max 200 blocks per call. offset=0 creates or replaces the body; "
                    "offset>0 appends after existing blocks."
                ),
                "items": {"type": "object", "additionalProperties": True},
            },
            "offset": {
                "type": "integer",
                "default": 0,
                "description": (
                    "Zero-based index where this batch starts. Use 0 for the first batch "
                    "(create/replace); for subsequent batches set offset to the previous total."
                ),
            },
            "style_map": {
                "type": "object",
                "description": (
                    "Optional draft→template style name map applied to paragraph blocks "
                    "before write (from plan_reformat_docx suggested_style_map)."
                ),
                "additionalProperties": {"type": "string"},
            },
        },
        "required": ["file_path", "contents"],
    },
    "plan_reformat_docx": {
        "type": "object",
        "additionalProperties": False,
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "properties": {
            "draft_path": {
                "type": "string",
                "description": "Path to the draft .docx file to reformat.",
            },
            "template_path": {
                "type": "string",
                "description": "Path to the template .docx file (format).",
            },
            "sample_blocks": {
                "type": "integer",
                "default": 10,
                "description": "Number of sample blocks per file for agent context (1-50).",
            },
            "resolve_styles": {
                "type": "boolean",
                "default": True,
                "description": "Resolve inherited style fields before catalog diff.",
            },
        },
        "required": ["draft_path", "template_path"],
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
                    "Style profile batch: paragraph_styles list (max 200 per call) and optional "
                    "section (page size and margins) from get_styles_from_docx — section only "
                    "on the first batch (offset=0)."
                ),
                "additionalProperties": True,
            },
            "offset": {
                "type": "integer",
                "default": 0,
                "description": (
                    "Zero-based index of the first paragraph style in this batch. "
                    "Loop with increasing offset until all template styles are written."
                ),
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
        "Write a batch of content blocks to a .docx file. Max 200 blocks per call. "
        "offset=0 creates a new file or replaces the document body; offset>0 appends "
        "the next batch (offset must equal current block count). Loop batches until "
        "all items from get_contents_from_docx are written. Call before write_styles_to_docx."
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
            description=(
                "Batch of paragraph or table block dicts from get_contents_from_docx (max 200)."
            )
        ),
    ],
    offset: Annotated[
        int,
        Field(
            description=(
                "Zero-based start index for this batch. 0 = create/replace; "
                "next batch offset = previous response total."
            ),
        ),
    ] = 0,
    style_map: Annotated[
        dict[str, str] | None,
        Field(
            description=(
                "Optional draft→template style name map (from plan_reformat_docx). "
                "Remaps paragraph block style.name before write."
            ),
        ),
    ] = None,
) -> dict:
    return _safe_call(
        lambda: _write_service.write_contents(file_path, contents, offset, style_map)
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
        "Union a batch of paragraph style definitions onto an existing .docx file. "
        "Max 200 styles per call. The target file must already exist — call "
        "write_contents_to_docx first. Incoming styles win on name conflict. Pass batches "
        "from get_styles_from_docx; include section only in the first batch (offset=0)."
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
                "Style profile batch with paragraph_styles list and optional section "
                "(page size and margins) on offset=0 only."
            )
        ),
    ],
    offset: Annotated[
        int,
        Field(description="Zero-based index of the first style in this batch."),
    ] = 0,
) -> dict:
    return _safe_call(
        lambda: _write_service.write_styles(file_path, styles, offset)
    )


@mcp.tool(
    title="Plan DOCX reformat",
    description=(
        "Analyze a draft against a template before reformat. Returns style usage "
        "counts, catalog diff, suggested_style_map, sample blocks, and recommended "
        "actions. Call first; review the map; then write contents with style_map."
    ),
    annotations=ToolAnnotations(
        title="Plan DOCX reformat",
        readOnlyHint=True,
        openWorldHint=False,
    ),
)
def plan_reformat_docx(
    draft_path: Annotated[
        str,
        Field(description="Path to the draft .docx file to reformat."),
    ],
    template_path: Annotated[
        str,
        Field(description="Path to the template .docx file (format)."),
    ],
    sample_blocks: Annotated[
        int,
        Field(description="Sample blocks per file for context (1-50, default 10)."),
    ] = 10,
    resolve_styles: Annotated[
        bool,
        Field(description="Resolve inherited fields before catalog diff (default true)."),
    ] = True,
) -> dict:
    return _safe_call(
        lambda: _reformat_service.plan(
            draft_path,
            template_path,
            sample_blocks,
            resolve_styles,
        )
    )


_patch_tool_input_schemas()


def main() -> None:
    mcp.run(transport="stdio")
