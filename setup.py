#!/usr/bin/env python3
"""Set up and launch a separate Codex home for DeepSeek, without changing ~/.codex."""
from __future__ import annotations
import argparse
import getpass
import glob
import os
from pathlib import Path
import shutil
import subprocess
import sys
import warnings

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
CHATGPT_MAC_CODEX = "/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex"


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


def build_command(codex: str, model: str, args: list[str]) -> list[str]:
    # Global options precede the optional subcommand and all user arguments.
    return [codex, "--profile", "deepseek", "--model", MODELS[model], *args]


def macos_security() -> str:
    if sys.platform != "darwin":
        raise ValueError("钥匙串功能仅支持 macOS；其他系统请使用交互式输入。")
    executable = "/usr/bin/security"
    if not os.path.isfile(executable) or not os.access(executable, os.X_OK):
        raise ValueError("找不到可执行的 macOS 系统命令 /usr/bin/security。")
    return executable


def save_keychain() -> int:
    security = macos_security()
    # '-w' with no value tells security itself to read the password from the
    # terminal without echo. No secret appears in argv or a Python file.
    # Omitting '-U' ensures that an existing item is never updated.
    print("请在系统提示时输入 DeepSeek API Key；已存在的同名钥匙串项目不会覆盖。", flush=True)
    return subprocess.call([security, "add-generic-password", "-s", KEYCHAIN_SERVICE,
                            "-a", KEYCHAIN_ACCOUNT, "-w"])


def prompt_key() -> str:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            key = getpass.getpass("输入 DeepSeek API Key（不会显示）：")
    except (EOFError, KeyboardInterrupt, getpass.GetPassWarning) as exc:
        raise ValueError("输入已取消，或无法隐藏输入。") from exc
    if not key or key != key.strip() or "\n" in key or "\r" in key:
        raise ValueError("API Key 不能为空，也不能包含首尾空格或换行。")
    return key


def save_credential() -> int:
    if sys.platform == "darwin":
        return save_keychain()
    if sys.platform == "win32":
        import wincred
        key = prompt_key()
        wincred.save_key(key)
        print("已保存到 Windows 凭据管理器。")
        return 0
    raise ValueError("持久凭据功能支持 Windows 和 macOS；其他系统请使用交互式输入。")


def read_credential() -> str:
    if sys.platform == "darwin":
        return read_keychain()
    if sys.platform == "win32":
        import wincred
        return wincred.read_key()
    raise ValueError("持久凭据功能支持 Windows 和 macOS。")


def read_keychain() -> str:
    security = macos_security()
    result = subprocess.run([security, "find-generic-password", "-s", KEYCHAIN_SERVICE,
                             "-a", KEYCHAIN_ACCOUNT, "-w"],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            text=True, check=False)
    if result.returncode != 0:
        raise ValueError("无法从钥匙串读取 API Key；请检查系统授权或先执行 keychain-save。")
    return result.stdout.removesuffix("\n").removesuffix("\r")


def find_codex() -> str | None:
    executable = shutil.which("codex.exe" if sys.platform == "win32" else "codex")
    if executable and (sys.platform != "win32" or executable.lower().endswith(".exe")):
        return executable
    if (sys.platform == "darwin" and os.path.isfile(CHATGPT_MAC_CODEX)
            and os.access(CHATGPT_MAC_CODEX, os.X_OK)):
        return CHATGPT_MAC_CODEX
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        local = os.environ["LOCALAPPDATA"]
        candidates = [os.path.join(local, "Programs", "OpenAI", "Codex", "bin", "codex.exe")]
        candidates += sorted(glob.glob(os.path.join(local, "OpenAI", "Codex", "bin", "*", "codex.exe")), reverse=True)
        for candidate in candidates:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
    return None


def run(home: Path, model: str, args: list[str], codex: str | None = None,
        use_keychain: bool = False) -> int:
    profile = home / "deepseek.config.toml"
    if home.is_symlink() or not home.is_dir() or profile.is_symlink() or not profile.is_file():
        raise ValueError("独立配置不存在或不是普通文件；请先运行 init。")
    codex = codex or find_codex()
    if not codex:
        if sys.platform == "win32":
            if shutil.which("codex.cmd"):
                raise ValueError("只找到 codex.cmd；为安全起见需要 codex.exe。请安装官方独立 CLI：https://developers.openai.com/codex/cli/")
            raise ValueError("找不到 codex.exe。请安装官方独立 CLI：https://developers.openai.com/codex/cli/")
        raise ValueError("找不到 codex 命令。请先安装并启动 Codex CLI。")
    if sys.platform == "win32" and not codex.lower().endswith(".exe"):
        raise ValueError("Windows 仅支持运行 codex.exe；请安装官方独立 CLI：https://developers.openai.com/codex/cli/")
    if use_keychain:
        key = read_credential()
    else:
        key = prompt_key()
    if not key or key != key.strip() or "\n" in key or "\r" in key:
        raise ValueError("API Key 不能为空，也不能包含首尾空格或换行。")
    env = os.environ.copy()
    env["CODEX_HOME"] = str(home.resolve())
    env["DEEPSEEK_API_KEY"] = key
    try:
        return subprocess.call(build_command(codex, model, args), env=env)
    finally:
        env.pop("DEEPSEEK_API_KEY", None)


def main() -> int:
    parser = argparse.ArgumentParser(description="使用独立 Codex 配置连接 DeepSeek。")
    parser.add_argument("--home", type=Path, default=Path.home() / ".codex-deepseek", help="独立配置目录（默认 ~/.codex-deepseek）")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("init", help="创建独立配置；已有目录绝不覆盖")
    sub.add_parser("keychain-save", help="macOS：将 Key 存入钥匙串（不会覆盖已有项目）")
    sub.add_parser("credential-save", help="Windows 或 macOS：保存 Key 至系统凭据管理器")
    launch = sub.add_parser("run", help="隐藏输入 Key 并启动 Codex")
    launch.add_argument("--model", choices=MODELS, default="flash", help="选择 flash 或 pro（默认 flash）")
    launch.add_argument("--credential", "--keychain", dest="keychain", action="store_true", help="从 Windows 凭据管理器或 macOS 钥匙串获取 Key")
    launch.add_argument("codex_args", nargs=argparse.REMAINDER, help="-- 之后的参数原样传给 codex")
    opts = parser.parse_args()
    home = opts.home.expanduser().absolute()
    try:
        if opts.action == "init":
            init_home(home)
            print(f"已创建独立配置：{home}")
            print("运行：python3 setup.py run")
            return 0
        if opts.action == "keychain-save":
            return save_keychain()
        if opts.action == "credential-save":
            return save_credential()
        args = opts.codex_args
        if args and args[0] == "--":
            args = args[1:]
        return run(home, opts.model, args, use_keychain=opts.keychain)
    except FileExistsError:
        print(f"目录已存在，未作修改：{home}", file=sys.stderr)
    except (OSError, ValueError) as exc:
        print(f"操作失败：{exc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
