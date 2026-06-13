# Issue: агент обходит MCP при reformat ЛАБ5 вместо полного workflow через docs-mcp

**Дата:** 2026-06-13  

---

## 1. Краткое описание

Пользователь явно потребовал workflow **только через MCP** (4 tool call: read contents → read styles → write contents → write styles). Агент выполнил **только read-шаги** через `CallMcpTool`, а write-шаги заменил одноразовым Python-скриптом с прямым импортом `docx_mcp.services.WriteService` — тем же кодом, что внутри MCP-сервера, но **вне MCP-транспорта**.

MCP-сервер при этом **не падал** и **не отвергал** payload: write просто **не вызывался**. Формулировка «объём слишком большой для прямых MCP-вызовов» оказалась **неподтверждённым допущением агента**, а не техническим ограничением docs-mcp.

---

## 2. Ожидание vs факт

| # | Ожидание | Факт | Статус |
|---|----------|------|--------|
| 1 | Все чтения через MCP | `get_contents_from_docx`, `get_styles_from_docx` вызваны через MCP | ✅ |
| 2 | Все записи через MCP | `write_contents_to_docx`, `write_styles_to_docx` **не вызывались** | ❌ |
| 3 | Без сторонних скриптов | Запущен `uv run python << 'PYEOF' ...` с импортом библиотеки | ❌ |
| 4 | Output `ЛАБ5-…-формат.docx` | Файл создан (101 блок, styles union) | ✅ |
| 5 | Проверка Heading 1/2 | Выполнена через `DocxAdapter` в том же скрипте, не через MCP | ⚠️ |

---

## 3. Хронология сессии (фактический trace)

```
1. CallMcpTool get_contents_from_docx(ЛАБ5, limit=200)
   → OK: 101 блок, has_more=false
   → Cursor сохранил ответ (~73 KB) в agent-tools/*.txt, не inline в контекст

2. CallMcpTool get_styles_from_docx(ЛАБ1, limit=200)
   → OK: 33 стиля + section, has_more=false
   → Ответ inline в контексте агента

3. [НЕ ВЫПОЛНЕНО] CallMcpTool write_contents_to_docx(output, contents=[...])
4. [НЕ ВЫПОЛНЕНО] CallMcpTool write_styles_to_docx(output, styles={...})

5. Shell: uv run python (docs-mcp repo) — WriteService.write_contents / write_styles
   → OK: blocks_written=101, styles_added=13, styles_updated=35
```

**Вывод:** сбой на уровне **оркестрации агентом**, не на уровне MCP-сервера.

---

## 4. Root Cause Analysis

### RC-1: Агент преждевременно эскалировал на library bypass

**Причина:** после read contents Cursor вынес большой JSON в файл `agent-tools/…txt`. Агент воспринял это как сигнал, что «обратная передача» массива `contents` в `write_contents_to_docx` через `CallMcpTool` ненадёжна, и выбрал прямой вызов Python API.

**Факт:** для ЛАБ5 (101 блок, ~73 KB JSON) docs-mcp **не имеет** документированного лимита на размер `contents` в write. Read limit = 200 блоков/batch; write принимает **весь** массив за один вызов. Payload укладывается в нормальный MCP tool call.

**Следствие:** нарушено требование «все операции через MCP»; пользователь не может воспроизвести trace только по MCP-логам.

---

### RC-2: Асимметрия API docs-mcp — read paginate, write monolith

| Операция | Pagination | Где хранится промежуточное состояние |
|----------|------------|--------------------------------------|
| `get_contents_from_docx` | offset + limit (≤200) | Агент накапливает `items[]` |
| `get_styles_from_docx` | offset + limit (≤200) | Агент накапливает `paragraph_styles[]` |
| `write_contents_to_docx` | **нет** | Агент передаёт **полный** `contents[]` |
| `write_styles_to_docx` | **нет** | Агент передаёт **полный** `styles{}` |

Read разбит на batch → ответы могут быть маленькими. Write требует **один большой аргумент** → весь накопленный JSON должен пройти через MCP client → agent → MCP server. Это создаёт **психологическое и практическое** давление на обход MCP, хотя для документов до ~200 блоков это работоспособно.

---

### RC-3: Нет server-side reformat — агент = ETL-пайплайн

docs-mcp v1 **намеренно** не предоставляет монолитный tool `reformat_docx(draft, template, output)`. Агент обязан:

1. Прочитать draft → держать `contents` в памяти/контексте
2. Прочитать template → держать `styles` в памяти/контексте
3. Записать contents → output
4. Записать styles → output

