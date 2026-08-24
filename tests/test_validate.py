from __future__ import annotations

from pathlib import Path

import pytest

from tools.validate import REPO_ROOT, Violation, validate_lock_sources


@pytest.mark.parametrize(
    ("url", "host"),
    [
        ("http://pypi.org/simple/example", "pypi.org"),
        (
            "https://airlock-proxy.uplink.goog:999/simple/example",
            "airlock-proxy.uplink.goog",
        ),
        ("https://localhost/example.whl", "localhost"),
        ("https://127.0.0.1/example.whl", "127.0.0.1"),
        ("https://packages.example.com/example.whl", "packages.example.com"),
        ("https://token:secret@pypi.org:444/simple", "pypi.org"),
        ("https://token:secret@pypi.org/simple", "pypi.org"),
        ("https://pypi.org:444/simple", "pypi.org"),
    ],
)
def test_validate_lock_sources_rejects_non_public_source(
    tmp_path: Path, url: str, host: str
) -> None:
    lock_path = tmp_path / "private.lock"
    lock_path.write_text(f'source = {{ url = "{url}" }}\n', encoding="utf-8")

    assert validate_lock_sources(lock_path) == [
        Violation(
            lock_path,
            1,
            f"lock source host {host!r} is not portable: {url}",
        )
    ]


def test_validate_lock_sources_accepts_public_sources(tmp_path: Path) -> None:
    lock_path = tmp_path / "public.lock"
    lock_path.write_text(
        'source = { registry = "https://pypi.org/simple" }\n'
        'explicit = { registry = "https://pypi.org:443/simple" }\n'
        'sdist = { url = "https://files.pythonhosted.org/example.tar.gz" }\n',
        encoding="utf-8",
    )

    assert validate_lock_sources(lock_path) == []


def test_repository_lock_sources_are_portable() -> None:
    assert validate_lock_sources(REPO_ROOT / "uv.lock") == []
