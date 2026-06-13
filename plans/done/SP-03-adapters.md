# SP-03: Docx Adapters

## Goal

Isolate all `python-docx` library access behind adapter classes. Services must never import `docx` directly — all document I/O goes through this layer.

## Depends on

SP-02.

## In scope

- `DocxAdapter` — open, save, read, inspect styles, reformat orchestration
- `ContentExtractor` — extract content **blocks** from a python-docx `Document`
- `StyleExtractor` — extract **full style catalog** (font + paragraph format) into `StyleProfile`
- `StyleMapper` — map source style names to template style names
- Path validation helpers (read/write)
- Block iteration preserving paragraph/table document order
- Unit tests for `StyleMapper`, `ContentExtractor`, and asset loading

## User pipeline (reformat)

1. `read_document(plain.docx)` → `DocumentModel` with blocks + default `styles`
2. `read_document(format.docx)` or `inspect_styles(format.docx)` → template `StyleProfile`
3. Reformat service copies template styles onto plain document body (SP-05)

`read_document()` must populate **both** `blocks` and `styles` on `DocumentModel`. Blocks reference styles by name (`StyleHint`); full definitions are in `DocumentModel.styles`.

## Out of scope

- Service layer (thin wrappers in SP-04/SP-05)
- MCP server and tools
- Full reformat integration tests (SP-05)
- Headers/footers, floating images, text boxes, footnotes

## Files to create/modify

| Path | Action |
|---|---|
| `src/docx_mcp/adapters/docx_adapter.py` | Create |
| `src/docx_mcp/adapters/content_extractor.py` | Create |
| `src/docx_mcp/adapters/style_extractor.py` | Create |
| `src/docx_mcp/adapters/style_mapper.py` | Create |
| `tests/test_style_mapper.py` | Create |
| `tests/test_content_extractor.py` | Create |
| `tests/test_load_assets.py` | Create |

## Implementation tasks

1. **StyleMapper**
   - Constructor accepts `template_style_names: list[str]` and optional `custom_map: dict[str, str]`
   - `map_style(source_style)` with priority:
     1. Exact name match in template styles
     2. Entry in `custom_map`
     3. Nearest heading fallback (`Heading N` → `Heading min(N, available)`)
     4. Fallback to `Normal` or first available template style
   - Track `unmapped_styles` for reporting

2. **StyleExtractor**
   - Extract all paragraph styles from `document.styles`
   - For each style capture font properties (`font_name`, `font_size_pt`, `bold`, `italic`) and paragraph format (`alignment`, spacing, indents)
   - Extract `SectionSetup` from first document section
   - `extract(document, source_path) -> StyleProfile`

3. **ContentExtractor**
   - Implement `iter_block_items()` to preserve paragraph/table order in document body
   - Extract `ParagraphBlock` with runs and **style name hint only** (`StyleHint`)
   - Extract `TableBlock` with nested cell paragraphs
   - `extract(document, source_path) -> DocumentModel` (blocks only; adapter attaches styles)

4. **DocxAdapter**
   - `open(path)` / `save(document, path)` with path validation
   - `read_document(path) -> DocumentModel` with populated `blocks` **and** `styles`
   - `inspect_styles(path) -> StyleProfile` (delegates to `StyleExtractor`)
   - `_clear_document_body()` — remove body content, keep `sectPr` and styles
   - `_write_paragraph()` / `_write_table()` — write domain blocks to document
   - Raise `DocxMcpError` on invalid paths and parse failures

5. Write unit tests for style mapping edge cases
6. Write unit tests for content extraction using programmatically created documents
7. Write integration tests loading `tests/assets/plain.docx` and `format.docx` asserting `DocumentModel.styles`

## Acceptance criteria

- [ ] No `docx` imports outside `adapters/` package
- [ ] `StyleMapper` exact match, custom map, heading fallback, and Normal fallback all tested
- [ ] `ContentExtractor` preserves paragraph/table order
- [ ] `StyleExtractor` captures font + paragraph format for styles like `Heading 1`
- [ ] `DocxAdapter.read_document()` returns `DocumentModel` with non-empty `styles.paragraph_styles`
- [ ] `DocxAdapter.inspect_styles()` returns `StyleProfile` with paragraph styles and margins
- [ ] Invalid paths raise structured `DocxMcpError`
- [ ] `uv run pytest tests/test_load_assets.py` passes

## README impact

None.

## Risks

| Risk | Mitigation |
|---|---|
| python-docx flat `document.paragraphs` loses table order | Use `iter_block_items()` on document body XML |
| Style type detection varies across python-docx versions | Check `style.type == 1` (WD_STYLE_TYPE.PARAGRAPH) with fallback |
| Inherited style values show as `None` in python-docx | Store `base_style`; copy resolved values at reformat time |
