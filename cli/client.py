"""
HTTP / WebSocket 客户端封装

@author buchi
@since 2026-06-15
"""
import asyncio
import json
from typing import Optional, Callable

import httpx
import websockets

from .config import Config


class WeChatClient:
    """远程 wchat server 的客户端"""

    def __init__(self, config: Config):
        self.config = config
        self._http: Optional[httpx.AsyncClient] = None
        self._ws = None
        self._ws_task: Optional[asyncio.Task] = None
        self._on_message: Optional[Callable] = None

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.config.token}"}

    async def _ensure_http(self):
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self.config.server_url,
                headers=self._headers,
                timeout=15.0,
            )

    async def close(self):
        if self._ws_task:
            self._ws_task.cancel()
        if self._ws:
            await self._ws.close()
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    async def health(self) -> dict:
        await self._ensure_http()
        r = await self._http.get("/health")
        return r.json()

    async def get_contacts(self, keyword: str = "") -> list[dict]:
        await self._ensure_http()
        params = {"keyword": keyword} if keyword else {}
        r = await self._http.get("/contacts", params=params)
        data = r.json()
        return data.get("contacts", [])

    async def get_chats(self) -> list[dict]:
        await self._ensure_http()
        r = await self._http.get("/chats")
        data = r.json()
        return data.get("chats", [])

    async def select_chat(self, name: str) -> bool:
        await self._ensure_http()
        r = await self._http.post("/chats/select", json={"name": name})
        data = r.json()
        return data.get("success", False)

    async def get_messages(self, count: int = 20) -> list[dict]:
        await self._ensure_http()
        r = await self._http.get("/messages", params={"count": count})
        data = r.json()
        return data.get("messages", [])

    async def send_message(self, text: str) -> bool:
        await self._ensure_http()
        r = await self._http.post("/messages", json={"text": text})
        data = r.json()
        return data.get("success", False)

    async def send_message_to(self, contact: str, text: str) -> bool:
        await self._ensure_http()
        r = await self._http.post(f"/messages/{contact}", json={"text": text})
        data = r.json()
        return data.get("success", False)

    async def send_file(self, path: str) -> bool:
        await self._ensure_http()
        r = await self._http.post("/files", json={"path": path})
        data = r.json()
        return data.get("success", False)

    async def start_listening(self, on_message: Callable):
        """启动 WebSocket 监听"""
        self._on_message = on_message
        self._ws_task = asyncio.create_task(self._ws_loop())

    async def stop_listening(self):
        if self._ws_task:
            self._ws_task.cancel()
            self._ws_task = None

    async def _ws_loop(self):
        ws_url = self.config.server_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/ws/notifications?token={self.config.token}"
        while True:
            try:
                async with websockets.connect(ws_url) as ws:
                    self._ws = ws
                    async for raw in ws:
                        try:
                            data = json.loads(raw)
                            if self._on_message and data.get("type") == "new_messages":
                                await self._on_message(data["data"])
                        except json.JSONDecodeError:
                            pass
            except (websockets.ConnectionClosed, ConnectionRefusedError, OSError):
                await asyncio.sleep(3)
            except asyncio.CancelledError:
                break
