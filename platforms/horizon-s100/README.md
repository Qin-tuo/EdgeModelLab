# Horizon S100 OpenExplorer 容器启动指南

本指南在 x86-64 宿主机上获取 OpenExplorer（OE）3.7.0，启动 D-Robotics 官方容器并完成工具自检。终点是 `hb_compile --help`；不包含模型量化、导出、编译或板端部署命令。

## 当前状态与固定版本

OpenExplorer 3.7.0 是 S100、S100P、S600 通用算法工具链；S100 对应板端系统软件 4.0.5。官方镜像均为 `linux/amd64`：

| 模式 | 固定镜像 |
| --- | --- |
| GPU | `registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_gpu:v3.7.0` |
| CPU | `registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_cpu:v3.7.0` |

OE 通用镜像不等于 S100 LLM 工具链。S100 LLM 1.0.0 官方支持 Qwen2.5 1.5B/7B 等型号，但不支持本仓库的 Qwen2.5-0.5B 或 Qwen3-4B；Qwen3-4B 的公开支持属于 S600，不能外推到 S100。这里仅声明 OE 环境启动，不声明本项目 Qwen 的 S100 生产链路。

## 宿主机准备

官方要求原生 Ubuntu 22.04 x86-64、至少 16 GB 内存和 Docker `>= 20.10.10`。GPU 模式还要求 NVIDIA Container Toolkit `>= 1.16.2`、驱动 `>= 550.163.01`；CUDA 12.6 环境由镜像提供，宿主机无需安装平台 SDK 或 CUDA Toolkit。CPU 模式不需要 GPU、驱动或 NVIDIA Container Toolkit。

