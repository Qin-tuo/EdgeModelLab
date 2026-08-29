# Jetson Orin NX 16GB

本目录是 NVIDIA TensorRT Edge-LLM 生产流程的平台边界。它保存平台配方、
版本约束和验证说明，不复制 NVIDIA Edge-LLM 源码，也不保存模型权重。

## 当前状态

Jetson Orin NX 平台目前仍是预留平台，尚未在 EdgeModelLab 中完成完整验证。
在 exporter、目标设备构建、runtime 加载和冒烟推理全部通过前，不要把此目录
下的产物标记为已验证。

目标设备是 Jetson Orin NX 16GB（`sm_87`、aarch64）。选择 NVIDIA 容器版本前，
必须核对目标机的 JetPack/L4T、CUDA、TensorRT 和 Edge-LLM 版本。能在 x86
主机运行的容器，不代表它就是 Jetson runtime 环境。

## 平台职责

平台生产流程负责：

- 固定 NVIDIA/Edge-LLM 导出和目标设备构建环境；
- 模型量化和 ONNX 导出命令；
- Orin NX TensorRT engine 构建命令；
- provenance、校验和及产物验证；
- native Edge-LLM runtime 冒烟测试。

平台不负责上游模型下载和应用推理代码。模型下载由 `models/Qwen` 负责，
应用推理由使用产物的项目负责。

## 两阶段流程

```text
models/Qwen/<model>/original/              只读上游模型快照
        |
        | 导出主机（x86 或受支持的 NVIDIA 设备）
        v
models/Qwen/<model>/jetson-orin-nx-16/<variant>/
        |-- quantized/                    量化 checkpoint
        `-- onnx/                         Edge-LLM ONNX 图
        |
        | 目标 Orin NX（JetPack/TensorRT）
        v
        `-- engine/                       设备专用 TensorRT engine
```

ONNX 目录属于当前平台和工具链变体，不是公共模型级中间产物。TensorRT
engine 必须在实际运行它的 Orin NX 上构建，不能把 x86 GPU 或其他 Jetson
生成的 engine 直接复制过来。

## 本地目录约定

```text
platforms/jetson-orin-nx-16/
|-- README.md
|-- Dockerfile.export       # 环境验证后再添加
|-- scripts/                # 导出和目标设备构建入口
|-- config/                 # 模型和 engine 参数
|-- schema/                 # manifest/产物约束
`-- vendor/                 # 第三方依赖的 Git submodule
```

TensorRT-Edge-LLM 作为 Git submodule 放在 `vendor/` 下。父仓库只记录
submodule 的上游地址和 commit，不复制第三方工作树。模型产物放在：

```text
models/Qwen/<model>/jetson-orin-nx-16/<variant>/
|-- quantized/
|-- onnx/
|-- engine/
`-- manifest.json
```

## 容器挂载约定

导出开发时使用显式挂载：

```sh
ROOT=$(git rev-parse --show-toplevel)
MODEL=Qwen3.5-4B

docker run --gpus all -it \
  --name edgellm-export \
  --volume "$ROOT/models/Qwen/$MODEL/original:/workspace/model:ro" \
  --volume "$ROOT/models/Qwen/$MODEL/jetson-orin-nx-16:/workspace/output" \
  --volume "$ROOT/platforms/jetson-orin-nx-16:/workspace/platform" \
  --workdir /workspace/platform \
  nvcr.io/nvidia/pytorch:<verified-tag> \
  bash
```

镜像由 Docker 管理，不复制到本目录。量化 checkpoint 和 ONNX 必须写入
`/workspace/output`，这样才会出现在宿主机的模型变体目录中。`original/`
必须以只读方式挂载。

TensorRT Edge-LLM 应安装在固定的平台环境中，不能安装到
`common/qwen-common`。导出命令以 [NVIDIA TensorRT-Edge-LLM 仓库](https://github.com/NVIDIA/TensorRT-Edge-LLM)
及 [Jetson AI Lab 教程](https://github.com/NVIDIA-AI-IOT/jetson-ai-lab/blob/main/src/content/tutorials/model-optimization/tensorrt-edge-llm.mdx)
为准。

## 版本和 provenance

每个正式变体的 manifest 至少记录：

- 上游模型仓库和 revision；
- Edge-LLM commit；
- NVIDIA 容器 tag；
- JetPack/L4T、CUDA、TensorRT 和插件版本；
- 量化格式和 ONNX opset；
- 目标架构和 engine 构建参数；
- 所有发布文件的校验和。

容器 tag、Edge-LLM、JetPack、CUDA、TensorRT、量化格式和目标 GPU 是一个
整体兼容集合，不能只升级其中一个组件。

## 验证门槛

平台从预留变为已验证前，必须完成：

1. 记录模型源快照和 revision；
2. 量化 checkpoint 和 ONNX 图完整且有校验和；
3. 对应 Edge-LLM builder 能接受该 ONNX；
4. engine 在目标 Orin NX 上构建成功；
5. native runtime 能加载 engine 并通过冒烟推理；
6. manifest 记录完整兼容集合，且没有破坏 Rockchip 或通用环境边界。

## 安全规则

不要将 Hugging Face、NGC、代理、SSH 或其他凭据写入仓库。模型权重、
量化文件、ONNX、engine、缓存和临时构建文件均不应提交到 Git。第三方
工具链通过 submodule 指针管理，具体工作树由 `git submodule update` 获取。
