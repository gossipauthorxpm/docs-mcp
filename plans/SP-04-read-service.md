# SP-04: ReadService

## Goal

Provide a service-layer API for reading `.docx` files into domain models, with optional block limiting for large documents. This service is the backend for the `read_docx` MCP tool.

## Depends on

SP-03.

## In scope

- `ReadService` class delegating to `DocxAdapter`
- `read(path, include_styles=True, limit=None) -> dict` returning JSON-ready document model
- Optional `limit` parameter to cap number of blocks returned
- Structured error propagation via `DocxMcpError.to_dict()`
- Unit/integration tests with fixture documents

## Out of scope

- Reformat logic (SP-05)
- MCP server wiring (SP-06)
- Write operations
- Headers/footers content extraction

## Files to create/modify

| Path | Action |
|---|---|
| `src/docx_mcp/services/read_service.py` | Create |
| `tests/test_read_service.py` | Create |
| `tests/fixtures/` | Create directory (fixtures added in SP-05; use programmatic docs here if needed) |

## Implementation tasks

1. Create `ReadService` accepting `DocxAdapter` via constructor (dependency injection)
2. Implement `read(path: str, include_styles: bool = True, limit: int | None = None) -> dict`:
   - Call `adapter.read_document(path)`
   - If `include_styles=False`, strip `style` from paragraph blocks in response
   - If `limit` set, truncate `blocks` list to first N items
   - Return `document.to_dict()` with block count metadata
3. Catch `DocxMcpError` and re-raise; wrap unexpected exceptions as `INTERNAL_ERROR`
4. Write tests:
   - Read a programmatically created `.docx` with headings and paragraphs
   - Verify block count and style names in output
   - Verify `limit` parameter truncates blocks
   - Verify `include_styles=False` omits style fields
   - Verify missing file returns structured error

## Acceptance criteria

- [ ] `ReadService.read()` returns JSON-serializable dict with `blocks` list
- [ ] `include_styles=False` removes style information from response
- [ ] `limit=N` returns at most N blocks
- [ ] File-not-found raises `DocxMcpError` with code `FILE_NOT_FOUND`
- [ ] `uv run pytest tests/test_read_service.py` passes
- [ ] No `docx` imports in `services/read_service.py`

## README impact

None.

## Risks

| Risk | Mitigation |
|---|---|
| Large documents overwhelm agent context | `limit` parameter defaults to unlimited but documented in SP-07 |
