"""Legacy ttk theme helpers.

Current app UI is based on customtkinter, but this module is kept to quickly
apply a consistent classic ttk palette in case parts of the UI move back to ttk.
"""

from __future__ import annotations

from dataclasses import dataclass
from tkinter import Tk, font as tkfont, ttk


@dataclass(frozen=True)
class OldRusPalette:
    """Color palette values used by `apply_old_rus_theme`."""

    bg: str = "#F3E7CF"  # parchment
    panel: str = "#E7D6B1"
    panel2: str = "#E0C89A"
    text: str = "#2B1B10"
    muted: str = "#5A3D2A"
    accent: str = "#7A3B1E"
    accent2: str = "#B44A2A"
    border: str = "#8C6A3D"
    select_bg: str = "#D9B26A"
    select_text: str = "#1B120B"


def _pick_font(families: list[str], default: str) -> str:
    """Pick first available font family, otherwise fallback to default."""
    available = set(tkfont.families())
    for f in families:
        if f in available:
            return f
    return default


def apply_old_rus_theme(root: Tk) -> OldRusPalette:
    """
    Apply a 'Old Rus' inspired ttk theme.
    Returns the palette so callers can use it for non-ttk widgets/canvas.
    """
    pal = OldRusPalette()

    # Root background (covers blank areas around ttk widgets)
    try:
        root.configure(bg=pal.bg)
    except Exception:
        pass

    # Fonts
    heading_family = _pick_font(["Georgia", "Times New Roman"], "TkDefaultFont")
    ui_family = _pick_font(["Segoe UI", "Tahoma", "Arial"], "TkDefaultFont")

    default_font = tkfont.nametofont("TkDefaultFont")
    default_font.configure(family=ui_family, size=10)
    root.option_add("*Font", default_font)

    text_font = tkfont.nametofont("TkTextFont")
    text_font.configure(family=ui_family, size=10)

    heading_font = tkfont.Font(family=heading_family, size=11, weight="bold")
    title_font = tkfont.Font(family=heading_family, size=14, weight="bold")

    style = ttk.Style(root)

    # Prefer "clam" because it applies custom colors/maps consistently on Windows.
    try:
        if "clam" in style.theme_names():
            style.theme_use("clam")
        elif "alt" in style.theme_names():
            style.theme_use("alt")
    except Exception:
        pass

    style.configure(".", background=pal.bg, foreground=pal.text)

    style.configure("Rus.TFrame", background=pal.bg)
    style.configure("Rus.Panel.TFrame", background=pal.panel)
    style.configure("Rus.Panel2.TFrame", background=pal.panel2)

    style.configure("Rus.TLabelframe", background=pal.bg, foreground=pal.text)
    style.configure("Rus.TLabelframe.Label", background=pal.bg, foreground=pal.accent, font=heading_font)

    style.configure("Rus.TLabel", background=pal.bg, foreground=pal.text)
    style.configure("Rus.Muted.TLabel", background=pal.bg, foreground=pal.muted)
    style.configure("Rus.Title.TLabel", background=pal.bg, foreground=pal.accent, font=title_font)
    style.configure("Rus.Heading.TLabel", background=pal.bg, foreground=pal.accent, font=heading_font)

    # Buttons
    style.configure(
        "Rus.TButton",
        padding=(12, 7),
        background=pal.panel,
        foreground=pal.text,
        bordercolor=pal.border,
        focusthickness=1,
        focuscolor=pal.accent,
        font=heading_font,
    )
    style.map(
        "Rus.TButton",
        background=[
            ("disabled", pal.panel),
            ("pressed", pal.panel2),
            ("active", pal.select_bg),
        ],
        foreground=[
            ("disabled", pal.muted),
            ("active", pal.select_text),
        ],
    )

    style.configure(
        "Rus.Accent.TButton",
        padding=(14, 8),
        background=pal.accent,
        foreground="#FFF6E8",
        bordercolor=pal.border,
        focusthickness=1,
        focuscolor=pal.select_bg,
        font=heading_font,
    )
    style.map(
        "Rus.Accent.TButton",
        background=[
            ("disabled", pal.panel),
            ("pressed", "#5C2A14"),
            ("active", pal.accent2),
        ],
        foreground=[
            ("disabled", pal.muted),
            ("active", "#FFF6E8"),
        ],
    )

    # Inputs
    style.configure(
        "Rus.TEntry",
        padding=6,
        fieldbackground="#FFF6E8",
        foreground=pal.text,
        insertcolor=pal.text,
    )
    style.configure(
        "Rus.TCombobox",
        padding=6,
        fieldbackground="#FFF6E8",
        foreground=pal.text,
        arrowcolor=pal.accent,
    )

    # Treeview
    style.configure(
        "Rus.Treeview",
        background="#FFF6E8",
        fieldbackground="#FFF6E8",
        foreground=pal.text,
        bordercolor=pal.border,
        rowheight=24,
    )
    style.map(
        "Rus.Treeview",
        background=[("selected", pal.select_bg)],
        foreground=[("selected", pal.select_text)],
    )
    style.configure(
        "Rus.Treeview.Heading",
        background=pal.panel2,
        foreground=pal.text,
        font=heading_font,
        relief="flat",
    )

    # Progressbar
    style.configure(
        "Rus.Horizontal.TProgressbar",
        background=pal.accent,
        troughcolor=pal.panel,
        bordercolor=pal.border,
        lightcolor=pal.accent2,
        darkcolor=pal.accent,
    )

    return pal

