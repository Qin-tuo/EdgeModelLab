# Rockchip RK3588/RK1828 容器启动指南

本指南从一台 Ubuntu x86-64 宿主机开始，准备并构建固定版本的 RKNN3 开发镜像，完成环境自检，然后启动可重复进入的交互容器。除特别说明外，命令均在宿主机执行。

## 当前状态

当前使用自建镜像 `edge-model-lab/rknn3:1.0.4`，基础系统为 Ubuntu 22.04。

已验证的范围是镜像环境：

- `from rknn.api import RKNN` 可以成功导入；
- 容器中的 PyTorch 可以看到宿主机透传的 NVIDIA GPU 和 CUDA runtime；
- 固定版本的 RKNN3 Model Zoo 和 Qwen3 `export_llm.py` 存在；
- 固定哈希的 RKNN3 runtime 头文件、aarch64 动态库和 `aarch64-linux-gnu-g++` 存在。

具体模型的量化、导出、转换、交叉编译和板端推理链路尚未验证。下面的成功自检只证明工具链环境已经就位，不代表任一模型转换结果可用。

## 适用范围与非目标

本指南适用于：

- Ubuntu 22.04 或 Ubuntu 24.04 的 x86-64 宿主机；
- 在 x86-64 主机上构建 RKNN3 1.0.4 开发环境；
- 面向 RK3588 主机加 RK1828 加速器的后续开发准备；
- 通过 NVIDIA GPU 为后续工具链提供 CUDA 能力。

本指南到“进入容器并通过工具链自检”为止，不提供模型下载、量化、导出、RKNN 转换、部署包构建或板端运行命令，也不增加启动脚本或 Docker Compose。模型名 `Qwen3-4B` 和 variant 名 `rknn3-1.0.4-w4a16` 只用于说明目录与挂载关系。

宿主机只负责 Docker、GPU runtime、目录和构建输入。不要在宿主机 Python 环境安装 RKNN、模型平台包、CUDA Toolkit、CMake 或 aarch64 交叉编译器；这些依赖由镜像隔离管理。

## 固定版本和上游来源

| 项目 | 固定值 |
| --- | --- |
| 本地镜像 | `edge-model-lab/rknn3:1.0.4` |
| 镜像基础系统 | Ubuntu 22.04 |
| `rknn3-toolkit` release | `V1.0.4` |
| `rknn3-toolkit` commit | `cf292045d77c9ad0377b9fb326f216967475071e` |
| `rknn3-model-zoo` release | `V1.0.4` |
| `rknn3-model-zoo` commit | `f63048265b49bd2c6236790087287bed6c6b76fe` |
| Python wheel | `vendor/rknn3-toolkit/rknn3-toolkit/packages/rknn3_toolkit-1.0.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` |
| wheel SHA-256 | `de5ec24e155e77cb37fdfe654a2d1d93fbf68b54679b326e6e4eb0c4c1662415` |
| runtime 版本 | `1.0.4` |

release tag 便于人工识别，完整 commit 才是可复现构建的最终身份。后续步骤会同时检查 tag checkout 的实际 commit 和文件哈希。

两个公开 Git 仓库不提供本次构建所需的完整、匹配哈希的 runtime 输入。不要从不明地址补文件，也不要假定其他 release 的同名文件兼容；必须从匹配 V1.0.4 的板卡 SDK、厂商交付包或 Rockchip FAE 获取受控 runtime。没有全部文件或任一哈希不符时，流程必须在构建前停止。

## 宿主机要求

需要以下条件：

- Ubuntu 22.04 或 Ubuntu 24.04 x86-64；
- 可用的 `sudo` 权限和互联网连接，用于首次安装及构建；
- Git 和系统自带的 `sha256sum`，用于获取并校验构建输入；
- NVIDIA GPU 以及已经能在宿主机运行 `nvidia-smi` 的驱动；
- 足够容纳 Git checkout、runtime、Docker 构建层、模型和输出的磁盘空间。

先确认系统和架构：

```bash
set -e
test "$(uname -m)" = x86_64
. /etc/os-release
if [ "$ID" != ubuntu ]; then
  echo "需要原生 Ubuntu，当前系统 ID 为 $ID" >&2
  exit 1
fi
case "$VERSION_ID" in
  22.04|24.04) ;;
  *) echo "需要 Ubuntu 22.04 或 24.04，当前为 $PRETTY_NAME" >&2; exit 1 ;;
esac
printf 'host=%s architecture=%s\n' "$PRETTY_NAME" "$(uname -m)"
df -h /
```

