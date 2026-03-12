"""
摸鱼阅读器 v6.0  —  章节滚动模式
  · 每章完整显示，鼠标滚轮在章内自由滚动
  · 点击文字区左侧 38% → 上一章
  · 点击文字区右侧 62% → 下一章
  · 底部 ◀ ▶ 按钮 / ← → 键 切换章节
  · S 键滚动到下一屏
运行：python novel_reader.py
打包：pip install pyinstaller
      pyinstaller --onefile --windowed --name 摸鱼阅读器 novel_reader.py
屏幕取色需要 Pillow：pip install pillow
"""

import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
import os, re, zipfile, sys, json
from html.parser import HTMLParser


# ══════════════════════════════════════════════════════════════
# HTML → 纯文本
# ══════════════════════════════════════════════════════════════
class _H2T(HTMLParser):
    SKIP  = {'script','style','head','meta','link'}
    BLOCK = {'p','div','br','h1','h2','h3','h4','h5',
             'h6','li','tr','td','th','section','article'}
    def __init__(self):
        super().__init__()
        self.out, self._s = [], 0
    def handle_starttag(self, tag, _):
        if tag in self.SKIP:  self._s += 1
        if tag in self.BLOCK: self.out.append('\n')
    def handle_endtag(self, tag):
        if tag in self.SKIP:  self._s = max(0, self._s - 1)
        if tag in self.BLOCK: self.out.append('\n')
    def handle_data(self, d):
        if not self._s: self.out.append(d)
    def text(self):
        return re.sub(r'\n{3,}', '\n\n', ''.join(self.out)).strip()

def html2text(s):
    p = _H2T()
    try: p.feed(s)
    except: pass
    return p.text()


# ══════════════════════════════════════════════════════════════
# EPUB
# ══════════════════════════════════════════════════════════════
def read_epub(path):
    import xml.etree.ElementTree as ET
    title = os.path.splitext(os.path.basename(path))[0]
    body  = ''
    try:
        with zipfile.ZipFile(path) as z:
            ns = z.namelist()
            opf, odir = '', ''
            if 'META-INF/container.xml' in ns:
                for el in ET.fromstring(z.read('META-INF/container.xml')).iter():
                    if el.tag.endswith('rootfile'):
                        opf  = el.get('full-path', '')
                        odir = opf.rsplit('/', 1)[0] if '/' in opf else ''
                        break
            items, spine = {}, []
            if opf and opf in ns:
                root = ET.fromstring(z.read(opf))
                for el in root.iter():
                    tag = el.tag.split('}')[-1]
                    if tag == 'item':
                        mid  = el.get('id','')
                        href = el.get('href','')
                        mt   = el.get('media-type','')
                        if href and ('html' in mt or href.endswith(('.html','.xhtml','.htm'))):
                            items[mid] = (odir+'/'+href).lstrip('/') if odir else href
                    elif tag == 'itemref':
                        r = el.get('idref','')
                        if r in items: spine.append(items[r])
                    elif tag == 'title' and el.text:
                        title = el.text
            if not spine:
                spine = sorted(f for f in ns
                               if re.search(r'\.(html|htm|xhtml)$', f, re.I)
                               and 'toc' not in f.lower() and 'nav' not in f.lower())
            for href in spine:
                if href in ns:
                    try: body += html2text(z.read(href).decode('utf-8','replace')) + '\n\n'
                    except: pass
    except Exception as e:
        body = f'[EPUB解析失败: {e}]'
    return title, body.strip()


# ══════════════════════════════════════════════════════════════
# 章节切割
# ══════════════════════════════════════════════════════════════
_CH = re.compile(
    r'^(第\s*[零一二三四五六七八九十百千万\d〇]+\s*[章节卷集回部篇][^\n]{0,40}'
    r'|Chapter\s*\d+[^\n]{0,40}'
    r'|CHAPTER\s*\d+[^\n]{0,40}'
    r'|【[^\n]{1,30}】)', re.I)

def split_chapters(text):
    """
    把全文按章节标题切割，返回 [{'title':str, 'body':str}]
    若无章节标题，整本作为一章。
    """
    boundaries = []   # (char_pos, title)
    for m in re.finditer(r'^.+$', text, re.M):
        line = m.group().strip()
        if line and _CH.match(line):
            boundaries.append((m.start(), line))

    if not boundaries:
        return [{'title': '全文', 'body': text}]

    chapters = []
    for i, (pos, title) in enumerate(boundaries):
        end = boundaries[i+1][0] if i+1 < len(boundaries) else len(text)
        chapters.append({'title': title, 'body': text[pos:end]})
    return chapters


