# 纯 RK3588 平台

本目录面向只使用 RK3588 芯片内置 NPU 的设备，不使用 RK1828 算力棒。
它与 `platforms/rockchip-rk3588-rk1828` 是两条独立的生产路线，不能共享
转换工具、运行时或生成模型。

## 官方工具链

工具链以 Git submodule 的形式放在 `vendor/` 下，并固定到可复现的发布版本：

| 组件 | 版本 | 用途 | 主要产物 |
| --- | --- | --- | --- |
| `rknn-toolkit2` | `v2.3.2` | 普通神经网络和多模态视觉子图转换 | `.rknn` |
| `rknn-model-zoo` | `v2.3.2` | 官方模型转换、推理示例和性能参考 | 示例代码 |
| `rknn-llm` | `release-v1.3.0` | Qwen 等大语言模型量化与转换 | `.rkllm` |

`rknn-toolkit2` 的板端 Lite API 和 RKNPU2 runtime 用于加载 `.rknn`；
`rknn-llm` 自带的 RKLLM runtime 用于加载 `.rkllm`。两者都针对 RK3588
的内置 NPU，不包含 RK1828 算力棒的 RKNN3 runtime。

`rknn-model-zoo` 对应官方仓库 `https://github.com/airockchip/rknn_model_zoo`。

首次克隆仓库后初始化这三个依赖：

```sh
git submodule update --init --recursive \
  platforms/rockchip-rk3588/vendor/rknn-toolkit2 \
  platforms/rockchip-rk3588/vendor/rknn-model-zoo \
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

## ARM64 Linux 交叉编译

目标板系统为 Ubuntu 22.04。当前用户级工具链位于
`~/.local/toolchains/aarch64-linux-gnu-ubuntu22.04/`，使用 Ubuntu 22.04
官方软件包中的 GCC/G++ 11.4、ARM64 glibc 2.35、Linux 5.15 头文件和
C++ 开发库；宿主端 binutils 沿用 2.42。编译命令已链接到 `~/.local/bin/`，
默认 `gcc`/`g++` 入口自动传入该工具链的 sysroot，避免链接宿主的 24.04 库。
原始软件包及版本清单保留在 `packages/` 下，无需激活 Conda 环境。
旧的 24.04 工具链仍保留在 `~/.local/toolchains/aarch64-linux-gnu/`，不再作为默认。

从仓库根目录构建 RKNN Model Zoo 的 YOLOv5 C++ 示例：

```sh
export PATH="$HOME/.local/bin:$PATH"
aarch64-linux-gnu-gcc -dumpmachine  # 应输出 aarch64-linux-gnu
aarch64-linux-gnu-gcc -print-sysroot  # 应指向 ubuntu22.04 工具链目录
cmake -S platforms/rockchip-rk3588/vendor/rknn-model-zoo/examples/yolov5/cpp \
  -B build/rockchip-rk3588/yolov5-ubuntu22.04-aarch64 \
  -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_SYSROOT="$HOME/.local/toolchains/aarch64-linux-gnu-ubuntu22.04" \
  -DCMAKE_C_COMPILER=aarch64-linux-gnu-gcc \
  -DCMAKE_CXX_COMPILER=aarch64-linux-gnu-g++ \
  -DTARGET_SOC=rk3588 -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PWD/build/rockchip-rk3588/yolov5-ubuntu22.04-install"
cmake --build build/rockchip-rk3588/yolov5-ubuntu22.04-aarch64 -j4
cmake --install build/rockchip-rk3588/yolov5-ubuntu22.04-aarch64
```

已验证 C、C++/pthread 编译链接，以及该示例生成 AArch64 ELF；尚未验证
板端推理。安装目录包含程序和 RKNN/RGA 库，不包含转换后的 `.rknn` 模型。
上述构建使用独立的 22.04 构建目录，不复用旧版 CMake 缓存或产物。
部署前仍需核对板端 NPU 驱动与 RKNN runtime 的兼容性。不可将交叉编译
成功视为已完成板端验证。

Toolkit 自带的 `rknpu2/examples/rknn_yolov5_demo/build-linux.sh` 还要求
显式设置 `GCC_COMPILER`，不能只设置 PATH。该变量是路径前缀，不带 `-gcc`：

```sh
cd platforms/rockchip-rk3588/vendor/rknn-toolkit2/rknpu2/examples/rknn_yolov5_demo
export GCC_COMPILER="$HOME/.local/bin/aarch64-linux-gnu"
./build-linux.sh -t rk3588 -a aarch64  # 默认 Release
```

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
