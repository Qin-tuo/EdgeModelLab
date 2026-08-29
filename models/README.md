# 模型资产目录

本目录是 EdgeModelLab 的模型资产根目录。模型权重和生成文件体积较大，
默认不上传到 Git；Git 只保留本说明文件和目录约定。

## 目录约定

```text
models/Qwen/<model>/
|-- original/                         上游模型完整快照，只读
|-- rockchip-rk3588/<variant>/        RKNN / RKLLM 专用模型和部署包（纯 NPU）
|-- rockchip-rk3588-rk1828/<variant>/ RKNN3 专用 ONNX、RKNN 和部署包
|-- jetson-orin-nx-16/<variant>/      Edge-LLM 专用 ONNX、engine 和 manifest
`-- horizon-s100/<variant>/            S100 专用产物
```

只有 `original/` 在不同平台之间共享。所有 ONNX 都是平台私有文件，必须
放在生成它的工具链和平台变体下。不同工具链的 ONNX 不能仅凭文件后缀
直接互换；TensorRT engine 还绑定目标 GPU、JetPack、TensorRT、插件和
构建参数。

纯 RK3588 的普通网络或视觉子图使用 `rknn-toolkit2`，大语言模型使用
`rknn-llm` 并生成 `.rkllm`。RK3588 + RK1828 算力棒使用独立的
`rknn3-toolkit` 并生成 RKNN3 产物；两条路线的模型和运行时不能混用。

## 纯 RK3588 转换入口

先在仓库根目录获取纯 RK3588 的官方工具链：

```sh
git submodule update --init --recursive \
  platforms/rockchip-rk3588/vendor/rknn-toolkit2 \
  platforms/rockchip-rk3588/vendor/rknn-llm
```

以 `models/Qwen/<model>/original/` 为只读输入，在与 Python 版本匹配的官方
环境中完成转换。普通网络或多模态视觉子图使用 `rknn-toolkit2`，输出
`.rknn`；Qwen 等大语言模型使用 `rknn-llm`，量化并输出 `.rkllm`。结果只
能写入 `models/Qwen/<model>/rockchip-rk3588/<variant>/`，并在
`manifest.json` 中记录工具链版本、目标 `rk3588`、量化参数和校验和。

具体模型的量化数据集和导出参数以
[`platforms/rockchip-rk3588/README.md`](../platforms/rockchip-rk3588/README.md)
及对应官方 submodule 文档为准。

## 本地下载

推荐使用仓库根目录的通用环境：

```sh
conda env create -f common/environment.yml
conda activate qwen-common
```

使用 Hugging Face：

```sh
MODEL=Qwen3.5-4B
mkdir -p "models/Qwen/$MODEL/original"

hf download Qwen/Qwen3.5-4B \
  --local-dir "models/Qwen/$MODEL/original"
```

使用 ModelScope：

```sh
python -m pip install -U modelscope

MODEL=Qwen3.5-4B
mkdir -p "models/Qwen/$MODEL/original"
modelscope download \
  --model Qwen/Qwen3.5-4B \
  --local_dir "models/Qwen/$MODEL/original"
```

## 本地算力不足时使用 AutoDL

如果本机 GPU 显存不足，可以在 AutoDL 上完成模型量化和 ONNX 导出，再把
Jetson 平台变体传回本机。建议选择 NVIDIA GPU，显存至少 16GB，推荐 24GB
或更高，并准备至少 50GB 可用磁盘。Qwen3.5-4B 原始权重约 9.3GB，量化
时需要额外显存和临时空间。

AutoDL 普通容器实例不能在内部继续运行 Docker，因此不要尝试在 AutoDL
里启动本机的 NGC Docker 镜像。选择 AutoDL 提供的 PyTorch/CUDA 镜像，
在实例环境中安装 Python 依赖即可。NVIDIA 容器只作为本机或支持 Docker
的主机环境使用。

### 1. 在 AutoDL 下载原始模型

登录 AutoDL 实例后执行：

```sh
mkdir -p /root/autodl-tmp/EdgeModelLab/models/Qwen/Qwen3.5-4B/original
python3 -m pip install -U modelscope
modelscope download \
  --model Qwen/Qwen3.5-4B \
  --local_dir /root/autodl-tmp/EdgeModelLab/models/Qwen/Qwen3.5-4B/original
