# SP-05: WriteService (User Story #1 Core)

## Goal

Implement write-side operations for the agent-driven reformat workflow: write content blocks to a `.docx` file (create if missing) and union style definitions onto an existing file (**incoming styles from `format.docx` are master** on name conflict). Backend for `write_contents_to_docx` and `write_styles_to_docx` MCP tools.

## Depends on

SP-04.

## In scope

- `WriteService` orchestrating content write and style union
- `StyleProfile.union_with(other, master="other")` in domain — merge catalogs; master wins on name conflict
- `StyleMigrator` — apply merged `StyleProfile` definitions to python-docx document
- `ContentWriter` — write/replace document body blocks
- `write_contents(file_path, contents) -> dict` — create new or replace body in existing file
- `write_styles(file_path, styles) -> dict` — union styles onto **existing** file
- Test fixtures and integration tests for user story #1 pipeline

## Out of scope

- MCP server wiring (SP-06)
- Monolithic `reformat_docx` tool (agent orchestrates via 4 MCP tools)
- Headers/footers field content
- Floating images, text boxes, footnotes
- Numbering restart
- Run-level formatting when named style exists (deferred to SP-10)

## Files to create/modify

| Path | Action |
|---|---|
| `src/docx_mcp/domain/style_profile.py` | Modify — add `union_with()` |
| `src/docx_mcp/adapters/content_writer.py` | Create |
| `src/docx_mcp/adapters/style_migrator.py` | Create |
| `src/docx_mcp/adapters/docx_adapter.py` | Modify — add `write_contents()`, `write_styles()` |
| `src/docx_mcp/services/write_service.py` | Create |
| `tests/test_content_writer.py` | Create |
| `tests/test_style_migrator.py` | Create |
| `tests/test_write_service.py` | Create |
| `tests/test_reformat_pipeline.py` | Create — end-to-end asset pipeline test (see below) |
| `tests/conftest.py` | Create — shared fixtures + assertion helpers |

## User pipeline (agent-orchestrated via MCP)

```
simple.docx                              format.docx
    │                                         │
    ├─ get_contents_from_docx (batches)       ├─ get_styles_from_docx (batches)
    │                                         │
    └──────────────┬──────────────────────────┘
                   ▼
         write_contents_to_docx(output.docx)   ← create if not exists
                   ▼
         write_styles_to_docx(output.docx)      ← union; format.docx wins
                   ▼
              formatted output
```

1. **Read struct** — agent batches `get_contents_from_docx(simple.docx, offset, limit)`
2. **Distill styles** — agent batches `get_styles_from_docx(format.docx, offset, limit)`
3. **Write content** — `write_contents_to_docx(output.docx, contents)` — new file OK
4. **Union styles** — `write_styles_to_docx(output.docx, styles)` — file must exist; **format.docx definitions win** on conflict

## Style union rule (`write_styles_to_docx`)

| Case | Action |
|---|---|
| Style only in incoming `styles` (from format.docx) | Add to target document |
| Style only in existing file | Keep |
| Same name, different definition | **Incoming styles win** — overwrite target |
| Section setup in incoming `styles` | Apply from incoming profile |

## MCP tool mapping

| MCP tool | Service method | File must exist |
|---|---|---|
| `write_contents_to_docx(file_path, contents)` | `WriteService.write_contents()` | No — creates new |
| `write_styles_to_docx(file_path, styles)` | `WriteService.write_styles()` | Yes |

## Response shapes

**write_contents:**

```json
{
  "file_path": "/path/output.docx",
  "blocks_written": 12,
  "created": true
}
```

**write_styles:**

```json
{
  "file_path": "/path/output.docx",
  "styles_added": 5,
  "styles_updated": 12,
  "styles_unchanged": 8
}
```

## Implementation tasks

1. Implement `StyleProfile.union_with(other, master="other") -> StyleProfile`:
   - Start from `self` styles; overlay styles from `other`
   - On same `name`: keep definition from `master` profile
   - Merge `section` from master when present

2. Create `ContentWriter`:
   - `write(document, blocks, *, replace=True) -> int` — clear body if replace, write blocks, return count

