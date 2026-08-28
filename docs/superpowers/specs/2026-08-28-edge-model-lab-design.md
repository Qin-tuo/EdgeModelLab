# EdgeModelLab Design

## Goal

Create one host-side workspace at `/home/barry/EdgeModelLab` for the complete
Qwen model lifecycle: source download, common ONNX export, platform conversion,
quantization, and deployment-package creation. Existing application projects
consume the centralized files but no longer own host-side model-production
tasks or duplicate model data.

## Scope

This migration covers only:

- `Qwen2.5-0.5B-Instruct`
- `Qwen3-4B`
- NVIDIA Jetson Orin NX host-side model production
- Horizon S100 host-side model production
- Rockchip RK1828 host-side model production

It does not migrate RTX 5070 work, S100 ACT/SmolVLA work, unrelated models,
board runtime code, inference application code, or benchmark execution code.

## Directory Structure

```text
/home/barry/EdgeModelLab/
|-- README.md
|-- models/
|   `-- Qwen/
|       |-- Qwen2.5-0.5B-Instruct/
|       |   |-- original/
|       |   |-- onnx/
|       |   |-- nvidia-orin/
|       |   |-- horizon-s100/
|       |   `-- rockchip-rk1828/
|       `-- Qwen3-4B/
|           |-- original/
|           |-- onnx/
|           |-- nvidia-orin/
|           |-- horizon-s100/
|           `-- rockchip-rk1828/
|-- common/
|   |-- environment.yml
|   `-- download.py
|-- platforms/
|   |-- nvidia-orin/
|   |   |-- Dockerfile
|   |   `-- scripts/
|   |-- horizon-s100/
|   |   |-- Dockerfile
|   |   `-- scripts/
|   `-- rockchip-rk1828/
|       |-- Dockerfile
|       |-- scripts/
|       `-- vendor/
`-- tmp/
```

No empty version hierarchy is created in advance. A readable variant directory
is added only when real outputs exist, for example
`rockchip-rk1828/rknn3-1.0.4-w4a16-ctx4096/`. Directory names do not contain
hashes.

## Ownership Boundaries

`models/Qwen` is the only persistent model-data store. `original` contains an
unaltered, complete upstream model. `onnx` contains common intermediate
exports. Each platform directory contains its conversion outputs and complete
deployable bundle.

`common` owns the one Conda environment definition and source download task.
The actual Conda environment is named `qwen-common` and remains under
`/home/barry/miniconda3/envs/qwen-common`. ONNX export stays in the matching
platform container because the verified exporters depend on vendor tooling.

`platforms` owns platform-specific Dockerfiles, vendor tooling, conversion,
quantization, and package assembly. Docker continues to manage image and
container data under `/var/lib/docker`; those files are never manipulated
directly.

`tmp` contains disposable downloads, conversion staging data, and intermediate
build files. A successful task publishes its result into the matching model
directory; failed tasks leave persistent model data unchanged.

## Container Access

Platform containers receive only three mounts:

- the selected `original` or `onnx` input directory as read-only;
- the selected platform output directory as writable;
- `/home/barry/EdgeModelLab/tmp` as writable scratch space.

The complete model tree is never mounted writable. NVIDIA, Horizon, and
Rockchip dependencies remain isolated from each other and from the common Conda
environment.

## Existing Project Changes

`/home/barry/AI_Infra/RK_LLM` stops owning host bootstrap, external-model
import, conversion, quantization, and deployment-package production. The
corresponding host modules, launchers, configurations, tests, and documentation
move to EdgeModelLab or are removed after their replacement is verified.

RK_LLM retains board deployment paths, deployment-package validation, RKNN3
runtime probing, inference, benchmark, and application behavior. These are
consumer responsibilities and must not move.

Existing project-visible model and package paths become symbolic links to the
matching EdgeModelLab directories. Runtime code continues using its established
project-relative paths and does not hard-code `/home/barry/EdgeModelLab`.

`/home/barry/AI_Infra/S100_VLA` remains unchanged because its current ACT and
SmolVLA workflows are outside this Qwen-only migration. The Orin learning
repository also remains unchanged except that future Qwen host-production work
must be added to EdgeModelLab instead of that repository.

The older workspace clone at
`/home/barry/rk1828-work/RK_LLM-rknn3-foundation-agent` is not treated as the
canonical application project. Only data and vendor inputs still required by
the centralized Rockchip task are adopted from `/home/barry/rk1828-work`.

## Data Migration

Migration is performed one model and one artifact class at a time:

1. Inventory the source and destination file lists, sizes, and existing
   project-declared checksums.
2. Select the verified complete copy from `/home/barry/rk1828-work` or
   `/home/barry/AI_Infra/RK_LLM/artifacts`.
3. Move that copy into the matching EdgeModelLab model directory on the same
   filesystem.
4. Validate completeness and existing checksum declarations.
5. Replace the old consumer path with a symbolic link.
6. Run the affected project tests and package/runtime probes.
7. Remove remaining duplicate copies only after all consumers pass.

Existing integrity metadata inside deployment packages remains valid. Hashes
may be used internally for migration and package validation but never appear in
human-facing directory names.

## Failure Handling

No source copy or duplicate is deleted before the centralized copy and all
consumer links are verified. A failed validation stops the migration for that
artifact class. Existing paths remain available until the replacement link has
passed its project checks.

Published platform outputs are not overwritten in place when their toolchain,
quantization, or context configuration changes. A new readable variant
directory is created instead.

## Verification

Completion requires all of the following:

- both Qwen `original` directories contain their complete expected file sets;
- all migrated ONNX and Rockchip artifacts match their existing sizes and
  checksum declarations;
- symbolic links resolve to regular files inside EdgeModelLab;
- RK_LLM non-hardware tests pass after host-production responsibilities are
  removed;
- RK_LLM package validation and runtime probes accept the centralized package;
- no model files remain duplicated under RK_LLM artifact directories or
  `/home/barry/rk1828-work/models`;
- S100_VLA and the Orin learning repository have no unintended changes;
- Git repositories contain no model weights, generated binaries, or caches.

## Non-Goals

The first implementation does not add a registry service, database, web UI,
general model-management framework, content-addressed store, custom cache
manager, or a single CLI that abstracts every vendor command. It centralizes
the existing Qwen data and host tasks with the smallest platform-specific
structure needed for current use.
