from __future__ import annotations

import re
from pathlib import Path

BLOCK_START = "# >>> code-buddy initialize >>>"
BLOCK_END = "# <<< code-buddy initialize <<<"


def install_path_block(zprofile_path: Path, shim_dir: Path) -> None:
    zprofile_path.parent.mkdir(parents=True, exist_ok=True)
    current = zprofile_path.read_text(encoding="utf-8") if zprofile_path.exists() else ""
    cleaned = _remove_block(current).rstrip("\n")
    block = _render_block(shim_dir)
    next_text = block if not cleaned else f"{cleaned}\n{block}"
    zprofile_path.write_text(next_text, encoding="utf-8")


def remove_path_block(zprofile_path: Path) -> None:
    if not zprofile_path.exists():
        return
    cleaned = _remove_block(zprofile_path.read_text(encoding="utf-8"))
    zprofile_path.write_text(cleaned, encoding="utf-8")


def has_path_block(zprofile_path: Path) -> bool:
    if not zprofile_path.exists():
        return False
    text = zprofile_path.read_text(encoding="utf-8")
    return BLOCK_START in text and BLOCK_END in text


def _render_block(shim_dir: Path) -> str:
    export_path = str(shim_dir)
    if shim_dir.name == "bin" and shim_dir.parent.name == ".code-buddy":
        export_path = "$HOME/.code-buddy/bin"
    return f'{BLOCK_START}\nexport PATH="{export_path}:$PATH"\n{BLOCK_END}\n'


def _remove_block(text: str) -> str:
    pattern = rf"\n?{re.escape(BLOCK_START)}.*?{re.escape(BLOCK_END)}\n?"
    cleaned = re.sub(pattern, "\n", text, flags=re.DOTALL)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned
