"""
生成消消乐动物素材 PNG
每种动物: 48x48, RGBA, 透明背景
文件输出到 assets/ 目录
"""
from PIL import Image, ImageDraw, ImageFilter
import math, os

SIZE = 48
os.makedirs("assets", exist_ok=True)

# ── 颜色方案 ─────────────────────────────────────────────
PALETTES = {
    "cat":    {"bg1": (255, 130, 130), "bg2": (220, 60, 60),
               "body": (245, 185, 160), "inner": (255, 210, 200), "accent": (255, 100, 120)},
    "dog":    {"bg1": (110, 175, 255), "bg2": (50, 120, 230),
               "body": (230, 190, 140), "inner": (245, 215, 180), "accent": (100, 150, 220)},
    "rabbit": {"bg1": (195, 140, 255), "bg2": (140, 60, 220),
               "body": (240, 230, 245), "inner": (255, 200, 230), "accent": (200, 100, 255)},
    "bear":   {"bg1": (100, 215, 160), "bg2": (40, 170, 100),
               "body": (190, 150, 110), "inner": (220, 185, 150), "accent": (60, 190, 120)},
    "bird":   {"bg1": (255, 210, 80),  "bg2": (240, 160, 20),
               "body": (255, 230, 120), "inner": (255, 245, 190), "accent": (255, 180, 30)},
    "fox":    {"bg1": (255, 160, 100), "bg2": (230, 100, 40),
               "body": (240, 160, 80),  "inner": (255, 220, 180), "accent": (220, 90, 30)},
}