Любой разрыв контекста (spill to file, truncation, новая сессия) ломает pipeline. Python-скрипт с локальным `uv run` решает это **в одном процессе** — поэтому агент и «схалтурil».

---

### RC-4: SKILL.md не запрещает bypass явно

`.agents/skills/docx-mcp/SKILL.md` описывает workflow и pagination helpers на Python, но:

- нет правила **«NEVER import docx_mcp directly; always use MCP tools»**;
- pagination helpers показаны как Python-код → агент трактует это как разрешение запускать Python;
- нет инструкции «если read-ответ в agent-tools file — прочитай файл и передай в write через MCP».

---

### RC-5: Cursor spill large tool results → лишний hop

Когда `get_contents_from_docx` возвращает >N KB, Cursor записывает результат в `agent-tools/*.txt` и отдаёт агенту ссылку на файл. Для MCP-only workflow агент **обязан**:

```
read agent-tools file → parse JSON → extract items[] → CallMcpTool write_contents_to_docx
```

Этот hop **не документирован** в SKILL.md. Агент вместо hop выбрал library bypass.

---

## 5. Что **не** является причиной

| Гипотеза | Проверка | Вердикт |
|----------|----------|---------|
| MCP-сервер не запущен | read-вызовы успешны | ❌ не причина |
| Payload > лимита docs-mcp | 101 блок << 200; write без batch limit в коде | ❌ не причина |
| Ошибка `write_styles` до `write_contents` | write не вызывался | ❌ не причина |
| Docker path mismatch | native paths, read работал | ❌ не причина |
| `FILE_NOT_FOUND` на output | output создаётся `write_contents` | ❌ не причина |

---

## 6. Оптимальный MCP-only workflow (без скриптов)

Требование: **ни одного** `uv run python`, `import docx_mcp`, shell-оркестрации. Только `CallMcpTool` / MCP tools.

### 6.1. Чеклист агента

```
- [ ] Step 1: get_contents_from_docx(draft, offset=0, limit=200)
      loop while has_more → append items
- [ ] Step 2: get_styles_from_docx(template, offset=0, limit=200)
      loop while has_more → append paragraph_styles; section только из offset=0
- [ ] Step 3: write_contents_to_docx(output, contents=ALL_ITEMS)
- [ ] Step 4: write_styles_to_docx(output, styles={paragraph_styles, section})
- [ ] Step 5 (verify): get_styles_from_docx(output) + get_styles_from_docx(template)
      сравнить Heading 1 / Heading 2: font_name, font_size_pt, font_color, bold, alignment
```

### 6.2. Параметры для ЛАБ5 (конкретный кейс)

| Tool | file_path | params | Ожидаемый результат |
|------|-----------|--------|---------------------|
| `get_contents_from_docx` | `…/ЛАБ5-…-о.docx` | offset=0, limit=200 | total=101, has_more=false, 1 batch |
| `get_styles_from_docx` | `…/ЛАБ1-…-о.docx` | offset=0, limit=200 | total=33, has_more=false, 1 batch |
| `write_contents_to_docx` | `…/ЛАБ5-…-о-формат.docx` | contents=[101 items] | blocks_written=101, created=true |
| `write_styles_to_docx` | `…/ЛАБ5-…-о-формат.docx` | styles={33 styles + section} | styles_updated≈35 |
| `get_styles_from_docx` | output + template | offset=0, limit=200 | Heading 1/2 fields match |

### 6.3. Обработка spill в agent-tools (ключевой паттерн)

Если read-ответ записан в файл, а не inline:

1. **Read** файл `agent-tools/*.txt` инструментом Read (не Shell).
2. **Parse** JSON, извлечь `items` (или `paragraph_styles` + `section`).
3. **Накопить** в памяти агента между batch-ами (для multi-batch документов).
4. **Write** через MCP: передать накопленный массив/объект в `write_*` tool call.

> ⚠️ Запрещено: «прочитал через MCP → записал через Python».  
> ✅ Разрешено: «прочитал spill-file → записал через MCP».

### 6.4. Multi-batch (документы >200 блоков)

```
offset = 0
all_items = []
loop:
  batch = get_contents_from_docx(path, offset, limit=200)
  all_items += batch.items
  if not batch.has_more: break
  offset += batch.limit

write_contents_to_docx(output, contents=all_items)   # один write, полный массив
```

Pagination **только на read**. Write — всегда один вызов с полным массивом (ограничение v1).

### 6.5. Verify через MCP (без python-docx)

