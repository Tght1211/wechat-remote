"""
FastAPI 服务端 — 暴露微信自动化能力为 REST API + WebSocket

@author buchi
@since 2026-06-15
"""
import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

from .auth import init_token, verify_token, TokenAuthMiddleware
from .wechat_auto import WeChatAutomation, Message

wechat = WeChatAutomation()

# WebSocket 连接管理
_ws_clients: set[WebSocket] = set()
_poll_task: Optional[asyncio.Task] = None
_last_messages: list[dict] = []


class SendMessageRequest(BaseModel):
    text: str


class SendFileRequest(BaseModel):
    path: str


class SelectChatRequest(BaseModel):
    name: str


async def _poll_new_messages():
    """后台轮询微信新消息，推送给所有 WebSocket 客户端"""
    global _last_messages
    while True:
        try:
            if _ws_clients:
                messages = wechat.get_messages(count=5)
                current = [
                    {"sender": m.sender, "content": m.content, "time": m.time}
                    for m in messages
                ]
                if current != _last_messages and current:
                    _last_messages = current
                    payload = json.dumps({
                        "type": "new_messages",
                        "data": current,
                    }, ensure_ascii=False)
                    dead = set()
                    for ws in _ws_clients:
                        try:
                            await ws.send_text(payload)
                        except Exception:
                            dead.add(ws)
                    _ws_clients -= dead
        except Exception:
            pass
        await asyncio.sleep(3)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _poll_task
    token = init_token()
    print(f"\n{'='*50}")
    print(f"  wchat server v0.1.0")
    print(f"  Token: {token}")
    print(f"  请将此 Token 配置到 CLI 客户端")
    print(f"{'='*50}\n")
    _poll_task = asyncio.create_task(_poll_new_messages())
    yield
    if _poll_task:
        _poll_task.cancel()


app = FastAPI(title="WeChat Remote", version="0.1.0", lifespan=lifespan)
app.add_middleware(TokenAuthMiddleware)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "wechat_running": wechat.is_running(),
        "timestamp": time.time(),
    }


@app.get("/contacts")
async def get_contacts(keyword: Optional[str] = Query(None)):
    try:
        if keyword:
            contacts = wechat.search_contact(keyword)
        else:
            contacts = wechat.get_contacts()
        return {
            "contacts": [{"name": c.name, "remark": c.remark} for c in contacts]
        }
    except Exception as e:
        return {"error": str(e), "contacts": []}


@app.get("/chats")
async def get_chats():
    try:
        sessions = wechat.get_session_list()
        return {
            "chats": [
                {"name": s.name, "last_message": s.last_message, "unread": s.unread}
                for s in sessions
            ]
        }
    except Exception as e:
        return {"error": str(e), "chats": []}


@app.post("/chats/select")
async def select_chat(req: SelectChatRequest):
    try:
        ok = wechat.select_chat(req.name)
        return {"success": ok, "chat": req.name}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/messages")
async def get_messages(count: int = Query(20, ge=1, le=100)):
    try:
        messages = wechat.get_messages(count=count)
        return {
            "messages": [
                {
                    "sender": m.sender,
                    "content": m.content,
                    "time": m.time,
                    "is_self": m.is_self,
                }
                for m in messages
            ]
        }
    except Exception as e:
        return {"error": str(e), "messages": []}


@app.post("/messages")
async def send_message(req: SendMessageRequest):
    try:
        ok = wechat.send_message(req.text)
        return {"success": ok}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/messages/{contact}")
async def send_message_to(contact: str, req: SendMessageRequest):
    try:
        ok = wechat.send_message_to(contact, req.text)
        return {"success": ok}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/files")
async def send_file(req: SendFileRequest):
    try:
        ok = wechat.send_file(req.path)
        return {"success": ok}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket, token: str = Query("")):
    if not verify_token(token):
        await websocket.close(code=4003, reason="Invalid token")
        return
    await websocket.accept()
    _ws_clients.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)


def main():
    import uvicorn
    uvicorn.run(
        "server.server:app",
        host="0.0.0.0",
        port=9100,
        log_level="info",
    )


if __name__ == "__main__":
    main()
