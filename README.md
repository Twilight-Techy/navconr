# Navconr

Navigate bounded knowledge maps and retrieve exact, versioned source evidence.

```bash
uv venv .venv
uv pip install --python .venv/bin/python -e '.[dev,formats,search,mcp]'
.venv/bin/navconr ingest examples/corpus --db .navconr/demo.sqlite
.venv/bin/navconr query 'How are refresh tokens revoked?' --db .navconr/demo.sqlite
```

The library runs locally without credentials. Model-directed navigation is optional. The working release is `0.1.0rc1`; external publication, licensing, and research claims remain separate gates. See [project documents](docs/README.md) and [task status](docs/TASKS.md).

```python
from navconr import Index, Limits

with Index('.navconr/demo.sqlite') as index:
    index.ingest('examples/corpus')
    session = index.session(limits=Limits(source_bytes=4096))
    candidates = session.search('refresh token revocation')
    for card in candidates.items[:2]:
        for item in session.read(card.span_ids):
            if item.evidence:
                print(item.evidence.span.source, item.evidence.text)
```

Use a session to share a budget across tools and pin a revision. Convenience methods on `Index` create a new session per call. Byte locators are zero-based/end-exclusive into an immutable original or explicitly identified extraction artifact. Summaries are navigation hints, not evidence.

Prepare the topic-map demo with `.venv/bin/python scripts/prepare_demo.py`, build the inspector with `cd viewer && npm ci && npm run build`, then run `make viewer` from the root. The inspector supports source/topic views, relationship-origin filters, exact source reads and recorded actions.

Optional LangGraph/LangChain integration is available with `navconr[langgraph]`. See [quickstart](docs/QUICKSTART.md), [API guide](docs/API.md), [current status](docs/STATUS.md), and [research limitations](docs/EVALUATION.md). The paper under `paper/` is a preliminary draft backed by authored software fixtures; independent research validation remains open.

Source repository: [Twilight-Techy/navconr](https://github.com/Twilight-Techy/navconr). A distribution license has not been selected; see [distribution status](LICENSE_STATUS.md).
