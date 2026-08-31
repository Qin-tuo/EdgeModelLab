# EdgeModelLab

> 面向真实硬件的边缘模型生产工作区。

EdgeModelLab 负责把上游模型快照转换成可追溯、可复现、可部署的边缘推理产物。模型源文件、平台工具链和生成结果各自隔离，避免同一份模型在不同硬件流程中失去边界。

## 当前平台

| 平台 | 产物 | 状态 |
| --- | --- | --- |
| [Rockchip RK3588（纯 NPU）](platforms/rockchip-rk3588/README.md) | RKNN / RKLLM 模型与部署包 | Toolkit2 2.3.2、RKLLM 1.3.0 已固定 |
| [Rockchip RK3588 + RK1828](platforms/rockchip-rk3588-rk1828/README.md) | RKNN3 模型与部署包 | RKNN3 1.0.4 镜像环境已验证，模型链路未验证 |
| [NVIDIA Jetson Orin NX 16GB](platforms/jetson-orin-nx-16/README.md) | TensorRT Edge-LLM ONNX / engine | x86 NGC 基础镜像已验证，Orin 链路未验证 |
| [Horizon S100](platforms/horizon-s100/README.md) | 平台专用转换产物 | OE 3.7.0 环境可启动，当前 Qwen 无官方 S100 支持声明 |

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

modelscope download \
  --model Qwen/Qwen3.5-4B \
  --local_dir "$ROOT/models/Qwen/$MODEL/original"
```

相关入口：

- [通用下载环境](common/environment.yml)
- [纯 RK3588 工具链说明](platforms/rockchip-rk3588/README.md)
- [RK3588 + RK1828 工具链说明](platforms/rockchip-rk3588-rk1828/README.md)
- [Jetson Orin NX 工具链说明](platforms/jetson-orin-nx-16/README.md)
- [Horizon S100 工具链说明](platforms/horizon-s100/README.md)

## 许可证

模型、厂商 SDK 和第三方工具链遵循各自上游许可证。发布派生产物前，请分别检查相关许可和再分发条款。
