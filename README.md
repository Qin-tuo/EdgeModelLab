# EdgeModelLab

> **从上游权重快照，到可审计、可复现、可部署的边缘模型产物。**

EdgeModelLab 是一个面向边缘 AI 的模型生产工作区。它把模型源文件、平台专用转换流程、量化配置、构建环境与发布清单组织在同一条生产链路中，让模型能够从实验性 checkpoint 稳定走向真实硬件。

这个仓库不是模型权重镜像，也不是某一块开发板的应用工程。Git 中保留的是可复用的流程骨架、平台边界、版本约束和复现说明；模型权重、ONNX、TensorRT/RKNN 产物、厂商 SDK、缓存和临时构建文件默认保留在本地。

## 项目状态

| 平台 | 生产职责 | 当前状态 |
| --- | --- | --- |
| Rockchip RK3588 / RK1828 | RKNN3 转换、量化与部署包 | 已有 Toolkit 1.0.4 配方 |
| NVIDIA Jetson Orin NX 16GB | TensorRT Edge-LLM 导出与 engine 构建 | 已规划边界，完整链路待硬件验证 |
| Horizon S100 | 平台专用转换与打包 | 预留 |

当前工作区覆盖 Qwen2.5-0.5B-Instruct、Qwen3-4B 和 Qwen3.5-4B。新增模型不需要改动框架；只有工具链、产物完整性和板端冒烟测试全部通过后，平台变体才会标记为已验证。

## 生产链路

```text
官方模型仓库
    |
    v
models/Qwen/<model>/original/             只读的上游模型快照
    |
    +--> platforms/rockchip-rk3588-rk1828  RKNN3 ONNX -> RKNN3 部署包
    |
    +--> platforms/jetson-orin-nx-16       Edge-LLM ONNX -> TensorRT engine
    |
    `--> platforms/<future-target>         其他硬件平台的独立生产流程
