# 纯 RK3588 平台

本目录面向只使用 RK3588 芯片内置 NPU 的设备，不使用 RK1828 算力棒。
它与 `platforms/rockchip-rk3588-rk1828` 是两条独立的生产路线，不能共享
转换工具、运行时或生成模型。

## 官方工具链

工具链以 Git submodule 的形式放在 `vendor/` 下，并固定到可复现的发布版本：

| 组件 | 版本 | 用途 | 主要产物 |
| --- | --- | --- | --- |
| `rknn-toolkit2` | `v2.3.2` | 普通神经网络和多模态视觉子图转换 | `.rknn` |
| `rknn-llm` | `release-v1.3.0` | Qwen 等大语言模型量化与转换 | `.rkllm` |

`rknn-toolkit2` 的板端 Lite API 和 RKNPU2 runtime 用于加载 `.rknn`；
`rknn-llm` 自带的 RKLLM runtime 用于加载 `.rkllm`。两者都针对 RK3588
的内置 NPU，不包含 RK1828 算力棒的 RKNN3 runtime。

首次克隆仓库后初始化这两个依赖：

```sh
git submodule update --init --recursive \
  platforms/rockchip-rk3588/vendor/rknn-toolkit2 \
  platforms/rockchip-rk3588/vendor/rknn-llm
```

如果当前 checkout 只显示少量说明文件，说明本地启用了稀疏检出。转换前
恢复对应发布版本的完整官方文件：

```sh
git -C platforms/rockchip-rk3588/vendor/rknn-toolkit2 sparse-checkout disable 2>/dev/null || true
git -C platforms/rockchip-rk3588/vendor/rknn-toolkit2 checkout --detach v2.3.2
git -C platforms/rockchip-rk3588/vendor/rknn-llm sparse-checkout disable 2>/dev/null || true
git -C platforms/rockchip-rk3588/vendor/rknn-llm checkout --detach release-v1.3.0
```

转换机使用 `vendor/` 中与 Python 版本匹配的官方 wheel。具体安装依赖、
量化数据集格式和模型支持列表以对应 submodule 的 README 和发布文档为准。
不要把这些 SDK 安装到 `common/qwen-common` 环境中。

## 模型资产边界

只读的 Hugging Face 或 ModelScope 快照位于：

```text
models/Qwen/<model>/original/
```

纯 RK3588 的转换结果位于：

```text
models/Qwen/<model>/rockchip-rk3588/<variant>/
|-- rknn/       视觉或普通网络的 .rknn 文件
|-- rkllm/      大语言模型的 .rkllm 文件
|-- runtime/    板端运行库和启动文件（如需要）
`-- manifest.json
```

`original/` 不得修改。`.rknn`、`.rkllm`、量化权重和部署包都属于纯
RK3588 的平台私有产物，不能放入 `rockchip-rk3588-rk1828/`，也不能将
RKNN3 生成的文件作为本目录的输入。

## 与 RK1828 路线的区别

| 路线 | 设备 | 转换工具 | 运行时/模型格式 |
| --- | --- | --- | --- |
| `rockchip-rk3588` | 仅 RK3588 内置 NPU | `rknn-toolkit2`、`rknn-llm` | RKNPU2 / RKLLM，`.rknn`、`.rkllm` |
| `rockchip-rk3588-rk1828` | RK3588 + RK1828 算力棒 | `rknn3-toolkit` | RKNPU3，RKNN3 产物 |

即使模型名称相同，也必须分别转换、分别验证，并在 manifest 中记录对应
工具链提交、目标平台、量化参数和校验和。
