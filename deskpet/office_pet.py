# -*- coding: utf-8 -*-
import math
import random
import time
import tkinter as tk
from dataclasses import dataclass


CANVAS_WIDTH = 240
CANVAS_HEIGHT = 220
MAGIC_COLOR = "#ff00ff"
OUTLINE = "#5d4234"
FUR = "#f7d7ad"
FUR_LIGHT = "#fff4e1"
EAR = "#ffc9bf"
CHEEK = "#f6a7a2"
BODY = "#fde8c4"
SHADOW = "#d6d0ca"
STATUS_BG = "#fffaf2"
STATUS_ACCENT = "#d7b48c"


def clamp(value, low, high):
    return max(low, min(high, value))


@dataclass
class PetStats:
    mood: int = 72
    energy: int = 68
    focus: int = 42


class OfficePet:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("摸鱼搭子")
        self.root.configure(bg=MAGIC_COLOR)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", MAGIC_COLOR)
        self.root.wm_attributes("-toolwindow", True)

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        start_x = screen_w - CANVAS_WIDTH - 70
        start_y = screen_h - CANVAS_HEIGHT - 110
        self.root.geometry(f"{CANVAS_WIDTH}x{CANVAS_HEIGHT}+{start_x}+{start_y}")

        self.canvas = tk.Canvas(
            self.root,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
            bg=MAGIC_COLOR,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()

        self.stats = PetStats()
        self.facing = 1
        self.speed = 1.8
        self.float_phase = 0.0
        self.roam_enabled = True
        self.dragging = False
        self.drag_moved = False
        self.drag_offset = (0, 0)
        self.last_drag_point = (0, 0)
        self.last_drag_time = time.monotonic()
        self.drag_speed = 0.0
        self.last_interaction = time.monotonic()
        self.last_behavior_change = time.monotonic()
        self.last_stat_update = time.monotonic()
        self.status_until = 0.0
        self.bubble_until = 0.0
        self.bubble_text = "今天也一起优雅摸鱼。"
        self.current_behavior = "idle"
        self.expression_override = None
        self.expression_until = 0.0
        self.action_name = ""
        self.action_until = 0.0
        self.stretch_x = 1.0
        self.stretch_y = 1.0
        self.target_stretch_x = 1.0
        self.target_stretch_y = 1.0
        self.bounce_until = 0.0
        self.bounce_strength = 0.0
        self.particles = []
        self.animation_tick = 0
        self.treat_cooldown_until = 0.0

        self.menu = tk.Menu(self.root, tearoff=False)
        self.menu.add_command(label="摸摸它", command=self.pet_pet)
        self.menu.add_command(label="喂零食", command=self.feed_pet)
        self.menu.add_command(label="看看状态", command=lambda: self.show_status(4.0))
        self.menu.add_command(label="让它认真上班", command=lambda: self.set_behavior("work"))
        self.menu.add_command(label="批准摸鱼", command=lambda: self.set_behavior("slack"))
        self.menu.add_separator()
        self.roam_menu_index = self.menu.index("end") + 1
        self.menu.add_command(label="暂停巡逻", command=self.toggle_roam)
        self.menu.add_command(label="贴边停靠", command=self.snap_to_corner)
        self.menu.add_separator()
        self.menu.add_command(label="退出", command=self.root.destroy)

        for widget in (self.root, self.canvas):
            widget.bind("<ButtonPress-1>", self.on_press)
            widget.bind("<B1-Motion>", self.on_drag)
            widget.bind("<ButtonRelease-1>", self.on_release)
            widget.bind("<Button-3>", self.show_menu)
            widget.bind("<Double-Button-1>", lambda _event: self.feed_pet())
            widget.bind("<Escape>", lambda _event: self.root.destroy())

        self.say("今天也一起优雅摸鱼。", duration=4.0)
        self.draw()
        self.tick()

    def map_point(self, base_x, base_y, local_x, local_y):
        return (
            base_x + (local_x * self.facing * self.stretch_x),
            base_y + (local_y * self.stretch_y),
        )

    def oval_coords(self, base_x, base_y, center_x, center_y, radius_x, radius_y):
        cx, cy = self.map_point(base_x, base_y, center_x, center_y)
        return (
            cx - radius_x * self.stretch_x,
            cy - radius_y * self.stretch_y,
            cx + radius_x * self.stretch_x,
            cy + radius_y * self.stretch_y,
        )

    def polygon_coords(self, base_x, base_y, points):
        coords = []
        for local_x, local_y in points:
            coords.extend(self.map_point(base_x, base_y, local_x, local_y))
        return coords

    def create_round_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        self.canvas.create_polygon(points, smooth=True, splinesteps=20, **kwargs)

    def on_press(self, event):
        self.dragging = True
        self.drag_moved = False
        self.drag_offset = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())
        self.last_drag_point = (event.x_root, event.y_root)
        self.last_drag_time = time.monotonic()
        self.target_stretch_x = 0.95
        self.target_stretch_y = 1.08
        self.show_status(4.0)

    def on_drag(self, event):
        if not self.dragging:
            return

        self.drag_moved = True
        new_x = event.x_root - self.drag_offset[0]
        new_y = event.y_root - self.drag_offset[1]
        self.root.geometry(f"+{new_x}+{new_y}")

        now = time.monotonic()
        delta_x = event.x_root - self.last_drag_point[0]
        delta_y = event.y_root - self.last_drag_point[1]
        delta_t = max(now - self.last_drag_time, 0.001)
        self.drag_speed = math.hypot(delta_x, delta_y) / delta_t
        self.last_drag_point = (event.x_root, event.y_root)
        self.last_drag_time = now

        if abs(delta_x) > 1:
            self.facing = 1 if delta_x > 0 else -1

        if abs(delta_x) >= abs(delta_y):
            stretch = clamp(1.0 + min(abs(delta_x) * 0.01, 0.16), 1.0, 1.16)
            squash = clamp(1.0 - min(abs(delta_x) * 0.006, 0.12), 0.88, 1.0)
            self.target_stretch_x = stretch
            self.target_stretch_y = squash
        else:
            stretch = clamp(1.0 + min(abs(delta_y) * 0.01, 0.18), 1.0, 1.18)
            squash = clamp(1.0 - min(abs(delta_y) * 0.006, 0.1), 0.9, 1.0)
            self.target_stretch_y = stretch
            self.target_stretch_x = squash

    def on_release(self, _event):
        if not self.dragging:
            return

        self.dragging = False
        self.target_stretch_x = 1.12 if self.drag_moved else 1.04
        self.target_stretch_y = 0.9 if self.drag_moved else 0.98
        self.bounce_until = time.monotonic() + 0.8
        self.bounce_strength = clamp(4.0 + self.drag_speed * 0.002, 4.0, 14.0)

        if not self.drag_moved:
            self.pet_pet()
        else:
            self.say("轻一点，我会自己弹回来。", duration=2.2)
            self.show_status(3.0)

    def show_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def pet_pet(self):
        self.stats.mood = clamp(self.stats.mood + 10, 0, 100)
        self.stats.energy = clamp(self.stats.energy + 3, 0, 100)
        self.last_interaction = time.monotonic()
        self.current_behavior = "happy"
        self.set_expression("happy", 1.6)
        self.set_action("wave", 1.2)
        self.spawn_particles("heart", 5)
        self.say(random.choice([
            "嘿嘿，这一下很受用。",
            "收到摸摸，心情回温。",
            "继续陪你一起混工位。",
        ]), duration=2.2)
        self.show_status(3.8)

    def feed_pet(self):
        now = time.monotonic()
        if now < self.treat_cooldown_until:
            self.say("零食还在嚼，再等我一下。", duration=2.1)
            self.show_status(3.0)
            return

        self.treat_cooldown_until = now + 8.0
        self.stats.energy = clamp(self.stats.energy + 16, 0, 100)
        self.stats.mood = clamp(self.stats.mood + 8, 0, 100)
        self.stats.focus = clamp(self.stats.focus + 4, 0, 100)
        self.last_interaction = now
        self.current_behavior = "snack"
        self.set_expression("chew", 2.0)
        self.set_action("chew", 1.8)
        self.spawn_particles("star", 6)
        self.spawn_particles("crumb", 5)
        self.say(random.choice([
            "咔滋咔滋，续命成功。",
            "好吃，今天继续营业。",
            "这口零食很提神。",
        ]), duration=2.4)
        self.show_status(4.0)

    def set_behavior(self, behavior):
        self.current_behavior = behavior
        self.last_behavior_change = time.monotonic()
        if behavior == "work":
            self.stats.focus = clamp(self.stats.focus + 14, 0, 100)
            self.stats.mood = clamp(self.stats.mood - 3, 0, 100)
            self.set_expression("focused", 1.8)
            self.set_action("nod", 1.0)
            self.say("收到，我开始假装整理周报。", duration=2.6)
        elif behavior == "slack":
            self.stats.mood = clamp(self.stats.mood + 10, 0, 100)
            self.stats.focus = clamp(self.stats.focus - 5, 0, 100)
            self.set_expression("mischief", 1.8)
            self.set_action("wiggle", 1.4)
            self.say("摸鱼许可已生效，状态良好。", duration=2.6)
        self.show_status(3.4)

    def toggle_roam(self):
        self.roam_enabled = not self.roam_enabled
        label = "恢复巡逻" if not self.roam_enabled else "暂停巡逻"
        self.menu.entryconfigure(self.roam_menu_index, label=label)
        self.say("我先在原地发会呆。" if not self.roam_enabled else "继续沿着桌面散步。", duration=2.3)

    def snap_to_corner(self):
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = screen_w - CANVAS_WIDTH - 28
        y = screen_h - CANVAS_HEIGHT - 60
        self.root.geometry(f"+{x}+{y}")
        self.say("已贴边停靠，不挡你视线。", duration=2.3)

    def say(self, text, duration=2.0):
        self.bubble_text = text
        self.bubble_until = time.monotonic() + duration

    def show_status(self, duration=3.0):
        self.status_until = time.monotonic() + duration

    def set_expression(self, expression, duration):
        self.expression_override = expression
        self.expression_until = time.monotonic() + duration

    def set_action(self, action_name, duration):
        self.action_name = action_name
        self.action_until = time.monotonic() + duration

    def spawn_particles(self, kind, count):
        for _ in range(count):
            self.particles.append(
                {
                    "kind": kind,
                    "x": 120 + random.uniform(-26, 26),
                    "y": 82 + random.uniform(-8, 16),
                    "vx": random.uniform(-1.5, 1.5),
                    "vy": random.uniform(-2.8, -1.4),
                    "size": random.uniform(8, 14),
                    "life": random.uniform(0.9, 1.4),
                    "born": time.monotonic(),
                }
            )

    def choose_behavior(self):
        now = time.monotonic()
        if now - self.last_behavior_change < random.uniform(4.0, 7.0):
            return
        self.last_behavior_change = now

        if self.stats.energy < 20:
            self.current_behavior = "sleep"
            self.say("电量告急，先眯一会。", duration=2.8)
            return

        if self.stats.mood < 30:
            self.current_behavior = "seek_attention"
            self.set_expression("sad", 2.0)
            self.say("今天有点蔫，摸摸我吧。", duration=2.6)
            return

        if self.stats.focus < 28 and self.stats.mood > 60:
            self.current_behavior = "slack"
            if random.random() < 0.5:
                self.set_expression("mischief", 1.5)
                self.say("我觉得现在适合发会呆。", duration=2.3)
            return

        self.current_behavior = random.choice(["idle", "work", "slack", "idle"])
        if self.current_behavior == "work" and random.random() < 0.35:
            self.set_expression("focused", 1.4)
        elif self.current_behavior == "slack" and random.random() < 0.35:
            self.set_expression("mischief", 1.4)

    def update_stats(self):
        now = time.monotonic()
        elapsed = now - self.last_stat_update
        if elapsed < 1.0:
            return

        steps = int(elapsed)
        self.last_stat_update += steps
        idle_seconds = now - self.last_interaction

        for _ in range(steps):
            if self.current_behavior == "sleep":
                self.stats.energy = clamp(self.stats.energy + 2, 0, 100)
                self.stats.focus = clamp(self.stats.focus + 1, 0, 100)
                self.stats.mood = clamp(self.stats.mood + 1, 0, 100)
            elif self.current_behavior == "work":
                self.stats.focus = clamp(self.stats.focus + 1, 0, 100)
                self.stats.energy = clamp(self.stats.energy - 1, 0, 100)
                self.stats.mood = clamp(self.stats.mood - 1, 0, 100)
            elif self.current_behavior == "slack":
                self.stats.mood = clamp(self.stats.mood + 1, 0, 100)
                self.stats.focus = clamp(self.stats.focus - 1, 0, 100)
            else:
                if random.random() < 0.28:
                    self.stats.energy = clamp(self.stats.energy - 1, 0, 100)
                if random.random() < 0.22:
                    self.stats.focus = clamp(self.stats.focus - 1, 0, 100)

            if idle_seconds > 18 and random.random() < 0.45:
                self.stats.mood = clamp(self.stats.mood - 1, 0, 100)

    def update_motion(self):
        if self.dragging or not self.roam_enabled:
            return

        if self.current_behavior == "sleep":
            self.speed = 0.0
            return

        if self.current_behavior == "work":
            self.speed = 1.0
        elif self.current_behavior == "slack":
            self.speed = 2.2
        elif self.current_behavior == "seek_attention":
            self.speed = 2.8
        else:
            self.speed = 1.6
            if random.random() < 0.04:
                self.facing *= -1

        x = self.root.winfo_x()
        y = self.root.winfo_y()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        new_x = x + (self.speed if self.facing > 0 else -self.speed)
        vertical_wobble = math.sin(self.float_phase * 0.8) * (1.5 if self.current_behavior == "slack" else 0.8)
        new_y = clamp(y + vertical_wobble, 10, screen_h - CANVAS_HEIGHT - 45)

        if new_x <= 0 or new_x >= screen_w - CANVAS_WIDTH:
            self.facing *= -1
            new_x = clamp(new_x, 0, screen_w - CANVAS_WIDTH)

        self.root.geometry(f"+{int(new_x)}+{int(new_y)}")

    def current_expression(self):
        now = time.monotonic()
        if self.expression_override and now < self.expression_until:
            return self.expression_override
        if self.current_behavior == "sleep":
            return "sleep"
        if self.current_behavior == "work":
            return "focused"
        if self.current_behavior == "seek_attention":
            return "sad"
        if self.current_behavior == "slack" and random.random() < 0.08:
            return "mischief"
        if self.animation_tick % 22 == 0:
            return "blink"
        return "idle"

    def current_bounce_offset(self):
        if time.monotonic() >= self.bounce_until:
            return 0.0
        progress = 1.0 - ((self.bounce_until - time.monotonic()) / 0.8)
        return -math.sin(progress * math.pi * 3.2) * self.bounce_strength * (1.0 - progress)

    def update_animation(self):
        self.float_phase += 0.16
        if not self.dragging:
            self.target_stretch_x += (1.0 - self.target_stretch_x) * 0.18
            self.target_stretch_y += (1.0 - self.target_stretch_y) * 0.18

        self.stretch_x += (self.target_stretch_x - self.stretch_x) * 0.28
        self.stretch_y += (self.target_stretch_y - self.stretch_y) * 0.28

        now = time.monotonic()
        active_particles = []
        for particle in self.particles:
            age = now - particle["born"]
            if age >= particle["life"]:
                continue
            particle["x"] += particle["vx"]
            particle["y"] += particle["vy"]
            particle["vy"] += 0.04
            active_particles.append(particle)
        self.particles = active_particles

    def draw_bubble(self):
        if time.monotonic() > self.bubble_until:
            return

        x1, y1, x2, y2 = 26, 8, 214, 54
        self.create_round_rect(
            x1,
            y1,
            x2,
            y2,
            14,
            fill="#fffdf8",
            outline="#bfa180",
            width=2,
        )
        self.canvas.create_polygon(
            70,
            y2 - 2,
            82,
            y2 - 2,
            76,
            y2 + 12,
            fill="#fffdf8",
            outline="#bfa180",
            width=2,
            smooth=True,
        )
        self.canvas.create_text(
            (x1 + x2) / 2,
            (y1 + y2) / 2,
            text=self.bubble_text,
            fill="#463124",
            width=(x2 - x1 - 20),
            font=("Microsoft YaHei UI", 9, "bold"),
        )

    def draw_status(self):
        if time.monotonic() > self.status_until:
            return

        x1, y1, x2, y2 = 34, 164, 206, 206
        self.create_round_rect(
            x1,
            y1,
            x2,
            y2,
            16,
            fill=STATUS_BG,
            outline=STATUS_ACCENT,
            width=2,
        )
        text = f"心情 {self.stats.mood:02d}   精力 {self.stats.energy:02d}   专注 {self.stats.focus:02d}"
        self.canvas.create_text(
            120,
            183,
            text=text,
            fill="#5a4033",
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        self.canvas.create_text(
            120,
            197,
            text=self.behavior_label(),
            fill="#9a7058",
            font=("Microsoft YaHei UI", 8),
        )

    def draw_particle(self, particle):
        age_ratio = (time.monotonic() - particle["born"]) / particle["life"]
        size = particle["size"] * (1.0 - age_ratio * 0.25)
        x = particle["x"]
        y = particle["y"]

        if particle["kind"] == "heart":
            self.canvas.create_text(
                x,
                y,
                text="♥",
                fill="#ff6f91",
                font=("Segoe UI Symbol", int(size), "bold"),
            )
        elif particle["kind"] == "star":
            self.canvas.create_text(
                x,
                y,
                text="✦",
                fill="#ffbf47",
                font=("Segoe UI Symbol", int(size), "bold"),
            )
        else:
            self.canvas.create_oval(
                x - size * 0.22,
                y - size * 0.14,
                x + size * 0.22,
                y + size * 0.14,
                fill="#d9a46b",
                outline="",
            )

    def draw_face(self, base_x, base_y):
        expression = self.current_expression()
        left_eye = self.map_point(base_x, base_y, -13, -17)
        right_eye = self.map_point(base_x, base_y, 13, -17)

        if expression in {"idle", "mischief", "chew", "surprised", "focused"}:
            eye_rx = 4 if expression != "focused" else 5
            eye_ry = 6 if expression == "surprised" else 5
            self.canvas.create_oval(
                left_eye[0] - eye_rx,
                left_eye[1] - eye_ry,
                left_eye[0] + eye_rx,
                left_eye[1] + eye_ry,
                fill="#3e3028",
                outline="",
            )
            if expression != "chew":
                self.canvas.create_oval(
                    right_eye[0] - eye_rx,
                    right_eye[1] - eye_ry,
                    right_eye[0] + eye_rx,
                    right_eye[1] + eye_ry,
                    fill="#3e3028",
                    outline="",
                )

        if expression == "chew":
            self.canvas.create_line(
                right_eye[0] - 5,
                right_eye[1],
                right_eye[0] + 5,
                right_eye[1],
                fill="#3e3028",
                width=3,
                capstyle=tk.ROUND,
            )
        elif expression in {"blink", "sleep"}:
            for eye in (left_eye, right_eye):
                self.canvas.create_line(
                    eye[0] - 5,
                    eye[1],
                    eye[0] + 5,
                    eye[1],
                    fill="#3e3028",
                    width=3,
                    capstyle=tk.ROUND,
                )
        elif expression == "happy":
            for eye in (left_eye, right_eye):
                self.canvas.create_arc(
                    eye[0] - 7,
                    eye[1] - 2,
                    eye[0] + 7,
                    eye[1] + 9,
                    start=200,
                    extent=140,
                    style=tk.ARC,
                    outline="#3e3028",
                    width=3,
                )
        elif expression == "sad":
            self.canvas.create_line(
                left_eye[0] - 6,
                left_eye[1] - 2,
                left_eye[0] + 4,
                left_eye[1] + 2,
                fill="#3e3028",
                width=3,
                capstyle=tk.ROUND,
            )
            self.canvas.create_line(
                right_eye[0] - 4,
                right_eye[1] + 2,
                right_eye[0] + 6,
                right_eye[1] - 2,
                fill="#3e3028",
                width=3,
                capstyle=tk.ROUND,
            )

        if expression in {"happy", "chew", "mischief"}:
            for cheek in (-19, 19):
                x, y = self.map_point(base_x, base_y, cheek, -3)
                self.canvas.create_oval(
                    x - 6,
                    y - 4,
                    x + 6,
                    y + 4,
                    fill=CHEEK,
                    outline="",
                )

        if expression == "focused":
            for brow_dir, eye in ((-1, left_eye), (1, right_eye)):
                self.canvas.create_line(
                    eye[0] - 7,
                    eye[1] - 9 - brow_dir,
                    eye[0] + 7,
                    eye[1] - 7 + brow_dir,
                    fill="#7f604d",
                    width=3,
                    capstyle=tk.ROUND,
                )
        elif expression == "sad":
            for brow_dir, eye in ((1, left_eye), (-1, right_eye)):
                self.canvas.create_line(
                    eye[0] - 6,
                    eye[1] - 8 + brow_dir,
                    eye[0] + 6,
                    eye[1] - 10 - brow_dir,
                    fill="#7f604d",
                    width=3,
                    capstyle=tk.ROUND,
                )

        nose = self.map_point(base_x, base_y, 0, -8)
        self.canvas.create_oval(
            nose[0] - 3,
            nose[1] - 2,
            nose[0] + 3,
            nose[1] + 2,
            fill="#8c6553",
            outline="",
        )

        mouth_y = self.map_point(base_x, base_y, 0, 4)[1]
        mouth_x = self.map_point(base_x, base_y, 0, 4)[0]

        if expression == "surprised":
            self.canvas.create_oval(
                mouth_x - 5,
                mouth_y - 3,
                mouth_x + 5,
                mouth_y + 7,
                outline="#8c6553",
                width=3,
            )
        elif expression in {"happy", "mischief", "chew"}:
            self.canvas.create_arc(
                mouth_x - 10,
                mouth_y - 2,
                mouth_x + 10,
                mouth_y + 10,
                start=200,
                extent=140,
                style=tk.ARC,
                outline="#8c6553",
                width=3,
            )
        elif expression == "sad":
            self.canvas.create_arc(
                mouth_x - 10,
                mouth_y + 3,
                mouth_x + 10,
                mouth_y + 10,
                start=20,
                extent=140,
                style=tk.ARC,
                outline="#8c6553",
                width=3,
            )
        else:
            self.canvas.create_line(
                mouth_x - 7,
                mouth_y + 4,
                mouth_x + 7,
                mouth_y + 4,
                fill="#8c6553",
                width=3,
                capstyle=tk.ROUND,
            )

        if expression == "sleep":
            self.canvas.create_text(
                base_x + 38,
                base_y - 50,
                text="Z",
                fill="#9f87ff",
                font=("Segoe UI", 12, "bold"),
            )
            self.canvas.create_text(
                base_x + 48,
                base_y - 64,
                text="z",
                fill="#9f87ff",
                font=("Segoe UI", 10, "bold"),
            )

    def draw_pet(self):
        base_x = 118
        base_y = 122 + math.sin(self.float_phase) * (2.0 if self.current_behavior == "slack" else 1.0)
        base_y += self.current_bounce_offset()

        shadow_w = 52 * (1.0 + abs(self.stretch_x - 1.0) * 0.4)
        shadow_h = 11 * (1.0 - abs(self.stretch_y - 1.0) * 0.2)
        self.canvas.create_oval(
            base_x - shadow_w,
            156,
            base_x + shadow_w,
            156 + shadow_h,
            fill=SHADOW,
            outline="",
        )

        tail_swing = math.sin(self.float_phase * (4.8 if self.current_behavior in {"happy", "slack"} else 3.1)) * 7
        if time.monotonic() < self.action_until and self.action_name == "wiggle":
            tail_swing *= 1.8

        tail_points = [(-28, 12), (-45, 2 + tail_swing * 0.2), (-54, -9 + tail_swing)]
        self.canvas.create_line(
            self.polygon_coords(base_x, base_y, tail_points),
            fill="#d7b28d",
            width=10,
            smooth=True,
            capstyle=tk.ROUND,
        )

        body_bounds = self.oval_coords(base_x, base_y, 0, 15, 37, 30)
        self.canvas.create_oval(*body_bounds, fill=BODY, outline=OUTLINE, width=4)

        ear_left = [(-26, -36), (-36, -70), (-15, -50)]
        ear_right = [(26, -36), (36, -70), (15, -50)]
        self.canvas.create_polygon(
            self.polygon_coords(base_x, base_y, ear_left),
            fill=FUR,
            outline=OUTLINE,
            width=4,
            smooth=True,
            splinesteps=18,
        )
        self.canvas.create_polygon(
            self.polygon_coords(base_x, base_y, ear_right),
            fill=FUR,
            outline=OUTLINE,
            width=4,
            smooth=True,
            splinesteps=18,
        )
        self.canvas.create_polygon(
            self.polygon_coords(base_x, base_y, [(-24, -40), (-29, -60), (-17, -48)]),
            fill=EAR,
            outline="",
            smooth=True,
        )
        self.canvas.create_polygon(
            self.polygon_coords(base_x, base_y, [(24, -40), (29, -60), (17, -48)]),
            fill=EAR,
            outline="",
            smooth=True,
        )

        head_bounds = self.oval_coords(base_x, base_y, 0, -10, 44, 40)
        self.canvas.create_oval(*head_bounds, fill=FUR, outline=OUTLINE, width=4)
        muzzle_bounds = self.oval_coords(base_x, base_y, 0, -1, 21, 15)
        self.canvas.create_oval(*muzzle_bounds, fill=FUR_LIGHT, outline=OUTLINE, width=3)

        paw_bob = math.sin(self.float_phase * 5.5) * 4
        front_paw_y = 34
        if time.monotonic() < self.action_until and self.action_name == "wave":
            front_paw_y = 18 + paw_bob
        elif time.monotonic() < self.action_until and self.action_name == "nod":
            front_paw_y = 29 + abs(paw_bob) * 0.4

        paw_specs = [(-18, 42, 11, 9), (18, front_paw_y, 11, 9)]
        for center_x, center_y, radius_x, radius_y in paw_specs:
            self.canvas.create_oval(
                *self.oval_coords(base_x, base_y, center_x, center_y, radius_x, radius_y),
                fill=FUR_LIGHT,
                outline=OUTLINE,
                width=3,
            )

        belly_bounds = self.oval_coords(base_x, base_y, 0, 22, 23, 18)
        self.canvas.create_oval(*belly_bounds, fill=FUR_LIGHT, outline="", width=0)

        if time.monotonic() < self.action_until and self.action_name == "chew":
            crumb_x, crumb_y = self.map_point(base_x, base_y, 20, 8)
            self.canvas.create_oval(
                crumb_x - 3,
                crumb_y - 2,
                crumb_x + 3,
                crumb_y + 2,
                fill="#d9a46b",
                outline="",
            )

        self.draw_face(base_x, base_y)

    def behavior_label(self):
        labels = {
            "idle": "待机中",
            "work": "假装上班",
            "slack": "快乐摸鱼",
            "sleep": "补觉中",
            "seek_attention": "求摸摸",
            "happy": "心情超好",
            "snack": "吃零食",
        }
        return labels.get(self.current_behavior, "待机中")

    def draw(self):
        self.canvas.delete("all")
        self.draw_bubble()
        self.draw_pet()
        for particle in self.particles:
            self.draw_particle(particle)
        self.draw_status()

    def tick(self):
        self.animation_tick += 1
        self.choose_behavior()
        self.update_stats()
        self.update_motion()
        self.update_animation()

        if self.stats.energy <= 10:
            self.current_behavior = "sleep"
        elif self.current_behavior == "sleep" and self.stats.energy >= 56:
            self.current_behavior = "idle"
            self.set_expression("happy", 1.2)
            self.say("我醒啦，继续陪你。", duration=2.2)

        if time.monotonic() >= self.expression_until:
            self.expression_override = None
        if time.monotonic() >= self.action_until:
            self.action_name = ""

        self.draw()
        self.root.after(33, self.tick)


def main():
    root = tk.Tk()
    OfficePet(root)
    root.mainloop()


if __name__ == "__main__":
    main()
