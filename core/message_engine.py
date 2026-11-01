"""Single-attempt send pipeline, journal-before-input and no automatic retries.

The lightweight keyboard API cannot inspect Minecraft's chat UI or read server acknowledgment.
Consequently `sent` means 'Enter was submitted without a detected input error', NOT delivery
confirmation. Default T binding and an unobstructed game view are explicit preconditions.
"""
from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass

from core.keyboard_adapter import KeyboardAdapter
from core.minecraft_detector import MinecraftDetector, Window
from database.database import Database
from database.models import Message

LOG = logging.getLogger(__name__)


class SendAborted(Exception):
    pass


@dataclass(frozen=True)
class SendResult:
    status: str
    attempt_id: str
    error: str = ""


class MessageEngine:
    CHAT_OPEN_DELAY = 0.40
    SETTLE_DELAY = 0.12

    def __init__(self, database: Database, detector: MinecraftDetector, keyboard: KeyboardAdapter):
        self.db = database
        self.detector = detector
        self.keyboard = keyboard
        self.session_id = uuid.uuid4().hex

    def send(self, message: Message, target: Window, cancel: threading.Event,
             cooldown: int) -> SendResult:
        attempt_id = uuid.uuid4().hex
        session_id = self.session_id  # one correlation ID per explicit automation session
        enter_dispatched = False
        journaled = False

        def guard() -> None:
            if cancel.is_set():
                raise SendAborted("İşlem iptal edildi. Enter gönderilmedi; oyunda taslak kalabilir.")
            check = self.detector.validate(target)
            if not check.can_send:
                raise SendAborted(check.detail + " Tuş gönderimi kesildi; otomatik devam edilmez.")

        try:
            guard()
            # Both records commit together before ANY synthetic keyboard input.
            self.db.begin_attempt(attempt_id, session_id, message, cooldown)
            journaled = True
            self.keyboard.press("t", guard)
            if cancel.wait(self.CHAT_OPEN_DELAY):
                guard()
            self.keyboard.clear(guard)
            self.keyboard.type_text(message.content, guard)
            if cancel.wait(self.SETTLE_DELAY):
                guard()
            guard()
            self.db.mark_sending(attempt_id)
            guard()
            enter_dispatched = True
            self.keyboard.press("enter", guard)
            self.db.finish_attempt(attempt_id, "sent")
            return SendResult("sent", attempt_id)
        except Exception as exc:
            aborted = isinstance(exc, SendAborted) or cancel.is_set()
            status = "aborted" if aborted and not enter_dispatched else "unknown" if enter_dispatched else "failed"
            detail = str(exc) if isinstance(exc, (SendAborted, RuntimeError, ValueError)) else (
                "Veritabanı/klavye hatası: " + type(exc).__name__)
            if enter_dispatched:
                detail += " Enter sonucu belirsiz olabilir; otomatik yeniden deneme yapılmaz."
            LOG.warning("Send attempt %s ended as %s (%s)", attempt_id, status, type(exc).__name__)
            if journaled:
                try:
                    self.db.finish_attempt(attempt_id, status, detail)
                except Exception:
                    LOG.exception("Could not finalize attempt journal")
                    detail += " İşlem kaydı tamamlanamadı; uygulama güvenle duraklatılmalı."
            return SendResult(status, attempt_id, detail)
