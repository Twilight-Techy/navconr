# Local retrieval smoke report

- Authored synthetic fixtures; no independent human review.
- TF-IDF is lexical vector search, not a semantic embedding baseline.
- No answer-quality study was run.
- Local methods use no LLM; these are software smoke results, not a scientific pilot.

| Method | Bytes | Recall | Complete evidence | Abstention | Failures |
| --- | ---: | ---: | ---: | ---: | ---: |
| lexical | 512 | 0.9166666666666666 | 0.8333333333333334 | 1 | 0 |
| lexical | 2048 | 1.0 | 1 | 1 | 0 |
| vector | 512 | 0.9166666666666666 | 0.8333333333333334 | 1 | 0 |
| vector | 2048 | 1.0 | 1 | 1 | 0 |
| hybrid | 512 | 0.9166666666666666 | 0.8333333333333334 | 1 | 0 |
| hybrid | 2048 | 1.0 | 1 | 1 | 0 |
| parent_child | 512 | 0.9166666666666666 | 0.8333333333333334 | 1 | 0 |
| parent_child | 2048 | 0.9833333333333333 | 0.9666666666666667 | 1 | 0 |
| structural | 512 | 0.9666666666666667 | 0.9333333333333333 | 1 | 0 |
| structural | 2048 | 0.9666666666666667 | 0.9333333333333333 | 1 | 0 |
| fixed | 512 | 0.9833333333333333 | 0.9666666666666667 | 1 | 0 |
| fixed | 2048 | 0.9833333333333333 | 0.9666666666666667 | 1 | 0 |
| adaptive | 512 | 0.95 | 0.9 | 1 | 0 |
| adaptive | 2048 | 1.0 | 1 | 1 | 0 |
| no_summaries | 512 | 1.0 | 1 | 1 | 0 |
| no_summaries | 2048 | 1.0 | 1 | 1 | 0 |
| no_references | 512 | 0.9666666666666667 | 0.9333333333333333 | 1 | 0 |
| no_references | 2048 | 0.9666666666666667 | 0.9333333333333333 | 1 | 0 |
