# SP-05: ReformatService (User Story #1 Core)

## Goal

Implement the template-as-base reformat workflow: extract content from a source document, apply it to a template document preserving the template's styles and page setup, and save the result. This is the core of user story #1.

## Depends on

SP-04.

## In scope

- `ReformatService` orchestrating template-as-base reformat
- Algorithm: extract source blocks → open template → clear body → map styles → write blocks → save
- Style mapping via `StyleMapper` (exact → custom map → heading fallback → Normal)
- `ReformatResult` with stats: paragraphs written, tables written, unmapped styles
- Test fixtures: `tests/fixtures/source.docx`, `tests/fixtures/template.docx`
- Integration tests verifying output uses template styles and margins

## Out of scope

- MCP server wiring (SP-06)
- Headers/footers field content
- Floating images, text boxes, footnotes
- Numbering restart
- Run-level formatting when named style exists (deferred to SP-10)

## Files to create/modify

| Path | Action |
|---|---|
| `src/docx_mcp/services/reformat_service.py` | Create |
| `tests/test_reformat_service.py` | Create |
| `tests/fixtures/source.docx` | Create |
| `tests/fixtures/template.docx` | Create |
| `tests/conftest.py` | Create (optional shared fixture helpers) |

## Implementation tasks

1. Create test fixtures programmatically:
   - **source.docx**: Title, Heading 1, Normal paragraphs, one table, optional custom style
   - **template.docx**: Different font sizes/margins, standard Word styles, empty body content preferred

2. Create `ReformatService` accepting `DocxAdapter` via constructor

3. Implement `reformat(source_path, template_path, output_path, style_map=None) -> dict`:
   - Validate all three paths
   - Delegate to `adapter.reformat(...)` or orchestrate adapter methods
   - Return `ReformatResult.to_dict()`

4. Verify output document:
   - Uses template section margins (compare EMU values)
   - Paragraph styles match mapped names (e.g. `Heading 1` in source → `Heading 1` in output)
   - Content text preserved from source
   - `unmapped_styles` reported when source has styles not in template

5. Write integration tests:
   - End-to-end reformat with fixtures
   - Custom `style_map` resolves unmapped custom style
   - Output file exists and is valid `.docx`
   - Stats reflect correct paragraph/table counts

## Acceptance criteria

- [ ] Reformat output uses template page margins
- [ ] Source content text is preserved in output
- [ ] Named styles mapped correctly (exact match)
- [ ] Custom `style_map` resolves non-standard style names
- [ ] `unmapped_styles` list populated when styles cannot be mapped
- [ ] `uv run pytest tests/test_reformat_service.py` passes
- [ ] Known limitations documented in test comments

## README impact

None (documented in SP-07).

## Risks

| Risk | Mitigation |
|---|---|
| Template with existing body content duplicated | `_clear_document_body()` before writing blocks |
| Custom styles in source not in template | Report in `unmapped_styles`; agent can supply `style_map` |
| Table styling lost | Use `Table Grid` style; document limitation for v1 |

## Style mapping reference

| Priority | Rule | Example |
|---|---|---|
| 1 | Exact name match | `Heading 1` → `Heading 1` |
| 2 | Agent `style_map` | `ReportTitle` → `Title` |
| 3 | Nearest heading level | `Heading 3` → `Heading 2` (if H3 missing) |
| 4 | Fallback | → `Normal` |
