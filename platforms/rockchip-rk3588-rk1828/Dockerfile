FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        android-tools-adb \
        build-essential \
        cmake \
        gcc \
        gcc-aarch64-linux-gnu \
        g++-aarch64-linux-gnu \
        libgl1 \
        libglib2.0-0 \
        libprotobuf-dev \
        libsm6 \
        python3.10 \
        python3.10-dev \
        python3-pip \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY vendor/rknn3-toolkit/rknn3-toolkit/packages/rknn3_toolkit-1.0.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl /tmp/rknn3_toolkit-1.0.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
COPY vendor/rknn3-model-zoo /opt/rknn3-model-zoo
COPY runtime /opt/rknn3-runtime

ARG PIP_INDEX_URL=https://pypi.org/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}

RUN python3.10 -m pip install --no-cache-dir --upgrade pip \
    && python3.10 -m pip install --no-cache-dir /tmp/rknn3_toolkit-1.0.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl \
    && rm /tmp/rknn3_toolkit-1.0.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl \
    && mkdir -p /opt/rknn3-model-zoo/3rdparty/rknpu3 \
    && cp -a /opt/rknn3-runtime/include /opt/rknn3-model-zoo/3rdparty/rknpu3/ \
    && cp -a /opt/rknn3-runtime/Linux /opt/rknn3-model-zoo/3rdparty/rknpu3/

ENV PYTHONPATH=/opt/rknn3-model-zoo \
    GCC_COMPILER=aarch64-linux-gnu \
    RKNN3_MODEL_ZOO=/opt/rknn3-model-zoo \
    RKNN3_RUNTIME=/opt/rknn3-runtime

WORKDIR /workspace
CMD ["/bin/bash"]
