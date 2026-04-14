# -*- coding: utf-8 -*-
import math
import random
import time
import tkinter as tk
from dataclasses import dataclass

W, H = 280, 250
MAGIC = "#ff00ff"

PETS = {
    "团子": {
        "outline": "#6a4b3a", "main": "#f6d7ae", "light": "#fff3df", "accent": "#f4a7a0",
        "tail": "#dcb48c", "ear": "#ffcdbf", "shadow": "#d9d2ca", "menu": "#fff8f0",
        "panel": "#d7bb97", "badge": "#f9e6da", "ear_style": "cat", "tail_style": "cat",
        "stripes": False, "bobble": False, "head_rx": 46, "head_ry": 40, "body_rx": 38, "body_ry": 31,
        "muzzle_rx": 21, "muzzle_ry": 15, "paw_rx": 11, "paw_ry": 9, "cheeks": True,
    },
    "乌鲁鲁": {
        "outline": "#41566f", "main": "#bfe6ff", "light": "#effaff", "accent": "#7fd7ff",
        "tail": "#7cc8f5", "ear": "#d2f5ff", "shadow": "#cfd8e1", "menu": "#f5fbff",
        "panel": "#8bc4e5", "badge": "#dff3ff", "ear_style": "fin", "tail_style": "ribbon",
        "stripes": False, "bobble": True, "head_rx": 42, "head_ry": 46, "body_rx": 34, "body_ry": 36,
        "muzzle_rx": 18, "muzzle_ry": 13, "paw_rx": 10, "paw_ry": 8, "cheeks": False,
    },
    "皮卡丘": {
        "outline": "#6b4d21", "main": "#ffd84d", "light": "#fff3a1", "accent": "#ff6b6b",
        "tail": "#cfa34a", "ear": "#ffe78d", "shadow": "#d8cba2", "menu": "#fffcee",
        "panel": "#d3b560", "badge": "#fff0b0", "ear_style": "pika", "tail_style": "lightning",
        "stripes": True, "bobble": False, "head_rx": 43, "head_ry": 37, "body_rx": 35, "body_ry": 29,
        "muzzle_rx": 17, "muzzle_ry": 12, "paw_rx": 10, "paw_ry": 8, "cheeks": True,
    },
}


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def tint(color, k):
    c = color.lstrip("#")
    r, g, b = int(c[:2], 16), int(c[2:4], 16), int(c[4:], 16)
    return f"#{int(clamp(r * k, 0, 255)):02x}{int(clamp(g * k, 0, 255)):02x}{int(clamp(b * k, 0, 255)):02x}"


@dataclass
class PetStats:
    mood: int = 74
    energy: int = 69
    focus: int = 43


