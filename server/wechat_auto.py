"""
微信 macOS UI 自动化核心模块
通过 Accessibility API + AppleScript 零侵入控制微信

@author buchi
@since 2026-06-15
"""
import subprocess
import time
import re
from dataclasses import dataclass, field
from typing import Optional

import Quartz
from ApplicationServices import (
    AXUIElementCreateApplication,
    AXUIElementCopyAttributeValue,
    AXUIElementCopyAttributeNames,
    AXUIElementPerformAction,
    AXUIElementSetAttributeValue,
)
from CoreFoundation import CFEqual


WECHAT_BUNDLE_ID = "com.tencent.xinWeChat"


@dataclass
class Message:
    sender: str
    content: str
    time: str = ""
    is_self: bool = False


@dataclass
class Contact:
    name: str
    remark: str = ""


@dataclass
class ChatSession:
    name: str
    last_message: str = ""
    unread: int = 0


def _run_applescript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript error: {result.stderr.strip()}")
    return result.stdout.strip()


def _get_wechat_pid() -> Optional[int]:
    apps = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID
    )
    for app in apps:
        if app.get("kCGWindowOwnerName") == "WeChat" or app.get("kCGWindowOwnerName") == "微信":
            return app["kCGWindowOwnerPID"]

    result = subprocess.run(
        ["pgrep", "-x", "WeChat"], capture_output=True, text=True
    )
    if result.returncode == 0 and result.stdout.strip():
        return int(result.stdout.strip().split("\n")[0])
    return None


def _ax_attr(element, attr: str):
    err, value = AXUIElementCopyAttributeValue(element, attr, None)
    if err == 0:
        return value
    return None


def _ax_attrs(element) -> list:
    err, names = AXUIElementCopyAttributeNames(element, None)
    if err == 0:
        return list(names)
    return []


def _ax_children(element) -> list:
    children = _ax_attr(element, "AXChildren")
    return list(children) if children else []


def _ax_role(element) -> str:
    return _ax_attr(element, "AXRole") or ""


def _ax_value(element) -> str:
    return _ax_attr(element, "AXValue") or ""


def _ax_title(element) -> str:
    return _ax_attr(element, "AXTitle") or ""


def _ax_description(element) -> str:
    return _ax_attr(element, "AXDescription") or ""


def _collect_texts(element, depth: int = 0, max_depth: int = 10) -> list[str]:
    """递归收集元素树中的所有文本"""
    if depth > max_depth:
        return []
    texts = []
    for getter in (_ax_value, _ax_title, _ax_description):
        val = getter(element)
        if val and isinstance(val, str) and val.strip():
            texts.append(val.strip())
    for child in _ax_children(element):
        texts.extend(_collect_texts(child, depth + 1, max_depth))
    return texts


