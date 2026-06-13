# SP-02: Domain Models and Contracts

## Goal

Define stable, I/O-free domain types used as the contract between services and adapters. All models must support JSON serialization for MCP tool responses.

## Depends on

SP-01.

## In scope

- `DocumentModel` — top-level document representation
- `ParagraphBlock`, `TableBlock`, `TableCellBlock` — content blocks
- `RunFormat`, `StyleHint` — inline formatting and style references
- `StyleProfile`, `ParagraphStyleInfo`, `SectionSetup` — template style snapshot
- `ReformatResult`, `ReformatStats` — reformat operation output
- `to_dict()` / `from_dict()` on all models
- Unit tests in `tests/test_domain_models.py`

## Out of scope

- python-docx imports
- Adapters and services
- MCP tools
- File I/O of any kind

## Files to create/modify

| Path | Action |
|---|---|
| `src/docx_mcp/domain/models.py` | Create |
| `src/docx_mcp/domain/style_profile.py` | Create |
| `tests/test_domain_models.py` | Create |

## Implementation tasks

1. Implement `RunFormat` with fields: `text`, `bold`, `italic`, `font_name`, `font_size_pt`
2. Implement `StyleHint` with fields: `name`, `style_type`
3. Implement `ParagraphBlock` with `runs`, `style`, computed `text` property
4. Implement `TableCellBlock` and `TableBlock` with nested paragraph support
5. Implement `DocumentModel` with `blocks: list[DocumentBlock]` and optional `source_path`
6. Implement `ReformatStats` and `ReformatResult`
7. Implement `ParagraphStyleInfo`, `SectionSetup`, `StyleProfile` with `style_names()` helper
8. Add `to_dict()` / `from_dict()` to all models
9. Write unit tests: roundtrip serialization, JSON encode/decode, edge cases (empty blocks)

## Acceptance criteria

- [ ] All models have `to_dict()` returning JSON-serializable dicts
- [ ] `from_dict()` restores models from dicts produced by `to_dict()`
- [ ] `DocumentModel` roundtrips through `json.dumps` / `json.loads`
- [ ] `StyleProfile.style_names()` returns list of paragraph style names
- [ ] `uv run pytest tests/test_domain_models.py` passes

## README impact

None.

## Risks

| Risk | Mitigation |
|---|---|
| Union type `DocumentBlock` complicates deserialization | Use `block_type` discriminator field in `from_dict()` |
