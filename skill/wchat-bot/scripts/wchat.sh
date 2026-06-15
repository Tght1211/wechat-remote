#!/usr/bin/env bash
# wchat.sh — wchat server REST API 封装
# 自动从 ~/.wchat.json 读取 server_url 和 token
set -euo pipefail

CONFIG_FILE="$HOME/.wchat.json"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo '{"error": "配置文件 ~/.wchat.json 不存在，请先运行 wchat CLI 完成配置"}' >&2
  exit 1
fi

SERVER_URL=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['server_url'])" 2>/dev/null)
TOKEN=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['token'])" 2>/dev/null)

if [[ -z "$SERVER_URL" || -z "$TOKEN" ]]; then
  echo '{"error": "无法从 ~/.wchat.json 读取 server_url 或 token"}' >&2
  exit 1
fi

AUTH="Authorization: Bearer $TOKEN"
CT="Content-Type: application/json"

cmd="${1:-help}"
shift || true

case "$cmd" in
  status)
    curl -s "$SERVER_URL/health"
    ;;
  chats)
    curl -s -H "$AUTH" "$SERVER_URL/chats"
    ;;
  contacts)
    curl -s -H "$AUTH" "$SERVER_URL/contacts"
    ;;
  search)
    keyword="${1:?用法: wchat.sh search <关键词>}"
    curl -s -H "$AUTH" "$SERVER_URL/contacts?keyword=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$keyword'))")"
    ;;
  select)
    name="${1:?用法: wchat.sh select <联系人名>}"
    curl -s -X POST -H "$AUTH" -H "$CT" -d "{\"name\":\"$name\"}" "$SERVER_URL/chats/select"
    ;;
  messages)
    count="${1:-20}"
    curl -s -H "$AUTH" "$SERVER_URL/messages?count=$count"
    ;;
  send)
    text="${1:?用法: wchat.sh send <消息文本>}"
    curl -s -X POST -H "$AUTH" -H "$CT" -d "{\"text\":\"$text\"}" "$SERVER_URL/messages"
    ;;
  send-to)
    contact="${1:?用法: wchat.sh send-to <联系人> <消息>}"
    text="${2:?用法: wchat.sh send-to <联系人> <消息>}"
    encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$contact'))")
    curl -s -X POST -H "$AUTH" -H "$CT" -d "{\"text\":\"$text\"}" "$SERVER_URL/messages/$encoded"
    ;;
  send-file)
    filepath="${1:?用法: wchat.sh send-file <文件路径>}"
    curl -s -X POST -H "$AUTH" -H "$CT" -d "{\"path\":\"$filepath\"}" "$SERVER_URL/files"
    ;;
  help)
    cat <<'USAGE'
用法: wchat.sh <命令> [参数]

命令:
  status                  检查服务端和微信状态
  chats                   查看最近会话列表
  contacts                查看联系人列表
  search <关键词>         搜索联系人
  select <联系人名>       选中一个聊天
  messages [数量]         读取当前聊天消息（默认20条）
  send <消息>             在当前聊天中发送消息
  send-to <联系人> <消息> 给指定联系人发消息
  send-file <文件路径>    在当前聊天中发送文件
  help                    显示此帮助
USAGE
    ;;
  *)
    echo "{\"error\": \"未知命令: $cmd，运行 wchat.sh help 查看帮助\"}" >&2
    exit 1
    ;;
esac
