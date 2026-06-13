# SP-01: Project Foundation

## Goal

Bootstrap the docs-mcp repository with Python packaging, directory layout, agent guidelines, and structured error codes. This subplan establishes the foundation that all later subplans build on.

## Depends on

None.

## In scope

- `pyproject.toml` with dependencies: `python-docx>=1.1.2`, `mcp>=1.12.0`
- Dev dependencies: `pytest>=8.0`
- Entry point script: `docx-mcp = "docx_mcp.server:main"`
- `src/docx_mcp/` package skeleton with empty subpackages
- `AGENTS.md` with architecture and layer rules
- `errors.py` with error codes and helper factories
- `plans/` folder for subplan documents
- Minimal `README.md` stub (title + one-line description)
- `.gitignore` for Python/uv artifacts

## Out of scope

- Domain models
- Adapters and services
- MCP server and tools
- Tests beyond import smoke check
- Full README documentation

## Files to create/modify

| Path | Action |
|---|---|
| `pyproject.toml` | Create |
| `README.md` | Create (stub) |
| `AGENTS.md` | Create |
| `.gitignore` | Create or extend |
| `src/docx_mcp/__init__.py` | Create |
| `src/docx_mcp/errors.py` | Create |
| `src/docx_mcp/domain/__init__.py` | Create |
| `src/docx_mcp/adapters/__init__.py` | Create |
| `src/docx_mcp/services/__init__.py` | Create |
| `tests/__init__.py` | Create |
| `plans/SP-01-foundation.md` | Create (this file) |

## Implementation tasks

1. Create `pyproject.toml` with hatchling build, Python 3.11+, and `[tool.pytest.ini_options]`
2. Create `src/docx_mcp/` package skeleton with `__init__.py` exporting `__version__`
3. Define error codes in `errors.py`:
   - `FILE_NOT_FOUND`, `FILE_NOT_READABLE`, `FILE_NOT_WRITABLE`
   - `INVALID_PATH`, `PARSE_ERROR`, `STYLE_NOT_FOUND`
   - `REFORMAT_ERROR`, `INTERNAL_ERROR`
   - `DocxMcpError` dataclass with `to_dict()` method
   - Helper factories: `file_not_found()`, `parse_error()`, etc.
4. Write `AGENTS.md` documenting layer rules (see master plan cross-cutting rules)
5. Add README stub: project name + one-line description
6. Run `uv sync --extra dev` and verify package imports

## Acceptance criteria

- [ ] `uv sync --extra dev` completes without errors
- [ ] `from docx_mcp.errors import DocxMcpError` succeeds
- [ ] `DocxMcpError(...).to_dict()` returns `{ "code", "message", "details" }`
- [ ] Directory layout matches master plan target structure
- [ ] `AGENTS.md` documents layer dependency rules

## README impact

Stub only — title and one-line description.

## Risks

| Risk | Mitigation |
|---|---|
| Hatchling src-layout misconfiguration | Use `packages = ["src/docx_mcp"]` in `[tool.hatch.build.targets.wheel]` |
