# Source and search adapters

| Format | Representation and locators | Limits |
| --- | --- | --- |
| Markdown / text | Original UTF-8 bytes, heading/section/block maps, line displays | Oversized atomic blocks use explicit UTF-8-safe splitting; exact raw pieces are retained |
| PDF | Per-page extracted UTF-8 artifacts linked to original PDF hash | Text-based PDFs only; no OCR, image understanding, guaranteed reading order, or table reconstruction |
| Python | Original bytes; AST class/function outline; resolvable file imports | Syntax errors fall back to text with diagnostics; no type inference or complete call graph |
| TypeScript / TSX | Original bytes; tree-sitter symbols and relative file imports | No compiler-level resolution, package aliases, full dependency analysis, or complete call graph |
| HTML | Extracted text/Markdown preserving headings and links; original hash retained | Scripts/styles removed from extracted text; dynamic rendering and visual layout are not reconstructed |
| DOCX | Ordered paragraph/table extraction with heading styles; original hash retained | No guaranteed layout, footnote, embedded-object or image fidelity |
| Notebook | Original notebook hash plus separate cell-source artifacts | Outputs/attachments intentionally excluded; cell indices and types identify extraction origin |

Install `navconr[formats]` for binary/document/code adapters. Unsupported dependencies raise actionable errors. Image-only PDFs fail explicitly rather than producing empty evidence. Unicode and original newline bytes are preserved for original-text sources. Extracted text is clearly labeled as an artifact and never presented as a byte slice of the original binary.

Structural segmentation prefers parser block boundaries; it preserves a fitting code fence, table or list. A single structure larger than the configured block limit requires smaller exact pieces. Whitespace-only gaps have coverage diagnostics. The parser fingerprint includes adapter and installed dependency versions so changed extraction logic cannot silently reuse old artifacts.

Explicit document links and supported file imports are parsed evidence of references. Missing targets stay unresolved. Similarity/inferred edges are separately labeled and optional. Semantic groups reference existing nodes through membership edges; they do not rearrange source files.

Search options are FTS5 lexical, sparse TF-IDF cosine vectors, reciprocal-rank fusion of those rankings, and an optional sentence-transformer Encoder. TF-IDF and its hybrid are lexical baselines. Learned embeddings are an additional integration, not implied by the word vector. Search ranks source blocks; cards remain bounded and can be paged.
