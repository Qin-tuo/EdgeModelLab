from pathlib import Path


def workspace_root(root: Path | None = None) -> Path:
    if root is not None:
        return root.expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def model_root(model_name: str, root: Path | None = None) -> Path:
    return (workspace_root(root) / "models" / "Qwen" / model_name).resolve()
