from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_loader_asset_exposes_expected_safe_bridge_api():
    loader = ROOT / "xcreator_integration" / "static" / "xcreator-loader.js"

    text = loader.read_text(encoding="utf-8")

    assert "window.XCreatorAssistantOcrLoader" in text
    assert "discoverUploads" in text
    assert "discoverFields" in text
    assert "fillFields" in text
    assert "renderAssistant" in text
    assert "renderOcrReview" in text
    assert ".click()" not in text
    assert "submit()" not in text


def test_local_clone_fixture_loads_loader_without_remote_or_production_urls():
    fixture = ROOT / "xcreator_integration" / "examples" / "cloned-page-smoke.html"

    text = fixture.read_text(encoding="utf-8")

    assert "xcreator-loader.js" in text
    assert "localhost" not in text
    assert "xcreator.sz-mtrtest.com" not in text
    assert "data-xc-role=\"save\"" in text
