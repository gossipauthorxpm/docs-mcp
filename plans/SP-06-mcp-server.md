# SP-06: MCP Server and Tools

## Goal

Expose ReadService and ReformatService as MCP tools via FastMCP with stdio transport, making the server usable from Cursor and other MCP clients.

## Depends on

SP-05.

## In scope

- `server.py` with FastMCP instance named `docs-mcp`
- MCP tools: `read_docx`, `inspect_styles`, `reformat_docx`
- stdio transport (default for Cursor)
- Structured error responses on tool failures
- Entry point: `docx-mcp` script via `pyproject.toml`
- Cursor MCP configuration snippet (for README/SP-07)

## Out of scope

- `write_docx` tool (SP-09)
- HTTP/streamable-http transport (SP-13)
- Full README (SP-07)
- Authentication

## Files to create/modify

| Path | Action |
|---|---|
| `src/docx_mcp/server.py` | Create |
| `pyproject.toml` | Verify entry point `docx-mcp = "docx_mcp.server:main"` |

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
   reformat_service = ReformatService(adapter)
   ```

3. Register tool `read_docx`:
   - Params: `path: str`, `include_styles: bool = True`, `limit: int | None = None`
   - Returns: document model dict or error dict
   - Docstring describes purpose for the agent

4. Register tool `inspect_styles`:
   - Params: `template_path: str`
   - Returns: `StyleProfile.to_dict()` or error dict

5. Register tool `reformat_docx`:
   - Params: `source_path: str`, `template_path: str`, `output_path: str`, `style_map: dict[str, str] | None = None`
   - Returns: `ReformatResult.to_dict()` or error dict

6. Implement error handler wrapper:
   - Catch `DocxMcpError` → return `error.to_dict()`
   - Catch unexpected exceptions → return `{ "code": "INTERNAL_ERROR", ... }`

7. Implement `main()`:
   ```python
   def main():
       mcp.run(transport="stdio")
   ```

8. Smoke test: `uv run docx-mcp` starts without crash

9. Manual test with fixture paths via MCP client or Cursor

## Acceptance criteria

- [ ] `uv run docx-mcp` starts and listens on stdio
- [ ] All three tools registered with descriptive docstrings
- [ ] Invalid file path returns structured error (not unhandled exception)
- [ ] `reformat_docx` with fixture paths produces output file
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
| Absolute paths required in Cursor config | Document in SP-07 with placeholder |
| MCP SDK API changes | Pin `mcp>=1.12.0`, test on install |
