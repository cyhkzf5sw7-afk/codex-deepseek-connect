#!/usr/bin/env python3
"""Set up and launch a separate Codex home for DeepSeek, without changing ~/.codex."""
from __future__ import annotations
import argparse
import getpass
import glob
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import warnings
import i18n
from i18n import tr

PROFILE = '''# Separate DeepSeek profile. This file contains no API key.
model = "deepseek-flash"
model_provider = "deepseek"
model_reasoning_effort = "high"
web_search = "disabled"

[model_providers.deepseek]
name = "DeepSeek"
base_url = "https://api.deepseek.com/"
wire_api = "responses"
env_key = "DEEPSEEK_API_KEY"
requires_openai_auth = false
'''
MODELS = {"flash": "deepseek-flash", "pro": "deepseek-v4-pro"}
KEYCHAIN_SERVICE = "org.codex-deepseek-connect.api-key.v1"
KEYCHAIN_ACCOUNT = "default"
CODEX_MAC_CODEX = "/Applications/Codex.app/Contents/Resources/codex"
CHATGPT_MAC_CODEX = "/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex"


def safe_text(value: str, stream) -> str:
    """Render text without failing on a redirected, legacy-encoded stream."""
    encoding = getattr(stream, "encoding", None) or "utf-8"
    try:
        return value.encode(encoding, errors="backslashreplace").decode(encoding)
    except LookupError:
        return value.encode("ascii", errors="backslashreplace").decode("ascii")


def safe_print(value: str, *, file=None, flush=False) -> None:
    stream = sys.stdout if file is None else file
    print(safe_text(value, stream), file=stream, flush=flush)


