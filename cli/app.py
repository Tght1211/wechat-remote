"""
wchat — Claude Code 风格的微信 REPL 客户端

@author buchi
@since 2026-06-15
"""
import asyncio
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from pathlib import Path

from .config import Config
from .client import WeChatClient
from .commands import handle_command, AppState
from .completer import WeChatCompleter
from . import renderer


HISTORY_FILE = Path.home() / ".wchat_history"


async def _setup_config() -> Config:
    config = Config.load()
    need_save = False

    if not config.server_url or config.server_url == "http://localhost:9100":
        renderer.console.print("[cyan]首次配置 wchat[/cyan]")
        renderer.console.print("请输入远程服务端地址（例如 http://192.168.1.100:9100）")
        renderer.console.print("直接回车使用默认值 http://localhost:9100")
        url = input("服务端地址: ").strip()
        if url:
            config.server_url = url
        need_save = True

    if not config.token:
        renderer.console.print("请输入服务端 Token（启动服务端时会显示）")
        token = input("Token: ").strip()
        if token:
            config.token = token
            need_save = True

    if need_save:
        config.save()
        renderer.render_info(f"配置已保存到 {Config.CONFIG_FILE}")

    return config


async def _preload_contacts(client: WeChatClient, completer: WeChatCompleter):
    """后台预加载联系人列表用于 Tab 补全"""
    try:
        contacts = await client.get_contacts()
        names = [c["name"] for c in contacts]
        completer.update_contacts(names)
    except Exception:
        pass


async def async_main():
    config = await _setup_config()
    client = WeChatClient(config)
    state = AppState()
    completer = WeChatCompleter()

    # 验证连接
    try:
        health = await client.health()
        if not health.get("wechat_running"):
            renderer.render_error("远程微信未运行，部分功能可能不可用")
    except Exception as e:
        renderer.render_error(f"无法连接服务端 {config.server_url}: {e}")
        renderer.render_info("请确认服务端已启动，或运行 wchat 时重新配置")
        retry = input("是否继续使用？(y/N): ").strip().lower()
        if retry != "y":
            return

    renderer.render_banner(config.server_url)

    # 后台加载联系人
    asyncio.create_task(_preload_contacts(client, completer))

    session: PromptSession = PromptSession(
        history=FileHistory(str(HISTORY_FILE)),
        completer=completer,
        complete_while_typing=False,
    )

    try:
        with patch_stdout():
            while True:
                try:
                    prompt = state.prompt_text
                    user_input = await session.prompt_async(prompt)
                    should_continue = await handle_command(user_input, client, state)
                    if not should_continue:
                        break
                except KeyboardInterrupt:
                    if state.in_chat:
                        renderer.render_info(f"已退出「{state.current_chat}」的聊天")
                        state.current_chat = None
                    else:
                        renderer.render_info("按 Ctrl+C 再次退出，或输入 /quit")
                        try:
                            user_input = await session.prompt_async("> ")
                            if not user_input.strip():
                                continue
                            should_continue = await handle_command(user_input, client, state)
                            if not should_continue:
                                break
                        except KeyboardInterrupt:
                            renderer.render_info("再见!")
                            break
                except EOFError:
                    break
    finally:
        await client.close()


def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
