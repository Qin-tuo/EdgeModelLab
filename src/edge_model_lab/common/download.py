from __future__ import annotations

import argparse
import shutil
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path

from edge_model_lab.paths import model_root, workspace_root


MODELS = {
    "Qwen2.5-0.5B-Instruct": (
        "Qwen/Qwen2.5-0.5B-Instruct",
        "7ae557604adf67be50417f59c2c2f167def9a775",
    ),
    "Qwen3-4B": (
        "Qwen/Qwen3-4B",
        "1cfa9a7208912126459214e8b04321603b3df60c",
    ),
}


Downloader = Callable[..., object]


def download_model(
    model_name: str,
    root: Path,
    downloader: Downloader,
) -> Path:
    try:
        repo_id, revision = MODELS[model_name]
    except KeyError as error:
        supported = ", ".join(sorted(MODELS))
        raise ValueError(f"unsupported model {model_name!r}; choose {supported}") from error

    destination = model_root(model_name, root) / "original"
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"destination is not empty: {destination}")
    if destination.exists() and not destination.is_dir():
        raise FileExistsError(f"destination is not a directory: {destination}")

    scratch_root = workspace_root(root) / "tmp" / "downloads"
    scratch_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{model_name}.", dir=scratch_root))
    try:
        downloader(
            repo_id=repo_id,
            revision=revision,
            local_dir=str(staging),
        )
        if not any(staging.iterdir()):
            raise RuntimeError(f"download produced no files for {model_name}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            destination.rmdir()
        staging.rename(destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return destination


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="edge-model-download")
    parser.add_argument("model", choices=sorted(MODELS))
    parser.add_argument("--root", type=Path)
    args = parser.parse_args(argv)

    from huggingface_hub import snapshot_download

    result = download_model(
        args.model,
        args.root or workspace_root(),
        snapshot_download,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
