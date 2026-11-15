"""Format adapters preserve original bytes or explicitly identified extraction artifacts."""

from __future__ import annotations

import ast
import io
import json
from dataclasses import dataclass
from pathlib import Path

from markdown_it import MarkdownIt

from .models import NavconrError

SUPPORTED = {
    ".md",
    ".markdown",
    ".txt",
    ".pdf",
    ".py",
    ".ts",
    ".tsx",
    ".html",
    ".htm",
    ".docx",
    ".ipynb",
}
PARSER_VERSION = "navconr-parsers-5"


@dataclass
class Part:
    data: bytes
    origin: str | None = None


@dataclass
class Outline:
    start: int
    end: int
    title: str
    level: int
    scope_end: int | None = None


def extract(path: str, raw: bytes) -> tuple[list[Part], str, list[str]]:
    suffix = Path(path).suffix.lower()
    diagnostics: list[str] = []
    try:
        if suffix == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(raw))
            parts = [
                Part((page.extract_text() or "").encode(), f"page:{i + 1}")
                for i, page in enumerate(reader.pages)
            ]
            if not any(p.data.strip() for p in parts):
                raise NavconrError(f"{path}: no extractable text; OCR is not supported")
            return parts, "application/pdf", diagnostics
        if suffix == ".docx":
            from docx import Document

            document = Document(io.BytesIO(raw))
            # iter_inner_content retains paragraph/table order in the extraction artifact.
            sections = []
            for element in document.iter_inner_content():
                if hasattr(element, "rows"):
                    sections.append(
                        "\n".join("\t".join(c.text for c in row.cells) for row in element.rows)
                    )
                else:
                    style = element.style.name if element.style else ""
                    prefix = (
                        "#" * int(style[-1]) + " "
                        if style.startswith("Heading ") and style[-1].isdigit()
                        else ""
                    )
                    fragments = []
                    for inline in element.iter_inner_content():
                        fragments.append(
                            "[" + inline.text + "](" + inline.url + ")"
                            if hasattr(inline, "url")
                            else inline.text
                        )
                    sections.append(prefix + "".join(fragments))
            return (
                [Part("\n".join(sections).encode(), "document:markdown")],
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                diagnostics,
            )
        if suffix in {".html", ".htm"}:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(raw, "html.parser")
            for tag in soup(["script", "style"]):
                tag.decompose()
            for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
                tag.replace_with("\n" + "#" * int(tag.name[1]) + " " + tag.get_text(" ") + "\n")
            for tag in soup.find_all("a", href=True):
                tag.replace_with("[" + tag.get_text(" ") + "](" + str(tag["href"]) + ")")
            return (
                [Part(soup.get_text("\n").encode(), "document:markdown")],
                "text/html",
                diagnostics,
            )
        if suffix == ".ipynb":
            notebook = json.loads(raw)
            parts = []
            for i, cell in enumerate(notebook.get("cells", [])):
                source = cell.get("source", [])
                text = source if isinstance(source, str) else "".join(source)
                parts.append(Part(text.encode(), f"cell:{i}:{cell.get('cell_type', 'unknown')}"))
            return parts or [Part(b"", "notebook:empty")], "application/x-ipynb+json", diagnostics
        raw.decode("utf-8")
        if suffix not in SUPPORTED:
            raise NavconrError(f"unsupported source type: {suffix}")
        return (
            [Part(raw)],
            "text/markdown" if suffix in {".md", ".markdown"} else "text/plain",
            diagnostics,
        )
    except ImportError as exc:
        raise NavconrError(f"{path}: install navconr[formats] for this adapter") from exc


def line_offsets(raw: bytes) -> list[int]:
    result = [0]
    for line in raw.splitlines(keepends=True):
        result.append(result[-1] + len(line))
    return result