按 [Docker Engine Ubuntu 安装](https://docs.docker.com/engine/install/ubuntu/) 和 [NVIDIA Container Toolkit 安装](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) 配置后，仅做短验证：

```bash
docker version
uname -m
nvidia-smi
docker run --rm --gpus all ubuntu:22.04 nvidia-smi
```

CPU 模式只执行前两行。Docker 组权限近似 root，只授予可信用户。

## 获取 OE 包和镜像

从 EdgeModelLab 仓库根目录执行。宿主机只下载并解压 OE 包，不运行其中的安装、resolve、量化或转换命令：

```bash
set -e
export EDGE_MODEL_LAB_ROOT="${EDGE_MODEL_LAB_ROOT:-$PWD}"
test -f "$EDGE_MODEL_LAB_ROOT/README.md"
export HORIZON_ROOT="$EDGE_MODEL_LAB_ROOT/platforms/horizon-s100"
export HORIZON_DATA="$EDGE_MODEL_LAB_ROOT/tmp/horizon-s100/data"
mkdir -p "$HORIZON_ROOT/vendor" "$HORIZON_DATA"
curl -fL https://d-robotics-aitoolchain.oss-cn-beijing.aliyuncs.com/oe/3.7.0/oe-package-3.7.0-s100-s600.tgz \
  -o "$HORIZON_ROOT/vendor/oe-package-3.7.0-s100-s600.tgz"
tar -xzf "$HORIZON_ROOT/vendor/oe-package-3.7.0-s100-s600.tgz" \
  -C "$HORIZON_ROOT/vendor"
export OE_ROOT="$HORIZON_ROOT/vendor/drobotics_s100_s600_open_explorer_v3.7.0"
test -f "$OE_ROOT/run_docker.sh"
```

Registry 密码只在交互提示中输入，不要写入命令、环境文件或仓库。Docker 会使用已配置的 credential helper；没有 helper 时，凭据会以 base64 写入 `~/.docker/config.json`，可在拉取后立即登出：

```bash
docker login --username 'ccr$deliver-ronly' registry.d-robotics.cc
docker pull --platform linux/amd64 \
  registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_gpu:v3.7.0
# CPU 模式按需改为拉取：
# docker pull --platform linux/amd64 registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_cpu:v3.7.0
docker logout registry.d-robotics.cc
```

## 准备挂载并启动

`MODEL=Qwen3-4B` 和 `VARIANT=oe-3.7.0` 仅演示目录布局，不表示 S100 支持该模型：

```bash
MODEL=Qwen3-4B
VARIANT=oe-3.7.0
MODEL_ROOT="$EDGE_MODEL_LAB_ROOT/models/Qwen/$MODEL"
OUTPUT_ROOT="$MODEL_ROOT/horizon-s100/$VARIANT"
TMP_ROOT="$EDGE_MODEL_LAB_ROOT/tmp/horizon-s100/$MODEL"
mkdir -p "$MODEL_ROOT/original" "$OUTPUT_ROOT" "$TMP_ROOT/home"
```

官方必需的 `/open_explorer`、`/data` 可写；项目额外挂载只读原始模型、可写平台输出和临时目录。GPU/CPU 二选一：

```bash
# GPU 模式
HORIZON_IMAGE=registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_gpu:v3.7.0
HORIZON_ACCEL_ARGS=(--gpus all --shm-size=15g)
# CPU 模式（二选一，替换上两行）
# HORIZON_IMAGE=registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_cpu:v3.7.0
# HORIZON_ACCEL_ARGS=()
docker run --name edge-model-lab-horizon-s100 \
  --network host \
  "${HORIZON_ACCEL_ARGS[@]}" \
  --env HOST_UID="$(id -u)" --env HOST_GID="$(id -g)" \
  --env HOME=/workspace/tmp/home \
  --env OE_FTP_SERVER --env OE_FTP_USER_INFO \
  --mount type=bind,src="$OE_ROOT",dst=/open_explorer \
  --mount type=bind,src="$HORIZON_DATA",dst=/data \
  --mount type=bind,src="$MODEL_ROOT/original",dst=/workspace/model,readonly \
  --mount type=bind,src="$OUTPUT_ROOT",dst=/workspace/output \
  --mount type=bind,src="$TMP_ROOT",dst=/workspace/tmp \
  --workdir /open_explorer -it "$HORIZON_IMAGE" bash
```

命令不使用 `--rm`。官方镜像默认以 root 运行；不要擅自增加 `--user`，否则可能破坏镜像的 `PATH`、`LD_LIBRARY_PATH` 或工具权限。`--network host` 权限较宽，仅在可信宿主机使用。`OE_FTP_SERVER` 和 `OE_FTP_USER_INFO` 只在宿主已设置时透传，不要把值提交到仓库。

root 可能在挂载目录产生文件。退出前，只递归修正本项目专属的输出和临时目录：

```bash
chown -R "${HOST_UID}:${HOST_GID}" /workspace/output /workspace/tmp
```

若工具在 `/open_explorer` 或 `/data` 产生 root-owned 内容，只对确认的具体生成子目录或文件修正属主，绝不递归修改整个 vendor 或 data mount。

## 容器自检与重新进入

进入容器后只检查工具存在和帮助信息，不传入模型或执行转换：

```bash
python --version
python -m pip list | grep -Ei 'horizon|hbdk|hmct'
command -v hb_compile
hb_compile --help
```

退出后优先使用 `start` 加 `attach` 重新进入；官方说明其他进入方式可能丢失镜像预置的 `PATH`、`LD_LIBRARY_PATH`：

```bash
docker start edge-model-lab-horizon-s100
docker attach edge-model-lab-horizon-s100
```

## 离线迁移与清理

官方离线 tar 的 GPU 版约 27.44 GiB，CPU 版约 10.44 GiB。官方未发布 SHA-256；联网机器按所选模式下载后自行生成校验文件：

```bash
TRANSFER_DIR="${TRANSFER_DIR:-$PWD/horizon-s100-transfer}"
HORIZON_TAR=ai_toolchain_ubuntu_22_s100_s600_gpu_v3.7.0.tar
HORIZON_TAR_URL=https://d-robotics-aitoolchain.oss-cn-beijing.aliyuncs.com/oe/3.7.0/ai_toolchain_ubuntu_22_s100_s600_gpu_v3.7.0.tar
# CPU 模式替换上两行：
# HORIZON_TAR=ai_toolchain_ubuntu_22_s100_s600_cpu_v3.7.0.tar
# HORIZON_TAR_URL=https://d-robotics-aitoolchain.oss-cn-beijing.aliyuncs.com/oe/3.7.0/ai_toolchain_ubuntu_22_s100_s600_cpu_v3.7.0.tar
mkdir -p "$TRANSFER_DIR"
curl -fL -C - "$HORIZON_TAR_URL" -o "$TRANSFER_DIR/$HORIZON_TAR"
cd "$TRANSFER_DIR"
sha256sum "$HORIZON_TAR" > "$HORIZON_TAR.sha256"
```

离线目标机先校验再加载，并检查实际 repository/tag：

```bash
TRANSFER_DIR="${TRANSFER_DIR:-$PWD/horizon-s100-transfer}"
HORIZON_TAR=ai_toolchain_ubuntu_22_s100_s600_gpu_v3.7.0.tar
# CPU 模式替换上一行：
# HORIZON_TAR=ai_toolchain_ubuntu_22_s100_s600_cpu_v3.7.0.tar
cd "$TRANSFER_DIR"
sha256sum -c "$HORIZON_TAR.sha256"
docker load -i "$HORIZON_TAR"
docker image ls --digests | grep ai_toolchain_ubuntu_22_s100_s600
```

离线 tar 的本地 tag 可能不带 registry 前缀。以上一步显示的实际 tag 为准；例如 GPU tag 如下时补齐启动命令使用的 tag：

```bash
LOADED_TAG=ai_toolchain_ubuntu_22_s100_s600_gpu:v3.7.0
HORIZON_IMAGE=registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_gpu:v3.7.0
# CPU 模式替换上两行：
# LOADED_TAG=ai_toolchain_ubuntu_22_s100_s600_cpu:v3.7.0
# HORIZON_IMAGE=registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_cpu:v3.7.0
docker tag "$LOADED_TAG" "$HORIZON_IMAGE"
```

镜像 tar 不包含 OE 包、模型、`output`、`tmp`、命名容器可写层或 Registry 凭据，须分别迁移必要的 bind mount 内容。只清理本指南指定对象，不使用全局 prune：

```bash
docker stop edge-model-lab-horizon-s100
docker rm edge-model-lab-horizon-s100
docker image rm registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_gpu:v3.7.0
docker image rm registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_cpu:v3.7.0
```

官方资料：[环境部署](https://toolchain.d-robotics.cc/guide/env_install.html)、[OE 3.7.0 发布页](https://developer.d-robotics.cc/rdk_s_doc/en/Advanced_development/toolchain_development/algorithm_toolchain/overview)、[S100 LLM 1.0.0 支持列表](https://developer.d-robotics.cc/rdk_s_doc/en/Advanced_development/toolchain_development/LLM_Toolchain/s100_LLM_Toolchain)、[S600 LLM 支持列表](https://developer.d-robotics.cc/rdk_s_doc/en/Advanced_development/toolchain_development/LLM_Toolchain/rdk_s600/s100_LLM_Toolchain_v1_0_5)。OE 包、Docker 镜像及其中第三方组件分别遵守其随附许可证。
