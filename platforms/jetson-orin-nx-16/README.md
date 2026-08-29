# NVIDIA Jetson Orin NX 16GB 容器启动指南

本指南从 Ubuntu x86-64 宿主机开始，拉取并自检 NVIDIA 官方 x86 镜像，再进入安装了 TensorRT Edge-LLM CLI 的容器。流程止于两个 CLI 的 `--help`，不包含模型量化、导出、engine build 或板端运行命令。

## 当前状态与固定版本

当前已验证 x86 NGC 基础镜像可启动，RTX 5070 8GB 对容器可见。Edge-LLM 依赖安装、任何具体模型，以及 Orin runtime 和 engine 均未验证。

| 项目 | 固定值 |
| --- | --- |
| x86 基础镜像 | `nvcr.io/nvidia/pytorch:25.12-py3` |
| linux/amd64 child manifest digest | `sha256:11e9976339d08669ede155cdbc601b1df5f57772fcee772b23527efc54e05602` |
| 基础系统 / Python | Ubuntu 24.04 / Python 3.12 |
| CUDA / PyTorch | CUDA 13.1 / PyTorch 2.10 development build (`2.10.0a0+b4e4ee81d3`) |
| TensorRT | 10.14.1 |
| TensorRT Edge-LLM | release `v0.10.0` / commit `71dd1bae032e70771265917ec74d3ff4cad07a10` |

`25.12-py3` 只用于 x86 导出环境准备，不是 Orin 运行镜像。Orin engine 必须在目标 Orin 上按其 JetPack、CUDA、TensorRT 和插件组合构建；Orin 只使用官方声明的 FP16、INT8、INT4，不能使用 FP8 或 FP4 系列 engine。

RTX 5070 8GB 只证明当前容器环境可访问 GPU。官方要求量化显存至少接近 FP16 checkpoint 大小，因此这里不保证示例中的 4B 模型可量化。

## 宿主机准备

