from stagorix.licenses import ASSETS_FILE, _allowed, assets_markdown, python_findings


def test_assets_register_matches_the_catalogs() -> None:
    assert ASSETS_FILE.read_text(encoding="utf-8") == assets_markdown(), (
        "ASSETS.md is out of date: run `uv run stagorix licenses --write-assets`"
    )


def test_license_expressions() -> None:
    assert _allowed("MIT")
    assert _allowed("(MIT OR GPL-3.0)")  # a choice: the permissive one is taken
    assert _allowed("MIT AND BSD-3-Clause")
    assert _allowed("3-Clause BSD License")
    assert not _allowed("GPL-3.0")
    assert not _allowed("MIT AND GPL-3.0")
    assert not _allowed("")


def test_python_dependencies_are_permissive() -> None:
    bad = [f"{f.package} {f.version}: {f.license!r}" for f in python_findings() if not f.ok]
    assert bad == [], f"review these licenses: {bad}"
