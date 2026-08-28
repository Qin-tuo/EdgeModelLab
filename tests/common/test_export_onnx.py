from pathlib import Path

from edge_model_lab.common.export_onnx import export_command


def test_qwen3_export_uses_central_paths(tmp_path: Path) -> None:
    command = export_command("Qwen3-4B", tmp_path, Path("/vendor/model-zoo"))

    assert command[-4:] == [
        "--model_path",
        str(tmp_path / "models/Qwen/Qwen3-4B/original"),
        "--export_llm_path",
        str(tmp_path / "models/Qwen/Qwen3-4B/onnx/Qwen3-4B.onnx"),
    ]
    assert command[1] == "/vendor/model-zoo/examples/Qwen3/python/export_llm.py"


def test_qwen2_5_export_selects_qwen2_5_vendor_script(tmp_path: Path) -> None:
    command = export_command(
        "Qwen2.5-0.5B-Instruct", tmp_path, Path("/vendor/model-zoo")
    )

    assert command[1] == (
        "/vendor/model-zoo/examples/Qwen2_5/python/export_llm.py"
    )
    assert command[-1].endswith(
        "models/Qwen/Qwen2.5-0.5B-Instruct/onnx/"
        "Qwen2.5-0.5B-Instruct.onnx"
    )
