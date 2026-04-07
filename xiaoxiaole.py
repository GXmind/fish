# import pygame
# import random
# import json
# import os
# import math

# # ─────────────────────────────────────────────── 常量 ──
# BASE_W, BASE_H = 480, 780   # 逻辑分辨率
# GRID_SIZE  = 8
# TILE_SIZE  = 50
# GRID_PX    = GRID_SIZE * TILE_SIZE   # 400

# COLORS = [
#     (220,  70,  70),  # 0 红
#     ( 60, 195,  80),  # 1 绿
#     ( 65, 135, 235),  # 2 蓝
#     (240, 210,  50),  # 3 黄
#     (240, 135,  45),  # 4 橙
#     (175,  75, 235),  # 5 紫
# ]
# COLOR_NAMES = ["红", "绿", "蓝", "黄", "橙", "紫"]

# # 特殊方块值编码
# # 0-5    普通
# # 10-15  横消（消整行）
# # 20-25  纵消（消整列）
# # 30-35  炸弹（菱形范围）
# # 40     彩虹（全消某色）
# SPECIAL_NONE    = 0
# SPECIAL_ROW     = 10
# SPECIAL_COL     = 20
# SPECIAL_BOMB    = 30
# SPECIAL_RAINBOW = 40

# # ── 关卡定义 ─────────────────────────────────────────
# # type:"score"  → 达到目标分数
# # type:"clear"  → 消除指定颜色N个方块，color=-1表示任意颜色
# # 三档分数: obj_target(1星) / star2(2星) / star3(3星)
# # 数值设计基线: 20步×平均10格×20分=4000分，连消加成可达6000+
# LEVELS = [
#     # 1-3 教学
#     {"type":"score",  "steps":22, "target":1200, "star2":2200, "star3":3500},
#     {"type":"score",  "steps":22, "target":1500, "star2":2800, "star3":4200},
#     {"type":"clear",  "steps":20, "target":20,   "color":0,    "star2":35,  "star3":52},
#     # 4-6 进阶
#     {"type":"score",  "steps":20, "target":2000, "star2":3800, "star3":5800},
#     {"type":"clear",  "steps":20, "target":25,   "color":1,    "star2":42,  "star3":62},
#     {"type":"clear",  "steps":22, "target":30,   "color":-1,   "star2":55,  "star3":82},
#     # 7-9 中期
#     {"type":"score",  "steps":18, "target":2500, "star2":4500, "star3":7000},
#     {"type":"clear",  "steps":18, "target":28,   "color":2,    "star2":48,  "star3":70},
#     {"type":"score",  "steps":20, "target":3000, "star2":5500, "star3":8500},
#     # 10-12 挑战
#     {"type":"clear",  "steps":18, "target":32,   "color":3,    "star2":55,  "star3":80},
#     {"type":"score",  "steps":16, "target":3200, "star2":5800, "star3":9000},
#     {"type":"clear",  "steps":16, "target":32,   "color":4,    "star2":52,  "star3":76},
#     # 13-15 高难
#     {"type":"score",  "steps":15, "target":3500, "star2":6500, "star3":10000},
#     {"type":"clear",  "steps":15, "target":38,   "color":5,    "star2":62,  "star3":90},
#     {"type":"score",  "steps":14, "target":4000, "star2":7500, "star3":12000},
# ]
# MAX_LEVELS = len(LEVELS)

# # ─────────────────────────────────────────────── 工具 ──
# def lerp(a, b, t):    return a + (b - a) * t
# def ease_out(t):      return 1 - (1 - t) ** 3
# def ease_in_out(t):   return t * t * (3 - 2 * t)
# def clamp(v, lo, hi): return max(lo, min(hi, v))


# def draw_grad_rect(surf, rect, col_top, col_bot, radius=12):
#     x, y, w, h = rect
#     if w <= 0 or h <= 0: return
#     tmp = pygame.Surface((w, h), pygame.SRCALPHA)
#     for i in range(h):
#         t = i / max(1, h - 1)
#         c = tuple(int(lerp(col_top[j], col_bot[j], t)) for j in range(3)) + (255,)
#         pygame.draw.line(tmp, c, (0, i), (w - 1, i))
#     mask = pygame.Surface((w, h), pygame.SRCALPHA)
#     pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=radius)
#     tmp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
#     surf.blit(tmp, (x, y))


# # ═══════════════════════════════════════════════ AnimTile ══
# class AnimTile:
#     def __init__(self):
#         self.ox = self.oy = 0.0
#         self.scale = 1.0
#         self.alpha = 255
#         self.phase = "idle"
#         self.t = self.dur = 0.0
#         self.swap_dx = self.swap_dy = 0.0
#         self.fall_from = 0.0
#         self.pop_particles = []

#     def start_swap(self, dx, dy, dur=0.16):
#         self.phase = "swap"
#         self.swap_dx = dx; self.swap_dy = dy
#         self.t = 0.0; self.dur = dur

#     def start_fall(self, from_oy, dur=0.22):
#         self.phase = "fall"
#         self.fall_from = from_oy; self.oy = from_oy
#         self.t = 0.0; self.dur = dur

#     def start_pop(self, color):
#         self.phase = "pop"; self.t = 0.0; self.dur = 0.28
#         self.pop_particles = []
#         for _ in range(10):
#             a = random.uniform(0, math.tau)
#             s = random.uniform(2.0, 5.0)
#             self.pop_particles.append(
#                 {"vx": math.cos(a)*s, "vy": math.sin(a)*s,
#                  "color": color, "x": 0.0, "y": 0.0})

#     def start_spawn(self, dur=0.18):
#         self.phase = "spawn"; self.scale = 0.0
#         self.t = 0.0; self.dur = dur

#     def update(self, dt):
#         if self.phase == "idle": return False
#         self.t += dt
#         p = min(1.0, self.t / self.dur) if self.dur > 0 else 1.0
#         if self.phase == "swap":
#             e = ease_in_out(p)
#             self.ox = self.swap_dx*(1-e); self.oy = self.swap_dy*(1-e)
#             if p >= 1.0: self.ox = self.oy = 0; self.phase = "idle"; return True
#         elif self.phase == "fall":
#             self.oy = self.fall_from*(1-ease_out(p))
#             if p >= 1.0: self.oy = 0; self.phase = "idle"; return True
#         elif self.phase == "spawn":
#             self.scale = ease_out(p)
#             if p >= 1.0: self.scale = 1.0; self.phase = "idle"; return True
#         elif self.phase == "pop":
#             self.scale = 1.0 - ease_out(p)
#             self.alpha = int(255*(1-p))
#             for pt in self.pop_particles:
#                 pt["x"] += pt["vx"]; pt["y"] += pt["vy"]; pt["vy"] += 0.25
#             if p >= 1.0:
#                 self.phase = "idle"; self.scale = 1.0; self.alpha = 255; return True
#         return False


# # ═══════════════════════════════════════════════ Match3Pro ══
# class Match3Pro:
#     def __init__(self):
#         pygame.init()
#         self.win_w, self.win_h = BASE_W, BASE_H
#         self.screen = pygame.display.set_mode(
#             (self.win_w, self.win_h), pygame.RESIZABLE)
#         pygame.display.set_caption("消消乐 ✦ 进阶版")
#         self.clock = pygame.time.Clock()
#         self.canvas = pygame.Surface((BASE_W, BASE_H))

#         self._init_fonts()
#         self.save_file = "game_save_pro.json"
#         self.user_data = self._load_save()

#         self.state = "MAP"
#         self.current_level = 1
#         self.anims  = [[AnimTile() for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
#         self.popups = []
#         self.settle_stars = 0
#         self._btn_retry = self._btn_map_btn = pygame.Rect(0,0,1,1)
#         self._reset_level()

#     # ─── 字体 ─────────────────────────────────────────────
#     def _init_fonts(self):
#         cn_names = ["SimHei","Microsoft YaHei","PingFang SC",
#                     "Hiragino Sans GB","WenQuanYi Micro Hei","Noto Sans CJK SC"]
#         cn = None
#         for name in cn_names:
#             try:
#                 if pygame.font.SysFont(name, 20): cn = name; break
#             except: pass
#         self.f_sm  = pygame.font.SysFont(cn or "sans", 20)
#         self.f_md  = pygame.font.SysFont(cn or "sans", 26)
#         self.f_lg  = pygame.font.SysFont(cn or "sans", 36, bold=True)
#         self.f_xl  = pygame.font.SysFont("Arial", 52, bold=True)
#         self.f_num = pygame.font.SysFont("Arial", 50, bold=True)

#     # ─── 存档 ─────────────────────────────────────────────
#     def _load_save(self):
#         if os.path.exists(self.save_file):
#             with open(self.save_file) as f: return json.load(f)
#         return {"unlocked": 1, "stars": {}}

#     def _write_save(self, lvl, stars):
#         self.user_data["stars"][str(lvl)] = max(
#             self.user_data["stars"].get(str(lvl), 0), stars)
#         if lvl == self.user_data["unlocked"] and lvl < MAX_LEVELS:
#             self.user_data["unlocked"] += 1
#         with open(self.save_file, "w") as f: json.dump(self.user_data, f)

#     # ─── 关卡初始化 ───────────────────────────────────────
#     def _reset_level(self):
#         self.grid  = [[random.randint(0,5) for _ in range(GRID_SIZE)]
#                        for _ in range(GRID_SIZE)]
#         self.anims = [[AnimTile() for _ in range(GRID_SIZE)]
#                        for _ in range(GRID_SIZE)]
#         self._remove_initial_matches()
#         self.selected = None
#         self.score    = 0
#         self.cleared  = [0]*6    # 各色消除计数
#         self.combo    = 0
#         self.busy     = False
#         self.popups   = []
#         ld = LEVELS[self.current_level-1]
#         self.steps      = ld["steps"]
#         self.obj_type   = ld["type"]
#         self.obj_target = ld["target"]
#         self.obj_color  = ld.get("color", -1)
#         self.star2_thr  = ld["star2"]
#         self.star3_thr  = ld["star3"]

#     def _remove_initial_matches(self):
#         for _ in range(200):
#             m = self._all_matches()
#             if not m: break
#             for r,c in m: self.grid[r][c] = random.randint(0,5)

#     # ─── 坐标换算 ─────────────────────────────────────────
#     def _scale(self):
#         return min(self.win_w/BASE_W, self.win_h/BASE_H)

#     def _win_to_logic(self, wx, wy):
#         s = self._scale()
#         ox = (self.win_w - BASE_W*s)/2
#         oy = (self.win_h - BASE_H*s)/2
#         return (wx-ox)/s, (wy-oy)/s

#     def _grid_offset(self):
#         return (BASE_W - GRID_PX)//2, 190

#     # ─────────────────────── 颜色 / 类型辅助 ──────────────
#     def _bc(self, val):
#         if val < 0 or val >= SPECIAL_RAINBOW: return -1
#         return val % 10

#     def _sp(self, val):
#         if val < 0:                 return -1
#         if val >= SPECIAL_RAINBOW:  return SPECIAL_RAINBOW
#         if val >= SPECIAL_BOMB:     return SPECIAL_BOMB
#         if val >= SPECIAL_COL:      return SPECIAL_COL
#         if val >= SPECIAL_ROW:      return SPECIAL_ROW
#         return SPECIAL_NONE

#     # ─── 匹配检测 ─────────────────────────────────────────
#     def _all_matches(self):
#         m = set()
#         for r in range(GRID_SIZE):
#             for c in range(GRID_SIZE-2):
#                 bc = [self._bc(self.grid[r][c+i]) for i in range(3)]
#                 if bc[0]>=0 and bc[0]==bc[1]==bc[2]:
#                     m.update([(r,c),(r,c+1),(r,c+2)])
#         for r in range(GRID_SIZE-2):
#             for c in range(GRID_SIZE):
#                 bc = [self._bc(self.grid[r+i][c]) for i in range(3)]
#                 if bc[0]>=0 and bc[0]==bc[1]==bc[2]:
#                     m.update([(r,c),(r+1,c),(r+2,c)])
#         return m

