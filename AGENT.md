# EdgeModelLab Agent Guide

## Repository Role

EdgeModelLab is the host-side model asset workspace. It owns source model
snapshots and platform-specific production recipes. Application repositories
consume published artifacts; they do not own model downloads, vendor SDK
installation, quantization, conversion, or deployment-package production.

The repository is intentionally conservative about verification. A reserved
platform directory is not a verified producer until its complete toolchain and
smoke inference path have passed on the declared hardware.

## Asset Ownership

`models/Qwen` is the only persistent host-side model store:

```text
models/Qwen/<model>/
|-- original/                         immutable upstream snapshot
|-- rockchip-rk3588/<variant>/        RKNN / RKLLM outputs and bundle (NPU only)
|-- rockchip-rk3588-rk1828/<variant>/ RKNN3 outputs and bundle
|-- jetson-orin-nx-16/<variant>/      Edge-LLM outputs and bundle
`-- horizon-s100/<variant>/            future verified outputs
```

`original/` must remain an unmodified upstream snapshot. Record the upstream
repository and revision for every promoted artifact. Do not duplicate model
weights under platform directories, application repositories, or Docker build
contexts.

All ONNX is platform-private. RKNN3 ONNX and TensorRT-Edge-LLM ONNX may contain
toolchain-specific graph changes, quantization assumptions, opsets, or plugin
requirements, so they must live below their platform and variant directory.
There is no shared model-level ONNX directory. TensorRT engines are always tied
to the target GPU, JetPack, TensorRT, plugins, and build parameters.

## Common Environment

`common/qwen-common` is for official Hugging Face/ModelScope download tools and
general model inspection only. Do not install NVIDIA, Rockchip, or other vendor
SDKs into it. Use the official downloader and an explicit `--local-dir` for
source snapshots.

## Platform Boundaries

Each `platforms/<target>` directory owns its Dockerfile, vendor submodules,
conversion/quantization commands, configuration, schemas, and verification
documentation. Platform images use the platform directory as their Docker
build context. Generated model files are written to the matching host model
variant through explicit mounts.

The two Rockchip producers are also independent: `rockchip-rk3588` is the
on-chip RK3588 NPU path and owns the `rknn-toolkit2` and `rknn-llm` submodules;
`rockchip-rk3588-rk1828` is the external RK1828 accelerator path and owns the
`rknn3-toolkit` and `rknn3-model-zoo` submodules. Their model formats and
runtimes must not be mixed. Never use an RKNN3 graph or bundle as an implicit
input to TensorRT-Edge-LLM, and never move NVIDIA runtime dependencies into a
Rockchip image.

## Jetson Orin NX / TensorRT Edge-LLM

`platforms/jetson-orin-nx-16` is the owner of the future Jetson producer. Its
workflow has two phases:

1. **Export phase:** on a supported x86 host or NVIDIA export device, load the
   read-only Hugging Face snapshot, apply a supported quantization such as
   INT4 AWQ, and export the Edge-LLM ONNX graph in the pinned NVIDIA/Edge-LLM
   environment.
2. **Target build phase:** on the Orin NX that will run the model, build the
   TensorRT engines and native Edge-LLM runtime using the target's JetPack,
   CUDA, TensorRT, GPU architecture, and plugin set.

ONNX is the transfer boundary between these phases. An x86 host may export
ONNX, but must not be treated as a valid place to build the final Orin engine.
Engines built on another GPU or with another TensorRT/plugin set are not
promoted as Orin NX artifacts.

The NVIDIA PyTorch NGC image is an export/build base environment, not the
Edge-LLM runtime by itself. Install and pin the TensorRT-Edge-LLM source in the
platform environment when implementing the producer. The image itself remains
in Docker's configured image store; the repository stores only the Dockerfile,
version notes, run configuration, and generated host artifacts.

Use `/workspace` for all container-visible inputs and outputs. Mount the source
snapshot read-only and a platform variant workspace writable. Do not use the
container's `/root` or hard-code `/home/barry` in reusable scripts.

## Compatibility and Provenance

Treat the NVIDIA container tag, TensorRT-Edge-LLM release/commit, JetPack/L4T,
CUDA, TensorRT, quantization format, ONNX opset, target GPU architecture, and
engine build parameters as one compatibility set. Pin the set in platform
documentation and `manifest.json`; do not silently upgrade one component or
replace the NVIDIA image's `torch` dependency.

The downloaded container tag must not be assumed to match every JetPack
release. Check the target's actual JetPack/L4T version before declaring the
platform compatible. For Orin NX, the target GPU architecture is `sm_87`.

A promoted Jetson variant must include provenance and checksums for its source,
quantized checkpoint, ONNX files, engines, and runtime bundle. Use readable
variant names that describe toolchain and precision; do not put hashes in
directory names.

## Verification Gate

Do not call the Jetson producer verified until all of these pass:

- the source model repository and revision are recorded;
- quantized and Edge-LLM ONNX outputs are complete and checksummed;
- the matching Edge-LLM engine builder accepts the ONNX;
- engines build successfully on the target Orin NX;
- the native runtime loads the engine and passes a smoke inference;
- the manifest records the full compatibility set; and
- no common-environment, Rockchip, or application ownership boundary changes.

## Safety and Hygiene

Never commit Hugging Face, NGC, proxy, SSH, or other credentials. Pass tokens
through interactive prompts or environment variables, and keep them out of
shell history, scripts, manifests, logs, and Dockerfiles. Keep model weights,
generated engines, vendor working trees, caches, and temporary build files out
of Git unless a platform explicitly requires a small, reviewable metadata file.
Represent third-party dependencies with submodule pointers under the platform's
`vendor/` directory; record their upstream URLs and commits in `.gitmodules` and
the Git index.
