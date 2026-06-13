"""Domain models for reformat planning — draft vs template analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StyleUsage:
    name: str
    block_count: int

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "block_count": self.block_count}


@dataclass
class StyleFieldMismatch:
    name: str
    fields: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "fields": list(self.fields)}


@dataclass
class StyleCatalogDiff:
    only_in_template: list[str] = field(default_factory=list)
    only_in_draft: list[str] = field(default_factory=list)
    field_mismatches: list[StyleFieldMismatch] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "only_in_template": list(self.only_in_template),
            "only_in_draft": list(self.only_in_draft),
            "field_mismatches": [m.to_dict() for m in self.field_mismatches],
        }


@dataclass
class SampleBlock:
    index: int
    block_type: str
    style_name: str | None
    text_preview: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "block_type": self.block_type,
            "style_name": self.style_name,
            "text_preview": self.text_preview,
        }


@dataclass
class ReformatPlan:
    draft_path: str
    template_path: str
    draft_style_usage: list[StyleUsage] = field(default_factory=list)
    template_style_usage: list[StyleUsage] = field(default_factory=list)
    style_catalog_diff: StyleCatalogDiff = field(default_factory=StyleCatalogDiff)
    suggested_style_map: dict[str, str] = field(default_factory=dict)
    heuristic_style_map: dict[str, bool] = field(default_factory=dict)
    unmapped_draft_styles: list[str] = field(default_factory=list)
    sample_draft_blocks: list[SampleBlock] = field(default_factory=list)
    sample_template_blocks: list[SampleBlock] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "draft_path": self.draft_path,
            "template_path": self.template_path,
            "draft_style_usage": [u.to_dict() for u in self.draft_style_usage],
            "template_style_usage": [u.to_dict() for u in self.template_style_usage],
            "style_catalog_diff": self.style_catalog_diff.to_dict(),
            "suggested_style_map": dict(self.suggested_style_map),
            "heuristic_style_map": dict(self.heuristic_style_map),
            "unmapped_draft_styles": list(self.unmapped_draft_styles),
            "sample_draft_blocks": [b.to_dict() for b in self.sample_draft_blocks],
            "sample_template_blocks": [b.to_dict() for b in self.sample_template_blocks],
            "recommended_actions": list(self.recommended_actions),
        }
