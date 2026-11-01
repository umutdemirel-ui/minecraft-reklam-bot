"""Explicit per-user Windows startup registration. Never starts automation itself."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "MinecraftAutoAdvertiser"


def startup_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}" --startup'
    python = Path(sys.executable)
    pythonw = python.with_name("pythonw.exe")
    if pythonw.exists():
        python = pythonw
    main = Path(__file__).resolve().parent.parent / "main.py"
    return f'"{python}" "{main}" --startup'


def set_startup(enabled: bool) -> None:
    if os.name != "nt":
        if enabled:
            raise RuntimeError("Windows başlangıç ayarı yalnızca Windows'ta değiştirilebilir.")
        return
    import winreg
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass


def open_data_folder(path: Path) -> None:
    if os.name == "nt":
        os.startfile(str(path))  # noqa: S606 - explicit user action, no shell interpolation
    else:
        subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
