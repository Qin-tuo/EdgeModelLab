from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from edge_model_lab.common.download import MODELS
from edge_model_lab.paths import model_root, workspace_root


EXPORTERS = {
    "Qwen2.5-0.5B-Instruct": Path("examples/Qwen2_5/python/export_llm.py"),
    "Qwen3-4B": Path("examples/Qwen3/python/export_llm.py"),
}


def export_command(
    model_name: str,
    root: Path,
    model_zoo: Path,
) -> list[str]:
    try:
        exporter = EXPORTERS[model_name]
    except KeyError as error:
        supported = ", ".join(sorted(EXPORTERS))
        raise ValueError(f"unsupported model {model_name!r}; choose {supported}") from error
    base = model_root(model_name, root)
    return [
        sys.executable,
        str(model_zoo / exporter),
        "--model_path",
        str(base / "original"),
        "--export_llm_path",
        str(base / "onnx" / f"{model_name}.onnx"),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="edge-model-export-onnx")
    parser.add_argument("model", choices=sorted(MODELS))
    parser.add_argument("--root", type=Path)
    parser.add_argument("--model-zoo", type=Path)
    args = parser.parse_args(argv)

    root = (args.root or workspace_root()).expanduser().resolve()
    model_zoo = (
        args.model_zoo
        or root / "platforms/rockchip-rk1828/vendor/rknn3-model-zoo"
    ).expanduser().resolve()
    command = export_command(args.model, root, model_zoo)
    exporter = Path(command[1])
    original = model_root(args.model, root) / "original"
    if not original.is_dir():
        raise FileNotFoundError(f"original model is missing: {original}")
    if not exporter.is_file():
        raise FileNotFoundError(f"vendor exporter is missing: {exporter}")
    (model_root(args.model, root) / "onnx").mkdir(parents=True, exist_ok=True)
    subprocess.run(command, cwd=exporter.parent, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

