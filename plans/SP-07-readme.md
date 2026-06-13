# SP-07: README.md and Documentation

## Goal

Write complete user-facing documentation covering installation, architecture, MCP tool reference, the reformat user story, known limitations, and development workflow.

## Depends on

SP-06.

## In scope

- Full `README.md` replacing the SP-01 stub
- All sections from master plan README outline
- Accurate tool parameters and JSON response examples matching implemented code
- Architecture diagram (mermaid)
- Quick start that works on a clean clone
- Style mapping rules documentation
- Known limitations section
- Roadmap for future subplans (SP-09+)

## Out of scope

- Agent prompt examples (SP-08)
- API reference beyond MCP tools
- Contributing guide (unless minimal dev section suffices)

## Files to create/modify

| Path | Action |
|---|---|
| `README.md` | Replace stub with full documentation |

## Implementation tasks

1. **Title and description** — MCP server for `.docx`, Python 3.11+
2. **Features** — list v1 tools: `read_docx`, `inspect_styles`, `reformat_docx`
3. **Architecture** — mermaid diagram from master plan; explain layer rules
4. **Tech stack** — python-docx, MCP Python SDK, uv
5. **Quick start**:
   - Clone repo
   - `uv sync --extra dev`
   - Add Cursor MCP config (absolute path placeholder)
   - Smoke test command
6. **Tools reference** — for each tool:
   - Parameters with types and defaults
   - Example request (conceptual)
   - Example JSON response
   - Error response format
7. **User story: Reformat by template**:
   - Example user prompt
   - Agent workflow (5 steps from master plan)
8. **Style mapping rules** — table with priority order
9. **Known limitations** — headers/footers, images, text boxes, footnotes, numbering
10. **Development** — `uv run pytest`, project layout, link to `AGENTS.md`
11. **Roadmap** — SP-09 through SP-13 topics

## Acceptance criteria

- [ ] README accurately reflects implemented MCP tools and parameters
- [ ] Quick start steps work on clean clone (`uv sync`, `uv run pytest`, `uv run docx-mcp`)
- [ ] Architecture diagram matches actual package structure
- [ ] Style mapping rules match `StyleMapper` behavior
- [ ] Known limitations list matches SP-05 scope exclusions
- [ ] Cursor MCP config snippet included with path placeholder note

## README impact

Full document — replaces SP-01 stub entirely.

## Risks

| Risk | Mitigation |
|---|---|
| README drifts from code | Verify all tool params against `server.py` before marking done |
| Quick start fails on different OS | Use portable commands (uv, no OS-specific paths) |