#     def _match_lines(self):
#         lines = []
#         def flush(run, d):
#             if len(run) >= 3: lines.append({"cells": run[:], "dir": d})
#         for r in range(GRID_SIZE):
#             run = []
#             for c in range(GRID_SIZE):
#                 bc = self._bc(self.grid[r][c])
#                 if bc < 0: flush(run,"h"); run=[]
#                 elif not run: run=[(r,c)]
#                 elif bc != self._bc(self.grid[run[-1][0]][run[-1][1]]): flush(run,"h"); run=[(r,c)]
#                 else: run.append((r,c))
#             flush(run,"h")
#         for c in range(GRID_SIZE):
#             run = []
#             for r in range(GRID_SIZE):
#                 bc = self._bc(self.grid[r][c])
#                 if bc < 0: flush(run,"v"); run=[]
#                 elif not run: run=[(r,c)]
#                 elif bc != self._bc(self.grid[run[-1][0]][run[-1][1]]): flush(run,"v"); run=[(r,c)]
#                 else: run.append((r,c))
#             flush(run,"v")
#         return lines

#     def _collect_triggers(self, cells):
#         to_del = set(cells)
#         queue  = list(cells)
#         vis    = set()
#         while queue:
#             r,c = queue.pop()
#             if (r,c) in vis: continue
#             vis.add((r,c))
#             val = self.grid[r][c]
#             sp  = self._sp(val)
#             if sp == SPECIAL_ROW:
#                 for cc in range(GRID_SIZE): to_del.add((r,cc)); queue.append((r,cc))
#             elif sp == SPECIAL_COL:
#                 for rr in range(GRID_SIZE): to_del.add((rr,c)); queue.append((rr,c))
#             elif sp == SPECIAL_BOMB:
#                 for dr in range(-2,3):
#                     for dc in range(-2,3):
#                         if abs(dr)+abs(dc) <= 2:
#                             nr,nc = r+dr,c+dc
#                             if 0<=nr<GRID_SIZE and 0<=nc<GRID_SIZE:
#                                 to_del.add((nr,nc)); queue.append((nr,nc))
#             elif sp == SPECIAL_RAINBOW:
#                 cnt = {}
#                 for rr in range(GRID_SIZE):
#                     for cc in range(GRID_SIZE):
#                         b = self._bc(self.grid[rr][cc])
#                         if b>=0: cnt[b]=cnt.get(b,0)+1
#                 if cnt:
#                     tc = max(cnt, key=cnt.get)
#                     for rr in range(GRID_SIZE):
#                         for cc in range(GRID_SIZE):
#                             if self._bc(self.grid[rr][cc]) == tc:
#                                 to_del.add((rr,cc)); queue.append((rr,cc))
#         return to_del

#     def _rainbow_combine(self, r1,c1,r2,c2):
#         v1,v2 = self.grid[r1][c1], self.grid[r2][c2]
#         rr,rc = (r1,c1) if self._sp(v1)==SPECIAL_RAINBOW else (r2,c2)
#         or_,oc = (r2,c2) if (rr,rc)==(r1,c1) else (r1,c1)
#         osp = self._sp(self.grid[or_][oc])
#         if osp in (SPECIAL_ROW,SPECIAL_COL,SPECIAL_BOMB):
#             oval=self.grid[or_][oc]; obc=self._bc(oval)
#             for row in range(GRID_SIZE):
#                 for col in range(GRID_SIZE):
#                     if self._bc(self.grid[row][col])==obc:
#                         self.grid[row][col]=osp+obc
#             cells = {(row,col) for row in range(GRID_SIZE) for col in range(GRID_SIZE)
#                      if self._bc(self.grid[row][col])==obc}
#             to_del = self._collect_triggers(cells)
#         else:
#             to_del = self._collect_triggers({(rr,rc)})
#         to_del.add((r1,c1)); to_del.add((r2,c2))
#         return to_del

#     def _detect_special(self, candidates, lines):
#         new_sp = {}
#         for sr,sc in candidates:
#             sl = [l for l in lines if (sr,sc) in l["cells"]]
#             if not sl: continue
#             bc = -1
#             for l in sl:
#                 for rr,cc in l["cells"]:
#                     bc = self._bc(self.grid[rr][cc])
#                     if bc >= 0: break
#                 if bc >= 0: break
#             if bc < 0: bc = 0
#             hl = [l for l in sl if l["dir"]=="h"]
#             vl = [l for l in sl if l["dir"]=="v"]
#             mh = max((len(l["cells"]) for l in hl), default=0)
#             mv = max((len(l["cells"]) for l in vl), default=0)
#             mn = max(mh,mv)
#             if hl and vl:       new_sp[(sr,sc)] = SPECIAL_BOMB + bc
#             elif mn >= 5:       new_sp[(sr,sc)] = SPECIAL_RAINBOW
#             elif mn == 4:       new_sp[(sr,sc)] = (SPECIAL_ROW if mh==4 else SPECIAL_COL) + bc
#         return new_sp

#     # ─── 消除流程 ─────────────────────────────────────────
#     def _try_swap(self, r1,c1,r2,c2):
#         if self.busy: return
#         dx=(c2-c1)*TILE_SIZE; dy=(r2-r1)*TILE_SIZE
#         self.anims[r1][c1].start_swap(dx,dy)
#         self.anims[r2][c2].start_swap(-dx,-dy)
#         self.busy = True
#         pygame.time.set_timer(pygame.USEREVENT+1, 180, 1)
#         self._pending = (r1,c1,r2,c2)

#     def _execute_swap(self):
#         r1,c1,r2,c2 = self._pending
#         self.grid[r1][c1],self.grid[r2][c2] = self.grid[r2][c2],self.grid[r1][c1]
#         v1,v2 = self.grid[r1][c1],self.grid[r2][c2]
#         sp1,sp2 = self._sp(v1),self._sp(v2)
#         direct=False; to_del=set()

#         if sp1==SPECIAL_RAINBOW and sp2==SPECIAL_RAINBOW:
#             to_del={(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)}; direct=True
#         elif sp1==SPECIAL_RAINBOW or sp2==SPECIAL_RAINBOW:
#             to_del=self._rainbow_combine(r1,c1,r2,c2); direct=True
#         elif sp1!=SPECIAL_NONE and sp2!=SPECIAL_NONE:
#             to_del=self._collect_triggers({(r1,c1),(r2,c2)}); direct=True
#         elif sp1!=SPECIAL_NONE or sp2!=SPECIAL_NONE:
#             pos=(r1,c1) if sp1!=SPECIAL_NONE else (r2,c2)
#             to_del=self._collect_triggers({pos}); direct=True

#         if direct and to_del:
#             self.steps -= 1; self.combo = 1
#             self._add_score(len(to_del)*20, to_del)
#             self._delete(to_del); self._fall_refill(); self._chain()
#         elif self._all_matches():
#             self.steps -= 1; self.combo = 0
#             self._chain(swap_cands=[(r1,c1),(r2,c2)])
#         else:
#             self.grid[r1][c1],self.grid[r2][c2]=self.grid[r2][c2],self.grid[r1][c1]
#             self.anims[r1][c1].start_swap(-((c2-c1)*TILE_SIZE),-((r2-r1)*TILE_SIZE))
#             self.anims[r2][c2].start_swap((c2-c1)*TILE_SIZE,(r2-r1)*TILE_SIZE)
#             self.busy = False

#     def _chain(self, swap_cands=None):
#         while True:
#             lines = self._match_lines()
#             if not lines: break
#             matched = set()
#             for l in lines: matched.update(l["cells"])
#             if not matched: break
#             self.combo += 1
#             new_sp = self._detect_special(swap_cands, lines) if swap_cands else {}
#             to_del = matched - set(new_sp.keys())
#             for r,c in list(matched):
#                 if (r,c) in new_sp: continue
#                 if self._sp(self.grid[r][c]) != SPECIAL_NONE:
#                     to_del.update(self._collect_triggers({(r,c)}))
#             for pos in list(new_sp.keys()):
#                 if pos in to_del: del new_sp[pos]
#             gain = len(to_del)*20*self.combo
#             self._add_score(gain, to_del)
#             self._delete(to_del)
#             if new_sp:
#                 for (r,c),val in new_sp.items():
#                     self.grid[r][c]=val
#                     self.anims[r][c].start_spawn(0.35)
#                 self._frames(30)
#             self._fall_refill()
#             swap_cands = None
#         # ─ 结束判断 ─
#         if self._is_three_star() and self.steps > 0:
#             self._bonus_phase()
#         elif self.steps <= 0 or self._is_three_star():
#             self._finish()
#         else:
#             self.busy = False

#     def _is_three_star(self):
#         v = self._progress_val()
#         return v >= self.star3_thr

#     def _progress_val(self):
#         if self.obj_type == "score": return self.score
#         return self.cleared[self.obj_color] if self.obj_color>=0 else sum(self.cleared)

#     def _calc_stars(self):
#         v = self._progress_val()
#         if v >= self.star3_thr: return 3
#         if v >= self.star2_thr: return 2
#         if v >= self.obj_target: return 1
#         return 0

#     def _add_score(self, gain, cells):
#         self.score += gain
#         # 统计消除颜色
#         for r,c in cells:
#             val = self.grid[r][c]
#             if val < 0: continue
#             bc = self._bc(val)
#             if 0<=bc<=5: self.cleared[bc] += 1
#         if gain > 0 and cells:
#             ox,oy = self._grid_offset()
#             ra = sum(r for r,c in cells)/len(cells)
#             ca = sum(c for r,c in cells)/len(cells)
#             col = (255,235,60) if self.combo<=1 else (255,160,40) if self.combo<=3 else (255,80,80)
#             txt = f"+{gain}" if self.combo<=1 else f"x{self.combo}  +{gain}"
#             self.popups.append({
#                 "text": txt,
#                 "x": ox+ca*TILE_SIZE+TILE_SIZE//2,
#                 "y": oy+ra*TILE_SIZE,
#                 "life": 1.2, "color": col,
#             })

#     def _delete(self, cells):
#         for r,c in cells:
#             val = self.grid[r][c]
#             if val >= 0:
#                 bc = self._bc(val)
#                 col = COLORS[bc] if bc>=0 else (220,220,220)
#                 self.anims[r][c].start_pop(col)
#             self.grid[r][c] = -1
#         self._frames(16)

#     def _fall_refill(self):
#         self._frames(5)
#         for c in range(GRID_SIZE):
#             col_vals = [(r,self.grid[r][c]) for r in range(GRID_SIZE) if self.grid[r][c]!=-1]
#             en = GRID_SIZE-len(col_vals)
#             for r in range(GRID_SIZE): self.grid[r][c]=-1
#             for i,(orig_r,val) in enumerate(reversed(col_vals)):
#                 dr2=GRID_SIZE-1-i; self.grid[dr2][c]=val
#                 fall=dr2-orig_r
#                 if fall>0: self.anims[dr2][c].start_fall(-fall*TILE_SIZE)
#             for i in range(en):
#                 self.grid[i][c]=random.randint(0,5)
#                 self.anims[i][c].start_fall(-(en-i)*TILE_SIZE)
#         self._frames(20)

#     def _bonus_phase(self):
#         self.state = "SETTLING"
#         rem=self.steps; self.steps=0
#         avail=[(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)
#                if self.grid[r][c]>=0 and self._sp(self.grid[r][c])==SPECIAL_NONE]
#         random.shuffle(avail)
#         bpos=[]
#         for _ in range(rem):
#             if not avail:
#                 avail=[(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)
#                        if self.grid[r][c]>=0 and self._sp(self.grid[r][c])==SPECIAL_NONE]
#                 random.shuffle(avail)
#             if not avail: break
#             br,bc2=avail.pop(0)
#             bc=self._bc(self.grid[br][bc2])
#             if bc<0: bc=0
#             spt=random.choice([SPECIAL_ROW,SPECIAL_COL,SPECIAL_BOMB,SPECIAL_BOMB,SPECIAL_RAINBOW])
#             self.grid[br][bc2]=SPECIAL_RAINBOW if spt==SPECIAL_RAINBOW else spt+bc
#             self.anims[br][bc2].start_spawn(0.3)
#             bpos.append((br,bc2))
#             self._frames(14)
#         self._frames(45)
#         if bpos:
#             ad=self._collect_triggers(set(bpos))
#             self._add_score(len(ad)*20, ad)
#             self._delete(ad); self._fall_refill(); self._silent_chain()
#         self._finish()

