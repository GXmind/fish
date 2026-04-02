import pygame
import random
import sys

# ===================== 常量设置 =====================
WIDTH, HEIGHT = 600, 700
ROWS, COLS = 8, 8
CELL_SIZE = 60
PADDING = 20
COLORS = [
    (255, 100, 100),   # 红
    (100, 255, 100),   # 绿
    (100, 100, 255),   # 蓝
    (255, 255, 100),   # 黄
    (255, 100, 255),   # 粉
    (100, 255, 255)    # 青
]
FPS = 60

# ===================== 初始化 =====================
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("开心消消乐 - 简易版")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 40)

# ===================== 生成棋盘 =====================
def create_board():
    board = [[random.choice(COLORS) for _ in range(COLS)] for _ in range(ROWS)]
    # 避免一开始就有三连
    while check_matches(board):
        board = [[random.choice(COLORS) for _ in range(COLS)] for _ in range(ROWS)]
    return board

# ===================== 绘制棋盘 =====================
def draw_board(board, selected=None):
    screen.fill((30, 30, 30))
    for r in range(ROWS):
        for c in range(COLS):
            x = PADDING + c * CELL_SIZE
            y = PADDING + r * CELL_SIZE
            color = board[r][c]
            pygame.draw.rect(screen, color, (x, y, CELL_SIZE-2, CELL_SIZE-2), border_radius=8)
            # 选中框
            if selected == (r, c):
                pygame.draw.rect(screen, (255,255,255), (x,y,CELL_SIZE-2,CELL_SIZE-2), 3, border_radius=8)
    # 分数
    score_text = font.render(f"Score: {score}", True, (255,255,255))
    screen.blit(score_text, (20, 550))

# ===================== 检查三连及以上 =====================
def check_matches(board):
    matched = [[False]*COLS for _ in range(ROWS)]
    # 横向
    for r in range(ROWS):
        for c in range(COLS-2):
            if board[r][c] == board[r][c+1] == board[r][c+2] != None:
                matched[r][c] = matched[r][c+1] = matched[r][c+2] = True
    # 纵向
    for c in range(COLS):
        for r in range(ROWS-2):
            if board[r][c] == board[r+1][c] == board[r+2][c] != None:
                matched[r][c] = matched[r+1][c] = matched[r+2][c] = True
    return matched

# ===================== 消除得分 =====================
def remove_matches(board, matched):
    global score
    count = 0
    for r in range(ROWS):
        for c in range(COLS):
            if matched[r][c]:
                board[r][c] = None
                count +=1
    score += count * 10
    return count >0

# ===================== 下落填充 =====================
def drop_down(board):
    for c in range(COLS):
        col = [board[r][c] for r in range(ROWS) if board[r][c] is not None]
        new_col = [None]*(ROWS - len(col)) + col
        for r in range(ROWS):
            board[r][c] = new_col[r]

# ===================== 顶部补充新方块 =====================
def fill_empty(board):
    for c in range(COLS):
        for r in range(ROWS):
            if board[r][c] is None:
                board[r][c] = random.choice(COLORS)

# ===================== 交换两个格子 =====================
def swap(board, r1,c1, r2,c2):
    board[r1][c1], board[r2][c2] = board[r2][c2], board[r1][c1]

# ===================== 判断是否相邻 =====================
def is_adjacent(r1,c1,r2,c2):
    return (abs(r1-r2) ==1 and c1==c2) or (abs(c1-c2)==1 and r1==r2)

# ===================== 主逻辑 =====================
def main():
    global score
    board = create_board()
    score = 0
    selected = None
    running = True

    while running:
        clock.tick(FPS)
        draw_board(board, selected)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                c = (mx - PADDING) // CELL_SIZE
                r = (my - PADDING) // CELL_SIZE

                if 0<=r<ROWS and 0<=c<COLS:
                    if not selected:
                        selected = (r,c)
                    else:
                        r1,c1 = selected
                        r2,c2 = r,c
                        if is_adjacent(r1,c1,r2,c2):
                            swap(board, r1,c1, r2,c2)
                            # 检查是否能消除
                            matched = check_matches(board)
                            if remove_matches(board, matched):
                                # 自动下落、填充、连续消除
                                while True:
                                    drop_down(board)
                                    fill_empty(board)
                                    matched = check_matches(board)
                                    if not remove_matches(board, matched):
                                        break
                            else:
                                # 不能消除就换回去
                                swap(board, r1,c1,r2,c2)
                        selected = None

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()