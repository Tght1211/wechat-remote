"""
Tab 补全 — 斜杠命令和联系人名补全

@author buchi
@since 2026-06-15
"""
from prompt_toolkit.completion import Completer, Completion


COMMANDS = [
    ("/contacts", "列出联系人"),
    ("/c", "列出联系人（简写）"),
    ("/chat", "进入聊天"),
    ("/chats", "最近会话"),
    ("/back", "退出当前聊天"),
    ("/b", "退出当前聊天（简写）"),
    ("/search", "搜索联系人"),
    ("/file", "发送文件"),
    ("/history", "查看历史消息"),
    ("/listen", "消息监听"),
    ("/status", "连接状态"),
    ("/help", "帮助"),
    ("/h", "帮助（简写）"),
    ("/quit", "退出"),
    ("/q", "退出（简写）"),
]


class WeChatCompleter(Completer):
    def __init__(self):
        self._contacts: list[str] = []

    def update_contacts(self, contacts: list[str]):
        self._contacts = contacts

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        stripped = text.lstrip()

        if not stripped.startswith("/"):
            return

        # "/chat 张" -> 补全联系人名
        if stripped.startswith("/chat "):
            prefix = stripped[6:]
            for name in self._contacts:
                if name.startswith(prefix) or prefix in name:
                    yield Completion(name, start_position=-len(prefix))
            return

        # "/search 关" -> 补全联系人名
        if stripped.startswith("/search "):
            prefix = stripped[8:]
            for name in self._contacts:
                if name.startswith(prefix) or prefix in name:
                    yield Completion(name, start_position=-len(prefix))
            return

        # 补全斜杠命令本身
        for cmd, desc in COMMANDS:
            if cmd.startswith(stripped):
                yield Completion(
                    cmd,
                    start_position=-len(stripped),
                    display_meta=desc,
                )
