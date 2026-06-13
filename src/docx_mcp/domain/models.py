"""Domain models — stable contract between services and adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from docx_mcp.domain.style_profile import StyleProfile


@dataclass
class RunFormat:
    text: str
    bold: bool | None = None
    italic: bool | None = None
    font_name: str | None = None
    font_size_pt: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "bold": self.bold,
            "italic": self.italic,
            "font_name": self.font_name,
            "font_size_pt": self.font_size_pt,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunFormat:
        return cls(
            text=data["text"],
            bold=data.get("bold"),
            italic=data.get("italic"),
            font_name=data.get("font_name"),
            font_size_pt=data.get("font_size_pt"),
        )


@dataclass
class StyleHint:
    name: str
    style_type: str = "paragraph"

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "style_type": self.style_type}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StyleHint:
        return cls(name=data["name"], style_type=data.get("style_type", "paragraph"))


@dataclass
class ParagraphBlock:
    block_type: Literal["paragraph"] = "paragraph"
    runs: list[RunFormat] = field(default_factory=list)
    style: StyleHint | None = None

    @property
    def text(self) -> str:
        return "".join(run.text for run in self.runs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_type": self.block_type,
            "runs": [r.to_dict() for r in self.runs],
            "style": self.style.to_dict() if self.style else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParagraphBlock:
        return cls(
            runs=[RunFormat.from_dict(r) for r in data.get("runs", [])],
            style=StyleHint.from_dict(data["style"]) if data.get("style") else None,
        )


@dataclass
class TableCellBlock:
    paragraphs: list[ParagraphBlock] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"paragraphs": [p.to_dict() for p in self.paragraphs]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TableCellBlock:
        return cls(
            paragraphs=[ParagraphBlock.from_dict(p) for p in data.get("paragraphs", [])]
        )


@dataclass
class TableBlock:
    block_type: Literal["table"] = "table"
    rows: list[list[TableCellBlock]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_type": self.block_type,
            "rows": [[cell.to_dict() for cell in row] for row in self.rows],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TableBlock:
        return cls(
            rows=[
                [TableCellBlock.from_dict(cell) for cell in row]
                for row in data.get("rows", [])
            ]
        )


DocumentBlock = ParagraphBlock | TableBlock


@dataclass
class DocumentModel:
    blocks: list[DocumentBlock] = field(default_factory=list)
    styles: StyleProfile = field(default_factory=StyleProfile)
    source_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocks": [b.to_dict() for b in self.blocks],
            "styles": self.styles.to_dict(),
            "source_path": self.source_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentModel:
        blocks: list[DocumentBlock] = []
        for block_data in data.get("blocks", []):
            block_type = block_data.get("block_type", "paragraph")
            if block_type == "table":
                blocks.append(TableBlock.from_dict(block_data))
            else:
                blocks.append(ParagraphBlock.from_dict(block_data))
        styles_data = data.get("styles")
        styles = StyleProfile.from_dict(styles_data) if styles_data else StyleProfile()
        return cls(blocks=blocks, styles=styles, source_path=data.get("source_path"))


@dataclass
class ReformatStats:
    paragraphs_written: int = 0
    tables_written: int = 0
    styles_mapped: int = 0
    unmapped_styles: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "paragraphs_written": self.paragraphs_written,
            "tables_written": self.tables_written,
            "styles_mapped": self.styles_mapped,
            "unmapped_styles": list(self.unmapped_styles),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReformatStats:
        return cls(
            paragraphs_written=data.get("paragraphs_written", 0),
            tables_written=data.get("tables_written", 0),
            styles_mapped=data.get("styles_mapped", 0),
            unmapped_styles=list(data.get("unmapped_styles", [])),
        )


@dataclass
class ReformatResult:
    output_path: str
    stats: ReformatStats

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_path": self.output_path,
            "stats": self.stats.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReformatResult:
        return cls(
            output_path=data["output_path"],
            stats=ReformatStats.from_dict(data["stats"]),
        )
