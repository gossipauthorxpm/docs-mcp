---
name: docx-mcp
description: >-
  Read and write .docx files via the docs-mcp MCP server — batch content reads,
  style catalog reads, content write, and style union. Use when the user asks
  to reformat a Word document, apply a template, read/write .docx content or
  styles, or when docs-mcp MCP tools are available.
---

# docs-mcp — Agent Workflow

MCP server with four tools. **No monolithic reformat tool** — the agent orchestrates reads and writes in the correct order with pagination.

## When to use

- Reformat a draft `.docx` using another file's styles (template)
- Read document structure (paragraphs, tables) in batches
- Write or replace document body content
- Apply or merge paragraph styles and page setup onto an existing file

## Prerequisites

- MCP server `docs-mcp` configured in the host (stdio via `uv run docx-mcp` or `docker run --rm -i docs-mcp`)
- File paths come from **tool call parameters** (`file_path`), not from server build or MCP config
- Native: host paths. Docker: paths inside the container; add `-v host:container` to `docker run` only if files live on the host

## Tools

| Tool | Purpose | Default limit |
|---|---|---|
| `get_contents_from_docx` | Batch-read content blocks | 10 |
| `get_styles_from_docx` | Batch-read style catalog | 25 |
| `write_contents_to_docx` | Write blocks; create file if missing | — |
| `write_styles_to_docx` | Union styles onto existing file | — |

Max `limit` per call: **200**.

## Reformat workflow (template apply)

Copy this checklist and track progress:

```
- [ ] Step 1: Paginate get_contents_from_docx on draft
- [ ] Step 2: Paginate get_styles_from_docx on template
- [ ] Step 3: write_contents_to_docx on output path
- [ ] Step 4: write_styles_to_docx on same output path
```

```
draft.docx                         template.docx
     │                                   │
     ├─ get_contents_from_docx           ├─ get_styles_from_docx
     │   (loop while has_more)           │   (loop while has_more)
     └──────────────┬────────────────────┘
                    ▼
         write_contents_to_docx(output.docx)
                    ▼
         write_styles_to_docx(output.docx)   ← template styles win
                    ▼
              formatted output
```

### Step 1 — Read draft content

```
get_contents_from_docx(file_path="draft.docx", offset=0, limit=50)
```

Loop while `has_more == true`: increment `offset` by `limit`, append `items`.

### Step 2 — Read template styles

```
get_styles_from_docx(file_path="template.docx", offset=0, limit=50)
```

Loop while `has_more == true`. Merge all `paragraph_styles`. Keep `section` from the **first batch only** (`offset=0`).

Build styles payload:

```json
{
  "paragraph_styles": [ "...merged from all batches..." ],
  "section": { "...from first batch..." }
}
```

### Step 3 — Write content

```
write_contents_to_docx(file_path="output.docx", contents=[...all items...])
```

Creates the file if missing. Replaces body if file already exists.

### Step 4 — Union styles

```
write_styles_to_docx(file_path="output.docx", styles={...})
```

**File must exist** — run step 3 first. Incoming (template) styles win on name conflict.

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
| `INVALID_PATH` | Bad `offset`/`limit` (offset < 0, limit <= 0, limit > 200) |
| `PARSE_ERROR` | Corrupt or invalid `.docx` |
| `INTERNAL_ERROR` | Unexpected server error |

Always check for `"code"` in the response before treating it as success.

## Pagination helpers

```python
def collect_contents(path, limit=50):
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

def collect_styles(path, limit=50):
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
```

## Design rules

- Blocks carry **style name references only** — full definitions live in `StyleProfile`
- Do not embed full style payloads inside content blocks
- Do not call `write_styles_to_docx` before `write_contents_to_docx`
- Each batch read re-parses the file (no server-side cache in v1)

## Limitations (v1)

Do not expect support for: headers/footers content, floating images, text boxes, footnotes, numbering restart, or run-level formatting override when a named style is applied.

## Schema reference

- Content block JSON: [references/blocks](references/blocks)
- Style profile JSON: [references/styles](references/styles)

## Example prompt

> Reformat `report_draft.docx` to match `company_template.docx`. Save as `report_final.docx`.

Expected tool order: read contents → read styles → write contents → write styles.

Test fixtures in this repo: `tests/assets/plain.docx` (draft), `tests/assets/format.docx` (template).
