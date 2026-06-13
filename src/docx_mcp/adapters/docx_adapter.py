"""python-docx adapter — all document I/O goes through this layer."""

from __future__ import annotations

from pathlib import Path

from docx import Document as DocxDocument

from docx_mcp.adapters.content_extractor import ContentExtractor
from docx_mcp.adapters.style_extractor import StyleExtractor
from docx_mcp.domain.models import DocumentModel
from docx_mcp.domain.style_profile import StyleProfile
from docx_mcp.errors import DocxMcpError, file_not_found, file_not_readable, parse_error


class DocxAdapter:
    def __init__(
        self,
        extractor: ContentExtractor | None = None,
        style_extractor: StyleExtractor | None = None,
    ) -> None:
        self._extractor = extractor or ContentExtractor()
        self._style_extractor = style_extractor or StyleExtractor()

    def open(self, path: str | Path) -> DocxDocument:
        resolved = self._validate_read_path(path)
        try:
            return DocxDocument(str(resolved))
        except Exception as exc:
            raise parse_error(str(resolved), str(exc)) from exc

    def save(self, document: DocxDocument, path: str | Path) -> None:
        resolved = self._validate_write_path(path)
        try:
            document.save(str(resolved))
        except Exception as exc:
            raise parse_error(str(resolved), str(exc)) from exc

    def read_document(self, path: str | Path) -> DocumentModel:
        resolved = self._validate_read_path(path)
        document = self.open(resolved)
        source = str(resolved)
        model = self._extractor.extract(document, source_path=source)
        model.styles = self._style_extractor.extract(document, source_path=source)
        return model

    def inspect_styles(self, path: str | Path) -> StyleProfile:
        resolved = self._validate_read_path(path)
        document = self.open(resolved)
        return self._style_extractor.extract(document, source_path=str(resolved))

    def _validate_read_path(self, path: str | Path) -> Path:
        resolved = Path(path).resolve()
        if not resolved.exists():
            raise file_not_found(str(resolved))
        if not resolved.is_file():
            raise file_not_readable(str(resolved))
        return resolved

    def _validate_write_path(self, path: str | Path) -> Path:
        resolved = Path(path).resolve()
        parent = resolved.parent
        if not parent.exists():
            raise file_not_found(str(parent))
        if resolved.exists() and not resolved.is_file():
            raise DocxMcpError(
                code="FILE_NOT_WRITABLE",
                message=f"Path is not a writable file: {resolved}",
                details={"path": str(resolved)},
            )
        return resolved