# ══════════════════════════════════════════════════════════════
# 书签
# ══════════════════════════════════════════════════════════════
BM_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        '.moyu_bookmarks.json')

def bm_load():
    try:
        with open(BM_FILE, encoding='utf-8') as f: return json.load(f)
    except: return {}

def bm_save(d):
    try:
        with open(BM_FILE, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except: pass


# ══════════════════════════════════════════════════════════════
# 屏幕取色器
# ══════════════════════════════════════════════════════════════
def screen_color_picker(callback):
    try:
        from PIL import ImageGrab
    except ImportError:
        c = colorchooser.askcolor(title='选择颜色')
        if c and c[1]: callback(c[1])
        return

    from PIL import ImageGrab, Image, ImageTk

    ZOOM = 10
    HALF = 5
    CS   = (HALF*2+1) * ZOOM   # canvas size = 110

    preview = tk.Toplevel()
    preview.overrideredirect(True)
    preview.attributes('-topmost', True)
    preview.configure(bg='#1a1a1a')
    preview.geometry(f'{CS+4}x{CS+28}+200+200')

    canvas = tk.Canvas(preview, width=CS, height=CS, bg='#000',
                       highlightthickness=1, highlightbackground='#555',
                       cursor='none')
    canvas.pack(padx=2, pady=(2,0))
    lbl = tk.Label(preview, text='#000000', font=('Consolas',9,'bold'),
                   bg='#1a1a1a', fg='white', pady=1)
    lbl.pack()

    cur  = ['#000000']
    ph   = [None]
    aid  = [None]
    done = [False]

    def update():
        if done[0]: return
        try:
            mx, my = preview.winfo_pointerx(), preview.winfo_pointery()
            box = (mx-HALF, my-HALF, mx+HALF+1, my+HALF+1)
            img    = ImageGrab.grab(bbox=box)
            zoomed = img.resize((CS, CS), Image.NEAREST)
            ph[0]  = ImageTk.PhotoImage(zoomed)
            canvas.delete('all')
            canvas.create_image(0, 0, anchor='nw', image=ph[0])
            c2 = CS // 2
            canvas.create_line(c2, 0, c2, CS, fill='white', width=1)
            canvas.create_line(0, c2, CS, c2, fill='white', width=1)
            canvas.create_rectangle(c2-ZOOM, c2-ZOOM, c2+ZOOM, c2+ZOOM,
                                     outline='white', width=2)
            px = img.getpixel((HALF, HALF))
            hx = '#{:02x}{:02x}{:02x}'.format(px[0], px[1], px[2])
            cur[0] = hx
            lbl.config(text=hx)
            sw, sh = preview.winfo_screenwidth(), preview.winfo_screenheight()
            ox, oy = mx+18, my+18
            if ox+CS+10 > sw: ox = mx-CS-22
            if oy+CS+32 > sh: oy = my-CS-34
            preview.geometry(f'+{ox}+{oy}')
        except: pass
        aid[0] = preview.after(40, update)

    def finish():
        done[0] = True
        if aid[0]:
            try: preview.after_cancel(aid[0])
            except: pass
        for w in (overlay, preview):
            try: w.destroy()
            except: pass

    def on_pick(e):
        color = cur[0]; finish(); callback(color)

    def on_cancel(e=None):
        finish()

    overlay = tk.Toplevel()
    overlay.overrideredirect(True)
    overlay.attributes('-topmost', True)
    overlay.attributes('-alpha', 0.01)
    sw = overlay.winfo_screenwidth()
    sh = overlay.winfo_screenheight()
    overlay.geometry(f'{sw}x{sh}+0+0')
    overlay.configure(bg='white', cursor='crosshair')
    overlay.bind('<Button-1>', on_pick)
    overlay.bind('<Escape>',   on_cancel)
    overlay.focus_force()

    aid[0] = preview.after(40, update)


# ══════════════════════════════════════════════════════════════
# 主程序
# ══════════════════════════════════════════════════════════════
class App:

    THEMES = {
        '暖黄': dict(bg='#fdf6e3', fg='#3c3836', bar='#ebdbb2', sel='#d5c4a1'),
        '夜间': dict(bg='#1e1e2e', fg='#cdd6f4', bar='#181825', sel='#313244'),
        '护眼': dict(bg='#1a2f1a', fg='#a8d5a2', bar='#152315', sel='#2d5a2d'),
        '纸张': dict(bg='#f5f0e8', fg='#2c2416', bar='#ede4d0', sel='#c8b89a'),
        '白底': dict(bg='#ffffff', fg='#1a1a1a', bar='#f0f0f0', sel='#dddddd'),
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title('摸鱼阅读器')
        self.root.geometry('420x560')
        self.root.minsize(300, 340)
        self.root.attributes('-topmost', True)

        # 书籍数据
        self.book_path   = ''
        self.book_title  = ''
        self.chapters    = []    # [{'title':str, 'body':str}]
        self.cur_ch      = 0    # 当前章节索引
        self.bookmarks   = bm_load()

        # UI 状态
        self.theme_name     = '暖黄'
        self.custom_bg      = None
        self.custom_bar     = None
        self.font_size      = 14
        self.line_spacing   = 6
        self.font_fam       = ('宋体' if sys.platform == 'win32'
                               else 'Songti SC' if sys.platform == 'darwin'
                               else 'Noto Serif CJK SC')
        self._d_held        = False
        self._minimized     = False
        self._settings_open = False
        # 滚轮累计，用于判断翻章节
        self._wheel_accum   = 0

        self._build_ui()
        self._apply_theme()
        self._bind_keys()
        self.root.mainloop()

    # ─────────────────────────────────────────────────
    # UI 构建
    # ─────────────────────────────────────────────────
    def _build_ui(self):
        r = self.root

        # 顶部栏
        self.topbar = tk.Frame(r, height=30)
        self.topbar.pack(fill='x')
        self.topbar.pack_propagate(False)

        dots = tk.Frame(self.topbar)
        dots.pack(side='left', padx=6, pady=5)
        self._dot(dots, '#ff5f57', self.toggle_minimize)
        self._dot(dots, '#ffbd2e', self.toggle_settings)
        self._dot(dots, '#28ca41', self.open_file)

        self.lbl_title = tk.Label(self.topbar, text='摸鱼阅读器', font=('', 9))
        self.lbl_title.pack(side='left', fill='x', expand=True)

        rbf = tk.Frame(self.topbar)
        rbf.pack(side='right', padx=4)
        for lbl, cmd in [('书签', self.open_bookmarks),
                          ('目录', self.open_chapters),
                          ('打开', self.open_file),
                          ('×',   r.destroy)]:
            tk.Button(rbf, text=lbl, font=('', 8), relief='flat',
                      padx=3, command=cmd).pack(side='left', padx=1)

        for w in (self.topbar, self.lbl_title):
            w.bind('<ButtonPress-1>', self._drag_start)
            w.bind('<B1-Motion>',     self._drag_move)

        # 设置栏（默认隐藏）
        self.setbar = tk.Frame(r)
        self._build_setbar()

        # 分隔线
        self.sep = tk.Frame(r, height=1)
        self.sep.pack(fill='x')

        # ── 文本区（带滚动条）─────────────────────────
        self.txt_frame = tk.Frame(r)
        self.txt_frame.pack(fill='both', expand=True)

        # 竖向滚动条（细，紧贴右边）
        self.vsb = tk.Scrollbar(self.txt_frame, orient='vertical', width=6)
        self.vsb.pack(side='right', fill='y')

        self.txt = tk.Text(
            self.txt_frame, wrap='word',
            relief='flat', padx=16, pady=10,
            state='disabled', cursor='arrow',
            font=(self.font_fam, self.font_size),
            borderwidth=0, highlightthickness=0,
            spacing1=self.line_spacing,
            spacing2=self.line_spacing // 2,
            spacing3=self.line_spacing,
            yscrollcommand=self.vsb.set,
        )
        self.txt.pack(side='left', fill='both', expand=True)
        self.vsb.config(command=self.txt.yview)

        self.txt.bind('<Button-1>',   self._on_click)
        self.txt.bind('<MouseWheel>', self._on_wheel)     # Windows / macOS
        self.txt.bind('<Button-4>',   self._on_wheel)     # Linux scroll up
        self.txt.bind('<Button-5>',   self._on_wheel)     # Linux scroll down

        self._show_welcome()

        # 底部导航
        self.botbar = tk.Frame(r, height=26)
        self.botbar.pack(fill='x', side='bottom')
        self.botbar.pack_propagate(False)

        self.btn_prev = tk.Button(self.botbar, text='◀ 上章', font=('', 8),
                                  relief='flat', padx=5, command=self.prev_chapter)
        self.btn_prev.pack(side='left', padx=6, pady=3)

        self.lbl_prog = tk.Label(self.botbar, text='', font=('', 8))
        self.lbl_prog.pack(side='left', expand=True)

        self.btn_bm = tk.Button(self.botbar, text='🔖', font=('', 9),
                                relief='flat', padx=2, command=self.add_bookmark)
        self.btn_bm.pack(side='right', padx=2, pady=3)

        self.btn_next = tk.Button(self.botbar, text='下章 ▶', font=('', 8),
                                  relief='flat', padx=5, command=self.next_chapter)
        self.btn_next.pack(side='right', padx=6, pady=3)

    def _dot(self, p, color, cmd):
        lb = tk.Label(p, text='⬤', fg=color, font=('', 12), cursor='hand2')
        lb.pack(side='left', padx=2)
        lb.bind('<Button-1>', lambda e: cmd())

    def _build_setbar(self):
        r1 = tk.Frame(self.setbar); r1.pack(fill='x', padx=8, pady=2)
        tk.Label(r1, text='字号', font=('',8)).pack(side='left')
        self.sl_font = tk.Scale(r1, from_=10, to=32, orient='horizontal',
                                length=70, showvalue=True, font=('',7),
                                command=self._on_font_size)
        self.sl_font.set(self.font_size)
        self.sl_font.pack(side='left', padx=2)

        tk.Label(r1, text='行距', font=('',8)).pack(side='left', padx=(8,0))
        self.sl_spacing = tk.Scale(r1, from_=0, to=24, orient='horizontal',
                                   length=70, showvalue=True, font=('',7),
                                   command=self._on_spacing)
        self.sl_spacing.set(self.line_spacing)
        self.sl_spacing.pack(side='left', padx=2)

        r2 = tk.Frame(self.setbar); r2.pack(fill='x', padx=8, pady=2)
        tk.Label(r2, text='透明', font=('',8)).pack(side='left')
        self.sl_alpha = tk.Scale(r2, from_=20, to=100, orient='horizontal',
                                 length=80, showvalue=True, font=('',7),
                                 command=lambda v: self.root.attributes('-alpha', int(v)/100))
        self.sl_alpha.set(100)
        self.sl_alpha.pack(side='left', padx=2)

        r3 = tk.Frame(self.setbar); r3.pack(fill='x', padx=8, pady=2)
        tk.Label(r3, text='字色', font=('',8)).pack(side='left')
        self.btn_fg_color = tk.Button(r3, text='  ', relief='groove', width=2,
                                      font=('',8), command=self._pick_fg)
        self.btn_fg_color.pack(side='left', padx=2)

        tk.Label(r3, text='背景', font=('',8)).pack(side='left', padx=(6,0))
        self.btn_bg_color = tk.Button(r3, text='  ', relief='groove', width=2,
                                      font=('',8), command=self._pick_bg)
        self.btn_bg_color.pack(side='left', padx=2)

        tk.Button(r3, text='🎨取色', font=('',8), relief='flat',
                  padx=4, command=self._screen_pick).pack(side='left', padx=4)
        tk.Button(r3, text='重置', font=('',8), relief='flat',
                  padx=4, command=self._reset_colors).pack(side='left', padx=2)

        r4 = tk.Frame(self.setbar); r4.pack(fill='x', padx=8, pady=2)
        tk.Label(r4, text='主题', font=('',8)).pack(side='left')
        self.var_theme = tk.StringVar(value=self.theme_name)
        cb = ttk.Combobox(r4, textvariable=self.var_theme,
                          values=list(self.THEMES.keys()),
                          width=7, font=('',8), state='readonly')
        cb.pack(side='left', padx=4)
        cb.bind('<<ComboboxSelected>>', self._on_theme)

    # ─────────────────────────────────────────────────
    # 颜色 / 主题
    # ─────────────────────────────────────────────────
    def _pick_fg(self):
        t = self._cur_theme()
        c = colorchooser.askcolor(color=t['fg'], title='选择字体颜色')
        if c and c[1]:
            self.THEMES[self.theme_name]['fg'] = c[1]
            self.txt.config(fg=c[1])
            self.btn_fg_color.config(bg=c[1])

    def _pick_bg(self):
        c = colorchooser.askcolor(color=self._cur_theme()['bg'], title='选择背景颜色')
        if c and c[1]: self._apply_custom_bg(c[1])

    def _screen_pick(self):
        alpha = self.sl_alpha.get() / 100
        self.root.attributes('-alpha', 0.0)
        def on_color(hx):
            self.root.after(100, lambda: self.root.attributes('-alpha', alpha))
            self._apply_custom_bg(hx)
        self.root.after(120, lambda: screen_color_picker(on_color))

    def _apply_custom_bg(self, hx):
        self.custom_bg  = hx
        self.custom_bar = self._darken(hx, 0.88)
        self._apply_theme()
        try: self.btn_bg_color.config(bg=hx)
        except: pass

    def _reset_colors(self):
        self.custom_bg = self.custom_bar = None
        self._apply_theme()

    def _darken(self, hx, f=0.88):
        h = hx.lstrip('#')
        return '#{:02x}{:02x}{:02x}'.format(
            int(int(h[0:2],16)*f), int(int(h[2:4],16)*f), int(int(h[4:6],16)*f))

    def _cur_theme(self):
        import copy
        t = copy.copy(self.THEMES[self.theme_name])
        if self.custom_bg:  t['bg']  = self.custom_bg
        if self.custom_bar: t['bar'] = self.custom_bar
        return t

    def _on_theme(self, e=None):
        self.theme_name = self.var_theme.get()
        self.custom_bg = self.custom_bar = None
        self._apply_theme()

    def _apply_theme(self):
        t = self._cur_theme()
        bg, fg, bar, sel = t['bg'], t['fg'], t['bar'], t['sel']
        self.root.configure(bg=bar)
        self._cf(self.topbar, bar, fg)
        self._cf(self.botbar, bar, fg)
        self.sep.config(bg=sel)
        self.txt_frame.config(bg=bg)
        self.vsb.config(bg=bar, troughcolor=bg, activebackground=sel)
        self.txt.config(bg=bg, fg=fg, insertbackground=fg, selectbackground=sel)
        self.lbl_prog.config(bg=bar, fg=fg)
        self.btn_bm.config(bg=bar, fg=fg, activebackground=sel)
        for b in (self.btn_prev, self.btn_next):
            b.config(bg=bar, fg=fg, activebackground=sel)
        self._retheme_setbar()
        try:
            if self.custom_bg: self.btn_bg_color.config(bg=self.custom_bg)
        except: pass

    def _cf(self, fr, bg, fg):
        try: fr.config(bg=bg)
        except: pass
        for w in fr.winfo_children():
            try: w.config(bg=bg, fg=fg, activebackground=bg)
            except: pass
            for w2 in w.winfo_children():
                try: w2.config(bg=bg, fg=fg, activebackground=bg)
                except: pass

    def _retheme_setbar(self):
        t = self._cur_theme()
        bg, fg, sel = t['bar'], t['fg'], t['sel']
        self._cf(self.setbar, bg, fg)
        for sl in (self.sl_font, self.sl_alpha, self.sl_spacing):
            try: sl.config(bg=bg, fg=fg, troughcolor=sel, activebackground=sel)
            except: pass
        try: self.btn_fg_color.config(bg=fg)
        except: pass

    # ─────────────────────────────────────────────────
    # 拖动窗口
    # ─────────────────────────────────────────────────
    def _drag_start(self, e):
        self._dx = e.x_root - self.root.winfo_x()
        self._dy = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        self.root.geometry(f'+{e.x_root-self._dx}+{e.y_root-self._dy}')

    # ─────────────────────────────────────────────────
    # 打开文件
    # ─────────────────────────────────────────────────
    def open_file(self):
        path = filedialog.askopenfilename(
            title='打开小说',
            filetypes=[('小说文件','*.txt *.epub *.md'),('所有文件','*.*')]
        )
        if not path: return
        ext = os.path.splitext(path)[1].lower()
        if ext == '.epub':
            title, text = read_epub(path)
        else:
            title = os.path.splitext(os.path.basename(path))[0]
            try:
                with open(path, encoding='utf-8', errors='replace') as f:
                    text = f.read()
            except Exception as e:
                messagebox.showerror('错误', str(e)); return

        self.book_path  = path
        self.book_title = title
        self.lbl_title.config(text=f'  {title}')
        self.root.title(f'摸鱼阅读器 — {title}')
        self._load(text, restore_bm=True)

    def _load(self, text, restore_bm=False):
        self.chapters = split_chapters(text)
        self.cur_ch   = 0
        if restore_bm and self.book_path in self.bookmarks:
            saved = self.bookmarks[self.book_path].get('chapter', 0)
            self.cur_ch = max(0, min(saved, len(self.chapters)-1))
        self._render_chapter()

    # ─────────────────────────────────────────────────
    # 渲染章节（核心：直接把整章文本塞进 Text）
    # ─────────────────────────────────────────────────
    def _render_chapter(self, scroll_to_top=True):
        if not self.chapters: return
        self.cur_ch = max(0, min(self.cur_ch, len(self.chapters)-1))
        ch = self.chapters[self.cur_ch]

        self.txt.config(state='normal')
        self.txt.delete('1.0', 'end')
        self.txt.insert('1.0', ch['body'])
        self.txt.config(state='disabled')

        if scroll_to_top:
            self.txt.yview_moveto(0.0)

        self._update_nav()
        self._wheel_accum = 0

    def _update_nav(self):
        n   = len(self.chapters)
        idx = self.cur_ch + 1
        self.lbl_prog.config(text=f'第 {idx} / {n} 章')
        self.btn_prev.config(state='normal' if self.cur_ch > 0   else 'disabled')
        self.btn_next.config(state='normal' if self.cur_ch < n-1 else 'disabled')

    # ─────────────────────────────────────────────────
    # 章节切换
    # ─────────────────────────────────────────────────
    def next_chapter(self):
        if self.chapters and self.cur_ch < len(self.chapters)-1:
            self.cur_ch += 1
            self._render_chapter(scroll_to_top=True)

    def prev_chapter(self):
        if self.chapters and self.cur_ch > 0:
            self.cur_ch -= 1
            self._render_chapter(scroll_to_top=True)

    def goto_chapter(self, idx):
        if not self.chapters: return
        self.cur_ch = max(0, min(idx, len(self.chapters)-1))
        self._render_chapter(scroll_to_top=True)

    # ─────────────────────────────────────────────────
    # 点击：左侧上章 / 右侧下章（忽略中间 38%~62% 区域）
    # ─────────────────────────────────────────────────
    def _on_click(self, e):
        w = self.txt.winfo_width()
        if   e.x < w * 0.30:
            self.prev_chapter()
        elif e.x > w * 0.70:
            self.next_chapter()
        # 中间区域：不响应（方便选文字）

    # ─────────────────────────────────────────────────
    # 滚轮：章内正常滚动；到达顶/底时累计后切章
    # ─────────────────────────────────────────────────
    def _on_wheel(self, e):
        # 判断滚动方向
        if e.num == 4:          # Linux up
            delta = 1
        elif e.num == 5:        # Linux down
            delta = -1
        else:
            delta = 1 if e.delta > 0 else -1   # Windows/macOS

        # 当前滚动位置 (top_frac, bottom_frac)
        top, bot = self.txt.yview()

        if delta < 0:   # 向下滚
            if bot >= 0.999:
                # 已在底部，累计后切下一章
                self._wheel_accum -= 1
                if self._wheel_accum <= -3:
                    self.next_chapter()
                    return
            else:
                self._wheel_accum = 0
                self.txt.yview_scroll(3, 'units')
        else:           # 向上滚
            if top <= 0.001:
                # 已在顶部，累计后切上一章
                self._wheel_accum += 1
                if self._wheel_accum >= 3:
                    self.prev_chapter()
                    # 切到上章后滚动到底部
                    self.root.after(30, lambda: self.txt.yview_moveto(1.0))
                    return
            else:
                self._wheel_accum = 0
                self.txt.yview_scroll(-3, 'units')

    # ─────────────────────────────────────────────────
    # S 键：向下翻一屏
    # ─────────────────────────────────────────────────
    def _scroll_down_screen(self):
        top, bot = self.txt.yview()
        if bot >= 0.999:
            self.next_chapter()
        else:
            self.txt.yview_scroll(1, 'pages')

    # ─────────────────────────────────────────────────
    # 欢迎页
    # ─────────────────────────────────────────────────
    def _show_welcome(self):
        self.txt.config(state='normal')
        self.txt.delete('1.0','end')
        self.txt.insert('1.0', (
            '\n\n\n\n'
            '       📚  摸鱼阅读器\n\n'
            '  支持：TXT  /  EPUB  /  MD\n\n'
            '  ● 右上角 [打开] 选择文件\n'
            '  ● 绿色圆点 快速打开\n'
            '  ● 黄色圆点 打开设置\n\n'
            '  操作方式：\n'
            '    滚轮          章内上下滚动\n'
            '    滚轮到底/顶   自动切换章节\n'
            '    点击左侧 30%  上一章\n'
            '    点击右侧 30%  下一章\n'
            '    S / ↓         向下翻一屏\n'
            '    ← / →         切换章节\n'
            '    D + E         最小化\n'
        ))
        self.txt.config(state='disabled')

    # ─────────────────────────────────────────────────
    # 最小化
    # ─────────────────────────────────────────────────
    def toggle_minimize(self):
        self._minimized = not self._minimized
        if self._minimized:
            self._saved_h = self.root.winfo_height()
            for w in (self.setbar, self.sep, self.txt_frame, self.botbar):
                w.pack_forget()
            self.root.geometry(f'{self.root.winfo_width()}x30')
        else:
            self.root.geometry(f'{self.root.winfo_width()}x{self._saved_h}')
            self.sep.pack(fill='x', after=self.topbar)
            if self._settings_open:
                self.setbar.pack(fill='x', after=self.topbar)
                self._retheme_setbar()
            self.txt_frame.pack(fill='both', expand=True)
            self.botbar.pack(fill='x', side='bottom')

    # ─────────────────────────────────────────────────
    # 设置栏
    # ─────────────────────────────────────────────────
    def toggle_settings(self):
        self._settings_open = not self._settings_open
        if self._settings_open:
            self.setbar.pack(fill='x', after=self.topbar)
            self._retheme_setbar()
        else:
            self.setbar.pack_forget()

    def _on_font_size(self, val):
        self.font_size = int(float(val))
        self.txt.config(font=(self.font_fam, self.font_size))

    def _on_spacing(self, val):
        self.line_spacing = int(float(val))
        sp = self.line_spacing
        self.txt.config(spacing1=sp, spacing2=sp//2, spacing3=sp)

    # ─────────────────────────────────────────────────
    # 章节目录
    # ─────────────────────────────────────────────────
    def open_chapters(self):
        if not self.chapters:
            messagebox.showinfo('提示','请先打开一本小说'); return

        t  = self._cur_theme()
        bg, fg, bar, sel = t['bg'], t['fg'], t['bar'], t['sel']

        win = tk.Toplevel(self.root)
        win.title('章节目录')
        win.geometry('300x480')
        win.resizable(True, True)
        win.attributes('-topmost', True)
        win.configure(bg=bg)

        hdr = tk.Frame(win, bg=bar, height=28)
        hdr.pack(fill='x'); hdr.pack_propagate(False)
        tk.Label(hdr, text='📑 章节目录', font=('',9,'bold'),
                 bg=bar, fg=fg).pack(side='left', padx=8, pady=4)
        tk.Button(hdr, text='×', relief='flat', font=('',10),
                  bg=bar, fg=fg, command=win.destroy).pack(side='right', padx=6)

        # 搜索
        sf = tk.Frame(win, bg=bg); sf.pack(fill='x', padx=6, pady=(6,2))
        sv = tk.StringVar()
        se = tk.Entry(sf, textvariable=sv, font=('',9), bg=bg, fg=fg,
                      insertbackground=fg, relief='groove')
        se.pack(fill='x', ipady=3)
        PH = '搜索章节名...'
        se.insert(0, PH); se.config(fg='gray')
        se.bind('<FocusIn>',  lambda e:(se.delete(0,'end'),se.config(fg=fg)) if se.get()==PH else None)
        se.bind('<FocusOut>', lambda e:(se.insert(0,PH),se.config(fg='gray')) if not se.get() else None)

        # 列表
        lf = tk.Frame(win, bg=bg); lf.pack(fill='both', expand=True, padx=4, pady=4)
        sb2 = tk.Scrollbar(lf); sb2.pack(side='right', fill='y')
        lb = tk.Listbox(lf, font=('',10), relief='flat', bg=bg, fg=fg,
                        selectbackground=sel, selectforeground=fg,
                        borderwidth=0, highlightthickness=0,
                        activestyle='none', yscrollcommand=sb2.set)
        lb.pack(fill='both', expand=True); sb2.config(command=lb.yview)

        btn_j = tk.Button(win, text='↩  跳转到选中章节', font=('',9,'bold'),
                          bg=bar, fg=fg, relief='flat', pady=5)
        btn_j.pack(fill='x', padx=6, pady=4)

        all_ch  = list(self.chapters)   # [{'title','body'}]
        visible = list(range(len(all_ch)))  # 存索引

        def fill(indices):
            visible.clear(); visible.extend(indices)
            lb.delete(0,'end')
            for i in indices:
                lb.insert('end', f'  {i+1}. {all_ch[i]["title"]}')

        fill(range(len(all_ch)))
        # 高亮当前
        try: lb.see(self.cur_ch); lb.selection_set(self.cur_ch)
        except: pass

        def on_search(*_):
            q = sv.get().strip()
            if q in ('', PH):
                fill(range(len(all_ch)))
            else:
                fill([i for i,c in enumerate(all_ch) if q in c['title']])
        sv.trace_add('write', on_search)

        def jump(event=None):
            idxs = lb.curselection()
            if not idxs: return
            real_idx = visible[idxs[0]]
            win.destroy()
            self.goto_chapter(real_idx)

        btn_j.config(command=jump)
        lb.bind('<Double-Button-1>', jump)
        lb.bind('<Return>', jump)

        rx = self.root.winfo_x() + self.root.winfo_width() + 8
        ry = self.root.winfo_y()
        win.geometry(f'300x480+{rx}+{ry}')

    # ─────────────────────────────────────────────────
    # 书签
    # ─────────────────────────────────────────────────
    def add_bookmark(self):
        if not self.book_path:
            messagebox.showinfo('提示','请先打开一本小说'); return
        ch = self.chapters[self.cur_ch] if self.chapters else {}
        self.bookmarks[self.book_path] = {
            'title':    self.book_title,
            'chapter':  self.cur_ch,
            'total':    len(self.chapters),
            'ch_title': ch.get('title',''),
            'path':     self.book_path,
        }
        bm_save(self.bookmarks)
        n = len(self.chapters)
        messagebox.showinfo('🔖 书签',
            f'已保存\n第 {self.cur_ch+1} / {n} 章\n{ch.get("title","")}')

    def open_bookmarks(self):
        if not self.bookmarks:
            messagebox.showinfo('书签','暂无书签'); return
        t  = self._cur_theme()
        bg, fg, bar, sel = t['bg'], t['fg'], t['bar'], t['sel']

        win = tk.Toplevel(self.root)
        win.title('书签'); win.geometry('320x300')
        win.resizable(True,True); win.attributes('-topmost',True)
        win.configure(bg=bg)

        hdr = tk.Frame(win, bg=bar, height=28)
        hdr.pack(fill='x'); hdr.pack_propagate(False)
        tk.Label(hdr, text='🔖 书签列表', font=('',9,'bold'),
                 bg=bar, fg=fg).pack(side='left', padx=8, pady=4)
        tk.Button(hdr, text='×', relief='flat', font=('',10),
                  bg=bar, fg=fg, command=win.destroy).pack(side='right', padx=6)

        lf = tk.Frame(win, bg=bg); lf.pack(fill='both', expand=True, padx=4, pady=4)
        sb2 = tk.Scrollbar(lf); sb2.pack(side='right', fill='y')
        lb = tk.Listbox(lf, font=('',10), relief='flat', bg=bg, fg=fg,
                        selectbackground=sel, selectforeground=fg,
                        borderwidth=0, highlightthickness=0,
                        activestyle='none', yscrollcommand=sb2.set)
        lb.pack(fill='both', expand=True); sb2.config(command=lb.yview)

        keys = list(self.bookmarks.keys())
        for k in keys:
            bm = self.bookmarks[k]
            s  = f"  {bm['title']}  第{bm['chapter']+1}章"
            if bm.get('ch_title'): s += f"  ·  {bm['ch_title']}"
            lb.insert('end', s)

        bf = tk.Frame(win, bg=bar); bf.pack(fill='x', padx=6, pady=4)

        def goto_bm():
            idxs = lb.curselection()
            if not idxs: return
            bm = self.bookmarks[keys[idxs[0]]]
            win.destroy()
            if bm['path'] != self.book_path:
                ext = os.path.splitext(bm['path'])[1].lower()
                try:
                    if ext == '.epub': _t, text = read_epub(bm['path'])
                    else:
                        with open(bm['path'],encoding='utf-8',errors='replace') as f: text=f.read()
                except:
                    messagebox.showerror('错误','文件不存在或已移动'); return
                self.book_path = bm['path']; self.book_title = bm['title']
                self.lbl_title.config(text=f"  {bm['title']}")
                self.root.title(f"摸鱼阅读器 — {bm['title']}")
                self.chapters = split_chapters(text)
            self.goto_chapter(bm['chapter'])

        def del_bm():
            idxs = lb.curselection()
            if not idxs: return
            k = keys.pop(idxs[0])
            del self.bookmarks[k]; bm_save(self.bookmarks)
            lb.delete(idxs[0])

        tk.Button(bf, text='跳转', font=('',9), bg=bar, fg=fg,
                  relief='flat', padx=8, command=goto_bm).pack(side='left', padx=4)
        tk.Button(bf, text='删除', font=('',9), bg=bar, fg=fg,
                  relief='flat', padx=8, command=del_bm).pack(side='left', padx=4)

        rx = self.root.winfo_x() + self.root.winfo_width() + 8
        ry = self.root.winfo_y()
        win.geometry(f'320x300+{rx}+{ry}')

    # ─────────────────────────────────────────────────
    # 快捷键
    # ─────────────────────────────────────────────────
    def _bind_keys(self):
        r = self.root
        r.bind('<KeyPress-s>',   lambda e: self._scroll_down_screen())
        r.bind('<KeyPress-S>',   lambda e: self._scroll_down_screen())
        r.bind('<Right>',        lambda e: self.next_chapter())
        r.bind('<Left>',         lambda e: self.prev_chapter())
        r.bind('<Down>',         lambda e: self._scroll_down_screen())
        r.bind('<Up>',           lambda e: self.txt.yview_scroll(-3,'units'))
        r.bind('<KeyPress-d>',   self._dp)
        r.bind('<KeyPress-D>',   self._dp)
        r.bind('<KeyRelease-d>', self._dr)
        r.bind('<KeyRelease-D>', self._dr)
        r.bind('<KeyPress-e>',   self._ep)
        r.bind('<KeyPress-E>',   self._ep)
        r.focus_set()

    def _dp(self, e): self._d_held = True
    def _dr(self, e): self._d_held = False
    def _ep(self, e):
        if self._d_held: self.toggle_minimize()


# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    App()