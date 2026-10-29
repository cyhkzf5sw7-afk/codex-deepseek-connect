# Codex DeepSeek Connect

[中文说明](README.zh-CN.md)

Download a package: [Windows · English](https://github.com/cyhkzf5sw7-afk/codex-deepseek-connect/raw/refs/heads/main/downloads/Codex-DeepSeek-Windows-en.zip) · [Windows · 中文](https://github.com/cyhkzf5sw7-afk/codex-deepseek-connect/raw/refs/heads/main/downloads/Codex-DeepSeek-Windows-zh-CN.zip) · [macOS · English](https://github.com/cyhkzf5sw7-afk/codex-deepseek-connect/raw/refs/heads/main/downloads/Codex-DeepSeek-macOS-en.zip) · [macOS · 中文](https://github.com/cyhkzf5sw7-afk/codex-deepseek-connect/raw/refs/heads/main/downloads/Codex-DeepSeek-macOS-zh-CN.zip). Extract it and read `START_HERE.txt`.

Use your own DeepSeek API account with Codex CLI, or let your desktop Codex ask DeepSeek for a second opinion when needed. This is an independent community tool, not an official OpenAI or DeepSeek plugin. It uses a separate Codex home, so it does not change your normal desktop model configuration.

Choose a guide:

- [Windows — English](docs/windows.en.md) · [Windows — 中文](docs/windows.zh-CN.md)
- [macOS — English](docs/macos.en.md) · [macOS — 中文](docs/macos.zh-CN.md)

You need Python 3.9 or later, Codex CLI 0.134.0 or later, and your own DeepSeek API key and available account balance. The key is entered locally; never paste it into chat or share it. Requests are billed to your DeepSeek account. Only send material you are willing to share with DeepSeek.

This package supports text requests with `deepseek-flash` and `deepseek-v4-pro`. It includes simplified model metadata based on DeepSeek's published capabilities and a short project-written instruction, rather than the full official catalog. `high` and `max` are requested settings, not guarantees of output quality; image input and context limits have not been verified. See the [DeepSeek integration guide](https://api-docs.deepseek.com/quick_start/agent_integrations/codex/).

The package has [automated tests](docs/VALIDATION.md), but the complete setup and a real DeepSeek request have not yet been verified end to end on Windows or macOS. `--sandbox read-only` limits writes; it does **not** disable tools or all reading. Asking the model not to use tools is an instruction, not a technical guarantee. The guides include a minimal connection test and optional instructions for desktop Codex to call DeepSeek on demand.