```

直接在 AutoDL 下载通常比从本机上传大模型更快。也可以使用 Hugging Face
CLI，但要先确认实例到 Hugging Face 的网络可达。


tmux new -s edgellm

tmux ls

tmux attach -t edgellm
### 2. 在 AutoDL 获取 Edge-LLM submodule

如果 AutoDL 上已经克隆了 EdgeModelLab 主仓库，执行：

```sh
cd /root/autodl-tmp/EdgeModelLab
git submodule update --init --recursive \
  platforms/jetson-orin-nx-16/vendor/TensorRT-Edge-LLM
cd platforms/jetson-orin-nx-16/vendor/TensorRT-Edge-LLM
```

也可以在主仓库之外单独获取同一个上游 checkout，但正式的 EdgeModelLab
目录应使用主仓库记录的 submodule 指针，以保证版本一致。

创建独立环境并安装平台工具：

```sh
python3 -m venv /root/autodl-tmp/edgellm-venv
source /root/autodl-tmp/edgellm-venv/bin/activate
python -m pip install -U pip
python -m pip install --no-deps -e .
python -m pip install \
  transformers onnx onnxscript onnx-graphsurgeon \
  safetensors nvidia-modelopt datasets tqdm einops peft
```

不同 Edge-LLM 版本的依赖可能不同，实际使用时以对应 checkout 的
`pyproject.toml` 和安装文档为准，不要替换 AutoDL 镜像中已可用的 CUDA
运行时组件。

### 3. 量化并导出 Jetson ONNX

量化输出和 ONNX 必须写到 Jetson 平台变体目录：

```sh
export SRC=/root/autodl-tmp/EdgeModelLab/models/Qwen/Qwen3.5-4B/original
export VARIANT=/root/autodl-tmp/EdgeModelLab/models/Qwen/Qwen3.5-4B/jetson-orin-nx-16/tensorrt-edgellm-v0.10.0-int4-awq

mkdir -p "$VARIANT/quantized" "$VARIANT/onnx"

tensorrt-edgellm-quantize llm \
  --model_dir "$SRC" \
  --output_dir "$VARIANT/quantized" \
  --quantization int4_awq

tensorrt-edgellm-export \
  "$VARIANT/quantized" \
  "$VARIANT/onnx" \
  --externalize-weights int4_ffn
```

上面的命令是流程示例。执行前必须确认当前 Edge-LLM 版本、模型类型和
目标 Jetson 的精度支持；不要在未经验证的情况下把结果标记为正式产物。

### 4. 回传平台变体

只回传 Jetson 平台变体，不要再次回传 `original/`：

```sh
rsync -avP --partial \
  -e "ssh -p <AutoDL端口>" \
  root@<AutoDL主机>:/root/autodl-tmp/EdgeModelLab/models/Qwen/Qwen3.5-4B/jetson-orin-nx-16/tensorrt-edgellm-v0.10.0-int4-awq/ \
  models/Qwen/Qwen3.5-4B/jetson-orin-nx-16/tensorrt-edgellm-v0.10.0-int4-awq/
```

`rsync -P` 中断后可以重复执行。AutoDL 的 SSH、SCP 和实例生命周期
说明见官方文档：

- [快速开始](https://www.autodl.com/docs/quick_start/)
- [SSH 远程连接](https://www.autodl.com/docs/ssh/)
- [文件上传](https://www.autodl.com/docs/scp/)

## 重要边界

AutoDL 或 x86 主机可以负责量化和 ONNX 导出，但最终 TensorRT engine 必须
在实际运行模型的 Jetson Orin NX 上构建。engine 生成后再放入同一个
`jetson-orin-nx-16/<variant>/engine/` 目录，并在 manifest 中记录完整的
版本和校验信息。
