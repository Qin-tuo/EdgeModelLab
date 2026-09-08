# NVIDIA Jetson Orin NX 16GB 容器启动

本指南只准备 x86 导出环境并完成 Edge-LLM CLI 自检，不执行模型量化、导出或 engine build。NGC 基础镜像和 GPU 可见性已验证；Edge-LLM 模型链路与 Orin runtime 尚未验证。

## 固定版本与前置条件

| 组件 | 固定值 |
| --- | --- |
| x86 基础镜像 | `nvcr.io/nvidia/pytorch:25.12-py3` |
| amd64 manifest | `sha256:11e9976339d08669ede155cdbc601b1df5f57772fcee772b23527efc54e05602` |
| 镜像环境 | Ubuntu 24.04 / Python 3.12 / CUDA 13.1 / PyTorch 2.10 dev / TensorRT 10.14.1 |
| Edge-LLM submodule | `bb291453bc10d9bd1142070c605e090d4e483ee2`（`v0.10.0` 后的官方文档更新） |

TensorRT source submodule 固定为 `v10.14`（`3b4ddc1d45f11167f2ea53dc6046bba8df800e2d`），用于
源码、头文件和 ONNX parser 参考；它不替代 Orin JetPack 提供的目标 TensorRT runtime。

该镜像不是 Orin 运行镜像。Orin engine 必须在目标 Orin 上使用匹配的 JetPack、CUDA 和 TensorRT 构建；Orin 只使用 FP16、INT8、INT4，不支持 FP8/FP4 系列 engine。RTX 5070 8GB 只证明环境可用，不保证 4B 模型量化显存足够。