最小化 Ubuntu 安装可能没有 Git；源码获取前先安装并确认基础工具：

```bash
set -e
sudo apt-get update
sudo apt-get install -y git
git --version
sha256sum --version | head -n 1
```

完整 GPU 路径还要求下面的宿主机检查成功。驱动版本取决于实际 GPU，不在本指南中统一固定：

```bash
nvidia-smi
```

只检查 RKNN Python import 时可以没有 GPU；本指南要求完成 CUDA 可见性自检，因此后续正式自检和交互容器都使用 `--gpus all`。

## Docker 与 GPU runtime

### 安装 Docker Engine

以下命令按照 Docker 官方 Ubuntu apt 仓库方式安装 Engine、CLI、containerd 和 Buildx。若主机已经装过发行版自带的 Docker 或独立 containerd，先按官方“卸载冲突包”说明确认迁移影响，不要直接覆盖现有生产环境。

```bash
set -e
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt-get update
sudo apt-get install -y \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

`docker` 组成员可以控制 Docker daemon，实际能力近似 root。只把可信用户加入该组。执行 `usermod` 后完全退出当前桌面或 SSH 登录并重新登录，再执行：

```bash
docker version
docker run --rm hello-world
```

### 安装 NVIDIA Container Toolkit

先确认宿主机 `nvidia-smi` 正常，再配置 NVIDIA 官方稳定 apt 仓库：

```bash
set -e
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  gnupg2

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor \
      -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L \
  https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

验证 Docker 可以向 Ubuntu 22.04 容器透传 GPU：

```bash
docker run --rm --gpus all ubuntu:22.04 nvidia-smi
```

这一步安装的是 NVIDIA Container Toolkit，不是宿主 CUDA Toolkit。容器通过宿主驱动访问 GPU；RKNN、PyTorch 和其他平台 Python 依赖仍由后面的自建镜像提供。

## 本地目录与挂载契约

最终目录关系如下。`vendor/`、`runtime/`、`models/` 和 `tmp/` 已由仓库忽略，不应提交 Git。

```text
$EDGE_MODEL_LAB_ROOT/
|-- README.md
|-- platforms/rockchip-rk3588-rk1828/
|   |-- Dockerfile
|   |-- vendor/
|   |   |-- rknn3-toolkit/
|   |   `-- rknn3-model-zoo/
|   `-- runtime/
|       |-- include/
|       |   |-- float16.h
|       |   `-- rknn3_api.h
|       `-- Linux/aarch64/
|           |-- librknn3_api.so
|           |-- librknn3_api_rkcp.so
|           `-- librknn3_api_native.so
|-- models/Qwen/Qwen3-4B/
|   |-- original/
|   `-- rockchip-rk3588-rk1828/rknn3-1.0.4-w4a16/
`-- tmp/rockchip-rk3588-rk1828/Qwen3-4B/home/
```

容器只使用三处 bind mount：

| 宿主机路径 | 容器路径 | 权限和用途 |
| --- | --- | --- |
| `models/Qwen/$MODEL/original` | `/workspace/model` | 只读，上游模型唯一副本 |
| `models/Qwen/$MODEL/rockchip-rk3588-rk1828/$VARIANT` | `/workspace/output` | 可写，只放本平台 variant 产物 |
| `tmp/rockchip-rk3588-rk1828/$MODEL` | `/workspace/tmp` | 可写，缓存、临时文件和容器 HOME |

Toolkit wheel、Model Zoo 和 runtime 是镜像构建输入，构建后分别安装或复制到镜像中；启动容器时不再挂载 `vendor/` 或 `runtime/`。容器使用当前宿主用户的 UID/GID，`HOME=/workspace/tmp/home`，工作目录为 `/opt/rknn3-model-zoo`。

## 获取源码或构建输入

### 固定两个官方 checkout

从 EdgeModelLab 仓库根目录开始，或者显式设置 `EDGE_MODEL_LAB_ROOT`：

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
```

检查 remote、工作区状态和实际 commit。两条 `test` 都必须成功，且 `status --porcelain` 必须为空：

