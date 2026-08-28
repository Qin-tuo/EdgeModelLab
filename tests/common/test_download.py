from pathlib import Path

import pytest

from edge_model_lab.common.download import MODELS, download_model


def test_only_approved_qwen_models_are_declared() -> None:
    assert set(MODELS) == {"Qwen2.5-0.5B-Instruct", "Qwen3-4B"}


def test_download_publishes_original_directory(tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    def fake_download(**kwargs: object) -> None:
        calls.append(kwargs)
        local_dir = Path(str(kwargs["local_dir"]))
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / "config.json").write_text("{}", encoding="utf-8")

    result = download_model("Qwen3-4B", tmp_path, fake_download)

    assert result == tmp_path / "models/Qwen/Qwen3-4B/original"
    assert (result / "config.json").read_text(encoding="utf-8") == "{}"
    assert calls[0]["repo_id"] == "Qwen/Qwen3-4B"
    assert calls[0]["revision"] == "1cfa9a7208912126459214e8b04321603b3df60c"


def test_download_rejects_nonempty_destination(tmp_path: Path) -> None:
    destination = tmp_path / "models/Qwen/Qwen3-4B/original"
    destination.mkdir(parents=True)
    (destination / "keep").write_text("data", encoding="utf-8")

    with pytest.raises(FileExistsError, match="destination is not empty"):
        download_model("Qwen3-4B", tmp_path, lambda **_: None)


def test_failed_download_does_not_publish_original(tmp_path: Path) -> None:
    def fail_download(**kwargs: object) -> None:
        local_dir = Path(str(kwargs["local_dir"]))
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / "partial").write_text("partial", encoding="utf-8")
        raise RuntimeError("network failed")

    with pytest.raises(RuntimeError, match="network failed"):
        download_model("Qwen2.5-0.5B-Instruct", tmp_path, fail_download)

    assert not (
        tmp_path / "models/Qwen/Qwen2.5-0.5B-Instruct/original"
    ).exists()