class WeChatAutomation:
    """微信 macOS 客户端自动化控制"""

    def __init__(self):
        self._app_ref = None
        self._pid: Optional[int] = None

    def _ensure_connected(self):
        pid = _get_wechat_pid()
        if pid is None:
            raise RuntimeError("微信未运行，请先启动微信并登录")
        if pid != self._pid:
            self._pid = pid
            self._app_ref = AXUIElementCreateApplication(pid)

    def _activate_wechat(self):
        _run_applescript('tell application "WeChat" to activate')
        time.sleep(0.3)

    def _get_main_window(self):
        self._ensure_connected()
        windows = _ax_attr(self._app_ref, "AXWindows")
        if not windows or len(windows) == 0:
            raise RuntimeError("无法获取微信窗口，请确保微信已打开且未最小化")
        return windows[0]

    def _find_element_by_role(self, parent, role: str, max_depth: int = 8) -> list:
        """在控件树中查找指定角色的所有元素"""
        results = []
        self._find_element_by_role_recursive(parent, role, results, 0, max_depth)
        return results

    def _find_element_by_role_recursive(self, element, role: str, results: list, depth: int, max_depth: int):
        if depth > max_depth:
            return
        if _ax_role(element) == role:
            results.append(element)
        for child in _ax_children(element):
            self._find_element_by_role_recursive(child, role, results, depth + 1, max_depth)

    def _click_element(self, element):
        AXUIElementPerformAction(element, "AXPress")

    def _set_focus(self, element):
        AXUIElementSetAttributeValue(element, "AXFocused", True)

    def is_running(self) -> bool:
        return _get_wechat_pid() is not None

    def get_session_list(self) -> list[ChatSession]:
        """获取左侧会话列表"""
        self._ensure_connected()
        window = self._get_main_window()

        sessions = []
        rows = self._find_element_by_role(window, "AXCell")

        for row in rows:
            texts = _collect_texts(row, max_depth=5)
            if not texts:
                continue
            name = texts[0]
            last_msg = texts[1] if len(texts) > 1 else ""
            sessions.append(ChatSession(name=name, last_message=last_msg))

        return sessions

    def get_contacts(self) -> list[Contact]:
        """
        获取联系人列表
        通过 AppleScript 切换到通讯录 tab，然后读取列表
        """
        self._activate_wechat()
        _run_applescript('''
            tell application "System Events"
                tell process "WeChat"
                    -- Cmd+Shift+C 打开通讯录（如果有此快捷键）
                    -- 否则通过点击通讯录图标
                end tell
            end tell
        ''')
        time.sleep(0.5)

        window = self._get_main_window()
        contacts = []
        rows = self._find_element_by_role(window, "AXCell")
        seen = set()

        for row in rows:
            texts = _collect_texts(row, max_depth=5)
            if texts and texts[0] not in seen:
                seen.add(texts[0])
                contacts.append(Contact(name=texts[0]))

        return contacts

    def search_contact(self, keyword: str) -> list[Contact]:
        """通过微信搜索框搜索联系人"""
        self._activate_wechat()

        _run_applescript(f'''
            tell application "System Events"
                tell process "WeChat"
                    keystroke "f" using command down
                    delay 0.3
                    keystroke "{keyword}"
                    delay 0.8
                end tell
            end tell
        ''')

        window = self._get_main_window()
        time.sleep(0.5)
        contacts = []
        rows = self._find_element_by_role(window, "AXCell")

        for row in rows:
            texts = _collect_texts(row, max_depth=5)
            if texts:
                contacts.append(Contact(name=texts[0]))

        # 按 Esc 关闭搜索
        _run_applescript('''
            tell application "System Events"
                tell process "WeChat"
                    key code 53
                end tell
            end tell
        ''')

        return contacts

    def select_chat(self, name: str) -> bool:
        """通过搜索选中一个聊天对象"""
        self._activate_wechat()

        _run_applescript(f'''
            tell application "System Events"
                tell process "WeChat"
                    keystroke "f" using command down
                    delay 0.3
                    keystroke "{name}"
                    delay 0.8
                    keystroke return
                    delay 0.3
                end tell
            end tell
        ''')

        time.sleep(0.5)
        # 按 Esc 关闭搜索面板但保留聊天窗口
        _run_applescript('''
            tell application "System Events"
                tell process "WeChat"
                    key code 53
                end tell
            end tell
        ''')
        return True

    def get_messages(self, count: int = 20) -> list[Message]:
        """读取当前聊天窗口中的消息"""
        self._ensure_connected()
        window = self._get_main_window()

        messages = []
        scroll_areas = self._find_element_by_role(window, "AXScrollArea")

        # 聊天消息通常在最大的 ScrollArea 中
        chat_area = None
        for sa in scroll_areas:
            children = _ax_children(sa)
            if len(children) > 2:
                chat_area = sa
                break

        if not chat_area:
            chat_area = scroll_areas[-1] if scroll_areas else None

        if not chat_area:
            return messages

        rows = self._find_element_by_role(chat_area, "AXGroup")
        if not rows:
            rows = self._find_element_by_role(chat_area, "AXCell")

        for row in rows:
            texts = _collect_texts(row, max_depth=6)
            if not texts:
                continue

            # 尝试解析消息格式：通常包含发送者名和消息内容
            msg = self._parse_message_texts(texts)
            if msg:
                messages.append(msg)

        return messages[-count:] if len(messages) > count else messages

    def _parse_message_texts(self, texts: list[str]) -> Optional[Message]:
        """从控件文本列表中解析出一条消息"""
        if not texts:
            return None

        time_str = ""
        sender = ""
        content = ""

        time_pattern = re.compile(r'^\d{1,2}:\d{2}$|^\d{4}.*\d{1,2}:\d{2}$|^昨天|^前天|^星期')

        for t in texts:
            if time_pattern.match(t):
                time_str = t
            elif not sender and not content:
                sender = t
            else:
                content = t if not content else f"{content} {t}"

        if not content and sender:
            content = sender
            sender = ""

        if content:
            return Message(sender=sender, content=content, time=time_str)
        return None

    def send_message(self, text: str) -> bool:
        """在当前聊天窗口发送文本消息"""
        self._activate_wechat()

        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        _run_applescript(f'''
            tell application "System Events"
                tell process "WeChat"
                    set the clipboard to "{escaped}"
                    keystroke "v" using command down
                    delay 0.1
                    keystroke return
                end tell
            end tell
        ''')
        return True

    def send_file(self, file_path: str) -> bool:
        """在当前聊天窗口发送文件"""
        self._activate_wechat()

        _run_applescript(f'''
            tell application "System Events"
                tell process "WeChat"
                    -- 使用文件发送快捷方式或拖拽
                    set the clipboard to POSIX file "{file_path}"
                    keystroke "v" using command down
                    delay 0.5
                    keystroke return
                end tell
            end tell
        ''')
        return True

    def send_message_to(self, name: str, text: str) -> bool:
        """搜索联系人并发送消息（组合操作）"""
        if not self.select_chat(name):
            return False
        time.sleep(0.3)
        return self.send_message(text)

    def get_current_chat_name(self) -> str:
        """获取当前聊天对象的名称"""
        self._ensure_connected()
        window = self._get_main_window()

        static_texts = self._find_element_by_role(window, "AXStaticText")
        for st in static_texts:
            title = _ax_value(st) or _ax_title(st)
            if title and len(title) < 30:
                return title

        return ""