```bash
set -e
git -C "$ROCKCHIP_ROOT/vendor/rknn3-toolkit" remote get-url origin
git -C "$ROCKCHIP_ROOT/vendor/rknn3-toolkit" status --short --branch
git -C "$ROCKCHIP_ROOT/vendor/rknn3-toolkit" rev-parse HEAD
test "$(git -C "$ROCKCHIP_ROOT/vendor/rknn3-toolkit" rev-parse HEAD)" \
  = cf292045d77c9ad0377b9fb326f216967475071e
test -z "$(git -C "$ROCKCHIP_ROOT/vendor/rknn3-toolkit" status --porcelain)"

git -C "$ROCKCHIP_ROOT/vendor/rknn3-model-zoo" remote get-url origin
git -C "$ROCKCHIP_ROOT/vendor/rknn3-model-zoo" status --short --branch
git -C "$ROCKCHIP_ROOT/vendor/rknn3-model-zoo" rev-parse HEAD
test "$(git -C "$ROCKCHIP_ROOT/vendor/rknn3-model-zoo" rev-parse HEAD)" \
  = f63048265b49bd2c6236790087287bed6c6b76fe
test -z "$(git -C "$ROCKCHIP_ROOT/vendor/rknn3-model-zoo" status --porcelain)"
```

已有 checkout 时不要覆盖或混合文件；先用上面的命令核对状态，确认是否需要在另一个空目录重新获取。

### 校验 cp310 wheel

V1.0.4 的 x86-64 Python 3.10 wheel 应位于 Toolkit checkout 的固定路径。精确校验：

```bash
set -e
(
  cd "$ROCKCHIP_ROOT"
  sha256sum -c <<'SHA256'
de5ec24e155e77cb37fdfe654a2d1d93fbf68b54679b326e6e4eb0c4c1662415  vendor/rknn3-toolkit/rknn3-toolkit/packages/rknn3_toolkit-1.0.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
SHA256
)
```

### 放置并校验受控 runtime

从匹配 V1.0.4 的板卡 SDK、厂商交付包或 Rockchip FAE 获取文件，按“本地目录与挂载契约”中的结构放入 `$ROCKCHIP_ROOT/runtime/`。公开的两个 Git checkout 不能替代这组受控输入，本指南也不提供未经确认的下载 URL。

构建前逐一校验：

```bash
set -e
(
  cd "$ROCKCHIP_ROOT"
  sha256sum -c <<'SHA256'
6e230c07bbcfd0ea75c64d44d1b07ed3e549a88d4bb6908b4b9941d4a04fb424  runtime/include/float16.h
64202b613bb87c6445499cb871e7227f02e9af4720e30750344477ae6e87c16d  runtime/include/rknn3_api.h
113ec97719e04f82e51fcb8badeb18461070ac55ca9a5da87f887f3110b4fcbe  runtime/Linux/aarch64/librknn3_api.so
5ea77749f44be1f0c2ad0347242d4b431d3907d03eac11d265496ddd80cfd210  runtime/Linux/aarch64/librknn3_api_rkcp.so
8ec78e9d294e6ecf2be6ad9e16004ae5c50bcb9a8567d8bac7310ab27b66dd11  runtime/Linux/aarch64/librknn3_api_native.so
SHA256
)
```

只有全部五行都显示 `OK` 才能继续。缺文件或显示 `FAILED` 时，检查交付包版本和复制过程并停止构建；不要跳过校验或用其他版本文件替换。

## 获取或构建镜像

本项目没有声明可直接拉取的公共 RKNN3 完整开发镜像。默认从已经校验的本地输入构建：

```bash
set -e
export EDGE_MODEL_LAB_ROOT="${EDGE_MODEL_LAB_ROOT:-$PWD}"
test -f "$EDGE_MODEL_LAB_ROOT/README.md"
export ROCKCHIP_ROOT="$EDGE_MODEL_LAB_ROOT/platforms/rockchip-rk3588-rk1828"
test -f "$ROCKCHIP_ROOT/Dockerfile"

docker build \
  -t edge-model-lab/rknn3:1.0.4 \
  -f "$ROCKCHIP_ROOT/Dockerfile" \
  "$ROCKCHIP_ROOT"
```

`$ROCKCHIP_ROOT` 必须是构建上下文，因为 Dockerfile 从该目录复制 `vendor/` 和 `runtime/`。构建会把 Toolkit、Model Zoo、runtime、CMake 和 aarch64 交叉编译器放进镜像；不要在宿主机重复安装。

