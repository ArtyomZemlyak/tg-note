"""
MCP Server Configuration Handlers for Telegram Bot
Allows users to manage MCP server configurations through Telegram
"""

from pathlib import Path
from typing import Dict, Optional

from loguru import logger
from telebot.async_telebot import AsyncTeleBot
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.bot.utils import escape_markdown
from src.mcp.registry.manager import MCPServersManager


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

    async def register_handlers_async(self):
        """Register all MCP handlers"""
        # MCP management commands
        self.bot.message_handler(commands=["addmcpserver"])(self.handle_add_mcp_server)
        self.bot.message_handler(commands=["listmcpservers"])(self.handle_list_mcp_servers)
        self.bot.message_handler(commands=["mcpstatus"])(self.handle_mcp_status)
        self.bot.message_handler(commands=["enablemcp"])(self.handle_enable_mcp)
        self.bot.message_handler(commands=["disablemcp"])(self.handle_disable_mcp)
        self.bot.message_handler(commands=["removemcp"])(self.handle_remove_mcp)

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
                "🔧 **Add MCP Server**\n\n"
                "Please send the MCP server configuration in JSON format.\n\n"
                "**Example:**\n"
                "```json\n"
                "{\n"
                '  "name": "my-mcp-server",\n'
                '  "description": "My custom MCP server",\n'
                '  "command": "python",\n'
                '  "args": ["-m", "my_package.server"],\n'
                '  "env": {\n'
                '    "API_KEY": "your-api-key"\n'
                "  },\n"
                '  "enabled": true\n'
                "}\n"
                "```\n\n"
                "**Required fields:**\n"
                "• `name` - Unique server name\n"
                "• `description` - Server description\n"
                "• `command` - Executable command\n"
                "• `args` - Command arguments (array)\n\n"
                "**Optional fields:**\n"
                "• `env` - Environment variables (object)\n"
                "• `working_dir` - Working directory\n"
                "• `enabled` - Enable immediately (default: true)\n\n"
                "Send /cancel to cancel."
            )

            await self.bot.reply_to(message, help_text, parse_mode="Markdown")

    async def handle_json_input(self, message: Message) -> None:
        """Handle JSON input for MCP server configuration"""
        user_id = message.from_user.id

        # Check if user is waiting for input
        if user_id not in self.waiting_for_json:
            return

        # Check for cancel
        if message.text and message.text.strip().lower() in ["/cancel", "cancel"]:
            del self.waiting_for_json[user_id]
            await self.bot.reply_to(message, "❌ Cancelled")
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

            # Add server via manager
            success = self.mcp_manager.add_server_from_json(json_content)

            if success:
                await self.bot.reply_to(
                    message,
                    "✅ MCP server configuration added successfully!\n\n"
                    "Use /listmcpservers to see all servers.",
                )
            else:
                await self.bot.reply_to(
                    message,
                    "❌ Failed to add MCP server. Please check:\n"
                    "• JSON format is valid\n"
                    "• Server name is unique\n"
                    "• Required fields are present\n\n"
                    "Use /addmcpserver to try again.",
                )

        except Exception as e:
            logger.error(f"Error processing MCP JSON config: {e}", exc_info=True)
            await self.bot.reply_to(
                message,
                f"❌ Error: {escape_markdown(str(e))}\n\n"
                "Please check your JSON syntax and try again.",
                parse_mode="Markdown",
            )

    async def handle_list_mcp_servers(self, message: Message) -> None:
        """Handle /listmcpservers command - list all MCP servers"""
        logger.info(f"List MCP servers requested by user {message.from_user.id}")

        # Get all servers
        all_servers = self.mcp_manager.get_all_servers()

        if not all_servers:
            await self.bot.reply_to(
                message,
                "📋 No MCP servers configured.\n\n" "Use /addmcpserver to add a new server.",
            )
            return

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

        await self.bot.send_message(
            message.chat.id, text, reply_markup=keyboard, parse_mode="Markdown"
        )

    async def handle_mcp_status(self, message: Message) -> None:
        """Handle /mcpstatus command - show MCP servers summary"""
        logger.info(f"MCP status requested by user {message.from_user.id}")

        summary = self.mcp_manager.get_servers_summary()

        status_text = (
            "📊 **MCP Servers Status**\n\n"
            f"Total servers: {summary['total']}\n"
            f"✅ Enabled: {summary['enabled']}\n"
            f"❌ Disabled: {summary['disabled']}\n\n"
            "Use /listmcpservers to see details."
        )

        await self.bot.reply_to(message, status_text, parse_mode="Markdown")

    async def handle_enable_mcp(self, message: Message) -> None:
        """Handle /enablemcp command - enable an MCP server"""
        logger.info(f"Enable MCP server requested by user {message.from_user.id}")

        args = message.text.split(maxsplit=1)

        if len(args) < 2:
            await self.bot.reply_to(
                message,
                "❌ Usage: `/enablemcp <server_name>`\n\n"
                "Example: `/enablemcp my-server`\n\n"
                "Use /listmcpservers to see available servers.",
                parse_mode="Markdown",
            )
            return

        server_name = args[1].strip()

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
                f"❌ Failed to enable server `{escape_markdown(server_name)}`.\n"
                f"Server may not exist. Use /listmcpservers to see available servers.",
                parse_mode="Markdown",
            )

    async def handle_disable_mcp(self, message: Message) -> None:
        """Handle /disablemcp command - disable an MCP server"""
        logger.info(f"Disable MCP server requested by user {message.from_user.id}")

        args = message.text.split(maxsplit=1)

        if len(args) < 2:
            await self.bot.reply_to(
                message,
                "❌ Usage: `/disablemcp <server_name>`\n\n"
                "Example: `/disablemcp my-server`\n\n"
                "Use /listmcpservers to see available servers.",
                parse_mode="Markdown",
            )
            return

        server_name = args[1].strip()

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
                f"❌ Failed to disable server `{escape_markdown(server_name)}`.\n"
                f"Server may not exist. Use /listmcpservers to see available servers.",
                parse_mode="Markdown",
            )

    async def handle_remove_mcp(self, message: Message) -> None:
        """Handle /removemcp command - remove an MCP server"""
        logger.info(f"Remove MCP server requested by user {message.from_user.id}")

        args = message.text.split(maxsplit=1)

        if len(args) < 2:
            await self.bot.reply_to(
                message,
                "❌ Usage: `/removemcp <server_name>`\n\n"
                "Example: `/removemcp my-server`\n\n"
                "⚠️ This will permanently delete the server configuration.\n"
                "Use /listmcpservers to see available servers.",
                parse_mode="Markdown",
            )
            return

        server_name = args[1].strip()

        # Get server info for confirmation
        server = self.mcp_manager.get_server(server_name)

        if not server:
            await self.bot.reply_to(
                message,
                f"❌ Server `{escape_markdown(server_name)}` not found.\n"
                f"Use /listmcpservers to see available servers.",
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
            f"⚠️ **Confirm Deletion**\n\n"
            f"Are you sure you want to delete MCP server `{escape_markdown(server_name)}`?\n\n"
            f"Description: {escape_markdown(server.description)}\n"
            f"This action cannot be undone.",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

    async def handle_mcp_callback(self, call: CallbackQuery) -> None:
        """Handle callback queries from MCP inline keyboards"""
        try:
            # Parse callback data
            parts = call.data.split(":", 2)

            if len(parts) < 2:
                await self.bot.answer_callback_query(call.id, "Invalid callback")
                return

            action = parts[1]

            if action == "list":
                # Refresh server list
                await self._refresh_server_list(call)

            elif action == "add":
                # Prompt to add new server
                await self.bot.answer_callback_query(call.id)
                await self.bot.send_message(
                    call.message.chat.id, "Use /addmcpserver to add a new MCP server configuration."
                )

            elif action == "enable":
                # Enable server
                server_name = parts[2]
                success = self.mcp_manager.enable_server(server_name)

                if success:
                    await self.bot.answer_callback_query(
                        call.id, f"✅ Server {server_name} enabled!", show_alert=True
                    )
                    await self._refresh_server_list(call)
                else:
                    await self.bot.answer_callback_query(
                        call.id, f"❌ Failed to enable {server_name}", show_alert=True
                    )

            elif action == "disable":
                # Disable server
                server_name = parts[2]
                success = self.mcp_manager.disable_server(server_name)

                if success:
                    await self.bot.answer_callback_query(
                        call.id, f"✅ Server {server_name} disabled!", show_alert=True
                    )
                    await self._refresh_server_list(call)
                else:
                    await self.bot.answer_callback_query(
                        call.id, f"❌ Failed to disable {server_name}", show_alert=True
                    )

            elif action == "confirm_remove":
                # Remove server
                server_name = parts[2]
                success = self.mcp_manager.remove_server(server_name)

                if success:
                    await self.bot.answer_callback_query(
                        call.id, f"✅ Server {server_name} deleted!", show_alert=True
                    )
                    # Delete confirmation message and show updated list
                    await self.bot.delete_message(call.message.chat.id, call.message.message_id)
                    # Show updated list
                    message = call.message
                    await self.handle_list_mcp_servers(message)
                else:
                    await self.bot.answer_callback_query(
                        call.id, f"❌ Failed to delete {server_name}", show_alert=True
                    )

            elif action == "cancel_remove":
                # Cancel removal
                await self.bot.answer_callback_query(call.id, "Cancelled")
                await self.bot.delete_message(call.message.chat.id, call.message.message_id)

            else:
                await self.bot.answer_callback_query(call.id, "Unknown action")

        except Exception as e:
            logger.error(f"Error handling MCP callback: {e}", exc_info=True)
            await self.bot.answer_callback_query(call.id, f"Error: {str(e)}")

    async def _refresh_server_list(self, call: CallbackQuery) -> None:
        """Refresh the server list display"""
        # Get all servers
        all_servers = self.mcp_manager.get_all_servers()

        if not all_servers:
            text = "📋 No MCP servers configured."
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("➕ Add New", callback_data="mcp:add"))
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
                    f"Markdown parsing failed in MCP list, sending without formatting: {e}"
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
