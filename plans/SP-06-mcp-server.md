# SP-06: MCP Server and Tools

## Goal

Expose ReadService and WriteService as four paginated MCP tools via FastMCP with stdio transport. The agent orchestrates the reformat user story by batching reads and calling write tools — no monolithic reformat tool.

## Depends on

SP-05.

## In scope

- `server.py` with FastMCP instance named `docs-mcp`
- Four MCP tools (agent interface):

| Tool | Purpose |
|---|---|
| `get_contents_from_docx` | Batch-read content blocks from `.docx` |
| `write_contents_to_docx` | Write/replace content blocks; create file if missing |
| `get_styles_from_docx` | Batch-read style catalog from `.docx` |
| `write_styles_to_docx` | Union styles onto existing file (incoming wins) |

- stdio transport (default for Cursor)
- Structured error responses on tool failures
- Entry point: `docx-mcp` script via `pyproject.toml`
- Cursor MCP configuration snippet (for README/SP-07)

## Out of scope

- Monolithic `reformat_docx` tool
- HTTP/streamable-http transport (SP-13)
- Full README (SP-07)
- Authentication

## Files to create/modify

| Path | Action |
|---|---|
| `src/docx_mcp/server.py` | Create |
| `pyproject.toml` | Verify entry point `docx-mcp = "docx_mcp.server:main"` |

## Tool signatures

```python
@mcp.tool()
def get_contents_from_docx(
    file_path: str,
    offset: int = 0,
    limit: int = 50,
) -> dict:
    """Return a paginated batch of document content blocks (paragraphs and tables)."""

@mcp.tool()
def write_contents_to_docx(
    file_path: str,
    contents: list[dict],
) -> dict:
    """Write content blocks to a .docx file. Creates a new file if path does not exist."""

@mcp.tool()
def get_styles_from_docx(
    file_path: str,
    offset: int = 0,
    limit: int = 50,
) -> dict:
    """Return a paginated batch of paragraph styles from a .docx file."""

@mcp.tool()
def write_styles_to_docx(
    file_path: str,
    styles: dict,
) -> dict:
    """Union style definitions onto an existing .docx file. Incoming styles win on name conflict."""
```

## Implementation tasks

1. Create FastMCP server:
   ```python
   from mcp.server.fastmcp import FastMCP
   mcp = FastMCP("docs-mcp")
   ```

2. Instantiate services with shared `DocxAdapter`:
   ```python
   adapter = DocxAdapter()
   read_service = ReadService(adapter)
   write_service = WriteService(adapter)
   ```

3. Register `get_contents_from_docx` → `read_service.get_contents(file_path, offset, limit)`

4. Register `get_styles_from_docx` → `read_service.get_styles(file_path, offset, limit)`

5. Register `write_contents_to_docx` → `write_service.write_contents(file_path, contents)`

6. Register `write_styles_to_docx` → `write_service.write_styles(file_path, styles)`

7. Implement error handler wrapper:
   - Catch `DocxMcpError` → return `error.to_dict()`
   - Catch unexpected exceptions → return `{ "code": "INTERNAL_ERROR", ... }`

8. Implement `main()`:
   ```python
   def main():
       mcp.run(transport="stdio")
   ```

9. Smoke test: `uv run docx-mcp` starts without crash

10. Manual test: run user story #1 tool sequence with fixture paths

## Agent workflow (reference)

```
# 1. Read simple.docx content in batches
get_contents_from_docx(file_path="simple.docx", offset=0, limit=50)
# repeat while has_more

# 2. Read format.docx styles in batches
get_styles_from_docx(file_path="format.docx", offset=0, limit=50)
# repeat while has_more; merge paragraph_styles client-side

# 3. Write content to output (creates file)
write_contents_to_docx(file_path="output.docx", contents=[...])

# 4. Union format styles onto output
write_styles_to_docx(file_path="output.docx", styles={ "paragraph_styles": [...], "section": {...} })
```

## Acceptance criteria

- [ ] `uv run docx-mcp` starts and listens on stdio
- [ ] All four tools registered with descriptive docstrings
- [ ] Invalid file path returns structured error (not unhandled exception)
- [ ] `write_contents_to_docx` creates file when path missing
- [ ] `write_styles_to_docx` returns error when file missing
- [ ] Paginated read tools return `has_more` correctly
- [ ] Tool responses are JSON-serializable dicts
- [ ] No business logic in `server.py` — only thin delegation to services

## README impact

Tools API section draft (finalized in SP-07).

## Cursor MCP config snippet

```json
{
  "mcpServers": {
    "docs-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/docs-mcp",
        "docx-mcp"
      ]
    }
  }
}
```

## Risks

| Risk | Mitigation |
|---|---|
| Agent calls tools in wrong order | Document sequence in SP-08; clear errors |
| Absolute paths required in Cursor config | Document in SP-07 with placeholder |
| MCP SDK API changes | Pin `mcp>=1.12.0`, test on install |