class OfficePet:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("摸鱼搭子")
        self.root.configure(bg=MAGIC)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", MAGIC)
        self.root.wm_attributes("-toolwindow", True)
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{W}x{H}+{sw - W - 80}+{sh - H - 120}")
        self.cv = tk.Canvas(root, width=W, height=H, bg=MAGIC, highlightthickness=0, bd=0)
        self.cv.pack()

        self.pet = "团子"
        self.stats = PetStats()
        self.face = 1
        self.phase = 0.0
        self.speed = 1.6
        self.drag = False
        self.dragged = False
        self.offset = (0, 0)
        self.press_root = (0, 0)
        self.last_drag = (0, 0)
        self.last_drag_t = time.monotonic()
        self.drag_speed = 0.0
        self.last_step = (0.0, 0.0)
        self.drag_vec = (0.0, 0.0)
        self.drag_tension = 0.0
        self.grab = (0.0, -12.0)
        self.grab_part = "head"
        self.sx = self.sy = 1.0
        self.tx = self.ty = 1.0
        self.bounce_until = 0.0
        self.bounce_power = 0.0
        self.fling_vx = 0.0
        self.fling_vy = 0.0
        self.inertia_until = 0.0
        self.roam = True
        self.behavior = "idle"
        self.expr = None
        self.expr_until = 0.0
        self.act = ""
        self.act_until = 0.0
        self.last_touch = time.monotonic()
        self.last_behavior = time.monotonic()
        self.last_stats = time.monotonic()
        self.bubble = "今天也一起优雅摸鱼。"
        self.bubble_until = 0.0
        self.status_until = 0.0
        self.food_until = 0.0
        self.particles = []
        self.tick_id = 0
        self.menu_open = False
        self.menu_mode = "main"
        self.menu_hover = None
        self.menu_items = []
        self.switch_rect = (0, 0, 0, 0)

        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_drag)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Double-Button-1>", self.on_double)
        self.cv.bind("<Button-3>", self.show_menu)
        self.cv.bind("<Motion>", self.on_move)
        self.root.bind("<Escape>", lambda _e: self.root.destroy())
        self.say("今天也一起优雅摸鱼。", 4)
        self.draw()
        self.loop()

    @property
    def cfg(self):
        return PETS[self.pet]

    def pt(self, bx, by, x, y):
        return bx + x * self.face * self.sx, by + y * self.sy

    def oval(self, bx, by, x, y, rx, ry):
        cx, cy = self.pt(bx, by, x, y)
        return cx - rx * self.sx, cy - ry * self.sy, cx + rx * self.sx, cy + ry * self.sy

    def poly(self, bx, by, pts):
        out = []
        for x, y in pts:
            out += self.pt(bx, by, x, y)
        return out

    def rr(self, x1, y1, x2, y2, r, **kw):
        p = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        self.cv.create_polygon(p, smooth=True, splinesteps=24, **kw)

    def blob(self, bx, by, cx, cy, rx, ry, fill, outline, width=4, bulges=None):
        bulges = bulges or []
        pts = []
        for i in range(28):
            t = math.tau * i / 28
            scale = 1.0
            for b in bulges:
                d = math.atan2(math.sin(t - b[0]), math.cos(t - b[0]))
                scale += b[1] * math.exp(-((d / b[2]) ** 2))
            x = cx + math.cos(t) * rx * scale
            y = cy + math.sin(t) * ry * scale
            pts += self.pt(bx, by, x, y)
        self.cv.create_polygon(pts, fill=fill, outline=outline, width=width, smooth=True, splinesteps=28)

    def anchor(self):
        return 142, 132 + math.sin(self.phase) * (2.2 if self.behavior == "slack" else 1.0) + self.bounce_y()

    def local(self, ex, ey):
        bx, by = self.anchor()
        x = (ex - bx) / max(self.sx, 0.001)
        y = (ey - by) / max(self.sy, 0.001)
        return x / self.face, y

    def bounce_y(self):
        if time.monotonic() >= self.bounce_until:
            return 0.0
        p = 1.0 - (self.bounce_until - time.monotonic()) / 1.05
        primary = -math.sin(p * math.pi * 3.1) * self.bounce_power * (1.0 - p)
        secondary = math.sin(p * math.pi * 6.2) * self.bounce_power * 0.24 * ((1.0 - p) ** 1.3)
        return primary + secondary

    def say(self, text, sec=2.0):
        self.bubble, self.bubble_until = text, time.monotonic() + sec

    def show_status(self, sec=3.0):
        self.status_until = time.monotonic() + sec

    def set_expr(self, name, sec):
        self.expr, self.expr_until = name, time.monotonic() + sec

    def set_act(self, name, sec):
        self.act, self.act_until = name, time.monotonic() + sec

    def spawn(self, kind, n):
        for _ in range(n):
            self.particles.append({
                "kind": kind, "x": 146 + random.uniform(-30, 30), "y": 82 + random.uniform(-10, 14),
                "vx": random.uniform(-1.4, 1.4), "vy": random.uniform(-2.6, -1.2),
                "size": random.uniform(8, 14), "life": random.uniform(0.9, 1.5), "born": time.monotonic(),
            })

    def hide_menu(self):
        self.menu_open = False
        self.menu_hover = None
        self.menu_items = []
        self.draw()

    def show_menu(self, _e):
        self.menu_open = True
        self.menu_mode = "main"
        self.menu_hover = None
        self.draw()

    def menu_hit(self, x, y):
        for i, item in enumerate(self.menu_items):
            x1, y1, x2, y2 = item["rect"]
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.menu_hover = i
                item["fn"]()
                return True
        return False

    def on_move(self, e):
        if not self.menu_open:
            return
        hit = None
        for i, item in enumerate(self.menu_items):
            x1, y1, x2, y2 = item["rect"]
            if x1 <= e.x <= x2 and y1 <= e.y <= y2:
                hit = i
                break
        if hit != self.menu_hover:
            self.menu_hover = hit
            self.draw()
    def on_press(self, e):
        x1, y1, x2, y2 = self.switch_rect
        if x1 <= e.x <= x2 and y1 <= e.y <= y2:
            self.menu_open = True
            self.menu_mode = "pets"
            self.menu_hover = None
            self.draw()
            return
        if self.menu_open:
            if self.menu_hit(e.x, e.y):
                return
            self.hide_menu()
            return
        self.drag = True
        self.dragged = False
        self.offset = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())
        self.press_root = (e.x_root, e.y_root)
        self.last_drag = (e.x_root, e.y_root)
        self.last_drag_t = time.monotonic()
        x, y = self.local(e.x, e.y)
        self.grab = (clamp(x, -36, 36), clamp(y, -40, 26))
        if y < -18:
            self.grab_part = "crown"
        elif y < 10 and x < -8:
            self.grab_part = "cheek_left"
        elif y < 10 and x > 8:
            self.grab_part = "cheek_right"
        else:
            self.grab_part = "head" if y < 10 else "body"
        self.fling_vx = 0.0
        self.fling_vy = 0.0
        self.inertia_until = 0.0
        self.tx, self.ty = 0.96, 1.04
        self.show_status(3.8)

    def on_drag(self, e):
        if not self.drag:
            return
        self.dragged = True
        self.root.geometry(f"+{e.x_root - self.offset[0]}+{e.y_root - self.offset[1]}")
        now = time.monotonic()
        dx, dy = e.x_root - self.last_drag[0], e.y_root - self.last_drag[1]
        dt = max(now - self.last_drag_t, 0.001)
        self.drag_speed = math.hypot(dx, dy) / dt
        self.last_step = (dx, dy)
        self.last_drag, self.last_drag_t = (e.x_root, e.y_root), now
        tx, ty = e.x_root - self.press_root[0], e.y_root - self.press_root[1]
        self.drag_vec = (tx, ty)
        self.drag_tension = clamp(math.hypot(tx, ty) * 0.035, 0, 1)
        if abs(dx) > 1:
            self.face = 1 if dx > 0 else -1
        self.tx = 1.0 + clamp(abs(tx) * 0.0032, 0, 0.22) - clamp(abs(ty) * 0.0014, 0, 0.07)
        self.ty = 1.0 + clamp(abs(ty) * 0.0032, 0, 0.18) - clamp(abs(tx) * 0.0012, 0, 0.07)
        if self.grab_part == "crown":
            self.set_expr("dizzy" if self.drag_tension > 0.5 else "surprised", 0.2)
        elif self.grab_part in {"cheek_left", "cheek_right"}:
            self.set_expr("squish", 0.2)
        else:
            self.set_expr("squish" if self.drag_tension < 0.45 else "dizzy", 0.2)

    def on_release(self, _e):
        if not self.drag:
            return
        self.drag = False
        self.tx, self.ty = (1.1, 0.9) if self.dragged else (1.02, 0.99)
        now = time.monotonic()
        self.bounce_until = now + 1.05
        self.bounce_power = clamp(5.0 + self.drag_speed * 0.002, 5, 16)
        if self.dragged:
            self.fling_vx = clamp(self.last_step[0] * 0.45, -16, 16)
            self.fling_vy = clamp(self.last_step[1] * 0.18, -6, 6)
            self.inertia_until = now + 0.55
            self.say("轻一点，我会自己弹回来。", 2.1)
            self.show_status(3.0)
        else:
            self.pet_pet()
        self.drag_vec, self.drag_tension = (0.0, 0.0), 0.0

    def on_double(self, _e):
        if not self.menu_open:
            self.feed_pet()

    def pet_pet(self):
        self.stats.mood = clamp(self.stats.mood + 9, 0, 100)
        self.stats.energy = clamp(self.stats.energy + 3, 0, 100)
        self.last_touch = time.monotonic()
        self.behavior = "happy"
        self.set_expr(random.choice(["happy", "sparkle", "peek"]), 1.7)
        self.set_act(random.choice(["wave", "hop"]), 1.2)
        self.spawn("heart", 5)
        self.say(random.choice(["嘿嘿，这一下很受用。", "收到摸摸，心情回温。", "继续陪你一起混工位。"]), 2.2)
        self.show_status(3.8)

    def feed_pet(self):
        now = time.monotonic()
        if now < self.food_until:
            self.say("零食还在嚼，再等我一下。", 2.0)
            self.show_status(3.0)
            return
        self.food_until = now + 8
        self.stats.energy = clamp(self.stats.energy + 16, 0, 100)
        self.stats.mood = clamp(self.stats.mood + 8, 0, 100)
        self.stats.focus = clamp(self.stats.focus + 4, 0, 100)
        self.last_touch = now
        self.behavior = "snack"
        self.set_expr("chew", 2.0)
        self.set_act("chew", 1.8)
        self.spawn("star", 6)
        self.spawn("crumb", 5)
        self.say(random.choice(["咔滋咔滋，续命成功。", "好吃，今天继续营业。", "这口零食很提神。"]), 2.3)
        self.show_status(4.0)

    def set_behavior(self, kind):
        self.behavior = kind
        self.last_behavior = time.monotonic()
        if kind == "work":
            self.stats.focus = clamp(self.stats.focus + 14, 0, 100)
            self.stats.mood = clamp(self.stats.mood - 3, 0, 100)
            self.set_expr("focused", 1.6)
            self.set_act("nod", 1.0)
            self.say("收到，我开始假装整理周报。", 2.4)
        else:
            self.stats.mood = clamp(self.stats.mood + 10, 0, 100)
            self.stats.focus = clamp(self.stats.focus - 5, 0, 100)
            self.set_expr("mischief", 1.6)
            self.set_act("wiggle", 1.3)
            self.say("摸鱼许可已生效，状态良好。", 2.4)
        self.show_status(3.4)
        self.hide_menu()

    def toggle_roam(self):
        self.roam = not self.roam
        self.say("我先在原地发会呆。" if not self.roam else "继续沿着桌面散步。", 2.1)
        self.hide_menu()

    def snap(self):
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"+{sw - W - 30}+{sh - H - 70}")
        self.say("已贴边停靠，不挡你视线。", 2.1)
        self.hide_menu()

    def pick_pet(self, name):
        self.pet = name
        self.set_expr("sparkle", 1.4)
        self.set_act("hop", 1.0)
        self.spawn("star", 7)
        self.say(f"{name} 已上线，准备陪你摸鱼。", 2.5)
        self.show_status(4.0)
        self.menu_mode = "main"
        self.draw()

    def mood_logic(self):
        now = time.monotonic()
        if now - self.last_behavior < random.uniform(4.2, 7.2):
            return
        self.last_behavior = now
        if self.stats.energy < 20:
            self.behavior = "sleep"
            self.say("电量告急，先眯一会。", 2.8)
            return
        if self.stats.mood < 30:
            self.behavior = "seek"
            self.set_expr("sad", 2.0)
            self.say("今天有点蔫，摸摸我吧。", 2.4)
            return
        if self.stats.focus < 28 and self.stats.mood > 60:
            self.behavior = "slack"
            if random.random() < 0.55:
                self.set_expr("peek", 1.2)
                self.say("我觉得现在适合发会呆。", 2.2)
            return
        self.behavior = random.choice(["idle", "work", "slack", "idle"])
        if self.behavior == "work" and random.random() < 0.35:
            self.set_expr("focused", 1.0)

    def stat_logic(self):
        now = time.monotonic()
        if now - self.last_stats < 1.0:
            return
        steps = int(now - self.last_stats)
        self.last_stats += steps
        idle = now - self.last_touch
        for _ in range(steps):
            if self.behavior == "sleep":
                self.stats.energy = clamp(self.stats.energy + 2, 0, 100)
                self.stats.focus = clamp(self.stats.focus + 1, 0, 100)
                self.stats.mood = clamp(self.stats.mood + 1, 0, 100)
            elif self.behavior == "work":
                self.stats.focus = clamp(self.stats.focus + 1, 0, 100)
                self.stats.energy = clamp(self.stats.energy - 1, 0, 100)
                self.stats.mood = clamp(self.stats.mood - 1, 0, 100)
            elif self.behavior == "slack":
                self.stats.mood = clamp(self.stats.mood + 1, 0, 100)
                self.stats.focus = clamp(self.stats.focus - 1, 0, 100)
            else:
                if random.random() < 0.25:
                    self.stats.energy = clamp(self.stats.energy - 1, 0, 100)
                if random.random() < 0.2:
                    self.stats.focus = clamp(self.stats.focus - 1, 0, 100)
            if idle > 18 and random.random() < 0.4:
                self.stats.mood = clamp(self.stats.mood - 1, 0, 100)

    def move_logic(self):
        if self.drag or self.menu_open:
            return
        if time.monotonic() < self.inertia_until:
            x, y = self.root.winfo_x(), self.root.winfo_y()
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            nx = x + self.fling_vx
            ny = clamp(y + self.fling_vy, 10, sh - H - 45)
            if nx <= 0 or nx >= sw - W:
                self.face *= -1
                self.fling_vx *= -0.45
                nx = clamp(nx, 0, sw - W)
            self.root.geometry(f"+{int(nx)}+{int(ny)}")
            self.fling_vx *= 0.86
            self.fling_vy *= 0.8
            return
        if not self.roam:
            return
        if self.behavior == "sleep":
            self.speed = 0.0
            return
        self.speed = {"work": 1.0, "slack": 2.2, "seek": 2.7}.get(self.behavior, 1.5)
        if self.behavior == "idle" and random.random() < 0.04:
            self.face *= -1
        x, y = self.root.winfo_x(), self.root.winfo_y()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        nx = x + (self.speed if self.face > 0 else -self.speed)
        ny = clamp(y + math.sin(self.phase * 0.8) * (1.6 if self.behavior == "slack" else 0.8), 10, sh - H - 45)
        if nx <= 0 or nx >= sw - W:
            self.face *= -1
            nx = clamp(nx, 0, sw - W)
        self.root.geometry(f"+{int(nx)}+{int(ny)}")

    def face_name(self):
        now = time.monotonic()
        if self.expr and now < self.expr_until:
            return self.expr
        if self.behavior == "sleep":
            return "sleep"
        if self.behavior == "work":
            return "focused"
        if self.behavior == "seek":
            return "sad"
        if self.behavior == "snack":
            return "chew"
        if self.tick_id % 28 == 0:
            return "blink"
        return "idle"

    def anim_logic(self):
        self.phase += 0.15
        if not self.drag:
            self.tx += (1 - self.tx) * 0.22
            self.ty += (1 - self.ty) * 0.22
        self.sx += (self.tx - self.sx) * 0.34
        self.sy += (self.ty - self.sy) * 0.34
        keep = []
        now = time.monotonic()
        for p in self.particles:
            if now - p["born"] >= p["life"]:
                continue
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.04
            keep.append(p)
        self.particles = keep

    def head_bulges(self):
        if not self.drag or self.grab_part not in {"head", "cheek_left", "cheek_right", "crown"}:
            return []
        if self.grab_part == "cheek_left":
            ang = math.pi * 0.95
            return [(ang, 0.24 + self.drag_tension * 0.2, 0.42), (ang + 0.65, -0.09, 0.55)]
        if self.grab_part == "cheek_right":
            ang = 0.05
            return [(ang, 0.24 + self.drag_tension * 0.2, 0.42), (ang - 0.65, -0.09, 0.55)]
        if self.grab_part == "crown":
            ang = -math.pi / 2
            return [(ang, 0.2 + self.drag_tension * 0.24, 0.38), (ang + math.pi, -0.1, 0.8)]
        ang = math.atan2(self.grab[1] / 38.0, self.grab[0] / 40.0)
        ang += clamp(self.drag_vec[1] * 0.002 - self.drag_vec[0] * 0.0025, -0.3, 0.3)
        return [(ang, 0.16 + self.drag_tension * 0.24, 0.5), (ang + math.pi, -0.08, 0.95)]

    def body_bulges(self):
        if not self.drag or self.grab_part != "body":
            return []
        ang = math.atan2(self.grab[1] / 30.0, self.grab[0] / 34.0)
        return [(ang, 0.12 + self.drag_tension * 0.18, 0.6), (ang + math.pi, -0.06, 1.0)]
    def draw_bubble(self):
        if time.monotonic() > self.bubble_until:
            return
        c = self.cfg
        self.rr(38, 14, 242, 60, 16, fill=tint(c["panel"], 0.92), outline="")
        self.rr(34, 10, 238, 56, 16, fill="#fffefb", outline=c["panel"], width=2)
        self.cv.create_polygon(86, 54, 102, 54, 94, 68, fill="#fffefb", outline=c["panel"], width=2, smooth=True)
        self.cv.create_text(136, 33, text=self.bubble, fill="#543b2f", width=182, font=("Microsoft YaHei UI", 9, "bold"))

    def draw_switch_chip(self):
        c = self.cfg
        x1, y1, x2, y2 = 202, 10, 266, 34
        self.switch_rect = (x1, y1, x2, y2)
        self.rr(x1 + 3, y1 + 3, x2 + 3, y2 + 3, 12, fill=tint(c["panel"], 0.9), outline="")
        self.rr(x1, y1, x2, y2, 12, fill=c["badge"], outline=c["panel"], width=2)
        self.cv.create_text((x1 + x2) / 2, y1 + 8, text="换宠", fill="#543b2f", font=("Microsoft YaHei UI", 8, "bold"))
        self.cv.create_text((x1 + x2) / 2, y1 + 18, text=self.pet, fill=tint(c["outline"], 1.08), font=("Microsoft YaHei UI", 7))

    def draw_status(self):
        if time.monotonic() > self.status_until:
            return
        c = self.cfg
        self.rr(48, 190, 240, 232, 18, fill=tint(c["panel"], 0.92), outline="")
        self.rr(44, 186, 236, 228, 18, fill="#fffdf8", outline=c["panel"], width=2)
        self.cv.create_text(140, 204, text=f"心情 {self.stats.mood:02d}   精力 {self.stats.energy:02d}   专注 {self.stats.focus:02d}", fill="#543b2f", font=("Microsoft YaHei UI", 9, "bold"))
        labels = {"idle": "待机中", "work": "假装上班", "slack": "快乐摸鱼", "sleep": "补觉中", "seek": "求摸摸", "happy": "心情超好", "snack": "吃零食"}
        self.cv.create_text(140, 218, text=f"{self.pet} · {labels.get(self.behavior, '待机中')}", fill=tint(c["outline"], 1.08), font=("Microsoft YaHei UI", 8))

    def draw_particle(self, p):
        k = (time.monotonic() - p["born"]) / p["life"]
        size = p["size"] * (1 - k * 0.25)
        if p["kind"] == "heart":
            self.cv.create_text(p["x"], p["y"], text="♥", fill="#ff7da0", font=("Segoe UI Symbol", int(size), "bold"))
        elif p["kind"] == "star":
            self.cv.create_text(p["x"], p["y"], text="✦", fill="#ffbf47", font=("Segoe UI Symbol", int(size), "bold"))
        else:
            self.cv.create_oval(p["x"] - size * 0.22, p["y"] - size * 0.14, p["x"] + size * 0.22, p["y"] + size * 0.14, fill="#d9a46b", outline="")

    def draw_face(self, bx, by):
        c, expr = self.cfg, self.face_name()
        face_shift_x = 0
        face_shift_y = 0
        if self.drag:
            if self.grab_part == "cheek_left":
                face_shift_x = -4 - self.drag_tension * 4
            elif self.grab_part == "cheek_right":
                face_shift_x = 4 + self.drag_tension * 4
            elif self.grab_part == "crown":
                face_shift_y = -4 - self.drag_tension * 3
        eye_y = -17 if self.pet != "乌鲁鲁" else -14
        le, re = self.pt(bx, by, -14 + face_shift_x * 0.35, eye_y + face_shift_y), self.pt(bx, by, 14 + face_shift_x * 0.35, eye_y + face_shift_y)

        def eye(pos, rx=4, ry=5):
            self.cv.create_oval(pos[0] - rx, pos[1] - ry, pos[0] + rx, pos[1] + ry, fill="#3e3028", outline="")

        if expr in {"idle", "mischief", "chew", "surprised", "focused", "peek", "sparkle", "dizzy", "squish"}:
            eye(le, 5 if expr in {"focused", "dizzy"} else 4, 6 if expr == "surprised" else 5)
            if expr == "chew":
                self.cv.create_line(re[0] - 5, re[1], re[0] + 5, re[1], fill="#3e3028", width=3, capstyle=tk.ROUND)
            elif expr == "peek":
                self.cv.create_arc(re[0] - 6, re[1] - 2, re[0] + 6, re[1] + 8, start=200, extent=150, style=tk.ARC, outline="#3e3028", width=3)
            elif expr == "dizzy":
                self.cv.create_text(re[0], re[1], text="×", fill="#3e3028", font=("Microsoft YaHei UI", 10, "bold"))
            else:
                eye(re, 5 if expr in {"focused", "dizzy"} else 4, 6 if expr == "surprised" else 5)
        if expr in {"blink", "sleep"}:
            for p in (le, re):
                self.cv.create_line(p[0] - 5, p[1], p[0] + 5, p[1], fill="#3e3028", width=3, capstyle=tk.ROUND)
        elif expr in {"happy", "sparkle"}:
            for p in (le, re):
                self.cv.create_arc(p[0] - 7, p[1] - 2, p[0] + 7, p[1] + 9, start=200, extent=140, style=tk.ARC, outline="#3e3028", width=3)
        elif expr == "sad":
            self.cv.create_line(le[0] - 6, le[1] - 2, le[0] + 4, le[1] + 2, fill="#3e3028", width=3, capstyle=tk.ROUND)
            self.cv.create_line(re[0] - 4, re[1] + 2, re[0] + 6, re[1] - 2, fill="#3e3028", width=3, capstyle=tk.ROUND)
        elif expr == "squish":
            for p in (le, re):
                self.cv.create_arc(p[0] - 6, p[1] - 1, p[0] + 6, p[1] + 6, start=180, extent=180, style=tk.ARC, outline="#3e3028", width=3)
        if c["cheeks"] and expr in {"happy", "chew", "mischief", "sparkle", "squish"}:
            for x in (-20, 20):
                px, py = self.pt(bx, by, x + face_shift_x * 0.4, -2 + face_shift_y * 0.3)
                self.cv.create_oval(px - 7, py - 5, px + 7, py + 5, fill=c["accent"], outline="")
        if self.pet == "皮卡丘":
            for x in (-21, 21):
                px, py = self.pt(bx, by, x + face_shift_x * 0.45, -1 + face_shift_y * 0.35)
                self.cv.create_oval(px - 8, py - 7, px + 8, py + 7, fill=c["accent"], outline="")
        if self.pet == "乌鲁鲁":
            for x in (-20, 20):
                px, py = self.pt(bx, by, x + face_shift_x * 0.35, 1 + face_shift_y * 0.3)
                self.cv.create_arc(px - 8, py - 5, px + 8, py + 7, start=190, extent=160, style=tk.ARC, outline=tint(c["outline"], 1.05), width=2)
        if expr == "focused":
            for s, p in ((-1, le), (1, re)):
                self.cv.create_line(p[0] - 7, p[1] - 10 - s, p[0] + 7, p[1] - 8 + s, fill=tint(c["outline"], 1.1), width=3, capstyle=tk.ROUND)
        elif expr == "sad":
            for s, p in ((1, le), (-1, re)):
                self.cv.create_line(p[0] - 6, p[1] - 8 + s, p[0] + 6, p[1] - 10 - s, fill=tint(c["outline"], 1.1), width=3, capstyle=tk.ROUND)
        nx, ny = self.pt(bx, by, face_shift_x * 0.3, -8 + face_shift_y * 0.7)
        self.cv.create_oval(nx - 3, ny - 2, nx + 3, ny + 2, fill=tint(c["outline"], 1.1), outline="")
        mx, my = self.pt(bx, by, face_shift_x * 0.55, 5 + face_shift_y * 0.8)
        if expr in {"surprised", "dizzy"}:
            self.cv.create_oval(mx - 5, my - 3, mx + 5, my + 7, outline=tint(c["outline"], 1.1), width=3)
        elif expr in {"happy", "mischief", "chew", "sparkle", "peek"}:
            self.cv.create_arc(mx - 10, my - 2, mx + 10, my + 10, start=200, extent=140, style=tk.ARC, outline=tint(c["outline"], 1.1), width=3)
        elif expr == "sad":
            self.cv.create_arc(mx - 10, my + 3, mx + 10, my + 10, start=20, extent=140, style=tk.ARC, outline=tint(c["outline"], 1.1), width=3)
        elif expr == "squish":
            self.cv.create_arc(mx - 8, my, mx + 8, my + 7, start=180, extent=180, style=tk.ARC, outline=tint(c["outline"], 1.1), width=3)
        else:
            self.cv.create_line(mx - 7, my + 4, mx + 7, my + 4, fill=tint(c["outline"], 1.1), width=3, capstyle=tk.ROUND)
        if expr == "sleep":
            self.cv.create_text(bx + 44, by - 56, text="Z", fill="#9d86ff", font=("Segoe UI", 12, "bold"))
            self.cv.create_text(bx + 56, by - 70, text="z", fill="#9d86ff", font=("Segoe UI", 10, "bold"))
        if expr == "sparkle":
            self.cv.create_text(re[0] + 10, re[1] - 10, text="✦", fill=c["accent"], font=("Segoe UI Symbol", 9, "bold"))
        if self.pet == "乌鲁鲁":
            self.cv.create_arc(bx - 18, by - 5, bx + 18, by + 21, start=210, extent=120, style=tk.ARC, outline=tint(c["outline"], 1.06), width=2)

    def draw_tail(self, bx, by):
        c = self.cfg
        swing = math.sin(self.phase * (5.2 if self.behavior in {"happy", "slack"} else 3.6)) * 8
        if time.monotonic() < self.act_until and self.act == "wiggle":
            swing *= 1.8
        if c["tail_style"] == "lightning":
            pts = [(-30, 6), (-54, -2 + swing * 0.15), (-42, -6 + swing * 0.25), (-66, -26 + swing * 0.45), (-50, -22 + swing * 0.2), (-58, -48 + swing * 0.5), (-30, -18 + swing * 0.18)]
            self.cv.create_polygon(self.poly(bx, by, pts), fill=c["tail"], outline=c["outline"], width=4, smooth=True, splinesteps=18)
        elif c["tail_style"] == "ribbon":
            self.cv.create_line(self.poly(bx, by, [(-28, 10), (-50, 2 + swing * 0.2), (-62, -16 + swing)]), fill=c["tail"], width=12, smooth=True, capstyle=tk.ROUND)
            self.cv.create_oval(*self.oval(bx, by, -64, -19 + swing, 11, 8), fill=c["accent"], outline=c["outline"], width=3)
        else:
            self.cv.create_line(self.poly(bx, by, [(-28, 12), (-45, 2 + swing * 0.2), (-55, -10 + swing)]), fill=c["tail"], width=11, smooth=True, capstyle=tk.ROUND)

    def draw_ears(self, bx, by):
        c, st = self.cfg, self.cfg["ear_style"]
        if st == "cat":
            outer = [[(-28, -38), (-40, -73), (-16, -52)], [(28, -38), (40, -73), (16, -52)]]
            inner = [[(-25, -42), (-31, -61), (-18, -49)], [(25, -42), (31, -61), (18, -49)]]
        elif st == "fin":
            outer = [[(-22, -34), (-42, -66), (-8, -49)], [(22, -34), (42, -66), (8, -49)]]
            inner = [[(-20, -39), (-31, -58), (-10, -48)], [(20, -39), (31, -58), (10, -48)]]
        else:
            outer = [[(-21, -35), (-24, -96), (-10, -50)], [(21, -35), (24, -96), (10, -50)]]
            inner = [[(-17, -38), (-18, -73), (-10, -49)], [(17, -38), (18, -73), (10, -49)]]
        for pts in outer:
            self.cv.create_polygon(self.poly(bx, by, pts), fill=c["main"], outline=c["outline"], width=4, smooth=True, splinesteps=18)
        for pts in inner:
            self.cv.create_polygon(self.poly(bx, by, pts), fill=c["ear"], outline="", smooth=True, splinesteps=18)
        if st == "pika":
            self.cv.create_polygon(self.poly(bx, by, [(-22, -65), (-24, -96), (-15, -72)]), fill="#2d251e", outline="")
            self.cv.create_polygon(self.poly(bx, by, [(22, -65), (24, -96), (15, -72)]), fill="#2d251e", outline="")

    def draw_pet(self):
        c = self.cfg
        bx, by = self.anchor()
        self.cv.create_oval(bx - 56 * (1 + abs(self.sx - 1) * 0.38), 168, bx + 56 * (1 + abs(self.sx - 1) * 0.38), 180, fill=c["shadow"], outline="")
        self.draw_tail(bx, by)
        body_y = 20 if self.pet == "乌鲁鲁" else 18
        self.blob(bx, by, 0, body_y, c["body_rx"], c["body_ry"], c["main"], c["outline"], bulges=self.body_bulges())
        self.draw_ears(bx, by)
        head_y = -6 if self.pet == "乌鲁鲁" else -10
        self.blob(bx, by, 0, head_y, c["head_rx"], c["head_ry"], c["main"], c["outline"], bulges=self.head_bulges())
        muzzle_y = 2 if self.pet == "乌鲁鲁" else -2
        self.blob(bx, by, 0, muzzle_y, c["muzzle_rx"], c["muzzle_ry"], c["light"], c["outline"], 3)
        if self.drag and self.grab_part == "head":
            gx, gy = self.grab
            self.blob(
                bx,
                by,
                gx + self.drag_vec[0] * 0.07,
                gy + self.drag_vec[1] * 0.05 - 4,
                12 + 10 * (0.35 + self.drag_tension * 0.7),
                9 + 8 * (0.35 + self.drag_tension * 0.7),
                c["main"],
                c["outline"],
                3,
            )
        paw_lift = 0
        if time.monotonic() < self.act_until and self.act == "wave":
            paw_lift = 14 + math.sin(self.phase * 7.2) * 5
        elif time.monotonic() < self.act_until and self.act == "hop":
            paw_lift = 6 + abs(math.sin(self.phase * 6.0)) * 6
        for x, y in [(-18, 44), (18, 44 - paw_lift)]:
            paw_y = y + (4 if self.pet == "乌鲁鲁" else 0)
            self.cv.create_oval(*self.oval(bx, by, x, paw_y, c["paw_rx"], c["paw_ry"]), fill=c["light"], outline=c["outline"], width=3)
        self.cv.create_oval(*self.oval(bx, by, 0, 24 if self.pet != "乌鲁鲁" else 28, 22 if self.pet != "皮卡丘" else 18, 17 if self.pet != "乌鲁鲁" else 20), fill=c["light"], outline="")
        if c["stripes"]:
            for dy in (-10, 2):
                self.cv.create_polygon(self.poly(bx, by, [(-10, dy + 20), (-2, dy + 12), (4, dy + 18), (-2, dy + 30)]), fill="#8f6b36", outline="", smooth=True)
        if c["bobble"]:
            self.cv.create_line(self.poly(bx, by, [(0, -44), (0, -60)]), fill=c["outline"], width=3, capstyle=tk.ROUND)
            self.cv.create_oval(*self.oval(bx, by, 0, -65, 7, 7), fill=c["accent"], outline=c["outline"], width=2)
            self.cv.create_polygon(self.poly(bx, by, [(-31, 4), (-43, 12), (-34, 22), (-18, 14)]), fill=tint(c["main"], 0.96), outline=c["outline"], width=3, smooth=True)
            self.cv.create_polygon(self.poly(bx, by, [(31, 4), (43, 12), (34, 22), (18, 14)]), fill=tint(c["main"], 0.96), outline=c["outline"], width=3, smooth=True)
        if self.pet == "皮卡丘":
            for x in (-25, 25):
                self.cv.create_oval(*self.oval(bx, by, x, 18, 6, 11), fill=c["main"], outline=c["outline"], width=3)
        if self.pet == "乌鲁鲁":
            self.cv.create_arc(bx - 32, by + 14, bx - 2, by + 44, start=250, extent=80, style=tk.ARC, outline=tint(c["accent"], 1.05), width=3)
            self.cv.create_arc(bx + 2, by + 14, bx + 32, by + 44, start=210, extent=80, style=tk.ARC, outline=tint(c["accent"], 1.05), width=3)
        if time.monotonic() < self.act_until and self.act == "chew":
            cx, cy = self.pt(bx, by, 18, 8)
            self.cv.create_oval(cx - 3, cy - 2, cx + 3, cy + 2, fill="#d8a26f", outline="")
        self.draw_face(bx, by)
    def menu_model(self):
        if self.menu_mode == "pets":
            return [
                ("团子", "软乎乎陪伴", PETS["团子"]["badge"], lambda: self.pick_pet("团子")),
                ("乌鲁鲁", "蓝白灵感体", PETS["乌鲁鲁"]["badge"], lambda: self.pick_pet("乌鲁鲁")),
                ("皮卡丘", "元气电力感", PETS["皮卡丘"]["badge"], lambda: self.pick_pet("皮卡丘")),
                ("返回", "回主菜单", self.cfg["badge"], lambda: setattr(self, "menu_mode", "main") or self.draw()),
            ]
        roam = "恢复巡逻" if not self.roam else "暂停巡逻"
        return [
            ("摸摸它", "互动安抚", self.cfg["badge"], lambda: (self.hide_menu(), self.pet_pet())),
            ("喂零食", "补充精力", self.cfg["badge"], lambda: (self.hide_menu(), self.feed_pet())),
            ("看看状态", "显示词条", self.cfg["badge"], lambda: (self.show_status(4), self.hide_menu())),
            (roam, "桌面行动", self.cfg["badge"], self.toggle_roam),
            ("认真上班", "切工作态", self.cfg["badge"], lambda: self.set_behavior("work")),
            ("批准摸鱼", "切摸鱼态", self.cfg["badge"], lambda: self.set_behavior("slack")),
            ("宠物库", self.pet, self.cfg["badge"], lambda: setattr(self, "menu_mode", "pets") or self.draw()),
            ("贴边停靠", "靠右下角", self.cfg["badge"], self.snap),
            ("退出", "关闭桌宠", self.cfg["badge"], self.root.destroy),
        ]

    def draw_menu(self):
        if not self.menu_open:
            return
        c = self.cfg
        self.rr(24, 66, 268, 240, 22, fill=tint(c["panel"], 0.88), outline="")
        self.rr(18, 58, 262, 232, 22, fill=c["menu"], outline=c["panel"], width=2)
        self.cv.create_text(40, 78, text="桌宠控制台" if self.menu_mode == "main" else "宠物库", anchor="w", fill="#543b2f", font=("Microsoft YaHei UI", 11, "bold"))
        self.cv.create_text(240, 78, text=self.pet, anchor="e", fill=tint(c["outline"], 1.08), font=("Microsoft YaHei UI", 8, "bold"))
        self.menu_items = []
        items = self.menu_model()
        cols, w, h, sx, sy = (1, 204, 30, 38, 104) if self.menu_mode == "pets" else (2, 102, 28, 34, 104)
        for i, (title, sub, fill, fn) in enumerate(items):
            col, row = i % cols, i // cols
            x1, y1 = sx + col * (w + 12), sy + row * (h + 10)
            x2, y2 = x1 + w, y1 + h
            if y2 > 220:
                break
            hover = i == self.menu_hover
            self.rr(x1, y1, x2, y2, 14, fill=c["panel"] if hover else fill, outline=tint(c["panel"], 1.0), width=2)
            self.cv.create_text(x1 + 12, y1 + 11, text=title, anchor="w", fill="#543b2f", font=("Microsoft YaHei UI", 9, "bold"))
            self.cv.create_text(x1 + 12, y1 + 22, text=sub, anchor="w", fill=tint(c["outline"], 1.08), font=("Microsoft YaHei UI", 7))
            self.menu_items.append({"rect": (x1, y1, x2, y2), "fn": fn})

    def draw(self):
        self.cv.delete("all")
        self.draw_bubble()
        self.draw_switch_chip()
        self.draw_pet()
        for p in self.particles:
            self.draw_particle(p)
        self.draw_status()
        self.draw_menu()

    def loop(self):
        self.tick_id += 1
        self.mood_logic()
        self.stat_logic()
        self.move_logic()
        self.anim_logic()
        if self.stats.energy <= 10:
            self.behavior = "sleep"
        elif self.behavior == "sleep" and self.stats.energy >= 56:
            self.behavior = "idle"
            self.set_expr("sparkle", 1.2)
            self.say("我醒啦，继续陪你。", 2.1)
        if time.monotonic() >= self.expr_until:
            self.expr = None
        if time.monotonic() >= self.act_until:
            self.act = ""
        self.draw()
        self.root.after(33, self.loop)


def main():
    root = tk.Tk()
    OfficePet(root)
    root.mainloop()


if __name__ == "__main__":
    main()
