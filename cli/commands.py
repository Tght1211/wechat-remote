"""
斜杠命令处理

@author buchi
@since 2026-06-15
"""
from dataclasses import dataclass, field
from typing import Optional

from .client import WeChatClient
from . import renderer


@dataclass
class AppState:
    current_chat: Optional[str] = None
    listening: bool = False
    contacts_cache: list[str] = field(default_factory=list)

    @property
    def in_chat(self) -> bool:
        return self.current_chat is not None

    @property
    def prompt_text(self) -> str:
        if self.current_chat:
            return f"{self.current_chat} > "
        return "> "


async def handle_command(raw: str, client: WeChatClient, state: AppState) -> bool:
    """
    处理用户输入。返回 False 表示退出程序。
    """
    stripped = raw.strip()
    if not stripped:
        return True

    # 在聊天界面中，非斜杠输入 = 发消息
    if state.in_chat and not stripped.startswith("/"):
        return await _send_in_chat(stripped, client, state)

    if not stripped.startswith("/"):
        renderer.render_info("输入 /help 查看可用命令")
        return True

    parts = stripped.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    handlers = {
        "/contacts": _cmd_contacts,
        "/c": _cmd_contacts,
        "/chat": _cmd_chat,
        "/chats": _cmd_chats,
        "/back": _cmd_back,
        "/b": _cmd_back,
        "/search": _cmd_search,
        "/file": _cmd_file,
        "/history": _cmd_history,
        "/listen": _cmd_listen,
        "/status": _cmd_status,
        "/help": _cmd_help,
        "/h": _cmd_help,
        "/quit": _cmd_quit,
        "/q": _cmd_quit,
    }

    handler = handlers.get(cmd)
    if handler:
        return await handler(arg, client, state)

    # 未匹配的 /xxx 尝试作为联系人名进入聊天
    name = cmd[1:]
    if name:
        return await _cmd_chat(name, client, state)

    renderer.render_error(f"未知命令: {cmd}，输入 /help 查看帮助")
    return True


async def _send_in_chat(text: str, client: WeChatClient, state: AppState) -> bool:
    try:
        ok = await client.send_message(text)
        if ok:
            renderer.render_sent_ok()
        else:
            renderer.render_sent_fail()
    except Exception as e:
        renderer.render_sent_fail(str(e))
    return True


async def _cmd_contacts(arg: str, client: WeChatClient, state: AppState) -> bool:
    try:
        contacts = await client.get_contacts(keyword=arg)
        renderer.render_contacts(contacts)
        state.contacts_cache = [c["name"] for c in contacts]
    except Exception as e:
        renderer.render_error(f"获取联系人失败: {e}")
    return True


async def _cmd_chat(arg: str, client: WeChatClient, state: AppState) -> bool:
    name = arg.strip()
    if not name:
        renderer.render_error("请指定联系人: /chat <名字>")
        return True
    try:
        ok = await client.select_chat(name)
        if ok:
            state.current_chat = name
            renderer.render_chat_header(name)
            messages = await client.get_messages(count=20)
            renderer.render_messages(messages)
        else:
            renderer.render_error(f"无法切换到「{name}」的聊天")
    except Exception as e:
        renderer.render_error(f"切换聊天失败: {e}")
    return True


async def _cmd_chats(arg: str, client: WeChatClient, state: AppState) -> bool:
    try:
        chats = await client.get_chats()
        renderer.render_chats(chats)
    except Exception as e:
        renderer.render_error(f"获取会话列表失败: {e}")
    return True


async def _cmd_back(arg: str, client: WeChatClient, state: AppState) -> bool:
    if state.in_chat:
        renderer.render_info(f"已退出「{state.current_chat}」的聊天")
        state.current_chat = None
    else:
        renderer.render_info("当前已在主界面")
    return True


async def _cmd_search(arg: str, client: WeChatClient, state: AppState) -> bool:
    keyword = arg.strip()
    if not keyword:
        renderer.render_error("请指定搜索关键词: /search <关键词>")
        return True
    try:
        contacts = await client.get_contacts(keyword=keyword)
        renderer.render_contacts(contacts)
    except Exception as e:
        renderer.render_error(f"搜索失败: {e}")
    return True


async def _cmd_file(arg: str, client: WeChatClient, state: AppState) -> bool:
    if not state.in_chat:
        renderer.render_error("请先进入聊天: /chat <名字>")
        return True
    path = arg.strip()
    if not path:
        renderer.render_error("请指定文件路径: /file <路径>")
        return True
    try:
        ok = await client.send_file(path)
        if ok:
            renderer.render_sent_ok()
        else:
            renderer.render_sent_fail()
    except Exception as e:
        renderer.render_sent_fail(str(e))
    return True


async def _cmd_history(arg: str, client: WeChatClient, state: AppState) -> bool:
    if not state.in_chat:
        renderer.render_error("请先进入聊天: /chat <名字>")
        return True
    try:
        count = int(arg) if arg.strip() else 20
    except ValueError:
        count = 20
    try:
        messages = await client.get_messages(count=count)
        renderer.render_messages(messages)
    except Exception as e:
        renderer.render_error(f"获取历史消息失败: {e}")
    return True


async def _cmd_listen(arg: str, client: WeChatClient, state: AppState) -> bool:
    if state.listening:
        await client.stop_listening()
        state.listening = False
        renderer.render_info("消息监听已关闭")
    else:
        async def on_message(messages):
            renderer.render_notification(messages)

        await client.start_listening(on_message)
        state.listening = True
        renderer.render_info("消息监听已开启，新消息将实时显示")
    return True


async def _cmd_status(arg: str, client: WeChatClient, state: AppState) -> bool:
    try:
        health = await client.health()
        renderer.render_status(
            server_url=client.config.server_url,
            wechat_running=health.get("wechat_running", False),
            listening=state.listening,
        )
    except Exception as e:
        renderer.render_error(f"无法连接服务端: {e}")
    return True


async def _cmd_help(arg: str, client: WeChatClient, state: AppState) -> bool:
    renderer.render_help()
    return True


async def _cmd_quit(arg: str, client: WeChatClient, state: AppState) -> bool:
    renderer.render_info("再见!")
    return False
