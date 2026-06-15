"""
终端渲染 — 用 rich 美化输出

@author buchi
@since 2026-06-15
"""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns

console = Console()

VERSION = "0.1.0"


def render_banner(server_url: str):
    banner = Text()
    banner.append("wchat", style="bold cyan")
    banner.append(f" v{VERSION}\n", style="dim")
    banner.append(f"已连接: {server_url}\n", style="green")
    banner.append("输入 /help 查看可用命令", style="dim")
    console.print(Panel(banner, border_style="cyan", expand=False))


def render_help():
    table = Table(title="可用命令", show_header=True, header_style="bold cyan", expand=False)
    table.add_column("命令", style="cyan", min_width=20)
    table.add_column("说明", style="white")
    table.add_row("/contacts, /c", "列出联系人")
    table.add_row("/chat <名字>", "进入与某人的聊天")
    table.add_row("/chats", "列出最近会话（含未读数）")
    table.add_row("/back, /b", "退出当前聊天，回到主界面")
    table.add_row("/search <关键词>", "搜索联系人/群")
    table.add_row("/file <路径>", "在当前聊天中发送文件")
    table.add_row("/history [n]", "查看更多历史消息")
    table.add_row("/listen", "开启/关闭后台消息监听")
    table.add_row("/status", "查看连接状态")
    table.add_row("/help, /h", "显示此帮助")
    table.add_row("/quit, /q", "退出")
    console.print(table)


def render_contacts(contacts: list[dict]):
    if not contacts:
        console.print("[dim]暂无联系人[/dim]")
        return
    table = Table(title="联系人", show_header=True, header_style="bold cyan", expand=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("名称", style="white")
    table.add_column("备注", style="dim")
    for i, c in enumerate(contacts, 1):
        table.add_row(str(i), c["name"], c.get("remark", ""))
    console.print(table)


def render_chats(chats: list[dict]):
    if not chats:
        console.print("[dim]暂无会话[/dim]")
        return
    table = Table(title="最近会话", show_header=True, header_style="bold cyan", expand=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("名称", style="white")
    table.add_column("最后消息", style="dim", max_width=40)
    table.add_column("未读", style="red", width=6)
    for i, c in enumerate(chats, 1):
        unread = f"[red]{c['unread']}[/red]" if c.get("unread") else ""
        table.add_row(str(i), c["name"], c.get("last_message", ""), unread)
    console.print(table)


def render_chat_header(name: str):
    console.print(f"\n[bold cyan]── 与「{name}」的对话 ──[/bold cyan]\n")


def render_messages(messages: list[dict]):
    if not messages:
        console.print("[dim]暂无消息[/dim]")
        return
    for msg in messages:
        time_str = f"[dim][{msg.get('time', '')}][/dim] " if msg.get("time") else ""
        sender = msg.get("sender", "")
        content = msg.get("content", "")
        is_self = msg.get("is_self", False)
        if is_self or not sender:
            console.print(f"  {time_str}[bold green]我[/bold green]: {content}")
        else:
            console.print(f"  {time_str}[bold blue]{sender}[/bold blue]: {content}")


def render_sent_ok():
    console.print("[green]  ✓ 已发送[/green]")


def render_sent_fail(reason: str = ""):
    msg = f"  ✗ 发送失败: {reason}" if reason else "  ✗ 发送失败"
    console.print(f"[red]{msg}[/red]")


def render_notification(messages: list[dict]):
    for msg in messages:
        sender = msg.get("sender", "未知")
        content = msg.get("content", "")
        preview = content[:40] + "..." if len(content) > 40 else content
        console.print(f"\n[yellow]📨 新消息 — {sender}: {preview}[/yellow]")


def render_status(server_url: str, wechat_running: bool, listening: bool):
    table = Table(title="连接状态", show_header=False, expand=False)
    table.add_column("项", style="cyan")
    table.add_column("值", style="white")
    table.add_row("服务端", server_url)
    status = "[green]运行中[/green]" if wechat_running else "[red]未运行[/red]"
    table.add_row("微信状态", status)
    listen_status = "[green]已开启[/green]" if listening else "[dim]未开启[/dim]"
    table.add_row("消息监听", listen_status)
    console.print(table)


def render_error(msg: str):
    console.print(f"[red]错误: {msg}[/red]")


def render_info(msg: str):
    console.print(f"[dim]{msg}[/dim]")