def init_home(path: Path) -> None:
    # The directory itself is the installation marker: never merge, overwrite, or
    # follow an existing installation, even if it is a symlink or empty.
    path.mkdir(mode=0o700, parents=False, exist_ok=False)
    try:
        profile = path / "deepseek.config.toml"
        fd = os.open(profile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(PROFILE)
    except BaseException:
        # Only remove the newly created directory if it is empty; retain any
        # partly written file for manual inspection rather than deleting data.
        try:
            path.rmdir()
        except OSError:
            pass
        raise


def build_command(codex: str, model: str, args: list[str], reasoning: str | None = None) -> list[str]:
    catalog = Path(__file__).resolve().with_name("models.json")
    command = [codex, "--profile", "deepseek", "--model", MODELS[model]]
    overrides = ["-c", "model_catalog_json=" + json.dumps(str(catalog), ensure_ascii=False)]
    if reasoning:
        overrides += ["-c", f'model_reasoning_effort="{reasoning}"']
    # Codex's exec/review subcommands have their own -c list; if any -c is
    # supplied there, it replaces the top-level list. Keep our overrides in
    # that same list so caller-supplied subcommand flags cannot discard them.
    if args and args[0] in ("exec", "e", "review"):
        return [*command, args[0], *overrides, *args[1:]]
    return [*command, *overrides, *args]


def save_keychain() -> int:
    if sys.platform != "darwin":
        raise ValueError(tr("钥匙串功能仅支持 macOS；其他系统请使用交互式输入。"))
    import maccred
    key = prompt_key()
    maccred.save_key(key)
    safe_print(tr("已保存到 macOS 钥匙串。"))
    return 0


def prompt_key() -> str:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            key = getpass.getpass(safe_text(tr("输入 DeepSeek API Key（不会显示）："), sys.stderr))
    except (EOFError, KeyboardInterrupt, getpass.GetPassWarning) as exc:
        raise ValueError(tr("输入已取消，或无法隐藏输入。")) from exc
    if not key or key != key.strip() or "\n" in key or "\r" in key:
        raise ValueError(tr("API Key 不能为空，也不能包含首尾空格或换行。"))
    return key


def save_credential() -> int:
    if sys.platform == "darwin":
        return save_keychain()
    if sys.platform == "win32":
        import wincred
        key = prompt_key()
        wincred.save_key(key)
        safe_print(tr("已保存到 Windows 凭据管理器。"))
        return 0
    raise ValueError(tr("持久凭据功能支持 Windows 和 macOS；其他系统请使用交互式输入。"))


def read_credential() -> str:
    if sys.platform == "darwin":
        return read_keychain()
    if sys.platform == "win32":
        import wincred
        return wincred.read_key()
    raise ValueError(tr("持久凭据功能支持 Windows 和 macOS。"))


def read_keychain() -> str:
    if sys.platform != "darwin":
        raise ValueError(tr("钥匙串功能仅支持 macOS；其他系统请使用交互式输入。"))
    import maccred
    return maccred.read_key()


def find_codex() -> str | None:
    executable = shutil.which("codex.exe" if sys.platform == "win32" else "codex")
    if executable and (sys.platform != "win32" or executable.lower().endswith(".exe")):
        return executable
    if sys.platform == "darwin":
        for candidate in (CHATGPT_MAC_CODEX, CODEX_MAC_CODEX):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        local = os.environ["LOCALAPPDATA"]
        candidates = [os.path.join(local, "Programs", "OpenAI", "Codex", "bin", "codex.exe")]
        candidates += sorted(glob.glob(os.path.join(local, "OpenAI", "Codex", "bin", "*", "codex.exe")), reverse=True)
        for candidate in candidates:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
    return None


def run(home: Path, model: str, args: list[str], codex: str | None = None,
        use_keychain: bool = False, reasoning: str | None = None) -> int:
    profile = home / "deepseek.config.toml"
    if home.is_symlink() or not home.is_dir() or profile.is_symlink() or not profile.is_file():
        raise ValueError(tr("独立配置不存在或不是普通文件；请先运行 init。"))
    codex = codex or find_codex()
    if not codex:
        if sys.platform == "win32":
            if shutil.which("codex.cmd"):
                raise ValueError(tr("只找到 codex.cmd；为安全起见需要 codex.exe。请安装官方独立 CLI：https://developers.openai.com/codex/cli/"))
            raise ValueError(tr("找不到 codex.exe。请安装官方独立 CLI：https://developers.openai.com/codex/cli/"))
        raise ValueError(tr("找不到 codex 命令。请先安装并启动 Codex CLI。"))
    if sys.platform == "win32" and not codex.lower().endswith(".exe"):
        raise ValueError(tr("Windows 仅支持运行 codex.exe；请安装官方独立 CLI：https://developers.openai.com/codex/cli/"))
    if use_keychain:
        key = read_credential()
    else:
        key = prompt_key()
    if not key or key != key.strip() or "\n" in key or "\r" in key:
        raise ValueError(tr("API Key 不能为空，也不能包含首尾空格或换行。"))
    env = os.environ.copy()
    env["CODEX_HOME"] = str(home.resolve())
    env["DEEPSEEK_API_KEY"] = key
    try:
        return subprocess.call(build_command(codex, model, args, reasoning), env=env)
    finally:
        env.pop("DEEPSEEK_API_KEY", None)


def main() -> int:
    # argparse prints directly to stdout/stderr, before our own safe_print calls.
    # Preserve the chosen encoding while escaping characters it cannot encode.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, OSError, ValueError):
            pass
    bootstrap = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    bootstrap.add_argument("--lang", choices=("en", "zh"))
    selected, _ = bootstrap.parse_known_args()
    i18n.set_language(selected.lang or i18n.package_language())
    parser = argparse.ArgumentParser(description=tr("使用独立 Codex 配置连接 DeepSeek。"))
    parser.add_argument("--lang", choices=("en", "zh"), default=i18n.package_language(), help=tr("界面语言（默认由 LANGUAGE 文件指定，否则为 zh）"))
    parser.add_argument("--home", type=Path, default=Path.home() / ".codex-deepseek", help=tr("独立配置目录（默认 ~/.codex-deepseek）"))
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("init", help=tr("创建独立配置；已有目录绝不覆盖"))
    sub.add_parser("keychain-save", help=tr("macOS：将 Key 存入钥匙串（不会覆盖已有项目）"))
    sub.add_parser("credential-save", help=tr("Windows 或 macOS：保存 Key 至系统凭据管理器"))
    launch = sub.add_parser("run", help=tr("隐藏输入 Key 并启动 Codex"))
    launch.add_argument("--model", choices=MODELS, default="flash", help=tr("选择 flash 或 pro（默认 flash）"))
    launch.add_argument("--reasoning", choices=("high", "max"), help=tr("选择推理档位 high 或 max（默认 high）"))
    launch.add_argument("--credential", "--keychain", dest="keychain", action="store_true", help=tr("从 Windows 凭据管理器或 macOS 钥匙串获取 Key"))
    launch.add_argument("codex_args", nargs=argparse.REMAINDER, help=tr("-- 之后的参数原样传给 codex"))
    opts = parser.parse_args()
    home = opts.home.expanduser().absolute()
    try:
        if opts.action == "init":
            init_home(home)
            safe_print(tr("已创建独立配置：{home}", home=home))
            safe_print(tr("运行：py -3 setup.py run") if sys.platform == "win32" else tr("运行：python3 setup.py run"))
            return 0
        if opts.action == "keychain-save":
            return save_keychain()
        if opts.action == "credential-save":
            return save_credential()
        args = opts.codex_args
        if args and args[0] == "--":
            args = args[1:]
        return run(home, opts.model, args, use_keychain=opts.keychain, reasoning=opts.reasoning)
    except FileExistsError:
        safe_print(tr("目录已存在，未作修改：{home}", home=home), file=sys.stderr)
    except (OSError, ValueError) as exc:
        safe_print(tr("操作失败：{error}", error=exc), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
