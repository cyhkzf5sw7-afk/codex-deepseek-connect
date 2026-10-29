"""Minimal interface translations; the package LANGUAGE file selects a default."""
from pathlib import Path

_LANG = "zh"
EN = {
    "无法打开默认钥匙串（状态码 {status}）。": "Cannot open the default Keychain (status {status}).",
    "同名钥匙串项目已存在，未覆盖。": "A Keychain item with this name already exists; it was not overwritten.",
    "无法保存钥匙串项目（状态码 {status}）。": "Cannot save the Keychain item (status {status}).",
    "未找到钥匙串项目；请先执行 credential-save。": "Keychain item not found; run credential-save first.",
    "无法读取钥匙串项目（状态码 {status}）。": "Cannot read the Keychain item (status {status}).",
    "钥匙串项目内容无效。": "The Keychain item is invalid.",
    "钥匙串项目编码无效。": "The Keychain item has invalid encoding.",
    "已保存到 macOS 钥匙串。": "Saved to macOS Keychain.",
    "钥匙串功能仅支持 macOS；其他系统请使用交互式输入。": "Keychain is available on macOS only; use interactive input on other systems.",
    "找不到可执行的 macOS 系统命令 /usr/bin/security。": "The macOS system command /usr/bin/security is missing or not executable.",
    "请在系统提示时输入 DeepSeek API Key；已存在的同名钥匙串项目不会覆盖。": "Enter your DeepSeek API key at the system prompt. Existing keychain items are not overwritten.",
    "输入 DeepSeek API Key（不会显示）：": "Enter your DeepSeek API key (input is hidden): ",
    "输入已取消，或无法隐藏输入。": "Input was cancelled or cannot be hidden.",
    "API Key 不能为空，也不能包含首尾空格或换行。": "The API key must not be empty or contain leading/trailing whitespace or newlines.",
    "已保存到 Windows 凭据管理器。": "Saved to Windows Credential Manager.",
    "持久凭据功能支持 Windows 和 macOS；其他系统请使用交互式输入。": "Stored credentials are available on Windows and macOS; use interactive input on other systems.",
    "持久凭据功能支持 Windows 和 macOS。": "Stored credentials are available on Windows and macOS.",
    "无法从钥匙串读取 API Key；请检查系统授权或先执行 keychain-save。": "Cannot read the API key from Keychain; check system permission or run keychain-save first.",
    "独立配置不存在或不是普通文件；请先运行 init。": "The separate profile is missing or not a regular file; run init first.",
    "只找到 codex.cmd；为安全起见需要 codex.exe。请安装官方独立 CLI：https://developers.openai.com/codex/cli/": "Only codex.cmd was found; codex.exe is required for safety. Install the official standalone CLI: https://developers.openai.com/codex/cli/",
    "找不到 codex.exe。请安装官方独立 CLI：https://developers.openai.com/codex/cli/": "codex.exe was not found. Install the official standalone CLI: https://developers.openai.com/codex/cli/",
    "找不到 codex 命令。请先安装并启动 Codex CLI。": "Codex CLI was not found. Install and start Codex CLI first.",
    "Windows 仅支持运行 codex.exe；请安装官方独立 CLI：https://developers.openai.com/codex/cli/": "Only codex.exe is supported on Windows. Install the official standalone CLI: https://developers.openai.com/codex/cli/",
    "使用独立 Codex 配置连接 DeepSeek。": "Connect to DeepSeek using a separate Codex profile.",
    "独立配置目录（默认 ~/.codex-deepseek）": "Separate Codex home (default: ~/.codex-deepseek)",
    "创建独立配置；已有目录绝不覆盖": "Create the separate profile; never overwrite an existing directory",
    "macOS：将 Key 存入钥匙串（不会覆盖已有项目）": "macOS: save the key to Keychain without updating an existing item",
    "Windows 或 macOS：保存 Key 至系统凭据管理器": "Windows or macOS: save the key to the system credential manager",
    "隐藏输入 Key 并启动 Codex": "Start Codex with hidden key input",
    "选择 flash 或 pro（默认 flash）": "Choose flash or pro (default: flash)",
    "从 Windows 凭据管理器或 macOS 钥匙串获取 Key": "Read the key from Windows Credential Manager or macOS Keychain",
    "-- 之后的参数原样传给 codex": "Pass arguments after -- directly to codex",
    "选择推理档位 high 或 max（默认 high）": "Reasoning effort: high or max (default: high)",
    "界面语言（默认由 LANGUAGE 文件指定，否则为 zh）": "Interface language (defaults to the LANGUAGE file or zh)",
    "已创建独立配置：{home}": "Created separate Codex home: {home}",
    "运行：py -3 setup.py run": "Run: py -3 setup.py run",
    "运行：python3 setup.py run": "Run: python3 setup.py run",
    "目录已存在，未作修改：{home}": "Directory already exists; no changes made: {home}",
    "操作失败：{error}": "Operation failed: {error}",
    "Windows 凭据管理器读取失败（错误码 {error}）。": "Windows Credential Manager read failed (error code {error}).",
    "未找到 DeepSeek 凭据；请先执行 credential-save。": "DeepSeek credential not found; run credential-save first.",
    "Windows 凭据内容无效。": "The Windows credential is invalid.",
    "Windows 凭据内容编码无效。": "The Windows credential has invalid encoding.",
    "同名 Windows 凭据已存在，未覆盖。": "A Windows credential with this name already exists; it was not overwritten.",
    "API Key 长度无效。": "The API key length is invalid.",
    "Windows 凭据管理器写入失败（错误码 {error}）。": "Windows Credential Manager write failed (error code {error}).",
}


def set_language(language):
    global _LANG
    _LANG = language if language in ("en", "zh") else "zh"


def package_language():
    try:
        language = Path(__file__).resolve().with_name("LANGUAGE").read_text(encoding="utf-8").strip().lower()
        return language if language in ("en", "zh") else "zh"
    except (OSError, UnicodeError):
        return "zh"


def tr(message, **values):
    template = EN.get(message, message) if _LANG == "en" else message
    return template.format(**values)
