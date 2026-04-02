import pygame
import random
import json
import os

# --- 配置 ---
SCREEN_WIDTH, SCREEN_HEIGHT = 450, 750
GRID_SIZE = 8
TILE_SIZE = 50
OFFSET_X = (SCREEN_WIDTH - GRID_SIZE * TILE_SIZE) // 2
OFFSET_Y = 180

# 颜色与类型
# 类型说明: 0-5 普通颜色; 10+ (类型-10)的横消; 20+ 纵消; 30+ 彩虹炸弹
COLORS = [(255, 80, 80), (80, 255, 80), (80, 80, 255), (255, 255, 80), (255, 150, 50), (180, 80, 255)]
BG_COLOR = (30, 30, 35)

class Match3Pro:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("消消乐：进阶道具版")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("SimHei", 24)
        self.bold_font = pygame.font.SysFont("Arial", 40, bold=True)
        
        self.state = "MAP" # MAP, PLAYING, SETTLING
        self.save_file = "game_save_pro.json"
        self.user_data = self.load_progress()
        self.reset_level_vars()

    def load_progress(self):
        if os.path.exists(self.save_file):
            with open(self.save_file, 'r') as f: return json.load(f)
        return {"unlocked": 1, "stars": {}}

    def reset_level_vars(self):
        # 0-5: 普通, 10-15: 横, 20-25: 纵, 30: 彩虹
        self.grid = [[random.randint(0, 5) for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.remove_matches_initially()
        self.selected = None
        self.score = 0
        self.steps = 20
        self.target = 1000
        self.combo = 0
        self.animating = False

    def remove_matches_initially(self):
        """生成棋盘时防止出现现成的三连"""
        while True:
            matches = self.find_all_matches()
            if not matches: break
            for r, c in matches: self.grid[r][c] = random.randint(0, 5)

    # --- 逻辑核心 ---
    def find_all_matches(self):
        matched = set()
        # 横向
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE - 2):
                if self.grid[r][c] % 10 == self.grid[r][c+1] % 10 == self.grid[r][c+2] % 10:
                    if self.grid[r][c] != -1: matched.update([(r,c), (r,c+1), (r,c+2)])
        # 纵向
        for r in range(GRID_SIZE - 2):
            for c in range(GRID_SIZE):
                if self.grid[r][c] % 10 == self.grid[r+1][c] % 10 == self.grid[r+2][c] % 10:
                    if self.grid[r][c] != -1: matched.update([(r,c), (r+1,c), (r+2,c)])
        return matched

    def trigger_special(self, r, c, tile_type):
        """处理特殊道具的连锁反应"""
        to_del = {(r, c)}
        if 10 <= tile_type < 20: # 横消
            for col in range(GRID_SIZE): to_del.add((r, col))
        elif 20 <= tile_type < 30: # 纵消
            for row in range(GRID_SIZE): to_del.add((row, c))
        elif tile_type >= 30: # 炸弹：消除全场同色
            color_target = random.randint(0, 5)
            for row in range(GRID_SIZE):
                for col in range(GRID_SIZE):
                    if self.grid[row][col] % 10 == color_target: to_del.add((row, col))
        return to_del

    def process_matches(self, last_swap_pos=None):
        """包含道具生成逻辑的消除过程"""
        self.animating = True
        while True:
            matches = list(self.find_all_matches())
            if not matches: break
            
            self.combo += 1
            actual_to_del = set()
            
            # 检查是否有特殊道具在消除范围内
            for r, c in matches:
                if self.grid[r][c] >= 10:
                    actual_to_del.update(self.trigger_special(r, c, self.grid[r][c]))
                else:
                    actual_to_del.add((r, c))
            
            # 道具生成逻辑 (4消或5消)
            special_created = False
            if last_swap_pos and len(matches) >= 4:
                sr, sc = last_swap_pos
                if len(matches) >= 5: self.grid[sr][sc] = 30 # 5消变彩虹
                elif len(matches) == 4: self.grid[sr][sc] = (self.grid[sr][sc]%10) + random.choice([10, 20])
                actual_to_del.discard((sr, sc))
                special_created = True

            # 执行消除
            self.score += len(actual_to_del) * 20 * self.combo
            for r, c in actual_to_del: self.grid[r][c] = -1
            
            self.animate_falling()
            last_swap_pos = None # 仅第一波触发道具生成

        self.animating = False

    def animate_falling(self):
        """物理掉落效果"""
        falling = True
        while falling:
            falling = False
            # 1. 掉落现有方块
            for c in range(GRID_SIZE):
                for r in range(GRID_SIZE-1, 0, -1):
                    if self.grid[r][c] == -1 and self.grid[r-1][c] != -1:
                        self.grid[r][c] = self.grid[r-1][c]
                        self.grid[r-1][c] = -1
                        falling = True
            # 2. 顶部生成新方块
            for c in range(GRID_SIZE):
                if self.grid[0][c] == -1:
                    self.grid[0][c] = random.randint(0, 5)
                    falling = True
            
            if falling:
                self.draw_playing()
                pygame.display.flip()
                pygame.time.delay(50)

    # --- UI 渲染 ---
    def draw_star_bar(self):
        bar_rect = pygame.Rect(50, 110, SCREEN_WIDTH-100, 15)
        pygame.draw.rect(self.screen, (50, 50, 50), bar_rect, border_radius=5)
        progress = min(1.0, self.score / (self.target * 2))
        curr_bar = pygame.Rect(50, 110, (SCREEN_WIDTH-100) * progress, 15)
        pygame.draw.rect(self.screen, (255, 215, 0), curr_bar, border_radius=5)
        
        # 绘制星级点
        for i in [1, 1.5, 2]:
            px = 50 + (SCREEN_WIDTH-100) * (i/2)
            color = (255, 255, 0) if self.score >= self.target * i/1 else (100, 100, 100)
            pygame.draw.circle(self.screen, color, (int(px), 118), 8)

    def draw_tile(self, r, c, val, x, y):
        if val == -1: return
        base_val = val % 10
        color = COLORS[base_val]
        rect = pygame.Rect(x+4, y+4, TILE_SIZE-8, TILE_SIZE-8)
        
        # 基础形状
        pygame.draw.rect(self.screen, color, rect, border_radius=12)
        
        # 道具特殊标记
        if 10 <= val < 20: # 横
            pygame.draw.line(self.screen, (255,255,255), (x+10, y+TILE_SIZE//2), (x+TILE_SIZE-10, y+TILE_SIZE//2), 4)
        elif 20 <= val < 30: # 纵
            pygame.draw.line(self.screen, (255,255,255), (x+TILE_SIZE//2, y+10), (x+TILE_SIZE//2, y+TILE_SIZE-10), 4)
        elif val >= 30: # 彩虹
            pygame.draw.circle(self.screen, (255,255,255), (x+TILE_SIZE//2, y+TILE_SIZE//2), TILE_SIZE//4, 3)

    def draw_playing(self):
        self.screen.fill(BG_COLOR)
        self.draw_star_bar()
        # UI
        step_txt = self.bold_font.render(f"{self.steps}", True, (255, 255, 255))
        self.screen.blit(step_txt, (SCREEN_WIDTH//2-15, 40))
        score_txt = self.font.render(f"Score: {self.score}", True, (200, 200, 200))
        self.screen.blit(score_txt, (SCREEN_WIDTH//2-40, 135))

        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                x, y = OFFSET_X + c*TILE_SIZE, OFFSET_Y + r*TILE_SIZE
                self.draw_tile(r, c, self.grid[r][c], x, y)
                if self.selected == (r, c):
                    pygame.draw.rect(self.screen, (255,255,255), (x, y, TILE_SIZE, TILE_SIZE), 2, 12)

    # --- 结算逻辑 ---
    def bonus_time(self):
        """结算：步数变道具并释放"""
        self.state = "SETTLING"
        while self.steps > 0:
            self.steps -= 1
            # 随机选一个变道具
            br, bc = random.randint(0, GRID_SIZE-1), random.randint(0, GRID_SIZE-1)
            self.grid[br][bc] = random.choice([10, 20, 30]) + (self.grid[br][bc]%10 if self.grid[br][bc]<30 else 0)
            
            self.draw_playing()
            pygame.display.flip()
            pygame.time.delay(200)
            
            self.process_matches((br, bc))
            
        # 计算星级
        stars = 0
        if self.score >= self.target: stars = 1
        if self.score >= self.target * 1.5: stars = 2
        if self.score >= self.target * 2: stars = 3
        
        # 保存并返回
        self.save_progress(self.current_level, stars)
        pygame.time.delay(1000)
        self.state = "MAP"

    def save_progress(self, lvl, stars):
        self.user_data["stars"][str(lvl)] = max(self.user_data["stars"].get(str(lvl), 0), stars)
        if lvl == self.user_data["unlocked"] and lvl < 15:
            self.user_data["unlocked"] += 1
        with open(self.save_file, 'w') as f: json.dump(self.user_data, f)

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.MOUSEBUTTONDOWN and not self.animating:
                    pos = event.pos
                    if self.state == "MAP":
                        # 简易地图点击判断
                        for i in range(1, 10):
                            r, c = (i-1)//3, (i-1)%3
                            if pygame.Rect(80+c*110, 200+r*110, 70, 70).collidepoint(pos) and i <= self.user_data["unlocked"]:
                                self.current_level = i
                                self.target = 1000 + i*500
                                self.reset_level_vars()
                                self.state = "PLAYING"
                    elif self.state == "PLAYING":
                        c, r = (pos[0]-OFFSET_X)//TILE_SIZE, (pos[1]-OFFSET_Y)//TILE_SIZE
                        if 0<=r<GRID_SIZE and 0<=c<GRID_SIZE:
                            if not self.selected: self.selected = (r, c)
                            else:
                                r1, c1 = self.selected
                                if abs(r1-r) + abs(c1-c) == 1:
                                    self.grid[r][c], self.grid[r1][c1] = self.grid[r1][c1], self.grid[r][c]
                                    if self.find_all_matches():
                                        self.steps -= 1
                                        self.combo = 0
                                        self.process_matches((r, c))
                                        if self.score >= self.target or self.steps <= 0:
                                            self.bonus_time()
                                    else:
                                        self.grid[r][c], self.grid[r1][c1] = self.grid[r1][c1], self.grid[r][c]
                                self.selected = None

            if self.state == "MAP":
                self.screen.fill(BG_COLOR)
                for i in range(1, 10):
                    r, c = (i-1)//3, (i-1)%3
                    color = (100, 200, 100) if i <= self.user_data["unlocked"] else (80, 80, 80)
                    pygame.draw.rect(self.screen, color, (80+c*110, 200+r*110, 70, 70), border_radius=15)
                    txt = self.font.render(str(i), True, (255,255,255))
                    self.screen.blit(txt, (105+c*110, 225+r*110))
            elif self.state == "PLAYING" or self.state == "SETTLING":
                self.draw_playing()
            
            pygame.display.flip()
            self.clock.tick(60)

if __name__ == "__main__":
    Match3Pro().run()