# Qwen Centralization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the existing Qwen2.5-0.5B-Instruct and Qwen3-4B source models and Rockchip artifacts into `/home/barry/EdgeModelLab`, centralize the working Rockchip host-production code there, and reduce RK_LLM to a deployment/runtime consumer.

**Architecture:** EdgeModelLab owns persistent Qwen data, the common download environment, and the currently verified RK1828 host pipeline. RK_LLM retains its deployment-package contract, validation, runtime, inference, and benchmark code, while legacy paths resolve through symlinks. NVIDIA Orin and Horizon S100 output directories are reserved for real artifacts, but no unverified vendor pipeline is fabricated in this migration.

**Tech Stack:** Python 3.12 for repository tooling, Conda environment specification for model download/export, Docker with Ubuntu 22.04/Python 3.10 for RKNN3 Toolkit 1.0.4, pytest, Git worktrees, POSIX symbolic links, existing RK_LLM JSON Schema package contract.

---

## File Structure

EdgeModelLab tracked files:

- `.gitignore`: exclude models, vendor repositories, temporary data, Python caches, and local environments.
- `README.md`: document the small workspace boundary and commands.
- `pyproject.toml`: package `edge-model-lab` and its test dependencies.
- `common/environment.yml`: define the `qwen-common` Conda environment.
- `src/edge_model_lab/common/download.py`: download one of the two approved model snapshots into `original/`.
- `src/edge_model_lab/common/export_onnx.py`: invoke the pinned Qwen2.5 or Qwen3 Model Zoo ONNX exporter with centralized paths.
- `src/edge_model_lab/errors.py`: host-production error types migrated from RK_LLM.
- `src/edge_model_lab/rockchip/manifests.py`: Rockchip upstream/model manifest parsing migrated from RK_LLM.
- `src/edge_model_lab/rockchip/bootstrap.py`: pinned RKNN3 Toolkit/Model Zoo bootstrap migrated from RK_LLM.
- `src/edge_model_lab/rockchip/package.py`: Qwen3 deployment-package producer migrated from RK_LLM and redirected to centralized paths.
- `src/edge_model_lab/rockchip/package_manifest.py`: producer-side package manifest creation and validation.
- `platforms/rockchip-rk1828/Dockerfile`: build the vendor-supported Ubuntu 22.04/Python 3.10 RKNN3 environment.
- `platforms/rockchip-rk1828/config/{upstream,qwen2_5_0_5b,qwen3_4b}.yaml`: retain current immutable input declarations.
- `platforms/rockchip-rk1828/schema/deployment-package.schema.json`: producer copy of the package contract.
- `tests/`: migrated host tests plus focused common-path and download tests.

RK_LLM retained and modified files:

- `Makefile`, `README.md`, `AGENT.md`, and host/export documentation: remove host-production commands and point operators to EdgeModelLab.
- `src/rk_llm/artifacts/manifest.py` and package schema: remain as the consumer-side deployment validator.
- `src/rk_llm/backends`, `platform`, `generation`, `metrics`, runtime configs, native runner, deploy and benchmark docs: remain in RK_LLM.
- `src/rk_llm/host`, `src/rk_llm/manifests`, model-production configs, host tools, and their tests: remove after equivalent EdgeModelLab tests pass.

## Task 1: Scaffold The EdgeModelLab Package

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `pyproject.toml`
- Create: `src/edge_model_lab/__init__.py`
- Create: `src/edge_model_lab/paths.py`
- Create: `tests/test_paths.py`

- [ ] **Step 1: Write the failing layout test**

```python
from pathlib import Path

from edge_model_lab.paths import model_root, workspace_root


def test_workspace_paths_are_derived_from_explicit_root(tmp_path: Path) -> None:
    assert workspace_root(tmp_path) == tmp_path.resolve()
    assert model_root("Qwen3-4B", tmp_path) == (
        tmp_path / "models/Qwen/Qwen3-4B"
    ).resolve()
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python3 -m pytest tests/test_paths.py -q`

Expected: collection fails because `edge_model_lab` does not exist.

- [ ] **Step 3: Add the minimal package and path functions**

