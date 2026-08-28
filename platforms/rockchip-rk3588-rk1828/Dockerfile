FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        android-tools-adb \
        gcc \
        libgl1 \
        libglib2.0-0 \
        libprotobuf-dev \
        libsm6 \
        python3.10 \
        python3.10-dev \
        python3-pip \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY platforms/rockchip-rk3588-rk1828/vendor/rknn3-toolkit/rknn3-toolkit/packages/rknn3_toolkit-1.0.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl /tmp/rknn3_toolkit-1.0.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

RUN python3.10 -m pip install --no-cache-dir --upgrade pip \
    && python3.10 -m pip install --no-cache-dir /tmp/rknn3_toolkit-1.0.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl \
    && rm /tmp/rknn3_toolkit-1.0.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

WORKDIR /workspace
