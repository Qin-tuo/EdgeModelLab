# RK3588 + RK1828 平台

本目录面向 RK3588 主机连接 RK1828 算力棒的设备。RK1828 通过独立的
RKNN3 工具链工作；它不是只使用 RK3588 内置 NPU 的
`platforms/rockchip-rk3588` 路线。

## 官方工具链

工具链以 Git submodule 的形式放在 `vendor/` 下：

| 组件 | 版本 | 用途 |
| --- | --- | --- |
| `rknn3-toolkit` | `V1.0.4` | 在转换机上完成模型转换和量化 |
| `rknn3-model-zoo` | `V1.0.4` | 提供示例、转换脚本和板端部署参考 |

初始化依赖：

```sh
git submodule update --init --recursive \
  platforms/rockchip-rk3588-rk1828/vendor/rknn3-toolkit \
  platforms/rockchip-rk3588-rk1828/vendor/rknn3-model-zoo
```

运行时、配置和 Docker 配方由本目录管理。转换机使用与官方 wheel 匹配的
Python 环境，板端通过 RKNN3 runtime 访问 RK1828。具体安装依赖、模型支持
列表和量化参数以对应 submodule 的上游发布文档为准。

## 模型资产边界

只读输入是 `models/Qwen/<model>/original/`。RKNN3 的 ONNX、量化文件、
部署包和校验清单必须写入：

```text
models/Qwen/<model>/rockchip-rk3588-rk1828/<variant>/
```

这些产物只适用于 RK3588 + RK1828 设备，不能放入纯 RK3588 目录，也不能
与 `rknn-toolkit2` 或 `rknn-llm` 生成的 `.rknn`、`.rkllm` 文件混用。