```python
from pathlib import Path


def workspace_root(root: Path | None = None) -> Path:
    if root is not None:
        return root.expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def model_root(model_name: str, root: Path | None = None) -> Path:
    return (workspace_root(root) / "models" / "Qwen" / model_name).resolve()
```

Add a minimal setuptools `pyproject.toml`, an empty package initializer, and a
`.gitignore` containing:

```gitignore
.venv/
__pycache__/
.pytest_cache/
*.egg-info/
models/
platforms/*/vendor/
tmp/
```

- [ ] **Step 4: Run the test and verify GREEN**

Run: `python3 -m pytest tests/test_paths.py -q`

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add .gitignore README.md pyproject.toml src tests/test_paths.py
git commit -m "feat: scaffold EdgeModelLab workspace"
```

## Task 2: Add The Common Download Boundary

**Files:**
- Create: `common/environment.yml`
- Create: `src/edge_model_lab/common/__init__.py`
- Create: `src/edge_model_lab/common/download.py`
- Create: `tests/common/test_download.py`

- [ ] **Step 1: Write failing tests for the two approved models and safe destination behavior**

```python
from pathlib import Path

import pytest

from edge_model_lab.common.download import MODELS, download_model


def test_only_approved_qwen_models_are_declared() -> None:
    assert set(MODELS) == {"Qwen2.5-0.5B-Instruct", "Qwen3-4B"}


def test_download_uses_original_directory(tmp_path: Path) -> None:
    calls = []

    def fake_download(**kwargs):
        calls.append(kwargs)
        Path(kwargs["local_dir"]).mkdir(parents=True)
        (Path(kwargs["local_dir"]) / "config.json").write_text("{}")

    result = download_model("Qwen3-4B", tmp_path, fake_download)
    assert result == tmp_path / "models/Qwen/Qwen3-4B/original"
    assert calls[0]["repo_id"] == "Qwen/Qwen3-4B"


def test_download_rejects_nonempty_destination(tmp_path: Path) -> None:
    destination = tmp_path / "models/Qwen/Qwen3-4B/original"
    destination.mkdir(parents=True)
    (destination / "keep").write_text("data")
    with pytest.raises(FileExistsError):
        download_model("Qwen3-4B", tmp_path, lambda **_: None)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m pytest tests/common/test_download.py -q`

Expected: import fails because `download.py` does not exist.

- [ ] **Step 3: Implement the two-model mapping and injected downloader**

Use the existing pinned revisions from the RK model manifests:

```python
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
```

The CLI imports `huggingface_hub.snapshot_download` only when invoked, writes
directly to the selected `original` directory, and refuses a nonempty
destination.

`common/environment.yml` defines Python 3.12, pip, `huggingface_hub==0.36.2`,
`transformers==4.57.6`, `torch==2.7.0`, `onnx==1.18.0`, and `pytest>=8,<9`.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `python3 -m pytest tests/common/test_download.py -q`

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add common src/edge_model_lab/common tests/common
git commit -m "feat: add centralized Qwen download task"
```

## Task 3: Migrate The Verified Rockchip Host Producer

**Files:**
- Create: `src/edge_model_lab/errors.py`
- Create: `src/edge_model_lab/rockchip/{__init__,manifests,bootstrap,package,package_manifest}.py`
- Create: `platforms/rockchip-rk1828/config/*.yaml`
- Create: `platforms/rockchip-rk1828/schema/deployment-package.schema.json`
- Create: `tests/rockchip/`

- [ ] **Step 1: Copy the existing producer tests into EdgeModelLab and update imports only**

Copy RK_LLM tests for bootstrap, manifests, and package production. Replace
imports as follows:

```text
rk_llm.host.bootstrap                  -> edge_model_lab.rockchip.bootstrap
rk_llm.host.package_vendor_demo        -> edge_model_lab.rockchip.package
rk_llm.manifests.loader                -> edge_model_lab.rockchip.manifests
rk_llm.artifacts.manifest              -> edge_model_lab.rockchip.package_manifest
rk_llm.errors                          -> edge_model_lab.errors
```

Do not copy `import_existing` tests; that one-time duplication workflow is being
retired rather than centralized.

