import pytest

from navconr import Index


@pytest.fixture
def corpus(tmp_path):
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "auth.md").write_bytes(
        b"# Authentication\r\n\r\n## Refresh tokens\r\nRefresh tokens expire after 30 days.\r\n"
        b"See [revocation](ops.md#revocation).\r\n\r\n## Access tokens\r\nAccess tokens expire after 15 minutes.\r\n"
    )
    (root / "ops.md").write_text(
        "# Operations\n\n## Revocation\nRevoke sessions by deleting their Redis key.\n",
        encoding="utf-8",
    )
    (root / "unicode.md").write_bytes("# Café\r\n日本語 🌍\r\n".encode())
    return root


@pytest.fixture
def index(tmp_path, corpus):
    with Index(tmp_path / "index.sqlite") as instance:
        instance.ingest(corpus)
        yield instance