宿主机要求 Ubuntu 22.04 或 24.04 x86-64、Git、Docker Engine（Server API `>= 1.49`，用于 `image inspect --platform`）、NVIDIA 驱动和 NVIDIA Container Toolkit。参考 [Docker Engine Ubuntu 安装](https://docs.docker.com/engine/install/ubuntu/) 与 [NVIDIA Container Toolkit 安装](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)；若 Server API 低于 1.49，先按 Docker 官方文档升级。Docker 组权限近似 root，只授予可信用户。

宿主机不安装 Edge-LLM、平台 Python 依赖或 TensorRT SDK。安装 Docker 与 GPU runtime 后仅验证：

```bash
docker version
docker version --format 'Server API={{.Server.APIVersion}}'
nvidia-smi
docker run --rm --gpus all ubuntu:22.04 nvidia-smi
```

## 准备源码和目录

从 EdgeModelLab 仓库根目录执行。宿主机只 clone 固定源码及 submodule；`pip` 安装留在容器内：

```bash
export EDGE_MODEL_LAB_ROOT="${EDGE_MODEL_LAB_ROOT:-$PWD}"
test -f "$EDGE_MODEL_LAB_ROOT/README.md"
export JETSON_ROOT="$EDGE_MODEL_LAB_ROOT/platforms/jetson-orin-nx-16"
mkdir -p "$JETSON_ROOT/vendor"
git clone --branch v0.10.0 --depth 1 --recurse-submodules \
  --shallow-submodules https://github.com/NVIDIA/TensorRT-Edge-LLM.git \
  "$JETSON_ROOT/vendor/TensorRT-Edge-LLM"
test "$(git -C "$JETSON_ROOT/vendor/TensorRT-Edge-LLM" rev-parse HEAD)" \
  = 71dd1bae032e70771265917ec74d3ff4cad07a10
```

准备只读原始模型、可写平台输出和可写临时目录。`MODEL=Qwen3.5-4B` 只是目录示例，不表示该模型已经验证：

```bash
MODEL=Qwen3.5-4B
VARIANT=tensorrt-edgellm-v0.10.0
MODEL_ROOT="$EDGE_MODEL_LAB_ROOT/models/Qwen/$MODEL"
OUTPUT_ROOT="$MODEL_ROOT/jetson-orin-nx-16/$VARIANT"
TMP_ROOT="$EDGE_MODEL_LAB_ROOT/tmp/jetson-orin-nx-16/$MODEL"
mkdir -p "$MODEL_ROOT/original" "$OUTPUT_ROOT" "$TMP_ROOT/home"
```

## 获取并自检镜像

按 [NGC User Guide](https://docs.nvidia.com/ngc/latest/ngc-catalog-user-guide.html) 交互登录，用户名必须原样保留。API key 只在密码提示中输入，不写入命令或环境文件。交互输入可避免 shell history 泄露，但 Docker 会使用 credential helper；未配置 helper 时会将凭据以 base64 写入 `$HOME/.docker/config.json`。建议配置 helper，或像下面这样拉取后立即登出：

```bash
docker login nvcr.io --username '$oauthtoken'
docker pull --platform linux/amd64 nvcr.io/nvidia/pytorch:25.12-py3
test "$(docker image inspect --platform linux/amd64 --format '{{.Descriptor.digest}}' nvcr.io/nvidia/pytorch:25.12-py3)" = sha256:11e9976339d08669ede155cdbc601b1df5f57772fcee772b23527efc54e05602
docker logout nvcr.io
```

tag pull 显示的是顶层多架构 index digest，与上表的 amd64 child manifest digest 不同；不要直接比较 pull 输出。上述断言独立验证本地 amd64 descriptor。

一次性容器只检查基础镜像中的 Python、PyTorch、CUDA 与 GPU，不表示 Edge-LLM 已安装：

```bash
docker run --rm --gpus all --platform linux/amd64 \
  nvcr.io/nvidia/pytorch:25.12-py3 \
  python3 -c 'import sys, torch; print(sys.version); print(torch.__version__); print(torch.version.cuda); assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0))'
```

组件版本依据 [PyTorch 25.12 发布说明](https://docs.nvidia.com/deeplearning/frameworks/pytorch-release-notes/rel-25-12.html)。

## 启动容器并自检工具链

保留前述目录变量，创建不带 `--rm` 的命名容器。只挂载所需目录，不把整个仓库可写挂入：

```bash
docker run --name edge-model-lab-jetson-export -it \
  --platform linux/amd64 --gpus all --shm-size=8g \
  --ulimit memlock=-1 --ulimit stack=67108864 \
  --user "$(id -u):$(id -g)" \
  --env HOME=/workspace/tmp/home \
  --volume "$MODEL_ROOT/original:/workspace/model:ro" \
  --volume "$OUTPUT_ROOT:/workspace/output:rw" \
  --volume "$TMP_ROOT:/workspace/tmp:rw" \
  --volume "$JETSON_ROOT/vendor/TensorRT-Edge-LLM:/workspace/TensorRT-Edge-LLM:rw" \
  --workdir /workspace/TensorRT-Edge-LLM \
  nvcr.io/nvidia/pytorch:25.12-py3 bash
```

进入容器后仅创建隔离 venv、安装固定 checkout，并显示 CLI help：

```bash
python3 -m venv /workspace/tmp/venv
source /workspace/tmp/venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[tools]'
tensorrt-edgellm-export --help
tensorrt-edgellm-quantize --help
python -m pip freeze > /workspace/output/environment.freeze.txt
```

v0.10.0 固定 `torch==2.13.0` 和 `transformers==5.14.1`；激活 venv 后使用的不是基础镜像 PyTorch 2.10。安装会额外下载依赖并占用 `tmp` 磁盘，但不会修改基础镜像的系统包，所以保留 `environment.freeze.txt`。两个 help 成功只证明入口可用，不证明模型流程或 Orin runtime 可用。

退出后可重新进入；venv 位于 `tmp` bind mount 中，会独立于容器持久化，但重入后需再次激活：

```bash
docker start -ai edge-model-lab-jetson-export
```

新 shell 启动后，在容器内执行：

```bash
source /workspace/tmp/venv/bin/activate
```

## 离线迁移与清理

联网机器保存指定基础镜像并生成哈希：

```bash
TRANSFER_DIR="${TRANSFER_DIR:-$PWD/jetson-export-transfer}"
mkdir -p "$TRANSFER_DIR"
docker image save --platform linux/amd64 \
  -o "$TRANSFER_DIR/nvidia-pytorch-25.12-py3-amd64.tar" \
  nvcr.io/nvidia/pytorch:25.12-py3
cd "$TRANSFER_DIR"
sha256sum nvidia-pytorch-25.12-py3-amd64.tar \
  > nvidia-pytorch-25.12-py3-amd64.tar.sha256
```

离线机器先校验再加载：

```bash
TRANSFER_DIR="${TRANSFER_DIR:-$PWD/jetson-export-transfer}"
cd "$TRANSFER_DIR"
sha256sum -c nvidia-pytorch-25.12-py3-amd64.tar.sha256
docker load -i nvidia-pytorch-25.12-py3-amd64.tar
test "$(docker image inspect --platform linux/amd64 --format '{{.Descriptor.digest}}' nvcr.io/nvidia/pytorch:25.12-py3)" = sha256:11e9976339d08669ede155cdbc601b1df5f57772fcee772b23527efc54e05602
```

该镜像归档不包含 Edge-LLM checkout、模型、`output`、`tmp` 中的 venv，也不包含命名容器的可写层；这些 bind mount 内容必须分别迁移。amd64 镜像不能作为 Orin 运行镜像。

只清理本指南指定的容器和镜像，不删除 bind mount，也不要使用全局 Docker prune：

```bash
docker stop edge-model-lab-jetson-export
docker rm edge-model-lab-jetson-export
docker image rm nvcr.io/nvidia/pytorch:25.12-py3
```

官方资料：[TensorRT Edge-LLM v0.10.0](https://github.com/NVIDIA/TensorRT-Edge-LLM/tree/v0.10.0)、[安装说明](https://github.com/NVIDIA/TensorRT-Edge-LLM/blob/v0.10.0/docs/source/user_guide/getting_started/installation.md)、[支持矩阵](https://github.com/NVIDIA/TensorRT-Edge-LLM/blob/v0.10.0/docs/source/user_guide/getting_started/support-matrix.md)。Edge-LLM 主仓库遵循 [Apache-2.0 LICENSE](https://github.com/NVIDIA/TensorRT-Edge-LLM/blob/v0.10.0/LICENSE)，submodule 各自遵循其随附许可证；NGC 镜像遵循 [NVIDIA governing terms](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/) 及镜像随附条款。
