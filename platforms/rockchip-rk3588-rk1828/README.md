# Rockchip RK3588 + RK1828 容器启动

本目录使用自建镜像 `edge-model-lab/rknn3:1.0.4`。已验证 RKNN import、CUDA、Model Zoo、runtime 和 aarch64 交叉编译器；具体模型量化、导出和板端运行尚未验证。

## 版本与前置条件

| 组件 | 固定版本 |
| --- | --- |
| `rknn3-toolkit` | `V1.0.4` / `cf292045d77c9ad0377b9fb326f216967475071e` |
| `rknn3-model-zoo` | `V1.0.4` / `f63048265b49bd2c6236790087287bed6c6b76fe` |
| cp310 wheel SHA-256 | `de5ec24e155e77cb37fdfe654a2d1d93fbf68b54679b326e6e4eb0c4c1662415` |

宿主机使用 Ubuntu 22.04/24.04 x86-64，只安装 Docker、NVIDIA 驱动和 NVIDIA Container Toolkit，不安装 RKNN、CUDA Toolkit 或交叉编译器。安装方法见 [Docker Engine](https://docs.docker.com/engine/install/ubuntu/) 和 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)。Docker 组权限近似 root，只授予可信用户。

```bash
docker version
nvidia-smi
docker run --rm --gpus all ubuntu:22.04 nvidia-smi
```

## 准备构建输入

官方源码由主仓库 submodule 固定。若手动修改 submodule，构建会包含修改内容，应另行记录 diff。

```bash
export EDGE_MODEL_LAB_ROOT="${EDGE_MODEL_LAB_ROOT:-$PWD}"
test -f "$EDGE_MODEL_LAB_ROOT/README.md"
export ROCKCHIP_ROOT="$EDGE_MODEL_LAB_ROOT/platforms/rockchip-rk3588-rk1828"

git -C "$EDGE_MODEL_LAB_ROOT" submodule update --init --recursive \
  platforms/rockchip-rk3588-rk1828/vendor/rknn3-toolkit \
  platforms/rockchip-rk3588-rk1828/vendor/rknn3-model-zoo
test "$(git -C "$ROCKCHIP_ROOT/vendor/rknn3-toolkit" rev-parse HEAD)" \
  = cf292045d77c9ad0377b9fb326f216967475071e
test "$(git -C "$ROCKCHIP_ROOT/vendor/rknn3-model-zoo" rev-parse HEAD)" \
  = f63048265b49bd2c6236790087287bed6c6b76fe
```

校验 Toolkit wheel：

```bash
cd "$ROCKCHIP_ROOT"
echo 'de5ec24e155e77cb37fdfe654a2d1d93fbf68b54679b326e6e4eb0c4c1662415  vendor/rknn3-toolkit/rknn3-toolkit/packages/rknn3_toolkit-1.0.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl' \
  | sha256sum -c -
```

公开仓库不包含完整 RKNN3 runtime。请从匹配 V1.0.4 的板卡 SDK、厂商交付包或 Rockchip FAE 获取文件，放到 `runtime/`；任一哈希不匹配都应停止。

```bash
cd "$ROCKCHIP_ROOT"
sha256sum -c <<'SHA256'
6e230c07bbcfd0ea75c64d44d1b07ed3e549a88d4bb6908b4b9941d4a04fb424  runtime/include/float16.h
64202b613bb87c6445499cb871e7227f02e9af4720e30750344477ae6e87c16d  runtime/include/rknn3_api.h
113ec97719e04f82e51fcb8badeb18461070ac55ca9a5da87f887f3110b4fcbe  runtime/Linux/aarch64/librknn3_api.so
5ea77749f44be1f0c2ad0347242d4b431d3907d03eac11d265496ddd80cfd210  runtime/Linux/aarch64/librknn3_api_rkcp.so
8ec78e9d294e6ecf2be6ad9e16004ae5c50bcb9a8567d8bac7310ab27b66dd11  runtime/Linux/aarch64/librknn3_api_native.so
SHA256
```

## 构建与启动

平台目录必须作为 Docker build context：

```bash
docker build -t edge-model-lab/rknn3:1.0.4 \
  -f "$ROCKCHIP_ROOT/Dockerfile" "$ROCKCHIP_ROOT"
```

镜像自检不执行模型转换：

```bash
docker run --rm --gpus all edge-model-lab/rknn3:1.0.4 bash -lc '
set -e
python3.10 -c "import torch; from rknn.api import RKNN; print(RKNN.__name__, torch.cuda.is_available())"
test -f /opt/rknn3-model-zoo/examples/Qwen3/python/export_llm.py
test -f /opt/rknn3-runtime/Linux/aarch64/librknn3_api.so
command -v aarch64-linux-gnu-g++
'
```

只挂载只读模型、可写平台输出和临时目录：

```bash
MODEL=Qwen3-4B
VARIANT=rknn3-1.0.4-w4a16
MODEL_ROOT="$EDGE_MODEL_LAB_ROOT/models/Qwen/$MODEL"
OUTPUT_ROOT="$MODEL_ROOT/rockchip-rk3588-rk1828/$VARIANT"
TMP_ROOT="$EDGE_MODEL_LAB_ROOT/tmp/rockchip-rk3588-rk1828/$MODEL"
mkdir -p "$MODEL_ROOT/original" "$OUTPUT_ROOT" "$TMP_ROOT/home"

docker run --name edge-model-lab-rknn3 -it --gpus all \
  --user "$(id -u):$(id -g)" --env HOME=/workspace/tmp/home \
  --mount type=bind,src="$MODEL_ROOT/original",dst=/workspace/model,readonly \
  --mount type=bind,src="$OUTPUT_ROOT",dst=/workspace/output \
  --mount type=bind,src="$TMP_ROOT",dst=/workspace/tmp \
  --workdir /opt/rknn3-model-zoo \
  edge-model-lab/rknn3:1.0.4 bash
```

退出后用 `docker start -ai edge-model-lab-rknn3` 重新进入。只有 bind mount 会持久化；容器内 `/opt` 的修改不会写回宿主机。

## 离线迁移与清理

```bash
docker save -o edge-model-lab-rknn3-1.0.4.tar edge-model-lab/rknn3:1.0.4
sha256sum edge-model-lab-rknn3-1.0.4.tar > edge-model-lab-rknn3-1.0.4.tar.sha256
sha256sum -c edge-model-lab-rknn3-1.0.4.tar.sha256
docker load -i edge-model-lab-rknn3-1.0.4.tar
```

镜像归档已经包含安装后的 Toolkit、Model Zoo 和 runtime，但不包含模型、输出、tmp 或容器可写层。只有离线重建或审计时，才需另迁 submodule 和原始 runtime 输入。

精确清理本指南创建的对象：

```bash
docker stop edge-model-lab-rknn3 2>/dev/null || true
docker rm edge-model-lab-rknn3 2>/dev/null || true
docker image rm edge-model-lab/rknn3:1.0.4
```

不要执行全局 Docker 清理。上游仓库：[rknn3-toolkit](https://github.com/airockchip/rknn3-toolkit)、[rknn3-model-zoo](https://github.com/airockchip/rknn3-model-zoo)；各组件遵循其随附许可证。
