# SP-02: Domain Models and Contracts

## Goal

Define stable, I/O-free domain types used as the contract between services and adapters. All models must support JSON serialization for MCP tool responses.

## Depends on

SP-01.

## In scope

- `DocumentModel` — top-level document representation with **document-level style catalog**
- `ParagraphBlock`, `TableBlock`, `TableCellBlock` — content blocks (structure + text only)
- `RunFormat`, `StyleHint` — inline formatting and **style name references** on blocks
- `StyleProfile`, `ParagraphStyleInfo`, `SectionSetup` — full style definitions (font + paragraph format)
- `ReformatResult`, `ReformatStats` — reformat operation output
- `to_dict()` / `from_dict()` on all models
- Unit tests in `tests/test_domain_models.py`

## User pipeline (reformat)

1. User creates a plain `.docx` with default Word styles (`plain.docx`).
2. Agent reads **content blocks** from plain file and **style catalog** from template file (`format.docx`).
3. Agent (or service) transfers template styles onto the plain document — user gets formatted output.

**Design rule:** full style definitions live on `DocumentModel.styles`, not nested inside `blocks`. Blocks carry only a `StyleHint` (style name reference); font, paragraph spacing, alignment, etc. are resolved from `DocumentModel.styles.get_paragraph_style(name)`.

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
2. Implement `StyleHint` with fields: `name`, `style_type` (reference only — no full style payload)
3. Implement `ParagraphBlock` with `runs`, `style` (hint), computed `text` property
4. Implement `TableCellBlock` and `TableBlock` with nested paragraph support
5. Implement `DocumentModel` with:
   - `blocks: list[DocumentBlock]` — document body content
   - `styles: StyleProfile` — **full paragraph style catalog + section setup**
   - `source_path: str | None`
6. Implement `ReformatStats` and `ReformatResult`
7. Implement `ParagraphStyleInfo` with font **and** paragraph format fields:
   - Font: `font_name`, `font_size_pt`, `bold`, `italic`
   - Paragraph: `alignment`, `line_spacing`, `space_before_pt`, `space_after_pt`, indents
   - Metadata: `name`, `base_style`
8. Implement `SectionSetup`, `StyleProfile` with `style_names()` and `get_paragraph_style(name)` helpers
9. Add `to_dict()` / `from_dict()` to all models
10. Write unit tests: roundtrip serialization, JSON encode/decode, `DocumentModel.styles` roundtrip

## Acceptance criteria

- [ ] All models have `to_dict()` returning JSON-serializable dicts
- [ ] `from_dict()` restores models from dicts produced by `to_dict()`
- [ ] `DocumentModel` roundtrips through `json.dumps` / `json.loads` including `styles`
- [ ] `DocumentModel.styles` holds full style catalog; blocks hold `StyleHint` references only
- [ ] `StyleProfile.get_paragraph_style("Heading 1")` returns font + paragraph fields
- [ ] `StyleProfile.style_names()` returns list of paragraph style names
- [ ] `uv run pytest tests/test_domain_models.py` passes

## README impact

None.

## Risks

| Risk | Mitigation |
|---|---|
| Union type `DocumentBlock` complicates deserialization | Use `block_type` discriminator field in `from_dict()` |
| Style inheritance in Word not fully resolved | Store `base_style` link; resolve at reformat time in adapter |
