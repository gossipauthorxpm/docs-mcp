"""Map source paragraph styles to template style names."""

from __future__ import annotations

import re


class StyleMapper:
    _HEADING_RE = re.compile(r"^Heading\s+(\d+)$", re.IGNORECASE)

    def __init__(
        self,
        template_style_names: list[str],
        custom_map: dict[str, str] | None = None,
    ) -> None:
        self._template_styles = list(template_style_names)
        self._template_set = set(template_style_names)
        self._custom_map = dict(custom_map or {})
        self.unmapped_styles: list[str] = []

    def map_style(self, source_style: str | None) -> str:
        if not source_style:
            return self._fallback()

        if source_style in self._template_set:
            return source_style

        if source_style in self._custom_map:
            mapped = self._custom_map[source_style]
            if mapped in self._template_set:
                return mapped

        heading_match = self._HEADING_RE.match(source_style)
        if heading_match:
            level = int(heading_match.group(1))
            available = self._available_heading_levels()
            if available:
                target_level = min(level, max(available))
                candidate = f"Heading {target_level}"
                if candidate in self._template_set:
                    return candidate

        self._track_unmapped(source_style)
        return self._fallback()

    def _available_heading_levels(self) -> list[int]:
        levels: list[int] = []
        for name in self._template_styles:
            match = self._HEADING_RE.match(name)
            if match:
                levels.append(int(match.group(1)))
        return sorted(levels)

    def _fallback(self) -> str:
        if "Normal" in self._template_set:
            return "Normal"
        if self._template_styles:
            return self._template_styles[0]
        return "Normal"

    def _track_unmapped(self, source_style: str) -> None:
        if source_style not in self.unmapped_styles:
            self.unmapped_styles.append(source_style)
