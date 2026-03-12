#!/usr/bin/env python3
"""
精美倒计时软件 - Beautiful Countdown Timer
Features: Custom time, checkpoints, progress bar, motivational messages, compact mode
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import math
import time
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

# ─── Config Persistence ───────────────────────────────────────────────────────
CONFIG_DIR  = Path.home() / ".countdown_timer"
CONFIG_FILE = CONFIG_DIR / "config.json"

def load_config() -> dict:
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_config(data: dict):
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[保存配置失败] {e}")

# ─── Color Palette ───────────────────────────────────────────────────────────
COLORS = {
    "bg_dark":      "#0D1117",
    "bg_card":      "#161B22",
    "bg_panel":     "#1C2128",
    "border":       "#30363D",
    "border_glow":  "#58A6FF",
    "text_primary": "#E6EDF3",
    "text_secondary":"#8B949E",
    "text_muted":   "#484F58",
    "accent_blue":  "#58A6FF",
    "accent_cyan":  "#39D5C3",
    "accent_green": "#3FB950",
    "accent_yellow":"#F0C840",
    "accent_orange":"#FF8C42",
    "accent_red":   "#FF6B6B",
    "accent_pink":  "#FF79C6",
    "accent_purple":"#BD93F9",
    "progress_bg":  "#21262D",
    "gradient_start":"#58A6FF",
    "gradient_end":  "#39D5C3",
}

# ─── Default Messages by Percentage ──────────────────────────────────────────
DEFAULT_MESSAGES = {
    100: ("🚀 旅程开始，星辰大海等你探索！", "#58A6FF"),
    70:  ("✨ 稳步前行，你正在掌控一切！", "#58A6FF"),
    50:  ("⚡ 已过半程，继续保持节奏！", "#39D5C3"),
    25:  ("💫 最后四分之一，感受到了吗？", "#F0C840"),
    20:  ("🔥 冲刺阶段！热血沸腾！", "#FF8C42"),
    10:  ("💥 最后10%！全力以赴！", "#FF6B6B"),
    5:   ("🎯 即将到达！心跳加速！", "#FF6B6B"),
    2:   ("🌟 胜利就在眼前！燃起来！", "#FF79C6"),
    1:   ("🎆 最后一刻！奇迹即将发生！！", "#FF79C6"),
    0:   ("🎉🎊 时间到！你做到了！恭喜！🎊🎉", "#BD93F9"),
}

PERCENTAGE_OPTIONS = [100, 70, 50, 25, 20, 10, 5, 2, 1, 0]


@dataclass
class Checkpoint:
    name: str
    remaining_at: int   # remaining seconds when this checkpoint fires (e.g. 0 = countdown hits 0)
    triggered: bool = False


@dataclass
class CustomMessage:
    percentage: int
    text: str
    color: str = "#58A6FF"



# ─── Progress Bar Color Bands ─────────────────────────────────────────────────
# Each band: (pct_upper, pct_lower, color_left, color_right)
# Drawn LEFT=elapsed=full, RIGHT=remaining=empty
PROGRESS_BANDS = [
    (100, 70,  "#A8D8FF", "#58A6FF"),   # light→deep blue
    (70,  50,  "#58A6FF", "#39D5C3"),   # blue→cyan
    (50,  25,  "#39D5C3", "#3FB950"),   # cyan→green
    (25,  20,  "#F0C840", "#F0A820"),   # yellow shades
    (20,  10,  "#FF8C42", "#FF6B20"),   # orange
    (10,   5,  "#FF6B6B", "#FF3030"),   # red
    (5,    0,  "#FF3030", "#CC0000"),   # deep red → crimson
]

def get_progress_color(pct_float):
    """Return fill color for a position 0.0-1.0 on the progress bar.
    pct_float = fraction of TIME REMAINING (1.0=full, 0.0=done).
    The bar fills left-to-right as time decreases, so position x
    on the bar represents (1 - x/bar_width) remaining fraction.
    """
    p = pct_float * 100  # convert to 0-100
    for upper, lower, c_left, c_right in PROGRESS_BANDS:
        if p <= upper and p >= lower:
            if upper == lower:
                return c_right
            t = (upper - p) / (upper - lower)  # 0=band start, 1=band end
            # Interpolate hex colors
            def hex_to_rgb(h):
                h = h.lstrip('#')
                return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
            r1,g1,b1 = hex_to_rgb(c_left)
            r2,g2,b2 = hex_to_rgb(c_right)
            r = int(r1 + (r2-r1)*t)
            g = int(g1 + (g2-g1)*t)
            b = int(b1 + (b2-b1)*t)
            return f"#{r:02x}{g:02x}{b:02x}"
    return "#CC0000"

class CountdownTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("⏱ 倒计时")
        self.root.configure(bg=COLORS["bg_dark"])
        self.root.minsize(480, 320)
        self.root.geometry("720x900")

        # Timer state
        self.total_seconds = 0
        self.remaining_seconds = 0
        self.ref_seconds = 0        # reference total (for offset start, feature 3)
        self.running = False
        self.paused = False
        self.compact_mode = False
        self._after_id = None
        self._last_tick = None
        self._flash_count = 0
        self._last_win_width = 0    # for adaptive font
        self._is_dragging = False
        self._drag_sample_id = None
        self._color_sample_id = None

        # Data
        self.checkpoints: List[Checkpoint] = []
        self.custom_messages: dict = {}  # percentage -> (text, color)
        self.current_message = ("🚀 设置时间，开始你的倒计时！", COLORS["accent_blue"])
        self.last_percentage_shown = -1

        self._build_ui()
        self._setup_resize()
        self._load_saved_config()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─── UI Construction ──────────────────────────────────────────────────

    def _build_ui(self):
        # Main container
        self.main_frame = tk.Frame(self.root, bg=COLORS["bg_dark"])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self._build_header()
        self._build_timer_display()
        self._build_progress_area()
        self._build_message_area()
        self._build_controls()
        self._build_settings_panel()
        self._build_checkpoints_panel()
        self._build_custom_messages_panel()
        self._build_compact_overlay()

    def _build_header(self):
        header = tk.Frame(self.main_frame, bg=COLORS["bg_dark"], height=56)
        header.pack(fill=tk.X, padx=20, pady=(16, 0))
        header.pack_propagate(False)

        # Title
        tk.Label(header, text="⏱  倒计时", font=("Courier New", 16, "bold"),
                 bg=COLORS["bg_dark"], fg=COLORS["text_primary"]).pack(side=tk.LEFT, anchor="w")

        # Compact toggle button
        self.compact_btn = tk.Button(
            header, text="精简模式", font=("Microsoft YaHei UI", 10),
            bg=COLORS["bg_panel"], fg=COLORS["text_secondary"],
            relief=tk.FLAT, bd=0, padx=14, pady=6,
            activebackground=COLORS["border_glow"], activeforeground=COLORS["bg_dark"],
            cursor="hand2", command=self._toggle_compact
        )
        self.compact_btn.pack(side=tk.RIGHT, anchor="e")

        # Divider
        divider = tk.Frame(self.main_frame, bg=COLORS["border"], height=1)
        divider.pack(fill=tk.X, padx=20, pady=(8, 0))

    def _build_timer_display(self):
        self.timer_frame = tk.Frame(self.main_frame, bg=COLORS["bg_card"],
                                     relief=tk.FLAT, bd=0)
        self.timer_frame.pack(fill=tk.X, padx=20, pady=(16, 0))

        inner = tk.Frame(self.timer_frame, bg=COLORS["bg_card"])
        inner.pack(padx=30, pady=24)

        # Time display with colon separators
        time_container = tk.Frame(inner, bg=COLORS["bg_card"])
        time_container.pack()

        self.hour_var = tk.StringVar(value="00")
        self.min_var = tk.StringVar(value="00")
        self.sec_var = tk.StringVar(value="00")

        def make_digit(parent, var, is_running=False):
            f = tk.Frame(parent, bg=COLORS["bg_panel"], padx=16, pady=8)
            f.pack(side=tk.LEFT)
            lbl = tk.Label(f, textvariable=var, font=("Courier New", 52, "bold"),
                           bg=COLORS["bg_panel"], fg=COLORS["text_primary"],
                           width=2, anchor="center")
            lbl.pack()
            return lbl

        def make_sep(parent):
            tk.Label(parent, text=":", font=("Courier New", 48, "bold"),
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"]).pack(side=tk.LEFT, padx=4)

        self.hour_lbl = make_digit(time_container, self.hour_var)
        make_sep(time_container)
        self.min_lbl = make_digit(time_container, self.min_var)
        make_sep(time_container)
        self.sec_lbl = make_digit(time_container, self.sec_var)

        # Unit labels
        units_frame = tk.Frame(inner, bg=COLORS["bg_card"])
        units_frame.pack(fill=tk.X, pady=(4, 0))
        for unit in ["时", "分", "秒"]:
            tk.Label(units_frame, text=unit, font=("Microsoft YaHei UI", 10),
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"]).pack(side=tk.LEFT, expand=True)

    def _build_progress_area(self):
        self.progress_frame = tk.Frame(self.main_frame, bg=COLORS["bg_dark"])
        self.progress_frame.pack(fill=tk.X, padx=20, pady=(14, 0))

        # Percentage label
        pct_row = tk.Frame(self.progress_frame, bg=COLORS["bg_dark"])
        pct_row.pack(fill=tk.X)

        self.pct_label = tk.Label(pct_row, text="0%", font=("Courier New", 11, "bold"),
                                   bg=COLORS["bg_dark"], fg=COLORS["accent_cyan"])
        self.pct_label.pack(side=tk.RIGHT)

        tk.Label(pct_row, text="剩余进度", font=("Microsoft YaHei UI", 10),
                 bg=COLORS["bg_dark"], fg=COLORS["text_muted"]).pack(side=tk.LEFT)

        # Canvas progress bar
        self.progress_canvas = tk.Canvas(self.progress_frame, height=12,
                                          bg=COLORS["progress_bg"], highlightthickness=0,
                                          relief=tk.FLAT)
        self.progress_canvas.pack(fill=tk.X, pady=(6, 0))
        self.progress_canvas.bind("<Configure>", self._redraw_progress)

        # Checkpoint markers row
        self.checkpoint_canvas = tk.Canvas(self.progress_frame, height=20,
                                            bg=COLORS["bg_dark"], highlightthickness=0)
        self.checkpoint_canvas.pack(fill=tk.X, pady=(2, 0))

    def _build_message_area(self):
        self.msg_frame = tk.Frame(self.main_frame, bg=COLORS["bg_card"])
        self.msg_frame.pack(fill=tk.X, padx=20, pady=(14, 0))

        inner = tk.Frame(self.msg_frame, bg=COLORS["bg_card"])
        inner.pack(fill=tk.X, padx=20, pady=16)

        self.message_label = tk.Label(
            inner, text=self.current_message[0],
            font=("Microsoft YaHei UI", 13, "bold"),
            bg=COLORS["bg_card"], fg=self.current_message[1],
            wraplength=500, justify=tk.CENTER
        )
        self.message_label.pack()

    def _build_controls(self):
        self.controls_frame = tk.Frame(self.main_frame, bg=COLORS["bg_dark"])
        self.controls_frame.pack(fill=tk.X, padx=20, pady=(16, 0))

        btn_config = dict(font=("Microsoft YaHei UI", 11, "bold"), relief=tk.FLAT,
                          bd=0, padx=20, pady=10, cursor="hand2")

        self.start_btn = tk.Button(
            self.controls_frame, text="▶  开始",
            bg=COLORS["accent_blue"], fg=COLORS["bg_dark"],
            activebackground=COLORS["accent_cyan"], activeforeground=COLORS["bg_dark"],
            command=self._start_pause, **btn_config
        )
        self.start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 6))

        self.reset_btn = tk.Button(
            self.controls_frame, text="↺  重置",
            bg=COLORS["bg_panel"], fg=COLORS["text_secondary"],
            activebackground=COLORS["border"], activeforeground=COLORS["text_primary"],
            command=self._reset, **btn_config
        )
        self.reset_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(6, 0))

    def _build_settings_panel(self):
        # Collapsible settings
        self.settings_visible = tk.BooleanVar(value=True)

        header = tk.Frame(self.main_frame, bg=COLORS["bg_dark"])
        header.pack(fill=tk.X, padx=20, pady=(16, 0))

        self.settings_toggle = tk.Button(
            header, text="▼  时间设置", font=("Microsoft YaHei UI", 10, "bold"),
            bg=COLORS["bg_dark"], fg=COLORS["text_secondary"],
            relief=tk.FLAT, bd=0, cursor="hand2",
            command=lambda: self._toggle_section("settings")
        )
        self.settings_toggle.pack(side=tk.LEFT)

        self.settings_panel = tk.Frame(self.main_frame, bg=COLORS["bg_card"])
        self.settings_panel.pack(fill=tk.X, padx=20, pady=(8, 0))

        inner = tk.Frame(self.settings_panel, bg=COLORS["bg_card"])
        inner.pack(fill=tk.X, padx=20, pady=16)

        tk.Label(inner, text="设置倒计时时长：", font=("Microsoft YaHei UI", 10),
                 bg=COLORS["bg_card"], fg=COLORS["text_secondary"]).pack(anchor="w", pady=(0, 10))

        spin_row = tk.Frame(inner, bg=COLORS["bg_card"])
        spin_row.pack(fill=tk.X)

        spin_style = dict(font=("Courier New", 18, "bold"), width=4,
                          bg=COLORS["bg_panel"], fg=COLORS["text_primary"],
                          relief=tk.FLAT, bd=0, insertbackground=COLORS["accent_blue"],
                          justify=tk.CENTER, highlightthickness=1,
                          highlightcolor=COLORS["accent_blue"],
                          highlightbackground=COLORS["border"])

        for label, var_name, max_val in [("时", "h_var", 99), ("分", "m_var", 59), ("秒", "s_var", 59)]:
            frame = tk.Frame(spin_row, bg=COLORS["bg_card"])
            frame.pack(side=tk.LEFT, expand=True, padx=6)

            setattr(self, var_name, tk.StringVar(value="00"))
            vcmd = (self.root.register(lambda v, mx=max_val: self._validate_spin(v, mx)), "%P")

            entry = tk.Entry(frame, textvariable=getattr(self, var_name),
                             validate="key", validatecommand=vcmd, **spin_style)
            entry.pack(fill=tk.X)

            tk.Label(frame, text=label, font=("Microsoft YaHei UI", 9),
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"]).pack(pady=(4, 0))

        # Set button
        set_btn = tk.Button(
            inner, text="✓ 应用时间", font=("Microsoft YaHei UI", 10, "bold"),
            bg=COLORS["accent_green"], fg=COLORS["bg_dark"],
            relief=tk.FLAT, bd=0, padx=16, pady=8, cursor="hand2",
            command=self._apply_time
        )
        set_btn.pack(pady=(12, 0))

        # ── Reference start point ─────────────────────────────────────
        tk.Frame(inner, bg=COLORS["border"], height=1).pack(fill=tk.X, pady=(14, 0))

        ref_header = tk.Frame(inner, bg=COLORS["bg_card"])
        ref_header.pack(fill=tk.X, pady=(10, 0))
        tk.Label(ref_header, text="📍 参考起点（可选）",
                 font=("Microsoft YaHei UI", 10, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["accent_yellow"]).pack(side=tk.LEFT)

        ref_tip = tk.Label(inner,
            text="设置后，进度条和百分比将基于参考起点计算。\n"
                 "例：参考起点 4:00:00，当前从 2:00:00 开始，\n"
                 "则进度条已走一半，百分比从 50% 继续。",
            font=("Microsoft YaHei UI", 8), bg=COLORS["bg_card"],
            fg=COLORS["text_muted"], justify=tk.LEFT)
        ref_tip.pack(anchor="w", pady=(4, 8))

        ref_spin_row = tk.Frame(inner, bg=COLORS["bg_card"])
        ref_spin_row.pack(fill=tk.X)

        ref_spin_style = dict(font=("Courier New", 14, "bold"), width=4,
                              bg=COLORS["bg_panel"], fg=COLORS["accent_yellow"],
                              relief=tk.FLAT, bd=0, insertbackground=COLORS["accent_yellow"],
                              justify=tk.CENTER, highlightthickness=1,
                              highlightcolor=COLORS["accent_yellow"],
                              highlightbackground=COLORS["border"])

        for lbl, var_name, max_v in [("时", "ref_h_var", 99), ("分", "ref_m_var", 59), ("秒", "ref_s_var", 59)]:
            fr = tk.Frame(ref_spin_row, bg=COLORS["bg_card"])
            fr.pack(side=tk.LEFT, expand=True, padx=6)
            setattr(self, var_name, tk.StringVar(value="00"))
            vcmd2 = (self.root.register(lambda v, mx=max_v: self._validate_spin(v, mx)), "%P")
            tk.Entry(fr, textvariable=getattr(self, var_name),
                     validate="key", validatecommand=vcmd2,
                     **ref_spin_style).pack(fill=tk.X)
            tk.Label(fr, text=lbl, font=("Microsoft YaHei UI", 8),
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"]).pack(pady=(3, 0))

        ref_btn_row = tk.Frame(inner, bg=COLORS["bg_card"])
        ref_btn_row.pack(fill=tk.X, pady=(10, 0))

        tk.Button(ref_btn_row, text="✓ 设置参考起点",
                  font=("Microsoft YaHei UI", 9, "bold"),
                  bg=COLORS["accent_yellow"], fg=COLORS["bg_dark"],
                  relief=tk.FLAT, bd=0, padx=14, pady=6, cursor="hand2",
                  command=self._apply_ref).pack(side=tk.LEFT)

        self.ref_label = tk.Label(ref_btn_row, text="未设置",
                                   font=("Courier New", 9),
                                   bg=COLORS["bg_card"], fg=COLORS["text_muted"])
        self.ref_label.pack(side=tk.LEFT, padx=(10, 0))

        tk.Button(ref_btn_row, text="✕ 清除",
                  font=("Microsoft YaHei UI", 8),
                  bg=COLORS["bg_panel"], fg=COLORS["accent_red"],
                  relief=tk.FLAT, bd=0, padx=8, pady=6, cursor="hand2",
                  command=self._clear_ref).pack(side=tk.LEFT, padx=(8, 0))

    def _apply_ref(self):
        """Set the reference start point."""
        try:
            h = int(self.ref_h_var.get() or 0)
            m = int(self.ref_m_var.get() or 0)
            s = int(self.ref_s_var.get() or 0)
            ref = h * 3600 + m * 60 + s
        except ValueError:
            messagebox.showerror("错误", "请输入有效时间！")
            return
        if ref <= 0:
            self._clear_ref()
            return
        if self.total_seconds > 0 and ref < self.total_seconds:
            messagebox.showerror("错误", "参考起点必须 ≥ 当前倒计时时长！")
            return
        self.ref_seconds = ref
        rh, rem = divmod(ref, 3600)
        rm, rs = divmod(rem, 60)
        self.ref_label.config(text=f"{rh:02d}:{rm:02d}:{rs:02d}", fg=COLORS["accent_yellow"])
        self._update_display()
        self._draw_checkpoint_markers()
        self._autosave()

    def _clear_ref(self):
        """Remove reference start point."""
        self.ref_seconds = 0
        self.ref_h_var.set("00")
        self.ref_m_var.set("00")
        self.ref_s_var.set("00")
        self.ref_label.config(text="未设置", fg=COLORS["text_muted"])
        self._update_display()
        self._draw_checkpoint_markers()
        self._autosave()

    def _build_checkpoints_panel(self):
        header = tk.Frame(self.main_frame, bg=COLORS["bg_dark"])
        header.pack(fill=tk.X, padx=20, pady=(12, 0))

        self.cp_toggle = tk.Button(
            header, text="▼  检查点", font=("Microsoft YaHei UI", 10, "bold"),
            bg=COLORS["bg_dark"], fg=COLORS["text_secondary"],
            relief=tk.FLAT, bd=0, cursor="hand2",
            command=lambda: self._toggle_section("checkpoints")
        )
        self.cp_toggle.pack(side=tk.LEFT)

        self.cp_panel = tk.Frame(self.main_frame, bg=COLORS["bg_card"])
        self.cp_panel.pack(fill=tk.X, padx=20, pady=(8, 0))

        self.cp_inner = tk.Frame(self.cp_panel, bg=COLORS["bg_card"])
        self.cp_inner.pack(fill=tk.X, padx=20, pady=12)

        add_row = tk.Frame(self.cp_inner, bg=COLORS["bg_card"])
        add_row.pack(fill=tk.X)

        tk.Label(add_row, text="名称:", font=("Microsoft YaHei UI", 9),
                 bg=COLORS["bg_card"], fg=COLORS["text_secondary"]).pack(side=tk.LEFT)

        self.cp_name_var = tk.StringVar()
        tk.Entry(add_row, textvariable=self.cp_name_var,
                 font=("Microsoft YaHei UI", 10),
                 bg=COLORS["bg_panel"], fg=COLORS["text_primary"],
                 relief=tk.FLAT, bd=0, width=12, insertbackground=COLORS["accent_blue"],
                 highlightthickness=1, highlightbackground=COLORS["border"],
                 highlightcolor=COLORS["accent_blue"]).pack(side=tk.LEFT, padx=(4, 8))

        for lbl, var_name in [("时", "cp_h"), ("分", "cp_m"), ("秒", "cp_s")]:
            setattr(self, f"{var_name}_var", tk.StringVar(value="00"))
            tk.Entry(add_row, textvariable=getattr(self, f"{var_name}_var"),
                     font=("Courier New", 10), width=3,
                     bg=COLORS["bg_panel"], fg=COLORS["text_primary"],
                     relief=tk.FLAT, bd=0, justify=tk.CENTER,
                     highlightthickness=1, highlightbackground=COLORS["border"],
                     highlightcolor=COLORS["accent_blue"],
                     insertbackground=COLORS["accent_blue"]).pack(side=tk.LEFT)
            tk.Label(add_row, text=lbl, font=("Microsoft YaHei UI", 8),
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"]).pack(side=tk.LEFT, padx=(1, 6))

        tk.Button(add_row, text="+ 添加", font=("Microsoft YaHei UI", 9, "bold"),
                  bg=COLORS["accent_blue"], fg=COLORS["bg_dark"],
                  relief=tk.FLAT, bd=0, padx=10, pady=4, cursor="hand2",
                  command=self._add_checkpoint).pack(side=tk.LEFT)

        # Checkpoint list
        self.cp_list_frame = tk.Frame(self.cp_inner, bg=COLORS["bg_card"])
        self.cp_list_frame.pack(fill=tk.X, pady=(8, 0))

    def _build_custom_messages_panel(self):
        header = tk.Frame(self.main_frame, bg=COLORS["bg_dark"])
        header.pack(fill=tk.X, padx=20, pady=(12, 0))

        self.msg_toggle = tk.Button(
            header, text="▼  自定义提示语", font=("Microsoft YaHei UI", 10, "bold"),
            bg=COLORS["bg_dark"], fg=COLORS["text_secondary"],
            relief=tk.FLAT, bd=0, cursor="hand2",
            command=lambda: self._toggle_section("messages")
        )
        self.msg_toggle.pack(side=tk.LEFT)

        self.msg_panel = tk.Frame(self.main_frame, bg=COLORS["bg_card"])
        self.msg_panel.pack(fill=tk.X, padx=20, pady=(8, 0))

        inner = tk.Frame(self.msg_panel, bg=COLORS["bg_card"])
        inner.pack(fill=tk.X, padx=20, pady=12)

        tk.Label(inner, text="在特定百分比时显示自定义消息：",
                 font=("Microsoft YaHei UI", 9),
                 bg=COLORS["bg_card"], fg=COLORS["text_secondary"]).pack(anchor="w", pady=(0, 8))

        add_row = tk.Frame(inner, bg=COLORS["bg_card"])
        add_row.pack(fill=tk.X)

        # Percentage dropdown
        self.msg_pct_var = tk.StringVar(value="50")
        pct_options = [str(p) for p in PERCENTAGE_OPTIONS]
        pct_menu = ttk.Combobox(add_row, textvariable=self.msg_pct_var,
                                 values=pct_options, width=5,
                                 font=("Courier New", 10), state="readonly")
        pct_menu.pack(side=tk.LEFT, padx=(0, 6))

        tk.Label(add_row, text="%  消息:", font=("Microsoft YaHei UI", 9),
                 bg=COLORS["bg_card"], fg=COLORS["text_secondary"]).pack(side=tk.LEFT)

        self.msg_text_var = tk.StringVar()
        tk.Entry(add_row, textvariable=self.msg_text_var,
                 font=("Microsoft YaHei UI", 10), width=22,
                 bg=COLORS["bg_panel"], fg=COLORS["text_primary"],
                 relief=tk.FLAT, bd=0, insertbackground=COLORS["accent_blue"],
                 highlightthickness=1, highlightbackground=COLORS["border"],
                 highlightcolor=COLORS["accent_blue"]).pack(side=tk.LEFT, padx=(4, 8))

        tk.Button(add_row, text="+ 添加", font=("Microsoft YaHei UI", 9, "bold"),
                  bg=COLORS["accent_purple"], fg=COLORS["bg_dark"],
                  relief=tk.FLAT, bd=0, padx=10, pady=4, cursor="hand2",
                  command=self._add_custom_message).pack(side=tk.LEFT)

        # Message list
        self.msg_list_frame = tk.Frame(inner, bg=COLORS["bg_card"])
        self.msg_list_frame.pack(fill=tk.X, pady=(8, 0))

        # Bottom padding
        tk.Frame(self.main_frame, bg=COLORS["bg_dark"], height=20).pack()

    def _build_compact_overlay(self):
        """Build the compact mode overlay window content"""
        self.compact_window = None

    # ─── Timer Logic ──────────────────────────────────────────────────────

    def _validate_spin(self, value, max_val):
        if value == "":
            return True
        try:
            v = int(value)
            return 0 <= v <= max_val and len(value) <= 2
        except ValueError:
            return False

    def _apply_time(self):
        if self.running:
            messagebox.showwarning("提示", "请先停止计时再修改时间！")
            return
        try:
            h = int(self.h_var.get() or 0)
            m = int(self.m_var.get() or 0)
            s = int(self.s_var.get() or 0)
            total = h * 3600 + m * 60 + s
            if total <= 0:
                messagebox.showerror("错误", "请设置大于0的时间！")
                return
            self.total_seconds = total
            self.remaining_seconds = total
            self.last_percentage_shown = -1
            self._update_display()
            self._reset_checkpoints()
            self._update_message(100)
            self._draw_checkpoint_markers()
            self._autosave()
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字！")

    def _start_pause(self):
        if self.total_seconds == 0:
            messagebox.showwarning("提示", "请先设置并应用倒计时时间！")
            return

        if not self.running and not self.paused:
            # Fresh start
            if self.remaining_seconds <= 0:
                self.remaining_seconds = self.total_seconds
                self._reset_checkpoints()
            self.running = True
            self.paused = False
            self._last_tick = time.time()
            self.start_btn.config(text="⏸  暂停", bg=COLORS["accent_orange"])
            self._tick()
        elif self.running and not self.paused:
            # Pause
            self.paused = True
            self.running = False
            self.start_btn.config(text="▶  继续", bg=COLORS["accent_green"])
            if self._after_id:
                self.root.after_cancel(self._after_id)
        else:
            # Resume
            self.running = True
            self.paused = False
            self._last_tick = time.time()
            self.start_btn.config(text="⏸  暂停", bg=COLORS["accent_orange"])
            self._tick()

    def _reset(self):
        self.running = False
        self.paused = False
        if self._after_id:
            self.root.after_cancel(self._after_id)
        self.remaining_seconds = self.total_seconds
        self.last_percentage_shown = -1
        self._reset_checkpoints()
        self._update_display()
        self._update_message(100 if self.total_seconds > 0 else None)
        self.start_btn.config(text="▶  开始", bg=COLORS["accent_blue"])

    def _tick(self):
        if not self.running:
            return

        now = time.time()
        elapsed = now - self._last_tick
        self._last_tick = now

        self.remaining_seconds = max(0, self.remaining_seconds - elapsed)

        self._update_display()

        if self.total_seconds > 0:
            ref = self.ref_seconds if self.ref_seconds > 0 else self.total_seconds
            pct = int((self.remaining_seconds / ref) * 100)
            self._update_message(pct)
            self._check_checkpoints()
            self._redraw_progress()

        if self.remaining_seconds <= 0:
            self._on_finish()
            return

        self._after_id = self.root.after(100, self._tick)

    def _on_finish(self):
        self.running = False
        self.remaining_seconds = 0
        self._update_display()
        self._update_message(0)
        self.start_btn.config(text="▶  开始", bg=COLORS["accent_blue"])
        self._flash_finish()

    def _flash_finish(self):
        """Flash the timer display to celebrate"""
        colors = [COLORS["accent_pink"], COLORS["accent_yellow"],
                  COLORS["accent_green"], COLORS["accent_cyan"], COLORS["accent_purple"]]
        self._flash_count = 0

        def do_flash():
            if self._flash_count >= 10:
                for lbl in [self.hour_lbl, self.min_lbl, self.sec_lbl]:
                    lbl.config(fg=COLORS["text_primary"])
                return
            color = colors[self._flash_count % len(colors)]
            for lbl in [self.hour_lbl, self.min_lbl, self.sec_lbl]:
                lbl.config(fg=color)
            self._flash_count += 1
            self.root.after(200, do_flash)

        do_flash()

    def _update_display(self):
        r = max(0, int(self.remaining_seconds))
        h = r // 3600
        m = (r % 3600) // 60
        s = r % 60
        self.hour_var.set(f"{h:02d}")
        self.min_var.set(f"{m:02d}")
        self.sec_var.set(f"{s:02d}")

        ref = self.ref_seconds if self.ref_seconds > 0 else self.total_seconds
        if ref > 0:
            pct = (self.remaining_seconds / ref) * 100
            self.pct_label.config(text=f"{pct:.1f}%")
        else:
            self.pct_label.config(text="—")

        # Update compact window if open
        if self.compact_window and self.compact_window.winfo_exists():
            self._update_compact_display()

    def _update_message(self, pct):
        if pct is None:
            return

        # Find the right threshold
        thresholds = sorted(PERCENTAGE_OPTIONS, reverse=True)
        chosen_pct = None
        for t in thresholds:
            if pct <= t:
                chosen_pct = t

        if chosen_pct is None:
            chosen_pct = 100

        if chosen_pct == self.last_percentage_shown and pct != 0:
            return

        # Check custom messages first
        if chosen_pct in self.custom_messages:
            text, color = self.custom_messages[chosen_pct]
        elif chosen_pct in DEFAULT_MESSAGES:
            text, color = DEFAULT_MESSAGES[chosen_pct]
        else:
            return

        self.last_percentage_shown = chosen_pct
        self.current_message = (text, color)
        self.message_label.config(text=text, fg=color)

        if self.compact_window and self.compact_window.winfo_exists():
            self._update_compact_display()

    # ─── Progress Bar ──────────────────────────────────────────────────────

    def _redraw_progress(self, event=None):
        canvas = self.progress_canvas
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1:
            return

        canvas.delete("all")
        canvas.create_rectangle(0, 0, w, h, fill=COLORS["progress_bg"], outline="", width=0)

        ref = self.ref_seconds if self.ref_seconds > 0 else self.total_seconds
        if ref <= 0:
            return

        remaining_frac = max(0.0, min(1.0, self.remaining_seconds / ref))
        # elapsed fraction: how far the bar has filled left→right
        elapsed_frac = 1.0 - remaining_frac
        fill_w = max(0, int(w * elapsed_frac))

        if fill_w <= 0:
            return

        # Draw filled portion in fine segments, each colored by its position
        SEG = max(1, fill_w // 3)
        for i in range(SEG):
            x0 = int(i * fill_w / SEG)
            x1 = int((i + 1) * fill_w / SEG)
            # position_frac: 0=leftmost(start) → 1=rightmost(now, minimum remaining)
            pos = (x0 + x1) / 2 / w   # 0..1 across full bar
            # remaining at this pixel = 1 - pos (as fraction of ref)
            rem_here = 1.0 - pos
            color = get_progress_color(rem_here)
            canvas.create_rectangle(x0, 0, x1, h, fill=color, outline="", width=0)

        # Glow tip at the right edge of filled portion
        if fill_w >= 3:
            canvas.create_rectangle(fill_w - 3, 0, fill_w, h,
                                     fill="white", outline="", width=0,
                                     stipple="gray50")

    def _draw_checkpoint_markers(self):
        canvas = self.checkpoint_canvas
        canvas.delete("all")
        ref = self.ref_seconds if self.ref_seconds > 0 else self.total_seconds
        if not self.checkpoints or ref <= 0:
            return

        w = canvas.winfo_width()
        if w <= 1:
            self.root.after(100, self._draw_checkpoint_markers)
            return

        for cp in self.checkpoints:
            # Position on bar: left=start(ref), right=end(0)
            # remaining_at=ref → x=0 (very left); remaining_at=0 → x=w (very right)
            pos = 1.0 - (cp.remaining_at / ref)
            x = int(pos * w)
            color = COLORS["accent_yellow"] if not cp.triggered else COLORS["text_muted"]
            canvas.create_line(x, 0, x, 14, fill=color, width=2)
            # Show countdown clock value at trigger
            h, rem = divmod(cp.remaining_at, 3600)
            mi, sc = divmod(rem, 60)
            time_tag = f"{h}:{mi:02d}" if h > 0 else f"{mi}:{sc:02d}"
            canvas.create_text(x, 18, text=f"{cp.name[:3]} {time_tag}",
                                fill=color, font=("Microsoft YaHei UI", 7), anchor="s")

    def _check_checkpoints(self):
        if self.total_seconds <= 0:
            return
        for cp in self.checkpoints:
            if not cp.triggered and self.remaining_seconds <= cp.remaining_at:
                cp.triggered = True
                self._notify_checkpoint(cp)
                self._refresh_checkpoint_list()
                self._draw_checkpoint_markers()

    def _notify_checkpoint(self, cp):
        # Flash the message area
        original_bg = self.msg_frame.cget("bg")
        self.message_label.config(
            text=f"📍 检查点：{cp.name}",
            fg=COLORS["accent_yellow"]
        )
        self.msg_frame.config(bg=COLORS["accent_yellow"])
        self.root.after(800, lambda: self.msg_frame.config(bg=original_bg))
        self.root.after(1200, lambda: self.message_label.config(
            text=self.current_message[0], fg=self.current_message[1]))

    # ─── Checkpoints Management ───────────────────────────────────────────

    def _add_checkpoint(self):
        name = self.cp_name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入检查点名称！")
            return
        try:
            h = int(self.cp_h_var.get() or 0)
            m = int(self.cp_m_var.get() or 0)
            s = int(self.cp_s_var.get() or 0)
            remaining_at = h * 3600 + m * 60 + s
        except ValueError:
            messagebox.showerror("错误", "请输入有效时间！")
            return

        ref = self.ref_seconds if self.ref_seconds > 0 else self.total_seconds
        if ref > 0 and remaining_at > ref:
            messagebox.showerror("错误", "检查点时间不能超过总时长！")
            return

        cp = Checkpoint(name=name, remaining_at=remaining_at)
        self.checkpoints.append(cp)
        # Sort descending: largest remaining time first (fires earliest)
        self.checkpoints.sort(key=lambda c: c.remaining_at, reverse=True)
        self.cp_name_var.set("")
        self._refresh_checkpoint_list()
        self._draw_checkpoint_markers()
        self._autosave()

    def _reset_checkpoints(self):
        for cp in self.checkpoints:
            cp.triggered = False
        self._refresh_checkpoint_list()

    def _refresh_checkpoint_list(self):
        for widget in self.cp_list_frame.winfo_children():
            widget.destroy()

        if not self.checkpoints:
            tk.Label(self.cp_list_frame, text="暂无检查点",
                     font=("Microsoft YaHei UI", 9),
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"]).pack(anchor="w")
            return

        for i, cp in enumerate(self.checkpoints):
            row = tk.Frame(self.cp_list_frame, bg=COLORS["bg_panel"])
            row.pack(fill=tk.X, pady=2)

            h, rem = divmod(cp.remaining_at, 3600)
            m, s = divmod(rem, 60)
            time_str = f"{h:02d}:{m:02d}:{s:02d}"

            color = COLORS["text_muted"] if cp.triggered else COLORS["accent_yellow"]
            mark = "✓" if cp.triggered else "◆"
            tk.Label(row, text=f"  {mark}  {cp.name}",
                     font=("Microsoft YaHei UI", 9, "bold"),
                     bg=COLORS["bg_panel"], fg=color).pack(side=tk.LEFT, padx=6, pady=4)
            tk.Label(row, text=f"倒计时至 {time_str}",
                     font=("Courier New", 9),
                     bg=COLORS["bg_panel"], fg=COLORS["text_muted"]).pack(side=tk.LEFT)

            del_btn = tk.Button(row, text="✕", font=("Microsoft YaHei UI", 8),
                                bg=COLORS["bg_panel"], fg=COLORS["accent_red"],
                                relief=tk.FLAT, bd=0, cursor="hand2",
                                command=lambda idx=i: self._delete_checkpoint(idx))
            del_btn.pack(side=tk.RIGHT, padx=6)

    def _delete_checkpoint(self, idx):
        self.checkpoints.pop(idx)
        self._refresh_checkpoint_list()
        self._draw_checkpoint_markers()
        self._autosave()

    # ─── Custom Messages ──────────────────────────────────────────────────

    def _add_custom_message(self):
        pct_str = self.msg_pct_var.get()
        text = self.msg_text_var.get().strip()
        if not text:
            messagebox.showwarning("提示", "请输入提示语！")
            return
        try:
            pct = int(pct_str)
        except ValueError:
            messagebox.showerror("错误", "无效的百分比！")
            return

        # Pick color based on pct
        color_map = {
            100: COLORS["accent_blue"], 70: COLORS["accent_blue"],
            50: COLORS["accent_cyan"], 25: COLORS["accent_yellow"],
            20: COLORS["accent_orange"], 10: COLORS["accent_red"],
            5: COLORS["accent_red"], 2: COLORS["accent_pink"],
            1: COLORS["accent_pink"], 0: COLORS["accent_purple"]
        }
        color = color_map.get(pct, COLORS["accent_blue"])

        self.custom_messages[pct] = (text, color)
        self.msg_text_var.set("")
        self._refresh_message_list()
        self._autosave()

    def _refresh_message_list(self):
        for widget in self.msg_list_frame.winfo_children():
            widget.destroy()

        if not self.custom_messages:
            tk.Label(self.msg_list_frame, text="暂无自定义消息",
                     font=("Microsoft YaHei UI", 9),
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"]).pack(anchor="w")
            return

        for pct in sorted(self.custom_messages.keys(), reverse=True):
            text, color = self.custom_messages[pct]
            row = tk.Frame(self.msg_list_frame, bg=COLORS["bg_panel"])
            row.pack(fill=tk.X, pady=2)

            tk.Label(row, text=f"  {pct}%",
                     font=("Courier New", 9, "bold"),
                     bg=COLORS["bg_panel"], fg=color, width=5).pack(side=tk.LEFT, pady=4)
            tk.Label(row, text=text, font=("Microsoft YaHei UI", 9),
                     bg=COLORS["bg_panel"], fg=COLORS["text_secondary"]).pack(side=tk.LEFT, padx=4)

            del_btn = tk.Button(row, text="✕", font=("Microsoft YaHei UI", 8),
                                bg=COLORS["bg_panel"], fg=COLORS["accent_red"],
                                relief=tk.FLAT, bd=0, cursor="hand2",
                                command=lambda p=pct: self._delete_custom_message(p))
            del_btn.pack(side=tk.RIGHT, padx=6)

    def _delete_custom_message(self, pct):
        self.custom_messages.pop(pct, None)
        self._refresh_message_list()
        self._autosave()

    # ─── Compact Mode (Win11 Taskbar Style) ───────────────────────────────

    def _toggle_compact(self):
        if not self.compact_window or not self.compact_window.winfo_exists():
            self._open_compact()
        else:
            self.compact_window.destroy()
            self.compact_window = None
            self._stop_color_sampling()
            self.compact_btn.config(text="精简模式", fg=COLORS["text_secondary"])

    def _open_compact(self):
        """Open the compact overlay bar with all three new features."""
        # ── Default compact settings ──────────────────────────────────
        if not hasattr(self, '_compact_settings'):
            self._compact_settings = {
                "show_icon":    True,
                "show_time":    True,
                "show_progress":True,
                "show_pct":     True,
                "show_message": True,
                "alpha":        0.90,
                "auto_color":   True,
            }
        cfg = self._compact_settings

        # ── Initial theme (will be overridden by auto-color) ──────────
        self._cw_theme = {
            "bg":      "#D8ECF8",
            "border":  "#B0CDE0",
            "text":    "#1A2A38",
            "text2":   "#3A6080",
            "accent":  "#0067C0",
            "bar_bg":  "#B8D4E8",
        }

        cw = tk.Toplevel(self.root)
        self.compact_window = cw
        cw.title("")
        cw.overrideredirect(True)
        cw.attributes("-topmost", True)
        cw.attributes("-alpha", cfg["alpha"])
        cw.resizable(False, False)

        BAR_H = 48
        scr_w = cw.winfo_screenwidth()
        scr_h = cw.winfo_screenheight()
        cw.configure(bg=self._cw_theme["bg"])

        self._drag_x = 0
        self._drag_y = 0
        self._color_sample_id = None
        self._compact_bar_initial_x = None  # will be set after first build

        # ── Build the bar UI (rebuilds on theme change) ───────────────
        self._compact_cw = cw
        self._compact_bar_h = BAR_H
        self._build_compact_bar()

        # Size naturally, then position at bottom-center
        cw.update_idletasks()
        bar_w = cw.winfo_reqwidth()
        x = (scr_w - bar_w) // 2
        y = scr_h - BAR_H - 48
        cw.geometry(f"+{x}+{y}")
        self.compact_btn.config(text="关闭精简", fg=COLORS["accent_cyan"])

        # ── Start auto color sampling ─────────────────────────────────
        if cfg["auto_color"]:
            self._start_color_sampling()

        self._update_compact_display()

        # ── Right-click: open settings panel ─────────────────────────
        cw.bind("<Button-3>", lambda e: self._open_compact_settings())

    def _build_compact_bar(self):
        """Build / rebuild all widgets inside the compact window."""
        cw = self._compact_cw
        cfg = self._compact_settings
        t = self._cw_theme

        # Clear existing children
        for child in cw.winfo_children():
            child.destroy()

        # Top accent line
        self._cw_accent_line = tk.Frame(cw, bg=t["accent"], height=2)
        self._cw_accent_line.pack(fill=tk.X, side=tk.TOP)

        # Main row
        row = tk.Frame(cw, bg=t["bg"])
        row.pack(fill=tk.BOTH, expand=True)
        self._cw_row = row

        def sep():
            tk.Frame(row, bg=t["border"], width=1).pack(
                side=tk.LEFT, fill=tk.Y, padx=(10, 10), pady=8)

        # ── Clock icon ────────────────────────────────────────────────
        if cfg["show_icon"]:
            tk.Label(row, text="⏱", font=("Segoe UI Emoji", 13),
                     bg=t["bg"], fg=t["text2"]).pack(side=tk.LEFT, padx=(14, 4))

        # ── Time ──────────────────────────────────────────────────────
        if cfg["show_time"]:
            self.compact_time_var = tk.StringVar(value="00:00:00")
            self.compact_time_lbl = tk.Label(
                row, textvariable=self.compact_time_var,
                font=("Segoe UI", 16, "bold"),
                bg=t["bg"], fg=t["text"]
            )
            self.compact_time_lbl.pack(side=tk.LEFT, padx=(4, 0))
        else:
            self.compact_time_var = tk.StringVar(value="00:00:00")
            self.compact_time_lbl = None

        # ── Progress area ──────────────────────────────────────────────
        if cfg["show_progress"] or cfg["show_pct"]:
            sep()
            prog_frame = tk.Frame(row, bg=t["bg"], width=140)
            prog_frame.pack(side=tk.LEFT, fill=tk.Y)
            prog_frame.pack_propagate(False)

            self.compact_pct_var = tk.StringVar(value="—")
            if cfg["show_pct"]:
                tk.Label(prog_frame, textvariable=self.compact_pct_var,
                         font=("Segoe UI", 7, "bold"), bg=t["bg"],
                         fg=t["accent"]).pack(anchor="w", pady=(7, 0), padx=2)

            if cfg["show_progress"]:
                self.compact_progress = tk.Canvas(
                    prog_frame, height=4, bg=t["bar_bg"],
                    highlightthickness=0, bd=0)
                self.compact_progress.pack(fill=tk.X, pady=(1, 0), padx=2)
                self.compact_progress.bind("<Configure>", self._redraw_compact_progress)
            else:
                self.compact_progress = None
        else:
            self.compact_pct_var = tk.StringVar(value="—")
            self.compact_progress = None

        # ── Message ────────────────────────────────────────────────────
        if cfg["show_message"]:
            sep()
            self.compact_msg_lbl = tk.Label(
                row, text=self.current_message[0],
                font=("Microsoft YaHei UI", 9),
                bg=t["bg"], fg=t["text2"], anchor="w"
            )
            self.compact_msg_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        else:
            self.compact_msg_lbl = None

        # ── Right side controls ────────────────────────────────────────
        # Settings gear (right-click hint)
        gear = tk.Label(row, text="⚙", font=("Segoe UI", 10),
                        bg=t["bg"], fg=t["text2"], padx=6, cursor="hand2")
        gear.pack(side=tk.RIGHT)
        gear.bind("<Button-1>", lambda e: self._open_compact_settings())
        gear.bind("<Enter>", lambda e: gear.config(fg=t["text"]))
        gear.bind("<Leave>", lambda e: gear.config(fg=t["text2"]))

        # Close button
        close_btn = tk.Label(row, text="✕", font=("Segoe UI", 9),
                             bg=t["bg"], fg=t["text2"], padx=10, cursor="hand2")
        close_btn.pack(side=tk.RIGHT)
        close_btn.bind("<Enter>", lambda e: close_btn.config(bg="#E81123", fg="#FFFFFF"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(bg=t["bg"], fg=t["text2"]))
        close_btn.bind("<Button-1>", lambda e: (
            self._compact_cw.destroy(),
            self._stop_color_sampling(),
            self.compact_btn.config(text="精简模式", fg=COLORS["text_secondary"])
        ))

        # ── Drag ──────────────────────────────────────────────────────
        # Sampling is event-driven: triggered only when drag ends.
        # During drag we just move the window; on release we wait
        # 150 ms (window finishes settling) then sample once.
        def on_drag_start(ev):
            self._drag_x = ev.x_root - cw.winfo_x()
            self._drag_y = ev.y_root - cw.winfo_y()
            self._is_dragging = True

        def on_drag_move(ev):
            nx = ev.x_root - self._drag_x
            ny = ev.y_root - self._drag_y
            cw.geometry(f"+{nx}+{ny}")

        def on_drag_end(ev):
            self._is_dragging = False
            if self._compact_settings.get("auto_color", True):
                # Cancel any pending sample, then schedule one after settle
                if hasattr(self, '_drag_sample_id') and self._drag_sample_id:
                    try:
                        self.root.after_cancel(self._drag_sample_id)
                    except Exception:
                        pass
                self._drag_sample_id = self.root.after(150, self._sample_and_apply_theme)

        drag_targets = [row]
        if cfg["show_progress"] or cfg["show_pct"]:
            try:
                drag_targets.append(prog_frame)
            except Exception:
                pass
        for w in drag_targets:
            try:
                w.bind("<Button-1>", on_drag_start)
                w.bind("<B1-Motion>", on_drag_move)
                w.bind("<ButtonRelease-1>", on_drag_end)
            except Exception:
                pass

    # ─── Auto Color Sampling ──────────────────────────────────────────────

    def _resize_compact_to_content(self):
        """Let the compact window shrink/grow to fit its current widgets."""
        cw = self._compact_cw
        if not cw or not cw.winfo_exists():
            return
        cw.update_idletasks()
        new_w = cw.winfo_reqwidth()
        new_h = cw.winfo_reqheight()
        x = cw.winfo_x()
        y = cw.winfo_y()
        cw.geometry(f"{new_w}x{new_h}+{x}+{y}")

    def _start_color_sampling(self):
        """Trigger an immediate one-shot sample (called on open / apply)."""
        self._stop_color_sampling()
        if self.compact_window and self.compact_window.winfo_exists():
            # Small delay so window is fully rendered before we hide it
            self._color_sample_id = self.root.after(200, self._do_color_sample_once)

    def _stop_color_sampling(self):
        """Cancel any pending scheduled sample."""
        for attr in ('_color_sample_id', '_drag_sample_id'):
            sid = getattr(self, attr, None)
            if sid:
                try:
                    self.root.after_cancel(sid)
                except Exception:
                    pass
                setattr(self, attr, None)

    def _do_color_sample_once(self):
        """Run one sample cycle (used by initial open and drag-end trigger)."""
        self._color_sample_id = None
        if not self.compact_window or not self.compact_window.winfo_exists():
            return
        try:
            self._sample_and_apply_theme()
        except Exception:
            pass

    def _sample_and_apply_theme(self):
        """
        Grab background pixels BEHIND the compact bar using PIL ImageGrab.
        Strategy: temporarily hide the window, screenshot the region, restore.
        This guarantees we read the actual background, not our own widgets.
        """
        cw = self.compact_window
        if not cw or not cw.winfo_exists():
            return

        cx = cw.winfo_x()
        cy = cw.winfo_y()
        cw_w = cw.winfo_width()
        cw_h = cw.winfo_height()
        screen_w = cw.winfo_screenwidth()
        screen_h = cw.winfo_screenheight()

        # Clamp to screen bounds
        x1 = max(0, cx)
        y1 = max(0, cy)
        x2 = min(screen_w, cx + cw_w)
        y2 = min(screen_h, cy + cw_h)
        if x2 <= x1 or y2 <= y1:
            return

        raw_colors = []

        # Method A: Hide window → screenshot → restore (most accurate)
        try:
            from PIL import ImageGrab
            # Temporarily make bar invisible
            cw.attributes("-alpha", 0.0)
            cw.update_idletasks()
            # Small delay so compositor can repaint
            import time as _time
            _time.sleep(0.05)
            img = ImageGrab.grab(bbox=(x1, y1, x2, y2), all_screens=True)
            # Restore alpha
            cw.attributes("-alpha", self._compact_settings.get("alpha", 0.90))
            raw_colors = list(img.getdata())
        except Exception:
            # Restore alpha even on error
            try:
                cw.attributes("-alpha", self._compact_settings.get("alpha", 0.90))
            except Exception:
                pass

        # Method B: Windows GDI fallback — sample points above/below bar
        if not raw_colors:
            try:
                import ctypes
                hdc = ctypes.windll.user32.GetDC(0)
                for frac in [0.1, 0.25, 0.5, 0.75, 0.9]:
                    sx = cx + int(cw_w * frac)
                    for sy in [max(0, cy - 60), min(screen_h-1, cy + cw_h + 60)]:
                        colorref = ctypes.windll.gdi32.GetPixel(hdc, sx, sy)
                        if colorref not in (0xFFFFFFFF, -1):
                            r = colorref & 0xFF
                            g = (colorref >> 8) & 0xFF
                            b = (colorref >> 16) & 0xFF
                            raw_colors.append((r, g, b))
                ctypes.windll.user32.ReleaseDC(0, hdc)
            except Exception:
                pass

        if not raw_colors:
            return

        avg_r = sum(c[0] for c in raw_colors) // len(raw_colors)
        avg_g = sum(c[1] for c in raw_colors) // len(raw_colors)
        avg_b = sum(c[2] for c in raw_colors) // len(raw_colors)

        self._apply_adaptive_theme(avg_r, avg_g, avg_b)

    def _apply_adaptive_theme(self, r, g, b):
        """Given background RGB, compute a harmonious bar theme and apply it."""
        # Perceived brightness
        brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0

        if brightness > 0.55:
            # Light background → light frosted bar (blend bg toward white)
            bar_r = min(255, int(r * 0.55 + 200))
            bar_g = min(255, int(g * 0.55 + 200))
            bar_b = min(255, int(b * 0.55 + 200))
            bg_hex   = f"#{bar_r:02x}{bar_g:02x}{bar_b:02x}"
            # Text: dark, slightly tinted with background hue
            txt_r = max(0, int(r * 0.15))
            txt_g = max(0, int(g * 0.15))
            txt_b = max(0, int(b * 0.15))
            text_hex  = f"#{txt_r:02x}{txt_g:02x}{txt_b:02x}"
            text2_hex = f"#{min(255,txt_r+60):02x}{min(255,txt_g+60):02x}{min(255,txt_b+60):02x}"
            border_r = max(0, bar_r - 30)
            border_g = max(0, bar_g - 30)
            border_b = max(0, bar_b - 30)
            border_hex = f"#{border_r:02x}{border_g:02x}{border_b:02x}"
            bar_bg_hex = f"#{max(0,bar_r-20):02x}{max(0,bar_g-20):02x}{max(0,bar_b-20):02x}"
            # Accent: saturated version of hue
            acc_r = max(0, min(255, int(r * 0.4)))
            acc_g = max(0, min(255, int(g * 0.4)))
            acc_b = max(0, min(255, int(b * 0.4 + 80)))
            accent_hex = f"#{acc_r:02x}{acc_g:02x}{acc_b:02x}"
        else:
            # Dark background → dark frosted bar
            bar_r = min(80, max(20, int(r * 0.4 + 20)))
            bar_g = min(80, max(20, int(g * 0.4 + 20)))
            bar_b = min(80, max(20, int(b * 0.4 + 20)))
            bg_hex   = f"#{bar_r:02x}{bar_g:02x}{bar_b:02x}"
            text_hex  = "#E8E8E8"
            text2_hex = "#A0A0A8"
            border_r = min(255, bar_r + 25)
            border_g = min(255, bar_g + 25)
            border_b = min(255, bar_b + 25)
            border_hex = f"#{border_r:02x}{border_g:02x}{border_b:02x}"
            bar_bg_hex = f"#{min(255,bar_r+15):02x}{min(255,bar_g+15):02x}{min(255,bar_b+15):02x}"
            acc_r = min(255, int(r * 0.3 + 80))
            acc_g = min(255, int(g * 0.3 + 80))
            acc_b = min(255, int(b * 0.3 + 180))
            accent_hex = f"#{acc_r:02x}{acc_g:02x}{acc_b:02x}"

        new_theme = {
            "bg": bg_hex, "border": border_hex,
            "text": text_hex, "text2": text2_hex,
            "accent": accent_hex, "bar_bg": bar_bg_hex,
        }

        # Only rebuild if theme changed meaningfully (avoid flicker on tiny deltas)
        old = self._cw_theme
        changed = (old.get("bg") != new_theme["bg"] or old.get("text") != new_theme["text"])
        if changed:
            self._cw_theme = new_theme
            if self.compact_window and self.compact_window.winfo_exists():
                self.compact_window.configure(bg=bg_hex)
                self._build_compact_bar()
                self._resize_compact_to_content()
                self._update_compact_display()

    # ─── Compact Settings Panel ───────────────────────────────────────────

    def _open_compact_settings(self):
        """Floating settings panel for the compact bar."""
        if hasattr(self, '_csettings_win') and self._csettings_win and                 self._csettings_win.winfo_exists():
            self._csettings_win.lift()
            return

        cfg = self._compact_settings
        cw = self.compact_window
        t = self._cw_theme

        sw = tk.Toplevel(self.root)
        self._csettings_win = sw
        sw.title("精简模式设置")
        sw.configure(bg=COLORS["bg_card"])
        sw.resizable(False, False)
        sw.attributes("-topmost", True)
        sw.overrideredirect(False)

        # Position near the compact bar
        if cw and cw.winfo_exists():
            x = cw.winfo_x()
            y = max(0, cw.winfo_y() - 300)
        else:
            x, y = 100, 100
        sw.geometry(f"300x380+{x}+{y}")

        # ── Title ──────────────────────────────────────────────────────
        tk.Label(sw, text="⚙  精简模式设置",
                 font=("Microsoft YaHei UI", 11, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text_primary"]).pack(pady=(14, 4), padx=16, anchor="w")
        tk.Frame(sw, bg=COLORS["border"], height=1).pack(fill=tk.X, padx=16)

        # ── Component toggles ──────────────────────────────────────────
        tk.Label(sw, text="显示组件", font=("Microsoft YaHei UI", 9, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text_secondary"]).pack(anchor="w", padx=16, pady=(10,2))

        toggle_items = [
            ("show_icon",     "⏱  时钟图标"),
            ("show_time",     "🕐  倒计时数字"),
            ("show_progress", "▬  进度条"),
            ("show_pct",      "%  百分比数字"),
            ("show_message",  "💬  提示语"),
            ("auto_color",    "🎨  自动颜色适应"),
        ]
        self._toggle_vars = {}
        for key, label in toggle_items:
            var = tk.BooleanVar(value=cfg[key])
            self._toggle_vars[key] = var
            row = tk.Frame(sw, bg=COLORS["bg_panel"])
            row.pack(fill=tk.X, padx=16, pady=2)
            tk.Label(row, text=label, font=("Microsoft YaHei UI", 9),
                     bg=COLORS["bg_panel"], fg=COLORS["text_primary"],
                     width=20, anchor="w").pack(side=tk.LEFT, padx=8, pady=6)
            cb = tk.Checkbutton(row, variable=var,
                                bg=COLORS["bg_panel"],
                                activebackground=COLORS["bg_panel"],
                                fg=COLORS["accent_blue"],
                                selectcolor=COLORS["bg_dark"],
                                relief=tk.FLAT, bd=0)
            cb.pack(side=tk.RIGHT, padx=8)

        # ── Transparency slider ────────────────────────────────────────
        tk.Label(sw, text="透明度", font=("Microsoft YaHei UI", 9, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text_secondary"]).pack(anchor="w", padx=16, pady=(12,2))

        slider_row = tk.Frame(sw, bg=COLORS["bg_card"])
        slider_row.pack(fill=tk.X, padx=16)

        alpha_var = tk.DoubleVar(value=cfg["alpha"])
        alpha_label = tk.Label(slider_row, text=f"{int(cfg['alpha']*100)}%",
                               font=("Courier New", 10, "bold"),
                               bg=COLORS["bg_card"], fg=COLORS["accent_cyan"], width=4)
        alpha_label.pack(side=tk.RIGHT)

        def on_alpha_change(val):
            v = round(float(val), 2)
            alpha_var.set(v)
            alpha_label.config(text=f"{int(v*100)}%")
            if self.compact_window and self.compact_window.winfo_exists():
                self.compact_window.attributes("-alpha", v)

        slider = ttk.Scale(slider_row, from_=0.10, to=1.0,
                           orient=tk.HORIZONTAL, variable=alpha_var,
                           command=on_alpha_change)
        slider.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=4)

        # ── Apply button ───────────────────────────────────────────────
        def apply_settings():
            for key, var in self._toggle_vars.items():
                cfg[key] = var.get()
            cfg["alpha"] = round(alpha_var.get(), 2)
            self._compact_settings = cfg
            # Rebuild compact bar with new settings
            if self.compact_window and self.compact_window.winfo_exists():
                self.compact_window.attributes("-alpha", cfg["alpha"])
                self._build_compact_bar()
                self._resize_compact_to_content()
                self._update_compact_display()
                if cfg["auto_color"]:
                    self._start_color_sampling()
                else:
                    self._stop_color_sampling()
            self._autosave()
            sw.destroy()

        # Bind window close (×) button to also apply settings
        sw.protocol("WM_DELETE_WINDOW", apply_settings)

        tk.Button(sw, text="✓  应用并关闭", font=("Microsoft YaHei UI", 10, "bold"),
                  bg=COLORS["accent_green"], fg=COLORS["bg_dark"],
                  relief=tk.FLAT, bd=0, padx=20, pady=8, cursor="hand2",
                  command=apply_settings).pack(pady=(8, 4))

        tk.Button(sw, text="✕  取消", font=("Microsoft YaHei UI", 9),
                  bg=COLORS["bg_panel"], fg=COLORS["text_secondary"],
                  relief=tk.FLAT, bd=0, padx=20, pady=6, cursor="hand2",
                  command=sw.destroy).pack(pady=(0, 14))

    # ─── Compact Display Update ───────────────────────────────────────────

    def _update_compact_display(self):
        if not self.compact_window or not self.compact_window.winfo_exists():
            return
        r = max(0, int(self.remaining_seconds))
        h = r // 3600
        m = (r % 3600) // 60
        s = r % 60

        if hasattr(self, 'compact_time_var'):
            self.compact_time_var.set(f"{h:02d}:{m:02d}:{s:02d}")

        ref = self.ref_seconds if self.ref_seconds > 0 else self.total_seconds
        if ref > 0:
            pct = (self.remaining_seconds / ref) * 100
            if hasattr(self, 'compact_pct_var'):
                self.compact_pct_var.set(f"{pct:.1f}%")
        else:
            if hasattr(self, 'compact_pct_var'):
                self.compact_pct_var.set("—")

        msg_text, msg_color = self.current_message
        if hasattr(self, 'compact_msg_lbl') and self.compact_msg_lbl:
            self.compact_msg_lbl.config(text=msg_text, fg=msg_color)

        self._redraw_compact_progress()

    def _redraw_compact_progress(self, event=None):
        if not self.compact_window or not self.compact_window.winfo_exists():
            return
        if not hasattr(self, 'compact_progress') or not self.compact_progress:
            return
        canvas = self.compact_progress
        try:
            w = canvas.winfo_width()
            h = canvas.winfo_height()
        except Exception:
            return
        if w <= 1:
            return
        canvas.delete("all")

        bar_bg = self._cw_theme.get("bar_bg", "#B8D4E8")
        canvas.create_rectangle(0, 0, w, h, fill=bar_bg, outline="")

        ref = self.ref_seconds if self.ref_seconds > 0 else self.total_seconds
        if ref <= 0:
            return

        remaining_frac = max(0.0, min(1.0, self.remaining_seconds / ref))
        elapsed_frac = 1.0 - remaining_frac
        fill_w = max(0, int(w * elapsed_frac))

        if fill_w <= 0:
            return

        SEG = max(1, fill_w // 2)
        for i in range(SEG):
            x0 = int(i * fill_w / SEG)
            x1 = int((i + 1) * fill_w / SEG)
            pos = (x0 + x1) / 2 / w
            rem_here = 1.0 - pos
            color = get_progress_color(rem_here)
            canvas.create_rectangle(x0, 0, x1, h, fill=color, outline="")

    # ─── Section Toggle ───────────────────────────────────────────────────

    def _toggle_section(self, section):
        panels = {
            "settings": (self.settings_panel, self.settings_toggle, "▼  时间设置", "▶  时间设置"),
            "checkpoints": (self.cp_panel, self.cp_toggle, "▼  检查点", "▶  检查点"),
            "messages": (self.msg_panel, self.msg_toggle, "▼  自定义提示语", "▶  自定义提示语"),
        }
        panel, btn, show_text, hide_text = panels[section]

        if panel.winfo_viewable():
            panel.pack_forget()
            btn.config(text=hide_text)
        else:
            # Re-pack in the correct position
            if section == "settings":
                panel.pack(fill=tk.X, padx=20, pady=(8, 0), after=btn.master)
            elif section == "checkpoints":
                panel.pack(fill=tk.X, padx=20, pady=(8, 0), after=btn.master)
            else:
                panel.pack(fill=tk.X, padx=20, pady=(8, 0), after=btn.master)
            btn.config(text=show_text)

    # ─── Window Resize ────────────────────────────────────────────────────


    # ─── Config Persistence ───────────────────────────────────────────────────

    def _autosave(self):
        """Serialize current state and write to disk silently."""
        compact_cfg = getattr(self, '_compact_settings', {})
        data = {
            "total_seconds": self.total_seconds,
            "ref_seconds": self.ref_seconds,
            "last_h": self.h_var.get(),
            "last_m": self.m_var.get(),
            "last_s": self.s_var.get(),
            "checkpoints": [
                {"name": cp.name, "remaining_at": cp.remaining_at}
                for cp in self.checkpoints
            ],
            "custom_messages": {
                str(pct): {"text": txt, "color": col}
                for pct, (txt, col) in self.custom_messages.items()
            },
            "compact_settings": compact_cfg,
        }
        save_config(data)

    def _load_saved_config(self):
        """Load persisted config and restore state into UI."""
        data = load_config()
        if not data:
            return

        # Restore time inputs
        self.h_var.set(data.get("last_h", "00"))
        self.m_var.set(data.get("last_m", "00"))
        self.s_var.set(data.get("last_s", "00"))
        total = data.get("total_seconds", 0)
        if total > 0:
            self.total_seconds = total
            self.remaining_seconds = total
            self._update_display()
        ref = data.get("ref_seconds", 0)
        if ref > 0:
            self.ref_seconds = ref
            rh, rem = divmod(ref, 3600)
            rm, rs = divmod(rem, 60)
            self.ref_h_var.set(f"{rh:02d}")
            self.ref_m_var.set(f"{rm:02d}")
            self.ref_s_var.set(f"{rs:02d}")
            self.ref_label.config(text=f"{rh:02d}:{rm:02d}:{rs:02d}",
                                   fg=COLORS["accent_yellow"])

        # Restore checkpoints
        for cp_data in data.get("checkpoints", []):
            cp = Checkpoint(name=cp_data["name"],
                            remaining_at=cp_data.get("remaining_at", cp_data.get("total_seconds", 0)))
            self.checkpoints.append(cp)
        self.checkpoints.sort(key=lambda c: c.remaining_at, reverse=True)
        self._refresh_checkpoint_list()
        self.root.after(200, self._draw_checkpoint_markers)

        # Restore custom messages
        color_map = {
            100: COLORS["accent_blue"], 70: COLORS["accent_blue"],
            50: COLORS["accent_cyan"], 25: COLORS["accent_yellow"],
            20: COLORS["accent_orange"], 10: COLORS["accent_red"],
            5: COLORS["accent_red"], 2: COLORS["accent_pink"],
            1: COLORS["accent_pink"], 0: COLORS["accent_purple"]
        }
        for pct_str, msg in data.get("custom_messages", {}).items():
            pct = int(pct_str)
            color = msg.get("color", color_map.get(pct, COLORS["accent_blue"]))
            self.custom_messages[pct] = (msg["text"], color)
        if self.custom_messages:
            self._refresh_message_list()

        # Restore compact settings
        saved_compact = data.get("compact_settings", {})
        if saved_compact:
            self._compact_settings = {
                "show_icon":    saved_compact.get("show_icon", True),
                "show_time":    saved_compact.get("show_time", True),
                "show_progress":saved_compact.get("show_progress", True),
                "show_pct":     saved_compact.get("show_pct", True),
                "show_message": saved_compact.get("show_message", True),
                "alpha":        saved_compact.get("alpha", 0.90),
                "auto_color":   saved_compact.get("auto_color", True),
            }

        # Show restore notification in the status bar briefly
        if self.checkpoints or self.custom_messages:
            self._show_restore_toast()

    def _show_restore_toast(self):
        """Briefly flash a 'config restored' hint in the message area."""
        cp_count = len(self.checkpoints)
        msg_count = len(self.custom_messages)
        parts = []
        if cp_count:
            parts.append(f"{cp_count} 个检查点")
        if msg_count:
            parts.append(f"{msg_count} 条自定义提示语")
        hint = "💾 已恢复上次配置：" + "、".join(parts)
        original = self.current_message
        self.message_label.config(text=hint, fg=COLORS["accent_green"])
        self.root.after(3000, lambda: self.message_label.config(
            text=original[0], fg=original[1]))

    def _on_close(self):
        """Save on exit and close."""
        self._autosave()
        self.root.destroy()

    def _setup_resize(self):
        self.root.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        if event.widget == self.root:
            new_wrap = max(200, event.width - 120)
            self.message_label.config(wraplength=new_wrap)
            self.root.after(50, self._redraw_progress)
            # Adaptive font: only update when width changes meaningfully
            if abs(event.width - self._last_win_width) > 20:
                self._last_win_width = event.width
                self.root.after(80, lambda: self._adapt_fonts(event.width))

    def _adapt_fonts(self, win_w):
        """Scale all key fonts proportionally to window width."""
        # Base design width = 720px
        scale = max(0.6, min(2.0, win_w / 720))

        # Timer digits (base 52)
        digit_size = max(24, int(52 * scale))
        sep_size   = max(22, int(48 * scale))
        unit_size  = max(8,  int(10 * scale))
        msg_size   = max(9,  int(13 * scale))
        pct_size   = max(8,  int(11 * scale))

        for lbl in [self.hour_lbl, self.min_lbl, self.sec_lbl]:
            lbl.config(font=("Courier New", digit_size, "bold"))
        # Separator colons
        try:
            tc = self.hour_lbl.master.master  # time_container's parent (inner)
            for child in self.hour_lbl.master.master.winfo_children():
                # Label with text ":"
                if hasattr(child, 'cget'):
                    try:
                        if child.cget('text') == ':':
                            child.config(font=("Courier New", sep_size, "bold"))
                    except Exception:
                        pass
        except Exception:
            pass

        self.message_label.config(font=("Microsoft YaHei UI", msg_size, "bold"))
        self.pct_label.config(font=("Courier New", pct_size, "bold"))

        # Adjust timer frame inner padding
        try:
            pad = max(8, int(24 * scale))
            self.timer_frame.winfo_children()[0].config(pady=pad)
        except Exception:
            pass


# ─── Style Setup ──────────────────────────────────────────────────────────────

def setup_styles():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TCombobox",
                    fieldbackground=COLORS["bg_panel"],
                    background=COLORS["bg_panel"],
                    foreground=COLORS["text_primary"],
                    bordercolor=COLORS["border"],
                    arrowcolor=COLORS["accent_blue"],
                    selectbackground=COLORS["accent_blue"],
                    selectforeground=COLORS["bg_dark"])


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    root.configure(bg=COLORS["bg_dark"])

    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    setup_styles()
    app = CountdownTimer(root)
    root.mainloop()