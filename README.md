# EdgeModelLab

EdgeModelLab is the host workspace for the two Qwen models currently used by
the edge projects on this machine:

- Qwen2.5-0.5B-Instruct
- Qwen3-4B

Model files live under `models/Qwen`. Common download and ONNX entry points
live under `common` and `edge_model_lab.common`. Verified vendor-specific host
tasks live under `platforms` and `edge_model_lab.rockchip`. Application
projects consume the resulting deployment bundles and do not produce them.

Large models, generated artifacts, vendor repositories, local environments,
and temporary files are intentionally excluded from Git.

## Layout

```text
models/Qwen/<model>/original          complete downloaded model
models/Qwen/<model>/onnx              ONNX and exporter metadata
models/Qwen/<model>/rockchip-rk1828   RKNN3 outputs and deployment bundle
models/Qwen/<model>/nvidia-orin       future verified Orin outputs
models/Qwen/<model>/horizon-s100      future verified S100 outputs
platforms/rockchip-rk1828             current host-production toolchain
```

No Qwen conversion pipeline has yet been verified for Orin NX or Horizon S100,
so this repository does not provide speculative Dockerfiles or commands for
those platforms.

## Common environment

```sh
conda env create -f common/environment.yml
conda run -n qwen-common python -m pip install -e /home/barry/EdgeModelLab
conda run -n qwen-common edge-model-download Qwen3-4B
```

The common environment downloads and inspects models. Platform conversion does
not install vendor SDKs into this environment.

## Rockchip RK1828

Build and verify the isolated Toolkit 1.0.4 environment:

```sh
docker build -t edge-model-lab/rknn3:1.0.4 \
  -f platforms/rockchip-rk1828/Dockerfile .
docker run --rm edge-model-lab/rknn3:1.0.4 \
  python3.10 -c 'from rknn.api import RKNN; print(RKNN)'
```

Export one of the approved models through the container:

```sh
platforms/rockchip-rk1828/scripts/export-qwen Qwen2.5-0.5B-Instruct
platforms/rockchip-rk1828/scripts/export-qwen Qwen3-4B
```

The source model mount is read-only. ONNX output and the Model Zoo calibration
dataset directory are the only writable task mounts.
