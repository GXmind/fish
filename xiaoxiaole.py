import pygame
import random
import json
import os
import math

# --- 配置 ---
SCREEN_WIDTH, SCREEN_HEIGHT = 480, 780
GRID_SIZE = 8
TILE_SIZE = 50
OFFSET_X = (SCREEN_WIDTH - GRID_SIZE * TILE_SIZE) // 2
OFFSET_Y = 185

# 颜色
COLORS = [
    (255, 80,  80),   # 0 红
    (80,  220, 80),   # 1 绿
    (80,  130, 255),  # 2 蓝
    (255, 230, 60),   # 3 黄
    (255, 150, 50),   # 4 橙
    (200, 80,  255),  # 5 紫
]
BG_COLOR  = (20, 20, 28)
DARK_CELL = (35, 35, 45)

# 特殊方块类型
# base_color = val % 10  (0-5)
# 0-5   : 普通
# 10-15 : 横消 (消一整行)
# 20-25 : 纵消 (消一整列)
# 30-35 : 炸弹 (5x5)
# 40    : 彩虹全消 (无色)
SPECIAL_NONE   = 0
SPECIAL_ROW    = 10
SPECIAL_COL    = 20
SPECIAL_BOMB   = 30
SPECIAL_RAINBOW = 40

# ------------------------------------------------------------------ helpers --
def lerp(a, b, t):
    return a + (b - a) * t

def ease_out(t):
    return 1 - (1 - t) ** 3

def ease_in_out(t):
    return t * t * (3 - 2 * t)

# ============================================================= AnimTile =======
class AnimTile:
    """单格动画状态"""
    def __init__(self):
        self.ox = 0.0   # 视觉偏移 x
        self.oy = 0.0   # 视觉偏移 y
        self.scale = 1.0
        self.alpha = 255
        self.phase = "idle"   # idle / swap / fall / pop / spawn
        self.t   = 0.0
        self.dur = 0.0
        # swap 专用
        self.swap_dx = 0.0
        self.swap_dy = 0.0
        # fall 专用
        self.fall_from = 0.0  # 像素偏移起点
        # pop 粒子
        self.pop_particles = []

    def start_swap(self, dx_px, dy_px, dur=0.18):
        self.phase = "swap"
        self.swap_dx = dx_px
        self.swap_dy = dy_px
        self.t = 0.0
        self.dur = dur

    def start_fall(self, from_oy, dur=0.25):
        self.phase = "fall"
        self.fall_from = from_oy
        self.oy = from_oy
        self.t = 0.0
        self.dur = dur

    def start_pop(self, color):
        self.phase = "pop"
        self.t = 0.0
        self.dur = 0.3
        self.pop_particles = []
        for _ in range(8):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.5, 4.0)
            self.pop_particles.append({
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "color": color,
                "x": 0.0, "y": 0.0,
                "life": random.uniform(0.5, 1.0),
            })

    def start_spawn(self, dur=0.2):
        self.phase = "spawn"
        self.scale = 0.0
        self.t = 0.0
        self.dur = dur

    def update(self, dt):
        if self.phase == "idle":
            return False

        self.t += dt
        progress = min(1.0, self.t / self.dur) if self.dur > 0 else 1.0

        if self.phase == "swap":
            e = ease_in_out(progress)
            self.ox = self.swap_dx * (1 - e)
            self.oy = self.swap_dy * (1 - e)
            if progress >= 1.0:
                self.ox = 0; self.oy = 0
                self.phase = "idle"
                return True

        elif self.phase == "fall":
            e = ease_out(progress)
            self.oy = self.fall_from * (1 - e)
            if progress >= 1.0:
                self.oy = 0
                self.phase = "idle"
                return True

        elif self.phase == "spawn":
            self.scale = ease_out(progress)
            if progress >= 1.0:
                self.scale = 1.0
                self.phase = "idle"
                return True

        elif self.phase == "pop":
            e = progress
            self.scale = 1.0 - ease_out(e)
            self.alpha = int(255 * (1 - e))
            for p in self.pop_particles:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["vy"] += 0.2  # 重力
            if progress >= 1.0:
                self.phase = "idle"
                self.scale = 1.0
                self.alpha = 255
                return True

        return False

    def is_animating(self):
        return self.phase != "idle"