#     def _silent_chain(self):
#         while True:
#             m=self._all_matches()
#             if not m: break
#             d=self._collect_triggers(m)
#             self._add_score(len(d)*20,d)
#             self._delete(d); self._fall_refill()

#     def _finish(self):
#         stars=self._calc_stars()
#         self.settle_stars=stars
#         self._write_save(self.current_level, stars)
#         self._frames(50)
#         self.state="RESULT"; self.busy=False

#     # ─── 帧驱动 ───────────────────────────────────────────
#     def _frames(self, n):
#         for _ in range(n):
#             dt=self.clock.tick(60)/1000.0
#             for r in range(GRID_SIZE):
#                 for c in range(GRID_SIZE): self.anims[r][c].update(dt)
#             self._upd_popups(dt)
#             self._render()
#             for ev in pygame.event.get():
#                 if ev.type==pygame.QUIT: pygame.quit(); raise SystemExit
#                 if ev.type==pygame.VIDEORESIZE: self._resize(ev.w,ev.h)

#     def _resize(self, w, h):
#         self.win_w=max(240,w); self.win_h=max(390,h)
#         self.screen=pygame.display.set_mode((self.win_w,self.win_h),pygame.RESIZABLE)

#     def _upd_popups(self, dt):
#         for p in self.popups: p["life"]-=dt; p["y"]-=38*dt
#         self.popups=[p for p in self.popups if p["life"]>0]

#     # ═══════════════════════════════════ 渲染总入口 ════════
#     def _render(self):
#         s = self._scale()
#         if self.state=="MAP":                       self._draw_map()
#         elif self.state in("PLAYING","SETTLING"):   self._draw_playing()
#         elif self.state=="RESULT":                  self._draw_result()

#         if abs(s-1.0) < 0.01:
#             self.screen.blit(self.canvas,(0,0))
#         else:
#             sw,sh = int(BASE_W*s),int(BASE_H*s)
#             scaled=pygame.transform.smoothscale(self.canvas,(sw,sh))
#             self.screen.fill((10,10,14))
#             self.screen.blit(scaled,((self.win_w-sw)//2,(self.win_h-sh)//2))
#         pygame.display.flip()

#     # ─── 方块绘制 ─────────────────────────────────────────
#     def _draw_tile(self, surf, r, c, val, x, y):
#         if val < 0: return
#         an = self.anims[r][c]
#         bc = self._bc(val)
#         sp = self._sp(val)
#         col = COLORS[bc] if bc>=0 else (200,200,210)

#         sc = max(0.0, an.scale)
#         tw = int((TILE_SIZE-6)*sc); th = int((TILE_SIZE-6)*sc)
#         if tw<2 or th<2: return
#         bx = int(x+an.ox + 3+(TILE_SIZE-6-tw)/2)
#         by = int(y+an.oy + 3+(TILE_SIZE-6-th)/2)

#         ts = pygame.Surface((tw,th), pygame.SRCALPHA)
#         # 底部暗影
#         dc = tuple(max(0,col[i]-55) for i in range(3))
#         pygame.draw.rect(ts, dc+(200,), (2,4,tw-2,th-2), border_radius=10)
#         # 渐变主体
#         lc = tuple(min(255,col[i]+35) for i in range(3))
#         draw_grad_rect(ts, (0,0,tw,th-2), lc, col, radius=10)
#         # 高光
#         hs=pygame.Surface((max(1,tw-12),max(1,th//3)),pygame.SRCALPHA)
#         hs.fill((255,255,255,55))
#         ts.blit(hs,(6,4))

#         if an.alpha < 255: ts.set_alpha(an.alpha)

#         cx,cy = tw//2,th//2
#         W = (255,255,255,235)
#         if sp==SPECIAL_ROW:
#             pygame.draw.line(ts,W,(8,cy),(tw-8,cy),3)
#             pygame.draw.polygon(ts,W,[(4,cy),(12,cy-5),(12,cy+5)])
#             pygame.draw.polygon(ts,W,[(tw-4,cy),(tw-12,cy-5),(tw-12,cy+5)])
#         elif sp==SPECIAL_COL:
#             pygame.draw.line(ts,W,(cx,8),(cx,th-8),3)
#             pygame.draw.polygon(ts,W,[(cx,4),(cx-5,12),(cx+5,12)])
#             pygame.draw.polygon(ts,W,[(cx,th-4),(cx-5,th-12),(cx+5,th-12)])
#         elif sp==SPECIAL_BOMB:
#             d=min(tw,th)//2-4
#             pygame.draw.polygon(ts,W,[(cx,cy-d),(cx+d,cy),(cx,cy+d),(cx-d,cy)],2)
#             pygame.draw.circle(ts,W,(cx,cy),4,0)
#         elif sp==SPECIAL_RAINBOW:
#             for i in range(6):
#                 rad=math.radians(i*60)
#                 px2=cx+int(math.cos(rad)*11); py2=cy+int(math.sin(rad)*11)
#                 pygame.draw.circle(ts,COLORS[i]+(230,),(px2,py2),4)
#             pygame.draw.circle(ts,(255,255,255,220),(cx,cy),5)

#         surf.blit(ts,(bx,by))

#         # 爆炸粒子
#         if an.phase=="pop":
#             frac=an.t/max(an.dur,0.001)
#             for pt in an.pop_particles:
#                 a2=max(0,int(255*(1-frac)))
#                 px2=int(x+TILE_SIZE//2+pt["x"]*3)
#                 py2=int(y+TILE_SIZE//2+pt["y"]*3)
#                 ps=pygame.Surface((7,7),pygame.SRCALPHA)
#                 pygame.draw.circle(ps,pt["color"]+(a2,),(3,3),3)
#                 surf.blit(ps,(px2-3,py2-3))

#     # ─── 进度条 ───────────────────────────────────────────
#     def _draw_progress(self, surf, x, y, w, h=13):
#         prog = clamp(self._progress_val()/max(1,self.star3_thr), 0, 1)
#         pygame.draw.rect(surf,(38,40,58),(x,y,w,h),border_radius=h//2)
#         fw=int(w*prog)
#         if fw>0:
#             for i in range(fw):
#                 t=i/max(1,w-1)
#                 if t<0.5:  rc=int(lerp(80,255,t*2)); gc=int(lerp(200,215,t*2)); bc2=50
#                 else:      rc=255; gc=int(lerp(215,120,(t-0.5)*2)); bc2=40
#                 pygame.draw.line(surf,(rc,gc,bc2),(x+i,y+2),(x+i,y+h-2))
#         stars_got=self._calc_stars()
#         for sn in range(1,4):
#             thr=[self.obj_target,self.star2_thr,self.star3_thr][sn-1]
#             px2=x+int(w*thr/max(1,self.star3_thr))
#             px2=min(px2,x+w)
#             pygame.draw.line(surf,(15,15,25),(px2,y),(px2,y+h),2)
#             sc2=(255,210,0) if stars_got>=sn else (65,65,82)
#             ss=self.f_sm.render("★",True,sc2)
#             surf.blit(ss,(px2-ss.get_width()//2,y-ss.get_height()-1))

#     # ─── 游戏界面 ─────────────────────────────────────────
#     def _draw_playing(self):
#         cv=self.canvas
#         cv.fill((18,18,28))
#         # 顶部信息板
#         pygame.draw.rect(cv,(22,24,40),(0,0,BASE_W,182))
#         pygame.draw.line(cv,(48,52,78),(0,182),(BASE_W,182),2)

#         # 关卡
#         lvl_s=self.f_sm.render(f"第 {self.current_level} 关",True,(115,122,160))
#         cv.blit(lvl_s,(BASE_W//2-lvl_s.get_width()//2,6))

#         # 步数大字
#         sc2=(255,255,255) if self.steps>5 else (255,120,80)
#         ns=self.f_num.render(str(self.steps),True,sc2)
#         cv.blit(ns,(BASE_W//2-ns.get_width()//2,22))
#         sl=self.f_sm.render("步",True,(100,108,140))
#         cv.blit(sl,(BASE_W//2-ns.get_width()//2-sl.get_width()-4,42))

#         # 目标说明
#         if self.obj_type=="score":
#             obj_s=self.f_sm.render(f"目标分数  {self.score:,} / {self.obj_target:,}",True,(175,185,215))
#         else:
#             cn=COLOR_NAMES[self.obj_color] if self.obj_color>=0 else "任意"
#             v=self.cleared[self.obj_color] if self.obj_color>=0 else sum(self.cleared)
#             obj_s=self.f_sm.render(f"消除{cn}色  {v} / {self.obj_target}",True,(175,185,215))
#             # 颜色指示方块
#             if self.obj_color>=0:
#                 ic=pygame.Surface((14,14),pygame.SRCALPHA)
#                 pygame.draw.rect(ic,COLORS[self.obj_color],(0,0,14,14),border_radius=4)
#                 cv.blit(ic,(BASE_W//2-obj_s.get_width()//2-18,88+3))
#         cv.blit(obj_s,(BASE_W//2-obj_s.get_width()//2,88))

#         # 进度条
#         self._draw_progress(cv,28,116,BASE_W-56,14)

#         # 分数（右侧小字）
#         if self.obj_type=="clear":
#             sc_s=self.f_sm.render(f"分数 {self.score:,}",True,(100,108,140))
#             cv.blit(sc_s,(BASE_W-sc_s.get_width()-10,88))

#         # ── 棋盘 ──
#         ox,oy=self._grid_offset()
#         board=pygame.Rect(ox-5,oy-5,GRID_PX+10,GRID_PX+10)
#         pygame.draw.rect(cv,(26,28,44),board,border_radius=12)
#         pygame.draw.rect(cv,(48,54,80),board,2,border_radius=12)

#         for r in range(GRID_SIZE):
#             for c in range(GRID_SIZE):
#                 shade=(30,32,46) if (r+c)%2==0 else (34,37,54)
#                 pygame.draw.rect(cv,shade,(ox+c*TILE_SIZE,oy+r*TILE_SIZE,TILE_SIZE,TILE_SIZE))

#         for r in range(GRID_SIZE):
#             for c in range(GRID_SIZE):
#                 self._draw_tile(cv,r,c,self.grid[r][c],ox+c*TILE_SIZE,oy+r*TILE_SIZE)

#         # 选中高亮
#         if self.selected:
#             sr,sc3=self.selected
#             sx=ox+sc3*TILE_SIZE; sy=oy+sr*TILE_SIZE
#             gl=pygame.Surface((TILE_SIZE+10,TILE_SIZE+10),pygame.SRCALPHA)
#             pygame.draw.rect(gl,(255,255,255,28),(0,0,TILE_SIZE+10,TILE_SIZE+10),border_radius=14)
#             cv.blit(gl,(sx-5,sy-5))
#             pygame.draw.rect(cv,(255,255,255),(sx,sy,TILE_SIZE,TILE_SIZE),3,12)

#         # 浮动弹窗
#         for p in self.popups:
#             a=min(255,int(255*p["life"]/1.2))
#             ps=self.f_md.render(p["text"],True,p["color"])
#             ps.set_alpha(a)
#             cv.blit(ps,(int(p["x"])-ps.get_width()//2,int(p["y"])))

