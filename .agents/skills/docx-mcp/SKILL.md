---
name: docx-mcp
description: >-
  Read and write .docx files via the docs-mcp MCP server — batch content reads,
  style catalog reads, batch content write, and batch style union. Use when the
  user asks to reformat a Word document, apply a template, read/write .docx content
  or styles, or when docs-mcp MCP tools are available.
---

# docs-mcp — Agent Workflow

MCP server with five tools. **No monolithic reformat tool** — the agent orchestrates plan, reads, style mapping, and writes in the correct order with pagination.

## MCP-only rule (mandatory)

**All reads and writes MUST use MCP tools** (`CallMcpTool` / `user-docs-mcp`). Never bypass the server.

| Allowed | Forbidden |
|---|---|
| `get_contents_from_docx`, `write_contents_to_docx`, … via MCP | `import docx_mcp`, `WriteService`, `ReadService`, `DocxAdapter` |
| Read spill file → parse JSON → MCP write | `uv run python` scripts that call library code |
| Verify via `get_styles_from_docx` on output + template | Shell orchestration with direct python-docx |

Working with `.docx` files means working **only through the MCP server**. External code paths produce results that are **not valid** for the user's workflow and must be treated as errors.

### Spill-file pattern

When a large read response is saved to an `agent-tools/*.txt` file instead of inline context:

1. **Read** the spill file with the Read tool (not Shell).
2. **Parse** JSON; extract `items` or `paragraph_styles` + `section`.
3. **Write** the same data back through MCP in batches (see below).

> Forbidden: read via MCP → write via Python.  
> Allowed: read spill file → write via MCP.

## When to use

- Reformat a draft `.docx` using another file's styles (template)
- Read document structure (paragraphs, tables) in batches
- Write or replace document body content in batches
- Apply or merge paragraph styles and page setup onto an existing file in batches

## Prerequisites

- MCP server `docs-mcp` configured in the host (stdio via `uv run docx-mcp` or `docker run --rm -i docs-mcp`)
- File paths come from **tool call parameters** (`file_path`), not from server build or MCP config
- Native: host paths. Docker: paths inside the container; add `-v host:container` to `docker run` only if files live on the host

## Tools

| Tool | Purpose | Default limit |
|---|---|---|
| `plan_reformat_docx` | Analyze draft vs template; suggested style map | sample_blocks=10 |
| `get_contents_from_docx` | Batch-read content blocks | 10 |
| `get_styles_from_docx` | Batch-read style catalog | 25 |
| `write_contents_to_docx` | Batch-write blocks; optional `style_map` | max 200/call |
| `write_styles_to_docx` | Batch union styles onto existing file | max 200/call |

Max `limit` per read call: **200**. Use **limit=200** for reformat to minimize round-trips.

## Reformat workflow (template apply)

Copy this checklist and track progress:

```
- [ ] Step 0: plan_reformat_docx(draft, template) — review suggested_style_map
- [ ] Step 1: Paginate get_contents_from_docx on draft (limit=200)
- [ ] Step 2: Paginate get_styles_from_docx on template (limit=200)
- [ ] Step 3: write_contents_to_docx with style_map (or patch style.name in batches)
- [ ] Step 4: Paginate write_styles_to_docx on same output path (mirror read batches)
- [ ] Step 5 (verify): plan_reformat_docx(draft, output) — unmapped styles empty
- [ ] Step 6 (optional): get_styles_from_docx on output + template — compare Heading 1/2
```

```
draft.docx                         template.docx
     │                                   │
     ├─ plan_reformat_docx ──────────────┤
     │   suggested_style_map             │
     ├─ get_contents_from_docx           ├─ get_styles_from_docx
     │   (loop while has_more)           │   (loop while has_more)
     └──────────────┬────────────────────┘
                    ▼
         write_contents_to_docx(output, style_map=…)   ← batch loop
                    ▼
         write_styles_to_docx(output)     ← batch loop; template styles win
                    ▼
         plan_reformat_docx(draft, output)  ← verify
                    ▼
              formatted output
```

### Step 0 — Plan reformat (before any write)

```
plan_reformat_docx(draft_path="draft.docx", template_path="template.docx", sample_blocks=10)
```

Review `suggested_style_map`, `heuristic_style_map`, and `unmapped_draft_styles`. Edit the map if needed (e.g. keep some `Normal` blocks unmapped). Use `sample_draft_blocks` / `sample_template_blocks` for context.

Key fields in response:

| Field | Use |
|---|---|
| `suggested_style_map` | Pass to `write_contents_to_docx` as `style_map` |
| `heuristic_style_map` | Entries flagged for manual review (e.g. `Normal` → `ТЕКСТ`) |
| `style_catalog_diff.only_in_template` | Styles union adds via write_styles |
| `recommended_actions` | Checklist hints |

Without style mapping, template custom styles (`ТЕKST`, `КОД`) land in the catalog but body blocks keep draft style names — **wrong fonts and sizes**.

### Step 1 — Read draft content

```
get_contents_from_docx(file_path="draft.docx", offset=0, limit=200)
```

Loop while `has_more == true`: increment `offset` by `limit`, append `items`.

### Step 2 — Read template styles

```
get_styles_from_docx(file_path="template.docx", offset=0, limit=200)
```

Loop while `has_more == true`. Merge all `paragraph_styles`. Keep `section` from the **first batch only** (`offset=0`).

