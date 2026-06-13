"""Reformat planning — draft vs template analysis for style mapping."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from docx.document import Document as DocxDocument

from docx_mcp.adapters.docx_adapter import DocxAdapter
from docx_mcp.adapters.style_mapper import StyleMapper
from docx_mcp.domain.models import DocumentModel, ParagraphBlock, TableBlock
from docx_mcp.domain.reformat_plan import (
    ReformatPlan,
    SampleBlock,
    StyleCatalogDiff,
    StyleFieldMismatch,
    StyleUsage,
)
from docx_mcp.domain.style_profile import StyleProfile
from docx_mcp.errors import DocxMcpError, internal_error

_MAX_SAMPLE_BLOCKS = 50
_TEXT_PREVIEW_LEN = 80


class ReformatService:
    def __init__(self, adapter: DocxAdapter) -> None:
        self._adapter = adapter

    def plan(
        self,
        draft_path: str,
        template_path: str,
        sample_blocks: int = 10,
        resolve_styles: bool = True,
    ) -> dict:
        if sample_blocks <= 0:
            raise DocxMcpError(
                code="INVALID_PATH",
                message="sample_blocks must be > 0",
                details={"sample_blocks": sample_blocks},
            )
        if sample_blocks > _MAX_SAMPLE_BLOCKS:
            raise DocxMcpError(
                code="INVALID_PATH",
                message=f"sample_blocks must be <= {_MAX_SAMPLE_BLOCKS}",
                details={"sample_blocks": sample_blocks, "max": _MAX_SAMPLE_BLOCKS},
            )
        try:
            draft_doc = self._adapter.read_document(draft_path)
            template_doc = self._adapter.open(template_path)
            draft_profile = self._adapter.inspect_styles(draft_path)
            template_profile = self._adapter.inspect_styles(template_path)

            draft_usage = _usage_from_blocks(draft_doc)
            template_usage = _usage_from_body_paragraphs(template_doc)

            if resolve_styles:
                draft_cmp = draft_profile.resolve_inherited()
                template_cmp = template_profile.resolve_inherited()
            else:
                draft_cmp = draft_profile
                template_cmp = template_profile

            catalog_diff = _catalog_diff(draft_cmp, template_cmp)
            mapper = StyleMapper(template_profile.style_names())
            suggested, unmapped, heuristics = mapper.suggest_map(
                {u.name: u.block_count for u in draft_usage}
            )

            plan = ReformatPlan(
                draft_path=str(Path(draft_path).resolve()),
                template_path=str(Path(template_path).resolve()),
                draft_style_usage=draft_usage,
                template_style_usage=template_usage,
                style_catalog_diff=catalog_diff,
                suggested_style_map=suggested,
                heuristic_style_map=heuristics,
                unmapped_draft_styles=unmapped,
                sample_draft_blocks=_sample_blocks(draft_doc, sample_blocks),
                sample_template_blocks=_sample_blocks_from_document(
                    template_doc, sample_blocks
                ),
                recommended_actions=_recommended_actions(
                    suggested, unmapped, heuristics, catalog_diff
                ),
            )
            return plan.to_dict()
        except DocxMcpError:
            raise
        except Exception as exc:
            raise internal_error(str(exc)) from exc


def _usage_from_blocks(document: DocumentModel) -> list[StyleUsage]:
    counts: Counter[str] = Counter()
    for block in document.blocks:
        if isinstance(block, ParagraphBlock) and block.style:
            counts[block.style.name] += 1
        elif isinstance(block, TableBlock):
            counts["(table)"] += 1
    return [
        StyleUsage(name=name, block_count=count)
        for name, count in counts.most_common()
    ]


def _usage_from_body_paragraphs(document: DocxDocument) -> list[StyleUsage]:
    counts: Counter[str] = Counter()
    for paragraph in document.paragraphs:
        if paragraph.style and paragraph.style.name:
            counts[paragraph.style.name] += 1
    return [
        StyleUsage(name=name, block_count=count)
        for name, count in counts.most_common()
    ]


def _catalog_diff(draft: StyleProfile, template: StyleProfile) -> StyleCatalogDiff:
    draft_names = set(draft.style_names())
    template_names = set(template.style_names())
    mismatches: list[StyleFieldMismatch] = []

    for name in sorted(draft_names & template_names):
        draft_style = draft.get_paragraph_style(name)
        template_style = template.get_paragraph_style(name)
        if draft_style is None or template_style is None:
            continue
        fields = [
            key
            for key, value in template_style.to_dict().items()
            if key != "name" and draft_style.to_dict().get(key) != value
        ]
        if fields:
            mismatches.append(StyleFieldMismatch(name=name, fields=fields))

    return StyleCatalogDiff(
        only_in_template=sorted(template_names - draft_names),
        only_in_draft=sorted(draft_names - template_names),
        field_mismatches=mismatches,
    )


def _sample_blocks(document: DocumentModel, limit: int) -> list[SampleBlock]:
    samples: list[SampleBlock] = []
    for index, block in enumerate(document.blocks[:limit]):
        if isinstance(block, ParagraphBlock):
            style_name = block.style.name if block.style else None
            text = block.text.replace("\n", " ").strip()
            samples.append(
                SampleBlock(
                    index=index,
                    block_type="paragraph",
                    style_name=style_name,
                    text_preview=_truncate(text),
                )
            )
        elif isinstance(block, TableBlock):
            samples.append(
                SampleBlock(
                    index=index,
                    block_type="table",
                    style_name=None,
                    text_preview=f"table {len(block.rows)}x{len(block.rows[0]) if block.rows else 0}",
                )
            )
    return samples


def _sample_blocks_from_document(document: DocxDocument, limit: int) -> list[SampleBlock]:
    samples: list[SampleBlock] = []
    for index, paragraph in enumerate(document.paragraphs[:limit]):
        style_name = paragraph.style.name if paragraph.style else None
        text = paragraph.text.replace("\n", " ").strip()
        if not text and style_name is None:
            continue
        samples.append(
            SampleBlock(
                index=index,
                block_type="paragraph",
                style_name=style_name,
                text_preview=_truncate(text),
            )
        )
        if len(samples) >= limit:
            break
    return samples


def _truncate(text: str) -> str:
    if len(text) <= _TEXT_PREVIEW_LEN:
        return text
    return text[: _TEXT_PREVIEW_LEN - 3] + "..."


def _recommended_actions(
    suggested_map: dict[str, str],
    unmapped: list[str],
    heuristics: dict[str, bool],
    catalog_diff: StyleCatalogDiff,
) -> list[str]:
    actions: list[str] = [
        "Review suggested_style_map and edit before write if needed.",
        "Remap draft block style.name values (or pass style_map to write_contents_to_docx).",
        "Write contents in batches, then write_styles from template catalog.",
    ]
    if heuristics:
        heuristic_names = ", ".join(sorted(heuristics))
        actions.insert(
            1,
            f"Heuristic mappings flagged for review: {heuristic_names}.",
        )
    if unmapped:
        actions.insert(
            1,
            f"Unmapped draft styles (fallback used): {', '.join(unmapped)}.",
        )
    if catalog_diff.only_in_template:
        names = ", ".join(catalog_diff.only_in_template[:8])
        suffix = "..." if len(catalog_diff.only_in_template) > 8 else ""
        actions.append(
            f"Template-only styles to union via write_styles: {names}{suffix}.",
        )
    return actions
