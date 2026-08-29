# 三平台容器启动文档设计

## 目标

为 EdgeModelLab 的三个目标平台提供可独立迁移、从零执行的中文 README：

- Rockchip RK3588/RK1828；
- NVIDIA Jetson Orin NX 16GB；
- D-Robotics Horizon S100。

每份 README 的终点是进入对应容器并通过工具链自检。本文档不定义具体模型的量化、导出、引擎构建或板端推理命令。

## 已确认边界

宿主机允许执行以下操作：

- 安装并启动 Docker Engine；
- 为 GPU 容器安装 NVIDIA Container Toolkit；
- 创建目录和设置文件权限；
- 使用 Git 获取官方源码仓库；
- 使用 Hugging Face 或 ModelScope 获取模型；
- 拉取、构建、保存、加载和启动 Docker 镜像。

宿主机不得安装或运行平台 SDK、平台 Python 依赖、量化工具、导出工具、编译工具链或模型转换程序。这些操作只能出现在对应容器中。

不增加 Compose、启动脚本、统一平台 CLI 或其他包装层。用户直接执行 README 中的 Docker 命令并进入容器。

## 文档组织

采用三份自包含的平台 README。少量 Docker 基础内容允许重复，确保只迁移一个平台目录时仍能从零操作。

需要创建或重写：

- `platforms/rockchip-rk3588-rk1828/README.md`；
- `platforms/jetson-orin-nx-16/README.md`；
- `platforms/horizon-s100/README.md`。

根 `README.md` 只保留平台状态、公共目录约定和三份平台 README 的链接，不再重复完整启动教程。

## 统一章节结构

三份 README 使用相同的信息顺序：

1. 当前状态；
2. 适用范围与非目标；
3. 固定版本和上游来源；
4. 宿主机要求；
5. Docker 与 GPU runtime 安装和验证；
6. 本地目录及挂载契约；
7. 获取源码或构建输入；
8. 拉取或构建镜像；
9. 镜像自检；
10. 启动交互容器；
11. 容器内路径和工具链自检；
12. 退出、重新进入与持久化边界；
13. 离线迁移；
14. 常见问题和精确清理；
15. 官方资料与许可证。

命令使用 `EDGE_MODEL_LAB_ROOT` 表示仓库根目录，不依赖固定用户名。输入模型目录以只读方式挂载，平台输出和临时目录分别以可写方式挂载。不得把整个仓库或整个模型树作为单一可写卷挂入容器。

## Rockchip RK3588/RK1828

Rockchip 没有可直接使用的完整官方开发镜像，因此保留当前自建镜像：

```text
edge-model-lab/rknn3:1.0.4
```

README 需要记录：

- `rknn3-toolkit` V1.0.4，commit `cf292045d77c9ad0377b9fb326f216967475071e`；
- `rknn3-model-zoo` V1.0.4，commit `f63048265b49bd2c6236790087287bed6c6b76fe`；
- cp310 Toolkit wheel SHA-256 `de5ec24e155e77cb37fdfe654a2d1d93fbf68b54679b326e6e4eb0c4c1662415`；
- `config/upstream.yaml` 中的 runtime 文件校验值；
- Dockerfile 以平台目录为唯一构建上下文；
- Toolkit、Model Zoo、runtime 和 aarch64 交叉编译器均烘焙到镜像中，运行时不挂载 vendor 仓库。

README 必须明确：官方仓库可以在宿主机 clone，但 Toolkit 安装、量化、导出和交叉编译只能在容器中执行。GPU 量化路径使用 `--gpus all`；只验证 RKNN import 时不要求 GPU。

公开的 `rknn3-toolkit` 与 `rknn3-model-zoo` Git 仓库没有包含构建示例所需的 RKNN3 runtime 头文件和动态库。README 不提供猜测的下载地址，而是要求迁移者从与 V1.0.4 匹配的板卡 SDK、厂商交付包或 Rockchip FAE 获取以下受控输入：