# ============================================================= Match3Pro ======
class Match3Pro:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("消消乐·进阶道具版")
        self.clock = pygame.time.Clock()

        # 字体
        self.font_sm  = pygame.font.SysFont("SimHei", 20)
        self.font_md  = pygame.font.SysFont("SimHei", 26)
        self.font_lg  = pygame.font.SysFont("Arial",  46, bold=True)
        self.font_xl  = pygame.font.SysFont("Arial",  60, bold=True)

        self.save_file = "game_save_pro.json"
        self.user_data = self.load_progress()

        self.state = "MAP"
        self.current_level = 1
        self.anims = [[AnimTile() for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        # 结算覆盖动画
        self.settle_overlay_alpha = 0
        self.settle_stars = 0
        self.settle_timer  = 0.0

        # 分数动画
        self.score_popups = []   # {"text", "x","y","life","color"}

        self.reset_level_vars()

    # ----------------------------------------------------------------- save --
    def load_progress(self):
        if os.path.exists(self.save_file):
            with open(self.save_file, 'r') as f:
                return json.load(f)
        return {"unlocked": 1, "stars": {}}

    def save_progress(self, lvl, stars):
        self.user_data["stars"][str(lvl)] = max(
            self.user_data["stars"].get(str(lvl), 0), stars)
        if lvl == self.user_data["unlocked"] and lvl < 15:
            self.user_data["unlocked"] += 1
        with open(self.save_file, 'w') as f:
            json.dump(self.user_data, f)

    # ---------------------------------------------------------------- level --
    def reset_level_vars(self):
        self.grid = [[random.randint(0, 5) for _ in range(GRID_SIZE)]
                     for _ in range(GRID_SIZE)]
        self.anims = [[AnimTile() for _ in range(GRID_SIZE)]
                      for _ in range(GRID_SIZE)]
        self.remove_initial_matches()
        self.selected  = None
        self.score     = 0
        self.steps     = 20
        self.target    = 1000 + self.current_level * 500
        self.combo     = 0
        self.busy      = False   # 正在执行连锁/动画
        self.score_popups = []

    def remove_initial_matches(self):
        for _ in range(100):
            if not self.find_all_matches():
                break
            for r, c in self.find_all_matches():
                self.grid[r][c] = random.randint(0, 5)

    # ============================================================= 核心逻辑 ==
    def base_color(self, val):
        if val < 0: return -1
        if val >= SPECIAL_RAINBOW: return -1  # 彩虹无色
        return val % 10

    def special_type(self, val):
        if val < 0:  return -1
        if val >= SPECIAL_RAINBOW: return SPECIAL_RAINBOW
        if val >= SPECIAL_BOMB:   return SPECIAL_BOMB
        if val >= SPECIAL_COL:    return SPECIAL_COL
        if val >= SPECIAL_ROW:    return SPECIAL_ROW
        return SPECIAL_NONE

    def find_all_matches(self):
        matched = set()
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE - 2):
                v = [self.grid[r][c+i] for i in range(3)]
                if -1 not in v and v[0] != -1:
                    bc = [self.base_color(x) for x in v]
                    if bc[0] == bc[1] == bc[2]:
                        matched.update([(r, c), (r, c+1), (r, c+2)])
        for r in range(GRID_SIZE - 2):
            for c in range(GRID_SIZE):
                v = [self.grid[r+i][c] for i in range(3)]
                if -1 not in v and v[0] != -1:
                    bc = [self.base_color(x) for x in v]
                    if bc[0] == bc[1] == bc[2]:
                        matched.update([(r, c), (r+1, c), (r+2, c)])
        return matched

    def find_match_lines(self):
        """返回所有连续相同色的线段（用于判断4消/5消及方向）。
        特殊道具参与颜色匹配（用 base_color 比较），-1 空格断开。
        """
        lines = []

        def flush(run, direction):
            if len(run) >= 3:
                lines.append({"cells": run[:], "dir": direction})

        # 横向
        for r in range(GRID_SIZE):
            run = []
            for c in range(GRID_SIZE):
                v = self.grid[r][c]
                bc = self.base_color(v)
                if bc < 0:                          # 空格或彩虹断开
                    flush(run, "h"); run = []
                elif not run:
                    run = [(r, c)]                  # 行首/断后第一个
                elif bc != self.base_color(self.grid[run[-1][0]][run[-1][1]]):
                    flush(run, "h"); run = [(r, c)] # 颜色变了
                else:
                    run.append((r, c))
            flush(run, "h")

        # 纵向
        for c in range(GRID_SIZE):
            run = []
            for r in range(GRID_SIZE):
                v = self.grid[r][c]
                bc = self.base_color(v)
                if bc < 0:
                    flush(run, "v"); run = []
                elif not run:
                    run = [(r, c)]
                elif bc != self.base_color(self.grid[run[-1][0]][run[-1][1]]):
                    flush(run, "v"); run = [(r, c)]
                else:
                    run.append((r, c))
            flush(run, "v")

        return lines

    def collect_special_triggers(self, matched_cells):
        """收集所有需要触发的特殊道具格，返回要删除的格子集合"""
        to_del = set(matched_cells)
        queue  = list(matched_cells)
        visited = set()
        while queue:
            r, c = queue.pop()
            if (r, c) in visited: continue
            visited.add((r, c))
            val = self.grid[r][c]
            sp  = self.special_type(val)
            if sp == SPECIAL_ROW:
                for cc in range(GRID_SIZE):
                    to_del.add((r, cc)); queue.append((r, cc))
            elif sp == SPECIAL_COL:
                for rr in range(GRID_SIZE):
                    to_del.add((rr, c)); queue.append((rr, c))
            elif sp == SPECIAL_BOMB:
                # 炸弹：菱形范围（曼哈顿距离 <= 2）
                #   X
                #  XXX
                # XXXXX
                #  XXX
                #   X
                for dr in range(-2, 3):
                    for dc in range(-2, 3):
                        if abs(dr) + abs(dc) <= 2:
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                                to_del.add((nr, nc)); queue.append((nr, nc))
            elif sp == SPECIAL_RAINBOW:
                # 全消某色 —— 选最多的普通色
                color_counts = {}
                for rr in range(GRID_SIZE):
                    for cc in range(GRID_SIZE):
                        bc = self.base_color(self.grid[rr][cc])
                        if 0 <= bc <= 5:
                            color_counts[bc] = color_counts.get(bc, 0) + 1
                if color_counts:
                    target_col = max(color_counts, key=color_counts.get)
                    for rr in range(GRID_SIZE):
                        for cc in range(GRID_SIZE):
                            if self.base_color(self.grid[rr][cc]) == target_col:
                                to_del.add((rr, cc)); queue.append((rr, cc))
        return to_del

    def rainbow_combine_with_special(self, r1, c1, r2, c2):
        """彩虹 + 特殊道具组合触发"""
        v1, v2 = self.grid[r1][c1], self.grid[r2][c2]
        rainbow_r, rainbow_c = (r1, c1) if self.special_type(v1) == SPECIAL_RAINBOW else (r2, c2)
        other_r,   other_c   = (r2, c2) if (rainbow_r, rainbow_c) == (r1, c1) else (r1, c1)
        other_sp = self.special_type(self.grid[other_r][other_c])
        to_del = set()
        if other_sp in (SPECIAL_ROW, SPECIAL_COL, SPECIAL_BOMB):
            # 全场同色格都变成 other_sp 类型并依次触发
            other_val = self.grid[other_r][other_c]
            bc_other  = self.base_color(other_val)
            for rr in range(GRID_SIZE):
                for cc in range(GRID_SIZE):
                    if self.base_color(self.grid[rr][cc]) == bc_other:
                        self.grid[rr][cc] = other_sp + bc_other
            # 然后正常触发消除
            all_cells = [(rr, cc) for rr in range(GRID_SIZE)
                         for cc in range(GRID_SIZE)
                         if self.base_color(self.grid[rr][cc]) == bc_other]
            to_del = self.collect_special_triggers(set(all_cells))
        else:
            # 纯彩虹消除最多色
            to_del = self.collect_special_triggers({(rainbow_r, rainbow_c)})
        to_del.add((r1, c1)); to_del.add((r2, c2))
        return to_del

    # ============================================================= 游戏流程 ==
    def try_swap(self, r1, c1, r2, c2):
        """尝试交换，处理动画与逻辑"""
        if self.busy: return
        dx1 = (c2 - c1) * TILE_SIZE
        dy1 = (r2 - r1) * TILE_SIZE
        # 先播放交换动画
        self.anims[r1][c1].start_swap(dx1, dy1)
        self.anims[r2][c2].start_swap(-dx1, -dy1)
        self.busy = True
        pygame.time.set_timer(pygame.USEREVENT + 1, 200, 1)  # 200ms 后执行逻辑
        self._pending_swap = (r1, c1, r2, c2)

    def execute_swap(self):
        r1, c1, r2, c2 = self._pending_swap
        self.grid[r1][c1], self.grid[r2][c2] = self.grid[r2][c2], self.grid[r1][c1]

        # 特殊道具与彩虹直接触发
        v1, v2 = self.grid[r1][c1], self.grid[r2][c2]
        sp1, sp2 = self.special_type(v1), self.special_type(v2)

        direct_trigger = False
        to_del = set()

        if sp1 == SPECIAL_RAINBOW and sp2 == SPECIAL_RAINBOW:
            to_del = {(rr, cc) for rr in range(GRID_SIZE) for cc in range(GRID_SIZE)}
            direct_trigger = True
        elif sp1 == SPECIAL_RAINBOW or sp2 == SPECIAL_RAINBOW:
            if sp1 != SPECIAL_NONE or sp2 != SPECIAL_NONE:
                to_del = self.rainbow_combine_with_special(r1, c1, r2, c2)
            else:
                to_del = self.collect_special_triggers({(r1, c1), (r2, c2)})
            direct_trigger = True
        elif (sp1 != SPECIAL_NONE) and (sp2 != SPECIAL_NONE):
            to_del = self.collect_special_triggers({(r1, c1), (r2, c2)})
            direct_trigger = True
        elif sp1 != SPECIAL_NONE or sp2 != SPECIAL_NONE:
            sp_r, sp_c = (r1, c1) if sp1 != SPECIAL_NONE else (r2, c2)
            to_del = self.collect_special_triggers({(sp_r, sp_c)})
            direct_trigger = True

        if direct_trigger and to_del:
            self.steps -= 1
            self.combo = 1
            # ★ 计算并加分
            score_gain = len(to_del) * 20 * self.combo
            self.score += score_gain
            self.spawn_score_popup(score_gain, to_del)
            self.delete_cells(to_del)
            self.do_fall_and_refill()
            self.process_chain()
        elif self.find_all_matches():
            self.steps -= 1
            self.combo = 0
            # 交换后两个格子都可能参与匹配，传入两个候选位置
            self.process_chain(swap_candidates=[(r1, c1), (r2, c2)])
        else:
            # 无效交换 —— 回退动画
            self.grid[r1][c1], self.grid[r2][c2] = self.grid[r2][c2], self.grid[r1][c1]
            self.anims[r1][c1].start_swap(-((c2 - c1) * TILE_SIZE), -((r2 - r1) * TILE_SIZE))
            self.anims[r2][c2].start_swap((c2 - c1) * TILE_SIZE,  (r2 - r1) * TILE_SIZE)
            self.busy = False

    def _detect_special_creation(self, candidates, lines):
        """从候选格子中找出应该生成特殊道具的格子和类型。
        candidates: [(r,c), ...] 本次交换的两个格子
        lines: find_match_lines() 的结果
        返回 dict {(r,c): new_val}
        """
        new_specials = {}
        for sr, sc in candidates:
            swap_lines = [l for l in lines if (sr, sc) in l["cells"]]
            if not swap_lines:
                continue

            # 读颜色：从匹配线中找第一个有效 base_color
            bc = -1
            for sl in swap_lines:
                for (rr, cc) in sl["cells"]:
                    candidate_bc = self.base_color(self.grid[rr][cc])
                    if candidate_bc >= 0:
                        bc = candidate_bc
                        break
                if bc >= 0:
                    break
            if bc < 0:
                bc = 0

            h_lines = [l for l in swap_lines if l["dir"] == "h"]
            v_lines = [l for l in swap_lines if l["dir"] == "v"]
            has_cross = bool(h_lines and v_lines)

            max_h = max((len(l["cells"]) for l in h_lines), default=0)
            max_v = max((len(l["cells"]) for l in v_lines), default=0)
            max_n = max(max_h, max_v)

            if has_cross:
                new_specials[(sr, sc)] = SPECIAL_BOMB + bc
            elif max_n >= 5:
                new_specials[(sr, sc)] = SPECIAL_RAINBOW
            elif max_n == 4:
                new_specials[(sr, sc)] = (SPECIAL_ROW if max_h == 4 else SPECIAL_COL) + bc
            # max_n == 3：普通三消，不生成道具

        return new_specials

    def process_chain(self, swap_candidates=None):
        """逐波消除，含道具生成。
        swap_candidates: [(r1,c1),(r2,c2)] 本次交换的两个格子位置，用于判断4消/5消
        """
        while True:
            lines = self.find_match_lines()
            if not lines:
                break

            all_matched = set()
            for ln in lines:
                all_matched.update(ln["cells"])
            if not all_matched:
                break

            self.combo += 1

            # ---- 道具生成判断（在删除前读颜色）----
            new_specials = {}
            if swap_candidates:
                new_specials = self._detect_special_creation(swap_candidates, lines)

            # ---- 确定要删除的格子：只删普通格，特殊道具参与匹配时才触发 ----
            to_del = set(all_matched) - set(new_specials.keys())

            # 被匹配到的特殊道具 → 触发连锁
            for r, c in list(all_matched):
                if (r, c) in new_specials:
                    continue
                sp = self.special_type(self.grid[r][c])
                if sp != SPECIAL_NONE:
                    extra = self.collect_special_triggers({(r, c)})
                    to_del.update(extra)

            # 如果新道具位置也被连锁删除范围覆盖，取消在该位置生成道具
            for pos in list(new_specials.keys()):
                if pos in to_del:
                    del new_specials[pos]

            score_gain = len(to_del) * 20 * self.combo
            self.score += score_gain
            self.spawn_score_popup(score_gain, to_del)

            self.delete_cells(to_del)

            # 生成新道具并渲染足够帧让玩家看清
            if new_specials:
                for (r, c), val in new_specials.items():
                    self.grid[r][c] = val
                    self.anims[r][c].start_spawn(0.4)
                self._render_frames(35)

            self.do_fall_and_refill()
            swap_candidates = None  # 只有第一波消除才尝试生成道具

        # 结算判断：
        # - 三星达到 (>= target*2) 且还有剩余步数 → 步数奖励
        # - 步数用完 → 直接结算
        # - 一/二星达标但步数未用完 → 继续游戏（让玩家用完步数冲更高分）
        if self.score >= self.target * 2 and self.steps > 0:
            self.start_bonus_phase()
        elif self.steps <= 0:
            self._finish_level()
        else:
            self.busy = False

    def delete_cells(self, to_del):
        """播放消除动画并清除格子"""
        for r, c in to_del:
            val = self.grid[r][c]
            if val >= 0:
                bc = self.base_color(val)
                color = COLORS[bc] if 0 <= bc <= 5 else (255, 255, 255)
                self.anims[r][c].start_pop(color)
            self.grid[r][c] = -1
        # 渲染几帧让爆炸动画可见
        self._render_frames(18)

    def do_fall_and_refill(self):
        """掉落：按列计算最终位置后一次性移动，避免颜色闪烁。"""
        # 1. 展示空白格子状态
        self._render_frames(6)

        # 2. 逐列处理：记录原始位置 → 一次性落到最终位置
        for c in range(GRID_SIZE):
            # 收集当前列非空格（含特殊道具），记录原始行号
            col_vals = []   # (original_row, value)
            for r in range(GRID_SIZE):
                if self.grid[r][c] != -1:
                    col_vals.append((r, self.grid[r][c]))

            empty_count = GRID_SIZE - len(col_vals)

            # 先清空整列
            for r in range(GRID_SIZE):
                self.grid[r][c] = -1

            # 现有方块落到底部（从底往上填）
            for i, (orig_r, val) in enumerate(reversed(col_vals)):
                dest_r = GRID_SIZE - 1 - i
                self.grid[dest_r][c] = val
                fall_dist = dest_r - orig_r   # 正值=往下落
                if fall_dist > 0:
                    self.anims[dest_r][c].start_fall(-fall_dist * TILE_SIZE)
                # fall_dist==0 说明没动，不需要动画

            # 顶部生成新方块，从屏幕上方落入
            for i in range(empty_count):
                r = i
                self.grid[r][c] = random.randint(0, 5)
                # 从屏幕外落入：偏移 = -(empty_count - i) 格
                fall_px = -(empty_count - i) * TILE_SIZE
                self.anims[r][c].start_fall(fall_px)

        # 3. 渲染落下动画
        self._render_frames(22)

    def _render_frames(self, n):
        """渲染 n 帧，驱动动画"""
        for _ in range(n):
            dt = self.clock.tick(60) / 1000.0
            # 更新动画
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE):
                    self.anims[r][c].update(dt)
            # 更新分数弹出
            self.update_score_popups(dt)
            self.draw_playing()
            pygame.display.flip()
            # 处理基本事件防止卡死
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); raise SystemExit

    # ============================================================= 结算阶段 ==
    def start_bonus_phase(self):
        if self.steps <= 0:
            self._finish_level()
            return
        self.state = "SETTLING"
        self.busy = True

        remaining = self.steps
        self.steps = 0

        # === 第一阶段：把所有剩余步数随机变成特殊道具，逐个弹出 ===
        available = [(r, c) for r in range(GRID_SIZE)
                     for c in range(GRID_SIZE)
                     if self.grid[r][c] >= 0 and
                        self.special_type(self.grid[r][c]) == SPECIAL_NONE]
        random.shuffle(available)

        bonus_positions = []
        for i in range(remaining):
            if not available:
                available = [(r, c) for r in range(GRID_SIZE)
                             for c in range(GRID_SIZE)
                             if self.grid[r][c] >= 0 and
                                self.special_type(self.grid[r][c]) == SPECIAL_NONE]
                random.shuffle(available)
            if not available:
                break

            br, bc_idx = available.pop(0)
            bc = self.base_color(self.grid[br][bc_idx])
            if bc < 0:
                bc = 0
            sp_type = random.choice([SPECIAL_ROW, SPECIAL_COL, SPECIAL_BOMB,
                                      SPECIAL_BOMB, SPECIAL_RAINBOW])
            new_val = SPECIAL_RAINBOW if sp_type == SPECIAL_RAINBOW else sp_type + bc
            self.grid[br][bc_idx] = new_val
            self.anims[br][bc_idx].start_spawn(0.35)
            bonus_positions.append((br, bc_idx))
            # 每个道具逐个弹出，给玩家时间看清楚
            self._render_frames(18)

        # 全部生成后停顿，让玩家欣赏一下
        self._render_frames(50)

        # === 第二阶段：统一触发所有奖励道具 ===
        if bonus_positions:
            all_to_del = self.collect_special_triggers(set(bonus_positions))
            score_gain = len(all_to_del) * 20
            self.score += score_gain
            self.spawn_score_popup(score_gain, all_to_del)
            self.delete_cells(all_to_del)
            self.do_fall_and_refill()
            self.process_chain_silent()

        self._finish_level()

    def process_chain_silent(self):
        """结算时不生成新道具的连锁消除"""
        while True:
            all_matched = self.find_all_matches()
            if not all_matched: break
            to_del = self.collect_special_triggers(all_matched)
            score_gain = len(to_del) * 20
            self.score += score_gain
            self.spawn_score_popup(score_gain, to_del)
            self.delete_cells(to_del)
            self.do_fall_and_refill()

    def _finish_level(self):
        stars = 0
        if self.score >= self.target:           stars = 1
        if self.score >= self.target * 1.5:     stars = 2
        if self.score >= self.target * 2:       stars = 3
        self.settle_stars = stars
        self.save_progress(self.current_level, stars)
        self._render_frames(60)   # 多渲染一秒让最终分看清楚
        self.state = "RESULT"
        self.settle_timer = 0.0
        self.busy = False

    # ============================================================= 分数弹窗 ==
    def spawn_score_popup(self, score, cells):
        if not cells or score <= 0: return
        r_avg = sum(r for r, c in cells) / len(cells)
        c_avg = sum(c for r, c in cells) / len(cells)
        x = OFFSET_X + c_avg * TILE_SIZE + TILE_SIZE // 2
        y = OFFSET_Y + r_avg * TILE_SIZE
        self.score_popups.append({
            "text": f"+{score}",
            "x": x, "y": y,
            "life": 1.2,
            "color": (255, 240, 60),
        })

    def update_score_popups(self, dt):
        for p in self.score_popups:
            p["life"] -= dt
            p["y"] -= 40 * dt
        self.score_popups = [p for p in self.score_popups if p["life"] > 0]

    # ============================================================= 绘制 ======
    def draw_tile(self, r, c, val, x, y):
        if val < 0: return
        anim = self.anims[r][c]
        bc   = self.base_color(val)
        sp   = self.special_type(val)
        color = COLORS[bc] if 0 <= bc <= 5 else (255, 255, 255)

        # 应用动画偏移
        rx = x + anim.ox
        ry = y + anim.oy
        sc = anim.scale
        tile_w = int((TILE_SIZE - 8) * sc)
        tile_h = int((TILE_SIZE - 8) * sc)
        bx = int(rx + 4 + (TILE_SIZE - 8 - tile_w) / 2)
        by = int(ry + 4 + (TILE_SIZE - 8 - tile_h) / 2)

        if tile_w <= 0 or tile_h <= 0: return

        # 创建带 alpha 的表面
        surf = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)

        # 阴影
        shadow_rect = pygame.Rect(3, 5, tile_w-3, tile_h-3)
        pygame.draw.rect(surf, (0, 0, 0, 80), shadow_rect, border_radius=12)

        # 主体
        body_rect = pygame.Rect(0, 0, tile_w, tile_h)
        pygame.draw.rect(surf, color + (anim.alpha,), body_rect, border_radius=12)

        # 高光
        hi_rect = pygame.Rect(4, 3, tile_w - 10, tile_h // 3)
        pygame.draw.rect(surf, (255, 255, 255, 60), hi_rect, border_radius=8)

        # 特殊标记
        cx, cy = tile_w // 2, tile_h // 2
        white = (255, 255, 255, 220)

        if sp == SPECIAL_ROW:
            for dx in [-6, 0, 6]:
                pygame.draw.line(surf, white, (cx + dx - 4, cy), (cx + dx + 4, cy), 2)
            # 两端箭头
            pygame.draw.polygon(surf, white, [(4, cy), (10, cy-4), (10, cy+4)])
            pygame.draw.polygon(surf, white, [(tile_w-4, cy), (tile_w-10, cy-4), (tile_w-10, cy+4)])

        elif sp == SPECIAL_COL:
            for dy in [-6, 0, 6]:
                pygame.draw.line(surf, white, (cx, cy + dy - 4), (cx, cy + dy + 4), 2)
            pygame.draw.polygon(surf, white, [(cx, 4), (cx-4, 10), (cx+4, 10)])
            pygame.draw.polygon(surf, white, [(cx, tile_h-4), (cx-4, tile_h-10), (cx+4, tile_h-10)])

        elif sp == SPECIAL_BOMB:
            # 炸弹图标：菱形轮廓
            pts = [
                (cx,      cy - 14),   # 上
                (cx + 14, cy),         # 右
                (cx,      cy + 14),   # 下
                (cx - 14, cy),         # 左
            ]
            pygame.draw.polygon(surf, white, pts, 2)
            # 中间小十字
            pygame.draw.line(surf, white, (cx-5, cy), (cx+5, cy), 2)
            pygame.draw.line(surf, white, (cx, cy-5), (cx, cy+5), 2)

        elif sp == SPECIAL_RAINBOW:
            # 彩虹：旋转彩色圆环
            for i in range(6):
                rad = math.radians(i * 60)
                px = cx + int(math.cos(rad) * 10)
                py = cy + int(math.sin(rad) * 10)
                pygame.draw.circle(surf, COLORS[i] + (220,), (px, py), 4)
            pygame.draw.circle(surf, (255, 255, 255, 200), (cx, cy), 4)

        self.screen.blit(surf, (bx, by))

        # 爆炸粒子
        if anim.phase == "pop":
            for p in anim.pop_particles:
                alpha = max(0, int(255 * (anim.dur - anim.t) / anim.dur))
                px = int(x + TILE_SIZE//2 + p["x"] * 3)
                py = int(y + TILE_SIZE//2 + p["y"] * 3)
                s = pygame.Surface((6, 6), pygame.SRCALPHA)
                pygame.draw.circle(s, p["color"] + (alpha,), (3, 3), 3)
                self.screen.blit(s, (px-3, py-3))

    def draw_star_bar(self):
        bar_x, bar_y = 40, 118
        bar_w = SCREEN_WIDTH - 80
        # 背景
        pygame.draw.rect(self.screen, (45, 45, 58), (bar_x, bar_y, bar_w, 14), border_radius=7)
        # 进度
        thresholds = [1.0, 1.5, 2.0]
        progress = min(1.0, self.score / (self.target * 2))
        fill_w = int(bar_w * progress)
        # 渐变色
        for i in range(fill_w):
            t   = i / max(1, bar_w)
            r_c = int(lerp(80, 255, t))
            g_c = int(lerp(200, 220, t))
            b_c = 40
            pygame.draw.line(self.screen, (r_c, g_c, b_c), (bar_x+i, bar_y+2), (bar_x+i, bar_y+11))

        # 星级点与分割线
        star_labels = ["★", "★", "★"]
        for idx, thresh in enumerate(thresholds):
            px = bar_x + int(bar_w * thresh / 2)
            filled = self.score >= self.target * thresh
            # 竖线分割
            pygame.draw.line(self.screen, (20,20,30), (px, bar_y), (px, bar_y+14), 2)
            # 星星
            color = (255, 215, 0) if filled else (80, 80, 80)
            st = self.font_sm.render(star_labels[idx], True, color)
            self.screen.blit(st, (px - st.get_width()//2, bar_y - 20))

    def draw_playing(self):
        self.screen.fill(BG_COLOR)

        # 顶部信息栏
        step_surf = self.font_xl.render(str(self.steps), True, (255, 255, 255))
        self.screen.blit(step_surf, (SCREEN_WIDTH//2 - step_surf.get_width()//2, 30))
        step_label = self.font_sm.render("剩余步数", True, (140, 140, 155))
        self.screen.blit(step_label, (SCREEN_WIDTH//2 - step_label.get_width()//2, 88))

        self.draw_star_bar()

        score_surf = self.font_md.render(f"分数 {self.score}", True, (200, 200, 215))
        self.screen.blit(score_surf, (SCREEN_WIDTH//2 - score_surf.get_width()//2, 140))

        # 棋盘背景
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                x = OFFSET_X + c * TILE_SIZE
                y = OFFSET_Y + r * TILE_SIZE
                shade = DARK_CELL if (r + c) % 2 == 0 else (40, 40, 52)
                pygame.draw.rect(self.screen, shade, (x, y, TILE_SIZE, TILE_SIZE))

        # 方块
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                x = OFFSET_X + c * TILE_SIZE
                y = OFFSET_Y + r * TILE_SIZE
                self.draw_tile(r, c, self.grid[r][c], x, y)

        # 选中高亮
        if self.selected:
            sr, sc = self.selected
            sx = OFFSET_X + sc * TILE_SIZE
            sy = OFFSET_Y + sr * TILE_SIZE
            pygame.draw.rect(self.screen, (255, 255, 255), (sx, sy, TILE_SIZE, TILE_SIZE), 3, 10)
            # 发光效果
            glow = pygame.Surface((TILE_SIZE+8, TILE_SIZE+8), pygame.SRCALPHA)
            pygame.draw.rect(glow, (255,255,255,40), (0, 0, TILE_SIZE+8, TILE_SIZE+8), border_radius=14)
            self.screen.blit(glow, (sx-4, sy-4))

        # 分数弹窗
        for p in self.score_popups:
            alpha = min(255, int(255 * p["life"] / 1.2))
            s = self.font_md.render(p["text"], True, p["color"])
            s.set_alpha(alpha)
            self.screen.blit(s, (int(p["x"]) - s.get_width()//2, int(p["y"])))

        # 结算状态提示
        if self.state == "SETTLING":
            lbl = self.font_md.render("✨ 步数奖励中...", True, (255, 215, 0))
            self.screen.blit(lbl, (SCREEN_WIDTH//2 - lbl.get_width()//2, SCREEN_HEIGHT - 50))

    # ============================================================= 结果界面 ==
    def draw_result(self):
        self.screen.fill(BG_COLOR)
        self.draw_playing()  # 底层

        # 半透明遮罩
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 190))
        self.screen.blit(overlay, (0, 0))

        # 卡片
        card_rect = pygame.Rect(60, 200, SCREEN_WIDTH-120, 320)
        pygame.draw.rect(self.screen, (35, 38, 55), card_rect, border_radius=24)
        pygame.draw.rect(self.screen, (80, 90, 130), card_rect, 2, border_radius=24)

        passed = self.score >= self.target
        title  = "关卡完成！" if passed else "关卡结束"
        color  = (100, 255, 160) if passed else (255, 120, 80)
        title_surf = self.font_lg.render(title, True, color)
        self.screen.blit(title_surf, (SCREEN_WIDTH//2 - title_surf.get_width()//2, 220))

        # 星星
        for i in range(3):
            filled = i < self.settle_stars
            star_color = (255, 215, 0) if filled else (60, 60, 80)
            star_surf = self.font_xl.render("★", True, star_color)
            bx = SCREEN_WIDTH//2 + (i-1)*70 - star_surf.get_width()//2
            self.screen.blit(star_surf, (bx, 280))

        score_surf = self.font_md.render(f"最终分数：{self.score}", True, (200, 210, 230))
        self.screen.blit(score_surf, (SCREEN_WIDTH//2 - score_surf.get_width()//2, 360))

        # 按钮
        for btn, bx, by, bc in [
            ("再来一局", SCREEN_WIDTH//2-130, 430, (60, 160, 90)),
            ("关卡地图", SCREEN_WIDTH//2+10,  430, (60, 100, 160)),
        ]:
            bw, bh = 120, 46
            pygame.draw.rect(self.screen, bc, (bx, by, bw, bh), border_radius=12)
            bs = self.font_sm.render(btn, True, (255, 255, 255))
            self.screen.blit(bs, (bx + bw//2 - bs.get_width()//2, by + bh//2 - bs.get_height()//2))

    # ============================================================= 地图界面 ==
    MAX_LEVELS = 15

    def draw_map(self):
        self.screen.fill(BG_COLOR)
        title = self.font_lg.render("关卡地图", True, (220, 225, 255))
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 30))

        # 树状布局：每行3关，交错连接
        # 定义布局坐标
        positions = self._level_positions()

        # 绘制连接线（树状路径）
        for i in range(1, self.MAX_LEVELS):
            p1 = positions[i-1]
            p2 = positions[i]
            locked = i+1 > self.user_data["unlocked"]
            line_color = (60, 80, 60) if locked else (80, 160, 80)
            # 弯曲路径：先画竖，再画横
            mid_y = (p1[1] + p2[1]) // 2
            pygame.draw.line(self.screen, line_color, p1, (p1[0], mid_y), 3)
            pygame.draw.line(self.screen, line_color, (p1[0], mid_y), (p2[0], mid_y), 3)
            pygame.draw.line(self.screen, line_color, (p2[0], mid_y), p2, 3)

        # 绘制关卡节点
        for i in range(self.MAX_LEVELS):
            lvl = i + 1
            px, py = positions[i]
            unlocked = lvl <= self.user_data["unlocked"]
            stars_got = self.user_data["stars"].get(str(lvl), 0)

            # 节点圆
            radius = 28
            if unlocked:
                pygame.draw.circle(self.screen, (50, 130, 80), (px, py), radius)
                pygame.draw.circle(self.screen, (80, 200, 120), (px, py), radius, 3)
            else:
                pygame.draw.circle(self.screen, (50, 50, 60), (px, py), radius)
                pygame.draw.circle(self.screen, (70, 70, 85), (px, py), radius, 2)

            # 关卡编号
            n_surf = self.font_md.render(str(lvl), True,
                                          (230,240,230) if unlocked else (90,90,100))
            self.screen.blit(n_surf, (px - n_surf.get_width()//2, py - n_surf.get_height()//2))

            # 小星星
            for s in range(3):
                sx = px - 20 + s * 18
                sy = py + radius + 6
                col = (255, 215, 0) if s < stars_got else (50, 50, 60)
                star_s = self.font_sm.render("★", True, col)
                self.screen.blit(star_s, (sx - star_s.get_width()//2, sy))

    def _level_positions(self):
        """生成蛇形/树状的关卡位置列表"""
        positions = []
        cols    = [90, SCREEN_WIDTH//2, SCREEN_WIDTH-90]
        row_h   = 90
        start_y = 110
        for i in range(self.MAX_LEVELS):
            row = i // 3
            col_idx = i % 3
            # 奇数行反向（蛇形）
            if row % 2 == 1:
                col_idx = 2 - col_idx
            positions.append((cols[col_idx], start_y + row * row_h))
        return positions

    def map_hit_level(self, pos):
        """返回点击了哪个关卡（0-based index），未命中返回-1"""
        positions = self._level_positions()
        for i, (px, py) in enumerate(positions):
            if math.hypot(pos[0]-px, pos[1]-py) <= 30:
                return i + 1
        return -1

    # ============================================================= 主循环 ==
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                # 延时执行交换逻辑
                if event.type == pygame.USEREVENT + 1:
                    self.execute_swap()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    pos = event.pos

                    if self.state == "MAP":
                        lvl = self.map_hit_level(pos)
                        if lvl > 0 and lvl <= self.user_data["unlocked"]:
                            self.current_level = lvl
                            self.reset_level_vars()
                            self.state = "PLAYING"

                    elif self.state == "RESULT":
                        # 再来一局
                        if pygame.Rect(SCREEN_WIDTH//2-130, 430, 120, 46).collidepoint(pos):
                            self.reset_level_vars()
                            self.state = "PLAYING"
                        # 关卡地图
                        elif pygame.Rect(SCREEN_WIDTH//2+10, 430, 120, 46).collidepoint(pos):
                            self.state = "MAP"

                    elif self.state == "PLAYING" and not self.busy:
                        c = (pos[0] - OFFSET_X) // TILE_SIZE
                        r = (pos[1] - OFFSET_Y) // TILE_SIZE
                        if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
                            if self.selected is None:
                                self.selected = (r, c)
                            else:
                                r1, c1 = self.selected
                                if abs(r1-r) + abs(c1-c) == 1:
                                    self.selected = None
                                    self.try_swap(r1, c1, r, c)
                                elif (r, c) == (r1, c1):
                                    self.selected = None
                                else:
                                    self.selected = (r, c)

            # 更新动画
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE):
                    self.anims[r][c].update(dt)
            self.update_score_popups(dt)

            # 渲染
            if self.state == "MAP":
                self.draw_map()
            elif self.state in ("PLAYING", "SETTLING"):
                self.draw_playing()
            elif self.state == "RESULT":
                self.draw_result()

            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    Match3Pro().run()