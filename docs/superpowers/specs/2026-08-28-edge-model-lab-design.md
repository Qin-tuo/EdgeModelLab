# EdgeModelLab Design

## Goal

Create one host-side workspace at `/home/barry/EdgeModelLab` for the Qwen model
assets and platform-specific export/quantization recipes. Existing application
projects consume the centralized files but no longer own host-side
model-production tasks or duplicate model data. Generic download and producer
APIs are intentionally outside this repository.

## Scope

The initial migration covers:

- `Qwen2.5-0.5B-Instruct`
- `Qwen3-4B`
- Rockchip RK3588 NPU and RK3588/RK1828 host-side model production

Jetson Orin NX and Horizon S100 directories are reserved for future verified
recipes; no pipeline for those targets is claimed by this migration.

Future source downloads are not restricted to these two models. The user
creates the desired directory and invokes the official Hugging Face or
ModelScope CLI directly.

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
|       |   |-- rockchip-rk3588/
|       |   |-- jetson-orin-nx-16/
|       |   |-- horizon-s100/
|       |   `-- rockchip-rk3588-rk1828/
|       `-- Qwen3-4B/
|           |-- original/
|           |-- rockchip-rk3588/
|           |-- jetson-orin-nx-16/
|           |-- horizon-s100/
|           `-- rockchip-rk3588-rk1828/
|-- common/
|   `-- environment.yml
|-- platforms/
|   |-- jetson-orin-nx-16/
|   |   |-- Dockerfile
|   |   `-- scripts/
|   |-- horizon-s100/
|   |   |-- Dockerfile
|   |   `-- scripts/
|   |-- rockchip-rk3588/
|   |   `-- vendor/
|   `-- rockchip-rk3588-rk1828/
|       |-- Dockerfile
|       |-- .dockerignore
|       |-- config/
|       |-- schema/
|       |-- runtime/
|       `-- vendor/
`-- tmp/
```

No empty version hierarchy is created in advance. A readable variant directory
is added only when real outputs exist, for example
`rockchip-rk3588/rkllm-1.3.0-w8a8/` or
`rockchip-rk3588-rk1828/rknn3-1.0.4-w4a16-ctx4096/`. Directory names do not
contain hashes.

## Ownership Boundaries

`models/Qwen` is the only persistent model-data store. `original` contains an
unaltered upstream snapshot. Each platform variant owns its conversion outputs
and complete deployable bundle; there is no shared model-level ONNX directory.

The pure RK3588 path uses `rknn-toolkit2` for ordinary networks and visual
subgraphs, and `rknn-llm` for LLMs. The RK3588/RK1828 path uses the separate
RKNN3 toolchain. Their model formats and runtimes are not interchangeable.

`common` owns only the Conda environment definition that installs the official
Hugging Face and ModelScope command-line tools. EdgeModelLab does not provide a
custom download wrapper or model allowlist. The actual environment is named
`qwen-common` and remains under `/home/barry/miniconda3/envs/qwen-common`.
ONNX export stays in the matching platform container because the verified
exporters depend on vendor tooling.

`platforms` owns platform-specific Dockerfiles, vendor tooling, conversion,
and quantization recipes. Every platform conversion command runs in its
declared container; no vendor SDK is installed into the common environment.
Deployment consumers own runtime/package activation. Docker continues to manage
image and container data under `/var/lib/docker`; those files are never
manipulated directly.

Each platform image is built with that platform directory as its Docker context.
The platform `.dockerignore` admits only the files needed by the image build;
model trees and unrelated vendor data never enter the build context.

`tmp` contains disposable conversion staging data and intermediate build files.
Manual source downloads write directly to the directory selected by the user;
the platform recipes stage generated output before publishing it.

## Container Access

An interactive platform container receives the selected model directory as a
writable mount and uses the vendor/toolchain files baked into the image. A
temporary host directory may be mounted separately for disposable build data.

The complete model tree is not mounted as a single writable volume for a
production task. Vendor checkouts are build inputs, not runtime mounts. NVIDIA,
Horizon, and Rockchip dependencies remain isolated from each other and from the
common Conda environment.

## Existing Project Changes

`/home/barry/AI_Infra/RK_LLM` stops owning host bootstrap, external-model
import, conversion, quantization, and deployment-package production. The
corresponding host modules, launchers, configurations, and tests are removed;
only the verified platform recipes and input declarations remain in
EdgeModelLab.

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
the existing Qwen data and platform recipes with the smallest structure needed
for current use.