3. Create `StyleMigrator`:
   - `apply(document, merged_profile) -> tuple[int, int, int]` — (added, updated, unchanged)
   - Apply `SectionSetup` to first document section

4. Extend `DocxAdapter`:
   - `create_document() -> DocxDocument` — blank document with default styles
   - `write_contents(path, blocks, *, replace=True) -> int`
   - `write_styles(path, styles_profile) -> tuple[int, int, int]` — open existing, union, save

5. Create `WriteService` accepting `DocxAdapter` via constructor

6. Implement `write_contents(file_path, contents: list[dict]) -> dict`:
   - Parse blocks from dicts via `DocumentModel.from_dict` / block `from_dict`
   - If file missing → create new document; else open and replace body
   - Return stats

7. Implement `write_styles(file_path, styles: dict) -> dict`:
   - Require existing file (`FILE_NOT_FOUND` if missing)
   - Parse `StyleProfile.from_dict(styles)`
   - Extract current styles from file; `union_with(incoming, master="other")`
   - Apply via `StyleMigrator`; return stats

8. Write integration tests — see **Integration test plan: asset pipeline** below

## Integration test plan: asset pipeline

End-to-end test reproducing the agent MCP workflow against real fixtures **without creating a physical output file on disk**.
File: `tests/test_reformat_pipeline.py`, class `TestReformatAssetPipeline`.

### Design rule: no output file on disk

- **Read-only** from existing assets: `tests/assets/plain.docx`, `tests/assets/format.docx`
- Steps 4–6 apply writes to an **in-memory** `DocxDocument` via adapter layer (`create_document()` → `ContentWriter` → `StyleMigrator`)
- Steps 7–8 compare domain models extracted from the in-memory document — **no `save()`**, no `tmp_path`, no new `.docx` file
- File I/O for `write_contents` / `write_styles` (path not found, create file) is tested separately in `tests/test_write_service.py` with mocks or isolated unit tests

### Asset paths (read-only)

| Role | Path | Alias in test |
|---|---|---|
| Simple (content source) | `tests/assets/plain.docx` | `SIMPLE_DOCX` |
| Format (style source) | `tests/assets/format.docx` | `FORMAT_DOCX` |
| Output | in-memory `DocxDocument` | `output_doc` |

### Pipeline steps (maps to MCP tools)

| Step | Action | Test implementation |
|---|---|---|
| 1 | Get asset format file | Assert `FORMAT_DOCX.exists()` |
| 2 | Get asset simple file | Assert `SIMPLE_DOCX.exists()` |
| 3 | From simple — get contents | `ReadService.get_contents(SIMPLE_DOCX, …)` — collect all batches |
| 4 | Write contents (in-memory) | `output_doc = adapter.create_document()` → `ContentWriter.write(output_doc, blocks)` |
| 5 | From format — get styles | `ReadService.get_styles(FORMAT_DOCX, …)` — collect all batches |
| 6 | Write styles (in-memory) | `merged = existing.union_with(incoming, master="other")` → `StyleMigrator.apply(output_doc, merged)` |
| 7 | Assert content equals simple | Extract blocks from `output_doc` vs `SIMPLE_DOCX` |
| 8 | Assert styles equals format ∪ simple | Extract styles from `output_doc` vs expected union profile |

Steps 4 and 6 mirror `WriteService` logic but skip path validation and `save()`.

### Step 3 — collect all contents (pagination loop)

```python
def collect_all_contents(read_service, file_path: str, limit: int = 50) -> list[dict]:
    items: list[dict] = []
    offset = 0
    while True:
        batch = read_service.get_contents(file_path, offset=offset, limit=limit)
        items.extend(batch["items"])
        if not batch["has_more"]:
            break
        offset += limit
    return items
```

### Step 5 — collect all styles (pagination loop)

```python
def collect_all_styles(read_service, file_path: str, limit: int = 50) -> dict:
    paragraph_styles: list[dict] = []
    section: dict | None = None
    offset = 0
    while True:
        batch = read_service.get_styles(file_path, offset=offset, limit=limit)
        if offset == 0:
            section = batch.get("section")
        paragraph_styles.extend(batch["paragraph_styles"])
        if not batch["has_more"]:
            break
        offset += limit
    return {"paragraph_styles": paragraph_styles, "section": section}
```

