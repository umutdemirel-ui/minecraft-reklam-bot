"""Quiet, high-contrast industrial palette. No animations or remote assets."""
from __future__ import annotations

import customtkinter as ctk

BG = ("#F2F3F5", "#0D0F12")
SIDEBAR = ("#E9EBEF", "#111317")
CARD = ("#FFFFFF", "#171A20")
CARD_ALT = ("#F5F6F8", "#1D2128")
BORDER = ("#DCE0E6", "#2A2E36")
TEXT = ("#171B22", "#F2F3F5")
MUTED = ("#626B78", "#959DAA")
RED = "#F04E45"
RED_HOVER = "#D83C35"
RED_TINT = ("#FDECE9", "#2D1C1E")
GREEN = ("#18764D", "#73D6A5")
AMBER = ("#926000", "#EFC174")
FONT = "Segoe UI"
MONO = "Consolas"


def font(size=13, weight="normal", family=FONT):
    return ctk.CTkFont(family=family, size=size, weight=weight)


def apply_theme(theme: str) -> None:
    ctk.set_appearance_mode({"Koyu": "dark", "Açık": "light", "Sistem": "system"}[theme])
    ctk.set_widget_scaling(1.0)
    # Keep default widgets on the same accent, including checkboxes and scrollbars.
    palette = ctk.ThemeManager.theme
    for widget, key in (("CTkCheckBox", "fg_color"), ("CTkSwitch", "progress_color"),
                        ("CTkProgressBar", "progress_color"), ("CTkSlider", "progress_color")):
        palette[widget][key] = [RED_HOVER, RED]
    palette["CTkOptionMenu"]["fg_color"] = [CARD_ALT[0], CARD_ALT[1]]
    palette["CTkOptionMenu"]["button_color"] = [RED_HOVER, RED]


class Card(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=14, fg_color=CARD,
                         border_width=1, border_color=BORDER, **kwargs)


def label(master, text="", size=13, color=MUTED, weight="normal", *, family=FONT, **kwargs):
    return ctk.CTkLabel(master, text=text, font=font(size, weight, family), text_color=color,
                        anchor="w", justify="left", **kwargs)


def button(master, text, command, *, primary=False, danger=False, width=120, **kwargs):
    return ctk.CTkButton(master, text=text, command=command, width=width, height=38,
                         corner_radius=8, font=font(13, "bold"),
                         fg_color=RED if primary else RED_TINT if danger else CARD_ALT,
                         hover_color=RED_HOVER if primary else BORDER,
                         text_color="#FFFFFF" if primary else RED if danger else TEXT,
                         border_width=0 if primary else 1, border_color=BORDER, **kwargs)


def entry(master, variable=None, **kwargs):
    return ctk.CTkEntry(master, textvariable=variable, height=38, corner_radius=8,
                        fg_color=BG, border_color=BORDER, text_color=TEXT,
                        font=font(), **kwargs)


def section(master, title, subtitle=None):
    frame = ctk.CTkFrame(master, fg_color="transparent")
    frame.pack(fill="x", padx=22, pady=(20, 8))
    label(frame, title, 17, TEXT, "bold").pack(anchor="w")
    if subtitle:
        label(frame, subtitle, 12).pack(anchor="w", pady=(3, 0))
    return frame


def notice(master, text, color=MUTED):
    return label(master, text, 12, color, wraplength=700)


def clock(seconds: float) -> str:
    value = max(0, int(seconds + 0.999))
    hours, rest = divmod(value, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
