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
| `write_contents_to_docx` | Write content blocks; create file if missing |
| `get_styles_from_docx` | Batch-read style catalog from `.docx` |
| `write_styles_to_docx` | Union styles onto existing file (incoming wins) |

- stdio transport (default for Cursor)
- Structured error responses on tool failures
- Entry point: `docx-mcp` script via `pyproject.toml`
- Cursor MCP configuration snippets: native `uv` and Docker `run --rm` (for README/SP-07)
- `Dockerfile` for ephemeral container deployment

## Out of scope

- Monolithic `reformat_docx` tool
- HTTP/streamable-http transport (SP-13)
- Full README (SP-07)
- Authentication

## Files to create/modify

| Path | Action |
|---|---|
| `src/docx_mcp/server.py` | Create |
| `Dockerfile` | Create |
| `pyproject.toml` | Verify entry point `docx-mcp = "docx_mcp.server:main"` |

## Tool signatures

```python
@mcp.tool()
def get_contents_from_docx(
    file_path: str,
    offset: int = 0,
    limit: int = 10,
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
    limit: int = 25,
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

11. Add `Dockerfile`:
    - Base: `python:3.12-slim`
    - Install project with `pip install .` (or copy + install from wheel)
    - `ENTRYPOINT ["docx-mcp"]` — stdio transport, no exposed ports

12. Document Docker MCP config with volume mount for host `.docx` paths

## User story: ephemeral Docker MCP session

**As a** user running an agent in Cursor (or any MCP host),
**I want** to configure docs-mcp as a Docker container that starts when the MCP session opens and is removed when the session ends,
**So that** I do not install Python/uv locally and each MCP session runs in an isolated, disposable environment.

> **Not per tool call.** Stdio MCP requires a persistent process: the host spawns one server (container) per session, routes all tool calls through it, then tears it down on disconnect. This matches FastMCP and MCP Python SDK behavior — see [References](#references-context7).

### Flow

```mermaid
sequenceDiagram
  participant User
  participant Agent as MCP Host / Agent
  participant Docker
  participant Container as docs-mcp container

  User->>Agent: 1. Add MCP config (docker run --rm -i …)
  Agent->>Docker: 2. Spawn MCP process on session start
  Docker->>Container: docker run --rm -i -v host:/workspace docs-mcp
  Container->>Container: docx-mcp listens on stdio
  Agent->>Container: 3. Multiple MCP tool calls (same session, same container)
  Container-->>Agent: JSON responses via stdio
  Agent->>Docker: 4. MCP session ends (disconnect / host restart)
  Docker->>Docker: process exits; --rm removes container
```

### Steps

1. **Setup** — user adds MCP server entry in agent config (Cursor `mcp.json`, Claude Desktop, etc.) with `command: docker` and `args: ["run", "--rm", "-i", …]`.
2. **Session start** — MCP host spawns `docker run --rm -i … docs-mcp` as a subprocess; container listens on stdio (JSON-RPC).
3. **Tool calls** — agent invokes tools (`get_contents_from_docx`, `write_contents_to_docx`, …); all calls in the session reuse the same container/process.
4. **Session end** — host closes the MCP connection → container process exits → `--rm` deletes the container (no stopped containers left behind).

### Constraints

| Topic | Rule |
|---|---|
| Lifecycle | One container **per MCP session**, not per tool call — client spawns and owns the server process ([FastMCP stdio](https://github.com/prefecthq/fastmcp/blob/main/docs/deployment/running-server.mdx)) |
| File paths | Mount a host directory (e.g. `-v /abs/host/docs:/workspace`); pass **container paths** in `file_path` (e.g. `/workspace/report.docx`) |
| Stdin | `-i` keeps stdin open for stdio JSON-RPC ([Microsoft MCP Docker example](https://github.com/microsoft/mcp-for-beginners/blob/main/03-GettingStarted/samples/csharp/README.md)) |
| Cleanup | `--rm` removes container when the session subprocess exits — not after each individual tool call |

### Acceptance (Docker)

- [ ] `docker build -t docs-mcp .` succeeds
- [ ] `docker run --rm -i docs-mcp` starts and accepts stdio (smoke: no immediate crash)
- [ ] With `-v /host/docs:/workspace`, tool calls using `/workspace/*.docx` read/write host files
- [ ] After ending the MCP session (kill subprocess / disconnect host), `docker ps -a` shows no leftover `docs-mcp` container

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

## Cursor MCP config snippets

### Native (uv)

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

### Docker (ephemeral session)

Build once: `docker build -t docs-mcp /absolute/path/to/docs-mcp`

```json
{
  "mcpServers": {
    "docs-mcp": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-v",
        "/absolute/path/to/your/docx-files:/workspace",
        "docs-mcp"
      ]
    }
  }
}
```

Use container paths in tool calls, e.g. `file_path="/workspace/simple.docx"`.

## Risks

| Risk | Mitigation |
|---|---|
| Agent calls tools in wrong order | Document sequence in SP-08; clear errors |
| Absolute paths required in Cursor config | Document in SP-07 with placeholder |
| MCP SDK API changes | Pin `mcp>=1.12.0`, test on install |
| Docker path confusion (host vs container) | Document mount + use `/workspace/...` in tool args |
| User expects one container per tool call | Document session lifecycle; cite FastMCP: client spawns server per session, not per call |

## References (Context7)

Validated against current MCP docs (Jun 2025):

| Source | Confirms |
|---|---|
| [FastMCP — Running Server / STDIO](https://github.com/prefecthq/fastmcp/blob/main/docs/deployment/running-server.mdx) | Client spawns server process **per session**; stdio reads stdin / writes stdout; server does not stay running on its own |
| [Microsoft MCP for Beginners — Docker config](https://github.com/microsoft/mcp-for-beginners/blob/main/03-GettingStarted/samples/csharp/README.md) | `command: docker`, `args: ["run", "--rm", "-i", "<image>"]` |
| [MCP Python SDK — StdioServerParameters](https://github.com/modelcontextprotocol/python-sdk/blob/main/README.md) | Host connects via `command` + `args` subprocess; same pattern works with `docker` as command |
