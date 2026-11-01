"""Construct every page in an isolated demo database. Never starts automation or sends input."""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.config import AppPaths, default_settings
from database.database import Database
from ui.app import App


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="maa-ui-smoke-") as folder:
        paths = AppPaths.discover(Path(folder) / "data")
        paths.ensure()
        db = Database(paths.database)
        settings = db.get_settings(default_settings(paths))
        db.add_message("Skyblock market", "Marketim açılmıştır! Uygun fiyatlar için beklerim.", True, 180)
        db.add_message("Yeni ürünler", "Skyblock marketimde yeni ürünler mevcut!", True, 180)
        db.add_message("Market daveti", "Alışveriş için marketime uğramayı unutmayın!", False, 300)
        message = db.messages()[0]
        db.begin_attempt("demo-preview", "demo-preview", message, 180)
        db.finish_attempt("demo-preview", "sent")
        app = App(paths, db, settings, smoke_test=True)
        app.geometry("980x660+0+0")  # also exercises the minimum supported window size
        app.update_idletasks()
        app.update()
        assert app.controller.snapshot()["mode"] == "stopped"
        assert not app.hotkeys.ready
        if args.screenshots:
            from PIL import ImageGrab
            args.screenshots.mkdir(parents=True, exist_ok=True)
        for name in ("dashboard", "messages", "scheduler", "history", "settings"):
            app.navigate(name)
            app.update_idletasks()
            app.update()
            assert app.pages[name].winfo_ismapped()
            # Verify the actual visible page, not merely stacking order of inner widgets.
            visible = app.winfo_containing(app.winfo_rootx() + 400, app.winfo_rooty() + 160)
            page = app.pages[name]
            while visible is not None and visible is not page and visible is not app:
                visible = getattr(visible, "master", None)
            assert visible is page, f"Navigation did not bring {name} to the front"
            if name == "dashboard":
                app.update_idletasks()
                dashboard = app.pages[name]
                for control in (dashboard.start_button, dashboard.pause_button, dashboard.stop_button):
                    assert control.winfo_width() > 50 and control.winfo_height() >= 30
                    assert control.winfo_rootx() + control.winfo_width() <= app.winfo_rootx() + app.winfo_width()
            if args.screenshots:
                x, y = app.winfo_rootx(), app.winfo_rooty()
                image = ImageGrab.grab(bbox=(x, y, x + app.winfo_width(), y + app.winfo_height()))
                image.save(args.screenshots / f"{name}.png")
        app.close()
        assert not app.controller.alive
        print("UI smoke passed: five pages; no hotkeys, no automation, no keyboard input.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        import urllib.parse
        detail = traceback.format_exc()
        print(detail)
        # GitHub's annotation API remains accessible even when artifact CDN downloads are not.
        print("::error title=UI smoke::" + urllib.parse.quote(detail, safe="")[:6000])
        raise
