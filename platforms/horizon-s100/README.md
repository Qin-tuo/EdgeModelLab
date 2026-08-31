# D-Robotics Horizon S100 容器启动

本指南只启动 OpenExplorer（OE）3.7.0 官方环境并完成工具自检，不执行模型转换。

## 状态与前置条件

OE 3.7.0 是 S100/S100P/S600 通用算法工具链，S100 对应板端系统软件 4.0.5。它不是 S100 LLM 工具链：S100 LLM 1.0.0 不支持本仓库的 Qwen2.5-0.5B 或 Qwen3-4B；Qwen3-4B 的公开支持属于 S600，不能外推到 S100。

官方 linux/amd64 镜像：

```text
registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_gpu:v3.7.0
registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_cpu:v3.7.0
```

宿主机要求原生 Ubuntu 22.04 x86-64、内存不少于 16GB、Docker 20.10.10+。GPU 模式还需 NVIDIA Container Toolkit 1.16.2+ 和驱动 550.163.01+；CUDA 12.6 环境由镜像提供。安装见 [Docker Engine](https://docs.docker.com/engine/install/ubuntu/) 与 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)。CPU 模式不需要 GPU。

```bash
test "$(uname -m)" = x86_64
docker version
```

仅 GPU 模式执行：

```bash
nvidia-smi
docker run --rm --gpus all ubuntu:22.04 nvidia-smi
```

## 获取 OE 包与镜像

宿主机只下载、解压和挂载 OE 包，不安装或运行其中的平台 SDK。

```bash
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

登录密码从[官方资源页](https://developer.d-robotics.cc/rdk_s_doc/en/Advanced_development/toolchain_development/algorithm_toolchain/overview)获取并在提示中输入，不写进命令。Docker 会使用 credential helper；无 helper 时会写入 `~/.docker/config.json`，拉取后可登出。

```bash
docker login --username 'ccr$deliver-ronly' registry.d-robotics.cc
docker pull registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_gpu:v3.7.0
# CPU 模式按需拉取：
# docker pull registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_cpu:v3.7.0
docker logout registry.d-robotics.cc
```

## 启动与自检

`Qwen3-4B` 仅演示挂载目录，不代表 S100 支持。

```bash
MODEL=Qwen3-4B
VARIANT=oe-3.7.0
MODEL_ROOT="$EDGE_MODEL_LAB_ROOT/models/Qwen/$MODEL"
OUTPUT_ROOT="$MODEL_ROOT/horizon-s100/$VARIANT"
TMP_ROOT="$EDGE_MODEL_LAB_ROOT/tmp/horizon-s100/$MODEL"
mkdir -p "$MODEL_ROOT/original" "$OUTPUT_ROOT" "$TMP_ROOT/home"

# GPU 模式；CPU 模式把 image 改为 cpu tag，并设置 HORIZON_ACCEL_ARGS=()。
HORIZON_IMAGE=registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_gpu:v3.7.0
HORIZON_ACCEL_ARGS=(--gpus all --shm-size=15g)

docker run --name edge-model-lab-horizon-s100 -it \
  --network host "${HORIZON_ACCEL_ARGS[@]}" \
  --env HOST_UID="$(id -u)" --env HOST_GID="$(id -g)" \
  --env OE_FTP_SERVER --env OE_FTP_USER_INFO \
  --mount type=bind,src="$OE_ROOT",dst=/open_explorer \
  --mount type=bind,src="$HORIZON_DATA",dst=/data \
  --mount type=bind,src="$MODEL_ROOT/original",dst=/workspace/model,readonly \
  --mount type=bind,src="$OUTPUT_ROOT",dst=/workspace/output \
  --mount type=bind,src="$TMP_ROOT",dst=/workspace/tmp \
  --workdir /open_explorer "$HORIZON_IMAGE" bash
```

官方镜像默认 root，且 `--network host` 权限较宽。不要随意增加 `--user`，以免破坏 PATH/LD_LIBRARY_PATH。只对本项目输出修正属主，不要递归修改整个 `/open_explorer` 或 `/data`。

```bash
# 容器内执行
python3 --version
python3 -m pip list | grep -E 'horizon|hbdk|hmct'
command -v hb_compile
hb_compile --help
chown -R "${HOST_UID}:${HOST_GID}" /workspace/output /workspace/tmp
```

退出后优先使用 `docker start edge-model-lab-horizon-s100` 和 `docker attach edge-model-lab-horizon-s100`，以保留官方环境变量。

## 离线迁移与清理

官方离线 tar：GPU 约 27.44GiB，CPU 约 10.44GiB。官方未发布 SHA-256，应在可信机器下载后自行生成校验文件。

```bash
curl -fLO https://d-robotics-aitoolchain.oss-cn-beijing.aliyuncs.com/oe/3.7.0/ai_toolchain_ubuntu_22_s100_s600_gpu_v3.7.0.tar
# CPU 包：将上面的 gpu 文件名替换为 ai_toolchain_ubuntu_22_s100_s600_cpu_v3.7.0.tar
sha256sum ai_toolchain_ubuntu_22_s100_s600_gpu_v3.7.0.tar \
  > ai_toolchain_ubuntu_22_s100_s600_gpu_v3.7.0.tar.sha256
sha256sum -c ai_toolchain_ubuntu_22_s100_s600_gpu_v3.7.0.tar.sha256
docker load -i ai_toolchain_ubuntu_22_s100_s600_gpu_v3.7.0.tar
docker image ls | grep ai_toolchain_ubuntu_22_s100_s600
```

离线 tar 可能加载为不带 registry 的本地 tag；确认列表后补 tag：

```bash
docker tag ai_toolchain_ubuntu_22_s100_s600_gpu:v3.7.0 \
  registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_gpu:v3.7.0
```

镜像不包含 OE 包、模型、输出、tmp 或凭据，这些需要单独迁移。

```bash
docker stop edge-model-lab-horizon-s100 2>/dev/null || true
docker rm edge-model-lab-horizon-s100 2>/dev/null || true
docker image rm registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_gpu:v3.7.0
```

不要执行全局 Docker 清理。官方资料：[环境部署](https://toolchain.d-robotics.cc/guide/env_install.html)、[S100 LLM 支持](https://developer.d-robotics.cc/rdk_s_doc/Advanced_development/toolchain_development/LLM_Toolchain/s100_LLM_Toolchain)。工具链和镜像遵循各自随附许可证。
