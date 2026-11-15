import io
import json

import pytest

from navconr import Index, NavconrError


def make_pdf(text):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=800)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET".encode())
    page[NameObject("/Contents")] = writer._add_object(stream)
    result = io.BytesIO()
    writer.write(result)
    return result.getvalue()


def test_mixed_formats_have_explicit_extraction_coordinates(tmp_path):
    from docx import Document

    root = tmp_path / "mixed"
    root.mkdir()
    (root / "guide.pdf").write_bytes(make_pdf("PDF evidence value 42"))
    (root / "page.html").write_text(
        "<h1>HTML Guide</h1><p>HTML evidence café</p><script>secret_script()</script>"
    )
    document = Document()
    document.add_heading("Document Guide", level=1)
    document.add_paragraph("DOCX evidence value 73")
    document.save(root / "guide.docx")
    (root / "notes.ipynb").write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "source": ["# Notebook\n", "Notebook evidence 日本語"],
                    }
                ]
            }
        )
    )
    (root / "app.py").write_text(
        'class Service:\n    def handle(self):\n        return "code evidence"\n'
    )
    (root / "app.ts").write_text(
        'export class Handler { process(): string { return "typescript evidence"; } }\n'
    )
    with Index(tmp_path / "mixed.sqlite") as index:
        data = index.ingest(root)
        assert len(data.sources) == 6
        assert len(data.artifacts) == 4
        symbols = {n.title for n in data.nodes.values() if n.kind == "symbol"}
        assert {"Service", "handle", "Handler", "process"} <= symbols
        session = index.session()
        text = ""
        for span in data.spans.values():
            item = session.read([span.id])[0]
            assert item.evidence is not None
            text += item.evidence.text
            extracted = span.source.endswith((".pdf", ".html", ".docx", ".ipynb"))
            assert (span.coordinate == "extracted") == extracted
            assert bool(span.origin) == extracted
        assert "PDF evidence value 42" in text
        assert "DOCX evidence value 73" in text
        assert "secret_script" not in text
        assert "日本語" in text


def test_image_only_pdf_is_explicitly_unsupported(tmp_path):
    from pypdf import PdfWriter

    root = tmp_path / "pdf"
    root.mkdir()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with (root / "blank.pdf").open("wb") as stream:
        writer.write(stream)
    with Index(tmp_path / "index.sqlite") as index:
        with pytest.raises(NavconrError, match="OCR"):
            index.ingest(root)


def test_enrichment_is_validated_and_cached(tmp_path):
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "guide.md").write_text("# Guide\n\nOriginal evidence.\n")

    class Enricher:
        fingerprint = "fixture-1"
        calls = 0

        def summarize(self, text):
            self.calls += 1
            return "Navigation hint only"

    enricher = Enricher()
    with Index(tmp_path / "index.sqlite") as index:
        data = index.ingest(root, enricher=enricher)
        count = enricher.calls
        assert count
        index.ingest(root, enricher=enricher)
        assert enricher.calls == count
        evidence = index.read(index.search("Original").items[0].span_ids)[0].evidence
        assert "Original evidence" in evidence.text
        assert "Navigation hint" not in evidence.text
        assert data.revision == index.store.current()


def test_long_unicode_block_retains_all_bytes(tmp_path):
    root = tmp_path / "unicode"
    root.mkdir()
    raw = ("é日本語🌍" * 100).encode()
    (root / "long.txt").write_bytes(raw)
    with Index(tmp_path / "index.sqlite") as index:
        data = index.ingest(root, block_bytes=64)
        spans = sorted(data.spans.values(), key=lambda s: s.start)
        assert b"".join(index.store.blob(s.blob)[s.start : s.end] for s in spans) == raw
        assert all(s.end - s.start <= 64 for s in spans)


def test_invalid_code_has_explicit_fallback(tmp_path):
    root = tmp_path / "invalid"
    root.mkdir()
    (root / "bad.py").write_text("def invalid(:\n")
    with Index(tmp_path / "index.sqlite") as index:
        data = index.ingest(root)
        assert any("syntax error" in value for value in data.diagnostics)


def test_supported_imports_resolve_to_existing_sources(tmp_path):
    root = tmp_path / "code"
    root.mkdir()
    (root / "main.py").write_text(
        "from helper import process\n\ndef run():\n    return process()\n"
    )
    (root / "helper.py").write_text("def process():\n    return 1\n")
    (root / "main.ts").write_text(
        "import { process } from './helper';\nexport function run() { return process(); }\n"
    )
    (root / "helper.ts").write_text("export function process() { return 1; }\n")
    with Index(tmp_path / "index.sqlite") as index:
        data = index.ingest(root)
        edges = [edge for edge in data.edges if edge.relation == "imports"]
        assert len(edges) == 2
        assert all(edge.target in data.nodes for edge in edges)


def test_fitting_code_fence_is_kept_intact(tmp_path):
    root = tmp_path / "blocks"
    root.mkdir()
    fence = "```python\n" + "print('evidence')\n" * 8 + "```\n"
    (root / "guide.md").write_text("# Guide\n\n" + "Paragraph. " * 12 + "\n\n" + fence)
    with Index(tmp_path / "index.sqlite") as index:
        data = index.ingest(root, block_bytes=256)
        texts = [
            index.store.blob(span.blob)[span.start : span.end].decode()
            for span in data.spans.values()
        ]
        assert any(fence in text for text in texts)


def test_code_scope_does_not_capture_following_module_statements(tmp_path):
    root = tmp_path / "scopes"
    root.mkdir()
    (root / "scope.py").write_text("def inside():\n    return 1\n\nOUTSIDE_MARKER = 2\n")
    with Index(tmp_path / "index.sqlite") as index:
        data = index.ingest(root)
        match = index.search("OUTSIDE_MARKER").items[0]
        parent = data.nodes[data.nodes[match.id].parent]
        assert parent.kind == "document"


def test_pdf_page_locators_distinguish_multiple_pages(tmp_path):
    from pypdf import PdfReader, PdfWriter

    root = tmp_path / "pages"
    root.mkdir()
    writer = PdfWriter()
    writer.append(PdfReader(io.BytesIO(make_pdf("FIRST_PAGE_MARKER"))))
    writer.append(PdfReader(io.BytesIO(make_pdf("SECOND_PAGE_MARKER"))))
    with (root / "pages.pdf").open("wb") as stream:
        writer.write(stream)
    with Index(tmp_path / "index.sqlite") as index:
        index.ingest(root)
        card = index.search("SECOND_PAGE_MARKER").items[0]
        evidence = index.read(card.span_ids)[0].evidence
        assert evidence.span.origin == "page:2"
        assert evidence.span.coordinate == "extracted"
        assert evidence.text.strip() == "SECOND_PAGE_MARKER"
