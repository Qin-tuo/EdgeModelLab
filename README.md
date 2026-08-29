# EdgeModelLab

> 面向真实硬件的边缘模型生产工作区。

EdgeModelLab 负责把上游模型快照转换成可追溯、可复现、可部署的边缘推理产物。模型源文件、平台工具链和生成结果各自隔离，避免同一份模型在不同硬件流程中失去边界。

## 当前平台

| 平台 | 产物 | 状态 |
| --- | --- | --- |
| Rockchip RK3588（纯 NPU） | RKNN / RKLLM 模型与部署包 | Toolkit2 2.3.2、RKLLM 1.3.0 工具链已纳入 |
| Rockchip RK3588 + RK1828 | RKNN3 模型与部署包 | Toolkit 1.0.4 配方可用 |
| NVIDIA Jetson Orin NX 16GB | TensorRT Edge-LLM ONNX / engine | 流程预留，待硬件验证 |
| Horizon S100 | 平台专用转换产物 | 流程预留 |

## 核心约定

- `models/Qwen/<model>/original/` 是只读的上游模型快照，所有平台共享同一输入。
- ONNX、量化权重、engine 和部署包必须放在对应的平台 variant 下，不能跨平台复用。
- 模型权重、生成产物、vendor checkout 内容、缓存和临时文件默认不进入 Git；
  第三方工具只通过 submodule 指针记录。
- 正式产物必须附带模型 revision、工具链版本、构建参数和校验和。

## 目录结构

```text
models/Qwen/<model>/
|-- original/                         上游模型快照
|-- rockchip-rk3588-rk1828/<variant>/ RKNN3 产物
|-- rockchip-rk3588/<variant>/        RKNN / RKLLM 产物
|-- jetson-orin-nx-16/<variant>/      TensorRT Edge-LLM 产物
`-- horizon-s100/<variant>/           Horizon 产物

platforms/
|-- rockchip-rk3588-rk1828/           Rockchip 生产配方
|-- rockchip-rk3588/                  纯 RK3588 NPU 生产配方
|-- jetson-orin-nx-16/                Jetson 生产边界
`-- horizon-s100/                     Horizon 生产边界
```

## 快速开始

创建通用下载环境：

```sh
conda env create -f common/environment.yml
conda activate qwen-common
```

使用 ModelScope 下载模型：

```sh
ROOT=$(git rev-parse --show-toplevel)
MODEL=Qwen3.5-4B

python -m pip install -U modelscope
modelscope download \
  --model Qwen/Qwen3.5-4B \
  --local_dir "$ROOT/models/Qwen/$MODEL/original"
```

相关入口：

- [通用下载环境](common/environment.yml)
- [RK3588 + RK1828 工具链说明](platforms/rockchip-rk3588-rk1828/README.md)
- [Rockchip 生产配方](platforms/rockchip-rk3588-rk1828/Dockerfile)
- [纯 RK3588 工具链说明](platforms/rockchip-rk3588/README.md)
- [Jetson Edge-LLM 项目](https://github.com/NVIDIA/TensorRT-Edge-LLM)
- [架构设计与决策记录](docs/superpowers/specs/2026-08-28-jetson-orin-edge-llm-design.md)

## Rockchip 快速入口

构建 RKNN3 Toolkit 1.0.4 生产镜像：

```sh
ROOT=$(git rev-parse --show-toplevel)
docker build -t edge-model-lab/rknn3:1.0.4 \
  -f "$ROOT/platforms/rockchip-rk3588-rk1828/Dockerfile" \
  "$ROOT/platforms/rockchip-rk3588-rk1828"
```

模型转换输出写入对应的 `models/Qwen/<model>/rockchip-rk3588-rk1828/<variant>/`，不要修改 `original/`。

纯 RK3588 不使用 RK1828 算力棒。普通网络或多模态视觉子图使用
`rknn-toolkit2` 生成 `.rknn`，Qwen 等大语言模型使用 `rknn-llm` 生成
`.rkllm`；输出写入 `models/Qwen/<model>/rockchip-rk3588/<variant>/`。

## 许可证

模型、厂商 SDK 和第三方工具链遵循各自上游许可证。发布派生产物前，请分别检查相关许可和再分发条款。
