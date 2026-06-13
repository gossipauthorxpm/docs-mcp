"""MCP server — thin tool handlers over ReadService and WriteService."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from docx_mcp.adapters.docx_adapter import DocxAdapter
from docx_mcp.errors import DocxMcpError, internal_error
from docx_mcp.services.read_service import ReadService
from docx_mcp.services.write_service import WriteService

mcp = FastMCP("docs-mcp")

_adapter = DocxAdapter()
_read_service = ReadService(_adapter)
_write_service = WriteService(_adapter)


def _safe_call(operation: Callable[[], dict]) -> dict:
    try:
        return operation()
    except DocxMcpError as exc:
        return exc.to_dict()
    except Exception as exc:
        return internal_error(str(exc)).to_dict()


@mcp.tool()
def get_contents_from_docx(
    file_path: str,
    offset: int = 0,
    limit: int = 10,
) -> dict:
    """Return a paginated batch of document content blocks (paragraphs and tables)."""
    return _safe_call(
        lambda: _read_service.get_contents(file_path, offset, limit)
    )


@mcp.tool()
def write_contents_to_docx(
    file_path: str,
    contents: list[dict],
) -> dict:
    """Write content blocks to a .docx file. Creates a new file if path does not exist."""
    return _safe_call(
        lambda: _write_service.write_contents(file_path, contents)
    )


@mcp.tool()
def get_styles_from_docx(
    file_path: str,
    offset: int = 0,
    limit: int = 25,
) -> dict:
    """Return a paginated batch of paragraph styles from a .docx file."""
    return _safe_call(
        lambda: _read_service.get_styles(file_path, offset, limit)
    )


@mcp.tool()
def write_styles_to_docx(
    file_path: str,
    styles: dict,
) -> dict:
    """Union style definitions onto an existing .docx file. Incoming styles win on name conflict."""
    return _safe_call(
        lambda: _write_service.write_styles(file_path, styles)
    )


def main() -> None:
    mcp.run(transport="stdio")
