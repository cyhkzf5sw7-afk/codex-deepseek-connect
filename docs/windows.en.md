# Windows guide

[Back to English home](../README.md) · [中文](windows.zh-CN.md)

This guide uses native Windows PowerShell. It creates a separate DeepSeek configuration and leaves your everyday desktop Codex model configuration unchanged. Use your own DeepSeek API key; requests are billed to your DeepSeek account.

## 1. Prepare

1. Install and open the Codex desktop app. Install the [official OpenAI Codex CLI](https://github.com/openai/codex#quickstart), reopen PowerShell, and run `codex --version`. Version 0.134.0 or later is required. This tool requires native Windows `codex.exe`; if you only have `codex.cmd`, install the official standalone CLI. Having the desktop app does not guarantee that the CLI is available in your terminal.
2. Install Python 3.9 or later from [python.org](https://www.python.org/downloads/windows/). In PowerShell, run `py -3 --version` to check it.
3. Create your own API key on the [DeepSeek platform](https://platform.deepseek.com/) and ensure your account has available balance. **Enter the key only on your own computer; do not paste it into chat, screenshots, or shared files.**
4. Download and extract this package to a stable folder. Open that folder in File Explorer, type `powershell` into the address bar, and press Enter. Run the commands below in that window.

If you only have `codex.cmd` or cannot find `codex.exe`, run the [official OpenAI standalone installer](https://github.com/openai/codex#quickstart) in PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
```

Reopen PowerShell and run `codex --version` after installation. This tool also checks the official installation directory for `codex.exe`.

## 2. Initialize and connect

Run these commands in order:

```powershell
py -3 setup.py init
py -3 setup.py run
```

The second command asks for your key with hidden input and starts a Flash session. Type a question once the session opens. `init` creates `%USERPROFILE%\.codex-deepseek`; if that directory already exists, it stops without overwriting it. Inspect an existing directory before taking action; do not delete unfamiliar files.

To select V4 Pro or a reasoning setting:

```powershell
py -3 setup.py run --model pro --reasoning high
py -3 setup.py run --model flash --reasoning max
```

Choose `flash` or `pro`, and `high` or `max`; the default is Flash / high. Use this package for text. `high` and `max` are requested settings, not guarantees of output quality.

For a short connection test, run this and enter your key when prompted:

```powershell
py -3 setup.py run -- exec --ephemeral --skip-git-repo-check "Reply with connection successful."
```

This sends a real API request and incurs usage. A model response confirms that particular request succeeded. If it fails, check the CLI, network, key and account balance; remove sensitive information before sharing errors.

## 3. Optional: let desktop Codex call DeepSeek on demand

In your own PowerShell, run this and enter your key at the hidden prompt to store it in Windows Credential Manager:

```powershell
py -3 setup.py credential-save
```

The tool stops if an item with the same name already exists. Do not run multiple save operations concurrently: the check and write are not atomic. Installations under the same Windows user share this credential by default; other users, service accounts and WSL may not be able to read it. The key is passed to the Codex child process and may be inherited by processes it starts.

Open this package folder in desktop Codex and send it the text below. Replace the placeholder with the actual absolute path to this package's `setup.py`, keeping the quotes:

```text
When a second opinion is useful, use the local DeepSeek tool. Handle ordinary tasks directly; use Flash for general review and consider Pro for complex architecture or multi-module work. Before each call state the model, reasoning setting, and reason. Send only the context needed for the task, never credentials or other chat histories. Verify the result yourself.

Use the following command, provide the task on standard input, and ask DeepSeek only to analyze: do not use tools, edit files, or call other models:
py -3 "<absolute path to package folder>\setup.py" run --credential --model flash --reasoning high -- exec --ephemeral --skip-git-repo-check --sandbox read-only --color never -

Change flash to pro for Pro or high to max for max. Read-only does not disable all tools, and instructions cannot guarantee that tools will not be used.
```

This gives the current chat a usage convention. To apply one to future chats, you may explicitly ask desktop Codex to append your chosen convention to your user-level `%USERPROFILE%\.codex\AGENTS.md`, preserving existing contents. If you move the package, update its path in the convention.

After saving a credential, this minimal test no longer requires typing the key:

```powershell
py -3 setup.py run --credential -- exec --ephemeral --skip-git-repo-check "Reply with connection successful."
```

## Boundaries

- The tool uses a separate home from your everyday desktop configuration. WSL normally has its own Linux home; this guide and credential method are for native Windows.
- The package includes simplified model metadata and a short project-written instruction. Image input and context limits have not been verified.
- `--sandbox read-only` does not disable tools or all reads. The model may receive material you provide and readable information in its execution environment; only share what you are willing to send to DeepSeek.
- To stop using the tool, stop running it. After checking their contents, you may remove the separate home and the Windows Credential Manager item named `codex-deepseek-connect/api-key/v1`.
- Windows credential handling has mock and system-credential tests, but the complete real API workflow has not been verified end to end on Windows.

The package's `LANGUAGE` file selects this tool's prompt language: English in the English package and Chinese in the Chinese package. Without the file, the default is Chinese. This does not control Codex's own language. You can override it before the subcommand with `--lang en` or `--lang zh`, for example `py -3 setup.py --lang en init`.