```text
runtime/include/float16.h
runtime/include/rknn3_api.h
runtime/Linux/aarch64/librknn3_api.so
runtime/Linux/aarch64/librknn3_api_rkcp.so
runtime/Linux/aarch64/librknn3_api_native.so
```

这些文件必须通过 `config/upstream.yaml` 的 SHA-256 校验后才能构建镜像。缺少文件或哈希不匹配时，README 的流程在构建前明确停止；仅 clone 两个公开仓库不宣称能够得到完整构建上下文。迁移归档需要把这组受许可证约束的 runtime 输入与仓库分开保存和校验。

Rockchip 当前验证级别为“镜像环境已验证”：RKNN import、CUDA 可见性、Model Zoo、runtime 文件和 aarch64 交叉编译器已经通过自检。具体模型转换仍需单独验证。

## NVIDIA Jetson Orin NX 16GB

x86-64 导出和量化阶段使用 NVIDIA TensorRT Edge-LLM 官方推荐的基础镜像：

```text
nvcr.io/nvidia/pytorch:25.12-py3
```

README 需要记录 amd64 manifest digest：

```text
sha256:11e9976339d08669ede155cdbc601b1df5f57772fcee772b23527efc54e05602
```

官方 TensorRT Edge-LLM 源码固定到 release `v0.10.0`，而不是跟随 `main`。宿主机可以 clone 和初始化 submodule；容器内执行 Python 依赖安装和 CLI 自检。

启动命令包含：

- `--platform linux/amd64` 用于拉取或明确镜像架构；
- `--gpus all` 用于量化环境；
- `--shm-size`，或 NVIDIA 建议的 IPC 配置；
- `--ulimit memlock=-1`；
- `--ulimit stack=67108864`；
- 当前用户 UID/GID；
- 只读源码模型挂载、可写 Jetson 输出挂载、可写临时目录；
- TensorRT Edge-LLM checkout 挂载到固定容器路径。

README 必须明确：

- `25.12-py3` 是 x86 导出/量化基础环境，不是 Orin 运行镜像；
- 基础镜像不等于完整 TensorRT Edge-LLM 环境，源码依赖安装后才可进行 CLI 自检；
- 当前基础镜像和 Edge-LLM release 的 Python 依赖可能改变基础镜像中的 Torch 等组件，不能在未验证前称为固定生产组合；
- Orin 引擎必须使用目标 JetPack、CUDA、TensorRT 和插件组合在目标 Orin 上构建；
- Orin 当前只使用官方支持的 FP16、INT8 或 INT4 路径，不能声明 FP8、MXFP8、FP4 或 NVFP4 支持。

Jetson 当前验证级别为“官方基础镜像启动已验证”：amd64 NGC 镜像可以访问 RTX 5070，Python 与 PyTorch 可运行。TensorRT Edge-LLM 完整依赖、具体模型导出和 Orin 目标端构建不标记为已验证。

## Horizon S100

通用 OpenExplorer 开发环境固定为 3.7.0，并与板端系统软件 4.0.5 配套。官方镜像为：

```text
registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_cpu:v3.7.0
registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_gpu:v3.7.0
```

README 同时提供在线 pull 与官方离线 tar 的迁移方式。登录凭据通过交互方式输入，不把官方页面中的密码、个人 token 或环境变量值写入仓库和 shell 历史。

GPU 启动命令与官方 `run_docker.sh` 的有效参数保持一致：

- `--network host`；
- `--gpus all`；
- `--shm-size=15g`；
- OpenExplorer 工作目录挂载到 `/open_explorer`；
- 数据目录挂载到 `/data`。

CPU 镜像不使用 GPU 参数。README 说明官方脚本默认以 root 运行且使用可写挂载，可能产生 root 所有文件；退出前需要在容器内修正输出属主，或在确认镜像兼容后使用宿主 UID/GID。

必须区分两套产品：

- OpenExplorer 3.7.0 通用算法工具链提供官方 Docker 镜像；
- S100 LLM 工具链 1.0.0 的官方发布流程不是上述通用 OE Docker。

