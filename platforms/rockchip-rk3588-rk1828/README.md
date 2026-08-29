# Rockchip RK3588/RK1828 容器启动指南

本指南从 Ubuntu x86-64 宿主机开始，构建并自检 RKNN3 开发镜像，最后启动可重复进入的交互容器。到工具链自检为止，不包含模型量化、导出、转换或板端部署命令。

## 当前状态与固定版本

当前验证级别为“镜像环境已验证”：RKNN import、CUDA 可见性、Model Zoo、runtime 和 aarch64 g++ 均已通过。具体模型转换链路尚未验证。

| 项目 | 固定值 |
| --- | --- |
| 镜像 | `edge-model-lab/rknn3:1.0.4` |
| 基础系统 | Ubuntu 22.04 |
| `rknn3-toolkit` | `V1.0.4` / `cf292045d77c9ad0377b9fb326f216967475071e` |
| `rknn3-model-zoo` | `V1.0.4` / `f63048265b49bd2c6236790087287bed6c6b76fe` |
| cp310 wheel | `vendor/rknn3-toolkit/rknn3-toolkit/packages/rknn3_toolkit-1.0.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` |
| wheel SHA-256 | `de5ec24e155e77cb37fdfe654a2d1d93fbf68b54679b326e6e4eb0c4c1662415` |

固定 runtime 文件如下：

```text
include/float16.h                              6e230c07bbcfd0ea75c64d44d1b07ed3e549a88d4bb6908b4b9941d4a04fb424
include/rknn3_api.h                            64202b613bb87c6445499cb871e7227f02e9af4720e30750344477ae6e87c16d
Linux/aarch64/librknn3_api.so                  113ec97719e04f82e51fcb8badeb18461070ac55ca9a5da87f887f3110b4fcbe
Linux/aarch64/librknn3_api_rkcp.so             5ea77749f44be1f0c2ad0347242d4b431d3907d03eac11d265496ddd80cfd210
Linux/aarch64/librknn3_api_native.so           8ec78e9d294e6ecf2be6ad9e16004ae5c50bcb9a8567d8bac7310ab27b66dd11
```

