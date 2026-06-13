# SP-08: Examples and Cursor Integration

## Goal

Provide copy-paste examples for agents and users demonstrating the reformat user story end-to-end via the four MCP read/write tools. Enable quick onboarding without reading the full README.

## Depends on

SP-07.

## In scope

- `examples/cursor_reformat_prompt.md` — sample user prompt and expected agent workflow
- Sample agent tool-call sequence with fixture file names
- Optional demo `.docx` files in `examples/` (or reference to `tests/assets/`)
- Link from README to examples section

## Out of scope

- Video tutorials
- Non-Cursor MCP client configs (can mention but not primary focus)
- Automated example scripts (optional nice-to-have, not required)

## Files to create/modify

| Path | Action |
|---|---|
| `examples/cursor_reformat_prompt.md` | Create |
| `examples/source_draft.docx` | Create (optional, or symlink/copy from assets) |
| `examples/company_template.docx` | Create (optional, or symlink/copy from assets) |
| `README.md` | Add link to examples section |

## Implementation tasks

1. Create `examples/cursor_reformat_prompt.md` with sections:
   - **Scenario** — reformat report to company template
   - **User prompt** — copy-paste example:
     > Reformat `report_draft.docx` to match `company_template.docx`. Save as `report_final.docx`.
   - **Expected agent workflow** — four-tool batch sequence
   - **Tool call examples** — JSON parameter examples for each tool
   - **Tool order** — `write_contents` before `write_styles`; styles from format.docx win on conflict
   - **Success criteria** — what the agent should report to the user

2. Copy or reference test assets as demo files:
   - `tests/assets/plain.docx` → draft content
   - `tests/assets/format.docx` → template styles

3. Add **Examples** section to README linking to `examples/cursor_reformat_prompt.md`

4. Verify example workflow manually with all four tools (same steps as `tests/test_reformat_pipeline.py`)

## Acceptance criteria

- [ ] `examples/cursor_reformat_prompt.md` exists with complete agent workflow
- [ ] Example prompt and tool sequence match SP-06 tool signatures
- [ ] README links to examples
- [ ] Manual execution of four-tool workflow with asset files succeeds
- [ ] `tests/test_reformat_pipeline.py` mirrors the example workflow (SP-05)
- [ ] Document explains batch pagination (`offset`, `limit`, `has_more`)

## README impact

Add **Examples** section with link to `examples/cursor_reformat_prompt.md`.

## Example agent workflow (reference)

```
# Step 1 — read content from simple.docx (paginated)
get_contents_from_docx(file_path="report_draft.docx", offset=0, limit=50)
# loop: offset += limit while has_more == true

# Step 2 — read styles from format.docx (paginated)
get_styles_from_docx(file_path="company_template.docx", offset=0, limit=50)
# loop while has_more; merge paragraph_styles into one StyleProfile dict
# section comes in first batch (offset=0)

# Step 3 — write content to output (creates file if missing)
write_contents_to_docx(
  file_path="report_final.docx",
  contents=[ ...all blocks from step 1... ]
)

# Step 4 — union format styles onto output (file must exist)
write_styles_to_docx(
  file_path="report_final.docx",
  styles={
    "paragraph_styles": [ ...merged from step 2... ],
    "section": { ...from step 2 first batch... }
  }
)
# incoming styles win when same name differs from existing file

# Report: output path, blocks_written, styles_added, styles_updated
```

## Risks

| Risk | Mitigation |
|---|---|
| Agent skips style batching and requests huge limit | Document recommended limit=50 |
| Agent calls write_styles before write_contents | Document required order; FILE_NOT_FOUND error is clear |
| Example files out of sync with assets | Copy assets once; note source in example doc |
