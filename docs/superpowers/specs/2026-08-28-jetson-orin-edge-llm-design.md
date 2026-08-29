# Jetson Orin NX TensorRT Edge-LLM Integration Design

## Status

This document defines the architecture contract for a future verified
`jetson-orin-nx-16` producer. It does not claim that the Edge-LLM exporter,
Docker image, or engine build has been verified in this repository yet.

## Goal

Integrate NVIDIA TensorRT Edge-LLM as an independent Jetson Orin NX model
production path while preserving EdgeModelLab's central model store and the
existing Rockchip ownership boundaries.

## Existing Architecture

`models/Qwen` is the only persistent host-side model asset store. An upstream
model is downloaded once into `original/`. Platform-specific producers consume
that source and publish their own artifacts under a readable platform and
toolchain variant. Application repositories consume published artifacts; they
do not own source downloads, vendor SDK installation, or model conversion.

The Rockchip producer is already isolated in its own Docker image and vendor
checkout. Its RKNN3 graph and artifacts are not inputs to NVIDIA tooling.
`common/qwen-common` contains only official source-download and general Python
packages; vendor toolchains must not be installed there.

The current tree has reserved Jetson directories and a downloaded
`Qwen3.5-4B/original` snapshot, but no verified Jetson producer implementation.

## Pipeline Boundary

The Jetson path has two distinct phases:

1. **Export phase (host or supported NVIDIA export device).** Load the
   unmodified Hugging Face snapshot, apply the Edge-LLM-supported quantization,
   and export the Edge-LLM ONNX graph. This phase runs in the pinned NVIDIA
   PyTorch/Edge-LLM environment.
2. **Target build phase (the Orin NX that will run the model).** Build the
   TensorRT engines and native Edge-LLM runtime on the target Jetson using its
   JetPack, TensorRT, CUDA, GPU architecture, and plugin versions.

The ONNX output is portable only within the compatibility contract of its
exporter, model family, opset, quantization format, and Edge-LLM release. A
Rockchip RKNN3 ONNX graph is not an Edge-LLM input by default, and an
Edge-LLM ONNX graph is not an RKNN3 input by default. A TensorRT engine is
always target-specific and must not be copied between different GPU or
TensorRT/plugin configurations.

## Data Layout

The intended layout is:

```text
models/Qwen/<model>/
|-- original/                         immutable upstream snapshot
|-- rockchip-rk3588-rk1828/<variant>/ RKNN3 graph and deployable artifacts
`-- jetson-orin-nx-16/<variant>/
    |-- quantized/                    Edge-LLM quantized checkpoint
    |-- onnx/                         Edge-LLM exporter output
    |-- engine/                       Orin NX TensorRT engines
    `-- manifest.json                 provenance and compatibility record
```

Every ONNX file belongs under a platform and toolchain variant. The model's
`original/` directory is the only shared input between Rockchip and Jetson
producers; there is no shared model-level ONNX directory.

The manifest for a promoted Jetson variant records at least the source model
repository and revision, exporter and Edge-LLM commits, NVIDIA container tag,
JetPack/L4T version, CUDA and TensorRT versions, quantization format, ONNX
opset, engine build parameters, target GPU architecture, and checksums for
published files.

## Platform Ownership

`platforms/jetson-orin-nx-16` owns the future Jetson recipe, including:

- the pinned export/build environment declarations;
- the Edge-LLM exporter and quantization commands;
- target-side engine build commands;
- input/output path conventions and provenance validation;
- platform-specific documentation and tests.

The platform directory must not duplicate model weights, copy Docker's image
store, or install NVIDIA packages into `common/qwen-common`. Generated files
must be written through explicit host mounts into the matching model variant.
Scripts must not hard-code the user's home directory when a repository-root or
explicit path can be used.

## Container Contract

Docker images and container layers remain managed by Docker, normally under its
configured data root. EdgeModelLab stores the Dockerfile, version notes, and
run configuration under the platform directory, not a second copy of the
image.

The export container mounts the selected model input read-only and a Jetson
variant workspace writable. It must write ONNX and quantized outputs below
`/workspace` so they appear on the host. The target build phase mounts the
Jetson ONNX input read-only and writes engines to the target variant's
`engine/` directory.

Do not treat a successful `docker pull` as validation of the producer. A
platform is verified only after the exporter, quantizer, ONNX inspection, target
engine build, and a minimal native inference probe all pass on the declared
version matrix.

## Version and Compatibility Rules

The NVIDIA PyTorch container tag, Edge-LLM release, JetPack/L4T release,
TensorRT version, and CUDA version form one compatibility set. Pin all of them
in the platform documentation and manifest. Do not silently substitute a newer
container or install a different `torch` dependency into the NVIDIA image.

The current host is x86_64 while the target platform is Jetson Orin NX
aarch64. An x86 export environment may produce ONNX, but the final TensorRT
engine must be built on the Orin NX. Before implementation, verify the exact
JetPack release on the target and select the matching NVIDIA/Edge-LLM release;
the currently downloaded PyTorch tag must not be assumed to match every
JetPack release.

## Non-Goals

This architecture does not add a global model-management CLI, merge Rockchip
and NVIDIA graphs, build a cross-device engine, or move inference application
code into EdgeModelLab. It also does not mark Jetson output as verified until
the complete two-phase workflow passes on the declared hardware and versions.

## Verification Gate

A future Jetson producer may be promoted from reserved to verified only when:

- the source snapshot and revision are recorded;
- quantized and Edge-LLM ONNX outputs are complete and checksummed;
- the ONNX is accepted by the matching Edge-LLM engine builder;
- the engine is built on the target Orin NX;
- the native runtime loads the engine and passes a smoke inference;
- the manifest records the complete compatibility set; and
- no Rockchip, common environment, or application ownership boundary changes.
