# Validation / 验证说明

[English home](../README.md) · [中文首页](../README.zh-CN.md)

## English

On the development Mac, the unit suite ran 33 tests: 32 passed and one Windows-only credential integration test was skipped. The CLI smoke test passed all four Flash/Pro and high/max combinations using Codex CLI 0.163.0-alpha.10.2 and a local mock Responses API; it checked the outgoing model, requested effort, standard input and response. Hidden key input was separately checked in a Mac terminal.

The tests use temporary files, mocks and synthetic keys. Actual macOS Keychain save/read under system authorization and a real DeepSeek API request have not been verified end to end. Image input and context-window boundaries have not been tested. The mock API cannot verify DeepSeek authentication, billing or model behavior.

To run the checks and build packages from this folder:

```text
python3 -B -m unittest -q test_setup
python3 -B -m unittest -v test_cli_smoke
python3 build_packages.py
```

On Windows use `py -3` in place of `python3`. The CLI smoke test requires a real Codex CLI; it skips when one is unavailable. The build writes ZIP files under `dist/` by default. No real API key is required for these commands.

## 中文

在开发用 Mac 上，单元测试共运行 33 项：32 项通过，1 项仅适用于 Windows 的真实凭据测试被跳过。CLI 冒烟测试使用 Codex CLI 0.163.0-alpha.10.2 和本地模拟 Responses API，Flash/Pro 与 high/max 的四种组合均通过，检查了发出的模型、推理参数、标准输入和响应。Mac 终端中还单独验证了 Key 的隐藏输入。

测试使用临时文件、模拟对象和虚构 Key。系统授权下的 macOS 钥匙串真实保存与读取、真实 DeepSeek API 请求尚未完成端到端验证；图片输入和上下文窗口边界也未测试。本地模拟 API 不能验证 DeepSeek 的认证、计费或模型表现。

在本文件夹中打开终端，运行检查和打包命令：

```text
python3 -B -m unittest -q test_setup
python3 -B -m unittest -v test_cli_smoke
python3 build_packages.py
```

Windows 将 `python3` 换成 `py -3`。CLI 冒烟测试需要真实 Codex CLI，找不到时会跳过。打包命令默认把 ZIP 文件写入 `dist/`。这些命令不需要真实 API Key。
