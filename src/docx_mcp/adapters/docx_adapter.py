"""python-docx adapter — all document I/O goes through this layer."""

from __future__ import annotations

from pathlib import Path

from docx import Document as DocxDocument

from docx_mcp.adapters.content_extractor import ContentExtractor
from docx_mcp.adapters.content_writer import ContentWriter
from docx_mcp.adapters.style_extractor import StyleExtractor
from docx_mcp.adapters.style_migrator import StyleMigrator
from docx_mcp.domain.models import DocumentBlock, DocumentModel
from docx_mcp.domain.style_profile import StyleProfile
from docx_mcp.errors import DocxMcpError, file_not_found, file_not_readable, parse_error


class DocxAdapter:
    def __init__(
        self,
        extractor: ContentExtractor | None = None,
        style_extractor: StyleExtractor | None = None,
        content_writer: ContentWriter | None = None,
        style_migrator: StyleMigrator | None = None,
    ) -> None:
        self._extractor = extractor or ContentExtractor()
        self._style_extractor = style_extractor or StyleExtractor()
        self._content_writer = content_writer or ContentWriter()
        self._style_migrator = style_migrator or StyleMigrator()

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

    def create_document(self) -> DocxDocument:
        return DocxDocument()

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

    def write_contents(
        self,
        path: str | Path,
        blocks: list[DocumentBlock],
        *,
        replace: bool = True,
    ) -> int:
        resolved = Path(path).resolve()
        if resolved.exists():
            document = self.open(resolved)
        else:
            self._validate_write_path(resolved)
            document = self.create_document()

        count = self._content_writer.write(document, blocks, replace=replace)
        self.save(document, resolved)
        return count

    def write_styles(self, path: str | Path, styles_profile: StyleProfile) -> tuple[int, int, int]:
        resolved = self._validate_read_path(path)
        document = self.open(resolved)
        existing = self._style_extractor.extract(document)
        merged = existing.union_with(styles_profile, master="other")
        result = self._style_migrator.apply(document, merged)
        self.save(document, resolved)
        return result

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