```

`original/` 是所有平台共享的唯一模型输入。ONNX 必须归属于具体平台和工具链变体，不能建立公共的模型级 ONNX 目录。RKNN3 ONNX 与 TensorRT Edge-LLM ONNX 默认不可互换；TensorRT engine 始终绑定目标 GPU、JetPack、TensorRT、插件和构建参数。

## 目录结构

```text
EdgeModelLab/
|-- AGENT.md                              仓库边界与协作约定
|-- README.md                             项目入口与操作指南
|-- common/
|   `-- environment.yml                   通用模型下载环境
|-- models/Qwen/<model>/                  本地模型资产，默认不上传
|   |-- original/                         上游模型快照
|   |-- rockchip-rk3588-rk1828/<variant>/ RKNN3 输出与部署包
|   |-- jetson-orin-nx-16/<variant>/      Edge-LLM ONNX、engine 与清单
|   `-- horizon-s100/<variant>/           未来平台产物
|-- platforms/
|   |-- rockchip-rk3588-rk1828/           Rockchip 生产配方
|   |-- jetson-orin-nx-16/                Jetson 生产边界
|   `-- horizon-s100/                     Horizon 平台边界
|-- docs/                                 架构设计与决策记录
`-- tmp/                                  临时转换目录
```

`models/` 下的下载文件由 `.gitignore` 排除；通过 `.gitkeep` 可以保留需要共享的目录层级。`platforms/*/vendor/`、本地 TensorRT-Edge-LLM checkout 和构建缓存同样不进入 Git。第三方依赖通过上游仓库与 commit 记录复现，不把完整 vendor checkout 复制进主仓库。

## 快速开始

### 1. 创建通用下载环境

通用环境只负责官方 Hugging Face/ModelScope 下载工具和基础模型检查，不安装 Rockchip、NVIDIA 或其他厂商 SDK。

```sh
conda env create -f common/environment.yml
conda activate qwen-common
```

### 2. 下载上游模型快照

建议始终指定明确的 revision，并将 `original/` 视为只读输入。

```sh
ROOT=$(git rev-parse --show-toplevel)
MODEL=Qwen3-4B

mkdir -p "$ROOT/models/Qwen/$MODEL/original"
hf download Qwen/Qwen3-4B \
  --revision 1cfa9a7208912126459214e8b04321603b3df60c \
  --local-dir "$ROOT/models/Qwen/$MODEL/original"
```

如果 Hugging Face 网络或本地带宽不适合当前任务，可以使用 ModelScope：

```sh
ROOT=$(git rev-parse --show-toplevel)
MODEL=Qwen3.5-4B

python -m pip install -U modelscope
modelscope download \
  --model Qwen/Qwen3.5-4B \
  --local_dir "$ROOT/models/Qwen/$MODEL/original"
```

### 3. 选择平台生产配方

平台流程只读 `original/`，并将所有生成文件写入同一模型下的平台变体目录。进入转换阶段前，先记录模型 revision、工具链版本、量化格式、ONNX opset、目标硬件和输出校验和。

## AutoDL 工作流

当本地 GPU 显存或磁盘不足时，可以只把 `original/` 模型放到 AutoDL，在云端完成量化与 ONNX 导出，再把平台变体传回本机。不要在 AutoDL 普通容器实例内部再次运行 Docker；直接使用 AutoDL 提供的 PyTorch/CUDA 环境。

```sh
mkdir -p /root/autodl-tmp/EdgeModelLab/models/Qwen/Qwen3.5-4B/original
python3 -m pip install -U modelscope
modelscope download \
  --model Qwen/Qwen3.5-4B \
  --local_dir /root/autodl-tmp/EdgeModelLab/models/Qwen/Qwen3.5-4B/original
```

AutoDL 中的量化与导出输出应写入：

```text
/root/autodl-tmp/EdgeModelLab/models/Qwen/Qwen3.5-4B/
|-- jetson-orin-nx-16/<variant>/quantized/
```

完成导出后，只回传对应的平台变体目录，不回传原始模型的重复副本。量化和导出过程必须记录完整的兼容性集合，包括模型 revision、Edge-LLM commit、Python/PyTorch/ModelOpt/ONNX 版本、量化方法和校验信息。

参考文档：[AutoDL 快速开始](https://www.autodl.com/docs/quick_start/)、[SSH 登录](https://www.autodl.com/docs/ssh/)、[文件上传](https://www.autodl.com/docs/scp/)。

## 平台生产配方

### Rockchip RK3588 / RK1828

Rockchip 配方构建隔离的 RKNN3 Toolkit 1.0.4 镜像。vendor checkout 和 runtime 文件是本地构建输入，不上传到 Git。

```sh
ROOT=$(git rev-parse --show-toplevel)
docker build -t edge-model-lab/rknn3:1.0.4 \
  -f "$ROOT/platforms/rockchip-rk3588-rk1828/Dockerfile" \
  "$ROOT/platforms/rockchip-rk3588-rk1828"
```

进入容器时显式挂载选定模型：

```sh
MODEL=Qwen3-4B
ROOT=$(git rev-parse --show-toplevel)
docker run --rm -it --gpus all \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp \
  --volume "$ROOT/models/Qwen/$MODEL:/workspace/model" \
  --workdir /opt/rknn3-model-zoo \
  edge-model-lab/rknn3:1.0.4 bash
```

不要把 RKNN3 安装进 `qwen-common`，也不要把 Rockchip ONNX 当作 NVIDIA 工具链的输入。

### Jetson Orin NX / TensorRT Edge-LLM

Jetson 流程分为两个阶段：

1. 在支持的 x86 主机或 NVIDIA 导出设备上完成模型量化与 Edge-LLM ONNX 导出；
2. 在实际运行模型的 Orin NX 上编译 C++ runtime 并构建 TensorRT engine。

x86 主机可以导出 ONNX，但不能发布 Orin NX engine。最终 engine 与 Orin NX 的 `sm_87`、JetPack/L4T、CUDA、TensorRT、插件和构建参数绑定。

参考 [NVIDIA TensorRT-Edge-LLM](https://github.com/NVIDIA/TensorRT-Edge-LLM) 和 [Jetson AI Lab 教程](https://github.com/NVIDIA-AI-IOT/jetson-ai-lab/blob/main/src/content/tutorials/model-optimization/tensorrt-edge-llm.mdx)。当前 Jetson 目录仍是预留边界，尚未在本仓库声明已验证的 Dockerfile 或导出脚本。

### Horizon S100

Horizon 平台保留独立目录和工具链边界。只有在形成真实产物、补齐版本清单并通过目标硬件冒烟测试后，才将其标记为已验证平台。

## 可复现性契约

每个正式平台变体至少记录：

- 上游模型仓库和 revision；
- exporter、厂商工具链和 Edge-LLM commit；
- Docker 镜像 tag 或环境锁定文件；
- JetPack/L4T、CUDA、TensorRT 和插件版本；
- 量化格式、ONNX opset 和 engine 构建参数；
- 目标 GPU 架构；
- 所有发布文件的校验和。

变体名称使用可读信息，例如 `rknn3-1.0.4-w4a16` 或 `tensorrt-edgellm-int4-awq`，不要把 hash 放进目录名。manifest 是产物进入发布状态前的必要门槛，而不是事后补充的说明文件。

## 扩展新平台

1. 创建 `platforms/<target>/`，写清平台边界和固定环境；
2. 只有产生真实产物后，才在每个模型下创建对应 target 目录；
3. 将该平台的 ONNX、engine 和部署包保持在自己的 variant 内；
4. 通过显式挂载使用源模型和输出目录，不把模型树复制进 Docker build context；
5. 添加 manifest 和冒烟测试后，才把平台标记为已验证。

部署应用和板端 runtime 仍由各自项目负责。EdgeModelLab 只负责模型生产、产物边界和复现证据。

## 许可证与致谢

厂商 SDK、第三方工具链和模型仓库各自遵循其上游许可证。发布派生产物或重新分发 vendor 内容前，请检查对应许可证。主仓库优先记录上游地址和 commit，而不是复制不必要的第三方代码。
