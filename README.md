# EdgeModelLab

EdgeModelLab is the host workspace for the two Qwen models currently used by
the edge projects on this machine:

- Qwen2.5-0.5B-Instruct
- Qwen3-4B

Model files live under `models/Qwen`. Common download and ONNX entry points
live under `common` and `edge_model_lab.common`. Verified vendor-specific host
tasks live under `platforms` and `edge_model_lab.rockchip`. Application
projects consume the resulting deployment bundles and do not produce them.

Large models, generated artifacts, vendor repositories, local environments,
and temporary files are intentionally excluded from Git.

