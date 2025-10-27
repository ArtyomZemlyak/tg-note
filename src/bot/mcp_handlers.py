"""
MCP Server Configuration Handlers for Telegram Bot
Allows users to manage MCP server configurations through Telegram
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlsplit, urlunsplit

from loguru import logger
from telebot.async_telebot import AsyncTeleBot
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.bot.utils import escape_markdown
from src.mcp.registry.manager import MCPServersManager

from .mcp_hub_client import MCPHubClient, MCPHubError


class MCPHandlers:
    """Telegram handlers for MCP server management"""

    def __init__(self, bot: AsyncTeleBot, mcp_manager: Optional[MCPServersManager] = None):
        """
        Initialize MCP handlers

        Args:
            bot: Telegram bot instance
            mcp_manager: MCP servers manager (optional, creates new if not provided)
        """
        self.bot = bot
        self.mcp_manager = mcp_manager or MCPServersManager()
        # Track users waiting for JSON input: user_id -> waiting state
        self.waiting_for_json: Dict[int, bool] = {}
        # Resolve MCP Hub base URL for HTTP registry API if in Docker mode
        self._hub_base = None
        self._mcp_client: Optional[MCPHubClient] = None
        mcp_hub_url = os.environ.get("MCP_HUB_URL")
        if mcp_hub_url:
            parts = urlsplit(mcp_hub_url)
            self._hub_base = urlunsplit((parts.scheme, parts.netloc, "", "", ""))
            self._mcp_client = MCPHubClient(self._hub_base)

    async def register_handlers_async(self):
        """Register all MCP handlers"""
        # MCP management commands
        self.bot.message_handler(commands=["addmcpserver"])(self.handle_add_mcp_server)
        self.bot.message_handler(commands=["listmcpservers"])(self.handle_list_mcp_servers)
        self.bot.message_handler(commands=["mcpstatus"])(self.handle_mcp_status)
        self.bot.message_handler(commands=["enablemcp"])(self.handle_enable_mcp)
        self.bot.message_handler(commands=["disablemcp"])(self.handle_disable_mcp)
        self.bot.message_handler(commands=["removemcp"])(self.handle_remove_mcp)
        # Support uploading JSON file to add server
        self.bot.message_handler(content_types=["document"], func=lambda m: self._is_json_file(m))(
            self.handle_add_mcp_server_file
        )

        # Text message handler for JSON input
        self.bot.message_handler(func=lambda m: m.from_user.id in self.waiting_for_json)(
            self.handle_json_input
        )

        # Callback query handlers for inline keyboards
        self.bot.callback_query_handler(func=lambda call: call.data.startswith("mcp:"))(
            self.handle_mcp_callback
        )

    async def handle_add_mcp_server(self, message: Message) -> None:
        """
        Handle /addmcpserver command - add a new MCP server configuration

        Usage: /addmcpserver or /addmcpserver <json>
        """
        logger.info(f"Add MCP server requested by user {message.from_user.id}")

        # Check if JSON is provided in the command
        args = message.text.split(maxsplit=1)

        if len(args) > 1:
            # JSON provided directly
            json_content = args[1].strip()
            await self._process_json_config(message, json_content)
        else:
            # Prompt for JSON input
            self.waiting_for_json[message.from_user.id] = True

            help_text = (
                "🔧 **Добавить MCP сервер**\n\n"
                "Пожалуйста, отправьте конфигурацию MCP сервера в формате JSON.\n\n"
                "**Пример:**\n"
                "```json\n"
                "{\n"
                '  "name": "my-mcp-server",\n'
                '  "description": "Мой пользовательский MCP сервер",\n'
                '  "command": "python",\n'
                '  "args": ["-m", "my_package.server"],\n'
                '  "env": {\n'
                '    "API_KEY": "your-api-key"\n'
                "  },\n"
                '  "enabled": true\n'
                "}\n"
                "```\n\n"
                "**Обязательные поля:**\n"
                "• `name` - Уникальное имя сервера\n"
                "• `description` - Описание сервера\n"
                "• `command` - Команда для запуска\n"
                "• `args` - Аргументы команды (массив)\n\n"
                "**Необязательные поля:**\n"
                "• `env` - Переменные окружения (объект)\n"
                "• `working_dir` - Рабочая директория\n"
                "• `enabled` - Включить сразу (по умолчанию: true)\n\n"
                "Отправьте /cancel для отмены."
            )

            await self.bot.reply_to(message, help_text, parse_mode="Markdown")
            if self._hub_base:
                await self.bot.send_message(
                    message.chat.id,
                    f"Обнаружен режим Hub. Вы также можете загрузить .json файл для регистрации через hub.",
                )

    async def handle_json_input(self, message: Message) -> None:
        """Handle JSON input for MCP server configuration"""
        user_id = message.from_user.id

        # Check if user is waiting for input
        if user_id not in self.waiting_for_json:
            return

        # Check for cancel
        if message.text and message.text.strip().lower() in ["/cancel", "cancel"]:
            del self.waiting_for_json[user_id]
            await self.bot.reply_to(message, "❌ Отменено")
            return

        json_content = message.text.strip()

        # Clear waiting state
        del self.waiting_for_json[user_id]

        await self._process_json_config(message, json_content)

    async def _process_json_config(self, message: Message, json_content: str) -> None:
        """Process JSON configuration and add MCP server"""
        try:
            # Try to extract JSON from code blocks if present
            if "```" in json_content:
                # Extract JSON from markdown code block
                parts = json_content.split("```")
                for part in parts:
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if part.startswith("{") or part.startswith("["):
                        json_content = part
                        break

            # Add server via MCP Hub HTTP API if available, else local registry
            success = False
            if self._mcp_client:
                try:
                    result = await self._mcp_client.registry_register_server(
                        json.loads(json_content)
                    )
                    if result.get("success"):
                        success = True
                        server_name = json.loads(json_content).get("name", "unknown")
                        logger.info(f"✅ [HTTP] Registered server via API: {server_name}")
                    else:
                        # Fall back to local manager on failure
                        success = self.mcp_manager.add_server_from_json(json_content)
                except MCPHubError as e:
                    logger.warning(f"⚠️ [HTTP] MCP Hub error: {e}, falling back to local registry")
                    success = self.mcp_manager.add_server_from_json(json_content)
                except Exception as e:
                    logger.warning(f"⚠️ [HTTP] Exception: {e}, falling back to local registry")
                    success = self.mcp_manager.add_server_from_json(json_content)
            else:
                success = self.mcp_manager.add_server_from_json(json_content)

            if success:
                await self.bot.reply_to(
                    message,
                    "✅ Конфигурация MCP сервера успешно добавлена!\n\n"
                    "Используйте /listmcpservers для просмотра всех серверов.",
                )
            else:
                await self.bot.reply_to(
                    message,
                    "❌ Не удалось добавить MCP сервер. Пожалуйста, проверьте:\n"
                    "• Формат JSON корректен\n"
                    "• Имя сервера уникально\n"
                    "• Все обязательные поля заполнены\n\n"
                    "Используйте /addmcpserver для повторной попытки.",
                )

        except Exception as e:
            logger.error(f"Error processing MCP JSON config: {e}", exc_info=True)
            await self.bot.reply_to(
                message,
                f"❌ Ошибка: {escape_markdown(str(e))}\n\n"
                "Пожалуйста, проверьте синтаксис JSON и попробуйте снова.",
                parse_mode="Markdown",
            )

    async def handle_list_mcp_servers(self, message: Message) -> None:
        """Handle /listmcpservers command - list all MCP servers"""
        logger.info(f"List MCP servers requested by user {message.from_user.id}")

        # Prefer hub endpoint if available
        all_servers = None
        if self._mcp_client:
            try:
                result = await self._mcp_client.registry_list_servers()
                all_servers = []
                for srv in result.get("servers", []):
                    # Minimal adapter object
                    from dataclasses import make_dataclass

                    MCPServer = make_dataclass(
                        "MCPServer",
                        [
                            ("name", str),
                            ("description", str),
                            ("command", str),
                            ("enabled", bool),
                        ],
                    )
                    all_servers.append(
                        MCPServer(
                            name=srv.get("name", ""),
                            description=srv.get("description", ""),
                            command=srv.get("command", ""),
                            enabled=bool(srv.get("enabled", False)),
                        )
                    )
            except MCPHubError as e:
                logger.warning(f"Failed to fetch servers from hub: {e}")
                all_servers = None
            except Exception as e:
                logger.warning(f"Failed to fetch servers from hub: {e}")
                all_servers = None

        if all_servers is None:
            # Fallback to local registry
            all_servers = self.mcp_manager.get_all_servers()

        if not all_servers:
            await self.bot.reply_to(
                message,
                "📋 Нет настроенных MCP серверов.\n\n" "Используйте /addmcpserver для добавления нового сервера.",
            )
            return

        # Build server list
        lines = ["🔧 **MCP Серверы**\n"]

        # Create inline keyboard for actions
        keyboard = InlineKeyboardMarkup()
        keyboard.row_width = 1

        for server in sorted(all_servers, key=lambda s: s.name):
            status_icon = "✅" if server.enabled else "❌"
            status_text = "включен" if server.enabled else "отключен"

            lines.append(
                f"{status_icon} **{escape_markdown(server.name)}**\n"
                f"   {escape_markdown(server.description)}\n"
                f"   Command: `{escape_markdown(server.command)}`\n"
                f"   Status: {status_text}\n"
            )

            # Add toggle button
            if server.enabled:
                keyboard.add(
                    InlineKeyboardButton(
                        f"🔴 Отключить {server.name}", callback_data=f"mcp:disable:{server.name}"
                    )
                )
            else:
                keyboard.add(
                    InlineKeyboardButton(
                        f"🟢 Включить {server.name}", callback_data=f"mcp:enable:{server.name}"
                    )
                )

        # Add refresh and add buttons
        keyboard.add(
            InlineKeyboardButton("🔄 Обновить", callback_data="mcp:list"),
            InlineKeyboardButton("➕ Добавить новый", callback_data="mcp:add"),
        )

        text = "\n".join(lines)

        await self.bot.send_message(
            message.chat.id, text, reply_markup=keyboard, parse_mode="Markdown"
        )

    async def handle_mcp_status(self, message: Message) -> None:
        """Handle /mcpstatus command - show MCP servers summary"""
        logger.info(f"MCP status requested by user {message.from_user.id}")

        # Prefer hub endpoint for summary
        summary = None
        if self._mcp_client:
            try:
                result = await self._mcp_client.registry_list_servers()
                total = int(result.get("total", 0))
                enabled = sum(1 for s in result.get("servers", []) if s.get("enabled"))
                summary = {
                    "total": total,
                    "enabled": enabled,
                    "disabled": total - enabled,
                }
            except MCPHubError as e:
                logger.warning(f"Failed to fetch status from hub: {e}")
                summary = None
            except Exception as e:
                logger.warning(f"Failed to fetch status from hub: {e}")
                summary = None
        if summary is None:
            summary = self.mcp_manager.get_servers_summary()

        status_text = (
            "📊 **Статус MCP серверов**\n\n"
            f"Всего серверов: {summary['total']}\n"
            f"✅ Включено: {summary['enabled']}\n"
            f"❌ Отключено: {summary['disabled']}\n\n"
            "Используйте /listmcpservers для просмотра деталей."
        )

        await self.bot.reply_to(message, status_text, parse_mode="Markdown")

    async def handle_enable_mcp(self, message: Message) -> None:
        """Handle /enablemcp command - enable an MCP server"""
        logger.info(f"Enable MCP server requested by user {message.from_user.id}")

        args = message.text.split(maxsplit=1)

        if len(args) < 2:
            await self.bot.reply_to(
                message,
                "❌ Использование: `/enablemcp <имя_сервера>`\n\n"
                "Пример: `/enablemcp my-server`\n\n"
                "Используйте /listmcpservers для просмотра доступных серверов.",
                parse_mode="Markdown",
            )
            return

        server_name = args[1].strip()

        success = False
        if self._mcp_client:
            try:
                result = await self._mcp_client.registry_enable_server(server_name)
                success = result.get("success", False)
            except MCPHubError as e:
                logger.warning(f"Failed to enable server via hub: {e}")
                success = False
            except Exception as e:
                logger.warning(f"Failed to enable server via hub: {e}")
                success = False
        if not success:
            success = self.mcp_manager.enable_server(server_name)

        if success:
            await self.bot.reply_to(
                message,
                f"✅ MCP server `{escape_markdown(server_name)}` enabled!",
                parse_mode="Markdown",
            )
        else:
            await self.bot.reply_to(
                message,
                f"❌ Не удалось включить сервер `{escape_markdown(server_name)}`.\n"
                f"Сервер может не существовать. Используйте /listmcpservers для просмотра доступных серверов.",
                parse_mode="Markdown",
            )

    async def handle_disable_mcp(self, message: Message) -> None:
        """Handle /disablemcp command - disable an MCP server"""
        logger.info(f"Disable MCP server requested by user {message.from_user.id}")

        args = message.text.split(maxsplit=1)

        if len(args) < 2:
            await self.bot.reply_to(
                message,
                "❌ Использование: `/disablemcp <имя_сервера>`\n\n"
                "Пример: `/disablemcp my-server`\n\n"
                "Используйте /listmcpservers для просмотра доступных серверов.",
                parse_mode="Markdown",
            )
            return

        server_name = args[1].strip()

        success = False
        if self._mcp_client:
            try:
                result = await self._mcp_client.registry_disable_server(server_name)
                success = result.get("success", False)
            except MCPHubError as e:
                logger.warning(f"Failed to disable server via hub: {e}")
                success = False
            except Exception as e:
                logger.warning(f"Failed to disable server via hub: {e}")
                success = False
        if not success:
            success = self.mcp_manager.disable_server(server_name)

        if success:
            await self.bot.reply_to(
                message,
                f"✅ MCP server `{escape_markdown(server_name)}` disabled!",
                parse_mode="Markdown",
            )
        else:
            await self.bot.reply_to(
                message,
                f"❌ Не удалось отключить сервер `{escape_markdown(server_name)}`.\n"
                f"Сервер может не существовать. Используйте /listmcpservers для просмотра доступных серверов.",
                parse_mode="Markdown",
            )

    async def handle_remove_mcp(self, message: Message) -> None:
        """Handle /removemcp command - remove an MCP server"""
        logger.info(f"Remove MCP server requested by user {message.from_user.id}")

        args = message.text.split(maxsplit=1)

        if len(args) < 2:
            await self.bot.reply_to(
                message,
                "❌ Использование: `/removemcp <имя_сервера>`\n\n"
                "Пример: `/removemcp my-server`\n\n"
                "⚠️ Это приведет к безвозвратному удалению конфигурации сервера.\n"
                "Используйте /listmcpservers для просмотра доступных серверов.",
                parse_mode="Markdown",
            )
            return

        server_name = args[1].strip()

        # Get server info for confirmation
        server = self.mcp_manager.get_server(server_name)

        if not server:
            await self.bot.reply_to(
                message,
                f"❌ Сервер `{escape_markdown(server_name)}` не найден.\n"
                f"Используйте /listmcpservers для просмотра доступных серверов.",
                parse_mode="Markdown",
            )
            return

        # Create confirmation keyboard
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                "✅ Yes, delete", callback_data=f"mcp:confirm_remove:{server_name}"
            ),
            InlineKeyboardButton("❌ Cancel", callback_data="mcp:cancel_remove"),
        )

        await self.bot.reply_to(
            message,
            f"⚠️ **Подтверждение удаления**\n\n"
            f"Вы уверены, что хотите удалить MCP сервер `{escape_markdown(server_name)}`?\n\n"
            f"Описание: {escape_markdown(server.description)}\n"
            f"Это действие нельзя отменить.",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

    async def handle_mcp_callback(self, call: CallbackQuery) -> None:
        """Handle callback queries from MCP inline keyboards"""
        try:
            # Parse callback data
            parts = call.data.split(":", 2)

            if len(parts) < 2:
                await self.bot.answer_callback_query(call.id, "Неверный callback")
                return

            action = parts[1]

            if action == "list":
                # Refresh server list
                await self._refresh_server_list(call)

            elif action == "add":
                # Prompt to add new server
                await self.bot.answer_callback_query(call.id)
                await self.bot.send_message(
                    call.message.chat.id, "Используйте /addmcpserver для добавления новой конфигурации MCP сервера."
                )

            elif action == "enable":
                # Enable server
                server_name = parts[2]
                success = self.mcp_manager.enable_server(server_name)

                if success:
                    await self.bot.answer_callback_query(
                        call.id, f"✅ Сервер {server_name} включен!", show_alert=True
                    )
                    await self._refresh_server_list(call)
                else:
                    await self.bot.answer_callback_query(
                        call.id, f"❌ Не удалось включить {server_name}", show_alert=True
                    )

            elif action == "disable":
                # Disable server
                server_name = parts[2]
                success = self.mcp_manager.disable_server(server_name)

                if success:
                    await self.bot.answer_callback_query(
                        call.id, f"✅ Сервер {server_name} отключен!", show_alert=True
                    )
                    await self._refresh_server_list(call)
                else:
                    await self.bot.answer_callback_query(
                        call.id, f"❌ Не удалось отключить {server_name}", show_alert=True
                    )

            elif action == "confirm_remove":
                # Remove server
                server_name = parts[2]
                success = False
                if self._mcp_client:
                    try:
                        result = await self._mcp_client.registry_remove_server(server_name)
                        success = result.get("success", False)
                    except MCPHubError as e:
                        logger.warning(f"Failed to remove server via hub: {e}")
                        success = False
                    except Exception as e:
                        logger.warning(f"Failed to remove server via hub: {e}")
                        success = False
                if not success:
                    success = self.mcp_manager.remove_server(server_name)

                if success:
                    await self.bot.answer_callback_query(
                        call.id, f"✅ Сервер {server_name} удален!", show_alert=True
                    )
                    # Delete confirmation message and show updated list
                    await self.bot.delete_message(call.message.chat.id, call.message.message_id)
                    # Show updated list
                    message = call.message
                    await self.handle_list_mcp_servers(message)
                else:
                    await self.bot.answer_callback_query(
                        call.id, f"❌ Не удалось удалить {server_name}", show_alert=True
                    )

            elif action == "cancel_remove":
                # Cancel removal
                await self.bot.answer_callback_query(call.id, "Отменено")
                await self.bot.delete_message(call.message.chat.id, call.message.message_id)

            else:
                await self.bot.answer_callback_query(call.id, "Неизвестное действие")

        except Exception as e:
            logger.error(f"Error handling MCP callback: {e}", exc_info=True)
            await self.bot.answer_callback_query(call.id, f"Ошибка: {str(e)}")

    async def _refresh_server_list(self, call: CallbackQuery) -> None:
        """Refresh the server list display"""
        # Get all servers
        all_servers = self.mcp_manager.get_all_servers()

        if not all_servers:
            text = "📋 Нет настроенных MCP серверов."
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("➕ Добавить новый", callback_data="mcp:add"))
        else:
            # Build server list
            lines = ["🔧 **MCP Servers**\n"]

            # Create inline keyboard for actions
            keyboard = InlineKeyboardMarkup()
            keyboard.row_width = 1

            for server in sorted(all_servers, key=lambda s: s.name):
                status_icon = "✅" if server.enabled else "❌"
                status_text = "enabled" if server.enabled else "disabled"

                lines.append(
                    f"{status_icon} **{escape_markdown(server.name)}**\n"
                    f"   {escape_markdown(server.description)}\n"
                    f"   Command: `{escape_markdown(server.command)}`\n"
                    f"   Status: {status_text}\n"
                )

                # Add toggle button
                if server.enabled:
                    keyboard.add(
                        InlineKeyboardButton(
                            f"🔴 Disable {server.name}", callback_data=f"mcp:disable:{server.name}"
                        )
                    )
                else:
                    keyboard.add(
                        InlineKeyboardButton(
                            f"🟢 Enable {server.name}", callback_data=f"mcp:enable:{server.name}"
                        )
                    )

            # Add refresh and add buttons
            keyboard.add(
                InlineKeyboardButton("🔄 Refresh", callback_data="mcp:list"),
                InlineKeyboardButton("➕ Add New", callback_data="mcp:add"),
            )

            text = "\n".join(lines)

        try:
            await self.bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
        except Exception as e:
            # If Markdown parsing fails, send without formatting
            if "can't parse entities" in str(e).lower():
                logger.warning(
                    f"Ошибка разбора Markdown в списке MCP, отправка без форматирования: {e}"
                )
                await self.bot.edit_message_text(
                    text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard,
                    parse_mode=None,
                )
            else:
                raise

        await self.bot.answer_callback_query(call.id)

    def _is_json_file(self, message: Message) -> bool:
        doc = getattr(message, "document", None)
        if not doc:
            return False
        file_name = (doc.file_name or "").lower()
        return file_name.endswith(".json") and (
            message.caption and message.caption.strip().lower().startswith("/addmcpserver")
        )

    async def handle_add_mcp_server_file(self, message: Message) -> None:
        """Handle uploaded JSON file with caption /addmcpserver"""
        try:
            file_info = await self.bot.get_file(message.document.file_id)
            file_bytes = await self.bot.download_file(file_info.file_path)
            json_content = file_bytes.decode("utf-8")
            await self._process_json_config(message, json_content)
        except Exception as e:
            await self.bot.reply_to(message, f"❌ Ошибка чтения загруженного файла: {str(e)}")