- [ ] **Step 2: Run the migrated tests and verify RED**

Run: `python3 -m pytest tests/rockchip -q`

Expected: imports fail because the Rockchip modules do not yet exist.

- [ ] **Step 3: Copy the verified implementation and configuration, then update module imports**

Copy the corresponding RK_LLM modules and these tracked declarations:

```text
manifests/upstream.yaml
configs/models/qwen2_5_0_5b.yaml
configs/models/qwen3_4b.yaml
manifests/schemas/deployment-package.schema.json
```

Keep validation behavior and ABI ceilings unchanged. Change repository-root
lookups to the EdgeModelLab layout. In the mechanically copied
`build_vendor_demo_package` implementation, replace the `project_root`
parameter with explicit `demo_root` and `package_root` parameters, delete the
expressions that derive those paths from `artifacts/work` and
`artifacts/packages`, and retain the existing validation, staging,
publication, and return-value logic unchanged.

The function must publish exactly at `package_root`; it must not create a hash
directory. The manifest may retain its existing internal `package_id`.

- [ ] **Step 4: Run Rockchip tests and verify GREEN**

Run: `python3 -m pytest tests/rockchip -q`

Expected: all migrated bootstrap, manifest, and package tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/edge_model_lab/errors.py src/edge_model_lab/rockchip platforms/rockchip-rk1828 tests/rockchip
git commit -m "feat: centralize Rockchip Qwen host producer"
```

## Task 4: Add Central ONNX Invocation And RKNN3 Docker Environment

**Files:**
- Create: `src/edge_model_lab/common/export_onnx.py`
- Create: `tests/common/test_export_onnx.py`
- Create: `platforms/rockchip-rk1828/Dockerfile`
- Create: `platforms/rockchip-rk1828/scripts/export-qwen`

- [ ] **Step 1: Write a failing command-construction test**

```python
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
    assert "examples/Qwen3/python/export_llm.py" in command[1]
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python3 -m pytest tests/common/test_export_onnx.py -q`

Expected: import fails because `export_onnx.py` does not exist.

- [ ] **Step 3: Implement command construction and the thin CLI**

Map Qwen2.5 to `examples/Qwen2_5/python/export_llm.py` and Qwen3 to
`examples/Qwen3/python/export_llm.py`. The CLI creates only the selected `onnx`
directory and executes the command with `check=True`; all conversion logic
remains in the pinned vendor repository.

Adapt the vendor Ubuntu 22.04/Python 3.10 Dockerfile to install the checked-in
RKNN3 Toolkit 1.0.4 CPython 3.10 wheel from
`platforms/rockchip-rk1828/vendor/rknn3-toolkit`. Do not install the wheel on
the host.

- [ ] **Step 4: Verify unit tests and build/import the container**

Run:

```bash
python3 -m pytest tests/common/test_export_onnx.py -q
docker build -t edge-model-lab/rknn3:1.0.4 -f platforms/rockchip-rk1828/Dockerfile .
docker run --rm edge-model-lab/rknn3:1.0.4 python3 -c 'from rknn.api import RKNN; print(RKNN)'
```

Expected: the test passes, the image builds, and the import prints the RKNN
class without an exception.

- [ ] **Step 5: Commit**

```bash
git add src/edge_model_lab/common/export_onnx.py tests/common/test_export_onnx.py platforms/rockchip-rk1828
git commit -m "feat: add Qwen export environment"
```

## Task 5: Publish Existing Model Data Centrally

**Files:**
- Move data into: `/home/barry/EdgeModelLab/models/Qwen/`
- Create compatibility links under: `/home/barry/rk1828-work/models/`
- Create compatibility links under: `/home/barry/AI_Infra/RK_LLM/artifacts/`

- [ ] **Step 1: Record pre-migration inventories and validate current declarations**

Run the existing model-manifest loaders and package validator against both
source trees, Qwen2.5 generated files, Qwen3 work files, and package
`4938370a62fd618b`. Save command output under
`/home/barry/EdgeModelLab/tmp/migration-evidence/`.

Expected: both model manifests load, all declared file sizes/checksums match,
and package validation returns model `qwen3_4b`.

- [ ] **Step 2: Move original source models and immediately restore old paths as links**

Move these complete directories on the same filesystem:

```text
/home/barry/rk1828-work/models/Qwen2.5-0.5B-Instruct
  -> /home/barry/EdgeModelLab/models/Qwen/Qwen2.5-0.5B-Instruct/original
