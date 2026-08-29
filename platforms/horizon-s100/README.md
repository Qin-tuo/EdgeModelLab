# Horizon S100

本目录是 Horizon S100 模型生产流程的平台边界，目前仅作为预留骨架。
完整的转换、量化、部署包和冒烟测试流程尚未在 EdgeModelLab 中验证。

## 平台职责

未来本目录负责 S100 专用的环境声明、厂商工具链、模型转换、量化、产物
清单和验证说明。上游模型下载仍由 `models/Qwen/<model>/original/` 负责，
板端应用和 runtime 仍由各自的消费项目负责。

## 产物目录

```text
models/Qwen/<model>/
|-- original/                    上游模型快照，只读
`-- horizon-s100/<variant>/      S100 专用产物
    |-- onnx/                    平台私有 ONNX
    |-- engine/                  S100 专用运行时文件
    `-- manifest.json             provenance 和校验信息
```

所有 ONNX 都必须归属于具体平台和工具链变体，不能直接复用 Rockchip 或
TensorRT Edge-LLM 生成的图。任何硬件专用 engine 都必须在目标 S100 的
兼容环境中构建。

## 验证门槛

平台从预留变为已验证前，必须记录模型 revision、厂商工具链版本、量化方式、
ONNX opset、目标硬件和所有产物校验和，并通过目标设备上的加载和冒烟推理。

模型权重、runtime 二进制、缓存和临时构建文件不应提交到 Git。第三方
依赖应放在 `vendor/` 下并通过 Git submodule 固定上游地址和 commit，不能
复制第三方工作树进主仓库。