官方源码：[rknn3-toolkit](https://github.com/airockchip/rknn3-toolkit/tree/V1.0.4)、[rknn3-model-zoo](https://github.com/airockchip/rknn3-model-zoo/tree/V1.0.4)。前者适用仓库内 RKNN SDK License，后者适用 Apache-2.0；runtime、模型和其他第三方组件分别遵守其随附许可证。

## 宿主机准备

宿主机要求 Ubuntu 22.04 或 Ubuntu 24.04 x86-64、Git、`sha256sum`、Docker Engine、NVIDIA 驱动和 NVIDIA Container Toolkit。Docker 组权限近似 root，只授予可信用户。宿主机不安装 CUDA Toolkit、RKNN、平台 Python 包、CMake 或交叉编译器。

- [Docker Engine Ubuntu 安装](https://docs.docker.com/engine/install/ubuntu/)
- [NVIDIA Container Toolkit 安装](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

按官方文档安装后验证：

```bash
set -e
test "$(uname -m)" = x86_64
docker version
nvidia-smi
docker run --rm --gpus all ubuntu:22.04 nvidia-smi
```

## 准备构建输入

从 EdgeModelLab 仓库根目录执行。两个 tag 仍用完整 commit 二次锁定：

```bash
set -e
export EDGE_MODEL_LAB_ROOT="${EDGE_MODEL_LAB_ROOT:-$PWD}"
test -f "$EDGE_MODEL_LAB_ROOT/README.md"
export ROCKCHIP_ROOT="$EDGE_MODEL_LAB_ROOT/platforms/rockchip-rk3588-rk1828"
mkdir -p "$ROCKCHIP_ROOT/vendor"

git clone --branch V1.0.4 --depth 1 \
  https://github.com/airockchip/rknn3-toolkit.git \
  "$ROCKCHIP_ROOT/vendor/rknn3-toolkit"
git -C "$ROCKCHIP_ROOT/vendor/rknn3-toolkit" \
  switch --detach cf292045d77c9ad0377b9fb326f216967475071e

git clone --branch V1.0.4 --depth 1 \
  https://github.com/airockchip/rknn3-model-zoo.git \
  "$ROCKCHIP_ROOT/vendor/rknn3-model-zoo"
git -C "$ROCKCHIP_ROOT/vendor/rknn3-model-zoo" \
  switch --detach f63048265b49bd2c6236790087287bed6c6b76fe

test "$(git -C "$ROCKCHIP_ROOT/vendor/rknn3-toolkit" rev-parse HEAD)" \
  = cf292045d77c9ad0377b9fb326f216967475071e
test "$(git -C "$ROCKCHIP_ROOT/vendor/rknn3-model-zoo" rev-parse HEAD)" \
  = f63048265b49bd2c6236790087287bed6c6b76fe
```

两个公开仓库不含本次构建所需的完整 runtime。必须从匹配 V1.0.4 的板卡 SDK、厂商交付包或 Rockchip FAE 获取五个文件，按上表路径放入 `$ROCKCHIP_ROOT/runtime/`；不要猜测下载 URL。

一次校验 wheel 和全部 runtime。任一项缺失或哈希不符就停止，不要构建：

```bash
set -e
cd "$ROCKCHIP_ROOT"
sha256sum -c <<'SHA256'
de5ec24e155e77cb37fdfe654a2d1d93fbf68b54679b326e6e4eb0c4c1662415  vendor/rknn3-toolkit/rknn3-toolkit/packages/rknn3_toolkit-1.0.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
6e230c07bbcfd0ea75c64d44d1b07ed3e549a88d4bb6908b4b9941d4a04fb424  runtime/include/float16.h
64202b613bb87c6445499cb871e7227f02e9af4720e30750344477ae6e87c16d  runtime/include/rknn3_api.h
113ec97719e04f82e51fcb8badeb18461070ac55ca9a5da87f887f3110b4fcbe  runtime/Linux/aarch64/librknn3_api.so
5ea77749f44be1f0c2ad0347242d4b431d3907d03eac11d265496ddd80cfd210  runtime/Linux/aarch64/librknn3_api_rkcp.so
8ec78e9d294e6ecf2be6ad9e16004ae5c50bcb9a8567d8bac7310ab27b66dd11  runtime/Linux/aarch64/librknn3_api_native.so
SHA256
```

## 构建与自检

平台目录是唯一构建上下文：

```bash
docker build -t edge-model-lab/rknn3:1.0.4 \
  -f "$ROCKCHIP_ROOT/Dockerfile" "$ROCKCHIP_ROOT"
```

自检只读取镜像内容，不执行模型操作：

```bash
docker run --rm --gpus all --entrypoint /bin/bash \
  edge-model-lab/rknn3:1.0.4 -lc '
set -euo pipefail
python3.10 -c "from rknn.api import RKNN; print(RKNN)"
python3.10 -c "import torch; assert torch.cuda.is_available(); print(torch.version.cuda, torch.cuda.get_device_name(0))"
test "$RKNN3_MODEL_ZOO" = /opt/rknn3-model-zoo
test "$RKNN3_RUNTIME" = /opt/rknn3-runtime
test "$GCC_COMPILER" = aarch64-linux-gnu
test -f "$RKNN3_MODEL_ZOO/examples/Qwen3/python/export_llm.py"
test -f "$RKNN3_RUNTIME/Linux/aarch64/librknn3_api.so"
test -f "$RKNN3_RUNTIME/Linux/aarch64/librknn3_api_rkcp.so"
test -f "$RKNN3_RUNTIME/Linux/aarch64/librknn3_api_native.so"
aarch64-linux-gnu-g++ --version | head -n 1
'
```

退出码为 0 才算镜像环境通过；这不证明模型转换链路通过。

## 启动容器

示例目录名为 `MODEL=Qwen3-4B`、`VARIANT=rknn3-1.0.4-w4a16`。三个挂载分别是只读原始模型、可写平台输出和可写临时目录。

```bash
set -e
export EDGE_MODEL_LAB_ROOT="${EDGE_MODEL_LAB_ROOT:-$PWD}"
MODEL=Qwen3-4B
VARIANT=rknn3-1.0.4-w4a16
MODEL_ROOT="$EDGE_MODEL_LAB_ROOT/models/Qwen/$MODEL"
OUTPUT_ROOT="$MODEL_ROOT/rockchip-rk3588-rk1828/$VARIANT"
TMP_ROOT="$EDGE_MODEL_LAB_ROOT/tmp/rockchip-rk3588-rk1828/$MODEL"
mkdir -p "$MODEL_ROOT/original" "$OUTPUT_ROOT" "$TMP_ROOT/home"

docker run --name edge-model-lab-rknn3 --gpus all -it \
  --user "$(id -u):$(id -g)" \
  --env HOME=/workspace/tmp/home \
  --volume "$MODEL_ROOT/original:/workspace/model:ro" \
  --volume "$OUTPUT_ROOT:/workspace/output:rw" \
  --volume "$TMP_ROOT:/workspace/tmp:rw" \
  --workdir /opt/rknn3-model-zoo \
  edge-model-lab/rknn3:1.0.4 /bin/bash
```

容器不使用 `--rm`。退出后重新进入：

```bash
docker start -ai edge-model-lab-rknn3
```

只有 bind mount 内容独立于容器持久化。对镜像 `/opt` 的修改不回写宿主，并会在删除容器后丢失。

## 离线迁移与清理

联网机器保存镜像并生成哈希：

```bash
set -e
TRANSFER_DIR="${TRANSFER_DIR:-$PWD/rockchip-rknn3-transfer}"
mkdir -p "$TRANSFER_DIR"
docker save -o "$TRANSFER_DIR/edge-model-lab-rknn3-1.0.4.tar" \
  edge-model-lab/rknn3:1.0.4
cd "$TRANSFER_DIR"
sha256sum edge-model-lab-rknn3-1.0.4.tar \
  > edge-model-lab-rknn3-1.0.4.tar.sha256
```

离线机器先校验再加载：

```bash
set -e
TRANSFER_DIR="${TRANSFER_DIR:-$PWD/rockchip-rknn3-transfer}"
cd "$TRANSFER_DIR"
sha256sum -c edge-model-lab-rknn3-1.0.4.tar.sha256
docker load -i edge-model-lab-rknn3-1.0.4.tar
docker image inspect edge-model-lab/rknn3:1.0.4
```

镜像归档已包含安装后的 Toolkit wheel，以及构建时复制入镜像的 Model Zoo 和 runtime。它不包含三个 bind mount、完整 Toolkit Git checkout 及其 `.git` 元数据，也不包含命名容器的可写层。

正常 `docker load` 后启动只需另行准备所需 bind mount 内容，不必再次提供两个源码 checkout 或原始 runtime。只有离线重建镜像或供应链审计时，才按许可证另迁两个固定 checkout 和原始受控 runtime；不要打包认证信息。

只清理本指南指定的容器和 tag：

```bash
docker stop edge-model-lab-rknn3
docker rm edge-model-lab-rknn3
docker image rm edge-model-lab/rknn3:1.0.4
```

这些命令不删除 bind mount。不要使用全局 Docker prune。