如果所在网络需要国内 PyPI 镜像，Dockerfile 支持可选的 `PIP_INDEX_URL` build argument。以下是可选构建方式，不改变 RKNN3 固定版本和本地文件哈希：

```bash
docker build \
  --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
  -t edge-model-lab/rknn3:1.0.4 \
  -f "$ROCKCHIP_ROOT/Dockerfile" \
  "$ROCKCHIP_ROOT"
```

构建后检查本地 tag 和架构：

```bash
docker image inspect edge-model-lab/rknn3:1.0.4 \
  --format 'ID={{.Id}} OS={{.Os}} ARCH={{.Architecture}} TAGS={{json .RepoTags}}'
```

应看到 `linux/amd64` 对应的 `OS=linux ARCH=amd64` 和目标 tag。

## 镜像自检

完整镜像自检会创建一次性容器并要求 GPU。它不挂载模型，也不执行量化或导出：

```bash
docker run --rm --gpus all \
  --entrypoint /bin/bash \
  edge-model-lab/rknn3:1.0.4 \
  -lc '
set -euo pipefail
grep -qx "VERSION_ID=\"22.04\"" /etc/os-release
python3.10 -c "from rknn.api import RKNN; print(\"RKNN import OK:\", RKNN)"
python3.10 -c "import torch; assert torch.cuda.is_available(), \"CUDA is not available\"; print(\"Torch:\", torch.__version__); print(\"CUDA:\", torch.version.cuda); print(\"GPU:\", torch.cuda.get_device_name(0))"
test "$RKNN3_MODEL_ZOO" = /opt/rknn3-model-zoo
test "$RKNN3_RUNTIME" = /opt/rknn3-runtime
test "$GCC_COMPILER" = aarch64-linux-gnu
test -f "$RKNN3_MODEL_ZOO/examples/Qwen3/python/export_llm.py"
test -f "$RKNN3_RUNTIME/include/float16.h"
test -f "$RKNN3_RUNTIME/include/rknn3_api.h"
test -f "$RKNN3_RUNTIME/Linux/aarch64/librknn3_api.so"
test -f "$RKNN3_RUNTIME/Linux/aarch64/librknn3_api_rkcp.so"
test -f "$RKNN3_RUNTIME/Linux/aarch64/librknn3_api_native.so"
aarch64-linux-gnu-g++ --version | head -n 1
env | grep -E "^(GCC_COMPILER|RKNN3_MODEL_ZOO|RKNN3_RUNTIME)=" | sort
'
```

命令退出码为 0 才算通过。PyTorch 在较新的 GPU 上可能给出计算能力兼容警告；本检查只确认 GPU/CUDA 对 PyTorch 可见。模型转换链路仍然保持“尚未验证”状态。

## 启动交互容器

下面创建示例目录并启动名为 `edge-model-lab-rknn3` 的容器。`original/` 可以在纯环境自检时为空；实际使用模型前，应通过合法来源把唯一上游副本放入该目录，并保持只读语义。

```bash
set -e
export EDGE_MODEL_LAB_ROOT="${EDGE_MODEL_LAB_ROOT:-$PWD}"
test -f "$EDGE_MODEL_LAB_ROOT/README.md"

MODEL=Qwen3-4B
VARIANT=rknn3-1.0.4-w4a16
MODEL_ROOT="$EDGE_MODEL_LAB_ROOT/models/Qwen/$MODEL"
OUTPUT_ROOT="$MODEL_ROOT/rockchip-rk3588-rk1828/$VARIANT"
TMP_ROOT="$EDGE_MODEL_LAB_ROOT/tmp/rockchip-rk3588-rk1828/$MODEL"

mkdir -p "$MODEL_ROOT/original"
mkdir -p "$OUTPUT_ROOT" "$TMP_ROOT/home"

docker run --name edge-model-lab-rknn3 \
  --gpus all \
  --interactive \
  --tty \
  --user "$(id -u):$(id -g)" \
  --env HOME=/workspace/tmp/home \
  --volume "$MODEL_ROOT/original:/workspace/model:ro" \
  --volume "$OUTPUT_ROOT:/workspace/output:rw" \
  --volume "$TMP_ROOT:/workspace/tmp:rw" \
  --workdir /opt/rknn3-model-zoo \
  edge-model-lab/rknn3:1.0.4 \
  /bin/bash
```

