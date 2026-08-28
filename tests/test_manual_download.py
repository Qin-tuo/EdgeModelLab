from pathlib import Path


def test_download_is_owned_by_official_cli_tools() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert not Path("src/edge_model_lab/common/download.py").exists()
    assert not Path("tests/common/test_download.py").exists()
    assert "edge-model-download" not in pyproject
    assert "edge-model-download" not in readme
    assert "hf download" in readme
    assert "modelscope download" in readme