def outline(path: str, part: Part) -> tuple[list[Outline], list[tuple[int, str]], list[str]]:
    raw = part.data
    text = raw.decode("utf-8")
    offsets = line_offsets(raw)
    suffix = Path(path).suffix.lower()
    headings = []
    links: list[tuple[int, str]] = []
    diagnostics: list[str] = []
    is_markdown = suffix in {".md", ".markdown"} or (
        part.origin and part.origin.endswith(":markdown")
    )
    if is_markdown:
        tokens = MarkdownIt("commonmark").enable("table").parse(text)
        for i, token in enumerate(tokens):
            if token.type == "heading_open" and token.map:
                start, end = token.map
                headings.append(
                    Outline(offsets[start], offsets[end], tokens[i + 1].content, int(token.tag[1:]))
                )
            if token.type == "inline" and token.map:
                for child in token.children or []:
                    if child.type == "link_open" and child.attrGet("href"):
                        links.append((offsets[token.map[0]], str(child.attrGet("href"))))
    elif suffix == ".py":
        try:
            tree = ast.parse(text)
            for item in ast.walk(tree):
                if isinstance(item, ast.Import):
                    links.extend(
                        (offsets[item.lineno - 1], "pyimport:" + alias.name) for alias in item.names
                    )
                elif isinstance(item, ast.ImportFrom):
                    links.append(
                        (
                            offsets[item.lineno - 1],
                            "pyimport:" + "." * item.level + (item.module or ""),
                        )
                    )

            def visit(node: ast.AST, level: int = 1) -> None:
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                        line = child.lineno - 1
                        headings.append(
                            Outline(
                                offsets[line],
                                offsets[line + 1],
                                child.name,
                                level,
                                offsets[child.end_lineno - 1] + child.end_col_offset
                                if child.end_lineno and child.end_col_offset is not None
                                else offsets[line + 1],
                            )
                        )
                        visit(child, level + 1)
                    else:
                        visit(child, level)

            visit(tree)
        except SyntaxError as exc:
            diagnostics.append(f"{path}: syntax error at line {exc.lineno}; plain-text fallback")
    elif suffix in {".ts", ".tsx"}:
        try:
            import tree_sitter_typescript
            from tree_sitter import Language, Parser

            language = (
                tree_sitter_typescript.language_tsx()
                if suffix == ".tsx"
                else tree_sitter_typescript.language_typescript()
            )
            syntax_tree = Parser(Language(language)).parse(raw)
            if syntax_tree.root_node.has_error:
                diagnostics.append(f"{path}: syntax errors; partial syntax outline")

            def walk(node, depth=1):
                if node.type == "import_statement":
                    imported = node.child_by_field_name("source")
                    if imported:
                        links.append(
                            (node.start_byte, "tsimport:" + imported.text.decode().strip("\"'"))
                        )
                relevant = node.type in {
                    "function_declaration",
                    "class_declaration",
                    "interface_declaration",
                    "method_definition",
                }
                name = node.child_by_field_name("name") if relevant else None
                if name:
                    start = node.start_byte
                    end = raw.find(b"\n", start)
                    headings.append(
                        Outline(
                            start,
                            min(node.end_byte, len(raw) if end < 0 else end + 1),
                            name.text.decode(),
                            depth,
                            node.end_byte,
                        )
                    )
                for child in node.children:
                    walk(child, depth + int(bool(name)))

            walk(syntax_tree.root_node)
        except ImportError as exc:
            raise NavconrError("TypeScript parsing requires navconr[formats]") from exc
    return sorted(headings, key=lambda h: h.start), links, diagnostics


def structure_breaks(path: str, part: Part) -> list[int]:
    if Path(path).suffix.lower() not in {".md", ".markdown"} and not (
        part.origin and part.origin.endswith(":markdown")
    ):
        return []
    offsets = line_offsets(part.data)
    tokens = MarkdownIt("commonmark").enable("table").parse(part.data.decode())
    return sorted(
        {offsets[line] for token in tokens if token.level == 0 and token.map for line in token.map}
    )


def split_ranges(
    raw: bytes, start: int, end: int, maximum: int, preferred: list[int] | None = None
) -> list[tuple[int, int]]:
    """Prefer blank lines/newlines, then UTF-8-safe byte boundaries; no bytes are lost."""
    ranges = []
    while start < end:
        stop = min(start + maximum, end)
        if stop < end:
            candidates = [position for position in preferred or [] if start < position <= stop]
            if candidates:
                stop = max(candidates)
            else:
                blank = raw.rfind(b"\n\n", start + maximum // 3, stop)
                newline = raw.rfind(b"\n", start + maximum // 3, stop)
                stop = blank + 2 if blank >= 0 else newline + 1 if newline >= 0 else stop
            while stop > start and raw[stop] & 0xC0 == 0x80:
                stop -= 1
        if stop <= start:
            raise NavconrError("block size cannot accommodate a UTF-8 code point")
        ranges.append((start, stop))
        start = stop
    return ranges or [(start, end)]