命令故意不使用 `--rm`，因此退出后可以按名称重新进入。不要给另一个项目复用这个容器名，也不要把整个仓库作为可写目录挂入容器。

## 容器内路径和工具链自检

进入容器后执行以下只读或临时目录检查：

```bash
set -euo pipefail
test "$(pwd)" = /opt/rknn3-model-zoo
test "$HOME" = /workspace/tmp/home
test -r /workspace/model
test -w /workspace/output
test -w /workspace/tmp
test "$RKNN3_MODEL_ZOO" = /opt/rknn3-model-zoo
test "$RKNN3_RUNTIME" = /opt/rknn3-runtime
test "$GCC_COMPILER" = aarch64-linux-gnu
test -f "$RKNN3_MODEL_ZOO/examples/Qwen3/python/export_llm.py"
test -f "$RKNN3_RUNTIME/Linux/aarch64/librknn3_api.so"
test -f "$RKNN3_RUNTIME/Linux/aarch64/librknn3_api_rkcp.so"
test -f "$RKNN3_RUNTIME/Linux/aarch64/librknn3_api_native.so"
python3.10 -c "from rknn.api import RKNN; print(RKNN)"
python3.10 -c "import torch; assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0))"
aarch64-linux-gnu-g++ --version | head -n 1
printf 'Rockchip RKNN3 toolchain self-check passed\n'
```

这仍然只是工具链自检。不要把输出当作模型已经完成量化、转换或板端验证的证据。

## 退出、重新进入与持久化

在容器 shell 中运行 `exit` 或按 `Ctrl-D` 会停止容器，但不会删除它。回到宿主机后查看并重新进入：

```bash
docker ps -a --filter name='^/edge-model-lab-rknn3$'
docker start -ai edge-model-lab-rknn3
```

`/workspace/model`、`/workspace/output` 和 `/workspace/tmp` 是 bind mount；其中 output 和 tmp 的写入直接保存在宿主机。`/workspace/model` 由 Docker 强制只读。

对镜像内 `/opt/rknn3-model-zoo` 或 `/opt/rknn3-runtime` 的交互式修改不会回写宿主源码或 runtime。此类容器层修改只在同一个命名容器被停止后重新启动时暂时保留，删除并重建容器后即消失。需要独立于容器生命周期持久保存的内容只能写入明确的 bind mount；可复现的工具链变更应修改 Dockerfile 后重建镜像，而不是在交互容器内安装。

## 离线迁移

在联网机器上把指定镜像保存为 tar，并立即生成和复核归档哈希：

```bash
set -e
export ROCKCHIP_TRANSFER_DIR="${ROCKCHIP_TRANSFER_DIR:-$PWD/rockchip-rknn3-transfer}"
mkdir -p "$ROCKCHIP_TRANSFER_DIR"

docker image inspect edge-model-lab/rknn3:1.0.4 \
  --format 'ID={{.Id}} OS={{.Os}} ARCH={{.Architecture}} TAGS={{json .RepoTags}}'
docker save \
  --output "$ROCKCHIP_TRANSFER_DIR/edge-model-lab-rknn3-1.0.4.tar" \
  edge-model-lab/rknn3:1.0.4
(
  cd "$ROCKCHIP_TRANSFER_DIR"
  sha256sum edge-model-lab-rknn3-1.0.4.tar \
    > edge-model-lab-rknn3-1.0.4.tar.sha256
  sha256sum -c edge-model-lab-rknn3-1.0.4.tar.sha256
)
```

把 tar 和 `.sha256` 文件送到离线机器后，先校验再导入：

```bash
set -e
export ROCKCHIP_TRANSFER_DIR="${ROCKCHIP_TRANSFER_DIR:-$PWD/rockchip-rknn3-transfer}"
(
  cd "$ROCKCHIP_TRANSFER_DIR"
  sha256sum -c edge-model-lab-rknn3-1.0.4.tar.sha256
)
docker load \
  --input "$ROCKCHIP_TRANSFER_DIR/edge-model-lab-rknn3-1.0.4.tar"
docker image inspect edge-model-lab/rknn3:1.0.4 \
  --format 'ID={{.Id}} OS={{.Os}} ARCH={{.Architecture}} TAGS={{json .RepoTags}} DIGESTS={{json .RepoDigests}}'
```

