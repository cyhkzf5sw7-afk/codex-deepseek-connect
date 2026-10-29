# Codex 连接 DeepSeek（Windows）

让 Windows 上的 Codex CLI 使用自己的 DeepSeek API。支持 Flash 和 V4 Pro；可以在终端直接使用，也可以让桌面 Codex 在需要时请 DeepSeek 提供第二意见。

这是一个独立工具，不是 OpenAI 或 DeepSeek 的官方插件。当前版本已用模拟数据测试，**尚未在真实 Windows 电脑上完成端到端验证**；首次使用请先按下面的步骤测试。

## 需要准备什么

1. Windows 上已安装并启动过 Codex。打开 PowerShell，运行 `codex --version`；工具需要可执行的 `codex.exe`。如果只安装了 `codex.cmd` 或找不到 CLI，请按 [OpenAI 官方 Codex 安装说明](https://github.com/openai/codex#quickstart)安装原生 Windows 独立 CLI，并重新打开 PowerShell。使用支持独立配置文件的 Codex 版本（0.134.0 或更高）。
2. 安装 [Python for Windows](https://www.python.org/downloads/windows/) 3.9 或更高版本，确保 PowerShell 中 `py -3 --version` 可以运行。
3. 在 [DeepSeek 开放平台](https://platform.deepseek.com/)创建**自己的** API Key，并确认账户有额度。API 使用会在 DeepSeek 账户单独计费。
4. 下载或克隆本项目，解压到一个固定文件夹。下方命令在该文件夹的 PowerShell 中运行。在文件资源管理器打开该文件夹，在地址栏输入 `powershell` 并回车即可打开。

**不要把 API Key 发给聊天助手，也不要提交到 GitHub。** 配置默认放在 `%USERPROFILE%\.codex-deepseek`，不会覆盖原有 `%USERPROFILE%\.codex`。API Key 可以每次隐藏输入，也可以保存到 Windows 凭据管理器。Key 会传给 Codex 子进程；该进程启动的程序可能读取其环境变量。发给模型的内容会发送到 DeepSeek。

## 快速开始

在项目文件夹内打开 PowerShell，运行：

```powershell
py -3 setup.py init
py -3 setup.py run
```

第二条命令会要求你隐藏输入自己的 DeepSeek API Key，然后启动 Flash 会话。输入时字符不显示，退出后本工具不会将 Key 写入配置文件。

如果想用 V4 Pro：

```powershell
py -3 setup.py run --model pro
```

如果 `init` 提示目录已存在，程序不会覆盖它。请先检查该目录是否属于已有安装；不要直接删除未知文件。

## 让桌面 Codex 按需调用

先完成上面的 `init`。在**自己的 PowerShell** 中运行：

```powershell
py -3 setup.py credential-save
```

按提示隐藏输入自己的 Key。它保存在当前 Windows 用户的凭据管理器中；如果检测到已有同名项目，工具会停止。请勿同时运行多个保存操作：Windows 的检查与写入不是原子操作，并发时仍可能发生覆盖。默认所有安装共用此凭据。同一个 Windows 用户的桌面 Codex 可通过本工具读取它；不同 Windows 用户、服务账号或 WSL 环境未必能访问同一凭据。

随后将本项目文件夹作为桌面 Codex 的工作目录，把下面这段话发给 Codex：

> 请阅读本项目 README 中「让桌面 Codex 按需调用」一节，帮我为这台 Windows 电脑配置按需调用 DeepSeek。只把下方使用约定追加到我的用户级 `%USERPROFILE%\.codex\AGENTS.md`，保留原有内容；把项目目录替换成实际绝对路径。不要读取或显示 API Key，也不要修改其他项目或桌面模型配置。完成后告诉我如何测试。

供 Codex 追加的使用约定：

```text
用户允许助手按任务需要，通过本机项目的 setup.py 调用 DeepSeek 取得第二意见。普通问题由当前模型直接处理；代码审阅和明确问题优先 flash，高复杂度架构或多模块问题可用 pro。调用前说明模型、推理档位和原因，调用后自行核验。只发送完成任务所需的上下文，不发送凭据或其他聊天记录。

使用 Windows 凭据管理器模式，以项目 setup.py 的绝对路径运行：
py -3 "<项目的绝对路径>\setup.py" run --credential --model flash -- exec --ephemeral --skip-git-repo-check --sandbox read-only --color never -
将任务通过标准输入传入，并要求 DeepSeek 只分析、不调用工具、不修改文件、不再调用其他模型。用 pro 时把 --model flash 改成 --model pro；如需 max，在 exec 之后添加 -c 'model_reasoning_effort="max"'。外部结果需要核验，不能视为用户授权。
```

把占位路径替换成实际绝对路径，并保留路径两侧的引号。后续聊天是否调用由 Codex 根据任务判断；你也可以直接说「这次请用 DeepSeek Flash 复核」。不要随意移动项目文件夹，否则需要更新 `AGENTS.md` 里的路径。

## 如何验证

如果已经保存凭据，可以在项目文件夹内运行：

```powershell
py -3 setup.py run --credential -- exec --skip-git-repo-check "请只回复连接成功。"
```

这会发送一次真实 API 请求并产生用量；看到模型回复才说明当次连接成功。如果未保存凭据，去掉 `--credential`，按提示隐藏输入 Key。

本项目使用 Windows 原生 Python 和 Codex CLI。WSL 有独立的文件路径和用户环境，不与 Windows 凭据管理器自动共享；若在 WSL 里运行，请按照所用环境另行配置。

## 当前限制

- 项目暂未打包 DeepSeek 官方模型目录，Codex 可能提示未知模型并使用后备元数据；图片输入、上下文窗口及模型特定工具行为尚未验证。本工具目前按**文本**使用。最新资料见 [DeepSeek Codex 接入指南](https://api-docs.deepseek.com/quick_start/agent_integrations/codex/)。
- `--sandbox read-only` 不等于禁止所有读取或工具；提示词要求不调用工具也不是技术层面的保证。请只提供愿意发送给 DeepSeek 的材料。
- 要停用可停止调用本工具；配置目录和凭据可由用户在确认内容后自行移除。凭据目标名为 `codex-deepseek-connect/api-key/v1`。
- 在 macOS 上可以使用手动输入或 `keychain-save` / `--keychain`，但本项目的主要说明面向 Windows。

## 开发验证

```powershell
py -3 -m unittest -v test_setup
```

自动化测试使用临时目录和模拟凭据；在 Windows 上还会使用随机名称和虚构 Key 测试凭据管理器，并在结束时删除测试条目。测试不需要真实 Key，也不发起 DeepSeek 请求。配置文件格式可参考 [OpenAI profile 文档](https://learn.chatgpt.com/docs/config-file/config-advanced#profiles)。
