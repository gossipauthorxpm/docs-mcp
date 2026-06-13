# docs-mcp — Agent Guidelines

## Architecture

Layered design: MCP tools delegate to services, services use adapters, adapters translate to/from domain models.

```mermaid
flowchart TB
  subgraph mcpLayer [MCP Layer]
    Server[FastMCP Server]
    Tools["4 Tools: get/write contents & styles"]
  end

  subgraph serviceLayer [Service Layer]
    ReadSvc[ReadService]
    WriteSvc[WriteService]
  end

  subgraph adapterLayer [Adapter Layer]
    DocxAdapter[DocxAdapter]
    ContentWriter[ContentWriter]
    StyleMigrator[StyleMigrator]
    ContentExtractor[ContentExtractor]
    StyleExtractor[StyleExtractor]
  end

  subgraph domainLayer [Domain Layer]
    DocModel[DocumentModel]
    StyleProfile[StyleProfile]
    BlockModel[ParagraphBlock / TableBlock]
  end

  Agent[Cursor Agent] -->|batch tool calls| Server
  Server --> Tools
  Tools --> ReadSvc
  Tools --> WriteSvc
  ReadSvc --> DocxAdapter
  WriteSvc --> DocxAdapter
  DocxAdapter --> ContentExtractor
  DocxAdapter --> StyleExtractor
  DocxAdapter --> ContentWriter
  DocxAdapter --> StyleMigrator
  ReadSvc --> domainLayer
  WriteSvc --> domainLayer
```

## MCP tools (agent interface)

| Tool | Service | Description |
|---|---|---|
| `get_contents_from_docx(file_path, offset, limit)` | ReadService | Batch-read content blocks |
| `write_contents_to_docx(file_path, contents)` | WriteService | Write blocks; create file if missing |
| `get_styles_from_docx(file_path, offset, limit)` | ReadService | Batch-read style catalog |
| `write_styles_to_docx(file_path, styles)` | WriteService | Union styles; incoming wins on conflict |

## Layer dependency rules

| Layer | Package | May import from | Must not import |
|---|---|---|---|
| MCP | `server.py` | `services/`, `errors` | `adapters/`, `docx` |
| Service | `services/` | `adapters/`, `domain/`, `errors` | `docx`, `mcp` |
| Adapter | `adapters/` | `domain/`, `errors`, `docx` | `services/`, `mcp` |
| Domain | `domain/` | stdlib only | everything else |

**Dependency direction is always downward:** MCP → Service → Adapter → Domain.

## Cross-cutting rules

- **New MCP tool** = thin handler in `server.py` + service method. No business logic in `server.py`.
- **`python-docx` imports only in `adapters/`** — never in services or MCP layer.
- **Structured errors** — return `{ "code", "message", "details" }` via `DocxMcpError.to_dict()`. Do not throw raw strings to MCP clients.
- **Domain models are the stable contract** between services and adapters. Services work with domain types, not python-docx objects.
- **Dependency injection** — services receive `DocxAdapter` via constructor, not module-level singletons.

## Project layout

```
docs-mcp/
├── README.md
├── pyproject.toml
├── AGENTS.md
├── plans/
├── src/docx_mcp/
│   ├── server.py
│   ├── errors.py
│   ├── domain/
│   ├── adapters/
│   └── services/
├── tests/
│   └── fixtures/
└── examples/
```

## Subplan workflow

Implement one subplan at a time (`plans/SP-XX-*.md`). Read the active subplan before making changes. Do not implement features from later subplans.

## Development

```bash
uv sync --extra dev
uv run pytest
```
