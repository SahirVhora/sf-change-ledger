from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_public_site_is_the_working_application() -> None:
    page = (ROOT / "index.html").read_text(encoding="utf-8")

    assert 'id="before_files"' in page
    assert 'id="after_files"' in page
    assert 'id="compare_button"' in page
    assert 'data-download="xlsx"' in page
    assert "assets/site.js" in page


def test_public_site_has_discovery_metadata() -> None:
    page = (ROOT / "index.html").read_text(encoding="utf-8")

    assert '<link rel="canonical"' in page
    assert 'property="og:image"' in page
    assert 'type="application/ld+json"' in page
    assert "No installation" in page
