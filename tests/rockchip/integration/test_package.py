import json
import os
import subprocess
import sys
from pathlib import Path


def test_package_vendor_demo_module_help() -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path("src").resolve())
    result = subprocess.run(
        [sys.executable, "-m", "edge_model_lab.rockchip.package", "--help"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0
    assert "--project-root" in result.stdout
    assert "--model-manifest" in result.stdout
    assert "--upstream-manifest" in result.stdout
    assert "--demo-root" in result.stdout
    assert "--package-root" in result.stdout
    assert "--readelf" in result.stdout
    assert result.stderr == ""


def test_package_vendor_demo_wrapper_invokes_module_help(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment["EDGE_MODEL_LAB_PYTHON"] = sys.executable
    environment["PYTHONPATH"] = str(Path("src").resolve())

    result = subprocess.run(
        [str(Path("platforms/rockchip-rk1828/scripts/package").resolve()), "--help"],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--project-root" in result.stdout
    assert result.stderr == ""


def test_module_cli_prints_one_json_summary(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    import edge_model_lab.rockchip.package as module

    summary = {
        "package_id": "0123456789abcdef",
        "model_id": "qwen3_4b",
        "status": "created",
        "package_path": str(tmp_path / "package"),
    }
    monkeypatch.setattr(module, "load_model_manifest", lambda path: object())
    monkeypatch.setattr(module, "load_upstream_manifest", lambda path: object())
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_build(*args: object, **kwargs: object) -> dict[str, object]:
        calls.append((args, kwargs))
        return summary

    monkeypatch.setattr(module, "build_vendor_demo_package", fake_build)

    result = module.main(
        [
            "--project-root",
            str(tmp_path),
            "--model-manifest",
            str(tmp_path / "model.yaml"),
            "--upstream-manifest",
            str(tmp_path / "upstream.yaml"),
            "--demo-root",
            str(tmp_path / "demo"),
            "--package-root",
            str(tmp_path / "package"),
            "--readelf",
            "readelf",
        ]
    )

    assert result == 0
    output = capsys.readouterr()
    assert output.err == ""
    assert output.out.count("\n") == 1
    assert json.loads(output.out) == summary
    assert calls[0][1]["demo_root"] == tmp_path / "demo"
    assert calls[0][1]["package_root"] == tmp_path / "package"
