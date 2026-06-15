<p align="center">
  <h1 align="center">wchat</h1>
  <p align="center">
    远程微信 CLI 客户端 — 像用 Claude Code 一样聊微信
    <br />
    <strong>零侵入 · 不封号 · REPL 交互</strong>
  </p>
  <p align="center">
    <a href="#快速开始">快速开始</a> ·
    <a href="#使用演示">使用演示</a> ·
    <a href="#命令参考">命令参考</a> ·
    <a href="#常见问题">FAQ</a>
  </p>
</p>

---

## 这是什么？

`wchat` 让你通过命令行远程控制另一台 Mac 上的微信 —— 查看联系人、收发消息、监听新消息通知，全部在终端里完成。

交互风格借鉴 Claude Code：启动后进入 REPL，用斜杠命令切换上下文，直接打字就是发消息。

**为什么需要它？** 你可能有多台电脑，但不想每台都登录微信。把微信留在一台 Mac 上，其他地方用 `wchat` 远程操作就行。

## 核心特性

- **零侵入**：通过 macOS Accessibility API + AppleScript 模拟人工操作，不注入进程、不修改内存、不拦截网络包
- **不封号**：对微信来说和人手动操作完全一样，无法区分
- **REPL 交互**：Claude Code 风格的斜杠命令，`/chat 张三` 进入聊天，直接打字发消息
- **Tab 补全**：联系人名称自动补全
- **实时通知**：WebSocket 长连接，新消息即时推送到终端
- **安全通信**：Token 鉴权，建议配合 Tailscale 内网使用

## 架构

```
┌──────────────┐              ┌───────────────────────────┐
│  任意电脑     │    HTTPS     │  装有微信的 Mac            │
│              │   + Token    │                           │
│  wchat CLI   │◄────────────►│  FastAPI Server           │
│  (REPL)      │   WebSocket  │    ↓                      │
│              │              │  Accessibility API        │
└──────────────┘              │    ↓                      │
                              │  微信客户端                │
                              └───────────────────────────┘
```

## 快速开始

### 前置条件