#         if self.state=="SETTLING":
#             bar=pygame.Surface((240,38),pygame.SRCALPHA)
#             draw_grad_rect(bar,(0,0,240,38),(40,38,64),(28,26,48),radius=19)
#             cv.blit(bar,(BASE_W//2-120,BASE_H-56))
#             tt=self.f_sm.render("✨ 步数奖励结算中…",True,(255,215,0))
#             cv.blit(tt,(BASE_W//2-tt.get_width()//2,BASE_H-47))

#     # ─── 结果界面 ─────────────────────────────────────────
#     def _draw_result(self):
#         self._draw_playing()
#         cv=self.canvas
#         ov=pygame.Surface((BASE_W,BASE_H),pygame.SRCALPHA)
#         ov.fill((6,6,16,210)); cv.blit(ov,(0,0))

#         cw,ch=BASE_W-70,320; cx2=35; cy2=188
#         card=pygame.Surface((cw,ch),pygame.SRCALPHA)
#         draw_grad_rect(card,(0,0,cw,ch),(38,42,66),(24,26,46),radius=22)
#         pygame.draw.rect(card,(72,84,128,170),(0,0,cw,ch),2,border_radius=22)
#         cv.blit(card,(cx2,cy2))

#         passed=self._calc_stars()>0
#         ts=self.f_lg.render("关卡完成！" if passed else "本关未通过",True,
#                              (90,250,155) if passed else (255,100,75))
#         cv.blit(ts,(BASE_W//2-ts.get_width()//2,cy2+16))

#         # 星星
#         for i in range(3):
#             filled=i<self.settle_stars
#             sc_col=(255,215,0) if filled else (52,55,76)
#             ss=self.f_xl.render("★",True,sc_col)
#             bx=BASE_W//2+(i-1)*74-ss.get_width()//2
#             if filled:
#                 gl=pygame.Surface((ss.get_width()+18,ss.get_height()+12),pygame.SRCALPHA)
#                 gl.fill((255,215,0,32)); cv.blit(gl,(bx-9,cy2+70))
#             cv.blit(ss,(bx,cy2+72))

#         # 数据行
#         if self.obj_type=="score":
#             lines2=[f"分数  {self.score:,}  /  目标 {self.obj_target:,}"]
#         else:
#             cn=COLOR_NAMES[self.obj_color] if self.obj_color>=0 else "任意"
#             v=self.cleared[self.obj_color] if self.obj_color>=0 else sum(self.cleared)
#             lines2=[f"消除{cn}色  {v} 个  /  目标 {self.obj_target}",
#                     f"总分  {self.score:,}"]
#         for i,ln in enumerate(lines2):
#             ls=self.f_sm.render(ln,True,(175,185,218))
#             cv.blit(ls,(BASE_W//2-ls.get_width()//2,cy2+152+i*26))

#         # 按钮
#         bw2=(cw-30)//2; bh2=48
#         btns=[("再来一局",cx2+8,cy2+ch-bh2-14,(50,140,78)),
#               ("关卡地图",cx2+bw2+22,cy2+ch-bh2-14,(45,92,152))]
#         self._btn_retry=pygame.Rect(cx2+8,cy2+ch-bh2-14,bw2,bh2)
#         self._btn_map_btn=pygame.Rect(cx2+bw2+22,cy2+ch-bh2-14,bw2,bh2)
#         for txt,bx,by,bc in btns:
#             lc2=tuple(min(255,bc[i]+30) for i in range(3))
#             draw_grad_rect(cv,(bx,by,bw2,bh2),lc2,bc,radius=13)
#             bs=self.f_md.render(txt,True,(240,246,255))
#             cv.blit(bs,(bx+bw2//2-bs.get_width()//2,by+bh2//2-bs.get_height()//2))

#     # ─── 地图界面 ─────────────────────────────────────────
#     def _draw_map(self):
#         cv=self.canvas
#         cv.fill((12,12,20))
#         title=self.f_lg.render("关  卡  地  图",True,(205,215,255))
#         cv.blit(title,(BASE_W//2-title.get_width()//2,16))

#         pos=self._map_pos()
#         # 路径
#         for i in range(1,MAX_LEVELS):
#             p1=pos[i-1]; p2=pos[i]
#             unlocked=i<self.user_data["unlocked"]
#             lc=(55,138,66) if unlocked else (42,44,58)
#             my=(p1[1]+p2[1])//2
#             pygame.draw.line(cv,lc,p1,(p1[0],my),3)
#             pygame.draw.line(cv,lc,(p1[0],my),(p2[0],my),3)
#             pygame.draw.line(cv,lc,(p2[0],my),p2,3)

#         # 节点
#         for i in range(MAX_LEVELS):
#             lvl=i+1; px,py=pos[i]
#             unlocked=lvl<=self.user_data["unlocked"]
#             sg=self.user_data["stars"].get(str(lvl),0)
#             ld=LEVELS[i]; R=26

#             if unlocked:
#                 if ld["type"]=="clear":
#                     cc=ld.get("color",-1)
#                     nc=COLORS[cc] if cc>=0 else (145,110,215)
#                     base_c=tuple(max(25,nc[i2]-65) for i2 in range(3))
#                     ring_c=nc
#                 else:
#                     base_c=(38,96,62); ring_c=(65,180,105)
#                 if sg==3:
#                     gl=pygame.Surface((R*2+18,R*2+18),pygame.SRCALPHA)
#                     pygame.draw.circle(gl,(255,215,0,38),(R+9,R+9),R+9)
#                     cv.blit(gl,(px-R-9,py-R-9))
#                 pygame.draw.circle(cv,base_c,(px,py),R)
#                 pygame.draw.circle(cv,ring_c,(px,py),R,3)
#                 ns=self.f_md.render(str(lvl),True,(225,238,225))
#             else:
#                 pygame.draw.circle(cv,(40,42,56),(px,py),R)
#                 pygame.draw.circle(cv,(60,62,80),(px,py),R,2)
#                 pygame.draw.line(cv,(70,72,90),(px-7,py-3),(px+7,py-3),3)
#                 pygame.draw.rect(cv,(70,72,90),(px-8,py-3,16,10),border_radius=3)
#                 ns=self.f_md.render(str(lvl),True,(75,78,95))
#             cv.blit(ns,(px-ns.get_width()//2,py-ns.get_height()//2))

#             # 类型图标（小字）
#             if unlocked:
#                 icon="★" if ld["type"]=="score" else "◈"
#                 ic=self.f_sm.render(icon,True,(185,200,185))
#                 cv.blit(ic,(px-ic.get_width()//2,py-R-ic.get_height()-2))

#             # 星星
#             for s in range(3):
#                 sx=px-18+s*17; sy=py+R+5
#                 sc_col=(255,210,0) if s<sg else (46,48,62)
#                 ss=self.f_sm.render("★",True,sc_col)
#                 cv.blit(ss,(sx-ss.get_width()//2,sy))

#     def _map_pos(self):
#         cols=[68,BASE_W//2,BASE_W-68]
#         row_h=88; sy=86; pos=[]
#         for i in range(MAX_LEVELS):
#             row=i//3; ci=i%3
#             if row%2==1: ci=2-ci
#             pos.append((cols[ci],sy+row*row_h))
#         return pos

#     def _map_hit(self, lx, ly):
#         for i,(px,py) in enumerate(self._map_pos()):
#             if math.hypot(lx-px,ly-py)<=32: return i+1
#         return -1

#     # ═══════════════════════════════════ 主循环 ═══════════
#     def run(self):
#         running=True
#         while running:
#             dt=self.clock.tick(60)/1000.0
#             for ev in pygame.event.get():
#                 if ev.type==pygame.QUIT: running=False
#                 elif ev.type==pygame.VIDEORESIZE: self._resize(ev.w,ev.h)
#                 elif ev.type==pygame.USEREVENT+1: self._execute_swap()
#                 elif ev.type==pygame.MOUSEBUTTONDOWN:
#                     lx,ly=self._win_to_logic(*ev.pos)
#                     if self.state=="MAP":
#                         lvl=self._map_hit(lx,ly)
#                         if lvl>0 and lvl<=self.user_data["unlocked"]:
#                             self.current_level=lvl; self._reset_level(); self.state="PLAYING"
#                     elif self.state=="RESULT":
#                         if self._btn_retry.collidepoint(lx,ly):
#                             self._reset_level(); self.state="PLAYING"
#                         elif self._btn_map_btn.collidepoint(lx,ly):
#                             self.state="MAP"
#                     elif self.state=="PLAYING" and not self.busy:
#                         ox,oy=self._grid_offset()
#                         c=int((lx-ox)//TILE_SIZE); r=int((ly-oy)//TILE_SIZE)
#                         if 0<=r<GRID_SIZE and 0<=c<GRID_SIZE:
#                             if self.selected is None: self.selected=(r,c)
#                             else:
#                                 r1,c1=self.selected
#                                 if abs(r1-r)+abs(c1-c)==1:
#                                     self.selected=None; self._try_swap(r1,c1,r,c)
#                                 elif (r,c)==(r1,c1): self.selected=None
#                                 else: self.selected=(r,c)

#             for r in range(GRID_SIZE):
#                 for c in range(GRID_SIZE): self.anims[r][c].update(dt)
#             self._upd_popups(dt)
#             self._render()

#         pygame.quit()


# if __name__ == "__main__":
#     Match3Pro().run()

import pygame
import random
import json
import os
import math

# ─────────────────────────────────────────────── 常量 ──
BASE_W, BASE_H = 480, 780   # 逻辑分辨率
GRID_SIZE  = 8
TILE_SIZE  = 50
GRID_PX    = GRID_SIZE * TILE_SIZE   # 400

COLORS = [
    (220,  70,  70),  # 0 红
    ( 60, 195,  80),  # 1 绿
    ( 65, 135, 235),  # 2 蓝
    (240, 210,  50),  # 3 黄
    (240, 135,  45),  # 4 橙
    (175,  75, 235),  # 5 紫
]
COLOR_NAMES = ["红", "绿", "蓝", "黄", "橙", "紫"]

# 特殊方块值编码
# 0-5    普通
# 10-15  横消（消整行）
# 20-25  纵消（消整列）
# 30-35  炸弹（菱形范围）
# 40     彩虹（全消某色）
SPECIAL_NONE    = 0
SPECIAL_ROW     = 10
SPECIAL_COL     = 20
SPECIAL_BOMB    = 30
SPECIAL_RAINBOW = 40

# ── 关卡定义 ─────────────────────────────────────────
LEVELS = [
    # 1-3 教学
    {"type":"score",  "steps":22, "target":1200, "star2":2200, "star3":3500},
    {"type":"score",  "steps":22, "target":1500, "star2":2800, "star3":4200},
    {"type":"clear",  "steps":20, "target":20,   "color":0,    "star2":35,  "star3":52},
    # 4-6 进阶
    {"type":"score",  "steps":20, "target":2000, "star2":3800, "star3":5800},
    {"type":"clear",  "steps":20, "target":25,   "color":1,    "star2":42,  "star3":62},
    {"type":"clear",  "steps":22, "target":30,   "color":-1,   "star2":55,  "star3":82},
    # 7-9 中期
    {"type":"score",  "steps":18, "target":2500, "star2":4500, "star3":7000},
    {"type":"clear",  "steps":18, "target":28,   "color":2,    "star2":48,  "star3":70},
    {"type":"score",  "steps":20, "target":3000, "star2":5500, "star3":8500},
    # 10-12 挑战
    {"type":"clear",  "steps":18, "target":32,   "color":3,    "star2":55,  "star3":80},
    {"type":"score",  "steps":16, "target":3200, "star2":5800, "star3":9000},
    {"type":"clear",  "steps":16, "target":32,   "color":4,    "star2":52,  "star3":76},
    # 13-15 高难
    {"type":"score",  "steps":15, "target":3500, "star2":6500, "star3":10000},
    {"type":"clear",  "steps":15, "target":38,   "color":5,    "star2":62,  "star3":90},
    {"type":"score",  "steps":14, "target":4000, "star2":7500, "star3":12000},
]
MAX_LEVELS = len(LEVELS)

