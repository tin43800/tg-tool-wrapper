"""Reusable Telegram bot wrapper.

Design:
- Sync (pyTelegramBotAPI) — simpler than async python-telegram-bot
- Long-polling — works locally without a public endpoint
- Owner lock: first user to message becomes owner, others rejected
- Decorator-based handler registration for photo / document / command / text
- Handler return value is sent as reply (None = no reply)
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Callable, Optional

import telebot
import truststore

truststore.inject_into_ssl()

logger = logging.getLogger(__name__)


class TelegramBot:
    """Reusable Telegram bot with owner-lock and decorator handlers.

    Example:
        bot = TelegramBot(token=os.environ['TELEGRAM_BOT_TOKEN'])

        @bot.on_command('start')
        def start(args, message):
            return "Hi!"

        @bot.on_photo
        def handle_photo(photo_path, message):
            return f"Got photo: {photo_path}"

        bot.run()
    """

    def __init__(
        self,
        token: str,
        owner_file: str = "telegram_owner.json",
        temp_suffix: str = ".jpg",
    ):
        self.bot = telebot.TeleBot(token)
        self.owner_file = Path(owner_file)
        self.owner_id: Optional[int] = self._load_owner()
        self.temp_suffix = temp_suffix
        self._photo_handler: Optional[Callable] = None
        self._document_handler: Optional[Callable] = None
        self._text_handler: Optional[Callable] = None
        self._command_handlers: dict[str, Callable] = {}
        self._wire_handlers()

    def _load_owner(self) -> Optional[int]:
        if self.owner_file.exists():
            data = json.loads(self.owner_file.read_text(encoding="utf-8"))
            return data.get("owner_id")
        return None

    def _save_owner(self, user_id: int, username: str = "") -> None:
        self.owner_file.write_text(
            json.dumps({"owner_id": user_id, "username": username}, ensure_ascii=False),
            encoding="utf-8",
        )
        self.owner_id = user_id

    def _check_auth(self, message) -> bool:
        user_id = message.from_user.id
        username = message.from_user.username or ""
        if self.owner_id is None:
            self._save_owner(user_id, username)
            logger.info(f"Owner registered: {user_id} (@{username})")
            self.bot.reply_to(
                message,
                f"✅ Owner registered: {username or user_id}\nYou are now the only user this bot listens to.",
            )
            return True
        if user_id != self.owner_id:
            logger.warning(f"Rejected message from unauthorized user {user_id} (@{username})")
            return False
        return True

    def on_command(self, command: str):
        """Register a /command handler. Handler signature: (args: str, message) -> str | None"""

        def decorator(func: Callable) -> Callable:
            self._command_handlers[command] = func
            return func

        return decorator

    def on_photo(self, func: Callable) -> Callable:
        """Register a photo handler. Handler signature: (photo_path: str, message) -> str | None"""
        self._photo_handler = func
        return func

    def on_document(self, func: Callable) -> Callable:
        """Register a document handler. Handler signature: (file_path: str, filename: str, message) -> str | None"""
        self._document_handler = func
        return func

    def on_text(self, func: Callable) -> Callable:
        """Register a plain-text fallback handler. Handler signature: (text: str, message) -> str | None"""
        self._text_handler = func
        return func

    def reply(self, message, text: str) -> None:
        """Send a reply to the given message (handlers can call this for progress updates)."""
        self.bot.reply_to(message, text)

    def _download_to_temp(self, file_id: str, suffix: str) -> str:
        file_info = self.bot.get_file(file_id)
        data = self.bot.download_file(file_info.file_path)
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return path

    def _wire_handlers(self) -> None:
        @self.bot.message_handler(content_types=["photo"])
        def _handle_photo(message):
            if not self._check_auth(message):
                return
            if self._photo_handler is None:
                self.bot.reply_to(message, "No photo handler registered.")
                return
            photo_path = None
            try:
                photo_path = self._download_to_temp(message.photo[-1].file_id, self.temp_suffix)
                reply = self._photo_handler(photo_path, message)
                if reply:
                    self.bot.reply_to(message, reply)
            except Exception as e:
                logger.exception("Photo handler failed")
                self.bot.reply_to(message, f"❌ Error: {e}")
            finally:
                if photo_path and os.path.exists(photo_path):
                    try:
                        os.unlink(photo_path)
                    except OSError:
                        pass

        @self.bot.message_handler(content_types=["document"])
        def _handle_document(message):
            if not self._check_auth(message):
                return
            if self._document_handler is None:
                self.bot.reply_to(message, "No document handler registered.")
                return
            filename = message.document.file_name or "file"
            suffix = Path(filename).suffix or ".bin"
            file_path = None
            try:
                file_path = self._download_to_temp(message.document.file_id, suffix)
                reply = self._document_handler(file_path, filename, message)
                if reply:
                    self.bot.reply_to(message, reply)
            except Exception as e:
                logger.exception("Document handler failed")
                self.bot.reply_to(message, f"❌ Error: {e}")
            finally:
                if file_path and os.path.exists(file_path):
                    try:
                        os.unlink(file_path)
                    except OSError:
                        pass

        @self.bot.message_handler(func=lambda m: bool(m.text and m.text.startswith("/")))
        def _handle_command(message):
            if not self._check_auth(message):
                return
            parts = message.text.split(maxsplit=1)
            cmd = parts[0][1:].split("@")[0]
            args = parts[1] if len(parts) > 1 else ""
            handler = self._command_handlers.get(cmd)
            if not handler:
                self.bot.reply_to(message, f"Unknown command: /{cmd}")
                return
            try:
                reply = handler(args, message)
                if reply:
                    self.bot.reply_to(message, reply)
            except Exception as e:
                logger.exception(f"Command /{cmd} failed")
                self.bot.reply_to(message, f"❌ Error: {e}")

        @self.bot.message_handler(content_types=["text"])
        def _handle_text(message):
            if not self._check_auth(message):
                return
            if self._text_handler:
                try:
                    reply = self._text_handler(message.text, message)
                    if reply:
                        self.bot.reply_to(message, reply)
                except Exception as e:
                    logger.exception("Text handler failed")
                    self.bot.reply_to(message, f"❌ Error: {e}")

    def run(self) -> None:
        """Start long-polling. Blocks until interrupted."""
        if self.owner_id:
            logger.info(f"Bot starting — owner: {self.owner_id}")
        else:
            logger.info("Bot starting — no owner yet, first user becomes owner")
        self.bot.infinity_polling()
