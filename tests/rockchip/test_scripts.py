from pathlib import Path


def test_export_wrapper_runs_rknn3_container_with_scoped_mounts() -> None:
    script = Path("platforms/rockchip-rk3588-rk1828/scripts/export-qwen").read_text(
        encoding="utf-8"
    )

    assert "docker run --rm" in script
    assert "edge-model-lab/rknn3:1.0.4" in script
    assert ':/input:ro' in script
    assert ':/output' in script
    assert ':/vendor:ro' in script
    assert "EDGE_MODEL_LAB_PYTHON" not in script