# ── 动物素材名称（与 COLORS 一一对应） ──────────────────
ANIMAL_NAMES = ["cat", "dog", "rabbit", "bear", "bird", "fox"]

# ── 素材目录（相对于本脚本） ─────────────────────────────
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# ─────────────────────────────────────────────── 工具 ──
def lerp(a, b, t):    return a + (b - a) * t
def ease_out(t):      return 1 - (1 - t) ** 3
def ease_in_out(t):   return t * t * (3 - 2 * t)
def clamp(v, lo, hi): return max(lo, min(hi, v))


def draw_grad_rect(surf, rect, col_top, col_bot, radius=12):
    x, y, w, h = rect
    if w <= 0 or h <= 0: return
    tmp = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(h):
        t = i / max(1, h - 1)
        c = tuple(int(lerp(col_top[j], col_bot[j], t)) for j in range(3)) + (255,)
        pygame.draw.line(tmp, c, (0, i), (w - 1, i))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=radius)
    tmp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(tmp, (x, y))


# ═══════════════════════════════════════ 素材加载器 ══════
class AssetLoader:
    """
    负责加载并缓存所有动物图片和特殊道具叠加层。
    若素材文件不存在，自动调用 gen_assets.py 生成。
    """
    def __init__(self):
        self.animal_imgs   = {}   # {idx: pygame.Surface}  原始 48×48
        self.special_imgs  = {}   # {"row"/"col"/"bomb"/"rainbow": pygame.Surface}
        self._tile_cache   = {}   # {(idx, sp, tw, th): pygame.Surface}
        self._loaded = False

    def ensure_assets(self):
        """若 assets/ 目录缺少文件则自动生成"""
        needed = [f"{n}.png" for n in ANIMAL_NAMES] + [
            "special_row.png","special_col.png",
            "special_bomb.png","special_rainbow.png",
        ]
        missing = any(
            not os.path.exists(os.path.join(ASSETS_DIR, f))
            for f in needed
        )
        if missing:
            gen_script = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "gen_assets.py")
            if os.path.exists(gen_script):
                import subprocess, sys
                subprocess.run([sys.executable, gen_script], check=True)
            else:
                print("[警告] 找不到 gen_assets.py，素材可能缺失")

    def load(self):
        if self._loaded:
            return
        self.ensure_assets()
        for idx, name in enumerate(ANIMAL_NAMES):
            path = os.path.join(ASSETS_DIR, f"{name}.png")
            if os.path.exists(path):
                self.animal_imgs[idx] = pygame.image.load(path).convert_alpha()
            else:
                # 降级：纯色圆
                surf = pygame.Surface((48, 48), pygame.SRCALPHA)
                pygame.draw.circle(surf, COLORS[idx] + (200,), (24, 24), 22)
                self.animal_imgs[idx] = surf

        sp_map = {
            "row":     "special_row.png",
            "col":     "special_col.png",
            "bomb":    "special_bomb.png",
            "rainbow": "special_rainbow.png",
        }
        for key, fname in sp_map.items():
            path = os.path.join(ASSETS_DIR, fname)
            if os.path.exists(path):
                self.special_imgs[key] = pygame.image.load(path).convert_alpha()

        self._loaded = True

    def get_tile(self, animal_idx, sp_key, tw, th):
        """
        返回指定尺寸的方块 Surface（animal + 特殊叠加，已缩放，带缓存）。
        sp_key: None | "row" | "col" | "bomb" | "rainbow"
        """
        cache_key = (animal_idx, sp_key, tw, th)
        if cache_key in self._tile_cache:
            return self._tile_cache[cache_key]

        surf = pygame.Surface((tw, th), pygame.SRCALPHA)

        # 底部阴影
        col = COLORS[animal_idx]
        dc  = tuple(max(0, col[i] - 55) for i in range(3))
        pygame.draw.rect(surf, dc + (160,), (2, 4, tw - 2, th - 2), border_radius=10)

        # 渐变背景圆角矩形
        lc = tuple(min(255, col[i] + 35) for i in range(3))
        draw_grad_rect(surf, (0, 0, tw, th - 2), lc, col, radius=10)

        # 高光
        hs = pygame.Surface((max(1, tw - 12), max(1, th // 3)), pygame.SRCALPHA)
        hs.fill((255, 255, 255, 55))
        surf.blit(hs, (6, 4))

        # 动物图
        if animal_idx in self.animal_imgs:
            animal_raw = self.animal_imgs[animal_idx]
            animal_scaled = pygame.transform.smoothscale(animal_raw, (tw - 4, th - 4))
            surf.blit(animal_scaled, (2, 2))

        # 特殊道具叠加（静态图层，不含实时动画）
        if sp_key and sp_key in self.special_imgs and sp_key != "bomb":
            ov_raw = self.special_imgs[sp_key]
            ov = pygame.transform.smoothscale(ov_raw, (tw, th))
            surf.blit(ov, (0, 0))

        self._tile_cache[cache_key] = surf
        return surf


# 全局素材加载器（在 pygame.init() 之后调用 .load()）
_assets = AssetLoader()


# ═══════════════════════════════════ 彩虹粒子系统 ══════════
class RainbowParticle:
    """围绕彩虹方块旋转的彩色粒子"""
    RAINBOW_COLORS = [
        (255, 80,  80),  (255, 180, 30), (255, 240, 40),
        (60,  220, 60),  (50,  160, 255),(160, 80,  255),
    ]

    def __init__(self, cx, cy, index, total):
        self.cx    = cx
        self.cy    = cy
        self.index = index
        self.total = total
        self.color = self.RAINBOW_COLORS[index % len(self.RAINBOW_COLORS)]
        self.phase = random.uniform(0, math.tau)   # 初始相位偏移
        self.radius = random.uniform(14, 20)       # 轨道半径
        self.size   = random.randint(2, 4)
        self.speed  = random.uniform(1.8, 2.8)     # 角速度 (rad/s)

    def update(self, dt):
        self.phase += self.speed * dt

    def draw(self, surf, tile_x, tile_y, alpha=255):
        """tile_x/tile_y 是方块左上角坐标"""
        cx = tile_x + self.cx
        cy = tile_y + self.cy
        px = int(cx + math.cos(self.phase + self.index * math.tau / self.total) * self.radius)
        py = int(cy + math.sin(self.phase + self.index * math.tau / self.total) * self.radius * 0.7)
        ps = pygame.Surface((self.size * 2 + 2, self.size * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(ps, self.color + (alpha,), (self.size + 1, self.size + 1), self.size)
        surf.blit(ps, (px - self.size - 1, py - self.size - 1))


class SpecialAnimManager:
    """
    管理棋盘上所有特殊方块的持续动画状态。
    每帧调用 update(dt)，渲染时调用 get_anim_state(r, c)。
    """
    def __init__(self):
        self._time    = {}   # (r,c) -> float 累计时间
        self._particles = {} # (r,c) -> list[RainbowParticle]

    def reset(self):
        self._time.clear()
        self._particles.clear()

    def update(self, dt, grid, sp_fn):
        """
        grid: 当前棋盘值
        sp_fn: 判断特殊类型的函数
        """
        active = set()
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                sp = sp_fn(grid[r][c])
                if sp in (SPECIAL_ROW, SPECIAL_COL, SPECIAL_BOMB, SPECIAL_RAINBOW):
                    active.add((r, c))
                    self._time[(r, c)] = self._time.get((r, c), 0.0) + dt
                    # 为彩虹方块维护粒子
                    if sp == SPECIAL_RAINBOW:
                        if (r, c) not in self._particles:
                            cx = TILE_SIZE // 2
                            cy = TILE_SIZE // 2
                            n  = 6
                            self._particles[(r, c)] = [
                                RainbowParticle(cx, cy, i, n)
                                for i in range(n)
                            ]
                        for p in self._particles[(r, c)]:
                            p.update(dt)
        # 清理不再活跃的方块
        for key in list(self._time.keys()):
            if key not in active:
                del self._time[key]
        for key in list(self._particles.keys()):
            if key not in active:
                del self._particles[key]

    def get_shake(self, r, c, sp):
        """
        返回 (ox, oy) 当前帧的抖动偏移（像素）。
        横消 → 水平轻微摇晃；纵消 → 垂直轻微摇晃。
        """
        t = self._time.get((r, c), 0.0)
        if sp == SPECIAL_ROW:
            ox = math.sin(t * 6.0) * 1.8
            return ox, 0.0
        elif sp == SPECIAL_COL:
            oy = math.sin(t * 6.0) * 1.8
            return 0.0, oy
        return 0.0, 0.0

    def get_bomb_glow_alpha(self, r, c):
        """炸弹红光脉冲强度 0~255"""
        t = self._time.get((r, c), 0.0)
        # 慢速脉冲：0.8Hz，范围 60~180
        val = (math.sin(t * 5.0) + 1.0) * 0.5
        return int(60 + val * 120)

    def get_particles(self, r, c):
        return self._particles.get((r, c), [])


# ═══════════════════════════════════════════════ AnimTile ══
class AnimTile:
    def __init__(self):
        self.ox = self.oy = 0.0
        self.scale = 1.0
        self.alpha = 255
        self.phase = "idle"
        self.t = self.dur = 0.0
        self.swap_dx = self.swap_dy = 0.0
        self.fall_from = 0.0
        self.pop_particles = []

    def start_swap(self, dx, dy, dur=0.16):
        self.phase = "swap"
        self.swap_dx = dx; self.swap_dy = dy
        self.t = 0.0; self.dur = dur

    def start_fall(self, from_oy, dur=0.22):
        self.phase = "fall"
        self.fall_from = from_oy; self.oy = from_oy
        self.t = 0.0; self.dur = dur

    def start_pop(self, color):
        self.phase = "pop"; self.t = 0.0; self.dur = 0.28
        self.pop_particles = []
        for _ in range(10):
            a = random.uniform(0, math.tau)
            s = random.uniform(2.0, 5.0)
            self.pop_particles.append(
                {"vx": math.cos(a)*s, "vy": math.sin(a)*s,
                 "color": color, "x": 0.0, "y": 0.0})

    def start_spawn(self, dur=0.18):
        self.phase = "spawn"; self.scale = 0.0
        self.t = 0.0; self.dur = dur

    def update(self, dt):
        if self.phase == "idle": return False
        self.t += dt
        p = min(1.0, self.t / self.dur) if self.dur > 0 else 1.0
        if self.phase == "swap":
            e = ease_in_out(p)
            self.ox = self.swap_dx*(1-e); self.oy = self.swap_dy*(1-e)
            if p >= 1.0: self.ox = self.oy = 0; self.phase = "idle"; return True
        elif self.phase == "fall":
            self.oy = self.fall_from*(1-ease_out(p))
            if p >= 1.0: self.oy = 0; self.phase = "idle"; return True
        elif self.phase == "spawn":
            self.scale = ease_out(p)
            if p >= 1.0: self.scale = 1.0; self.phase = "idle"; return True
        elif self.phase == "pop":
            self.scale = 1.0 - ease_out(p)
            self.alpha = int(255*(1-p))
            for pt in self.pop_particles:
                pt["x"] += pt["vx"]; pt["y"] += pt["vy"]; pt["vy"] += 0.25
            if p >= 1.0:
                self.phase = "idle"; self.scale = 1.0; self.alpha = 255; return True
        return False


# ═══════════════════════════════════════════════ Match3Pro ══
class Match3Pro:
    def __init__(self):
        pygame.init()
        self.win_w, self.win_h = BASE_W, BASE_H
        self.screen = pygame.display.set_mode(
            (self.win_w, self.win_h), pygame.RESIZABLE)
        pygame.display.set_caption("消消乐 ✦ 进阶版")
        self.clock = pygame.time.Clock()
        self.canvas = pygame.Surface((BASE_W, BASE_H))

        # ── 加载素材 ──────────────────────────────────────
        _assets.load()

        self._init_fonts()
        self.save_file = "game_save_pro.json"
        self.user_data = self._load_save()

        # ── 特殊道具动画管理器 ────────────────────────────
        self._sp_anim = SpecialAnimManager()

        self.state = "MAP"
        self.current_level = 1
        self.anims  = [[AnimTile() for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.popups = []
        self.settle_stars = 0
        self._btn_retry = self._btn_map_btn = pygame.Rect(0,0,1,1)
        self._reset_level()

    # ─── 字体 ─────────────────────────────────────────────
    def _init_fonts(self):
        cn_names = ["SimHei","Microsoft YaHei","PingFang SC",
                    "Hiragino Sans GB","WenQuanYi Micro Hei","Noto Sans CJK SC"]
        cn = None
        for name in cn_names:
            try:
                if pygame.font.SysFont(name, 20): cn = name; break
            except: pass
        self.f_sm  = pygame.font.SysFont(cn or "sans", 20)
        self.f_md  = pygame.font.SysFont(cn or "sans", 26)
        self.f_lg  = pygame.font.SysFont(cn or "sans", 36, bold=True)
        self.f_xl  = pygame.font.SysFont("Arial", 52, bold=True)
        self.f_num = pygame.font.SysFont("Arial", 50, bold=True)

    # ─── 存档 ─────────────────────────────────────────────
    def _load_save(self):
        if os.path.exists(self.save_file):
            with open(self.save_file) as f: return json.load(f)
        return {"unlocked": 1, "stars": {}}

    def _write_save(self, lvl, stars):
        self.user_data["stars"][str(lvl)] = max(
            self.user_data["stars"].get(str(lvl), 0), stars)
        if lvl == self.user_data["unlocked"] and lvl < MAX_LEVELS:
            self.user_data["unlocked"] += 1
        with open(self.save_file, "w") as f: json.dump(self.user_data, f)

    # ─── 关卡初始化 ───────────────────────────────────────
    def _reset_level(self):
        self.grid  = [[random.randint(0,5) for _ in range(GRID_SIZE)]
                       for _ in range(GRID_SIZE)]
        self.anims = [[AnimTile() for _ in range(GRID_SIZE)]
                       for _ in range(GRID_SIZE)]
        self._sp_anim.reset()          # ← 重置特殊道具动画状态
        self._remove_initial_matches()
        self.selected = None
        self.score    = 0
        self.cleared  = [0]*6    # 各色消除计数
        self.combo    = 0
        self.busy     = False
        self.popups   = []
        ld = LEVELS[self.current_level-1]
        self.steps      = ld["steps"]
        self.obj_type   = ld["type"]
        self.obj_target = ld["target"]
        self.obj_color  = ld.get("color", -1)
        self.star2_thr  = ld["star2"]
        self.star3_thr  = ld["star3"]

    def _remove_initial_matches(self):
        for _ in range(200):
            m = self._all_matches()
            if not m: break
            for r,c in m: self.grid[r][c] = random.randint(0,5)

    # ─── 坐标换算 ─────────────────────────────────────────
    def _scale(self):
        return min(self.win_w/BASE_W, self.win_h/BASE_H)

    def _win_to_logic(self, wx, wy):
        s = self._scale()
        ox = (self.win_w - BASE_W*s)/2
        oy = (self.win_h - BASE_H*s)/2
        return (wx-ox)/s, (wy-oy)/s

    def _grid_offset(self):
        return (BASE_W - GRID_PX)//2, 190

    # ─────────────────────── 颜色 / 类型辅助 ──────────────
    def _bc(self, val):
        if val < 0 or val >= SPECIAL_RAINBOW: return -1
        return val % 10

    def _sp(self, val):
        if val < 0:                 return -1
        if val >= SPECIAL_RAINBOW:  return SPECIAL_RAINBOW
        if val >= SPECIAL_BOMB:     return SPECIAL_BOMB
        if val >= SPECIAL_COL:      return SPECIAL_COL
        if val >= SPECIAL_ROW:      return SPECIAL_ROW
        return SPECIAL_NONE

    # ─── 匹配检测 ─────────────────────────────────────────
    def _all_matches(self):
        m = set()
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE-2):
                bc = [self._bc(self.grid[r][c+i]) for i in range(3)]
                if bc[0]>=0 and bc[0]==bc[1]==bc[2]:
                    m.update([(r,c),(r,c+1),(r,c+2)])
        for r in range(GRID_SIZE-2):
            for c in range(GRID_SIZE):
                bc = [self._bc(self.grid[r+i][c]) for i in range(3)]
                if bc[0]>=0 and bc[0]==bc[1]==bc[2]:
                    m.update([(r,c),(r+1,c),(r+2,c)])
        return m

    def _match_lines(self):
        lines = []
        def flush(run, d):
            if len(run) >= 3: lines.append({"cells": run[:], "dir": d})
        for r in range(GRID_SIZE):
            run = []
            for c in range(GRID_SIZE):
                bc = self._bc(self.grid[r][c])
                if bc < 0: flush(run,"h"); run=[]
                elif not run: run=[(r,c)]
                elif bc != self._bc(self.grid[run[-1][0]][run[-1][1]]): flush(run,"h"); run=[(r,c)]
                else: run.append((r,c))
            flush(run,"h")
        for c in range(GRID_SIZE):
            run = []
            for r in range(GRID_SIZE):
                bc = self._bc(self.grid[r][c])
                if bc < 0: flush(run,"v"); run=[]
                elif not run: run=[(r,c)]
                elif bc != self._bc(self.grid[run[-1][0]][run[-1][1]]): flush(run,"v"); run=[(r,c)]
                else: run.append((r,c))
            flush(run,"v")
        return lines

    def _collect_triggers(self, cells):
        to_del = set(cells)
        queue  = list(cells)
        vis    = set()
        while queue:
            r,c = queue.pop()
            if (r,c) in vis: continue
            vis.add((r,c))
            val = self.grid[r][c]
            sp  = self._sp(val)
            if sp == SPECIAL_ROW:
                for cc in range(GRID_SIZE): to_del.add((r,cc)); queue.append((r,cc))
            elif sp == SPECIAL_COL:
                for rr in range(GRID_SIZE): to_del.add((rr,c)); queue.append((rr,c))
            elif sp == SPECIAL_BOMB:
                for dr in range(-2,3):
                    for dc in range(-2,3):
                        if abs(dr)+abs(dc) <= 2:
                            nr,nc = r+dr,c+dc
                            if 0<=nr<GRID_SIZE and 0<=nc<GRID_SIZE:
                                to_del.add((nr,nc)); queue.append((nr,nc))
            elif sp == SPECIAL_RAINBOW:
                cnt = {}
                for rr in range(GRID_SIZE):
                    for cc in range(GRID_SIZE):
                        b = self._bc(self.grid[rr][cc])
                        if b>=0: cnt[b]=cnt.get(b,0)+1
                if cnt:
                    tc = max(cnt, key=cnt.get)
                    for rr in range(GRID_SIZE):
                        for cc in range(GRID_SIZE):
                            if self._bc(self.grid[rr][cc]) == tc:
                                to_del.add((rr,cc)); queue.append((rr,cc))
        return to_del

    def _rainbow_combine(self, r1,c1,r2,c2):
        v1,v2 = self.grid[r1][c1], self.grid[r2][c2]
        rr,rc = (r1,c1) if self._sp(v1)==SPECIAL_RAINBOW else (r2,c2)
        or_,oc = (r2,c2) if (rr,rc)==(r1,c1) else (r1,c1)
        osp = self._sp(self.grid[or_][oc])
        if osp in (SPECIAL_ROW,SPECIAL_COL,SPECIAL_BOMB):
            oval=self.grid[or_][oc]; obc=self._bc(oval)
            for row in range(GRID_SIZE):
                for col in range(GRID_SIZE):
                    if self._bc(self.grid[row][col])==obc:
                        self.grid[row][col]=osp+obc
            cells = {(row,col) for row in range(GRID_SIZE) for col in range(GRID_SIZE)
                     if self._bc(self.grid[row][col])==obc}
            to_del = self._collect_triggers(cells)
        else:
            to_del = self._collect_triggers({(rr,rc)})
        to_del.add((r1,c1)); to_del.add((r2,c2))
        return to_del

    def _detect_special(self, candidates, lines):
        new_sp = {}
        for sr,sc in candidates:
            sl = [l for l in lines if (sr,sc) in l["cells"]]
            if not sl: continue
            bc = -1
            for l in sl:
                for rr,cc in l["cells"]:
                    bc = self._bc(self.grid[rr][cc])
                    if bc >= 0: break
                if bc >= 0: break
            if bc < 0: bc = 0
            hl = [l for l in sl if l["dir"]=="h"]
            vl = [l for l in sl if l["dir"]=="v"]
            mh = max((len(l["cells"]) for l in hl), default=0)
            mv = max((len(l["cells"]) for l in vl), default=0)
            mn = max(mh,mv)
            if hl and vl:       new_sp[(sr,sc)] = SPECIAL_BOMB + bc
            elif mn >= 5:       new_sp[(sr,sc)] = SPECIAL_RAINBOW
            elif mn == 4:       new_sp[(sr,sc)] = (SPECIAL_ROW if mh==4 else SPECIAL_COL) + bc
        return new_sp

    # ─── 消除流程 ─────────────────────────────────────────
    def _try_swap(self, r1,c1,r2,c2):
        if self.busy: return
        dx=(c2-c1)*TILE_SIZE; dy=(r2-r1)*TILE_SIZE
        self.anims[r1][c1].start_swap(dx,dy)
        self.anims[r2][c2].start_swap(-dx,-dy)
        self.busy = True
        pygame.time.set_timer(pygame.USEREVENT+1, 180, 1)
        self._pending = (r1,c1,r2,c2)

    def _execute_swap(self):
        r1,c1,r2,c2 = self._pending
        self.grid[r1][c1],self.grid[r2][c2] = self.grid[r2][c2],self.grid[r1][c1]
        v1,v2 = self.grid[r1][c1],self.grid[r2][c2]
        sp1,sp2 = self._sp(v1),self._sp(v2)
        direct=False; to_del=set()

        if sp1==SPECIAL_RAINBOW and sp2==SPECIAL_RAINBOW:
            to_del={(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)}; direct=True
        elif sp1==SPECIAL_RAINBOW or sp2==SPECIAL_RAINBOW:
            to_del=self._rainbow_combine(r1,c1,r2,c2); direct=True
        elif sp1!=SPECIAL_NONE and sp2!=SPECIAL_NONE:
            to_del=self._collect_triggers({(r1,c1),(r2,c2)}); direct=True
        elif sp1!=SPECIAL_NONE or sp2!=SPECIAL_NONE:
            pos=(r1,c1) if sp1!=SPECIAL_NONE else (r2,c2)
            to_del=self._collect_triggers({pos}); direct=True

        if direct and to_del:
            self.steps -= 1; self.combo = 1
            self._add_score(len(to_del)*20, to_del)
            self._delete(to_del); self._fall_refill(); self._chain()
        elif self._all_matches():
            self.steps -= 1; self.combo = 0
            self._chain(swap_cands=[(r1,c1),(r2,c2)])
        else:
            self.grid[r1][c1],self.grid[r2][c2]=self.grid[r2][c2],self.grid[r1][c1]
            self.anims[r1][c1].start_swap(-((c2-c1)*TILE_SIZE),-((r2-r1)*TILE_SIZE))
            self.anims[r2][c2].start_swap((c2-c1)*TILE_SIZE,(r2-r1)*TILE_SIZE)
            self.busy = False

    def _chain(self, swap_cands=None):
        while True:
            lines = self._match_lines()
            if not lines: break
            matched = set()
            for l in lines: matched.update(l["cells"])
            if not matched: break
            self.combo += 1
            new_sp = self._detect_special(swap_cands, lines) if swap_cands else {}
            to_del = matched - set(new_sp.keys())
            for r,c in list(matched):
                if (r,c) in new_sp: continue
                if self._sp(self.grid[r][c]) != SPECIAL_NONE:
                    to_del.update(self._collect_triggers({(r,c)}))
            for pos in list(new_sp.keys()):
                if pos in to_del: del new_sp[pos]
            gain = len(to_del)*20*self.combo
            self._add_score(gain, to_del)
            self._delete(to_del)
            if new_sp:
                for (r,c),val in new_sp.items():
                    self.grid[r][c]=val
                    self.anims[r][c].start_spawn(0.35)
                self._frames(30)
            self._fall_refill()
            swap_cands = None
        # ─ 结束判断 ─
        if self._is_three_star() and self.steps > 0:
            self._bonus_phase()
        elif self.steps <= 0 or self._is_three_star():
            self._finish()
        else:
            self.busy = False

    def _is_three_star(self):
        v = self._progress_val()
        return v >= self.star3_thr

    def _progress_val(self):
        if self.obj_type == "score": return self.score
        return self.cleared[self.obj_color] if self.obj_color>=0 else sum(self.cleared)

    def _calc_stars(self):
        v = self._progress_val()
        if v >= self.star3_thr: return 3
        if v >= self.star2_thr: return 2
        if v >= self.obj_target: return 1
        return 0

    def _add_score(self, gain, cells):
        self.score += gain
        # 统计消除颜色
        for r,c in cells:
            val = self.grid[r][c]
            if val < 0: continue
            bc = self._bc(val)
            if 0<=bc<=5: self.cleared[bc] += 1
        if gain > 0 and cells:
            ox,oy = self._grid_offset()
            ra = sum(r for r,c in cells)/len(cells)
            ca = sum(c for r,c in cells)/len(cells)
            col = (255,235,60) if self.combo<=1 else (255,160,40) if self.combo<=3 else (255,80,80)
            txt = f"+{gain}" if self.combo<=1 else f"x{self.combo}  +{gain}"
            self.popups.append({
                "text": txt,
                "x": ox+ca*TILE_SIZE+TILE_SIZE//2,
                "y": oy+ra*TILE_SIZE,
                "life": 1.2, "color": col,
            })

    def _delete(self, cells):
        for r,c in cells:
            val = self.grid[r][c]
            if val >= 0:
                bc = self._bc(val)
                col = COLORS[bc] if bc>=0 else (220,220,220)
                self.anims[r][c].start_pop(col)
            self.grid[r][c] = -1
        self._frames(16)

    def _fall_refill(self):
        self._frames(5)
        for c in range(GRID_SIZE):
            col_vals = [(r,self.grid[r][c]) for r in range(GRID_SIZE) if self.grid[r][c]!=-1]
            en = GRID_SIZE-len(col_vals)
            for r in range(GRID_SIZE): self.grid[r][c]=-1
            for i,(orig_r,val) in enumerate(reversed(col_vals)):
                dr2=GRID_SIZE-1-i; self.grid[dr2][c]=val
                fall=dr2-orig_r
                if fall>0: self.anims[dr2][c].start_fall(-fall*TILE_SIZE)
            for i in range(en):
                self.grid[i][c]=random.randint(0,5)
                self.anims[i][c].start_fall(-(en-i)*TILE_SIZE)
        self._frames(20)

    def _bonus_phase(self):
        self.state = "SETTLING"
        rem=self.steps; self.steps=0
        avail=[(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)
               if self.grid[r][c]>=0 and self._sp(self.grid[r][c])==SPECIAL_NONE]
        random.shuffle(avail)
        bpos=[]
        for _ in range(rem):
            if not avail:
                avail=[(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)
                       if self.grid[r][c]>=0 and self._sp(self.grid[r][c])==SPECIAL_NONE]
                random.shuffle(avail)
            if not avail: break
            br,bc2=avail.pop(0)
            bc=self._bc(self.grid[br][bc2])
            if bc<0: bc=0
            spt=random.choice([SPECIAL_ROW,SPECIAL_COL,SPECIAL_BOMB,SPECIAL_BOMB,SPECIAL_RAINBOW])
            self.grid[br][bc2]=SPECIAL_RAINBOW if spt==SPECIAL_RAINBOW else spt+bc
            self.anims[br][bc2].start_spawn(0.3)
            bpos.append((br,bc2))
            self._frames(14)
        self._frames(45)
        if bpos:
            ad=self._collect_triggers(set(bpos))
            self._add_score(len(ad)*20, ad)
            self._delete(ad); self._fall_refill(); self._silent_chain()
        self._finish()

    def _silent_chain(self):
        while True:
            m=self._all_matches()
            if not m: break
            d=self._collect_triggers(m)
            self._add_score(len(d)*20,d)
            self._delete(d); self._fall_refill()

    def _finish(self):
        stars=self._calc_stars()
        self.settle_stars=stars
        self._write_save(self.current_level, stars)
        self._frames(50)
        self.state="RESULT"; self.busy=False

    # ─── 帧驱动 ───────────────────────────────────────────
    def _frames(self, n):
        for _ in range(n):
            dt=self.clock.tick(60)/1000.0
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE): self.anims[r][c].update(dt)
            self._sp_anim.update(dt, self.grid, self._sp)   # ← 更新特殊动画
            self._upd_popups(dt)
            self._render()
            for ev in pygame.event.get():
                if ev.type==pygame.QUIT: pygame.quit(); raise SystemExit
                if ev.type==pygame.VIDEORESIZE: self._resize(ev.w,ev.h)

    def _resize(self, w, h):
        self.win_w=max(240,w); self.win_h=max(390,h)
        self.screen=pygame.display.set_mode((self.win_w,self.win_h),pygame.RESIZABLE)

    def _upd_popups(self, dt):
        for p in self.popups: p["life"]-=dt; p["y"]-=38*dt
        self.popups=[p for p in self.popups if p["life"]>0]

    # ═══════════════════════════════════ 渲染总入口 ════════
    def _render(self):
        s = self._scale()
        if self.state=="MAP":                       self._draw_map()
        elif self.state in("PLAYING","SETTLING"):   self._draw_playing()
        elif self.state=="RESULT":                  self._draw_result()

        if abs(s-1.0) < 0.01:
            self.screen.blit(self.canvas,(0,0))
        else:
            sw,sh = int(BASE_W*s),int(BASE_H*s)
            scaled=pygame.transform.smoothscale(self.canvas,(sw,sh))
            self.screen.fill((10,10,14))
            self.screen.blit(scaled,((self.win_w-sw)//2,(self.win_h-sh)//2))
        pygame.display.flip()

    # ─── 方块绘制（核心改造：动物图片 + 特殊道具动画）────
    def _draw_tile(self, surf, r, c, val, x, y):
        if val < 0: return
        an = self.anims[r][c]
        bc = self._bc(val)
        sp = self._sp(val)
        col = COLORS[bc] if bc>=0 else (200,200,210)

        sc = max(0.0, an.scale)
        tw = int((TILE_SIZE-6)*sc)
        th = int((TILE_SIZE-6)*sc)
        if tw<2 or th<2: return

        # ── 特殊道具抖动偏移 ──────────────────────────────
        shk_ox, shk_oy = 0.0, 0.0
        if sp in (SPECIAL_ROW, SPECIAL_COL):
            shk_ox, shk_oy = self._sp_anim.get_shake(r, c, sp)

        bx = int(x + an.ox + shk_ox + 3 + (TILE_SIZE-6-tw)/2)
        by = int(y + an.oy + shk_oy + 3 + (TILE_SIZE-6-th)/2)

        # ── 确定素材 key ──────────────────────────────────
        if bc < 0:
            bc_safe = 0
        else:
            bc_safe = bc
        sp_key = None
        if sp == SPECIAL_ROW:     sp_key = "row"
        elif sp == SPECIAL_COL:   sp_key = "col"
        elif sp == SPECIAL_BOMB:  sp_key = "bomb"
        elif sp == SPECIAL_RAINBOW: sp_key = "rainbow"

        # ── 获取基础图块（animal + 静态叠加，带缓存）────────
        tile_surf = _assets.get_tile(bc_safe, sp_key, tw, th)

        # 处理 alpha（pop 动画）
        if an.alpha < 255:
            tile_surf = tile_surf.copy()
            tile_surf.set_alpha(an.alpha)

        surf.blit(tile_surf, (bx, by))

        # ── 炸弹：动态红光光晕（实时绘制，不进缓存）────────
        if sp == SPECIAL_BOMB:
            glow_alpha = self._sp_anim.get_bomb_glow_alpha(r, c)
            cx_abs = bx + tw//2
            cy_abs = by + th//2
            for ring_r in range(tw//2, tw//2 + 7, 2):
                ring_a = max(0, glow_alpha - (ring_r - tw//2) * 20)
                if ring_a <= 0: break
                ring_surf = pygame.Surface((ring_r*2+2, ring_r*2+2), pygame.SRCALPHA)
                pygame.draw.circle(ring_surf, (255, 50, 20, ring_a),
                                   (ring_r+1, ring_r+1), ring_r, 2)
                surf.blit(ring_surf, (cx_abs - ring_r - 1, cy_abs - ring_r - 1))
            # 炸弹叠加图（菱形符号）
            if "bomb" in _assets.special_imgs:
                ov = pygame.transform.smoothscale(_assets.special_imgs["bomb"], (tw, th))
                surf.blit(ov, (bx, by))

        # ── 彩虹：粒子环绕效果（实时绘制）──────────────────
        if sp == SPECIAL_RAINBOW:
            for p in self._sp_anim.get_particles(r, c):
                p.draw(surf, bx, by, alpha=min(255, an.alpha))

        # ── 爆炸粒子（pop 阶段）──────────────────────────
        if an.phase=="pop":
            frac=an.t/max(an.dur,0.001)
            for pt in an.pop_particles:
                a2=max(0,int(255*(1-frac)))
                px2=int(x+TILE_SIZE//2+pt["x"]*3)
                py2=int(y+TILE_SIZE//2+pt["y"]*3)
                ps=pygame.Surface((7,7),pygame.SRCALPHA)
                pygame.draw.circle(ps,pt["color"]+(a2,),(3,3),3)
                surf.blit(ps,(px2-3,py2-3))

    # ─── 进度条 ───────────────────────────────────────────
    def _draw_progress(self, surf, x, y, w, h=13):
        prog = clamp(self._progress_val()/max(1,self.star3_thr), 0, 1)
        pygame.draw.rect(surf,(38,40,58),(x,y,w,h),border_radius=h//2)
        fw=int(w*prog)
        if fw>0:
            for i in range(fw):
                t=i/max(1,w-1)
                if t<0.5:  rc=int(lerp(80,255,t*2)); gc=int(lerp(200,215,t*2)); bc2=50
                else:      rc=255; gc=int(lerp(215,120,(t-0.5)*2)); bc2=40
                pygame.draw.line(surf,(rc,gc,bc2),(x+i,y+2),(x+i,y+h-2))
        stars_got=self._calc_stars()
        for sn in range(1,4):
            thr=[self.obj_target,self.star2_thr,self.star3_thr][sn-1]
            px2=x+int(w*thr/max(1,self.star3_thr))
            px2=min(px2,x+w)
            pygame.draw.line(surf,(15,15,25),(px2,y),(px2,y+h),2)
            sc2=(255,210,0) if stars_got>=sn else (65,65,82)
            ss=self.f_sm.render("★",True,sc2)
            surf.blit(ss,(px2-ss.get_width()//2,y-ss.get_height()-1))

    # ─── 游戏界面 ─────────────────────────────────────────
    def _draw_playing(self):
        cv=self.canvas
        cv.fill((18,18,28))
        # 顶部信息板
        pygame.draw.rect(cv,(22,24,40),(0,0,BASE_W,182))
        pygame.draw.line(cv,(48,52,78),(0,182),(BASE_W,182),2)

        # 关卡
        lvl_s=self.f_sm.render(f"第 {self.current_level} 关",True,(115,122,160))
        cv.blit(lvl_s,(BASE_W//2-lvl_s.get_width()//2,6))

        # 步数大字
        sc2=(255,255,255) if self.steps>5 else (255,120,80)
        ns=self.f_num.render(str(self.steps),True,sc2)
        cv.blit(ns,(BASE_W//2-ns.get_width()//2,22))
        sl=self.f_sm.render("步",True,(100,108,140))
        cv.blit(sl,(BASE_W//2-ns.get_width()//2-sl.get_width()-4,42))

        # 目标说明
        if self.obj_type=="score":
            obj_s=self.f_sm.render(f"目标分数  {self.score:,} / {self.obj_target:,}",True,(175,185,215))
        else:
            cn=COLOR_NAMES[self.obj_color] if self.obj_color>=0 else "任意"
            v=self.cleared[self.obj_color] if self.obj_color>=0 else sum(self.cleared)
            obj_s=self.f_sm.render(f"消除{cn}色  {v} / {self.obj_target}",True,(175,185,215))
            # 颜色指示方块
            if self.obj_color>=0:
                ic=pygame.Surface((14,14),pygame.SRCALPHA)
                pygame.draw.rect(ic,COLORS[self.obj_color],(0,0,14,14),border_radius=4)
                cv.blit(ic,(BASE_W//2-obj_s.get_width()//2-18,88+3))
        cv.blit(obj_s,(BASE_W//2-obj_s.get_width()//2,88))

        # 进度条
        self._draw_progress(cv,28,116,BASE_W-56,14)

        # 分数（右侧小字）
        if self.obj_type=="clear":
            sc_s=self.f_sm.render(f"分数 {self.score:,}",True,(100,108,140))
            cv.blit(sc_s,(BASE_W-sc_s.get_width()-10,88))

        # ── 棋盘 ──
        ox,oy=self._grid_offset()
        board=pygame.Rect(ox-5,oy-5,GRID_PX+10,GRID_PX+10)
        pygame.draw.rect(cv,(26,28,44),board,border_radius=12)
        pygame.draw.rect(cv,(48,54,80),board,2,border_radius=12)

        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                shade=(30,32,46) if (r+c)%2==0 else (34,37,54)
                pygame.draw.rect(cv,shade,(ox+c*TILE_SIZE,oy+r*TILE_SIZE,TILE_SIZE,TILE_SIZE))

        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                self._draw_tile(cv,r,c,self.grid[r][c],ox+c*TILE_SIZE,oy+r*TILE_SIZE)

        # 选中高亮
        if self.selected:
            sr,sc3=self.selected
            sx=ox+sc3*TILE_SIZE; sy=oy+sr*TILE_SIZE
            gl=pygame.Surface((TILE_SIZE+10,TILE_SIZE+10),pygame.SRCALPHA)
            pygame.draw.rect(gl,(255,255,255,28),(0,0,TILE_SIZE+10,TILE_SIZE+10),border_radius=14)
            cv.blit(gl,(sx-5,sy-5))
            pygame.draw.rect(cv,(255,255,255),(sx,sy,TILE_SIZE,TILE_SIZE),3,12)

        # 浮动弹窗
        for p in self.popups:
            a=min(255,int(255*p["life"]/1.2))
            ps=self.f_md.render(p["text"],True,p["color"])
            ps.set_alpha(a)
            cv.blit(ps,(int(p["x"])-ps.get_width()//2,int(p["y"])))

        if self.state=="SETTLING":
            bar=pygame.Surface((240,38),pygame.SRCALPHA)
            draw_grad_rect(bar,(0,0,240,38),(40,38,64),(28,26,48),radius=19)
            cv.blit(bar,(BASE_W//2-120,BASE_H-56))
            tt=self.f_sm.render("✨ 步数奖励结算中…",True,(255,215,0))
            cv.blit(tt,(BASE_W//2-tt.get_width()//2,BASE_H-47))

    # ─── 结果界面 ─────────────────────────────────────────
    def _draw_result(self):
        self._draw_playing()
        cv=self.canvas
        ov=pygame.Surface((BASE_W,BASE_H),pygame.SRCALPHA)
        ov.fill((6,6,16,210)); cv.blit(ov,(0,0))

        cw,ch=BASE_W-70,320; cx2=35; cy2=188
        card=pygame.Surface((cw,ch),pygame.SRCALPHA)
        draw_grad_rect(card,(0,0,cw,ch),(38,42,66),(24,26,46),radius=22)
        pygame.draw.rect(card,(72,84,128,170),(0,0,cw,ch),2,border_radius=22)
        cv.blit(card,(cx2,cy2))

        passed=self._calc_stars()>0
        ts=self.f_lg.render("关卡完成！" if passed else "本关未通过",True,
                             (90,250,155) if passed else (255,100,75))
        cv.blit(ts,(BASE_W//2-ts.get_width()//2,cy2+16))

        # 星星
        for i in range(3):
            filled=i<self.settle_stars
            sc_col=(255,215,0) if filled else (52,55,76)
            ss=self.f_xl.render("★",True,sc_col)
            bx=BASE_W//2+(i-1)*74-ss.get_width()//2
            if filled:
                gl=pygame.Surface((ss.get_width()+18,ss.get_height()+12),pygame.SRCALPHA)
                gl.fill((255,215,0,32)); cv.blit(gl,(bx-9,cy2+70))
            cv.blit(ss,(bx,cy2+72))

        # 数据行
        if self.obj_type=="score":
            lines2=[f"分数  {self.score:,}  /  目标 {self.obj_target:,}"]
        else:
            cn=COLOR_NAMES[self.obj_color] if self.obj_color>=0 else "任意"
            v=self.cleared[self.obj_color] if self.obj_color>=0 else sum(self.cleared)
            lines2=[f"消除{cn}色  {v} 个  /  目标 {self.obj_target}",
                    f"总分  {self.score:,}"]
        for i,ln in enumerate(lines2):
            ls=self.f_sm.render(ln,True,(175,185,218))
            cv.blit(ls,(BASE_W//2-ls.get_width()//2,cy2+152+i*26))

        # 按钮
        bw2=(cw-30)//2; bh2=48
        btns=[("再来一局",cx2+8,cy2+ch-bh2-14,(50,140,78)),
              ("关卡地图",cx2+bw2+22,cy2+ch-bh2-14,(45,92,152))]
        self._btn_retry=pygame.Rect(cx2+8,cy2+ch-bh2-14,bw2,bh2)
        self._btn_map_btn=pygame.Rect(cx2+bw2+22,cy2+ch-bh2-14,bw2,bh2)
        for txt,bx,by,bc in btns:
            lc2=tuple(min(255,bc[i]+30) for i in range(3))
            draw_grad_rect(cv,(bx,by,bw2,bh2),lc2,bc,radius=13)
            bs=self.f_md.render(txt,True,(240,246,255))
            cv.blit(bs,(bx+bw2//2-bs.get_width()//2,by+bh2//2-bs.get_height()//2))

    # ─── 地图界面 ─────────────────────────────────────────
    def _draw_map(self):
        cv=self.canvas
        cv.fill((12,12,20))
        title=self.f_lg.render("关  卡  地  图",True,(205,215,255))
        cv.blit(title,(BASE_W//2-title.get_width()//2,16))

        pos=self._map_pos()
        # 路径
        for i in range(1,MAX_LEVELS):
            p1=pos[i-1]; p2=pos[i]
            unlocked=i<self.user_data["unlocked"]
            lc=(55,138,66) if unlocked else (42,44,58)
            my=(p1[1]+p2[1])//2
            pygame.draw.line(cv,lc,p1,(p1[0],my),3)
            pygame.draw.line(cv,lc,(p1[0],my),(p2[0],my),3)
            pygame.draw.line(cv,lc,(p2[0],my),p2,3)

        # 节点
        for i in range(MAX_LEVELS):
            lvl=i+1; px,py=pos[i]
            unlocked=lvl<=self.user_data["unlocked"]
            sg=self.user_data["stars"].get(str(lvl),0)
            ld=LEVELS[i]; R=26

            if unlocked:
                if ld["type"]=="clear":
                    cc=ld.get("color",-1)
                    nc=COLORS[cc] if cc>=0 else (145,110,215)
                    base_c=tuple(max(25,nc[i2]-65) for i2 in range(3))
                    ring_c=nc
                else:
                    base_c=(38,96,62); ring_c=(65,180,105)
                if sg==3:
                    gl=pygame.Surface((R*2+18,R*2+18),pygame.SRCALPHA)
                    pygame.draw.circle(gl,(255,215,0,38),(R+9,R+9),R+9)
                    cv.blit(gl,(px-R-9,py-R-9))
                pygame.draw.circle(cv,base_c,(px,py),R)
                pygame.draw.circle(cv,ring_c,(px,py),R,3)
                ns=self.f_md.render(str(lvl),True,(225,238,225))
            else:
                pygame.draw.circle(cv,(40,42,56),(px,py),R)
                pygame.draw.circle(cv,(60,62,80),(px,py),R,2)
                pygame.draw.line(cv,(70,72,90),(px-7,py-3),(px+7,py-3),3)
                pygame.draw.rect(cv,(70,72,90),(px-8,py-3,16,10),border_radius=3)
                ns=self.f_md.render(str(lvl),True,(75,78,95))
            cv.blit(ns,(px-ns.get_width()//2,py-ns.get_height()//2))

            # 类型图标（小字）
            if unlocked:
                icon="★" if ld["type"]=="score" else "◈"
                ic=self.f_sm.render(icon,True,(185,200,185))
                cv.blit(ic,(px-ic.get_width()//2,py-R-ic.get_height()-2))

            # 星星
            for s in range(3):
                sx=px-18+s*17; sy=py+R+5
                sc_col=(255,210,0) if s<sg else (46,48,62)
                ss=self.f_sm.render("★",True,sc_col)
                cv.blit(ss,(sx-ss.get_width()//2,sy))

    def _map_pos(self):
        cols=[68,BASE_W//2,BASE_W-68]
        row_h=88; sy=86; pos=[]
        for i in range(MAX_LEVELS):
            row=i//3; ci=i%3
            if row%2==1: ci=2-ci
            pos.append((cols[ci],sy+row*row_h))
        return pos

    def _map_hit(self, lx, ly):
        for i,(px,py) in enumerate(self._map_pos()):
            if math.hypot(lx-px,ly-py)<=32: return i+1
        return -1

    # ═══════════════════════════════════ 主循环 ═══════════
    def run(self):
        running=True
        while running:
            dt=self.clock.tick(60)/1000.0
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE): self.anims[r][c].update(dt)
            self._sp_anim.update(dt, self.grid, self._sp)   # ← 更新特殊道具动画
            self._upd_popups(dt)
            self._render()

            for ev in pygame.event.get():
                if ev.type==pygame.QUIT: running=False
                elif ev.type==pygame.VIDEORESIZE: self._resize(ev.w,ev.h)
                elif ev.type==pygame.USEREVENT+1: self._execute_swap()
                elif ev.type==pygame.MOUSEBUTTONDOWN:
                    lx,ly=self._win_to_logic(*ev.pos)
                    if self.state=="MAP":
                        lvl=self._map_hit(lx,ly)
                        if lvl>0 and lvl<=self.user_data["unlocked"]:
                            self.current_level=lvl; self._reset_level(); self.state="PLAYING"
                    elif self.state=="RESULT":
                        if self._btn_retry.collidepoint(lx,ly):
                            self._reset_level(); self.state="PLAYING"
                        elif self._btn_map_btn.collidepoint(lx,ly):
                            self.state="MAP"
                    elif self.state=="PLAYING" and not self.busy:
                        ox,oy=self._grid_offset()
                        c=int((lx-ox)//TILE_SIZE); r=int((ly-oy)//TILE_SIZE)
                        if 0<=r<GRID_SIZE and 0<=c<GRID_SIZE:
                            if self.selected is None: self.selected=(r,c)
                            else:
                                r1,c1=self.selected
                                if abs(r1-r)+abs(c1-c)==1:
                                    self.selected=None; self._try_swap(r1,c1,r,c)
                                elif (r,c)==(r1,c1): self.selected=None
                                else: self.selected=(r,c)

        pygame.quit()


if __name__ == "__main__":
    Match3Pro().run()