def make_base(img, draw, pal):
    """圆形渐变底盘"""
    cx = cy = SIZE // 2
    r = SIZE // 2 - 2
    # 外发光
    for i in range(4, 0, -1):
        alpha = 40 - i * 8
        color = pal["bg1"] + (alpha,)
        draw.ellipse([cx-r-i, cy-r-i, cx+r+i, cy+r+i], fill=color)
    # 主圆 - 简单径向渐变用多层椭圆模拟
    for step in range(r, 0, -1):
        t = step / r
        c = tuple(int(pal["bg1"][j] * (1-t) + pal["bg2"][j] * t) for j in range(3))
        draw.ellipse([cx-step, cy-step, cx+step, cy+step], fill=c + (255,))
    # 高光
    draw.ellipse([cx-r//2, cy-r+3, cx+r//4, cy-r//3],
                 fill=(255, 255, 255, 60))

def draw_cat(img, draw, pal):
    cx = cy = SIZE // 2
    B = SIZE * 0.42
    # 耳朵
    for ex in [-1, 1]:
        pts = [
            (cx + ex*B*0.28, cy - B*0.70),
            (cx + ex*B*0.58, cy - B*1.18),
            (cx + ex*B*0.62, cy - B*0.70),
        ]
        pts = [(int(x), int(y)) for x, y in pts]
        draw.polygon(pts, fill=pal["body"])
        inner = [
            (cx + ex*B*0.33, cy - B*0.72),
            (cx + ex*B*0.54, cy - B*1.08),
            (cx + ex*B*0.57, cy - B*0.72),
        ]
        inner = [(int(x), int(y)) for x, y in inner]
        draw.polygon(inner, fill=pal["accent"])
    # 身体
    draw.ellipse([int(cx-B*.72), int(cy+B*.05-B*.58), int(cx+B*.72), int(cy+B*.05+B*.58)],
                 fill=pal["body"])
    # 头
    draw.ellipse([int(cx-B*.56), int(cy-B*.78), int(cx+B*.56), int(cy+B*.34)],
                 fill=pal["body"])
    # 脸白色
    draw.ellipse([int(cx-B*.28), int(cy-B*.36), int(cx+B*.28), int(cy+B*.1)],
                 fill=pal["inner"])
    # 眼睛
    for ex in [-1, 1]:
        ex2 = int(cx + ex*B*.22); ey2 = int(cy - B*.26)
        draw.ellipse([ex2-int(B*.1), ey2-int(B*.12), ex2+int(B*.1), ey2+int(B*.12)],
                     fill=(30, 20, 20))
        draw.ellipse([ex2+int(B*.03)-3, ey2-int(B*.1), ex2+int(B*.03)+2, ey2-int(B*.1)+4],
                     fill=(255, 255, 255))
    # 鼻子
    draw.ellipse([int(cx-B*.06), int(cy-B*.1), int(cx+B*.06), int(cy-B*.02)],
                 fill=(255, 140, 160))
    # 胡须
    for ey2, ex2_end in [(-1, -1), (0, -1), (-1, 1), (0, 1)]:
        x0 = int(cx); y0 = int(cy - B*.06 + ey2*2)
        x1 = int(cx + ex2_end*B*.38); y1 = int(cy - B*.04 + ey2*2)
        draw.line([(x0, y0), (x1, y1)], fill=(180, 140, 140, 180), width=1)
    # 尾巴
    pts = []
    for t2 in range(20):
        tt = t2 / 19
        qx = (1-tt)**2*(cx+B*.5) + 2*(1-tt)*tt*(cx+B*1.1) + tt**2*(cx+B*.9)
        qy = (1-tt)**2*(cy+B*.45) + 2*(1-tt)*tt*(cy+B*.15) + tt**2*(cy-B*.15)
        pts.append((int(qx), int(qy)))
    if len(pts) > 1:
        draw.line(pts, fill=pal["body"], width=max(2, int(B*.18)))

def draw_dog(img, draw, pal):
    cx = cy = SIZE // 2
    B = SIZE * 0.42
    # 垂耳
    for ex in [-1, 1]:
        ex2 = cx + int(ex * B * .52)
        draw.ellipse([ex2-int(B*.22), int(cy-B*.38), ex2+int(B*.22), int(cy+B*.38)],
                     fill=pal["accent"])
    # 身体
    draw.ellipse([int(cx-B*.8), int(cy-B*.4), int(cx+B*.8), int(cy+B*.72)],
                 fill=pal["body"])
    # 头
    draw.ellipse([int(cx-B*.58), int(cy-B*.82), int(cx+B*.58), int(cy+B*.28)],
                 fill=pal["body"])
    # 口鼻
    draw.ellipse([int(cx-B*.3), int(cy-B*.3), int(cx+B*.3), int(cy+B*.1)],
                 fill=pal["inner"])
    # 眼睛
    for ex in [-1, 1]:
        ex2 = int(cx + ex*B*.2); ey2 = int(cy - B*.42)
        draw.ellipse([ex2-int(B*.1), ey2-int(B*.11), ex2+int(B*.1), ey2+int(B*.11)],
                     fill=(40, 25, 10))
        draw.ellipse([ex2+3, ey2-int(B*.09), ex2+6, ey2-int(B*.09)+4],
                     fill=(255, 255, 255))
    # 鼻子
    draw.ellipse([int(cx-B*.1), int(cy-B*.22), int(cx+B*.1), int(cy-B*.08)],
                 fill=(60, 40, 20))
    # 尾巴
    pts = []
    for t2 in range(16):
        tt = t2/15
        qx=(1-tt)**2*(cx+B*.6)+2*(1-tt)*tt*(cx+B*1.05)+tt**2*(cx+B*.88)
        qy=(1-tt)**2*(cy+B*.28)+2*(1-tt)*tt*(cy-B*.06)+tt**2*(cy-B*.4)
        pts.append((int(qx),int(qy)))
    if len(pts)>1:
        draw.line(pts,fill=pal["body"],width=max(2,int(B*.18)))

def draw_rabbit(img, draw, pal):
    cx = cy = SIZE // 2
    B = SIZE * 0.42
    # 长耳朵
    for ex in [-1, 1]:
        angle = 0.08 * ex
        ex2 = cx + int(ex * B * .26)
        ey2 = cy - int(B * 1.22)
        draw.ellipse([ex2-int(B*.16), ey2-int(B*.5), ex2+int(B*.16), ey2+int(B*.5)],
                     fill=pal["body"])
        draw.ellipse([ex2-int(B*.08), ey2-int(B*.4), ex2+int(B*.08), ey2+int(B*.4)],
                     fill=pal["accent"])
    # 身体
    draw.ellipse([int(cx-B*.68), int(cy-B*.22), int(cx+B*.68), int(cy+B*.72)],
                 fill=pal["body"])
    # 头
    draw.ellipse([int(cx-B*.52), int(cy-B*.78), int(cx+B*.52), int(cy+B*.22)],
                 fill=pal["body"])
    # 脸
    draw.ellipse([int(cx-B*.26), int(cy-B*.38), int(cx+B*.26), int(cy+B*.06)],
                 fill=pal["inner"])
    # 眼睛（粉红）
    for ex in [-1, 1]:
        ex2=int(cx+ex*B*.18); ey2=int(cy-B*.42)
        draw.ellipse([ex2-int(B*.09),ey2-int(B*.11),ex2+int(B*.09),ey2+int(B*.11)],
                     fill=(200, 60, 100))
        draw.ellipse([ex2+2,ey2-int(B*.09),ex2+5,ey2-int(B*.09)+4],fill=(255,255,255))
    # 鼻子
    draw.ellipse([int(cx-B*.055),int(cy-B*.22),int(cx+B*.055),int(cy-B*.12)],
                 fill=(255, 170, 190))
    # 尾巴
    draw.ellipse([int(cx+B*.42),int(cy+B*.38),int(cx+B*.42)+int(B*.36),int(cy+B*.38)+int(B*.36)],
                 fill=(255,255,255))

def draw_bear(img, draw, pal):
    cx = cy = SIZE // 2
    B = SIZE * 0.42
    # 圆耳朵
    for ex in [-1, 1]:
        ex2=int(cx+ex*B*.44); ey2=int(cy-B*.76)
        draw.ellipse([ex2-int(B*.22),ey2-int(B*.22),ex2+int(B*.22),ey2+int(B*.22)],fill=pal["body"])
        draw.ellipse([ex2-int(B*.12),ey2-int(B*.12),ex2+int(B*.12),ey2+int(B*.12)],fill=pal["accent"])
    # 身体
    draw.ellipse([int(cx-B*.82),int(cy-B*.32),int(cx+B*.82),int(cy+B*.76)],fill=pal["body"])
    # 头
    draw.ellipse([int(cx-B*.60),int(cy-B*.86),int(cx+B*.60),int(cy+B*.28)],fill=pal["body"])
    # 口鼻
    draw.ellipse([int(cx-B*.3),int(cy-B*.28),int(cx+B*.3),int(cy+B*.14)],fill=pal["inner"])
    # 眼睛
    for ex in [-1, 1]:
        ex2=int(cx+ex*B*.2); ey2=int(cy-B*.42)
        draw.ellipse([ex2-int(B*.1),ey2-int(B*.11),ex2+int(B*.1),ey2+int(B*.11)],fill=(25,12,5))
        draw.ellipse([ex2+2,ey2-9,ex2+5,ey2-5],fill=(255,255,255))
    # 鼻子
    draw.ellipse([int(cx-B*.1),int(cy-B*.22),int(cx+B*.1),int(cy-B*.1)],fill=(80,45,20))

def draw_bird(img, draw, pal):
    cx = cy = SIZE // 2
    B = SIZE * 0.42
    # 翅膀
    for ex in [-1, 1]:
        pts=[(cx,cy),(cx+ex*B*.5,cy-B*.28),(cx+ex*B*.58,cy+B*.52),(cx,cy+B*.3)]
        draw.polygon([(int(x),int(y)) for x,y in pts],fill=pal["accent"])
    # 身体
    draw.ellipse([int(cx-B*.6),int(cy-B*.48),int(cx+B*.6),int(cy+B*.72)],fill=pal["body"])
    # 头
    draw.ellipse([int(cx-B*.48),int(cy-B*.9),int(cx+B*.48),int(cy+B*.0)],fill=pal["body"])
    # 嘴
    pts=[(cx-int(B*.07),int(cy-B*.44)),(cx+int(B*.07),int(cy-B*.44)),(cx,int(cy-B*.18))]
    draw.polygon([(int(x),int(y)) for x,y in pts],fill=(255,200,20))
    # 眼睛
    for ex in [-1,1]:
        ex2=int(cx+ex*B*.18); ey2=int(cy-B*.58)
        draw.ellipse([ex2-int(B*.1),ey2-int(B*.1),ex2+int(B*.1),ey2+int(B*.1)],fill=(20,20,20))
        draw.ellipse([ex2+2,ey2-8,ex2+5,ey2-4],fill=(255,255,255))
    # 尾巴
    pts=[(int(cx-B*.28),int(cy+B*.72)),(cx,int(cy+B*.55)),(int(cx+B*.28),int(cy+B*.72)),(cx,int(cy+B*1.08))]
    draw.polygon([(int(x),int(y)) for x,y in pts],fill=pal["accent"])

def draw_fox(img, draw, pal):
    cx = cy = SIZE // 2
    B = SIZE * 0.42
    # 尖耳朵
    for ex in [-1, 1]:
        pts=[(cx+ex*B*.2,cy-B*.68),(cx+ex*B*.52,cy-B*1.22),(cx+ex*B*.6,cy-B*.68)]
        draw.polygon([(int(x),int(y)) for x,y in pts],fill=pal["body"])
        inner=[(cx+ex*B*.26,cy-B*.72),(cx+ex*B*.48,cy-B*1.1),(cx+ex*B*.54,cy-B*.72)]
        draw.polygon([(int(x),int(y)) for x,y in inner],fill=pal["accent"])
    # 身体
    draw.ellipse([int(cx-B*.76),int(cy-B*.12),int(cx+B*.76),int(cy+B*.72)],fill=pal["body"])
    # 头
    draw.ellipse([int(cx-B*.56),int(cy-B*.78),int(cx+B*.56),int(cy+B*.28)],fill=pal["body"])
    # 白色脸部
    draw.ellipse([int(cx-B*.32),int(cy-B*.36),int(cx+B*.32),int(cy+B*.1)],fill=(255,248,240))
    # 眼睛
    for ex in [-1,1]:
        ex2=int(cx+ex*B*.2); ey2=int(cy-B*.3)
        draw.ellipse([ex2-int(B*.1),ey2-int(B*.12),ex2+int(B*.1),ey2+int(B*.12)],fill=(30,15,5))
        draw.ellipse([ex2+2,ey2-10,ex2+5,ey2-6],fill=(255,255,255))
    # 鼻子
    draw.ellipse([int(cx-B*.07),int(cy-B*.14),int(cx+B*.07),int(cy-B*.04)],fill=(180,60,30))
    # 尾巴
    pts=[]
    for t2 in range(18):
        tt=t2/17
        qx=(1-tt)**2*(cx+B*.6)+2*(1-tt)*tt*(cx+B*1.12)+tt**2*(cx+B*.92)
        qy=(1-tt)**2*(cy+B*.48)+2*(1-tt)*tt*(cy+B*.12)+tt**2*(cy-B*.18)
        pts.append((int(qx),int(qy)))
    if len(pts)>1:
        draw.line(pts,fill=pal["body"],width=max(3,int(B*.26)))
    # 尾尖白
    pts2=[]
    for t2 in range(8):
        tt=t2/7
        qx=(1-tt)**2*(cx+B*.88)+2*(1-tt)*tt*(cx+B*1.0)+tt**2*(cx+B*.92)
        qy=(1-tt)**2*(cy-B*.1)+2*(1-tt)*tt*(cy-B*.22)+tt**2*(cy-B*.18)
        pts2.append((int(qx),int(qy)))
    if len(pts2)>1:
        draw.line(pts2,fill=(255,248,240),width=max(2,int(B*.14)))

DRAW_FNS = {
    "cat": draw_cat, "dog": draw_dog, "rabbit": draw_rabbit,
    "bear": draw_bear, "bird": draw_bird, "fox": draw_fox,
}

# ── 生成每种动物 ───────────────────────────────────────────
for name, pal in PALETTES.items():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    make_base(img, draw, pal)
    DRAW_FNS[name](img, draw, pal)
    img.save(f"assets/{name}.png")
    print(f"saved assets/{name}.png")

# ── 生成特殊叠加层 ──────────────────────────────────────────
# 横消箭头层
def make_row_arrow():
    img = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    cx = cy = SIZE // 2
    y = cy + 16
    col = (255, 235, 60, 230)
    # 横线
    draw.line([(8, y), (SIZE-8, y)], fill=col, width=3)
    # 左箭头
    draw.polygon([(8,y),(14,y-5),(14,y+5)], fill=col)
    # 右箭头
    draw.polygon([(SIZE-8,y),(SIZE-14,y-5),(SIZE-14,y+5)], fill=col)
    img.save("assets/special_row.png")
    print("saved assets/special_row.png")

# 纵消箭头层
def make_col_arrow():
    img = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    cx = cy = SIZE // 2
    x = cx + 16
    col = (100, 210, 255, 230)
    draw.line([(x, 8), (x, SIZE-8)], fill=col, width=3)
    draw.polygon([(x,8),(x-5,14),(x+5,14)], fill=col)
    draw.polygon([(x,SIZE-8),(x-5,SIZE-14),(x+5,SIZE-14)], fill=col)
    img.save("assets/special_col.png")
    print("saved assets/special_col.png")

# 炸弹光晕层（只有一圈红色光晕，实际炸弹红光用代码实时绘制）
def make_bomb_overlay():
    img = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    cx = cy = SIZE // 2
    r = SIZE // 2 - 1
    # 多层红色光晕
    for i in range(5, 0, -1):
        alpha = 15 + i*12
        draw.ellipse([cx-r+i, cy-r+i, cx+r-i, cy+r-i],
                     outline=(255, 60, 30, alpha), width=2)
    # 炸弹符号（菱形）
    d = 9
    draw.polygon([(cx,cy-d),(cx+d,cy),(cx,cy+d),(cx-d,cy)],
                 outline=(255,80,40,200), width=2)
    draw.ellipse([cx-3,cy-3,cx+3,cy+3], fill=(255,80,40,200))
    img.save("assets/special_bomb.png")
    print("saved assets/special_bomb.png")

# 彩虹层（7彩色光点环）
def make_rainbow_overlay():
    img = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    cx = cy = SIZE // 2
    colors = [
        (255,60,60,220),(255,150,30,220),(255,230,30,220),
        (60,210,60,220),(40,160,255,220),(100,80,255,220),(220,60,220,220)
    ]
    r_ring = 17
    for i, col in enumerate(colors):
        angle = math.radians(i * 360/7)
        px = int(cx + math.cos(angle) * r_ring)
        py = int(cy + math.sin(angle) * r_ring)
        draw.ellipse([px-4,py-4,px+4,py+4], fill=col)
    # 中心白点
    draw.ellipse([cx-5,cy-5,cx+5,cy+5], fill=(255,255,255,230))
    img.save("assets/special_rainbow.png")
    print("saved assets/special_rainbow.png")

make_row_arrow()
make_col_arrow()
make_bomb_overlay()
make_rainbow_overlay()

# ── 验证 ──────────────────────────────────────────────────
files = os.listdir("assets")
print(f"\n✓ 共生成 {len(files)} 个素材文件:")
for f in sorted(files):
    path = f"assets/{f}"
    size = os.path.getsize(path)
    print(f"  {f}  ({size} bytes)")