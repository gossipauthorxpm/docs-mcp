"""Structured error codes and helpers for docs-mcp."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

FILE_NOT_FOUND = "FILE_NOT_FOUND"
FILE_NOT_READABLE = "FILE_NOT_READABLE"
FILE_NOT_WRITABLE = "FILE_NOT_WRITABLE"
INVALID_PATH = "INVALID_PATH"
PARSE_ERROR = "PARSE_ERROR"
STYLE_NOT_FOUND = "STYLE_NOT_FOUND"
REFORMAT_ERROR = "REFORMAT_ERROR"
INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class DocxMcpError(Exception):
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


def file_not_found(path: str) -> DocxMcpError:
    return DocxMcpError(
        code=FILE_NOT_FOUND,
        message=f"File not found: {path}",
        details={"path": path},
    )


def file_not_readable(path: str) -> DocxMcpError:
    return DocxMcpError(
        code=FILE_NOT_READABLE,
        message=f"File is not readable: {path}",
        details={"path": path},
    )


def file_not_writable(path: str) -> DocxMcpError:
    return DocxMcpError(
        code=FILE_NOT_WRITABLE,
        message=f"File is not writable: {path}",
        details={"path": path},
    )


def invalid_path(path: str, reason: str) -> DocxMcpError:
    return DocxMcpError(
        code=INVALID_PATH,
        message=f"Invalid path: {path}",
        details={"path": path, "reason": reason},
    )


def parse_error(path: str, reason: str) -> DocxMcpError:
    return DocxMcpError(
        code=PARSE_ERROR,
        message=f"Failed to parse document: {path}",
        details={"path": path, "reason": reason},
    )


def style_not_found(style_name: str) -> DocxMcpError:
    return DocxMcpError(
        code=STYLE_NOT_FOUND,
        message=f"Style not found: {style_name}",
        details={"style_name": style_name},
    )


def reformat_error(message: str, details: dict[str, Any] | None = None) -> DocxMcpError:
    return DocxMcpError(
        code=REFORMAT_ERROR,
        message=message,
        details=details or {},
    )


def internal_error(message: str, details: dict[str, Any] | None = None) -> DocxMcpError:
    return DocxMcpError(
        code=INTERNAL_ERROR,
        message=message,
        details=details or {},
    )
