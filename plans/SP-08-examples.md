# SP-08: Examples and Cursor Integration

## Goal

Provide copy-paste examples for agents and users demonstrating the reformat user story end-to-end via MCP tools. Enable quick onboarding without reading the full README.

## Depends on

SP-07.

## In scope

- `examples/cursor_reformat_prompt.md` — sample user prompt and expected agent workflow
- Sample agent tool-call sequence with fixture file names
- Optional demo `.docx` files in `examples/` (or reference to `tests/fixtures/`)
- Link from README to examples section

## Out of scope

- Video tutorials
- Non-Cursor MCP client configs (can mention but not primary focus)
- Automated example scripts (optional nice-to-have, not required)

## Files to create/modify

| Path | Action |
|---|---|
| `examples/cursor_reformat_prompt.md` | Create |
| `examples/source_draft.docx` | Create (optional, or symlink/copy from fixtures) |
| `examples/company_template.docx` | Create (optional, or symlink/copy from fixtures) |
| `README.md` | Add link to examples section |

## Implementation tasks

1. Create `examples/cursor_reformat_prompt.md` with sections:
   - **Scenario** — business context (reformat report to company template)
   - **User prompt** — copy-paste example:
     > Reformat `report_draft.docx` to match `company_template.docx`. Save as `report_final.docx`.
   - **Expected agent workflow** — numbered steps calling MCP tools
   - **Tool call examples** — JSON-like parameter examples for each tool
   - **Handling unmapped styles** — when to build and pass `style_map`
   - **Success criteria** — what the agent should report to the user

2. Copy or reference test fixtures as demo files:
   - Either copy `tests/fixtures/source.docx` → `examples/report_draft.docx`
   - Or document that examples use `tests/fixtures/` paths

3. Add **Examples** section to README linking to `examples/cursor_reformat_prompt.md`

4. Verify example workflow produces expected output when executed manually:
   - `inspect_styles` → `read_docx` → `reformat_docx`
   - Output file created with correct stats

## Acceptance criteria

- [ ] `examples/cursor_reformat_prompt.md` exists with complete agent workflow
- [ ] Example prompt and tool sequence match SP-06 tool signatures
- [ ] README links to examples
- [ ] Manual execution of example workflow with fixture files succeeds
- [ ] Document explains how to handle `unmapped_styles` in tool response

## README impact

Add **Examples** section with link to `examples/cursor_reformat_prompt.md`.

## Example agent workflow (reference)

```
1. inspect_styles(template_path="company_template.docx")
2. read_docx(path="report_draft.docx", include_styles=true)
3. (optional) build style_map for custom styles
4. reformat_docx(
     source_path="report_draft.docx",
     template_path="company_template.docx",
     output_path="report_final.docx",
     style_map={"ReportTitle": "Title"}  # optional
   )
5. Report: output path, paragraphs_written, tables_written, unmapped_styles
```

## Risks

| Risk | Mitigation |
|---|---|
| Example files out of sync with fixtures | Copy fixtures once; note source in example doc |
| Agent skips inspect_styles step | Document why style inspection helps with style_map |
