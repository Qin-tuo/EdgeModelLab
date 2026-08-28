from pathlib import Path

from edge_model_lab.paths import model_root, workspace_root


def test_workspace_paths_are_derived_from_explicit_root(tmp_path: Path) -> None:
    assert workspace_root(tmp_path) == tmp_path.resolve()
    assert model_root("Qwen3-4B", tmp_path) == (
        tmp_path / "models/Qwen/Qwen3-4B"
    ).resolve()