宿主机使用 Ubuntu 22.04/24.04 x86-64、Docker Server API `>=1.49`、NVIDIA 驱动和 NVIDIA Container Toolkit。安装见 [Docker Engine](https://docs.docker.com/engine/install/ubuntu/) 与 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)。宿主机不安装 Edge-LLM 或平台 Python 依赖。

```bash
docker version --format 'Server API={{.Server.APIVersion}}'
nvidia-smi
docker run --rm --gpus all ubuntu:22.04 nvidia-smi
```

## 准备源码与镜像

```bash
export EDGE_MODEL_LAB_ROOT="${EDGE_MODEL_LAB_ROOT:-$PWD}"
test -f "$EDGE_MODEL_LAB_ROOT/README.md"
export JETSON_ROOT="$EDGE_MODEL_LAB_ROOT/platforms/jetson-orin-nx-16"

git -C "$EDGE_MODEL_LAB_ROOT" submodule update --init --recursive \
  platforms/jetson-orin-nx-16/vendor/TensorRT-Edge-LLM \
  platforms/jetson-orin-nx-16/vendor/TensorRT
test "$(git -C "$JETSON_ROOT/vendor/TensorRT-Edge-LLM" rev-parse HEAD)" \
  = bb291453bc10d9bd1142070c605e090d4e483ee2
test "$(git -C "$JETSON_ROOT/vendor/TensorRT" rev-parse HEAD)" \
  = 3b4ddc1d45f11167f2ea53dc6046bba8df800e2d
```

按 [NGC 文档](https://docs.nvidia.com/ngc/latest/ngc-catalog-user-guide.html) 登录。API key 只在提示中输入；Docker 会写入 credential helper，未配置 helper 时会以 base64 写入 `~/.docker/config.json`，拉取后可立即登出。

```bash
docker login nvcr.io --username '$oauthtoken'
docker pull --platform linux/amd64 nvcr.io/nvidia/pytorch:25.12-py3
test "$(docker image inspect --platform linux/amd64 --format '{{.Descriptor.digest}}' nvcr.io/nvidia/pytorch:25.12-py3)" \
  = sha256:11e9976339d08669ede155cdbc601b1df5f57772fcee772b23527efc54e05602
docker logout nvcr.io
```

基础镜像自检不代表 Edge-LLM 已安装：

```bash
docker run --rm --gpus all --platform linux/amd64 \
  nvcr.io/nvidia/pytorch:25.12-py3 \
  python3 -c 'import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())'
```

## 启动并自检工具链

`Qwen3.5-4B` 仅作为目录示例，不表示模型链路已验证。

```bash
MODEL=Qwen3.5-4B
VARIANT=tensorrt-edgellm-v0.10.0
MODEL_ROOT="$EDGE_MODEL_LAB_ROOT/models/Qwen/$MODEL"
OUTPUT_ROOT="$MODEL_ROOT/jetson-orin-nx-16/$VARIANT"
TMP_ROOT="$EDGE_MODEL_LAB_ROOT/tmp/jetson-orin-nx-16/$MODEL"
mkdir -p "$MODEL_ROOT/original" "$OUTPUT_ROOT" "$TMP_ROOT/home"

docker run --name edge-model-lab-jetson-export -it \
  --platform linux/amd64 --gpus all --shm-size=8g \
  --ulimit memlock=-1 --ulimit stack=67108864 \
  --user "$(id -u):$(id -g)" --env HOME=/workspace/tmp/home \
  --mount type=bind,src="$MODEL_ROOT/original",dst=/workspace/model,readonly \
  --mount type=bind,src="$OUTPUT_ROOT",dst=/workspace/output \
  --mount type=bind,src="$TMP_ROOT",dst=/workspace/tmp \
  --mount type=bind,src="$JETSON_ROOT/vendor/TensorRT-Edge-LLM",dst=/workspace/TensorRT-Edge-LLM \
  --workdir /workspace/TensorRT-Edge-LLM \
  nvcr.io/nvidia/pytorch:25.12-py3 bash
```

以下命令只在容器内执行。当前 submodule 固定 `torch==2.13.0`、`transformers==5.14.1`；venv 会额外占用磁盘，但不会修改基础镜像系统包。

```bash
python3 -m venv /workspace/tmp/venv
source /workspace/tmp/venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[tools]'
tensorrt-edgellm-export --help
tensorrt-edgellm-quantize --help
python -m pip freeze > /workspace/output/environment.freeze.txt
```

退出后使用 `docker start -ai edge-model-lab-jetson-export`，再在容器内执行 `source /workspace/tmp/venv/bin/activate`。

## 离线迁移与清理

```bash
docker image save --platform linux/amd64 -o nvidia-pytorch-25.12-py3-amd64.tar \
  nvcr.io/nvidia/pytorch:25.12-py3
sha256sum nvidia-pytorch-25.12-py3-amd64.tar > nvidia-pytorch-25.12-py3-amd64.tar.sha256
sha256sum -c nvidia-pytorch-25.12-py3-amd64.tar.sha256
docker load -i nvidia-pytorch-25.12-py3-amd64.tar
```

归档不包含 submodule、模型、输出、tmp venv 或容器可写层；amd64 镜像不能在 Orin 上作为 runtime 使用。

```bash
docker stop edge-model-lab-jetson-export 2>/dev/null || true
docker rm edge-model-lab-jetson-export 2>/dev/null || true
docker image rm nvcr.io/nvidia/pytorch:25.12-py3
```

不要执行全局 Docker 清理。上游资料：[安装说明](https://github.com/NVIDIA/TensorRT-Edge-LLM/blob/main/docs/source/user_guide/getting_started/installation.md)、[支持矩阵](https://github.com/NVIDIA/TensorRT-Edge-LLM/blob/main/docs/source/user_guide/getting_started/support-matrix.md)、[PyTorch 25.12](https://docs.nvidia.com/deeplearning/frameworks/pytorch-release-notes/rel-25-12.html)。Edge-LLM 主仓库为 Apache-2.0，submodule 各自遵循随附许可证，NGC 镜像遵循 NVIDIA 条款。