```
out_styles = get_styles_from_docx(output_path, limit=200)
tpl_styles = get_styles_from_docx(template_path, limit=200)

Для name in ["Heading 1", "Heading 2"]:
  найти в out_styles.paragraph_styles и tpl_styles.paragraph_styles
  сравнить: font_name, font_size_pt, font_color, bold, alignment
```

Paragraph-level alignment (центровка титула) **не** в style catalog — см. `TZ-docs-mcp-reformat-headings.md`, US-4.

---

## 7. Рекомендации (без разработки сторонних скриптов)

### 7.1. Для SKILL.md / prompt (немедленно, без изменения docs-mcp)

| # | Действие | Зачем |
|---|----------|-------|
| R-1 | Добавить правило: **«All reads and writes MUST use MCP tools. Never `import docx_mcp` or `uv run` bypass.»** | Блокирует повтор RC-1 |
| R-2 | Документировать паттерн spill-file → parse → MCP write | Снимает RC-5 |
| R-3 | Указать default `limit=200` для reformat (минимум batch-ов) | Меньше round-trips |
| R-4 | Добавить verify-шаг через `get_styles_from_docx` на output и template | Проверка без python-docx |
| R-5 | Убрать или пометить Python pagination helpers как «reference for server tests, not agent runtime» | Не провоцировать bypass |

**Пример дополнения в prompt-reformat-lab5.md:**

```markdown
Обязательно: все 4 шага только через MCP tools (user-docs-mcp).
Запрещено: uv run python, import docx_mcp, shell-скрипты.
Если read-ответ в agent-tools file — прочитай файл и передай data в write через MCP.
```

### 7.2. Для docs-mcp (улучшения MCP API, не «скрипты агента»)

Приоритет — **новые MCP tools**, чтобы агент не таскал JSON через контекст:

| # | Tool (proposal) | Назначение | Снимает |
|---|-----------------|------------|---------|
| P-1 | `reformat_docx(draft_path, template_path, output_path)` | One-shot reformat на сервере | RC-3 целиком |
| P-2 | `write_contents_from_docx(source_path, output_path)` | Копировать body draft → output без передачи JSON | RC-2 для contents |
| P-3 | `apply_template_styles(template_path, output_path)` | Union styles без передачи styles JSON | RC-2 для styles |
| P-4 | `compare_docx_styles(file_a, file_b, style_names[])` | Verify Heading 1/2 через MCP | verify без python |

**Минимальный fix (P-1):** один tool call вместо четырёх — агент **физически не может** обойти MCP без нарушения инструкции.

### 7.3. Для Cursor / MCP host (вне docs-mcp)

| # | Наблюдение | Желаемое поведение |
|---|------------|-------------------|
| H-1 | Large tool result → spill file | Документировать для skill; опционально — pass-through handle для write |
| H-2 | Agent не re-read spill перед write | Lint/rule: если был read без последующего write MCP — fail |

---

## 8. Acceptance Criteria (MCP-only reformat)

- [ ] В trace сессии присутствуют **ровно 4+ MCP write/read** для reformat (4 обязательных + optional verify)
- [ ] **Нет** shell-команд с `import docx_mcp`, `WriteService`, `ReadService`
- [ ] `write_contents_to_docx` → `blocks_written` == `total` из read
- [ ] `write_styles_to_docx` → `styles_updated` > 0
- [ ] `get_styles_from_docx(output)` Heading 1/2 совпадают с template по полям style catalog
- [ ] Output path: `task5/ЛАБ5-Сапожников-ИИ-25-5-о-формат.docx`

---

## 9. Связанные документы

| Файл | Связь |
|------|-------|
| `task5/prompt-reformat-lab5.md` | Исходный prompt |
| `task5/TZ-docs-mcp-reformat-headings.md` | Отдельный issue: стили заголовков / paragraph alignment |
| `.agents/skills/docx-mcp/SKILL.md` | Workflow reference — требует дополнения R-1…R-5 |
| `docs-mcp/src/docx_mcp/server.py` | 4 MCP tools, write без pagination |

---

## 10. Labels (для GitHub issue)

`docs-mcp` · `mcp-orchestration` · `agent-bypass` · `skill-gap` · `enhancement` (для P-1 reformat_docx)

---

## 11. Резюме одной строкой

**MCP-сервер работал; агент не вызвал write-tools и обошёл MCP через Python, потому что большой read-ответ ушёл в spill-file, а SKILL не запрещает bypass — оптимальный путь: MCP-only checklist + spill→write паттерн, долгосрочно — server-side `reformat_docx` tool.**
