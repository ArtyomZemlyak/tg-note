"""
Scheduled Task Handlers for Telegram Bot
Provides interface for managing scheduled agent tasks
"""

import uuid
from datetime import datetime
from typing import Dict, Optional

from loguru import logger
from telebot.async_telebot import AsyncTeleBot
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.bot.utils import escape_html
from src.knowledge_base.user_settings import UserSettings
from src.services.scheduled_task import ScheduledTask
from src.services.scheduled_task_service import ScheduledTaskService


class ScheduledTaskHandlers:
    """Telegram handlers for scheduled task management"""

    def __init__(
        self,
        bot: AsyncTeleBot,
        task_service: ScheduledTaskService,
        user_settings: UserSettings,
        handlers=None,
    ):
        """
        Initialize scheduled task handlers

        Args:
            bot: Telegram bot instance
            task_service: Scheduled task service
            user_settings: User settings manager
            handlers: Reference to main handlers (for navigation)
        """
        self.bot = bot
        self.task_service = task_service
        self.user_settings = user_settings
        self.handlers = handlers

        # Track users waiting for input: user_id -> (waiting_for_type, task_id)
        self.waiting_for_input: Dict[int, tuple[str, Optional[str]]] = {}

    async def register_handlers_async(self):
        """Register all scheduled task handlers"""
        # Scheduled task commands
        self.bot.message_handler(commands=["tasks", "scheduled_tasks"])(self.handle_tasks_menu)

        # Text message handler for task input
        self.bot.message_handler(func=lambda m: m.from_user.id in self.waiting_for_input)(
            self.handle_task_input
        )

        # Callback query handlers for inline keyboards
        self.bot.callback_query_handler(func=lambda call: call.data.startswith("task:"))(
            self.handle_task_callback
        )

    async def handle_tasks_menu(self, message: Message) -> None:
        """Handle /tasks command - show scheduled tasks menu"""
        logger.info(f"Scheduled tasks menu requested by user {message.from_user.id}")

        user_id = message.from_user.id
        tasks = self.task_service.get_tasks_for_user(user_id)

        keyboard = InlineKeyboardMarkup()
        keyboard.row_width = 1

        # Add back button
        keyboard.add(InlineKeyboardButton("« Назад", callback_data="task:back"))

        # Add create task button
        keyboard.add(InlineKeyboardButton("➕ Создать задачу", callback_data="task:create"))

        # Add list of existing tasks
        if tasks:
            for task in tasks:
                status_emoji = "✅" if task.enabled else "⏸️"
                keyboard.add(
                    InlineKeyboardButton(
                        f"{status_emoji} {task.task_id} ({task.kb_name})",
                        callback_data=f"task:view:{task.task_id}",
                    )
                )
        else:
            keyboard.add(
                InlineKeyboardButton("📋 Нет задач", callback_data="task:empty", disabled=True)
            )

        menu_text = (
            "⏰ <b>Регулярные задачи</b>\n\n"
            "Управление автоматическими задачами для агента.\n\n"
            f"Всего задач: {len(tasks)}\n"
            f"Активных: {sum(1 for t in tasks if t.enabled)}\n\n"
            "Выберите действие:"
        )

        await self.bot.send_message(
            message.chat.id, menu_text, reply_markup=keyboard, parse_mode="HTML"
        )

    async def handle_task_callback(self, call: CallbackQuery) -> None:
        """Handle callback queries from task menu"""
        try:
            await self.bot.answer_callback_query(call.id)

            parts = call.data.split(":", 2)
            if len(parts) < 2:
                return

            action = parts[1]

            if action == "back":
                # Go back to main menu
                if self.handlers:
                    message = call.message
                    message.from_user = call.from_user
                    message.text = "/start"
                    await self.handlers.handle_start(message)
                return

            elif action == "create":
                await self._show_create_task_menu(call)
                return

            elif action == "view" and len(parts) > 2:
                task_id = parts[2]
                await self._show_task_details(call, task_id)
                return

            elif action == "edit" and len(parts) > 2:
                task_id = parts[2]
                await self._show_edit_task_menu(call, task_id)
                return

            elif action == "delete" and len(parts) > 2:
                task_id = parts[2]
                await self._confirm_delete_task(call, task_id)
                return

            elif action == "confirm_delete" and len(parts) > 2:
                task_id = parts[2]
                await self._delete_task(call, task_id)
                return

            elif action == "toggle" and len(parts) > 2:
                task_id = parts[2]
                await self._toggle_task(call, task_id)
                return

            elif action == "set_kb" and len(parts) > 2:
                task_id = parts[2]
                user_id = call.from_user.id
                self.waiting_for_input[user_id] = ("kb_name", task_id)
                await self.bot.send_message(
                    call.message.chat.id,
                    "📚 Введите название базы знаний для задачи:",
                )
                return

            elif action == "set_schedule" and len(parts) > 2:
                task_id = parts[2]
                user_id = call.from_user.id
                self.waiting_for_input[user_id] = ("schedule", task_id)
                await self.bot.send_message(
                    call.message.chat.id,
                    "⏰ Введите расписание:\n\n"
                    "• Cron выражение (например: '0 9 * * *' для ежедневно в 9:00)\n"
                    "• Или интервал в секундах (например: '3600' для каждый час)",
                )
                return

            elif action == "set_prompt_path" and len(parts) > 2:
                task_id = parts[2]
                user_id = call.from_user.id
                self.waiting_for_input[user_id] = ("prompt_path", task_id)
                await self.bot.send_message(
                    call.message.chat.id,
                    "📝 Введите путь к промпту (promptic формат, например: 'agent_mode_v5.md'):",
                )
                return

            elif action == "set_prompt_text" and len(parts) > 2:
                task_id = parts[2]
                user_id = call.from_user.id
                self.waiting_for_input[user_id] = ("prompt_text", task_id)
                await self.bot.send_message(
                    call.message.chat.id,
                    "📝 Введите текст промпта:",
                )
                return

        except Exception as e:
            logger.error(f"Error handling task callback: {e}", exc_info=True)
            await self.bot.send_message(
                call.message.chat.id, f"❌ Ошибка: {str(e)}", parse_mode="HTML"
            )

    async def handle_task_input(self, message: Message) -> None:
        """Handle text input for task creation/editing"""
        user_id = message.from_user.id
        if user_id not in self.waiting_for_input:
            return

        waiting_type, task_id = self.waiting_for_input[user_id]
        del self.waiting_for_input[user_id]

        try:
            if waiting_type == "kb_name":
                task = self.task_service.get_task(task_id)
                if task:
                    task.kb_name = message.text.strip()
                    self.task_service.update_task(task)
                    await self.bot.send_message(
                        message.chat.id, f"✅ База знаний установлена: {task.kb_name}"
                    )
                else:
                    await self.bot.send_message(message.chat.id, "❌ Задача не найдена")

            elif waiting_type == "schedule":
                task = self.task_service.get_task(task_id)
                if task:
                    task.schedule = message.text.strip()
                    self.task_service.update_task(task)
                    await self.bot.send_message(
                        message.chat.id, f"✅ Расписание установлено: {task.schedule}"
                    )
                else:
                    await self.bot.send_message(message.chat.id, "❌ Задача не найдена")

            elif waiting_type == "prompt_path":
                task = self.task_service.get_task(task_id)
                if task:
                    task.prompt_path = message.text.strip()
                    task.prompt_text = None  # Clear prompt_text if setting prompt_path
                    self.task_service.update_task(task)
                    await self.bot.send_message(
                        message.chat.id, f"✅ Путь к промпту установлен: {task.prompt_path}"
                    )
                else:
                    await self.bot.send_message(message.chat.id, "❌ Задача не найдена")

            elif waiting_type == "prompt_text":
                task = self.task_service.get_task(task_id)
                if task:
                    task.prompt_text = message.text.strip()
                    task.prompt_path = None  # Clear prompt_path if setting prompt_text
                    self.task_service.update_task(task)
                    await self.bot.send_message(message.chat.id, "✅ Текст промпта установлен")
                else:
                    await self.bot.send_message(message.chat.id, "❌ Задача не найдена")

        except Exception as e:
            logger.error(f"Error handling task input: {e}", exc_info=True)
            await self.bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

    async def _show_create_task_menu(self, call: CallbackQuery) -> None:
        """Show menu for creating a new task"""
        user_id = call.from_user.id
        user_kb = self.user_settings.get_user_kb(user_id)

        if not user_kb:
            await self.bot.send_message(
                call.message.chat.id,
                "❌ Сначала настройте базу знаний: /kb",
            )
            return

        # Create a new task with defaults
        task_id = f"task_{user_id}_{uuid.uuid4().hex[:8]}"
        task = ScheduledTask(
            task_id=task_id,
            user_id=user_id,
            kb_name=user_kb["kb_name"],
            schedule="0 9 * * *",  # Default: daily at 9 AM
            enabled=True,
            chat_id=call.message.chat.id,
        )

        self.task_service.create_task(task)

        await self._show_task_details(call, task_id)

    async def _show_task_details(self, call: CallbackQuery, task_id: str) -> None:
        """Show details of a task"""
        task = self.task_service.get_task(task_id)
        if not task:
            await self.bot.send_message(call.message.chat.id, "❌ Задача не найдена")
            return

        # Check if user owns the task
        if task.user_id != call.from_user.id:
            await self.bot.send_message(call.message.chat.id, "❌ Доступ запрещен")
            return

        keyboard = InlineKeyboardMarkup()
        keyboard.row_width = 1

        keyboard.add(InlineKeyboardButton("« Назад к списку", callback_data="task:back"))
        keyboard.add(InlineKeyboardButton("✏️ Редактировать", callback_data=f"task:edit:{task_id}"))
        keyboard.add(
            InlineKeyboardButton(
                "✅ Включить" if not task.enabled else "⏸️ Выключить",
                callback_data=f"task:toggle:{task_id}",
            )
        )
        keyboard.add(InlineKeyboardButton("🗑️ Удалить", callback_data=f"task:delete:{task_id}"))

        status_text = "✅ Включена" if task.enabled else "⏸️ Выключена"
        last_run_text = task.last_run.strftime("%Y-%m-%d %H:%M:%S") if task.last_run else "Никогда"
        next_run_text = (
            task.next_run.strftime("%Y-%m-%d %H:%M:%S") if task.next_run else "Не запланировано"
        )

        prompt_info = ""
        if task.prompt_path:
            prompt_info = f"📝 <b>Промпт:</b> {escape_html(task.prompt_path)}"
        elif task.prompt_text:
            prompt_text_preview = (
                task.prompt_text[:50] + "..." if len(task.prompt_text) > 50 else task.prompt_text
            )
            prompt_info = f"📝 <b>Промпт:</b> {escape_html(prompt_text_preview)}"

        details_text = (
            f"⏰ <b>Задача: {escape_html(task.task_id)}</b>\n\n"
            f"📚 <b>База знаний:</b> {escape_html(task.kb_name)}\n"
            f"⏰ <b>Расписание:</b> {escape_html(task.schedule)}\n"
            f"{prompt_info}\n"
            f"📊 <b>Статус:</b> {status_text}\n"
            f"🕐 <b>Последний запуск:</b> {last_run_text}\n"
            f"🕐 <b>Следующий запуск:</b> {next_run_text}\n"
        )

        await self.bot.edit_message_text(
            details_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    async def _show_edit_task_menu(self, call: CallbackQuery, task_id: str) -> None:
        """Show menu for editing a task"""
        task = self.task_service.get_task(task_id)
        if not task:
            await self.bot.send_message(call.message.chat.id, "❌ Задача не найдена")
            return

        if task.user_id != call.from_user.id:
            await self.bot.send_message(call.message.chat.id, "❌ Доступ запрещен")
            return

        keyboard = InlineKeyboardMarkup()
        keyboard.row_width = 1

        keyboard.add(InlineKeyboardButton("« Назад", callback_data=f"task:view:{task_id}"))
        keyboard.add(
            InlineKeyboardButton(
                f"📚 База знаний: {task.kb_name}", callback_data=f"task:set_kb:{task_id}"
            )
        )
        keyboard.add(
            InlineKeyboardButton(
                f"⏰ Расписание: {task.schedule}", callback_data=f"task:set_schedule:{task_id}"
            )
        )
        if task.prompt_path:
            keyboard.add(
                InlineKeyboardButton(
                    f"📝 Промпт (путь): {task.prompt_path}",
                    callback_data=f"task:set_prompt_path:{task_id}",
                )
            )
        else:
            keyboard.add(
                InlineKeyboardButton(
                    "📝 Промпт (текст)", callback_data=f"task:set_prompt_text:{task_id}"
                )
            )

        edit_text = (
            f"✏️ <b>Редактирование задачи</b>\n\n"
            f"Задача: {escape_html(task.task_id)}\n\n"
            "Выберите параметр для изменения:"
        )

        await self.bot.edit_message_text(
            edit_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    async def _toggle_task(self, call: CallbackQuery, task_id: str) -> None:
        """Toggle task enabled/disabled status"""
        task = self.task_service.get_task(task_id)
        if not task:
            await self.bot.send_message(call.message.chat.id, "❌ Задача не найдена")
            return

        if task.user_id != call.from_user.id:
            await self.bot.send_message(call.message.chat.id, "❌ Доступ запрещен")
            return

        task.enabled = not task.enabled
        self.task_service.update_task(task)

        status_text = "включена" if task.enabled else "выключена"
        await self.bot.send_message(
            call.message.chat.id, f"✅ Задача {status_text}", parse_mode="HTML"
        )

        # Refresh task details
        await self._show_task_details(call, task_id)

    async def _confirm_delete_task(self, call: CallbackQuery, task_id: str) -> None:
        """Show confirmation for task deletion"""
        task = self.task_service.get_task(task_id)
        if not task:
            await self.bot.send_message(call.message.chat.id, "❌ Задача не найдена")
            return

        if task.user_id != call.from_user.id:
            await self.bot.send_message(call.message.chat.id, "❌ Доступ запрещен")
            return

        keyboard = InlineKeyboardMarkup()
        keyboard.row_width = 2

        keyboard.add(
            InlineKeyboardButton("❌ Отмена", callback_data=f"task:view:{task_id}"),
            InlineKeyboardButton("✅ Удалить", callback_data=f"task:confirm_delete:{task_id}"),
        )

        confirm_text = (
            f"🗑️ <b>Удаление задачи</b>\n\n"
            f"Вы уверены, что хотите удалить задачу '{escape_html(task.task_id)}'?\n\n"
            "Это действие нельзя отменить."
        )

        await self.bot.edit_message_text(
            confirm_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    async def _delete_task(self, call: CallbackQuery, task_id: str) -> None:
        """Delete a task"""
        task = self.task_service.get_task(task_id)
        if not task:
            await self.bot.send_message(call.message.chat.id, "❌ Задача не найдена")
            return

        if task.user_id != call.from_user.id:
            await self.bot.send_message(call.message.chat.id, "❌ Доступ запрещен")
            return

        self.task_service.delete_task(task_id)
        await self.bot.send_message(call.message.chat.id, f"✅ Задача '{task.task_id}' удалена")

        # Go back to tasks menu
        message = call.message
        message.from_user = call.from_user
        message.text = "/tasks"
        await self.handle_tasks_menu(message)