本地自建或从 tar 加载的镜像可能没有 registry digest；此时以传输 tar 的 SHA-256、镜像 ID、tag 和架构共同核对来源。

`docker save` 不包含任何 bind mount 内容。为支持离线重建、审计或继续工作，还要按各自许可证和访问控制单独迁移：

- 固定 commit 的两个官方 Git checkout；
- 经过上述 SHA-256 校验的受控 runtime；
- `models/Qwen/$MODEL/original/` 中的模型输入；
- 需要保留的平台 output 和必要的 tmp 内容。

不要把 registry 配置、Git/SSH 认证材料、模型站点认证材料或 shell 历史放入镜像归档或源码包。受控 runtime 能否复制到另一台机器或交给其他主体，以厂商交付条款为准。

## 常见问题和精确清理

### 构建上下文找不到文件

确认最后一个 `docker build` 参数是平台目录，而不是仓库根目录：

```bash
printf 'ROCKCHIP_ROOT=%s\n' "$ROCKCHIP_ROOT"
test -f "$ROCKCHIP_ROOT/Dockerfile"
test -f "$ROCKCHIP_ROOT/vendor/rknn3-toolkit/rknn3-toolkit/packages/rknn3_toolkit-1.0.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
test -d "$ROCKCHIP_ROOT/vendor/rknn3-model-zoo"
test -d "$ROCKCHIP_ROOT/runtime"
```

### wheel 或 runtime 哈希失败

不要构建。重新确认 checkout commit、SDK/交付包版本和文件复制过程，再运行“获取源码或构建输入”中的两组 `sha256sum -c`。哈希不同不是可忽略警告。

### 容器看不到 GPU

依次确认宿主驱动、NVIDIA Container Toolkit 和目标镜像：

```bash
nvidia-smi
docker run --rm --gpus all ubuntu:22.04 nvidia-smi
docker image inspect edge-model-lab/rknn3:1.0.4
```

如果前两项失败，先修复宿主驱动或 container runtime；不要在 RKNN3 容器内安装宿主驱动。

### 容器名已存在

先检查状态。要保留原容器就重新进入；只有确认不再需要该容器层时才删除指定容器并按“启动交互容器”重新创建：

```bash
docker ps -a --filter name='^/edge-model-lab-rknn3$'
docker start -ai edge-model-lab-rknn3
```

### 输出权限或磁盘空间异常

容器使用启动命令执行者的 UID/GID。检查三个精确宿主目录和 Docker 空间占用：

```bash
id
ls -ld \
  "$MODEL_ROOT/original" \
  "$OUTPUT_ROOT" \
  "$TMP_ROOT" \
  "$TMP_ROOT/home"
df -h "$EDGE_MODEL_LAB_ROOT"
docker system df
```

### 删除本指南创建的容器和镜像

以下命令只针对固定容器名和固定 image tag。先确认 output/tmp 中需要保留的文件已经在宿主机可见：

```bash
docker ps -a --filter name='^/edge-model-lab-rknn3$'
docker stop edge-model-lab-rknn3
docker rm edge-model-lab-rknn3
docker image rm edge-model-lab/rknn3:1.0.4
```

这些命令不会删除 bind mount 目录。不要使用全局 Docker 清理或删除整个 Docker 数据目录；它们可能移除其他平台仍在使用的容器、镜像、卷或构建缓存。

## 官方资料与许可证

- [Docker Engine：Ubuntu 安装](https://docs.docker.com/engine/install/ubuntu/)
- [Docker：Linux 安装后配置](https://docs.docker.com/engine/install/linux-postinstall/)
- [NVIDIA Container Toolkit：安装与 Docker 配置](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- [NVIDIA Driver 安装指南](https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/)
- [airockchip/rknn3-toolkit](https://github.com/airockchip/rknn3-toolkit/tree/V1.0.4)
- [airockchip/rknn3-model-zoo](https://github.com/airockchip/rknn3-model-zoo/tree/V1.0.4)

`rknn3-toolkit` V1.0.4 使用仓库内的 RKNN SDK License；`rknn3-model-zoo` V1.0.4 使用仓库内的 Apache License 2.0。runtime、模型权重、Python 包、基础系统包及其他第三方组件各自适用其随附许可证和再分发限制，不能用某一个仓库的许可证替代其他组件条款。尤其是受控 runtime，应遵守板卡 SDK、厂商交付包或 FAE 交付时附带的许可和保密要求。
