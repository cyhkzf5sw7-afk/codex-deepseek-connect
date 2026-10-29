# macOS 使用指南

[返回中文首页](../README.zh-CN.md) · [English](macos.en.md)

这份指南在 Mac 的“终端”中操作。它会创建单独的 DeepSeek 配置，不改变你平时使用的 Codex 桌面模型。请使用自己的 DeepSeek API Key，API 用量由你的 DeepSeek 账户单独计费。

## 1. 准备

1. 安装并打开过 Codex 桌面应用。打开“终端”输入 `codex --version` 检查 CLI；需要 0.134.0 或更新版本。如果找不到，按 [OpenAI 官方说明](https://github.com/openai/codex#quickstart)安装 Codex CLI；本工具也会尝试查找默认安装位置的 ChatGPT 桌面应用内置 CLI。
2. 在终端运行 `python3 --version`。需要 Python 3.9 或更新版本；如未安装，可从 [Python 官方网站](https://www.python.org/downloads/macos/)下载。
3. 在 [DeepSeek 开放平台](https://platform.deepseek.com/)创建自己的 API Key，确认账户有可用额度。**只在自己的电脑上输入 Key，不要发到聊天里、截图或共享。**
4. 下载并解压本包到一个固定文件夹。打开“终端”，输入 `cd `（最后有一个空格），把解压后的文件夹拖到终端窗口，再按回车。以下命令都在这个窗口运行。

## 2. 初始化和连接

依次输入：

```bash
python3 setup.py init
python3 setup.py run
```

第二条命令会提示输入 Key，输入时不会显示字符；按回车后启动 Flash 会话。你可以在会话里输入问题。`init` 创建 `~/.codex-deepseek`；如果目录已存在，程序会停止，不会覆盖它。请先检查现有目录，不要直接删除未知文件。

选 V4 Pro 或指定推理档位：

```bash
python3 setup.py run --model pro --reasoning high
python3 setup.py run --model flash --reasoning max
```

支持 `flash`、`pro` 和 `high`、`max`，默认是 Flash / high。当前按文本使用；`high` 和 `max` 是请求参数，不保证输出效果。

想先做一次简短连接测试，可运行下面的命令并按提示输入 Key：

```bash
python3 setup.py run -- exec --ephemeral --skip-git-repo-check "请只回复连接成功。"
```

这是一次真实 API 请求，会产生用量。看到模型回复才表示该次请求成功；报错时请检查 CLI、网络、Key 和账户额度，分享错误前先去掉任何敏感信息。

## 3. 可选：让桌面 Codex 按需调用

在自己的终端执行以下命令，在隐藏输入提示处输入 Key，将其保存到 macOS 当前默认钥匙串：

```bash
python3 setup.py credential-save
```

`keychain-save` 是同一操作的别名。保存和读取都使用当前默认钥匙串；如果已有同名项目，程序不会覆盖它。读取时 macOS 可能要求授权。Key 会传给 Codex 子进程及其可能继承环境变量的子进程。

在桌面 Codex 中打开本包所在文件夹，复制下面的话发送给它；请把占位路径改成本包内 `setup.py` 的实际绝对路径，保留引号：

```text
请在需要第二意见时使用本机 DeepSeek：普通任务直接处理；一般审阅选 Flash，复杂架构或多模块问题可选 Pro。每次调用前说明模型、档位和原因；只发送完成任务所需的上下文，不发送凭据或其他聊天记录。请核验输出。

使用以下命令，将任务通过标准输入提供，并要求 DeepSeek 仅分析，不使用工具、不修改文件、不再调用其他模型：
python3 "<本包文件夹的绝对路径>/setup.py" run --credential --model flash --reasoning high -- exec --ephemeral --skip-git-repo-check --sandbox read-only --color never -

需要 Pro 时将 flash 改为 pro，需要 max 时将 high 改为 max。read-only 不会禁用所有工具，提示词也不能保证工具不被使用。
```

这段话只对发送它的聊天提供使用约定。若想让以后新聊天也遵循，可明确请桌面 Codex 将适合你的约定追加到用户级 `~/.codex/AGENTS.md`，并保留原有内容。不要随意移动包文件夹，否则须更新约定中的路径。

保存凭据后，可运行下面的最小测试，不再重复输入 Key：

```bash
python3 setup.py run --credential -- exec --ephemeral --skip-git-repo-check "请只回复连接成功。"
```

## 使用边界

- 本工具使用独立目录，和桌面的日常 Codex 配置分开。
- 本包附带简化模型信息与本项目编写的简短基础指令；图片输入和上下文边界尚未验证。
- `--sandbox read-only` 不是禁用工具，也不禁止所有读取。模型可能看到你提供的材料及运行环境中可读取的内容；仅提交愿意发送给 DeepSeek 的内容。
- 停用时停止运行本工具；确认内容后可自行移除独立目录和“钥匙串访问”中服务名为 `org.codex-deepseek-connect.api-key.v1`、账户为 `default` 的条目。
- macOS 钥匙串的真实保存与读取、真实 DeepSeek API 流程尚未端到端验证。

程序语言由包内 `LANGUAGE` 文件决定：英文包默认英文，中文包默认中文；文件不存在时默认为中文。这只控制本工具的提示，不控制 Codex 自身的语言。也可在子命令前指定 `--lang zh` 或 `--lang en`，例如 `python3 setup.py --lang en init`。
