"""Style profile snapshot extracted from a template document."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParagraphStyleInfo:
    name: str
    base_style: str | None = None
    font_name: str | None = None
    font_size_pt: float | None = None
    bold: bool | None = None
    italic: bool | None = None
    alignment: str | None = None
    line_spacing: float | None = None
    space_before_pt: float | None = None
    space_after_pt: float | None = None
    left_indent_cm: float | None = None
    right_indent_cm: float | None = None
    first_line_indent_cm: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "base_style": self.base_style,
            "font_name": self.font_name,
            "font_size_pt": self.font_size_pt,
            "bold": self.bold,
            "italic": self.italic,
            "alignment": self.alignment,
            "line_spacing": self.line_spacing,
            "space_before_pt": self.space_before_pt,
            "space_after_pt": self.space_after_pt,
            "left_indent_cm": self.left_indent_cm,
            "right_indent_cm": self.right_indent_cm,
            "first_line_indent_cm": self.first_line_indent_cm,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParagraphStyleInfo:
        return cls(
            name=data["name"],
            base_style=data.get("base_style"),
            font_name=data.get("font_name"),
            font_size_pt=data.get("font_size_pt"),
            bold=data.get("bold"),
            italic=data.get("italic"),
            alignment=data.get("alignment"),
            line_spacing=data.get("line_spacing"),
            space_before_pt=data.get("space_before_pt"),
            space_after_pt=data.get("space_after_pt"),
            left_indent_cm=data.get("left_indent_cm"),
            right_indent_cm=data.get("right_indent_cm"),
            first_line_indent_cm=data.get("first_line_indent_cm"),
        )


@dataclass
class SectionSetup:
    page_width_cm: float | None = None
    page_height_cm: float | None = None
    left_margin_cm: float | None = None
    right_margin_cm: float | None = None
    top_margin_cm: float | None = None
    bottom_margin_cm: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_width_cm": self.page_width_cm,
            "page_height_cm": self.page_height_cm,
            "left_margin_cm": self.left_margin_cm,
            "right_margin_cm": self.right_margin_cm,
            "top_margin_cm": self.top_margin_cm,
            "bottom_margin_cm": self.bottom_margin_cm,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SectionSetup:
        return cls(
            page_width_cm=data.get("page_width_cm"),
            page_height_cm=data.get("page_height_cm"),
            left_margin_cm=data.get("left_margin_cm"),
            right_margin_cm=data.get("right_margin_cm"),
            top_margin_cm=data.get("top_margin_cm"),
            bottom_margin_cm=data.get("bottom_margin_cm"),
        )


@dataclass
class StyleProfile:
    paragraph_styles: list[ParagraphStyleInfo] = field(default_factory=list)
    section: SectionSetup | None = None
    source_path: str | None = None

    def style_names(self) -> list[str]:
        return [s.name for s in self.paragraph_styles]

    def get_paragraph_style(self, name: str) -> ParagraphStyleInfo | None:
        for style in self.paragraph_styles:
            if style.name == name:
                return style
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "paragraph_styles": [s.to_dict() for s in self.paragraph_styles],
            "section": self.section.to_dict() if self.section else None,
            "source_path": self.source_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StyleProfile:
        return cls(
            paragraph_styles=[
                ParagraphStyleInfo.from_dict(s) for s in data.get("paragraph_styles", [])
            ],
            section=SectionSetup.from_dict(data["section"]) if data.get("section") else None,
            source_path=data.get("source_path"),
        )
