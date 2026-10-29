# Codex 连接 DeepSeek

[English](README.md)

下载适合你的版本：[Windows 中文版](https://github.com/cyhkzf5sw7-afk/codex-deepseek-connect/raw/refs/heads/main/downloads/Codex-DeepSeek-Windows-zh-CN.zip) · [Windows English](https://github.com/cyhkzf5sw7-afk/codex-deepseek-connect/raw/refs/heads/main/downloads/Codex-DeepSeek-Windows-en.zip) · [macOS 中文版](https://github.com/cyhkzf5sw7-afk/codex-deepseek-connect/raw/refs/heads/main/downloads/Codex-DeepSeek-macOS-zh-CN.zip) · [macOS English](https://github.com/cyhkzf5sw7-afk/codex-deepseek-connect/raw/refs/heads/main/downloads/Codex-DeepSeek-macOS-en.zip)。解压后先阅读 `START_HERE.txt`。

用你自己的 DeepSeek API 账户连接 Codex CLI，也可以让桌面 Codex 在需要时请 DeepSeek 提供第二意见。这是独立的社区工具，不是 OpenAI 或 DeepSeek 官方插件。工具使用独立的 Codex 配置目录，不会改变你平时使用的桌面模型配置。

选择适合你的指南：

- [Windows 中文指南](docs/windows.zh-CN.md) · [Windows English](docs/windows.en.md)
- [macOS 中文指南](docs/macos.zh-CN.md) · [macOS English](docs/macos.en.md)

需要 Python 3.9 或更新版本、Codex CLI 0.134.0 或更新版本，以及你自己的 DeepSeek API Key 和账户可用额度。Key 只在本机输入，不要发给聊天助手或其他人。API 请求由你的 DeepSeek 账户计费；只发送你愿意提供给 DeepSeek 的内容。

本包按文本请求支持 `deepseek-flash` 和 `deepseek-v4-pro`。包内附带基于 DeepSeek 公开能力信息整理的简化模型目录，以及本项目编写的简短基础指令；它不是完整官方目录。`high` 和 `max` 是请求参数，不保证输出效果；图片输入和上下文边界尚未验证。详见 [DeepSeek 官方接入指南](https://api-docs.deepseek.com/quick_start/agent_integrations/codex/)。

本包有[自动化测试](docs/VALIDATION.md)，但尚未在 Windows 或 macOS 上完成包含真实 DeepSeek 请求的端到端验证。`--sandbox read-only` 限制写入，**不等于禁用工具或禁止所有读取**；提示模型不用工具也不是技术保证。各平台指南包含最小连接测试，以及可选的桌面 Codex 按需调用说明。
