"""Build four shareable packages from an explicit, credential-free file list."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
FILES = (
    "setup.py", "wincred.py", "maccred.py", "i18n.py", "models.json", "test_setup.py", "test_cli_smoke.py",
    "README.md", "README.zh-CN.md", "build_packages.py", ".gitignore",
    ".github/workflows/windows-tests.yml",
    "docs/windows.en.md", "docs/windows.zh-CN.md",
    "docs/macos.en.md", "docs/macos.zh-CN.md",
    "docs/VALIDATION.md",
)
VARIANTS = (("Windows", "windows", "zh-CN", "zh"),
            ("Windows", "windows", "en", "en"),
            ("macOS", "macos", "zh-CN", "zh"),
            ("macOS", "macos", "en", "en"))


def build(output: Path) -> None:
    output = output.absolute()
    # Refuse accidental replacement of an existing delivery directory.
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Output already exists: {output}")
    for name in FILES:
        source = ROOT / name
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"Missing or unsafe source file: {name}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".deepseek-packages-", dir=output.parent) as temp:
        staging = Path(temp) / "packages"
        staging.mkdir()
        checksums = []
        for platform, slug, label, language in VARIANTS:
            name = f"Codex-DeepSeek-{platform}-{label}"
            package = staging / name
            package.mkdir()
            for filename in FILES:
                target = package / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / filename, target)
            (package / "LANGUAGE").write_text(language + "\n", encoding="utf-8")
            command = "py -3" if platform == "Windows" else "python3"
            guide = f"docs/{slug}.{label}.md"
            if language == "zh":
                start = (f"Codex 连接 DeepSeek · {platform} 中文版\n\n"
                         f"先阅读 {guide}，按说明安装 Python 和 Codex CLI。\n"
                         "请先完整解压，再在这个文件夹中打开终端。\n\n"
                         f"1. {command} setup.py init\n"
                         f"2. {command} setup.py run\n\n"
                         "Key 只在自己的终端中隐藏输入，不要发给别人。\n"
                         "可选：使用 --model pro 切换 V4 Pro，--reasoning max 选择 max。\n"
                         "完整连接测试、系统凭据保存及桌面按需调用见使用指南。\n"
                         "本工具的语言设为中文；Codex 本身的界面由 Codex 决定。\n")
            else:
                start = (f"Codex DeepSeek Connect · {platform} English edition\n\n"
                         f"Read {guide} first and install Python and Codex CLI.\n"
                         "Extract the entire ZIP, then open a terminal in this folder.\n\n"
                         f"1. {command} setup.py init\n"
                         f"2. {command} setup.py run\n\n"
                         "Enter your key only in your own terminal; input is hidden. Never share it.\n"
                         "Use --model pro for V4 Pro or --reasoning max for max effort.\n"
                         "See the guide for connection tests, credential storage, and desktop usage.\n"
                         "This tool uses English; Codex controls its own interface language.\n")
            (package / "START_HERE.txt").write_text(start, encoding="utf-8-sig")
            archive = staging / (name + ".zip")
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                for path in sorted(package.rglob("*")):
                    if path.is_file():
                        info = zipfile.ZipInfo(path.relative_to(staging).as_posix(), (2026, 1, 1, 0, 0, 0))
                        info.compress_type = zipfile.ZIP_DEFLATED
                        info.create_system = 3
                        info.external_attr = 0o100644 << 16
                        bundle.writestr(info, path.read_bytes())
            with zipfile.ZipFile(archive) as bundle:
                if bundle.testzip() is not None:
                    raise ValueError(f"Invalid archive: {archive.name}")
            checksums.append(hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name)
        (staging / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="ascii")
        staging.rename(output)
    print(f"Created four packages in {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    build(parser.parse_args().output)