/home/barry/rk1828-work/models/Qwen3-4B
  -> /home/barry/EdgeModelLab/models/Qwen/Qwen3-4B/original
```

Create absolute compatibility links at the two old paths. Validate every
declared source file through both the central path and old link.

- [ ] **Step 3: Move Qwen2.5 ONNX and RK1828 outputs**

From `rknn3-model-zoo/examples/Qwen2_5/model/llm`, move `.onnx` and
`.config.pkl` into the central `onnx` directory. Move `.rknn`, `.weight`,
`.embed.bin`, and `.tokenizer.gguf` into
`rockchip-rk1828/rknn3-1.0.4-w4a16`. Replace the vendor output path with links
that preserve the filenames expected by existing scripts.

- [ ] **Step 4: Move the validated Qwen3 package as the central RK1828 output**

Move the validated package directory to:

```text
/home/barry/EdgeModelLab/models/Qwen/Qwen3-4B/rockchip-rk1828/rknn3-1.0.4-w4a16/
```

Create the legacy project link
`artifacts/packages/qwen3_4b/4938370a62fd618b` to this readable central
directory. Move Qwen3 `.onnx` and `.config.pkl` from the verified work copy into
the central `onnx` directory.

- [ ] **Step 5: Move vendor repositories into the central platform directory**

Move clean tracked repositories plus their required untracked runtime/build
inputs:

```text
/home/barry/rk1828-work/rknn3-toolkit
  -> /home/barry/EdgeModelLab/platforms/rockchip-rk1828/vendor/rknn3-toolkit
/home/barry/rk1828-work/rknn3-model-zoo
  -> /home/barry/EdgeModelLab/platforms/rockchip-rk1828/vendor/rknn3-model-zoo
```

Restore the old workspace names as compatibility links. Verify both Git
revisions and confirm the vendor export scripts resolve through both paths.

- [ ] **Step 6: Verify central files before deleting duplicates**

Run source-manifest checks, central package validation, `readelf` ABI checks,
symlink resolution checks, and exact inventory comparisons. Expected: all
checks pass and no central path traverses back into RK_LLM artifacts.

## Task 6: Remove Host Production From RK_LLM

**Files:**
- Delete: `src/rk_llm/host/`
- Delete: `src/rk_llm/manifests/`
- Delete: `tools/host/`
- Delete: `tools/export/`
- Delete: `configs/models/`
- Delete: `manifests/upstream.yaml`
- Delete: `requirements/toolkit.txt`
- Delete: host-production unit/integration tests
- Modify: `Makefile`
- Modify: `README.md`
- Modify: `AGENT.md`
- Modify: `docs/host-setup.md`
- Modify: `docs/model-export.md`
- Modify: `docs/architecture.md`
- Modify: `docs/implementation-roadmap.md`
- Modify: `docs/rk1828-rknn3-deployment.md`
- Modify: `docs/rk1828-qwen3-4b-quick-deployment.md`
- Modify: `tests/unit/test_repository_layout.py`

- [ ] **Step 1: Replace repository-layout assertions first and verify RED**

Update `test_repository_layout.py` to assert that `host-bootstrap`,
`host-import`, and `host-package` are absent, that the host module directory is
absent, and that documentation names `/home/barry/EdgeModelLab`. Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .host-venv/bin/python -m pytest \
  tests/unit/test_repository_layout.py -q
```

Expected: failures show the old host targets and files still exist.

- [ ] **Step 2: Remove producer code, targets, configurations, and producer tests**

Delete only the files listed above. Keep `src/rk_llm/artifacts/manifest.py`, the
deployment schema, runtime config, native runner, platform probe, backend,
benchmark, and all consumer tests.

- [ ] **Step 3: Rewrite project documentation around the consumer boundary**

Document that EdgeModelLab produces the package, RK_LLM validates and consumes
it, and `artifacts/deploy/current` remains the board activation path. Remove all
instructions that tell operators to download, import, export, quantize, or
package models inside RK_LLM.

- [ ] **Step 4: Run RK_LLM non-hardware tests and verify GREEN**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .host-venv/bin/python -m pytest -m 'not hardware'
```

Expected: all selected tests pass; the prior baseline was 337 selected tests,
and the new count is lower only by explicitly removed producer tests.

- [ ] **Step 5: Commit RK_LLM changes**

```bash
git add -A
git commit -m "refactor: move Qwen host production to EdgeModelLab"
```

## Task 7: Remove Verified Duplicate Data

**Files:**
- Remove duplicate regular files under `/home/barry/AI_Infra/RK_LLM/artifacts/source_models/`
- Remove duplicate regular files under `/home/barry/AI_Infra/RK_LLM/artifacts/work/`
- Remove incomplete `/home/barry/rk1828-work/models/Qwen3-4B-hf-partial-20260818-194656`
- Remove obsolete `/home/barry/rk1828-work/.venv` only after the RKNN3 Docker import succeeds
- Remove empty `/home/barry/Model`

- [ ] **Step 1: Prove no process has the duplicate files open**

Run `fuser` against the duplicate roots and stop if any process is using them.
Expected: no owning process.

- [ ] **Step 2: Re-run checksum/inventory comparisons**

Expected: every duplicate source/work file that will be removed has an
equivalent central source, ONNX file, or complete central deployment package.

- [ ] **Step 3: Remove duplicates and create only required compatibility links**

Create these project-visible source links after their duplicate directories are
removed:

```text
/home/barry/AI_Infra/RK_LLM/artifacts/source_models/qwen2_5_0_5b
  -> /home/barry/EdgeModelLab/models/Qwen/Qwen2.5-0.5B-Instruct/original
/home/barry/AI_Infra/RK_LLM/artifacts/source_models/qwen3_4b
  -> /home/barry/EdgeModelLab/models/Qwen/Qwen3-4B/original
```

Preserve the legacy Qwen3 package link created in Task 5. Do not retain links
for retired `artifacts/work` producer paths.

- [ ] **Step 4: Measure storage and verify no scattered regular model files remain**

Run `find` for Qwen `.safetensors`, `.onnx`, `.rknn`, `.weight`, and
`.embed.bin` outside EdgeModelLab, excluding Python environments and download
caches. Expected: only approved compatibility symlinks and unrelated test
fixtures remain.

## Task 8: Full Verification And Integration

**Files:**
- Modify: `README.md` in EdgeModelLab if commands differ from verified reality
- Modify: plan checkboxes as tasks complete

- [ ] **Step 1: Run EdgeModelLab tests**

Run: `python3 -m pytest -q`

Expected: all tests pass.

- [ ] **Step 2: Run RK_LLM consumer tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .host-venv/bin/python -m pytest -m 'not hardware'
```

Expected: all selected tests pass.

- [ ] **Step 3: Validate central package and runtime probe**

Run RK_LLM `package-validate` against the central Qwen3 Rockchip directory and
run:

```bash
.host-venv/bin/rk-llm doctor --backend rknn3 \
  --package /home/barry/EdgeModelLab/models/Qwen/Qwen3-4B/rockchip-rk1828/rknn3-1.0.4-w4a16
```

Expected: package validation succeeds; on the x86 host the runtime probe may
report the expected architecture guard but must recognize the complete
package.

- [ ] **Step 4: Verify untouched repositories and Git hygiene**

Confirm S100_VLA is clean, the Orin repository has no new tracked changes,
EdgeModelLab does not track model binaries/vendor repositories, and RK_LLM has
only the intended consumer-boundary commit.

- [ ] **Step 5: Commit final EdgeModelLab documentation and plan status**

```bash
git add README.md docs/superpowers/plans/2026-08-28-qwen-centralization.md
git commit -m "docs: record centralized Qwen workflow"
```

- [ ] **Step 6: Integrate both feature branches locally**

After final verification, merge `feature/qwen-centralization` into
EdgeModelLab `main` and `feature/edge-model-lab-consumer` into RK_LLM `main`.
Do not push either repository without a separate user request.