### Step 3 — Write content (batched + style_map)

Write in batches that mirror read batches — each MCP call carries at most 200 blocks.

Pass `style_map` from step 0 (server remaps `style.name` on each paragraph block):

```
write_contents_to_docx(
  file_path="output.docx",
  contents=[...batch...],
  offset=0,
  style_map={"Normal": "ТЕКСТ", "List Paragraph": "ТЕКСТ", "macro": "КОД"},
)
```

Alternative (phase 1): patch `style.name` in each block dict before write.

Response includes `styles_remapped` and `style_map_warnings` (unused map keys in batch).

Missing target styles are created as stubs during write; `write_styles` fills full definitions afterward.

Single-batch documents (≤200 blocks): one call with `offset=0` and all items.

### Step 4 — Union styles (batched)

File **must exist** — run step 3 first. Write style batches mirroring step 2.

**First batch** — include `section` from template:

```
write_styles_to_docx(
  file_path="output.docx",
  styles={"paragraph_styles": [...batch...], "section": {...}},
  offset=0,
)
```

**Next batches** — styles only, no `section`:

```
write_styles_to_docx(
  file_path="output.docx",
  styles={"paragraph_styles": [...batch...]},
  offset=<previous offset + batch size>,
)
```

Incoming (template) styles win on name conflict.

### Step 5 — Verify (MCP only)

```
out = get_styles_from_docx(output_path, limit=200)
tpl = get_styles_from_docx(template_path, limit=200)
```

For each name in `["Heading 1", "Heading 2"]`, compare in both responses: `font_name`, `font_size_pt`, `font_color`, `bold`, `alignment`.

## Style union rules

| Case | Result |
|---|---|
| Style only in template | Added |
| Style only in output file | Kept |
| Same name, different definition | **Template wins** |
| Section setup | From template (incoming) |

## Error handling

Failed tool calls return a dict with `code`, `message`, `details` — not a thrown exception.

| Code | Typical cause |
|---|---|
| `FILE_NOT_FOUND` | Source missing, or `write_styles` before `write_contents` |
| `INVALID_PATH` | Bad `offset`/`limit`, wrong append offset, batch > 200, `section` on offset>0 |
| `PARSE_ERROR` | Corrupt or invalid `.docx` |
| `INTERNAL_ERROR` | Unexpected server error |

Always check for `"code"` in the response before treating it as success.

## Pagination helpers (reference only)

The snippets below illustrate batch logic for **tests and documentation**. At runtime the agent MUST call MCP tools directly — do not run these as Python scripts.

```python
# REFERENCE — not for agent runtime; use CallMcpTool instead

def collect_contents(path, limit=200):
    items, offset = [], 0
    while True:
        batch = get_contents_from_docx(path, offset=offset, limit=limit)
        if batch.get("code"):
            return batch  # error
        items.extend(batch["items"])
        if not batch["has_more"]:
            break
        offset += batch["limit"]
    return items

def collect_styles(path, limit=200):
    styles, section, offset = [], None, 0
    while True:
        batch = get_styles_from_docx(path, offset=offset, limit=limit)
        if batch.get("code"):
            return batch  # error
        if offset == 0:
            section = batch.get("section")
        styles.extend(batch["paragraph_styles"])
        if not batch["has_more"]:
            break
        offset += batch["limit"]
    return {"paragraph_styles": styles, "section": section}

def write_contents_batched(output_path, items, limit=200):
    offset = 0
    for start in range(0, len(items), limit):
        batch = items[start : start + limit]
        result = write_contents_to_docx(output_path, batch, offset=offset)
        if result.get("code"):
            return result
        offset = result["total"]

def write_styles_batched(output_path, styles, limit=200):
    paragraph_styles = styles["paragraph_styles"]
    section = styles.get("section")
    offset = 0
    for start in range(0, len(paragraph_styles), limit):
        batch_styles = paragraph_styles[start : start + limit]
        payload = {"paragraph_styles": batch_styles}
        if offset == 0 and section is not None:
            payload["section"] = section
        result = write_styles_to_docx(output_path, payload, offset=offset)
        if result.get("code"):
            return result
        offset = start + len(batch_styles)
```

## Design rules

- Blocks carry **style name references only** — full definitions live in `StyleProfile`
- Do not embed full style payloads inside content blocks
- Do not call `write_styles_to_docx` before `write_contents_to_docx`
- Each batch read re-parses the file (no server-side cache in v1)
- Read and write are both paginated — pass one batch per MCP call, not the full document JSON

## Limitations (v1)

Do not expect support for: headers/footers content, floating images, text boxes, footnotes, numbering restart, or run-level formatting override when a named style is applied.

Style catalog supports `font_color` (RGB hex). For `bold`, `italic`, and `font_color`, a resolved `null` is an explicit reset (clears the draft override), so template styles fully replace draft theme colors and bold headings. Paragraph-level direct formatting (e.g. a centered title set on the paragraph rather than the style) is not carried by content blocks.

## Schema reference

- Content block JSON: [references/blocks](references/blocks)
- Style profile JSON: [references/styles](references/styles)

## Example prompt

> Reformat `report_draft.docx` to match `company_template.docx`. Save as `report_final.docx`.

Expected tool order: read contents → read styles → write contents (batched) → write styles (batched) → verify styles.

Test fixtures in this repo: `tests/assets/plain.docx` (draft), `tests/assets/format.docx` (template).
