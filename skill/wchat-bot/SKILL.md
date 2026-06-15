---
name: wchat-bot
description: >-
  通过 wchat server REST API 远程操控微信：查看会话、联系人、收发消息、发送文件。
  当用户提到微信、发消息、聊天记录、联系人、给某人发微信、看看谁找我、
  微信回复、查微信消息时触发本 skill。
---

# wchat 微信操控助手

通过 wchat server 的 REST API 远程操控 macOS 微信客户端。所有工具通过 Shell 执行脚本完成。使用中文回答。

## 前置条件

- wchat server 已在目标 Mac 上运行（微信已登录）
- `~/.wchat.json` 已配置（含 `server_url` 和 `token`）

检查方式：

```bash
bash ~/.cursor/skills/wchat-bot/scripts/wchat.sh status
```

返回 `{"status":"ok","wechat_running":true,...}` 表示就绪。若失败，提示用户先启动 wchat server 并配置。

## Use when

- 用户说"发微信"、"微信消息"、"给 xxx 发消息"、"帮我回复 xxx"
- "看看谁找我了"、"最近微信消息"、"有人找我吗"
- "查联系人"、"搜一下 xxx"、"微信里有没有 xxx"
- "查看聊天记录"、"和 xxx 的对话"
- "发个文件给 xxx"
- "微信状态"、"微信连上了吗"

## Do not use when

- 用户讨论微信开发、微信小程序、微信公众号等技术话题（不是操控微信本身）
- 用户讨论企业微信 API 或 Bot 框架开发
- 操作与微信无关的聊天工具（钉钉、Slack、飞书等）

## 工具调用

> 所有命令通过 Shell 执行 `bash ~/.cursor/skills/wchat-bot/scripts/wchat.sh`，脚本自动从 `~/.wchat.json` 读取服务端地址和 Token。返回值均为 JSON。

### 1. 检查状态

```bash
bash ~/.cursor/skills/wchat-bot/scripts/wchat.sh status
```

返回：`{"status":"ok","wechat_running":true,"timestamp":...}`

### 2. 查看最近会话

```bash
bash ~/.cursor/skills/wchat-bot/scripts/wchat.sh chats
```

返回：`{"chats":[{"name":"张三","last_message":"好的","unread":0},...]}`

### 3. 查看联系人

```bash
bash ~/.cursor/skills/wchat-bot/scripts/wchat.sh contacts
```

返回：`{"contacts":[{"name":"张三","remark":""},...]}`

### 4. 搜索联系人

```bash
bash ~/.cursor/skills/wchat-bot/scripts/wchat.sh search "关键词"
```

返回：同联系人格式

### 5. 选中聊天并读取消息

先选中，再读消息，两步操作：

```bash
bash ~/.cursor/skills/wchat-bot/scripts/wchat.sh select "张三"
bash ~/.cursor/skills/wchat-bot/scripts/wchat.sh messages 20
```

返回消息：`{"messages":[{"sender":"张三","content":"明天开会","time":"14:01","is_self":false},...]}`

### 6. 在当前聊天中发送消息

先确保已 `select` 目标聊天：

```bash
bash ~/.cursor/skills/wchat-bot/scripts/wchat.sh send "你好，收到"
```

返回：`{"success":true}`

### 7. 给指定联系人发消息（一步完成）

无需先 select，直接发送：

```bash
bash ~/.cursor/skills/wchat-bot/scripts/wchat.sh send-to "张三" "明天10点开会"
```

返回：`{"success":true}`

### 8. 发送文件

先确保已 `select` 目标聊天：

```bash
bash ~/.cursor/skills/wchat-bot/scripts/wchat.sh send-file "/Users/xxx/report.pdf"
```

返回：`{"success":true}`

## 交互流程

### 场景 1：用户要给某人发消息

> 用户："帮我给张三发个微信，说明天下午3点开会"

1. 调用 `send-to "张三" "明天下午3点开会"`
2. 检查返回 `success`
3. 回复用户：已给张三发送消息 "明天下午3点开会"

### 场景 2：用户要查看最近消息

> 用户："看看最近谁找我了"

1. 调用 `chats` 获取最近会话列表
2. 以表格形式展示：联系人/群名、最后一条消息、未读数
3. 若用户接着说"看看张三说了什么"，进入场景 3

### 场景 3：用户要查看与某人的聊天记录

> 用户："看看和张三的聊天记录"

1. 调用 `select "张三"`
2. 调用 `messages 20` 读取最近 20 条
3. 以对话形式展示消息列表（区分对方/自己，带时间戳）
4. 用户可能接着说"回复他..."，进入场景 4

### 场景 4：用户要在当前对话中回复

> 用户："回复他：好的，明天见"

前提：已通过场景 3 选中了聊天对象

1. 调用 `send "好的，明天见"`
2. 确认发送成功

### 场景 5：用户要搜索联系人

> 用户："微信里有没有一个叫王什么的人"

1. 调用 `search "王"`
2. 展示匹配的联系人列表
3. 用户可能接着说"给第一个人发消息..."

### 场景 6：用户要发文件

> 用户："把这个 report.pdf 发给张三"

1. 调用 `select "张三"`
2. 调用 `send-file "/absolute/path/to/report.pdf"`（文件路径须为远程 Mac 上的绝对路径）
3. 确认发送成功

**文件路径注意**：如果 wchat server 和当前环境在同一台 Mac 上，直接用本地绝对路径即可；如果在不同机器，需要用远程 Mac 上的路径。

## 安全约束

- **发送消息前确认**：当用户意图明确（如"给张三发：xxx"）时直接发送，无需二次确认。但如果用户意图模糊（如"跟张三说一下"但没给具体内容），先追问消息内容
- **不要自动群发**：不支持也不执行批量给多人发同一条消息的操作
- **隐私保护**：聊天记录仅在当前对话中展示，不要主动存储或转发
- **错误处理**：API 返回错误时，用通俗的中文提示用户问题所在（如"微信未运行"、"找不到该联系人"）