### Step 4 — write contents in memory

```python
output_doc = adapter.create_document()
blocks = [DocumentModel._block_from_dict(b) for b in contents]  # or block from_dict helpers
blocks_written = content_writer.write(output_doc, blocks, replace=True)
```

### Step 6 — union styles in memory

```python
existing = style_extractor.extract(output_doc)
incoming = StyleProfile.from_dict(format_styles_dict)
merged = existing.union_with(incoming, master="other")  # format wins
style_migrator.apply(output_doc, merged)
```

### Step 7 — assert content equality

Helper: `assert_blocks_equal(actual_blocks, expected_blocks)` in `tests/conftest.py`.

Build expected from asset read (no second file):

```python
expected_doc = adapter.read_document(SIMPLE_DOCX)
actual_blocks = content_extractor.extract(output_doc, source_path=None).blocks
assert_blocks_equal(actual_blocks, expected_doc.blocks)
```

| Field | Rule |
|---|---|
| Block count | Same length |
| Block type | Same `block_type` per index |
| Paragraph text | Same `block.text` |
| Style hint | Same `block.style.name` when present |
| Table shape | Same row/column count; same cell paragraph texts |

Do **not** compare inline run formatting — styles are applied in step 6.

### Step 8 — assert styles equality (format ∪ simple)

Helper: `assert_styles_equal(actual: StyleProfile, expected: StyleProfile)` in `tests/conftest.py`.

```python
simple_styles = adapter.inspect_styles(SIMPLE_DOCX)
format_styles = adapter.inspect_styles(FORMAT_DOCX)
expected = simple_styles.union_with(format_styles, master="other")
actual = style_extractor.extract(output_doc)
assert_styles_equal(actual, expected)
```

Spot checks proving union rule (format wins):

| Style | Source | Expected value from |
|---|---|---|
| `Heading 1` | both, differ | **format.docx** — `space_before_pt == 18.0` |
| `Normal` | both, differ | **format.docx** — `font_name == "Times New Roman"` |
| `КОД` | format only | Present in output |
| `macro` | simple only | Present in output (kept from union) |

### Test cases

| Test name | Scope |
|---|---|
| `test_asset_files_exist` | Steps 1–2 |
| `test_reformat_pipeline_end_to_end` | Steps 3–8 in-memory pipeline |
| `test_write_styles_requires_existing_file` | In `test_write_service.py` — mocked path → `FILE_NOT_FOUND` |

### Acceptance criteria (pipeline test)

- [ ] `test_reformat_pipeline_end_to_end` passes with `plain.docx` + `format.docx`
- [ ] No output `.docx` file created on disk during pipeline test
- [ ] Step 7: in-memory blocks match simple file content
- [ ] Step 8: in-memory styles match `simple.union_with(format, master=format)`
- [ ] `Heading 1` spacing from format.docx, not plain.docx
- [ ] Custom style `КОД` present; simple-only `macro` retained
- [ ] `uv run pytest tests/test_reformat_pipeline.py` passes

## Acceptance criteria

- [ ] `StyleProfile.union_with()` merges catalogs; incoming (format) wins on name conflict
- [ ] `write_contents_to_docx` creates file when path not found
- [ ] `write_contents_to_docx` replaces body when file exists
- [ ] `write_styles_to_docx` requires existing file; unions styles with incoming as master
- [ ] Template-only user styles (e.g. `КОД`) present after union
- [ ] Section setup from format.docx applied
- [ ] `uv run pytest tests/test_write_service.py tests/test_style_migrator.py tests/test_content_writer.py tests/test_reformat_pipeline.py` passes

## README impact

None (documented in SP-07).

## Risks

| Risk | Mitigation |
|---|---|
| Agent calls `write_styles` before `write_contents` | Document tool order in SP-08; return clear error if file missing |
| python-docx cannot create all custom style types | Test with fixture `КОД` style; document limitation |
| Inherited style values show as `None` | Resolve from `base_style` chain before writing |
