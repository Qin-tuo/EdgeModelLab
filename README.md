# EdgeModelLab

EdgeModelLab 是边缘平台的模型资产与生产环境工作区。每个上游模型只保存一份；Rockchip、NVIDIA Jetson 和 Horizon 分别管理自己的量化、导出、编译流程及产物目录。

根 README 只定义公共契约并提供平台索引。镜像准备、容器启动、环境自检和平台工具链说明见对应平台 README。

## 平台状态

| 平台 | 当前状态 |
| --- | --- |
| [Rockchip RK3588/RK1828](platforms/rockchip-rk3588-rk1828/README.md) | RKNN3 1.0.4 镜像环境已验证；具体模型链路单独验证。 |
| [NVIDIA Jetson Orin NX 16GB](platforms/jetson-orin-nx-16/README.md) | x86 NGC 基础镜像已验证；Edge-LLM 和 Orin engine 尚未验证。 |
| [Horizon S100](platforms/horizon-s100/README.md) | OE 3.7.0 官方环境可启动；当前 Qwen 模型没有官方 S100 支持声明。 |

## 目录与资产契约

```text
models/Qwen/<model>/
|-- original/
|-- rockchip-rk3588-rk1828/<variant>/
|-- jetson-orin-nx-16/<variant>/
`-- horizon-s100/<variant>/
```

- `models/Qwen/<model>/original/` 是唯一共享且不可修改的上游输入。
- `rockchip-rk3588-rk1828/<variant>/`、`jetson-orin-nx-16/<variant>/` 和 `horizon-s100/<variant>/` 是对应平台独立拥有的产物目录；量化、导出和编译结果只能写入本平台目录。
- ONNX 和 engine 均属于生成它们的平台及工具链，不跨平台复用。
- 模型、vendor、runtime、Docker 层和 `tmp` 不提交 Git。

## 操作边界

宿主机可以安装 Docker、创建目录、下载模型和 clone 官方源码。平台 SDK、平台 Python 依赖、量化、导出和编译只能在对应容器内执行，不能安装或运行在宿主机公共环境中。

宿主机下载模型时，先创建唯一的 `original/` 目录，再使用官方工具写入该目录。例如：

```sh
export EDGE_MODEL_LAB_ROOT=/path/to/EdgeModelLab
mkdir -p "$EDGE_MODEL_LAB_ROOT/models/Qwen/Qwen3-4B/original"
cd "$EDGE_MODEL_LAB_ROOT/models/Qwen/Qwen3-4B/original"
hf download Qwen/Qwen3-4B --local-dir .
```

也可以在同一目录使用 ModelScope 官方下载工具：

```sh
modelscope download Qwen/Qwen3-4B --local_dir .
```

按实际模型替换仓库标识和目录名。下载完成后保持 `original/` 只读语义，所有平台产物写入各自的 `<variant>/`。

## 清理原则

清理资源前必须确认具体容器、镜像、构建目录或临时目录，并只删除确认不再需要的对象。禁止使用全局 Docker 清理方式，以免删除其他平台仍在使用的镜像、构建缓存或容器；具体清理步骤见对应平台 README。