- Python 3.10+
- 一台 Mac 上已登录微信
- （推荐）两台设备通过 [Tailscale](https://tailscale.com/) 组内网

### 1. 服务端（装有微信的 Mac）

```bash
git clone https://github.com/Tght1211/wechat-remote.git
cd wechat-remote

# 安装服务端依赖
pip install -r server/requirements.txt
```

**授权辅助功能**（必须）：

> 系统设置 → 隐私与安全性 → 辅助功能 → 添加你使用的终端（Terminal / iTerm2 / Warp 等）

```bash
# 确保微信已打开并登录，然后启动服务端
python -m server.server
```

启动成功后会打印 Token：

```
==================================================
  wchat server v0.1.0
  Token: your-secret-token-here
  请将此 Token 配置到 CLI 客户端
==================================================
```

### 2. 客户端（你日常用的电脑）

```bash
cd wechat-remote

# 安装为命令行工具
pip install -e .

# 启动
wchat
```

首次启动会交互式引导你配置服务端地址和 Token：

```
首次配置 wchat
请输入远程服务端地址（例如 http://192.168.1.100:9100）
服务端地址: http://100.xx.xx.xx:9100
请输入服务端 Token（启动服务端时会显示）
Token: your-secret-token-here
```

配置保存在 `~/.wchat.json`，下次启动自动读取。

## 使用演示

```
┌──────────────────────────────────────────────┐
│  wchat v0.1.0                                │
│  已连接: http://100.64.0.2:9100              │
│  输入 /help 查看可用命令                      │
├──────────────────────────────────────────────┤

> /chats

  最近会话:
  1. 工作群
  2. 张三
  3. 李四

> /chat 张三

  ── 与「张三」的对话 ──
  [14:01] 张三: 明天开会吗？
  [14:02] 我: 嗯，10点
  [14:03] 张三: 好的

张三 > 收到，明天见
  ✓ 已发送

张三 > /back

> /listen
  消息监听已开启，新消息将实时显示

  📨 新消息 — 李四: 在吗？

> /quit
  再见!
```

## 命令参考

| 命令 | 简写 | 说明 |
|------|------|------|
| `/contacts` | `/c` | 列出联系人 |
| `/chat <名字>` | `/<名字>` | 进入与某人的聊天，显示最近消息 |
| `/chats` | | 列出最近会话（含未读数） |
| `/back` | `/b` | 退出当前聊天，回到主界面 |
| `/search <关键词>` | | 搜索联系人或群 |
| `/file <路径>` | | 在当前聊天中发送文件 |
| `/history [n]` | | 查看更多历史消息（默认 20 条） |
| `/listen` | | 开启/关闭后台消息监听 |
| `/status` | | 查看连接状态 |
| `/help` | `/h` | 显示帮助 |
| `/quit` | `/q` | 退出 |

**聊天模式下**：直接输入文字即发送消息，`Ctrl+C` 退出当前聊天回到主界面。

## 网络配置

### 推荐：Tailscale（最简单）

两台 Mac 都安装 [Tailscale](https://tailscale.com/)，加入同一个网络，用 Tailscale 分配的 IP 地址即可互通，无需公网 IP 或端口映射。

### 备选：SSH 隧道

```bash
# 在本地 Mac 上建立 SSH 隧道
ssh -L 9100:localhost:9100 user@remote-mac
# 然后 wchat 连接 http://localhost:9100
```

### 备选：WireGuard / ZeroTier

任何能让两台设备互通的组网方案都可以，服务端默认监听 `0.0.0.0:9100`。

## 项目结构

```
wechat-remote/
├── server/                  # 远程服务端
│   ├── wechat_auto.py       # 微信 UI 自动化（Accessibility API + AppleScript）
│   ├── server.py            # FastAPI HTTP + WebSocket 服务
│   ├── auth.py              # Token 鉴权中间件
│   ├── __init__.py
│   └── requirements.txt
├── cli/                     # CLI 客户端
│   ├── app.py               # REPL 主循环（prompt_toolkit）
│   ├── commands.py          # 斜杠命令处理器
│   ├── renderer.py          # 终端渲染（rich）
│   ├── client.py            # HTTP + WebSocket 客户端
│   ├── completer.py         # Tab 补全
│   ├── config.py            # 配置管理
│   ├── __init__.py
│   └── requirements.txt
├── setup.py                 # pip install 入口，注册 wchat 命令
├── .gitignore
└── README.md
```

## API 参考

服务端暴露以下 REST API（均需 `Authorization: Bearer <token>` 头）：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查（无需鉴权） |
| GET | `/contacts?keyword=` | 获取联系人列表 |
| GET | `/chats` | 获取最近会话 |
| POST | `/chats/select` | 选中一个聊天 |
| GET | `/messages?count=20` | 获取当前聊天消息 |
| POST | `/messages` | 在当前聊天发送消息 |
| POST | `/messages/{contact}` | 向指定联系人发消息 |
| POST | `/files` | 在当前聊天发送文件 |
| WS | `/ws/notifications?token=` | WebSocket 实时消息推送 |

## 安全说明

- Token 保存在 `~/.wchat_token`（服务端）和 `~/.wchat.json`（客户端），权限均为 `600`
- 服务端启动时自动生成随机 Token，也可通过 `WCHAT_TOKEN` 环境变量指定
- **强烈建议**通过 Tailscale / SSH 隧道 / VPN 访问，不要将服务端直接暴露到公网

## 常见问题

<details>
<summary><strong>Q: 会被微信封号吗？</strong></summary>

本项目通过 macOS Accessibility API 读取微信界面控件、通过 AppleScript 模拟键盘操作来收发消息。不注入微信进程、不修改内存、不 Hook 任何函数。对微信来说，这和人手动操作没有区别。

但任何自动化工具都不能 100% 保证安全，建议仅用于个人用途，不要高频发送消息。
</details>

<details>
<summary><strong>Q: 支持 Windows 吗？</strong></summary>

目前仅支持 macOS 作为服务端（因为使用了 macOS Accessibility API）。CLI 客户端理论上可在任何平台运行。

Windows 版本可以考虑使用 pywinauto 作为自动化后端，欢迎 PR。
</details>

<details>
<summary><strong>Q: 微信更新后不能用了？</strong></summary>

微信大版本更新可能改变界面控件树结构，导致 `wechat_auto.py` 中的控件查找逻辑失效。遇到这种情况需要用 Accessibility Inspector（Xcode 内置）重新分析控件树并适配。
</details>

<details>
<summary><strong>Q: 辅助功能权限怎么授予？</strong></summary>

系统设置 → 隐私与安全性 → 辅助功能 → 点击 `+` → 添加你运行服务端的终端 App（Terminal / iTerm2 / Warp 等）。如果通过 Python 虚拟环境运行，可能需要添加 Python 可执行文件本身。
</details>

<details>
<summary><strong>Q: 远程 Mac 需要一直开着屏幕吗？</strong></summary>

不需要开着屏幕，但微信窗口不能最小化。可以把微信窗口放在桌面上然后锁屏，锁屏状态下 Accessibility API 仍然可用。
</details>

## 技术栈

| 组件 | 技术 |
|------|------|
| UI 自动化 | macOS Accessibility API (`pyobjc`) + AppleScript |
| 服务端 | Python + FastAPI + uvicorn |
| CLI 交互 | prompt_toolkit + rich |
| HTTP 客户端 | httpx (async) |
| 实时通信 | WebSocket (`websockets`) |
| 鉴权 | Bearer Token |

## Contributing

欢迎提交 Issue 和 PR。以下是一些可以改进的方向：

- [ ] Windows 服务端支持（pywinauto）
- [ ] 群聊 @ 功能
- [ ] 图片/表情消息的展示
- [ ] 消息本地缓存和搜索
- [ ] 更精确的消息解析（区分发送者/时间/内容）
- [ ] 支持发送图片
- [ ] 配置文件支持多个服务端 profile

## License

[MIT](LICENSE)

## 免责声明

本项目仅供学习和个人使用。请遵守微信使用条款，不要用于群发、骚扰、自动营销等违规行为。因使用本项目导致的任何问题，作者不承担责任。