S100 LLM 1.0.0 官方支持列表不包含本仓库的 Qwen2.5-0.5B 或 Qwen3-4B。Qwen3-4B 的公开支持属于 S600 LLM 工具链，不能外推到 S100。因此 Horizon README 只能将“官方 OE 镜像启动和工具链自检”标记为可执行，不能提供或暗示这两个模型在 S100 上的量化、导出和部署命令。

## 离线迁移约定

每个平台 README 都需要包含：

1. 联网机器保存镜像；
2. 为镜像归档生成 SHA-256；
3. 单独打包平台源码、配置和必要构建输入；
4. 在离线机器验证归档哈希；
5. 使用 `docker load` 导入；
6. 检查导入后的 repository、tag、digest 和架构；
7. 创建模型输入、输出和临时目录后启动容器。

镜像归档不包含 bind mount 内容、模型、源码、容器内未提交的交互式安装结果或凭据。README 必须显式说明这些边界。

Horizon 官方离线 tar 的本地 tag 可能与 `run_docker.sh` 使用的 registry-qualified tag 不一致。文档需要在 `docker load` 后检查实际 tag，并按需补充本地 tag，再执行启动命令。

## 错误处理和清理

README 只给出精确对象的诊断与清理命令：

- `docker image inspect`、`docker ps -a`、`docker system df`；
- 停止和删除指定名称的容器；
- 删除指定 repository:tag 的镜像；
- 检查挂载目录属主和剩余磁盘空间。

文档不推荐 `docker system prune -a`、无过滤的 `docker builder prune` 或删除整个 Docker 数据目录。这些命令可能删除其他平台的有效镜像或构建缓存。

## 验证标准

README 实施完成后需要进行以下验证：

- 三份文件均为中文并具备统一章节；
- 所有 shell 代码块通过静态 shell 语法检查；
- 镜像名称、tag、commit 和 digest 与官方资料或本地锁定记录一致；
- Rockchip 镜像能够 import RKNN，并找到 Model Zoo、runtime 和交叉编译器；
- Jetson NGC 镜像能够访问 GPU，并输出 Python、PyTorch 和 CUDA 信息；
- Horizon 启动命令与官方 OE 3.7.0 `run_docker.sh` 参数一致；
- README 不包含凭据、token、占位镜像 tag 或未经验证的模型命令；
- 根 README 不再重复或冲突于平台文档；
- 当前模型、vendor 仓库、Docker 镜像和用户工作区不因文档修改而改变。

## 非目标

本次不执行以下工作：

- 不下载约 29GB 的 Horizon GPU 离线镜像；
- 不创建 Jetson 或 Horizon 派生 Dockerfile；
- 不运行模型量化或导出；
- 不构建 Orin TensorRT engine；
- 不声明 Horizon S100 支持当前 Qwen 模型；
- 不增加启动脚本、Compose、平台 CLI、自动清理器或注册表服务；
- 不重构或提交当前工作区中与平台 README 无关的改动。

## 官方资料

- NVIDIA TensorRT Edge-LLM 安装说明：`https://github.com/NVIDIA/TensorRT-Edge-LLM/blob/main/docs/source/user_guide/getting_started/installation.md`
- NVIDIA NGC 使用说明：`https://docs.nvidia.com/ngc/latest/ngc-catalog-user-guide.html`
- NVIDIA PyTorch 25.12 发布说明：`https://docs.nvidia.com/deeplearning/frameworks/pytorch-release-notes/rel-25-12.html`
- D-Robotics 环境部署：`https://toolchain.d-robotics.cc/guide/env_install.html`
- D-Robotics OE 3.7.0：`https://developer.d-robotics.cc/rdk_s_doc/en/Advanced_development/toolchain_development/algorithm_toolchain/overview`
- D-Robotics S100 LLM 工具链：`https://developer.d-robotics.cc/rdk_s_doc/Advanced_development/toolchain_development/LLM_Toolchain/s100_LLM_Toolchain`
