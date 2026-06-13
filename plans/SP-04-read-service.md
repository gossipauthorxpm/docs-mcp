# SP-04: ReadService

## Goal

Provide a service-layer API for reading `.docx` files in **paginated batches** — content blocks and styles separately. Backend for `get_contents_from_docx` and `get_styles_from_docx` MCP tools.

## Depends on

SP-03.

## In scope

- `ReadService` class delegating to `DocxAdapter`
- `get_contents(file_path, offset=0, limit=50) -> dict` — batch of `DocumentBlock` (paragraph + table)
- `get_styles(file_path, offset=0, limit=50) -> dict` — batch of `ParagraphStyleInfo` from `StyleProfile`
- Paginated response envelope: `items`, `total`, `offset`, `limit`, `has_more`, `source_path`
- `section` included in first styles batch only (`offset == 0`)
- Structured error propagation via `DocxMcpError.to_dict()`
- Unit/integration tests with fixture documents

## Out of scope

- Write operations (SP-05)
- MCP server wiring (SP-06)
- Headers/footers content extraction
- Caching document parses across batch calls (v1 re-reads file each call)

## Files to create/modify

| Path | Action |
|---|---|
| `src/docx_mcp/services/read_service.py` | Create |
| `tests/test_read_service.py` | Create |

## MCP tool mapping

| MCP tool | Service method |
|---|---|
| `get_contents_from_docx(file_path, offset, limit)` | `ReadService.get_contents()` |
| `get_styles_from_docx(file_path, offset, limit)` | `ReadService.get_styles()` |

## Response shapes

**get_contents:**

```json
{
  "items": [ { "block_type": "paragraph", "runs": [...], "style": {...} } ],
  "total": 42,
  "offset": 0,
  "limit": 50,
  "has_more": false,
  "source_path": "/path/simple.docx"
}
```

**get_styles:**

```json
{
  "paragraph_styles": [ { "name": "Heading 1", "font_size_pt": 14.0, ... } ],
  "section": { "left_margin_cm": 3.0, ... },
  "total": 33,
  "offset": 0,
  "limit": 50,
  "has_more": false,
  "source_path": "/path/format.docx"
}
```

`section` is present when `offset == 0`, omitted otherwise.

## Implementation tasks

1. Create `ReadService` accepting `DocxAdapter` via constructor (dependency injection)

2. Implement `get_contents(file_path: str, offset: int = 0, limit: int = 50) -> dict`:
   - Call `adapter.read_document(file_path)`
   - Slice `blocks[offset : offset + limit]`
   - Return paginated envelope with `items` as block dicts

3. Implement `get_styles(file_path: str, offset: int = 0, limit: int = 50) -> dict`:
   - Call `adapter.inspect_styles(file_path)`
   - Slice `paragraph_styles[offset : offset + limit]`
   - Include `section` when `offset == 0`

4. Validate `offset >= 0`, `limit > 0` (cap max limit e.g. 200)

5. Catch `DocxMcpError` and re-raise; wrap unexpected exceptions as `INTERNAL_ERROR`

6. Write tests:
   - Batch contents from programmatic `.docx` with headings, paragraphs, table
   - Verify `offset`/`limit` pagination and `has_more`
   - Batch styles; verify `section` only on first page
   - Verify missing file returns structured error

## Acceptance criteria

- [ ] `get_contents()` returns paginated `DocumentBlock` dicts in `items`
- [ ] `get_styles()` returns paginated `paragraph_styles` with `section` on first batch
- [ ] `has_more` correctly reflects remaining items
- [ ] File-not-found raises `DocxMcpError` with code `FILE_NOT_FOUND`
- [ ] `uv run pytest tests/test_read_service.py` passes
- [ ] No `docx` imports in `services/read_service.py`

## README impact

None (documented in SP-07).

## Risks

| Risk | Mitigation |
|---|---|
| Large documents re-parsed on every batch call | Document in SP-07; cache deferred |
| Agent requests huge `limit` | Cap at 200 blocks/styles per call |
