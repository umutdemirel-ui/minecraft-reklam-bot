"""Minecraft Auto Advertiser. Startup never begins sending."""
from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Minecraft Auto Advertiser")
    parser.add_argument("--startup", action="store_true", help="Windows startup entry; still requires explicit Start")
    parser.add_argument("--data-dir", type=Path, help="Override the user-data directory")
    parser.add_argument("--smoke-test", action="store_true", help="Open UI without hotkeys/input, then close")
    return parser.parse_args()


def show_fatal(message: str) -> None:
    if os.name == "nt":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, "Minecraft Auto Advertiser", 0x10)
    else:
        print(message, file=sys.stderr)


def main() -> int:
    args = parse_args()
    if sys.version_info < (3, 12):
        show_fatal("Bu uygulama Python 3.12 veya daha yeni bir sürüm gerektirir. Windows EXE sürümünde Python kurmanız gerekmez.")
        return 1
    # Import GUI/platform libraries only after the supported runtime check.
    from core.config import AppPaths, default_settings
    from core.single_instance import InstanceLock
    from database.database import Database
    paths = AppPaths.discover(args.data_dir)
    lock = InstanceLock(paths.data / "instance.lock")
    app = None
    try:
        paths.ensure()
        if not lock.acquire():
            show_fatal("Minecraft Auto Advertiser zaten açık. İkinci bir otomasyon örneği başlatılmadı.")
            return 0
        handler = RotatingFileHandler(paths.logs / "application.log", maxBytes=1_000_000,
                                      backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logging.basicConfig(level=logging.INFO, handlers=[handler])
        log = logging.getLogger(__name__)
        log.info("Starting; portable=%s; startup=%s", paths.portable, args.startup)
        db = Database(paths.database)
        recovered = db.recover_interrupted()
        settings = db.get_settings(default_settings(paths))
        from ui.app import App
        if args.smoke_test and os.name == "nt":
            # Construct native adapters to verify packaging, but NEVER press a key or hook F8.
            from core.keyboard_adapter import DesktopKeyboard
            import keyboard
            assert callable(keyboard.add_hotkey)
            DesktopKeyboard()
            log.info("Packaged native adapters loaded; no desktop input performed.")
        app = App(paths, db, settings, smoke_test=args.smoke_test)
        def unexpected_exception(kind, value, tb):
            log.error("Uncaught exception", exc_info=(kind, value, tb))
            app.controller.stop("Beklenmeyen hata nedeniyle güvenli durdurma.")
        def thread_exception(args):
            unexpected_exception(args.exc_type, args.exc_value, args.exc_traceback)
        sys.excepthook = unexpected_exception
        threading.excepthook = thread_exception
        if recovered:
            from tkinter.messagebox import showwarning
            app.after(300, lambda: showwarning(
                "Kesinti kurtarması", f"{recovered} önceki girişim tamamlanmamış. Sonuçları belirsiz olarak işaretlendi.\n"
                "Mesajlar otomatik yeniden gönderilmez. Gönderim geçmişi ekranını kontrol edin.", parent=app))
        app.mainloop()
        return 0
    except Exception as exc:
        logging.getLogger(__name__).exception("Fatal startup error")
        show_fatal(f"Uygulama güvenli şekilde kapatıldı.\n{type(exc).__name__}: {exc}\n\n"
                   f"Veri ve log klasörü: {paths.data}")
        return 1
    finally:
        if app is not None:
            try:
                app.close()
            except Exception:
                logging.getLogger(__name__).exception("Cleanup error")
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
