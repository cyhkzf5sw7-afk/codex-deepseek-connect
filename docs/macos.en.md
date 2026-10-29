# macOS guide

[Back to English home](../README.md) · [中文](macos.zh-CN.md)

This guide uses Terminal on your Mac. It creates a separate DeepSeek configuration and leaves your everyday desktop Codex model configuration unchanged. Use your own DeepSeek API key; requests are billed to your DeepSeek account.

## 1. Prepare

1. Install and open the Codex desktop app. Open Terminal and run `codex --version`; version 0.134.0 or later is required. If the command is unavailable, install the Codex CLI using [OpenAI's official instructions](https://github.com/openai/codex#quickstart). This tool also tries the default location of the CLI bundled with the ChatGPT desktop app.
2. In Terminal run `python3 --version`. Python 3.9 or later is required; if needed, download it from [python.org](https://www.python.org/downloads/macos/).
3. Create your own API key on the [DeepSeek platform](https://platform.deepseek.com/) and ensure your account has available balance. **Enter the key only on your own computer; do not paste it into chat, screenshots, or shared files.**
4. Download and extract this package to a stable folder. Open Terminal, type `cd ` (including the trailing space), drag the extracted folder into the Terminal window, and press Enter. Run the commands below in that window.

## 2. Initialize and connect

Run these commands in order:

```bash
python3 setup.py init
python3 setup.py run
```

The second command asks for your key with hidden input and starts a Flash session. Type a question once the session opens. `init` creates `~/.codex-deepseek`; if that directory already exists, it stops without overwriting it. Inspect an existing directory before taking action; do not delete unfamiliar files.

To select V4 Pro or a reasoning setting:

```bash
python3 setup.py run --model pro --reasoning high
python3 setup.py run --model flash --reasoning max
```

Choose `flash` or `pro`, and `high` or `max`; the default is Flash / high. Use this package for text. `high` and `max` are requested settings, not guarantees of output quality.

For a short connection test, run this and enter your key when prompted:

```bash
python3 setup.py run -- exec --ephemeral --skip-git-repo-check "Reply with connection successful."
```

This sends a real API request and incurs usage. A model response confirms that particular request succeeded. If it fails, check the CLI, network, key and account balance; remove sensitive information before sharing errors.

## 3. Optional: let desktop Codex call DeepSeek on demand

In your own Terminal, run this and enter your key at the hidden prompt to store it in the current macOS default keychain:

```bash
python3 setup.py credential-save
```

`keychain-save` is an alias for the same operation. Saving and reading use the current default keychain. An existing item with the same name will not be overwritten. macOS may ask for permission when it is read. The key is passed to the Codex child process and may be inherited by processes it starts.

Open this package folder in desktop Codex and send it the text below. Replace the placeholder with the actual absolute path to this package's `setup.py`, keeping the quotes:

```text
When a second opinion is useful, use the local DeepSeek tool. Handle ordinary tasks directly; use Flash for general review and consider Pro for complex architecture or multi-module work. Before each call state the model, reasoning setting, and reason. Send only the context needed for the task, never credentials or other chat histories. Verify the result yourself.

Use the following command, provide the task on standard input, and ask DeepSeek only to analyze: do not use tools, edit files, or call other models:
python3 "<absolute path to package folder>/setup.py" run --credential --model flash --reasoning high -- exec --ephemeral --skip-git-repo-check --sandbox read-only --color never -

Change flash to pro for Pro or high to max for max. Read-only does not disable all tools, and instructions cannot guarantee that tools will not be used.
```

This gives the current chat a usage convention. To apply one to future chats, you may explicitly ask desktop Codex to append your chosen convention to your user-level `~/.codex/AGENTS.md`, preserving existing contents. If you move the package, update its path in the convention.

After saving a credential, this minimal test no longer requires typing the key:

```bash
python3 setup.py run --credential -- exec --ephemeral --skip-git-repo-check "Reply with connection successful."
```

## Boundaries

- The tool uses a separate home from your everyday desktop configuration.
- The package includes simplified model metadata and a short project-written instruction. Image input and context limits have not been verified.
- `--sandbox read-only` does not disable tools or all reads. The model may receive material you provide and readable information in its execution environment; only share what you are willing to send to DeepSeek.
- To stop using the tool, stop running it. After checking their contents, you may remove the separate home and the Keychain Access item with service `org.codex-deepseek-connect.api-key.v1` and account `default`.
- Actual macOS Keychain save/read and the real DeepSeek API workflow have not been verified end to end.

The package's `LANGUAGE` file selects this tool's prompt language: English in the English package and Chinese in the Chinese package. Without the file, the default is Chinese. This does not control Codex's own language. You can override it before the subcommand with `--lang en` or `--lang zh`, for example `python3 setup.py --lang en init`.
