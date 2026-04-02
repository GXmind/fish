# """
# 摸鱼阅读器 v6.0  —  章节滚动模式
#   · 每章完整显示，鼠标滚轮在章内自由滚动
#   · 点击文字区左侧 38% → 上一章
#   · 点击文字区右侧 62% → 下一章
#   · 底部 ◀ ▶ 按钮 / ← → 键 切换章节
#   · S 键滚动到下一屏
# 运行：python novel_reader.py
# 打包：pip install pyinstaller
#       pyinstaller --onefile --windowed --name 摸鱼阅读器 novel_reader.py
# 屏幕取色需要 Pillow：pip install pillow
# """

# import tkinter as tk
# from tkinter import ttk, filedialog, colorchooser, messagebox
# import os, re, zipfile, sys, json
# from html.parser import HTMLParser


# # ══════════════════════════════════════════════════════════════
# # HTML → 纯文本
# # ══════════════════════════════════════════════════════════════
# class _H2T(HTMLParser):
#     SKIP  = {'script','style','head','meta','link'}
#     BLOCK = {'p','div','br','h1','h2','h3','h4','h5',
#              'h6','li','tr','td','th','section','article'}
#     def __init__(self):
#         super().__init__()
#         self.out, self._s = [], 0
#     def handle_starttag(self, tag, _):
#         if tag in self.SKIP:  self._s += 1
#         if tag in self.BLOCK: self.out.append('\n')
#     def handle_endtag(self, tag):
#         if tag in self.SKIP:  self._s = max(0, self._s - 1)
#         if tag in self.BLOCK: self.out.append('\n')
#     def handle_data(self, d):
#         if not self._s: self.out.append(d)
#     def text(self):
#         return re.sub(r'\n{3,}', '\n\n', ''.join(self.out)).strip()

# def html2text(s):
#     p = _H2T()
#     try: p.feed(s)
#     except: pass
#     return p.text()


# # ══════════════════════════════════════════════════════════════
# # EPUB
# # ══════════════════════════════════════════════════════════════
# def read_epub(path):
#     import xml.etree.ElementTree as ET
#     title = os.path.splitext(os.path.basename(path))[0]
#     body  = ''
#     try:
#         with zipfile.ZipFile(path) as z:
#             ns = z.namelist()
#             opf, odir = '', ''
#             if 'META-INF/container.xml' in ns:
#                 for el in ET.fromstring(z.read('META-INF/container.xml')).iter():
#                     if el.tag.endswith('rootfile'):
#                         opf  = el.get('full-path', '')
#                         odir = opf.rsplit('/', 1)[0] if '/' in opf else ''
#                         break
#             items, spine = {}, []
#             if opf and opf in ns:
#                 root = ET.fromstring(z.read(opf))
#                 for el in root.iter():
#                     tag = el.tag.split('}')[-1]
#                     if tag == 'item':
#                         mid  = el.get('id','')
#                         href = el.get('href','')
#                         mt   = el.get('media-type','')
#                         if href and ('html' in mt or href.endswith(('.html','.xhtml','.htm'))):
#                             items[mid] = (odir+'/'+href).lstrip('/') if odir else href
#                     elif tag == 'itemref':
#                         r = el.get('idref','')
#                         if r in items: spine.append(items[r])
#                     elif tag == 'title' and el.text:
#                         title = el.text
#             if not spine:
#                 spine = sorted(f for f in ns
#                                if re.search(r'\.(html|htm|xhtml)$', f, re.I)
#                                and 'toc' not in f.lower() and 'nav' not in f.lower())
#             for href in spine:
#                 if href in ns:
#                     try: body += html2text(z.read(href).decode('utf-8','replace')) + '\n\n'
#                     except: pass
#     except Exception as e:
#         body = f'[EPUB解析失败: {e}]'
#     return title, body.strip()


# # ══════════════════════════════════════════════════════════════
# # 章节切割
# # ══════════════════════════════════════════════════════════════
# _CH = re.compile(
#     r'^(第\s*[零一二三四五六七八九十百千万\d〇]+\s*[章节卷集回部篇][^\n]{0,40}'
#     r'|Chapter\s*\d+[^\n]{0,40}'
#     r'|CHAPTER\s*\d+[^\n]{0,40}'
#     r'|【[^\n]{1,30}】)', re.I)

# def split_chapters(text):
#     """
#     把全文按章节标题切割，返回 [{'title':str, 'body':str}]
#     若无章节标题，整本作为一章。
#     """
#     boundaries = []   # (char_pos, title)
#     for m in re.finditer(r'^.+$', text, re.M):
#         line = m.group().strip()
#         if line and _CH.match(line):
#             boundaries.append((m.start(), line))

#     if not boundaries:
#         return [{'title': '全文', 'body': text}]

#     chapters = []
#     for i, (pos, title) in enumerate(boundaries):
#         end = boundaries[i+1][0] if i+1 < len(boundaries) else len(text)
#         chapters.append({'title': title, 'body': text[pos:end]})
#     return chapters


# # ══════════════════════════════════════════════════════════════
# # 书签
# # ══════════════════════════════════════════════════════════════
# BM_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
#                         '.moyu_bookmarks.json')

# def bm_load():
#     try:
#         with open(BM_FILE, encoding='utf-8') as f: return json.load(f)
#     except: return {}

# def bm_save(d):
#     try:
#         with open(BM_FILE, 'w', encoding='utf-8') as f:
#             json.dump(d, f, ensure_ascii=False, indent=2)
#     except: pass


# # ══════════════════════════════════════════════════════════════
# # 屏幕取色器
# # ══════════════════════════════════════════════════════════════
# def screen_color_picker(callback):
#     try:
#         from PIL import ImageGrab
#     except ImportError:
#         c = colorchooser.askcolor(title='选择颜色')
#         if c and c[1]: callback(c[1])
#         return

#     from PIL import ImageGrab, Image, ImageTk

#     ZOOM = 10
#     HALF = 5
#     CS   = (HALF*2+1) * ZOOM   # canvas size = 110

#     preview = tk.Toplevel()
#     preview.overrideredirect(True)
#     preview.attributes('-topmost', True)
#     preview.configure(bg='#1a1a1a')
#     preview.geometry(f'{CS+4}x{CS+28}+200+200')

#     canvas = tk.Canvas(preview, width=CS, height=CS, bg='#000',
#                        highlightthickness=1, highlightbackground='#555',
#                        cursor='none')
#     canvas.pack(padx=2, pady=(2,0))
#     lbl = tk.Label(preview, text='#000000', font=('Consolas',9,'bold'),
#                    bg='#1a1a1a', fg='white', pady=1)
#     lbl.pack()

#     cur  = ['#000000']
#     ph   = [None]
#     aid  = [None]
#     done = [False]

#     def update():
#         if done[0]: return
#         try:
#             mx, my = preview.winfo_pointerx(), preview.winfo_pointery()
#             box = (mx-HALF, my-HALF, mx+HALF+1, my+HALF+1)
#             img    = ImageGrab.grab(bbox=box)
#             zoomed = img.resize((CS, CS), Image.NEAREST)
#             ph[0]  = ImageTk.PhotoImage(zoomed)
#             canvas.delete('all')
#             canvas.create_image(0, 0, anchor='nw', image=ph[0])
#             c2 = CS // 2
#             canvas.create_line(c2, 0, c2, CS, fill='white', width=1)
#             canvas.create_line(0, c2, CS, c2, fill='white', width=1)
#             canvas.create_rectangle(c2-ZOOM, c2-ZOOM, c2+ZOOM, c2+ZOOM,
#                                      outline='white', width=2)
#             px = img.getpixel((HALF, HALF))
#             hx = '#{:02x}{:02x}{:02x}'.format(px[0], px[1], px[2])
#             cur[0] = hx
#             lbl.config(text=hx)
#             sw, sh = preview.winfo_screenwidth(), preview.winfo_screenheight()
#             ox, oy = mx+18, my+18
#             if ox+CS+10 > sw: ox = mx-CS-22
#             if oy+CS+32 > sh: oy = my-CS-34
#             preview.geometry(f'+{ox}+{oy}')
#         except: pass
#         aid[0] = preview.after(40, update)

#     def finish():
#         done[0] = True
#         if aid[0]:
#             try: preview.after_cancel(aid[0])
#             except: pass
#         for w in (overlay, preview):
#             try: w.destroy()
#             except: pass

#     def on_pick(e):
#         color = cur[0]; finish(); callback(color)

#     def on_cancel(e=None):
#         finish()

#     overlay = tk.Toplevel()
#     overlay.overrideredirect(True)
#     overlay.attributes('-topmost', True)
#     overlay.attributes('-alpha', 0.01)
#     sw = overlay.winfo_screenwidth()
#     sh = overlay.winfo_screenheight()
#     overlay.geometry(f'{sw}x{sh}+0+0')
#     overlay.configure(bg='white', cursor='crosshair')
#     overlay.bind('<Button-1>', on_pick)
#     overlay.bind('<Escape>',   on_cancel)
#     overlay.focus_force()

#     aid[0] = preview.after(40, update)


# # ══════════════════════════════════════════════════════════════
# # 主程序
# # ══════════════════════════════════════════════════════════════
# class App:

#     THEMES = {
#         '暖黄': dict(bg='#fdf6e3', fg='#3c3836', bar='#ebdbb2', sel='#d5c4a1'),
#         '夜间': dict(bg='#1e1e2e', fg='#cdd6f4', bar='#181825', sel='#313244'),
#         '护眼': dict(bg='#1a2f1a', fg='#a8d5a2', bar='#152315', sel='#2d5a2d'),
#         '纸张': dict(bg='#f5f0e8', fg='#2c2416', bar='#ede4d0', sel='#c8b89a'),
#         '白底': dict(bg='#ffffff', fg='#1a1a1a', bar='#f0f0f0', sel='#dddddd'),
#     }

#     def __init__(self):
#         self.root = tk.Tk()
#         self.root.title('摸鱼阅读器')
#         self.root.geometry('420x560')
#         self.root.minsize(300, 340)
#         self.root.attributes('-topmost', True)

#         # 书籍数据
#         self.book_path   = ''
#         self.book_title  = ''
#         self.chapters    = []    # [{'title':str, 'body':str}]
#         self.cur_ch      = 0    # 当前章节索引
#         self.bookmarks   = bm_load()

#         # UI 状态
#         self.theme_name     = '暖黄'
#         self.custom_bg      = None
#         self.custom_bar     = None
#         self.font_size      = 14
#         self.line_spacing   = 6
#         self.font_fam       = ('宋体' if sys.platform == 'win32'
#                                else 'Songti SC' if sys.platform == 'darwin'
#                                else 'Noto Serif CJK SC')
#         self._d_held        = False
#         self._minimized     = False
#         self._settings_open = False
#         # 滚轮累计，用于判断翻章节
#         self._wheel_accum   = 0

#         self._build_ui()
#         self._apply_theme()
#         self._bind_keys()
#         self.root.mainloop()

#     # ─────────────────────────────────────────────────
#     # UI 构建
#     # ─────────────────────────────────────────────────
#     def _build_ui(self):
#         r = self.root

#         # 顶部栏
#         self.topbar = tk.Frame(r, height=30)
#         self.topbar.pack(fill='x')
#         self.topbar.pack_propagate(False)

#         dots = tk.Frame(self.topbar)
#         dots.pack(side='left', padx=6, pady=5)
#         self._dot(dots, '#ff5f57', self.toggle_minimize)
#         self._dot(dots, '#ffbd2e', self.toggle_settings)
#         self._dot(dots, '#28ca41', self.open_file)

#         self.lbl_title = tk.Label(self.topbar, text='摸鱼阅读器', font=('', 9))
#         self.lbl_title.pack(side='left', fill='x', expand=True)

#         rbf = tk.Frame(self.topbar)
#         rbf.pack(side='right', padx=4)
#         for lbl, cmd in [('书签', self.open_bookmarks),
#                           ('目录', self.open_chapters),
#                           ('打开', self.open_file),
#                           ('×',   r.destroy)]:
#             tk.Button(rbf, text=lbl, font=('', 8), relief='flat',
#                       padx=3, command=cmd).pack(side='left', padx=1)

#         for w in (self.topbar, self.lbl_title):
#             w.bind('<ButtonPress-1>', self._drag_start)
#             w.bind('<B1-Motion>',     self._drag_move)

#         # 设置栏（默认隐藏）
#         self.setbar = tk.Frame(r)
#         self._build_setbar()

#         # 分隔线
#         self.sep = tk.Frame(r, height=1)
#         self.sep.pack(fill='x')

#         # ── 文本区（带滚动条）─────────────────────────
#         self.txt_frame = tk.Frame(r)
#         self.txt_frame.pack(fill='both', expand=True)

#         # 竖向滚动条（细，紧贴右边）
#         self.vsb = tk.Scrollbar(self.txt_frame, orient='vertical', width=6)
#         self.vsb.pack(side='right', fill='y')

#         self.txt = tk.Text(
#             self.txt_frame, wrap='word',
#             relief='flat', padx=16, pady=10,
#             state='disabled', cursor='arrow',
#             font=(self.font_fam, self.font_size),
#             borderwidth=0, highlightthickness=0,
#             spacing1=self.line_spacing,
#             spacing2=self.line_spacing // 2,
#             spacing3=self.line_spacing,
#             yscrollcommand=self.vsb.set,
#         )
#         self.txt.pack(side='left', fill='both', expand=True)
#         self.vsb.config(command=self.txt.yview)

#         self.txt.bind('<Button-1>',   self._on_click)
#         self.txt.bind('<MouseWheel>', self._on_wheel)     # Windows / macOS
#         self.txt.bind('<Button-4>',   self._on_wheel)     # Linux scroll up
#         self.txt.bind('<Button-5>',   self._on_wheel)     # Linux scroll down

#         self._show_welcome()

#         # 底部导航
#         self.botbar = tk.Frame(r, height=26)
#         self.botbar.pack(fill='x', side='bottom')
#         self.botbar.pack_propagate(False)

#         self.btn_prev = tk.Button(self.botbar, text='◀ 上章', font=('', 8),
#                                   relief='flat', padx=5, command=self.prev_chapter)
#         self.btn_prev.pack(side='left', padx=6, pady=3)

#         self.lbl_prog = tk.Label(self.botbar, text='', font=('', 8))
#         self.lbl_prog.pack(side='left', expand=True)

#         self.btn_bm = tk.Button(self.botbar, text='🔖', font=('', 9),
#                                 relief='flat', padx=2, command=self.add_bookmark)
#         self.btn_bm.pack(side='right', padx=2, pady=3)

#         self.btn_next = tk.Button(self.botbar, text='下章 ▶', font=('', 8),
#                                   relief='flat', padx=5, command=self.next_chapter)
#         self.btn_next.pack(side='right', padx=6, pady=3)

#     def _dot(self, p, color, cmd):
#         lb = tk.Label(p, text='⬤', fg=color, font=('', 12), cursor='hand2')
#         lb.pack(side='left', padx=2)
#         lb.bind('<Button-1>', lambda e: cmd())

#     def _build_setbar(self):
#         r1 = tk.Frame(self.setbar); r1.pack(fill='x', padx=8, pady=2)
#         tk.Label(r1, text='字号', font=('',8)).pack(side='left')
#         self.sl_font = tk.Scale(r1, from_=10, to=32, orient='horizontal',
#                                 length=70, showvalue=True, font=('',7),
#                                 command=self._on_font_size)
#         self.sl_font.set(self.font_size)
#         self.sl_font.pack(side='left', padx=2)

#         tk.Label(r1, text='行距', font=('',8)).pack(side='left', padx=(8,0))
#         self.sl_spacing = tk.Scale(r1, from_=0, to=24, orient='horizontal',
#                                    length=70, showvalue=True, font=('',7),
#                                    command=self._on_spacing)
#         self.sl_spacing.set(self.line_spacing)
#         self.sl_spacing.pack(side='left', padx=2)

#         r2 = tk.Frame(self.setbar); r2.pack(fill='x', padx=8, pady=2)
#         tk.Label(r2, text='透明', font=('',8)).pack(side='left')
#         self.sl_alpha = tk.Scale(r2, from_=20, to=100, orient='horizontal',
#                                  length=80, showvalue=True, font=('',7),
#                                  command=lambda v: self.root.attributes('-alpha', int(v)/100))
#         self.sl_alpha.set(100)
#         self.sl_alpha.pack(side='left', padx=2)

#         r3 = tk.Frame(self.setbar); r3.pack(fill='x', padx=8, pady=2)
#         tk.Label(r3, text='字色', font=('',8)).pack(side='left')
#         self.btn_fg_color = tk.Button(r3, text='  ', relief='groove', width=2,
#                                       font=('',8), command=self._pick_fg)
#         self.btn_fg_color.pack(side='left', padx=2)

#         tk.Label(r3, text='背景', font=('',8)).pack(side='left', padx=(6,0))
#         self.btn_bg_color = tk.Button(r3, text='  ', relief='groove', width=2,
#                                       font=('',8), command=self._pick_bg)
#         self.btn_bg_color.pack(side='left', padx=2)

#         tk.Button(r3, text='🎨取色', font=('',8), relief='flat',
#                   padx=4, command=self._screen_pick).pack(side='left', padx=4)
#         tk.Button(r3, text='重置', font=('',8), relief='flat',
#                   padx=4, command=self._reset_colors).pack(side='left', padx=2)

#         r4 = tk.Frame(self.setbar); r4.pack(fill='x', padx=8, pady=2)
#         tk.Label(r4, text='主题', font=('',8)).pack(side='left')
#         self.var_theme = tk.StringVar(value=self.theme_name)
#         cb = ttk.Combobox(r4, textvariable=self.var_theme,
#                           values=list(self.THEMES.keys()),
#                           width=7, font=('',8), state='readonly')
#         cb.pack(side='left', padx=4)
#         cb.bind('<<ComboboxSelected>>', self._on_theme)

#     # ─────────────────────────────────────────────────
#     # 颜色 / 主题
#     # ─────────────────────────────────────────────────
#     def _pick_fg(self):
#         t = self._cur_theme()
#         c = colorchooser.askcolor(color=t['fg'], title='选择字体颜色')
#         if c and c[1]:
#             self.THEMES[self.theme_name]['fg'] = c[1]
#             self.txt.config(fg=c[1])
#             self.btn_fg_color.config(bg=c[1])

#     def _pick_bg(self):
#         c = colorchooser.askcolor(color=self._cur_theme()['bg'], title='选择背景颜色')
#         if c and c[1]: self._apply_custom_bg(c[1])

#     def _screen_pick(self):
#         alpha = self.sl_alpha.get() / 100
#         self.root.attributes('-alpha', 0.0)
#         def on_color(hx):
#             self.root.after(100, lambda: self.root.attributes('-alpha', alpha))
#             self._apply_custom_bg(hx)
#         self.root.after(120, lambda: screen_color_picker(on_color))

#     def _apply_custom_bg(self, hx):
#         self.custom_bg  = hx
#         self.custom_bar = self._darken(hx, 0.88)
#         self._apply_theme()
#         try: self.btn_bg_color.config(bg=hx)
#         except: pass

#     def _reset_colors(self):
#         self.custom_bg = self.custom_bar = None
#         self._apply_theme()

#     def _darken(self, hx, f=0.88):
#         h = hx.lstrip('#')
#         return '#{:02x}{:02x}{:02x}'.format(
#             int(int(h[0:2],16)*f), int(int(h[2:4],16)*f), int(int(h[4:6],16)*f))

#     def _cur_theme(self):
#         import copy
#         t = copy.copy(self.THEMES[self.theme_name])
#         if self.custom_bg:  t['bg']  = self.custom_bg
#         if self.custom_bar: t['bar'] = self.custom_bar
#         return t

#     def _on_theme(self, e=None):
#         self.theme_name = self.var_theme.get()
#         self.custom_bg = self.custom_bar = None
#         self._apply_theme()

#     def _apply_theme(self):
#         t = self._cur_theme()
#         bg, fg, bar, sel = t['bg'], t['fg'], t['bar'], t['sel']
#         self.root.configure(bg=bar)
#         self._cf(self.topbar, bar, fg)
#         self._cf(self.botbar, bar, fg)
#         self.sep.config(bg=sel)
#         self.txt_frame.config(bg=bg)
#         self.vsb.config(bg=bar, troughcolor=bg, activebackground=sel)
#         self.txt.config(bg=bg, fg=fg, insertbackground=fg, selectbackground=sel)
#         self.lbl_prog.config(bg=bar, fg=fg)
#         self.btn_bm.config(bg=bar, fg=fg, activebackground=sel)
#         for b in (self.btn_prev, self.btn_next):
#             b.config(bg=bar, fg=fg, activebackground=sel)
#         self._retheme_setbar()
#         try:
#             if self.custom_bg: self.btn_bg_color.config(bg=self.custom_bg)
#         except: pass

#     def _cf(self, fr, bg, fg):
#         try: fr.config(bg=bg)
#         except: pass
#         for w in fr.winfo_children():
#             try: w.config(bg=bg, fg=fg, activebackground=bg)
#             except: pass
#             for w2 in w.winfo_children():
#                 try: w2.config(bg=bg, fg=fg, activebackground=bg)
#                 except: pass

#     def _retheme_setbar(self):
#         t = self._cur_theme()
#         bg, fg, sel = t['bar'], t['fg'], t['sel']
#         self._cf(self.setbar, bg, fg)
#         for sl in (self.sl_font, self.sl_alpha, self.sl_spacing):
#             try: sl.config(bg=bg, fg=fg, troughcolor=sel, activebackground=sel)
#             except: pass
#         try: self.btn_fg_color.config(bg=fg)
#         except: pass

#     # ─────────────────────────────────────────────────
#     # 拖动窗口
#     # ─────────────────────────────────────────────────
#     def _drag_start(self, e):
#         self._dx = e.x_root - self.root.winfo_x()
#         self._dy = e.y_root - self.root.winfo_y()

#     def _drag_move(self, e):
#         self.root.geometry(f'+{e.x_root-self._dx}+{e.y_root-self._dy}')

#     # ─────────────────────────────────────────────────
#     # 打开文件
#     # ─────────────────────────────────────────────────
#     def open_file(self):
#         path = filedialog.askopenfilename(
#             title='打开小说',
#             filetypes=[('小说文件','*.txt *.epub *.md'),('所有文件','*.*')]
#         )
#         if not path: return
#         ext = os.path.splitext(path)[1].lower()
#         if ext == '.epub':
#             title, text = read_epub(path)
#         else:
#             title = os.path.splitext(os.path.basename(path))[0]
#             try:
#                 with open(path, encoding='utf-8', errors='replace') as f:
#                     text = f.read()
#             except Exception as e:
#                 messagebox.showerror('错误', str(e)); return

#         self.book_path  = path
#         self.book_title = title
#         self.lbl_title.config(text=f'  {title}')
#         self.root.title(f'摸鱼阅读器 — {title}')
#         self._load(text, restore_bm=True)

#     def _load(self, text, restore_bm=False):
#         self.chapters = split_chapters(text)
#         self.cur_ch   = 0
#         if restore_bm and self.book_path in self.bookmarks:
#             saved = self.bookmarks[self.book_path].get('chapter', 0)
#             self.cur_ch = max(0, min(saved, len(self.chapters)-1))
#         self._render_chapter()

#     # ─────────────────────────────────────────────────
#     # 渲染章节（核心：直接把整章文本塞进 Text）
#     # ─────────────────────────────────────────────────
#     def _render_chapter(self, scroll_to_top=True):
#         if not self.chapters: return
#         self.cur_ch = max(0, min(self.cur_ch, len(self.chapters)-1))
#         ch = self.chapters[self.cur_ch]

#         self.txt.config(state='normal')
#         self.txt.delete('1.0', 'end')
#         self.txt.insert('1.0', ch['body'])
#         self.txt.config(state='disabled')

#         if scroll_to_top:
#             self.txt.yview_moveto(0.0)

#         self._update_nav()
#         self._wheel_accum = 0

#     def _update_nav(self):
#         n   = len(self.chapters)
#         idx = self.cur_ch + 1
#         self.lbl_prog.config(text=f'第 {idx} / {n} 章')
#         self.btn_prev.config(state='normal' if self.cur_ch > 0   else 'disabled')
#         self.btn_next.config(state='normal' if self.cur_ch < n-1 else 'disabled')

#     # ─────────────────────────────────────────────────
#     # 章节切换
#     # ─────────────────────────────────────────────────
#     def next_chapter(self):
#         if self.chapters and self.cur_ch < len(self.chapters)-1:
#             self.cur_ch += 1
#             self._render_chapter(scroll_to_top=True)

#     def prev_chapter(self):
#         if self.chapters and self.cur_ch > 0:
#             self.cur_ch -= 1
#             self._render_chapter(scroll_to_top=True)

#     def goto_chapter(self, idx):
#         if not self.chapters: return
#         self.cur_ch = max(0, min(idx, len(self.chapters)-1))
#         self._render_chapter(scroll_to_top=True)

#     # ─────────────────────────────────────────────────
#     # 点击：左侧上章 / 右侧下章（忽略中间 38%~62% 区域）
#     # ─────────────────────────────────────────────────
#     def _on_click(self, e):
#         w = self.txt.winfo_width()
#         if   e.x < w * 0.30:
#             self.prev_chapter()
#         elif e.x > w * 0.70:
#             self.next_chapter()
#         # 中间区域：不响应（方便选文字）

#     # ─────────────────────────────────────────────────
#     # 滚轮：章内正常滚动；到达顶/底时累计后切章
#     # ─────────────────────────────────────────────────
#     def _on_wheel(self, e):
#         # 判断滚动方向
#         if e.num == 4:          # Linux up
#             delta = 1
#         elif e.num == 5:        # Linux down
#             delta = -1
#         else:
#             delta = 1 if e.delta > 0 else -1   # Windows/macOS

#         # 当前滚动位置 (top_frac, bottom_frac)
#         top, bot = self.txt.yview()

#         if delta < 0:   # 向下滚
#             if bot >= 0.999:
#                 # 已在底部，累计后切下一章
#                 self._wheel_accum -= 1
#                 if self._wheel_accum <= -3:
#                     self.next_chapter()
#                     return
#             else:
#                 self._wheel_accum = 0
#                 self.txt.yview_scroll(3, 'units')
#         else:           # 向上滚
#             if top <= 0.001:
#                 # 已在顶部，累计后切上一章
#                 self._wheel_accum += 1
#                 if self._wheel_accum >= 3:
#                     self.prev_chapter()
#                     # 切到上章后滚动到底部
#                     self.root.after(30, lambda: self.txt.yview_moveto(1.0))
#                     return
#             else:
#                 self._wheel_accum = 0
#                 self.txt.yview_scroll(-3, 'units')

#     # ─────────────────────────────────────────────────
#     # S 键：向下翻一屏
#     # ─────────────────────────────────────────────────
#     def _scroll_down_screen(self):
#         top, bot = self.txt.yview()
#         if bot >= 0.999:
#             self.next_chapter()
#         else:
#             self.txt.yview_scroll(1, 'pages')

#     # ─────────────────────────────────────────────────
#     # 欢迎页
#     # ─────────────────────────────────────────────────
#     def _show_welcome(self):
#         self.txt.config(state='normal')
#         self.txt.delete('1.0','end')
#         self.txt.insert('1.0', (
#             '\n\n\n\n'
#             '       📚  摸鱼阅读器\n\n'
#             '  支持：TXT  /  EPUB  /  MD\n\n'
#             '  ● 右上角 [打开] 选择文件\n'
#             '  ● 绿色圆点 快速打开\n'
#             '  ● 黄色圆点 打开设置\n\n'
#             '  操作方式：\n'
#             '    滚轮          章内上下滚动\n'
#             '    滚轮到底/顶   自动切换章节\n'
#             '    点击左侧 30%  上一章\n'
#             '    点击右侧 30%  下一章\n'
#             '    S / ↓         向下翻一屏\n'
#             '    ← / →         切换章节\n'
#             '    D + E         最小化\n'
#         ))
#         self.txt.config(state='disabled')

#     # ─────────────────────────────────────────────────
#     # 最小化
#     # ─────────────────────────────────────────────────
#     def toggle_minimize(self):
#         self._minimized = not self._minimized
#         if self._minimized:
#             self._saved_h = self.root.winfo_height()
#             for w in (self.setbar, self.sep, self.txt_frame, self.botbar):
#                 w.pack_forget()
#             self.root.geometry(f'{self.root.winfo_width()}x30')
#         else:
#             self.root.geometry(f'{self.root.winfo_width()}x{self._saved_h}')
#             self.sep.pack(fill='x', after=self.topbar)
#             if self._settings_open:
#                 self.setbar.pack(fill='x', after=self.topbar)
#                 self._retheme_setbar()
#             self.txt_frame.pack(fill='both', expand=True)
#             self.botbar.pack(fill='x', side='bottom')

#     # ─────────────────────────────────────────────────
#     # 设置栏
#     # ─────────────────────────────────────────────────
#     def toggle_settings(self):
#         self._settings_open = not self._settings_open
#         if self._settings_open:
#             self.setbar.pack(fill='x', after=self.topbar)
#             self._retheme_setbar()
#         else:
#             self.setbar.pack_forget()

#     def _on_font_size(self, val):
#         self.font_size = int(float(val))
#         self.txt.config(font=(self.font_fam, self.font_size))

#     def _on_spacing(self, val):
#         self.line_spacing = int(float(val))
#         sp = self.line_spacing
#         self.txt.config(spacing1=sp, spacing2=sp//2, spacing3=sp)

#     # ─────────────────────────────────────────────────
#     # 章节目录
#     # ─────────────────────────────────────────────────
#     def open_chapters(self):
#         if not self.chapters:
#             messagebox.showinfo('提示','请先打开一本小说'); return

#         t  = self._cur_theme()
#         bg, fg, bar, sel = t['bg'], t['fg'], t['bar'], t['sel']

#         win = tk.Toplevel(self.root)
#         win.title('章节目录')
#         win.geometry('300x480')
#         win.resizable(True, True)
#         win.attributes('-topmost', True)
#         win.configure(bg=bg)

#         hdr = tk.Frame(win, bg=bar, height=28)
#         hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr, text='📑 章节目录', font=('',9,'bold'),
#                  bg=bar, fg=fg).pack(side='left', padx=8, pady=4)
#         tk.Button(hdr, text='×', relief='flat', font=('',10),
#                   bg=bar, fg=fg, command=win.destroy).pack(side='right', padx=6)

#         # 搜索
#         sf = tk.Frame(win, bg=bg); sf.pack(fill='x', padx=6, pady=(6,2))
#         sv = tk.StringVar()
#         se = tk.Entry(sf, textvariable=sv, font=('',9), bg=bg, fg=fg,
#                       insertbackground=fg, relief='groove')
#         se.pack(fill='x', ipady=3)
#         PH = '搜索章节名...'
#         se.insert(0, PH); se.config(fg='gray')
#         se.bind('<FocusIn>',  lambda e:(se.delete(0,'end'),se.config(fg=fg)) if se.get()==PH else None)
#         se.bind('<FocusOut>', lambda e:(se.insert(0,PH),se.config(fg='gray')) if not se.get() else None)

#         # 列表
#         lf = tk.Frame(win, bg=bg); lf.pack(fill='both', expand=True, padx=4, pady=4)
#         sb2 = tk.Scrollbar(lf); sb2.pack(side='right', fill='y')
#         lb = tk.Listbox(lf, font=('',10), relief='flat', bg=bg, fg=fg,
#                         selectbackground=sel, selectforeground=fg,
#                         borderwidth=0, highlightthickness=0,
#                         activestyle='none', yscrollcommand=sb2.set)
#         lb.pack(fill='both', expand=True); sb2.config(command=lb.yview)

#         btn_j = tk.Button(win, text='↩  跳转到选中章节', font=('',9,'bold'),
#                           bg=bar, fg=fg, relief='flat', pady=5)
#         btn_j.pack(fill='x', padx=6, pady=4)

#         all_ch  = list(self.chapters)   # [{'title','body'}]
#         visible = list(range(len(all_ch)))  # 存索引

#         def fill(indices):
#             visible.clear(); visible.extend(indices)
#             lb.delete(0,'end')
#             for i in indices:
#                 lb.insert('end', f'  {i+1}. {all_ch[i]["title"]}')

#         fill(range(len(all_ch)))
#         # 高亮当前
#         try: lb.see(self.cur_ch); lb.selection_set(self.cur_ch)
#         except: pass

#         def on_search(*_):
#             q = sv.get().strip()
#             if q in ('', PH):
#                 fill(range(len(all_ch)))
#             else:
#                 fill([i for i,c in enumerate(all_ch) if q in c['title']])
#         sv.trace_add('write', on_search)

#         def jump(event=None):
#             idxs = lb.curselection()
#             if not idxs: return
#             real_idx = visible[idxs[0]]
#             win.destroy()
#             self.goto_chapter(real_idx)

#         btn_j.config(command=jump)
#         lb.bind('<Double-Button-1>', jump)
#         lb.bind('<Return>', jump)

#         rx = self.root.winfo_x() + self.root.winfo_width() + 8
#         ry = self.root.winfo_y()
#         win.geometry(f'300x480+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 书签
#     # ─────────────────────────────────────────────────
#     def add_bookmark(self):
#         if not self.book_path:
#             messagebox.showinfo('提示','请先打开一本小说'); return
#         ch = self.chapters[self.cur_ch] if self.chapters else {}
#         self.bookmarks[self.book_path] = {
#             'title':    self.book_title,
#             'chapter':  self.cur_ch,
#             'total':    len(self.chapters),
#             'ch_title': ch.get('title',''),
#             'path':     self.book_path,
#         }
#         bm_save(self.bookmarks)
#         n = len(self.chapters)
#         messagebox.showinfo('🔖 书签',
#             f'已保存\n第 {self.cur_ch+1} / {n} 章\n{ch.get("title","")}')

#     def open_bookmarks(self):
#         if not self.bookmarks:
#             messagebox.showinfo('书签','暂无书签'); return
#         t  = self._cur_theme()
#         bg, fg, bar, sel = t['bg'], t['fg'], t['bar'], t['sel']

#         win = tk.Toplevel(self.root)
#         win.title('书签'); win.geometry('320x300')
#         win.resizable(True,True); win.attributes('-topmost',True)
#         win.configure(bg=bg)

#         hdr = tk.Frame(win, bg=bar, height=28)
#         hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr, text='🔖 书签列表', font=('',9,'bold'),
#                  bg=bar, fg=fg).pack(side='left', padx=8, pady=4)
#         tk.Button(hdr, text='×', relief='flat', font=('',10),
#                   bg=bar, fg=fg, command=win.destroy).pack(side='right', padx=6)

#         lf = tk.Frame(win, bg=bg); lf.pack(fill='both', expand=True, padx=4, pady=4)
#         sb2 = tk.Scrollbar(lf); sb2.pack(side='right', fill='y')
#         lb = tk.Listbox(lf, font=('',10), relief='flat', bg=bg, fg=fg,
#                         selectbackground=sel, selectforeground=fg,
#                         borderwidth=0, highlightthickness=0,
#                         activestyle='none', yscrollcommand=sb2.set)
#         lb.pack(fill='both', expand=True); sb2.config(command=lb.yview)

#         keys = list(self.bookmarks.keys())
#         for k in keys:
#             bm = self.bookmarks[k]
#             s  = f"  {bm['title']}  第{bm['chapter']+1}章"
#             if bm.get('ch_title'): s += f"  ·  {bm['ch_title']}"
#             lb.insert('end', s)

#         bf = tk.Frame(win, bg=bar); bf.pack(fill='x', padx=6, pady=4)

#         def goto_bm():
#             idxs = lb.curselection()
#             if not idxs: return
#             bm = self.bookmarks[keys[idxs[0]]]
#             win.destroy()
#             if bm['path'] != self.book_path:
#                 ext = os.path.splitext(bm['path'])[1].lower()
#                 try:
#                     if ext == '.epub': _t, text = read_epub(bm['path'])
#                     else:
#                         with open(bm['path'],encoding='utf-8',errors='replace') as f: text=f.read()
#                 except:
#                     messagebox.showerror('错误','文件不存在或已移动'); return
#                 self.book_path = bm['path']; self.book_title = bm['title']
#                 self.lbl_title.config(text=f"  {bm['title']}")
#                 self.root.title(f"摸鱼阅读器 — {bm['title']}")
#                 self.chapters = split_chapters(text)
#             self.goto_chapter(bm['chapter'])

#         def del_bm():
#             idxs = lb.curselection()
#             if not idxs: return
#             k = keys.pop(idxs[0])
#             del self.bookmarks[k]; bm_save(self.bookmarks)
#             lb.delete(idxs[0])

#         tk.Button(bf, text='跳转', font=('',9), bg=bar, fg=fg,
#                   relief='flat', padx=8, command=goto_bm).pack(side='left', padx=4)
#         tk.Button(bf, text='删除', font=('',9), bg=bar, fg=fg,
#                   relief='flat', padx=8, command=del_bm).pack(side='left', padx=4)

#         rx = self.root.winfo_x() + self.root.winfo_width() + 8
#         ry = self.root.winfo_y()
#         win.geometry(f'320x300+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 快捷键
#     # ─────────────────────────────────────────────────
#     def _bind_keys(self):
#         r = self.root
#         r.bind('<KeyPress-s>',   lambda e: self._scroll_down_screen())
#         r.bind('<KeyPress-S>',   lambda e: self._scroll_down_screen())
#         r.bind('<Right>',        lambda e: self.next_chapter())
#         r.bind('<Left>',         lambda e: self.prev_chapter())
#         r.bind('<Down>',         lambda e: self._scroll_down_screen())
#         r.bind('<Up>',           lambda e: self.txt.yview_scroll(-3,'units'))
#         r.bind('<KeyPress-d>',   self._dp)
#         r.bind('<KeyPress-D>',   self._dp)
#         r.bind('<KeyRelease-d>', self._dr)
#         r.bind('<KeyRelease-D>', self._dr)
#         r.bind('<KeyPress-e>',   self._ep)
#         r.bind('<KeyPress-E>',   self._ep)
#         r.focus_set()

#     def _dp(self, e): self._d_held = True
#     def _dr(self, e): self._d_held = False
#     def _ep(self, e):
#         if self._d_held: self.toggle_minimize()


# # ══════════════════════════════════════════════════════════════
# if __name__ == '__main__':
#     try:
#         from ctypes import windll
#         windll.shcore.SetProcessDpiAwareness(1)
#     except: pass
#     App()


##  V2测试

# """
# 摸鱼阅读器 v7.0
# 新增：
#   · 底部进度拖拽条（可拖拽跳章节，书签在条上显示小旗）
#   · O 键快速创建书签标记（支持多书签）
#   · 书签列表支持跳转 / 删除单条

# 运行：python novel_reader.py
# 打包：pip install pyinstaller
#       pyinstaller --onefile --windowed --name 摸鱼阅读器 novel_reader.py
# 屏幕取色需要 Pillow：pip install pillow
# """

# import tkinter as tk
# from tkinter import ttk, filedialog, colorchooser, messagebox
# import os, re, zipfile, sys, json, copy
# from html.parser import HTMLParser


# # ══════════════════════════════════════════════════════════════
# # HTML → 纯文本
# # ══════════════════════════════════════════════════════════════
# class _H2T(HTMLParser):
#     SKIP  = {'script','style','head','meta','link'}
#     BLOCK = {'p','div','br','h1','h2','h3','h4','h5',
#              'h6','li','tr','td','th','section','article'}
#     def __init__(self):
#         super().__init__()
#         self.out, self._s = [], 0
#     def handle_starttag(self, tag, _):
#         if tag in self.SKIP:  self._s += 1
#         if tag in self.BLOCK: self.out.append('\n')
#     def handle_endtag(self, tag):
#         if tag in self.SKIP:  self._s = max(0, self._s - 1)
#         if tag in self.BLOCK: self.out.append('\n')
#     def handle_data(self, d):
#         if not self._s: self.out.append(d)
#     def text(self):
#         return re.sub(r'\n{3,}', '\n\n', ''.join(self.out)).strip()

# def html2text(s):
#     p = _H2T()
#     try: p.feed(s)
#     except: pass
#     return p.text()


# # ══════════════════════════════════════════════════════════════
# # EPUB
# # ══════════════════════════════════════════════════════════════
# def read_epub(path):
#     import xml.etree.ElementTree as ET
#     title = os.path.splitext(os.path.basename(path))[0]
#     body  = ''
#     try:
#         with zipfile.ZipFile(path) as z:
#             ns = z.namelist()
#             opf, odir = '', ''
#             if 'META-INF/container.xml' in ns:
#                 for el in ET.fromstring(z.read('META-INF/container.xml')).iter():
#                     if el.tag.endswith('rootfile'):
#                         opf  = el.get('full-path', '')
#                         odir = opf.rsplit('/', 1)[0] if '/' in opf else ''
#                         break
#             items, spine = {}, []
#             if opf and opf in ns:
#                 root = ET.fromstring(z.read(opf))
#                 for el in root.iter():
#                     tag = el.tag.split('}')[-1]
#                     if tag == 'item':
#                         mid  = el.get('id','')
#                         href = el.get('href','')
#                         mt   = el.get('media-type','')
#                         if href and ('html' in mt or href.endswith(('.html','.xhtml','.htm'))):
#                             items[mid] = (odir+'/'+href).lstrip('/') if odir else href
#                     elif tag == 'itemref':
#                         r = el.get('idref','')
#                         if r in items: spine.append(items[r])
#                     elif tag == 'title' and el.text:
#                         title = el.text
#             if not spine:
#                 spine = sorted(f for f in ns
#                                if re.search(r'\.(html|htm|xhtml)$', f, re.I)
#                                and 'toc' not in f.lower() and 'nav' not in f.lower())
#             for href in spine:
#                 if href in ns:
#                     try: body += html2text(z.read(href).decode('utf-8','replace')) + '\n\n'
#                     except: pass
#     except Exception as e:
#         body = f'[EPUB解析失败: {e}]'
#     return title, body.strip()


# # ══════════════════════════════════════════════════════════════
# # 章节切割
# # ══════════════════════════════════════════════════════════════
# _CH = re.compile(
#     r'^(第\s*[零一二三四五六七八九十百千万\d〇]+\s*[章节卷集回部篇][^\n]{0,40}'
#     r'|Chapter\s*\d+[^\n]{0,40}'
#     r'|CHAPTER\s*\d+[^\n]{0,40}'
#     r'|【[^\n]{1,30}】)', re.I)

# def split_chapters(text):
#     boundaries = []
#     for m in re.finditer(r'^.+$', text, re.M):
#         line = m.group().strip()
#         if line and _CH.match(line):
#             boundaries.append((m.start(), line))
#     if not boundaries:
#         return [{'title': '全文', 'body': text}]
#     chapters = []
#     for i, (pos, title) in enumerate(boundaries):
#         end = boundaries[i+1][0] if i+1 < len(boundaries) else len(text)
#         chapters.append({'title': title, 'body': text[pos:end]})
#     return chapters


# # ══════════════════════════════════════════════════════════════
# # 书签存储  —  支持每本书多个标记书签
# # ══════════════════════════════════════════════════════════════
# BM_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
#                         '.moyu_bookmarks.json')

# def bm_load():
#     try:
#         with open(BM_FILE, encoding='utf-8') as f: return json.load(f)
#     except: return {}

# def bm_save(d):
#     try:
#         with open(BM_FILE, 'w', encoding='utf-8') as f:
#             json.dump(d, f, ensure_ascii=False, indent=2)
#     except: pass


# # ══════════════════════════════════════════════════════════════
# # 屏幕取色器
# # ══════════════════════════════════════════════════════════════
# def screen_color_picker(callback):
#     try:
#         from PIL import ImageGrab
#     except ImportError:
#         c = colorchooser.askcolor(title='选择颜色')
#         if c and c[1]: callback(c[1])
#         return

#     from PIL import ImageGrab, Image, ImageTk
#     ZOOM, HALF = 10, 5
#     CS = (HALF*2+1) * ZOOM

#     preview = tk.Toplevel()
#     preview.overrideredirect(True)
#     preview.attributes('-topmost', True)
#     preview.configure(bg='#1a1a1a')
#     preview.geometry(f'{CS+4}x{CS+28}+200+200')

#     canvas = tk.Canvas(preview, width=CS, height=CS, bg='#000',
#                        highlightthickness=1, highlightbackground='#555', cursor='none')
#     canvas.pack(padx=2, pady=(2,0))
#     lbl = tk.Label(preview, text='#000000', font=('Consolas',9,'bold'),
#                    bg='#1a1a1a', fg='white', pady=1)
#     lbl.pack()

#     cur, ph, aid, done = ['#000000'], [None], [None], [False]

#     def update():
#         if done[0]: return
#         try:
#             mx, my = preview.winfo_pointerx(), preview.winfo_pointery()
#             img    = ImageGrab.grab(bbox=(mx-HALF, my-HALF, mx+HALF+1, my+HALF+1))
#             zoomed = img.resize((CS, CS), Image.NEAREST)
#             ph[0]  = ImageTk.PhotoImage(zoomed)
#             canvas.delete('all')
#             canvas.create_image(0, 0, anchor='nw', image=ph[0])
#             c2 = CS//2
#             canvas.create_line(c2, 0, c2, CS, fill='white', width=1)
#             canvas.create_line(0, c2, CS, c2, fill='white', width=1)
#             canvas.create_rectangle(c2-ZOOM, c2-ZOOM, c2+ZOOM, c2+ZOOM, outline='white', width=2)
#             px  = img.getpixel((HALF, HALF))
#             hx  = '#{:02x}{:02x}{:02x}'.format(px[0], px[1], px[2])
#             cur[0] = hx; lbl.config(text=hx)
#             sw, sh = preview.winfo_screenwidth(), preview.winfo_screenheight()
#             ox, oy = mx+18, my+18
#             if ox+CS+10 > sw: ox = mx-CS-22
#             if oy+CS+32 > sh: oy = my-CS-34
#             preview.geometry(f'+{ox}+{oy}')
#         except: pass
#         aid[0] = preview.after(40, update)

#     def finish():
#         done[0] = True
#         if aid[0]:
#             try: preview.after_cancel(aid[0])
#             except: pass
#         for w in (overlay, preview):
#             try: w.destroy()
#             except: pass

#     overlay = tk.Toplevel()
#     overlay.overrideredirect(True)
#     overlay.attributes('-topmost', True)
#     overlay.attributes('-alpha', 0.01)
#     sw, sh = overlay.winfo_screenwidth(), overlay.winfo_screenheight()
#     overlay.geometry(f'{sw}x{sh}+0+0')
#     overlay.configure(bg='white', cursor='crosshair')
#     overlay.bind('<Button-1>', lambda e: (finish(), callback(cur[0])))
#     overlay.bind('<Escape>',   lambda e: finish())
#     overlay.focus_force()
#     aid[0] = preview.after(40, update)


# # ══════════════════════════════════════════════════════════════
# # 自定义竖向滚动条（Canvas 实现，支持拖拽，圆角滑块）
# # ══════════════════════════════════════════════════════════════
# class SmoothScrollbar:
#     """
#     替代原生 Scrollbar：
#       · 宽度可设置，默认 10px
#       · 圆角滑块，颜色随主题
#       · 支持点击轨道跳转、拖拽滑块
#       · 接口兼容原生 Scrollbar：set(lo, hi) / get()
#     """
#     W = 10      # 滚动条宽度

#     def __init__(self, parent, on_scroll, **kw):
#         """on_scroll(fraction) 当用户拖拽/点击时调用，fraction ∈ [0,1]"""
#         self.on_scroll = on_scroll
#         self._lo = 0.0
#         self._hi = 1.0
#         self._dragging  = False
#         self._drag_start_y    = 0
#         self._drag_start_lo   = 0.0

#         # 颜色
#         self.c_bg    = '#ebdbb2'
#         self.c_track = '#d5c4a1'
#         self.c_thumb = '#b8a57a'
#         self.c_hover = '#9a8060'

#         self.cv = tk.Canvas(parent, width=self.W,
#                             highlightthickness=0, cursor='arrow', **kw)
#         self.cv.pack(side='right', fill='y')

#         self.cv.bind('<Configure>',       lambda e: self._draw())
#         self.cv.bind('<ButtonPress-1>',   self._press)
#         self.cv.bind('<B1-Motion>',       self._drag)
#         self.cv.bind('<ButtonRelease-1>', self._release)
#         self.cv.bind('<Enter>',           lambda e: self._set_hover(True))
#         self.cv.bind('<Leave>',           lambda e: self._set_hover(False))
#         self._hover = False

#     # ── 外部接口（兼容 Text yscrollcommand）────────────
#     def set(self, lo, hi):
#         """Text widget 调用此方法更新滑块位置"""
#         self._lo = float(lo)
#         self._hi = float(hi)
#         self._draw()

#     def set_colors(self, bg, track, thumb, thumb_hover):
#         self.c_bg    = bg
#         self.c_track = track
#         self.c_thumb = thumb
#         self.c_hover = thumb_hover
#         self._draw()

#     # ── 绘制 ────────────────────────────────────────────
#     def _draw(self):
#         cv  = self.cv
#         W   = self.W
#         H   = cv.winfo_height()
#         if H < 4: return
#         cv.delete('all')

#         PAD = 2   # 上下留白

#         # 背景 / 轨道
#         cv.create_rectangle(0, 0, W, H, fill=self.c_bg, outline='')
#         tx = W // 2
#         cv.create_line(tx, PAD, tx, H - PAD,
#                        fill=self.c_track, width=W - 4, capstyle='round')

#         # 滑块
#         thumb_h = max(20, int((self._hi - self._lo) * (H - 2*PAD)))
#         thumb_y = PAD + int(self._lo * (H - 2*PAD))
#         thumb_y2 = min(H - PAD, thumb_y + thumb_h)

#         color = self.c_hover if self._hover else self.c_thumb
#         r = (W - 4) // 2     # 圆角半径

#         # 用 create_oval + rectangle 模拟圆角矩形
#         x1, x2 = 2, W - 2
#         y1, y2 = thumb_y, thumb_y2
#         if y2 - y1 >= 2*r:
#             cv.create_rectangle(x1, y1+r, x2, y2-r, fill=color, outline='')
#             cv.create_oval(x1, y1, x2, y1+2*r, fill=color, outline='')
#             cv.create_oval(x1, y2-2*r, x2, y2, fill=color, outline='')
#         else:
#             cv.create_oval(x1, y1, x2, y2, fill=color, outline='')

#     def _set_hover(self, v):
#         self._hover = v
#         self._draw()

#     # ── 交互 ────────────────────────────────────────────
#     def _y_to_frac(self, y):
#         H   = self.cv.winfo_height()
#         PAD = 2
#         return max(0.0, min(1.0, (y - PAD) / max(1, H - 2*PAD)))

#     def _thumb_range(self):
#         H   = self.cv.winfo_height()
#         PAD = 2
#         th  = max(20, int((self._hi - self._lo) * (H - 2*PAD)))
#         ty  = PAD + int(self._lo * (H - 2*PAD))
#         return ty, ty + th

#     def _press(self, e):
#         ty1, ty2 = self._thumb_range()
#         if ty1 <= e.y <= ty2:
#             # 点在滑块上 → 开始拖拽
#             self._dragging       = True
#             self._drag_start_y   = e.y
#             self._drag_start_lo  = self._lo
#         else:
#             # 点在轨道 → 直接跳转到点击位置（页面中心对齐点击处）
#             frac = self._y_to_frac(e.y)
#             span = self._hi - self._lo
#             target = max(0.0, min(1.0 - span, frac - span / 2))
#             self.on_scroll(target)

#     def _drag(self, e):
#         if not self._dragging: return
#         H   = self.cv.winfo_height()
#         PAD = 2
#         dy  = e.y - self._drag_start_y
#         delta = dy / max(1, H - 2*PAD)
#         span  = self._hi - self._lo
#         target = max(0.0, min(1.0 - span, self._drag_start_lo + delta))
#         self._lo = target
#         self._hi = target + span
#         self._draw()
#         self.on_scroll(target)

#     def _release(self, e):
#         self._dragging = False


# # ══════════════════════════════════════════════════════════════
# # 主程序
# # ══════════════════════════════════════════════════════════════
# class App:

#     THEMES = {
#         '暖黄': dict(bg='#fdf6e3', fg='#3c3836', bar='#ebdbb2', sel='#d5c4a1',
#                     thumb='#b8a882', thumb_h='#8f7a55'),
#         '夜间': dict(bg='#1e1e2e', fg='#cdd6f4', bar='#181825', sel='#313244',
#                     thumb='#45475a', thumb_h='#6c7086'),
#         '护眼': dict(bg='#1a2f1a', fg='#a8d5a2', bar='#152315', sel='#2d5a2d',
#                     thumb='#3a6b3a', thumb_h='#57c454'),
#         '纸张': dict(bg='#f5f0e8', fg='#2c2416', bar='#ede4d0', sel='#c8b89a',
#                     thumb='#c8a882', thumb_h='#8b6045'),
#         '白底': dict(bg='#ffffff', fg='#1a1a1a', bar='#f0f0f0', sel='#dddddd',
#                     thumb='#bbbbbb', thumb_h='#888888'),
#     }

#     def __init__(self):
#         self.root = tk.Tk()
#         self.root.title('摸鱼阅读器')
#         self.root.geometry('420x580')
#         self.root.minsize(300, 360)
#         self.root.attributes('-topmost', True)

#         # 书籍数据
#         self.book_path   = ''
#         self.book_title  = ''
#         self.chapters    = []
#         self.cur_ch      = 0
#         self.bookmarks   = bm_load()   # {path: {meta, marks:[{chapter,ch_title,note}]}}

#         # UI 状态
#         self.theme_name     = '暖黄'
#         self.custom_bg      = None
#         self.custom_bar     = None
#         self.font_size      = 14
#         self.line_spacing   = 6
#         self.font_fam       = ('宋体' if sys.platform == 'win32'
#                                else 'Songti SC' if sys.platform == 'darwin'
#                                else 'Noto Serif CJK SC')
#         self._d_held        = False
#         self._minimized     = False
#         self._settings_open = False
#         self._wheel_accum   = 0

#         self._build_ui()
#         self._apply_theme()
#         self._bind_keys()
#         self.root.mainloop()

#     # ─────────────────────────────────────────────────
#     # UI 构建
#     # ─────────────────────────────────────────────────
#     def _build_ui(self):
#         r = self.root

#         # 顶部栏
#         self.topbar = tk.Frame(r, height=30)
#         self.topbar.pack(fill='x')
#         self.topbar.pack_propagate(False)

#         dots = tk.Frame(self.topbar)
#         dots.pack(side='left', padx=6, pady=5)
#         self._dot(dots, '#ff5f57', self.toggle_minimize)
#         self._dot(dots, '#ffbd2e', self.toggle_settings)
#         self._dot(dots, '#28ca41', self.open_file)

#         self.lbl_title = tk.Label(self.topbar, text='摸鱼阅读器', font=('', 9))
#         self.lbl_title.pack(side='left', fill='x', expand=True)

#         rbf = tk.Frame(self.topbar)
#         rbf.pack(side='right', padx=4)
#         for lbl, cmd in [('书签', self.open_bookmarks),
#                           ('目录', self.open_chapters),
#                           ('打开', self.open_file),
#                           ('×',   r.destroy)]:
#             tk.Button(rbf, text=lbl, font=('', 8), relief='flat',
#                       padx=3, command=cmd).pack(side='left', padx=1)

#         for w in (self.topbar, self.lbl_title):
#             w.bind('<ButtonPress-1>', self._drag_start)
#             w.bind('<B1-Motion>',     self._drag_move)

#         # 设置栏（默认隐藏）
#         self.setbar = tk.Frame(r)
#         self._build_setbar()

#         # 分隔线
#         self.sep = tk.Frame(r, height=1)
#         self.sep.pack(fill='x')

#         # 文本区（先 pack txt_frame，再在内部放 txt 和 vsb）
#         self.txt_frame = tk.Frame(r)
#         self.txt_frame.pack(fill='both', expand=True)

#         # 自定义竖向拖拽滚动条（先 pack 到右侧，再 pack txt）
#         self.vsb = SmoothScrollbar(
#             self.txt_frame,
#             on_scroll=lambda frac: self.txt.yview_moveto(frac),
#         )

#         self.txt = tk.Text(
#             self.txt_frame, wrap='word',
#             relief='flat', padx=16, pady=10,
#             state='disabled', cursor='arrow',
#             font=(self.font_fam, self.font_size),
#             borderwidth=0, highlightthickness=0,
#             spacing1=self.line_spacing,
#             spacing2=self.line_spacing // 2,
#             spacing3=self.line_spacing,
#             yscrollcommand=self._on_yscroll,
#         )
#         self.txt.pack(side='left', fill='both', expand=True)

#         self.txt.bind('<Button-1>',   self._on_click)
#         self.txt.bind('<MouseWheel>', self._on_wheel)
#         self.txt.bind('<Button-4>',   self._on_wheel)
#         self.txt.bind('<Button-5>',   self._on_wheel)

#         self._show_welcome()

#         # ── 底部区域（仅导航栏，无横向进度条）──────
#         self.bot_area = tk.Frame(r)
#         self.bot_area.pack(fill='x', side='bottom')

#         # 导航栏
#         self.botbar = tk.Frame(self.bot_area, height=26)
#         self.botbar.pack(fill='x')
#         self.botbar.pack_propagate(False)

#         self.btn_prev = tk.Button(self.botbar, text='◀ 上章', font=('', 8),
#                                   relief='flat', padx=5, command=self.prev_chapter)
#         self.btn_prev.pack(side='left', padx=6, pady=3)

#         self.lbl_prog = tk.Label(self.botbar, text='', font=('', 8))
#         self.lbl_prog.pack(side='left', expand=True)

#         # O键提示
#         tk.Label(self.botbar, text='O=书签', font=('', 7)).pack(side='right', padx=2)

#         self.btn_bm = tk.Button(self.botbar, text='🔖', font=('', 9),
#                                 relief='flat', padx=2, command=self.add_mark)
#         self.btn_bm.pack(side='right', padx=2, pady=3)

#         self.btn_next = tk.Button(self.botbar, text='下章 ▶', font=('', 8),
#                                   relief='flat', padx=5, command=self.next_chapter)
#         self.btn_next.pack(side='right', padx=6, pady=3)

#     def _dot(self, p, color, cmd):
#         lb = tk.Label(p, text='⬤', fg=color, font=('', 12), cursor='hand2')
#         lb.pack(side='left', padx=2)
#         lb.bind('<Button-1>', lambda e: cmd())

#     def _build_setbar(self):
#         r1 = tk.Frame(self.setbar); r1.pack(fill='x', padx=8, pady=2)
#         tk.Label(r1, text='字号', font=('',8)).pack(side='left')
#         self.sl_font = tk.Scale(r1, from_=10, to=32, orient='horizontal',
#                                 length=70, showvalue=True, font=('',7),
#                                 command=self._on_font_size)
#         self.sl_font.set(self.font_size)
#         self.sl_font.pack(side='left', padx=2)

#         tk.Label(r1, text='行距', font=('',8)).pack(side='left', padx=(8,0))
#         self.sl_spacing = tk.Scale(r1, from_=0, to=24, orient='horizontal',
#                                    length=70, showvalue=True, font=('',7),
#                                    command=self._on_spacing)
#         self.sl_spacing.set(self.line_spacing)
#         self.sl_spacing.pack(side='left', padx=2)

#         r2 = tk.Frame(self.setbar); r2.pack(fill='x', padx=8, pady=2)
#         tk.Label(r2, text='透明', font=('',8)).pack(side='left')
#         self.sl_alpha = tk.Scale(r2, from_=20, to=100, orient='horizontal',
#                                  length=80, showvalue=True, font=('',7),
#                                  command=lambda v: self.root.attributes('-alpha', int(v)/100))
#         self.sl_alpha.set(100)
#         self.sl_alpha.pack(side='left', padx=2)

#         r3 = tk.Frame(self.setbar); r3.pack(fill='x', padx=8, pady=2)
#         tk.Label(r3, text='字色', font=('',8)).pack(side='left')
#         self.btn_fg_color = tk.Button(r3, text='  ', relief='groove', width=2,
#                                       font=('',8), command=self._pick_fg)
#         self.btn_fg_color.pack(side='left', padx=2)

#         tk.Label(r3, text='背景', font=('',8)).pack(side='left', padx=(6,0))
#         self.btn_bg_color = tk.Button(r3, text='  ', relief='groove', width=2,
#                                       font=('',8), command=self._pick_bg)
#         self.btn_bg_color.pack(side='left', padx=2)

#         tk.Button(r3, text='🎨取色', font=('',8), relief='flat',
#                   padx=4, command=self._screen_pick).pack(side='left', padx=4)
#         tk.Button(r3, text='重置', font=('',8), relief='flat',
#                   padx=4, command=self._reset_colors).pack(side='left', padx=2)

#         r4 = tk.Frame(self.setbar); r4.pack(fill='x', padx=8, pady=2)
#         tk.Label(r4, text='主题', font=('',8)).pack(side='left')
#         self.var_theme = tk.StringVar(value=self.theme_name)
#         cb = ttk.Combobox(r4, textvariable=self.var_theme,
#                           values=list(self.THEMES.keys()),
#                           width=7, font=('',8), state='readonly')
#         cb.pack(side='left', padx=4)
#         cb.bind('<<ComboboxSelected>>', self._on_theme)

#     # ─────────────────────────────────────────────────
#     # 颜色 / 主题
#     # ─────────────────────────────────────────────────
#     def _pick_fg(self):
#         t = self._cur_theme()
#         c = colorchooser.askcolor(color=t['fg'], title='选择字体颜色')
#         if c and c[1]:
#             self.THEMES[self.theme_name]['fg'] = c[1]
#             self.txt.config(fg=c[1])
#             self.btn_fg_color.config(bg=c[1])

#     def _pick_bg(self):
#         c = colorchooser.askcolor(color=self._cur_theme()['bg'], title='选择背景颜色')
#         if c and c[1]: self._apply_custom_bg(c[1])

#     def _screen_pick(self):
#         alpha = self.sl_alpha.get() / 100
#         self.root.attributes('-alpha', 0.0)
#         def on_color(hx):
#             self.root.after(100, lambda: self.root.attributes('-alpha', alpha))
#             self._apply_custom_bg(hx)
#         self.root.after(120, lambda: screen_color_picker(on_color))

#     def _apply_custom_bg(self, hx):
#         self.custom_bg  = hx
#         self.custom_bar = self._darken(hx, 0.88)
#         self._apply_theme()
#         try: self.btn_bg_color.config(bg=hx)
#         except: pass

#     def _reset_colors(self):
#         self.custom_bg = self.custom_bar = None
#         self._apply_theme()

#     def _darken(self, hx, f=0.88):
#         h = hx.lstrip('#')
#         return '#{:02x}{:02x}{:02x}'.format(
#             int(int(h[0:2],16)*f), int(int(h[2:4],16)*f), int(int(h[4:6],16)*f))

#     def _cur_theme(self):
#         t = copy.copy(self.THEMES[self.theme_name])
#         if self.custom_bg:  t['bg']  = self.custom_bg
#         if self.custom_bar: t['bar'] = self.custom_bar
#         return t

#     def _on_theme(self, e=None):
#         self.theme_name = self.var_theme.get()
#         self.custom_bg = self.custom_bar = None
#         self._apply_theme()

#     def _apply_theme(self):
#         t = self._cur_theme()
#         bg, fg, bar, sel = t['bg'], t['fg'], t['bar'], t['sel']
#         self.root.configure(bg=bar)
#         self._cf(self.topbar, bar, fg)
#         self._cf(self.botbar, bar, fg)
#         self._cf(self.bot_area, bar, fg)
#         self.sep.config(bg=sel)
#         self.txt_frame.config(bg=bg)
#         self.vsb.cv.config(bg=bg)
#         self.vsb.set_colors(bg=bg, track=sel,
#                             thumb=t.get('thumb', sel),
#                             thumb_hover=t.get('thumb_h', fg))
#         self.txt.config(bg=bg, fg=fg, insertbackground=fg, selectbackground=sel)
#         self.lbl_prog.config(bg=bar, fg=fg)
#         self.btn_bm.config(bg=bar, fg=fg, activebackground=sel)
#         for b in (self.btn_prev, self.btn_next):
#             b.config(bg=bar, fg=fg, activebackground=sel)

#         self._retheme_setbar()
#         try:
#             if self.custom_bg: self.btn_bg_color.config(bg=self.custom_bg)
#         except: pass

#     def _cf(self, fr, bg, fg):
#         try: fr.config(bg=bg)
#         except: pass
#         for w in fr.winfo_children():
#             try: w.config(bg=bg, fg=fg, activebackground=bg)
#             except: pass
#             for w2 in w.winfo_children():
#                 try: w2.config(bg=bg, fg=fg, activebackground=bg)
#                 except: pass

#     def _retheme_setbar(self):
#         t = self._cur_theme()
#         bg, fg, sel = t['bar'], t['fg'], t['sel']
#         self._cf(self.setbar, bg, fg)
#         for sl in (self.sl_font, self.sl_alpha, self.sl_spacing):
#             try: sl.config(bg=bg, fg=fg, troughcolor=sel, activebackground=sel)
#             except: pass
#         try: self.btn_fg_color.config(bg=fg)
#         except: pass

#     # ─────────────────────────────────────────────────
#     # 拖动窗口
#     # ─────────────────────────────────────────────────
#     def _drag_start(self, e):
#         self._dx = e.x_root - self.root.winfo_x()
#         self._dy = e.y_root - self.root.winfo_y()

#     def _drag_move(self, e):
#         self.root.geometry(f'+{e.x_root-self._dx}+{e.y_root-self._dy}')

#     # ─────────────────────────────────────────────────
#     # 打开文件
#     # ─────────────────────────────────────────────────
#     def open_file(self):
#         path = filedialog.askopenfilename(
#             title='打开小说',
#             filetypes=[('小说文件','*.txt *.epub *.md'),('所有文件','*.*')]
#         )
#         if not path: return
#         ext = os.path.splitext(path)[1].lower()
#         if ext == '.epub':
#             title, text = read_epub(path)
#         else:
#             title = os.path.splitext(os.path.basename(path))[0]
#             try:
#                 with open(path, encoding='utf-8', errors='replace') as f: text = f.read()
#             except Exception as e:
#                 messagebox.showerror('错误', str(e)); return

#         self.book_path  = path
#         self.book_title = title
#         self.lbl_title.config(text=f'  {title}')
#         self.root.title(f'摸鱼阅读器 — {title}')
#         self._load(text, restore_bm=True)

#     def _load(self, text, restore_bm=False):
#         self.chapters = split_chapters(text)
#         self.cur_ch   = 0
#         bm = self.bookmarks.get(self.book_path, {})
#         if restore_bm and bm:
#             # 恢复上次"最近位置"（非标记书签）
#             saved = bm.get('last_chapter', 0)
#             self.cur_ch = max(0, min(saved, len(self.chapters)-1))
#         self._render_chapter()

#     # ─────────────────────────────────────────────────
#     # 渲染章节
#     # ─────────────────────────────────────────────────
#     def _render_chapter(self, scroll_to_top=True):
#         if not self.chapters: return
#         self.cur_ch = max(0, min(self.cur_ch, len(self.chapters)-1))
#         ch = self.chapters[self.cur_ch]

#         self.txt.config(state='normal')
#         self.txt.delete('1.0', 'end')
#         self.txt.insert('1.0', ch['body'])
#         self.txt.config(state='disabled')

#         if scroll_to_top:
#             self.txt.yview_moveto(0.0)

#         self._update_nav()
#         self._wheel_accum = 0
#         # 自动保存"最近位置"书签
#         self._save_last_position()

#     def _update_nav(self):
#         n   = len(self.chapters)
#         idx = self.cur_ch + 1
#         self.lbl_prog.config(text=f'第 {idx} / {n} 章')
#         self.btn_prev.config(state='normal' if self.cur_ch > 0   else 'disabled')
#         self.btn_next.config(state='normal' if self.cur_ch < n-1 else 'disabled')


#     def _get_mark_chapters(self):
#         """返回当前书的所有标记书签的章节索引列表"""
#         bm = self.bookmarks.get(self.book_path, {})
#         return [m['chapter'] for m in bm.get('marks', [])]

#     # ─────────────────────────────────────────────────
#     # 章节切换
#     # ─────────────────────────────────────────────────
#     def next_chapter(self):
#         if self.chapters and self.cur_ch < len(self.chapters)-1:
#             self.cur_ch += 1
#             self._render_chapter(scroll_to_top=True)

#     def prev_chapter(self):
#         if self.chapters and self.cur_ch > 0:
#             self.cur_ch -= 1
#             self._render_chapter(scroll_to_top=True)

#     def goto_chapter(self, idx):
#         if not self.chapters: return
#         self.cur_ch = max(0, min(idx, len(self.chapters)-1))
#         self._render_chapter(scroll_to_top=True)

#     # ─────────────────────────────────────────────────
#     # 点击翻章 / 滚轮
#     # ─────────────────────────────────────────────────
#     def _on_yscroll(self, lo, hi):
#         """Text widget 回调 → 转发给自定义滚动条"""
#         self.vsb.set(lo, hi)

#     def _on_click(self, e):
#         w = self.txt.winfo_width()
#         if   e.x < w * 0.30: self.prev_chapter()
#         elif e.x > w * 0.70: self.next_chapter()

#     def _on_wheel(self, e):
#         if e.num == 4:   delta = 1
#         elif e.num == 5: delta = -1
#         else:            delta = 1 if e.delta > 0 else -1
#         top, bot = self.txt.yview()
#         if delta < 0:
#             if bot >= 0.999:
#                 self._wheel_accum -= 1
#                 if self._wheel_accum <= -3: self.next_chapter(); return
#             else:
#                 self._wheel_accum = 0
#                 self.txt.yview_scroll(3, 'units')
#         else:
#             if top <= 0.001:
#                 self._wheel_accum += 1
#                 if self._wheel_accum >= 3:
#                     self.prev_chapter()
#                     self.root.after(30, lambda: self.txt.yview_moveto(1.0))
#                     return
#             else:
#                 self._wheel_accum = 0
#                 self.txt.yview_scroll(-3, 'units')

#     def _scroll_down_screen(self):
#         _, bot = self.txt.yview()
#         if bot >= 0.999: self.next_chapter()
#         else:            self.txt.yview_scroll(1, 'pages')

#     # ─────────────────────────────────────────────────
#     # 书签系统（多标记）
#     # ─────────────────────────────────────────────────
#     def _ensure_bm_entry(self):
#         """确保当前书在 bookmarks 里有条目"""
#         if self.book_path not in self.bookmarks:
#             self.bookmarks[self.book_path] = {
#                 'title': self.book_title,
#                 'path':  self.book_path,
#                 'last_chapter': self.cur_ch,
#                 'marks': [],
#             }

#     def _save_last_position(self):
#         """自动保存"最近阅读位置"（不算标记书签）"""
#         if not self.book_path: return
#         self._ensure_bm_entry()
#         self.bookmarks[self.book_path]['last_chapter'] = self.cur_ch
#         bm_save(self.bookmarks)

#     def add_mark(self, note=''):
#         """O键 / 🔖按钮：在当前章节添加标记书签"""
#         if not self.book_path:
#             messagebox.showinfo('提示', '请先打开一本小说'); return
#         self._ensure_bm_entry()
#         ch      = self.chapters[self.cur_ch]
#         marks   = self.bookmarks[self.book_path]['marks']

#         # 同章节已有书签则更新，否则追加
#         existing = next((m for m in marks if m['chapter'] == self.cur_ch), None)
#         entry = {
#             'chapter':  self.cur_ch,
#             'ch_title': ch['title'],
#             'note':     note,
#         }
#         if existing:
#             existing.update(entry)
#             msg = f'书签已更新\n第 {self.cur_ch+1} 章\n{ch["title"]}'
#         else:
#             marks.append(entry)
#             msg = f'🔖 书签已添加\n第 {self.cur_ch+1} 章\n{ch["title"]}'

#         bm_save(self.bookmarks)
#         self._update_nav()   # 刷新进度条上的旗子

#         # 顶部短暂提示（不用弹窗打扰）
#         self._toast(msg)

#     def _toast(self, msg):
#         """在窗口内弹出短暂提示条，1.5秒后消失"""
#         t = self._cur_theme()
#         toast = tk.Label(self.root, text=msg.replace('\n', '  '),
#                          font=('', 8), bg=t.get('fill', t['bar']),
#                          fg=t['bg'], padx=8, pady=3, relief='flat')
#         toast.place(relx=0.5, rely=0.08, anchor='n')
#         self.root.after(1500, toast.destroy)

#     def open_bookmarks(self):
#         bm = self.bookmarks.get(self.book_path, {})
#         marks = bm.get('marks', [])

#         # 如果没书，显示所有书的"最近位置"
#         all_books = {k: v for k, v in self.bookmarks.items()}
#         if not all_books:
#             messagebox.showinfo('书签', '暂无书签'); return

#         t  = self._cur_theme()
#         bg, fg, bar, sel = t['bg'], t['fg'], t['bar'], t['sel']

#         win = tk.Toplevel(self.root)
#         win.title('书签管理')
#         win.geometry('340x400')
#         win.resizable(True, True)
#         win.attributes('-topmost', True)
#         win.configure(bg=bg)

#         hdr = tk.Frame(win, bg=bar, height=28)
#         hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr, text='🔖 书签管理', font=('',9,'bold'),
#                  bg=bar, fg=fg).pack(side='left', padx=8, pady=4)
#         tk.Button(hdr, text='×', relief='flat', font=('',10),
#                   bg=bar, fg=fg, command=win.destroy).pack(side='right', padx=6)

#         # Tab：本书书签 / 所有书
#         nb = ttk.Notebook(win)
#         nb.pack(fill='both', expand=True, padx=4, pady=4)

#         def make_tab(parent, rows, jump_fn, del_fn):
#             """rows: [(display_str, data_obj)]"""
#             f = tk.Frame(parent, bg=bg)
#             sb2 = tk.Scrollbar(f); sb2.pack(side='right', fill='y')
#             lb = tk.Listbox(f, font=('',10), relief='flat', bg=bg, fg=fg,
#                             selectbackground=sel, selectforeground=fg,
#                             borderwidth=0, highlightthickness=0,
#                             activestyle='none', yscrollcommand=sb2.set)
#             lb.pack(fill='both', expand=True); sb2.config(command=lb.yview)
#             for txt, _ in rows:
#                 lb.insert('end', txt)
#             bf = tk.Frame(f, bg=bar); bf.pack(fill='x', pady=2)
#             def _jump():
#                 idxs = lb.curselection()
#                 if idxs: jump_fn(rows[idxs[0]][1])
#             def _del():
#                 idxs = lb.curselection()
#                 if idxs:
#                     del_fn(rows[idxs[0]][1])
#                     lb.delete(idxs[0])
#                     rows.pop(idxs[0])
#             tk.Button(bf, text='跳转', font=('',9), bg=bar, fg=fg,
#                       relief='flat', padx=8, command=_jump).pack(side='left', padx=4)
#             tk.Button(bf, text='删除', font=('',9), bg=bar, fg=fg,
#                       relief='flat', padx=8, command=_del).pack(side='left')
#             lb.bind('<Double-Button-1>', lambda e: _jump())
#             return f

#         # ── 本书标记书签 tab ──────────────────────────
#         mark_rows = []
#         for m in marks:
#             s = f"  🏴 第{m['chapter']+1}章  {m['ch_title']}"
#             if m.get('note'): s += f"  —  {m['note']}"
#             mark_rows.append((s, m))

#         def jump_mark(m):
#             win.destroy()
#             self.goto_chapter(m['chapter'])

#         def del_mark(m):
#             bm2 = self.bookmarks.get(self.book_path, {})
#             bm2['marks'] = [x for x in bm2.get('marks',[]) if x is not m]
#             bm_save(self.bookmarks)
#             self._update_nav()

#         tab1 = make_tab(nb, mark_rows, jump_mark, del_mark)
#         nb.add(tab1, text=f'本书书签 ({len(mark_rows)})')

#         # ── 所有书最近位置 tab ────────────────────────
#         book_rows = []
#         for k, v in all_books.items():
#             lc  = v.get('last_chapter', 0)
#             tot = v.get('total_chapters', '?')
#             s   = f"  📖 {v.get('title','?')}  第{lc+1}章"
#             book_rows.append((s, v))

#         def jump_book(v):
#             win.destroy()
#             path = v.get('path','')
#             if not path: return
#             if path == self.book_path:
#                 self.goto_chapter(v.get('last_chapter', 0))
#             else:
#                 ext = os.path.splitext(path)[1].lower()
#                 try:
#                     if ext == '.epub': title2, text2 = read_epub(path)
#                     else:
#                         with open(path, encoding='utf-8', errors='replace') as f: text2=f.read()
#                         title2 = v.get('title', os.path.basename(path))
#                 except:
#                     messagebox.showerror('错误','文件不存在或已移动'); return
#                 self.book_path = path; self.book_title = title2
#                 self.lbl_title.config(text=f'  {title2}')
#                 self.root.title(f'摸鱼阅读器 — {title2}')
#                 self.chapters = split_chapters(text2)
#                 self.goto_chapter(v.get('last_chapter', 0))

#         def del_book(v):
#             k = v.get('path','')
#             if k in self.bookmarks:
#                 del self.bookmarks[k]
#                 bm_save(self.bookmarks)

#         tab2 = make_tab(nb, book_rows, jump_book, del_book)
#         nb.add(tab2, text=f'所有书籍 ({len(book_rows)})')

#         rx = self.root.winfo_x() + self.root.winfo_width() + 8
#         ry = self.root.winfo_y()
#         win.geometry(f'340x400+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 欢迎页
#     # ─────────────────────────────────────────────────
#     def _show_welcome(self):
#         self.txt.config(state='normal')
#         self.txt.delete('1.0','end')
#         self.txt.insert('1.0', (
#             '\n\n\n\n'
#             '       📚  摸鱼阅读器\n\n'
#             '  支持：TXT  /  EPUB  /  MD\n\n'
#             '  ● 右上角 [打开] 选择文件\n'
#             '  ● 绿色圆点 快速打开\n\n'
#             '  操作方式：\n'
#             '    滚轮          章内上下滚动\n'
#             '    滚到底/顶     自动切换章节\n'
#             '    点击左侧 30%  上一章\n'
#             '    点击右侧 30%  下一章\n'
#             '    拖拽底部进度条 快速定位章节\n'
#             '    S / ↓         向下翻一屏\n'
#             '    ← / →         切换章节\n'
#             '    O             添加书签标记\n'
#             '    D + E         最小化\n'
#         ))
#         self.txt.config(state='disabled')

#     # ─────────────────────────────────────────────────
#     # 最小化
#     # ─────────────────────────────────────────────────
#     def toggle_minimize(self):
#         self._minimized = not self._minimized
#         if self._minimized:
#             self._saved_h = self.root.winfo_height()
#             for w in (self.setbar, self.sep, self.txt_frame, self.bot_area):
#                 w.pack_forget()
#             self.root.geometry(f'{self.root.winfo_width()}x30')
#         else:
#             self.root.geometry(f'{self.root.winfo_width()}x{self._saved_h}')
#             self.sep.pack(fill='x', after=self.topbar)
#             if self._settings_open:
#                 self.setbar.pack(fill='x', after=self.topbar)
#                 self._retheme_setbar()
#             self.txt_frame.pack(fill='both', expand=True)
#             self.bot_area.pack(fill='x', side='bottom')

#     def toggle_settings(self):
#         self._settings_open = not self._settings_open
#         if self._settings_open:
#             self.setbar.pack(fill='x', after=self.topbar)
#             self._retheme_setbar()
#         else:
#             self.setbar.pack_forget()

#     def _on_font_size(self, val):
#         self.font_size = int(float(val))
#         self.txt.config(font=(self.font_fam, self.font_size))

#     def _on_spacing(self, val):
#         sp = int(float(val))
#         self.line_spacing = sp
#         self.txt.config(spacing1=sp, spacing2=sp//2, spacing3=sp)

#     # ─────────────────────────────────────────────────
#     # 章节目录
#     # ─────────────────────────────────────────────────
#     def open_chapters(self):
#         if not self.chapters:
#             messagebox.showinfo('提示','请先打开一本小说'); return

#         t  = self._cur_theme()
#         bg, fg, bar, sel = t['bg'], t['fg'], t['bar'], t['sel']
#         marks_set = set(self._get_mark_chapters())

#         win = tk.Toplevel(self.root)
#         win.title('章节目录')
#         win.geometry('300x480')
#         win.resizable(True, True)
#         win.attributes('-topmost', True)
#         win.configure(bg=bg)

#         hdr = tk.Frame(win, bg=bar, height=28)
#         hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr, text='📑 章节目录', font=('',9,'bold'),
#                  bg=bar, fg=fg).pack(side='left', padx=8, pady=4)
#         tk.Button(hdr, text='×', relief='flat', font=('',10),
#                   bg=bar, fg=fg, command=win.destroy).pack(side='right', padx=6)

#         sf = tk.Frame(win, bg=bg); sf.pack(fill='x', padx=6, pady=(6,2))
#         sv = tk.StringVar()
#         se = tk.Entry(sf, textvariable=sv, font=('',9), bg=bg, fg=fg,
#                       insertbackground=fg, relief='groove')
#         se.pack(fill='x', ipady=3)
#         PH = '搜索章节名...'
#         se.insert(0, PH); se.config(fg='gray')
#         se.bind('<FocusIn>',  lambda e:(se.delete(0,'end'),se.config(fg=fg)) if se.get()==PH else None)
#         se.bind('<FocusOut>', lambda e:(se.insert(0,PH),se.config(fg='gray')) if not se.get() else None)

#         lf = tk.Frame(win, bg=bg); lf.pack(fill='both', expand=True, padx=4, pady=4)
#         sb2 = tk.Scrollbar(lf); sb2.pack(side='right', fill='y')
#         lb = tk.Listbox(lf, font=('',10), relief='flat', bg=bg, fg=fg,
#                         selectbackground=sel, selectforeground=fg,
#                         borderwidth=0, highlightthickness=0,
#                         activestyle='none', yscrollcommand=sb2.set)
#         lb.pack(fill='both', expand=True); sb2.config(command=lb.yview)

#         btn_j = tk.Button(win, text='↩  跳转到选中章节', font=('',9,'bold'),
#                           bg=bar, fg=fg, relief='flat', pady=5)
#         btn_j.pack(fill='x', padx=6, pady=4)

#         all_ch  = list(self.chapters)
#         visible = list(range(len(all_ch)))

#         def fill(indices):
#             visible.clear(); visible.extend(indices)
#             lb.delete(0,'end')
#             for i in indices:
#                 flag = ' 🏴' if i in marks_set else ''
#                 lb.insert('end', f'  {i+1}. {all_ch[i]["title"]}{flag}')

#         fill(range(len(all_ch)))
#         try: lb.see(self.cur_ch); lb.selection_set(self.cur_ch)
#         except: pass

#         def on_search(*_):
#             q = sv.get().strip()
#             fill(range(len(all_ch))) if q in ('',PH) else \
#             fill([i for i,c in enumerate(all_ch) if q in c['title']])
#         sv.trace_add('write', on_search)

#         def jump(event=None):
#             idxs = lb.curselection()
#             if not idxs: return
#             win.destroy()
#             self.goto_chapter(visible[idxs[0]])

#         btn_j.config(command=jump)
#         lb.bind('<Double-Button-1>', jump)
#         lb.bind('<Return>', jump)

#         rx = self.root.winfo_x() + self.root.winfo_width() + 8
#         ry = self.root.winfo_y()
#         win.geometry(f'300x480+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 快捷键
#     # ─────────────────────────────────────────────────
#     def _bind_keys(self):
#         r = self.root
#         r.bind('<KeyPress-s>',   lambda e: self._scroll_down_screen())
#         r.bind('<KeyPress-S>',   lambda e: self._scroll_down_screen())
#         r.bind('<Right>',        lambda e: self.next_chapter())
#         r.bind('<Left>',         lambda e: self.prev_chapter())
#         r.bind('<Down>',         lambda e: self._scroll_down_screen())
#         r.bind('<Up>',           lambda e: self.txt.yview_scroll(-3,'units'))
#         r.bind('<KeyPress-o>',   lambda e: self.add_mark())
#         r.bind('<KeyPress-O>',   lambda e: self.add_mark())
#         r.bind('<KeyPress-d>',   self._dp)
#         r.bind('<KeyPress-D>',   self._dp)
#         r.bind('<KeyRelease-d>', self._dr)
#         r.bind('<KeyRelease-D>', self._dr)
#         r.bind('<KeyPress-e>',   self._ep)
#         r.bind('<KeyPress-E>',   self._ep)
#         r.focus_set()

#     def _dp(self, e): self._d_held = True
#     def _dr(self, e): self._d_held = False
#     def _ep(self, e):
#         if self._d_held: self.toggle_minimize()


# # ══════════════════════════════════════════════════════════════
# if __name__ == '__main__':
#     try:
#         from ctypes import windll
#         windll.shcore.SetProcessDpiAwareness(1)
#     except: pass
#     App()


# """
# 摸鱼阅读器 v8.0  —  全功能版
# 功能：
#   阅读体验：章节滚动、翻页、字号/行距/字色/背景/护眼模式、透明度、屏幕取色
#   书架管理：添加/删除/重命名书籍、显示封面/进度/上次阅读时间
#   阅读进度：自动记录、书架显示进度条
#   笔记系统：N键在当前章节创建笔记、查看/编辑/删除笔记
#   书签系统：O键快速书签、书签列表跳转删除
#   听书TTS ：F5启动/停止，支持语速调整（需系统 pyttsx3 或 espeak）
#   竖向拖拽滚动条、目录跳转、搜索

# 运行：python novel_reader.py
# 依赖：pip install pyttsx3   （TTS，可选）
#       pip install pillow     （屏幕取色，可选）
# """

# import tkinter as tk
# from tkinter import ttk, filedialog, colorchooser, messagebox, scrolledtext
# import os, re, zipfile, sys, json, copy, threading, time, datetime
# from html.parser import HTMLParser


# # ══════════════════════════════════════════════════════════════
# # HTML → 纯文本
# # ══════════════════════════════════════════════════════════════
# class _H2T(HTMLParser):
#     SKIP  = {'script','style','head','meta','link'}
#     BLOCK = {'p','div','br','h1','h2','h3','h4','h5',
#              'h6','li','tr','td','th','section','article'}
#     def __init__(self): super().__init__(); self.out, self._s = [], 0
#     def handle_starttag(self, tag, _):
#         if tag in self.SKIP:  self._s += 1
#         if tag in self.BLOCK: self.out.append('\n')
#     def handle_endtag(self, tag):
#         if tag in self.SKIP:  self._s = max(0, self._s-1)
#         if tag in self.BLOCK: self.out.append('\n')
#     def handle_data(self, d):
#         if not self._s: self.out.append(d)
#     def text(self): return re.sub(r'\n{3,}','\n\n',''.join(self.out)).strip()

# def html2text(s):
#     p = _H2T()
#     try: p.feed(s)
#     except: pass
#     return p.text()


# # ══════════════════════════════════════════════════════════════
# # EPUB
# # ══════════════════════════════════════════════════════════════
# def read_epub(path):
#     import xml.etree.ElementTree as ET
#     title = os.path.splitext(os.path.basename(path))[0]
#     body  = ''
#     try:
#         with zipfile.ZipFile(path) as z:
#             ns = z.namelist()
#             opf, odir = '', ''
#             if 'META-INF/container.xml' in ns:
#                 for el in ET.fromstring(z.read('META-INF/container.xml')).iter():
#                     if el.tag.endswith('rootfile'):
#                         opf = el.get('full-path',''); odir = opf.rsplit('/',1)[0] if '/' in opf else ''; break
#             items, spine = {}, []
#             if opf and opf in ns:
#                 root = ET.fromstring(z.read(opf))
#                 for el in root.iter():
#                     tag = el.tag.split('}')[-1]
#                     if tag == 'item':
#                         mid,href,mt = el.get('id',''),el.get('href',''),el.get('media-type','')
#                         if href and ('html' in mt or href.endswith(('.html','.xhtml','.htm'))):
#                             items[mid] = (odir+'/'+href).lstrip('/') if odir else href
#                     elif tag == 'itemref':
#                         r = el.get('idref','')
#                         if r in items: spine.append(items[r])
#                     elif tag == 'title' and el.text: title = el.text
#             if not spine:
#                 spine = sorted(f for f in ns if re.search(r'\.(html|htm|xhtml)$',f,re.I)
#                                and 'toc' not in f.lower() and 'nav' not in f.lower())
#             for href in spine:
#                 if href in ns:
#                     try: body += html2text(z.read(href).decode('utf-8','replace')) + '\n\n'
#                     except: pass
#     except Exception as e: body = f'[EPUB解析失败: {e}]'
#     return title, body.strip()


# # ══════════════════════════════════════════════════════════════
# # 章节切割
# # ══════════════════════════════════════════════════════════════
# _CH = re.compile(
#     r'^(第\s*[零一二三四五六七八九十百千万\d〇]+\s*[章节卷集回部篇][^\n]{0,40}'
#     r'|Chapter\s*\d+[^\n]{0,40}|CHAPTER\s*\d+[^\n]{0,40}|【[^\n]{1,30}】)', re.I)

# def split_chapters(text):
#     bounds = []
#     for m in re.finditer(r'^.+$', text, re.M):
#         line = m.group().strip()
#         if line and _CH.match(line): bounds.append((m.start(), line))
#     if not bounds: return [{'title':'全文','body':text}]
#     chs = []
#     for i,(pos,title) in enumerate(bounds):
#         end = bounds[i+1][0] if i+1<len(bounds) else len(text)
#         chs.append({'title':title,'body':text[pos:end]})
#     return chs


# # ══════════════════════════════════════════════════════════════
# # 数据存储
# # ══════════════════════════════════════════════════════════════
# DATA_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.moyu_data')
# os.makedirs(DATA_DIR, exist_ok=True)
# SHELF_FILE = os.path.join(DATA_DIR, 'shelf.json')
# NOTES_FILE = os.path.join(DATA_DIR, 'notes.json')
# MARKS_FILE = os.path.join(DATA_DIR, 'marks.json')

# def _jload(f):
#     try:
#         with open(f, encoding='utf-8') as fp: return json.load(fp)
#     except: return {}

# def _jsave(f, d):
#     try:
#         with open(f, 'w', encoding='utf-8') as fp: json.dump(d, fp, ensure_ascii=False, indent=2)
#     except: pass


# # ══════════════════════════════════════════════════════════════
# # TTS 引擎（可选）
# # ══════════════════════════════════════════════════════════════
# class TTS:
#     def __init__(self):
#         self._engine = None
#         self._thread = None
#         self._stop   = threading.Event()
#         self._text   = ''
#         self._rate   = 180
#         self._avail  = False
#         self._init()

#     def _init(self):
#         try:
#             import pyttsx3
#             self._engine = pyttsx3.init()
#             self._avail  = True
#         except:
#             self._avail = False

#     @property
#     def available(self): return self._avail

#     def set_rate(self, rate):
#         self._rate = int(rate)
#         if self._engine:
#             try: self._engine.setProperty('rate', self._rate)
#             except: pass

#     def speak(self, text, on_done=None):
#         if not self._avail: return
#         self.stop()
#         self._stop.clear()
#         self._text = text

#         def run():
#             try:
#                 import pyttsx3
#                 eng = pyttsx3.init()
#                 eng.setProperty('rate', self._rate)
#                 # 逐段朗读，支持中途停止
#                 paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
#                 for para in paragraphs:
#                     if self._stop.is_set(): break
#                     eng.say(para)
#                     eng.runAndWait()
#                 eng.stop()
#             except: pass
#             if on_done: on_done()

#         self._thread = threading.Thread(target=run, daemon=True)
#         self._thread.start()

#     def stop(self):
#         self._stop.set()
#         if self._engine:
#             try: self._engine.stop()
#             except: pass


# # ══════════════════════════════════════════════════════════════
# # 屏幕取色器
# # ══════════════════════════════════════════════════════════════
# def screen_color_picker(callback):
#     try: from PIL import ImageGrab
#     except ImportError:
#         c = colorchooser.askcolor(title='选择颜色')
#         if c and c[1]: callback(c[1])
#         return
#     from PIL import ImageGrab, Image, ImageTk
#     ZOOM,HALF = 10,5; CS = (HALF*2+1)*ZOOM
#     preview = tk.Toplevel(); preview.overrideredirect(True)
#     preview.attributes('-topmost',True); preview.configure(bg='#1a1a1a')
#     preview.geometry(f'{CS+4}x{CS+28}+200+200')
#     canvas = tk.Canvas(preview,width=CS,height=CS,bg='#000',highlightthickness=1,
#                        highlightbackground='#555',cursor='none')
#     canvas.pack(padx=2,pady=(2,0))
#     lbl = tk.Label(preview,text='#000000',font=('Consolas',9,'bold'),bg='#1a1a1a',fg='white',pady=1)
#     lbl.pack()
#     cur,ph,aid,done = ['#000000'],[None],[None],[False]
#     def update():
#         if done[0]: return
#         try:
#             mx,my = preview.winfo_pointerx(),preview.winfo_pointery()
#             img = ImageGrab.grab(bbox=(mx-HALF,my-HALF,mx+HALF+1,my+HALF+1))
#             zoomed = img.resize((CS,CS),Image.NEAREST); ph[0]=ImageTk.PhotoImage(zoomed)
#             canvas.delete('all'); canvas.create_image(0,0,anchor='nw',image=ph[0])
#             c2=CS//2
#             canvas.create_line(c2,0,c2,CS,fill='white',width=1)
#             canvas.create_line(0,c2,CS,c2,fill='white',width=1)
#             canvas.create_rectangle(c2-ZOOM,c2-ZOOM,c2+ZOOM,c2+ZOOM,outline='white',width=2)
#             px=img.getpixel((HALF,HALF)); hx='#{:02x}{:02x}{:02x}'.format(px[0],px[1],px[2])
#             cur[0]=hx; lbl.config(text=hx)
#             sw,sh=preview.winfo_screenwidth(),preview.winfo_screenheight()
#             ox,oy=mx+18,my+18
#             if ox+CS+10>sw: ox=mx-CS-22
#             if oy+CS+32>sh: oy=my-CS-34
#             preview.geometry(f'+{ox}+{oy}')
#         except: pass
#         aid[0]=preview.after(40,update)
#     def finish():
#         done[0]=True
#         if aid[0]:
#             try: preview.after_cancel(aid[0])
#             except: pass
#         for w in (overlay,preview):
#             try: w.destroy()
#             except: pass
#     overlay = tk.Toplevel(); overlay.overrideredirect(True)
#     overlay.attributes('-topmost',True); overlay.attributes('-alpha',0.01)
#     sw,sh=overlay.winfo_screenwidth(),overlay.winfo_screenheight()
#     overlay.geometry(f'{sw}x{sh}+0+0'); overlay.configure(bg='white',cursor='crosshair')
#     overlay.bind('<Button-1>',lambda e:(finish(),callback(cur[0])))
#     overlay.bind('<Escape>',lambda e:finish())
#     overlay.focus_force(); aid[0]=preview.after(40,update)


# # ══════════════════════════════════════════════════════════════
# # 自定义竖向滚动条
# # ══════════════════════════════════════════════════════════════
# class SmoothScrollbar:
#     W = 10
#     def __init__(self, parent, on_scroll):
#         self.on_scroll = on_scroll
#         self._lo,self._hi = 0.0,1.0
#         self._dragging = False; self._drag_start_y = 0; self._drag_start_lo = 0.0
#         self.c_bg='#ebdbb2'; self.c_track='#d5c4a1'; self.c_thumb='#b8a882'; self.c_hover='#8f7a55'
#         self.cv = tk.Canvas(parent, width=self.W, highlightthickness=0, cursor='arrow')
#         self.cv.pack(side='right', fill='y')
#         self.cv.bind('<Configure>', lambda e: self._draw())
#         self.cv.bind('<ButtonPress-1>',   self._press)
#         self.cv.bind('<B1-Motion>',       self._drag)
#         self.cv.bind('<ButtonRelease-1>', self._release)
#         self.cv.bind('<Enter>', lambda e: self._hover(True))
#         self.cv.bind('<Leave>', lambda e: self._hover(False))
#         self._hovered = False

#     def set(self, lo, hi): self._lo,self._hi = float(lo),float(hi); self._draw()

#     def set_colors(self, bg, track, thumb, thumb_hover):
#         self.c_bg=bg; self.c_track=track; self.c_thumb=thumb; self.c_hover=thumb_hover; self._draw()

#     def _draw(self):
#         cv=self.cv; W=self.W; H=cv.winfo_height()
#         if H<4: return
#         cv.delete('all'); PAD=2
#         cv.create_rectangle(0,0,W,H,fill=self.c_bg,outline='')
#         tx=W//2
#         cv.create_line(tx,PAD,tx,H-PAD,fill=self.c_track,width=W-4,capstyle='round')
#         th=max(20,int((self._hi-self._lo)*(H-2*PAD))); ty=PAD+int(self._lo*(H-2*PAD))
#         ty2=min(H-PAD,ty+th); color=self.c_hover if self._hovered else self.c_thumb
#         r=(W-4)//2; x1,x2=2,W-2; y1,y2=ty,ty2
#         if y2-y1>=2*r:
#             cv.create_rectangle(x1,y1+r,x2,y2-r,fill=color,outline='')
#             cv.create_oval(x1,y1,x2,y1+2*r,fill=color,outline='')
#             cv.create_oval(x1,y2-2*r,x2,y2,fill=color,outline='')
#         else: cv.create_oval(x1,y1,x2,y2,fill=color,outline='')

#     def _hover(self, v): self._hovered=v; self._draw()

#     def _y_to_frac(self,y):
#         H=self.cv.winfo_height(); PAD=2
#         return max(0.0,min(1.0,(y-PAD)/max(1,H-2*PAD)))

#     def _thumb_range(self):
#         H=self.cv.winfo_height(); PAD=2
#         th=max(20,int((self._hi-self._lo)*(H-2*PAD))); ty=PAD+int(self._lo*(H-2*PAD))
#         return ty,ty+th

#     def _press(self, e):
#         ty1,ty2=self._thumb_range()
#         if ty1<=e.y<=ty2:
#             self._dragging=True; self._drag_start_y=e.y; self._drag_start_lo=self._lo
#         else:
#             frac=self._y_to_frac(e.y); span=self._hi-self._lo
#             self.on_scroll(max(0.0,min(1.0-span,frac-span/2)))

#     def _drag(self, e):
#         if not self._dragging: return
#         H=self.cv.winfo_height(); PAD=2; dy=e.y-self._drag_start_y
#         delta=dy/max(1,H-2*PAD); span=self._hi-self._lo
#         target=max(0.0,min(1.0-span,self._drag_start_lo+delta))
#         self._lo=target; self._hi=target+span; self._draw(); self.on_scroll(target)

#     def _release(self, e): self._dragging=False


# # ══════════════════════════════════════════════════════════════
# # 主程序
# # ══════════════════════════════════════════════════════════════
# class App:

#     THEMES = {
#         '暖黄': dict(bg='#fdf6e3',fg='#3c3836',bar='#ebdbb2',sel='#d5c4a1',thumb='#b8a882',thumb_h='#8f7a55'),
#         '夜间': dict(bg='#1e1e2e',fg='#cdd6f4',bar='#181825',sel='#313244',thumb='#45475a',thumb_h='#6c7086'),
#         '护眼': dict(bg='#1a2f1a',fg='#a8d5a2',bar='#152315',sel='#2d5a2d',thumb='#3a6b3a',thumb_h='#57c454'),
#         '纸张': dict(bg='#f5f0e8',fg='#2c2416',bar='#ede4d0',sel='#c8b89a',thumb='#c8a882',thumb_h='#8b6045'),
#         '白底': dict(bg='#ffffff',fg='#1a1a1a',bar='#f0f0f0',sel='#dddddd',thumb='#bbbbbb',thumb_h='#888888'),
#     }

#     def __init__(self):
#         self.root = tk.Tk()
#         self.root.title('摸鱼阅读器')
#         self.root.geometry('440x600')
#         self.root.minsize(320, 400)
#         self.root.attributes('-topmost', True)

#         # 数据
#         self.shelf   = _jload(SHELF_FILE)   # {path: {title,last_ch,total_ch,last_time,read_time}}
#         self.notes   = _jload(NOTES_FILE)   # {path: [{ch,title,content,time}]}
#         self.marks   = _jload(MARKS_FILE)   # {path: [{ch,ch_title,time}]}

#         self.book_path  = ''
#         self.book_title = ''
#         self.chapters   = []
#         self.cur_ch     = 0

#         # UI 状态
#         self.theme_name     = '暖黄'
#         self.custom_bg      = None
#         self.custom_bar     = None
#         self.font_size      = 14
#         self.line_spacing   = 6
#         self.font_fam       = ('宋体' if sys.platform=='win32'
#                                else 'Songti SC' if sys.platform=='darwin'
#                                else 'Noto Serif CJK SC')
#         self._d_held        = False
#         self._minimized     = False
#         self._settings_open = False
#         self._wheel_accum   = 0
#         self._tts_playing   = False

#         self.tts = TTS()

#         self._build_ui()
#         self._apply_theme()
#         self._bind_keys()
#         self.root.protocol('WM_DELETE_WINDOW', self._on_close)
#         self.root.mainloop()

#     # ─────────────────────────────────────────────────
#     # UI 构建
#     # ─────────────────────────────────────────────────
#     def _build_ui(self):
#         r = self.root

#         # 顶部栏
#         self.topbar = tk.Frame(r, height=30)
#         self.topbar.pack(fill='x')
#         self.topbar.pack_propagate(False)

#         dots = tk.Frame(self.topbar)
#         dots.pack(side='left', padx=6, pady=5)
#         self._dot(dots, '#ff5f57', self.toggle_minimize)
#         self._dot(dots, '#ffbd2e', self.toggle_settings)
#         self._dot(dots, '#28ca41', self.open_file)

#         self.lbl_title = tk.Label(self.topbar, text='摸鱼阅读器', font=('',9))
#         self.lbl_title.pack(side='left', fill='x', expand=True)

#         rbf = tk.Frame(self.topbar); rbf.pack(side='right', padx=2)
#         self._tbtn(rbf, '书架', self.open_shelf)
#         self._tbtn(rbf, '目录', self.open_chapters)
#         self._tbtn(rbf, '笔记', self.open_notes)
#         self._tbtn(rbf, '书签', self.open_marks)
#         self._tbtn(rbf, '打开', self.open_file)
#         self._tbtn(rbf, '×',   r.destroy)

#         for w in (self.topbar, self.lbl_title):
#             w.bind('<ButtonPress-1>', self._drag_start)
#             w.bind('<B1-Motion>',     self._drag_move)

#         # 设置栏
#         self.setbar = tk.Frame(r)
#         self._build_setbar()

#         # 分隔线
#         self.sep = tk.Frame(r, height=1)
#         self.sep.pack(fill='x')

#         # 文本区
#         self.txt_frame = tk.Frame(r)
#         self.txt_frame.pack(fill='both', expand=True)

#         self.vsb = SmoothScrollbar(self.txt_frame,
#                                    on_scroll=lambda f: self.txt.yview_moveto(f))

#         self.txt = tk.Text(
#             self.txt_frame, wrap='word',
#             relief='flat', padx=16, pady=10,
#             state='disabled', cursor='arrow',
#             font=(self.font_fam, self.font_size),
#             borderwidth=0, highlightthickness=0,
#             spacing1=self.line_spacing,
#             spacing2=self.line_spacing//2,
#             spacing3=self.line_spacing,
#             yscrollcommand=self._on_yscroll,
#         )
#         self.txt.pack(side='left', fill='both', expand=True)
#         self.txt.bind('<Button-1>',   self._on_click)
#         self.txt.bind('<MouseWheel>', self._on_wheel)
#         self.txt.bind('<Button-4>',   self._on_wheel)
#         self.txt.bind('<Button-5>',   self._on_wheel)
#         self._show_welcome()

#         # 底部
#         self.bot_area = tk.Frame(r)
#         self.bot_area.pack(fill='x', side='bottom')

#         self.botbar = tk.Frame(self.bot_area, height=28)
#         self.botbar.pack(fill='x')
#         self.botbar.pack_propagate(False)

#         self.btn_prev = tk.Button(self.botbar, text='◀', font=('',9),
#                                   relief='flat', padx=4, command=self.prev_chapter)
#         self.btn_prev.pack(side='left', padx=4, pady=3)

#         self.lbl_prog = tk.Label(self.botbar, text='', font=('',8))
#         self.lbl_prog.pack(side='left', expand=True)

#         self.btn_tts = tk.Button(self.botbar, text='🔊', font=('',9),
#                                  relief='flat', padx=3, command=self.toggle_tts)
#         self.btn_tts.pack(side='right', padx=2, pady=3)

#         self.btn_note = tk.Button(self.botbar, text='✏', font=('',9),
#                                   relief='flat', padx=3, command=self.add_note)
#         self.btn_note.pack(side='right', padx=2, pady=3)

#         self.btn_mark = tk.Button(self.botbar, text='🔖', font=('',9),
#                                   relief='flat', padx=2, command=self.add_mark)
#         self.btn_mark.pack(side='right', padx=2, pady=3)

#         self.btn_next = tk.Button(self.botbar, text='▶', font=('',9),
#                                   relief='flat', padx=4, command=self.next_chapter)
#         self.btn_next.pack(side='right', padx=4, pady=3)

#     def _tbtn(self, parent, text, cmd):
#         tk.Button(parent, text=text, font=('',8), relief='flat',
#                   padx=3, command=cmd).pack(side='left', padx=1)

#     def _dot(self, p, color, cmd):
#         lb = tk.Label(p, text='⬤', fg=color, font=('',12), cursor='hand2')
#         lb.pack(side='left', padx=2)
#         lb.bind('<Button-1>', lambda e: cmd())

#     # ─────────────────────────────────────────────────
#     # 设置栏
#     # ─────────────────────────────────────────────────
#     def _build_setbar(self):
#         def row(): f=tk.Frame(self.setbar); f.pack(fill='x',padx=8,pady=2); return f

#         r1 = row()
#         tk.Label(r1,text='字号',font=('',8)).pack(side='left')
#         self.sl_font = tk.Scale(r1,from_=10,to=32,orient='horizontal',length=70,
#                                 showvalue=True,font=('',7),command=self._on_font_size)
#         self.sl_font.set(self.font_size); self.sl_font.pack(side='left',padx=2)
#         tk.Label(r1,text='行距',font=('',8)).pack(side='left',padx=(8,0))
#         self.sl_spacing = tk.Scale(r1,from_=0,to=24,orient='horizontal',length=70,
#                                    showvalue=True,font=('',7),command=self._on_spacing)
#         self.sl_spacing.set(self.line_spacing); self.sl_spacing.pack(side='left',padx=2)

#         r2 = row()
#         tk.Label(r2,text='透明',font=('',8)).pack(side='left')
#         self.sl_alpha = tk.Scale(r2,from_=20,to=100,orient='horizontal',length=80,
#                                  showvalue=True,font=('',7),
#                                  command=lambda v: self.root.attributes('-alpha',int(v)/100))
#         self.sl_alpha.set(100); self.sl_alpha.pack(side='left',padx=2)
#         # TTS 语速
#         tk.Label(r2,text='语速',font=('',8)).pack(side='left',padx=(8,0))
#         self.sl_tts_rate = tk.Scale(r2,from_=80,to=300,orient='horizontal',length=70,
#                                     showvalue=True,font=('',7),
#                                     command=lambda v: self.tts.set_rate(int(v)))
#         self.sl_tts_rate.set(180); self.sl_tts_rate.pack(side='left',padx=2)

#         r3 = row()
#         tk.Label(r3,text='字色',font=('',8)).pack(side='left')
#         self.btn_fg_color = tk.Button(r3,text='  ',relief='groove',width=2,
#                                       font=('',8),command=self._pick_fg)
#         self.btn_fg_color.pack(side='left',padx=2)
#         tk.Label(r3,text='背景',font=('',8)).pack(side='left',padx=(6,0))
#         self.btn_bg_color = tk.Button(r3,text='  ',relief='groove',width=2,
#                                       font=('',8),command=self._pick_bg)
#         self.btn_bg_color.pack(side='left',padx=2)
#         tk.Button(r3,text='🎨取色',font=('',8),relief='flat',padx=4,
#                   command=self._screen_pick).pack(side='left',padx=4)
#         tk.Button(r3,text='重置',font=('',8),relief='flat',padx=4,
#                   command=self._reset_colors).pack(side='left',padx=2)

#         r4 = row()
#         tk.Label(r4,text='主题',font=('',8)).pack(side='left')
#         self.var_theme = tk.StringVar(value=self.theme_name)
#         cb = ttk.Combobox(r4,textvariable=self.var_theme,
#                           values=list(self.THEMES.keys()),width=7,font=('',8),state='readonly')
#         cb.pack(side='left',padx=4); cb.bind('<<ComboboxSelected>>',self._on_theme)
#         # 快速护眼切换
#         tk.Button(r4,text='☘护眼',font=('',8),relief='flat',padx=4,
#                   command=lambda: (self.var_theme.set('护眼'),self._on_theme())).pack(side='left',padx=2)
#         tk.Button(r4,text='🌙夜间',font=('',8),relief='flat',padx=4,
#                   command=lambda: (self.var_theme.set('夜间'),self._on_theme())).pack(side='left',padx=2)

#     # ─────────────────────────────────────────────────
#     # 颜色
#     # ─────────────────────────────────────────────────
#     def _pick_fg(self):
#         t=self._cur_theme(); c=colorchooser.askcolor(color=t['fg'],title='字体颜色')
#         if c and c[1]: self.THEMES[self.theme_name]['fg']=c[1]; self.txt.config(fg=c[1]); self.btn_fg_color.config(bg=c[1])

#     def _pick_bg(self):
#         c=colorchooser.askcolor(color=self._cur_theme()['bg'],title='背景颜色')
#         if c and c[1]: self._apply_custom_bg(c[1])

#     def _screen_pick(self):
#         alpha=self.sl_alpha.get()/100; self.root.attributes('-alpha',0.0)
#         def on(hx): self.root.after(100,lambda:self.root.attributes('-alpha',alpha)); self._apply_custom_bg(hx)
#         self.root.after(120, lambda: screen_color_picker(on))

#     def _apply_custom_bg(self,hx):
#         self.custom_bg=hx; self.custom_bar=self._darken(hx,0.88); self._apply_theme()
#         try: self.btn_bg_color.config(bg=hx)
#         except: pass

#     def _reset_colors(self): self.custom_bg=self.custom_bar=None; self._apply_theme()
#     def _darken(self,hx,f=0.88):
#         h=hx.lstrip('#')
#         return '#{:02x}{:02x}{:02x}'.format(int(int(h[0:2],16)*f),int(int(h[2:4],16)*f),int(int(h[4:6],16)*f))

#     def _cur_theme(self):
#         t=copy.copy(self.THEMES[self.theme_name])
#         if self.custom_bg:  t['bg']=self.custom_bg
#         if self.custom_bar: t['bar']=self.custom_bar
#         return t

#     def _on_theme(self, e=None):
#         self.theme_name=self.var_theme.get(); self.custom_bg=self.custom_bar=None; self._apply_theme()

#     def _apply_theme(self):
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         self.root.configure(bg=bar)
#         self._cf(self.topbar,bar,fg); self._cf(self.botbar,bar,fg); self._cf(self.bot_area,bar,fg)
#         self.sep.config(bg=sel); self.txt_frame.config(bg=bg)
#         self.vsb.cv.config(bg=bg)
#         self.vsb.set_colors(bg=bg,track=sel,thumb=t.get('thumb',sel),thumb_hover=t.get('thumb_h',fg))
#         self.txt.config(bg=bg,fg=fg,insertbackground=fg,selectbackground=sel)
#         self.lbl_prog.config(bg=bar,fg=fg)
#         for b in (self.btn_prev,self.btn_next,self.btn_mark,self.btn_note,self.btn_tts):
#             b.config(bg=bar,fg=fg,activebackground=sel)
#         self._retheme_setbar()
#         try:
#             if self.custom_bg: self.btn_bg_color.config(bg=self.custom_bg)
#         except: pass

#     def _cf(self,fr,bg,fg):
#         try: fr.config(bg=bg)
#         except: pass
#         for w in fr.winfo_children():
#             try: w.config(bg=bg,fg=fg,activebackground=bg)
#             except: pass
#             for w2 in w.winfo_children():
#                 try: w2.config(bg=bg,fg=fg,activebackground=bg)
#                 except: pass

#     def _retheme_setbar(self):
#         t=self._cur_theme(); bg,fg,sel=t['bar'],t['fg'],t['sel']
#         self._cf(self.setbar,bg,fg)
#         for sl in (self.sl_font,self.sl_alpha,self.sl_spacing,self.sl_tts_rate):
#             try: sl.config(bg=bg,fg=fg,troughcolor=sel,activebackground=sel)
#             except: pass
#         try: self.btn_fg_color.config(bg=fg)
#         except: pass

#     # ─────────────────────────────────────────────────
#     # 字号 / 行距
#     # ─────────────────────────────────────────────────
#     def _on_font_size(self,val):
#         self.font_size=int(float(val)); self.txt.config(font=(self.font_fam,self.font_size))

#     def _on_spacing(self,val):
#         sp=int(float(val)); self.line_spacing=sp
#         self.txt.config(spacing1=sp,spacing2=sp//2,spacing3=sp)

#     # ─────────────────────────────────────────────────
#     # 拖动窗口
#     # ─────────────────────────────────────────────────
#     def _drag_start(self,e): self._dx=e.x_root-self.root.winfo_x(); self._dy=e.y_root-self.root.winfo_y()
#     def _drag_move(self,e):  self.root.geometry(f'+{e.x_root-self._dx}+{e.y_root-self._dy}')

#     # ─────────────────────────────────────────────────
#     # 打开文件
#     # ─────────────────────────────────────────────────
#     def open_file(self, path=None):
#         if path is None:
#             path = filedialog.askopenfilename(
#                 title='打开小说',
#                 filetypes=[('小说文件','*.txt *.epub *.md'),('所有文件','*.*')])
#         if not path: return
#         ext = os.path.splitext(path)[1].lower()
#         if ext == '.epub': title,text = read_epub(path)
#         else:
#             title = os.path.splitext(os.path.basename(path))[0]
#             try:
#                 with open(path,encoding='utf-8',errors='replace') as f: text=f.read()
#             except Exception as e: messagebox.showerror('错误',str(e)); return
#         self.book_path=path; self.book_title=title
#         self.lbl_title.config(text=f'  {title}'); self.root.title(f'摸鱼阅读器 — {title}')
#         self._load(text)

#     def _load(self,text):
#         self.chapters = split_chapters(text)
#         # 恢复上次阅读位置
#         si = self.shelf.get(self.book_path,{})
#         self.cur_ch = max(0,min(si.get('last_ch',0),len(self.chapters)-1))
#         # 更新书架
#         self._shelf_update()
#         self._render_chapter()

#     # ─────────────────────────────────────────────────
#     # 书架管理
#     # ─────────────────────────────────────────────────
#     def _shelf_update(self):
#         p = self.book_path
#         prev = self.shelf.get(p,{})
#         self.shelf[p] = {
#             'title':      self.book_title,
#             'path':       p,
#             'last_ch':    self.cur_ch,
#             'total_ch':   len(self.chapters),
#             'last_time':  datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
#             'added_time': prev.get('added_time', datetime.datetime.now().strftime('%Y-%m-%d')),
#         }
#         _jsave(SHELF_FILE, self.shelf)

#     def open_shelf(self):
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('书架'); win.geometry('380x460')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)

#         hdr=tk.Frame(win,bg=bar,height=30); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='📚 书架',font=('',10,'bold'),bg=bar,fg=fg).pack(side='left',padx=10,pady=5)
#         tk.Button(hdr,text='+添加',font=('',8),relief='flat',bg=bar,fg=fg,
#                   command=lambda:self._shelf_add(win)).pack(side='right',padx=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,
#                   command=win.destroy).pack(side='right',padx=4)

#         # 书籍列表
#         frame=tk.Frame(win,bg=bg); frame.pack(fill='both',expand=True,padx=6,pady=6)
#         sb2=tk.Scrollbar(frame); sb2.pack(side='right',fill='y')
#         canvas=tk.Canvas(frame,bg=bg,highlightthickness=0,yscrollcommand=sb2.set)
#         canvas.pack(fill='both',expand=True); sb2.config(command=canvas.yview)
#         inner=tk.Frame(canvas,bg=bg); canvas.create_window((0,0),window=inner,anchor='nw')

#         def refresh():
#             for w in inner.winfo_children(): w.destroy()
#             if not self.shelf:
#                 tk.Label(inner,text='书架空空，快去添加书吧',font=('',10),bg=bg,fg=sel).pack(pady=30)
#             for path,info in sorted(self.shelf.items(),key=lambda x:x[1].get('last_time',''),reverse=True):
#                 self._shelf_card(inner,path,info,bg,fg,bar,sel,win,refresh)
#             inner.update_idletasks()
#             canvas.config(scrollregion=canvas.bbox('all'))
#         refresh()

#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'380x460+{rx}+{ry}')

#     def _shelf_card(self,parent,path,info,bg,fg,bar,sel,shelf_win,refresh):
#         card=tk.Frame(parent,bg=bar,relief='flat',bd=0)
#         card.pack(fill='x',padx=4,pady=3)
#         # 封面色块
#         colors=['#8f3f71','#458588','#d79921','#689d6a','#cc241d']
#         ccolor=colors[hash(path)%len(colors)]
#         cover=tk.Frame(card,bg=ccolor,width=36,height=50); cover.pack(side='left',padx=6,pady=6); cover.pack_propagate(False)
#         tk.Label(cover,text='📖',font=('',14),bg=ccolor).pack(expand=True)
#         # 信息
#         info_f=tk.Frame(card,bg=bar); info_f.pack(side='left',fill='both',expand=True,pady=4)
#         tk.Label(info_f,text=info.get('title','未知'),font=('',9,'bold'),bg=bar,fg=fg,anchor='w').pack(fill='x')
#         lc=info.get('last_ch',0); tc=info.get('total_ch',1)
#         pct=int(lc/max(1,tc-1)*100) if tc>1 else 0
#         tk.Label(info_f,text=f'第{lc+1}/{tc}章  {pct}%',font=('',8),bg=bar,fg=sel,anchor='w').pack(fill='x')
#         # 进度条
#         pb_f=tk.Frame(info_f,bg=bar,height=4); pb_f.pack(fill='x',pady=2); pb_f.pack_propagate(False)
#         pb_done=tk.Frame(pb_f,bg=ccolor,height=4); pb_done.place(x=0,y=0,relwidth=pct/100,relheight=1)
#         tk.Frame(pb_f,bg=sel,height=4).place(x=0,y=0,relwidth=1,relheight=1)
#         pb_done.lift()
#         tk.Label(info_f,text=f'上次：{info.get("last_time","")}',font=('',7),bg=bar,fg=sel,anchor='w').pack(fill='x')
#         # 按钮
#         btn_f=tk.Frame(card,bg=bar); btn_f.pack(side='right',padx=6,pady=4)
#         def open_it(p=path):
#             shelf_win.destroy(); self.open_file(p)
#         def del_it(p=path):
#             if messagebox.askyesno('删除','从书架移除此书？',parent=shelf_win):
#                 del self.shelf[p]; _jsave(SHELF_FILE,self.shelf); refresh()
#         tk.Button(btn_f,text='阅读',font=('',8),relief='flat',bg=ccolor,fg='white',
#                   padx=6,command=open_it).pack(pady=2)
#         tk.Button(btn_f,text='移除',font=('',7),relief='flat',bg=bar,fg=sel,
#                   padx=4,command=del_it).pack(pady=2)

#     def _shelf_add(self, shelf_win):
#         path=filedialog.askopenfilename(title='选择书籍',
#             filetypes=[('小说文件','*.txt *.epub *.md'),('所有文件','*.*')])
#         if not path: return
#         if path not in self.shelf:
#             title=os.path.splitext(os.path.basename(path))[0]
#             self.shelf[path]={'title':title,'path':path,'last_ch':0,'total_ch':0,
#                               'last_time':'','added_time':datetime.datetime.now().strftime('%Y-%m-%d')}
#             _jsave(SHELF_FILE,self.shelf)
#         shelf_win.destroy(); self.open_shelf()

#     # ─────────────────────────────────────────────────
#     # 渲染章节
#     # ─────────────────────────────────────────────────
#     def _render_chapter(self, scroll_to_top=True):
#         if not self.chapters: return
#         self.cur_ch=max(0,min(self.cur_ch,len(self.chapters)-1))
#         ch=self.chapters[self.cur_ch]
#         self.txt.config(state='normal'); self.txt.delete('1.0','end')
#         self.txt.insert('1.0', ch['body']); self.txt.config(state='disabled')
#         if scroll_to_top: self.txt.yview_moveto(0.0)
#         self._update_nav(); self._wheel_accum=0
#         self._shelf_update()

#     def _update_nav(self):
#         n=len(self.chapters); idx=self.cur_ch+1
#         # 有无书签/笔记标记
#         m_chs={m['ch'] for m in self.marks.get(self.book_path,[])}
#         n_chs={n2['ch'] for n2 in self.notes.get(self.book_path,[])}
#         flags=('🔖' if self.cur_ch in m_chs else '')+('✏' if self.cur_ch in n_chs else '')
#         self.lbl_prog.config(text=f'{flags}  第{idx}/{n}章')
#         self.btn_prev.config(state='normal' if self.cur_ch>0   else 'disabled')
#         self.btn_next.config(state='normal' if self.cur_ch<n-1 else 'disabled')

#     def _on_yscroll(self,lo,hi): self.vsb.set(lo,hi)

#     # ─────────────────────────────────────────────────
#     # 翻章
#     # ─────────────────────────────────────────────────
#     def next_chapter(self):
#         if self.chapters and self.cur_ch<len(self.chapters)-1:
#             self.cur_ch+=1; self._render_chapter()

#     def prev_chapter(self):
#         if self.chapters and self.cur_ch>0:
#             self.cur_ch-=1; self._render_chapter()

#     def goto_chapter(self,idx):
#         if not self.chapters: return
#         self.cur_ch=max(0,min(idx,len(self.chapters)-1)); self._render_chapter()

#     def _on_click(self,e):
#         w=self.txt.winfo_width()
#         if   e.x<w*0.28: self.prev_chapter()
#         elif e.x>w*0.72: self.next_chapter()

#     def _on_wheel(self,e):
#         delta=1 if e.num==4 else (-1 if e.num==5 else (1 if e.delta>0 else -1))
#         top,bot=self.txt.yview()
#         if delta<0:
#             if bot>=0.999:
#                 self._wheel_accum-=1
#                 if self._wheel_accum<=-3: self.next_chapter(); return
#             else: self._wheel_accum=0; self.txt.yview_scroll(3,'units')
#         else:
#             if top<=0.001:
#                 self._wheel_accum+=1
#                 if self._wheel_accum>=3:
#                     self.prev_chapter(); self.root.after(30,lambda:self.txt.yview_moveto(1.0)); return
#             else: self._wheel_accum=0; self.txt.yview_scroll(-3,'units')

#     def _scroll_down(self):
#         _,bot=self.txt.yview()
#         if bot>=0.999: self.next_chapter()
#         else: self.txt.yview_scroll(1,'pages')

#     # ─────────────────────────────────────────────────
#     # TTS 听书
#     # ─────────────────────────────────────────────────
#     def toggle_tts(self):
#         if not self.tts.available:
#             messagebox.showinfo('提示','请先安装 pyttsx3：\npip install pyttsx3'); return
#         if self._tts_playing:
#             self.tts.stop(); self._tts_playing=False
#             self.btn_tts.config(text='🔊')
#             self._toast('⏹ 已停止朗读')
#         else:
#             if not self.chapters: return
#             ch=self.chapters[self.cur_ch]
#             self._tts_playing=True; self.btn_tts.config(text='⏸')
#             self._toast('▶ 开始朗读…')
#             def done(): self.root.after(0,self._tts_done)
#             self.tts.speak(ch['body'],on_done=done)

#     def _tts_done(self):
#         self._tts_playing=False; self.btn_tts.config(text='🔊')

#     # ─────────────────────────────────────────────────
#     # 书签（O 键）
#     # ─────────────────────────────────────────────────
#     def add_mark(self):
#         if not self.book_path: messagebox.showinfo('提示','请先打开书'); return
#         marks=self.marks.setdefault(self.book_path,[])
#         ch=self.chapters[self.cur_ch]; now=datetime.datetime.now().strftime('%m-%d %H:%M')
#         existing=next((m for m in marks if m['ch']==self.cur_ch),None)
#         entry={'ch':self.cur_ch,'ch_title':ch['title'],'time':now}
#         if existing: existing.update(entry); self._toast('🔖 书签已更新')
#         else: marks.append(entry); self._toast(f'🔖 书签已添加  第{self.cur_ch+1}章')
#         _jsave(MARKS_FILE,self.marks); self._update_nav()

#     def open_marks(self):
#         marks=self.marks.get(self.book_path,[])
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('书签'); win.geometry('300x360')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='🔖 书签列表',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
#         lf=tk.Frame(win,bg=bg); lf.pack(fill='both',expand=True,padx=4,pady=4)
#         sb2=tk.Scrollbar(lf); sb2.pack(side='right',fill='y')
#         lb=tk.Listbox(lf,font=('',10),relief='flat',bg=bg,fg=fg,selectbackground=sel,
#                       selectforeground=fg,borderwidth=0,highlightthickness=0,
#                       activestyle='none',yscrollcommand=sb2.set)
#         lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
#         rows=list(marks)
#         for m in rows: lb.insert('end',f"  🏴 第{m['ch']+1}章  {m['ch_title']}  {m['time']}")
#         bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=6,pady=4)
#         def jump():
#             idxs=lb.curselection()
#             if not idxs: return
#             win.destroy(); self.goto_chapter(rows[idxs[0]]['ch'])
#         def delete():
#             idxs=lb.curselection()
#             if not idxs: return
#             m=rows.pop(idxs[0]); lb.delete(idxs[0])
#             self.marks[self.book_path]=[x for x in self.marks.get(self.book_path,[]) if x is not m]
#             _jsave(MARKS_FILE,self.marks); self._update_nav()
#         tk.Button(bf,text='跳转',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=jump).pack(side='left',padx=4)
#         tk.Button(bf,text='删除',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=delete).pack(side='left')
#         lb.bind('<Double-Button-1>',lambda e:jump())
#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'300x360+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 笔记（N 键）
#     # ─────────────────────────────────────────────────
#     def add_note(self):
#         if not self.book_path: messagebox.showinfo('提示','请先打开书'); return
#         ch=self.chapters[self.cur_ch]
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('添加笔记'); win.geometry('340x260')
#         win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text=f'✏ 笔记 — {ch["title"][:20]}',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
#         # 选中文字自动填入
#         sel_text=''
#         try: sel_text=self.txt.get(tk.SEL_FIRST,tk.SEL_LAST)
#         except: pass
#         if sel_text:
#             tk.Label(win,text='引用文字：',font=('',8),bg=bg,fg=fg).pack(anchor='w',padx=8,pady=(6,0))
#             ref=tk.Label(win,text=sel_text[:80]+'…' if len(sel_text)>80 else sel_text,
#                         font=('',8,'italic'),bg=sel,fg=fg,wraplength=300,anchor='w',justify='left')
#             ref.pack(fill='x',padx=8,pady=2)
#         tk.Label(win,text='笔记内容：',font=('',8),bg=bg,fg=fg).pack(anchor='w',padx=8,pady=(6,0))
#         ta=tk.Text(win,height=6,font=('',10),bg=bg,fg=fg,insertbackground=fg,
#                    relief='flat',padx=8,pady=4,wrap='word',borderwidth=1,highlightthickness=1,
#                    highlightbackground=sel,highlightcolor=fg)
#         ta.pack(fill='both',expand=True,padx=8,pady=4); ta.focus()
#         def save():
#             content=ta.get('1.0','end').strip()
#             if not content: win.destroy(); return
#             notes=self.notes.setdefault(self.book_path,[])
#             now=datetime.datetime.now().strftime('%m-%d %H:%M')
#             notes.append({'ch':self.cur_ch,'ch_title':ch['title'],'content':content,
#                           'quote':sel_text,'time':now})
#             _jsave(NOTES_FILE,self.notes); self._update_nav(); win.destroy()
#             self._toast('✏ 笔记已保存')
#         bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=8,pady=4)
#         tk.Button(bf,text='保存笔记',font=('',9,'bold'),bg=bar,fg=fg,relief='flat',
#                   padx=10,command=save).pack(side='right',padx=4)
#         win.bind('<Control-Return>',lambda e:save())

#     def open_notes(self):
#         notes=self.notes.get(self.book_path,[])
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('笔记'); win.geometry('360x480')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='✏ 笔记列表',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)

#         # 列表 + 详情
#         paned=tk.PanedWindow(win,orient='vertical',bg=bg,sashwidth=4,sashrelief='flat')
#         paned.pack(fill='both',expand=True,padx=4,pady=4)

#         top_f=tk.Frame(paned,bg=bg); paned.add(top_f,height=200)
#         sb2=tk.Scrollbar(top_f); sb2.pack(side='right',fill='y')
#         lb=tk.Listbox(top_f,font=('',9),relief='flat',bg=bg,fg=fg,selectbackground=sel,
#                       selectforeground=fg,borderwidth=0,highlightthickness=0,
#                       activestyle='none',yscrollcommand=sb2.set)
#         lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
#         rows=list(notes)
#         for n2 in rows: lb.insert('end',f"  第{n2['ch']+1}章  {n2['ch_title'][:16]}  {n2['time']}")

#         bot_f=tk.Frame(paned,bg=bg); paned.add(bot_f)
#         detail=tk.Text(bot_f,font=('',10),bg=bg,fg=fg,insertbackground=fg,
#                        relief='flat',padx=8,pady=6,wrap='word',state='disabled',
#                        borderwidth=0,highlightthickness=0)
#         detail.pack(fill='both',expand=True)

#         def show_detail(event=None):
#             idxs=lb.curselection()
#             if not idxs: return
#             n2=rows[idxs[0]]
#             detail.config(state='normal'); detail.delete('1.0','end')
#             if n2.get('quote'): detail.insert('end',f'引用：{n2["quote"]}\n\n','quote')
#             detail.insert('end',n2['content'])
#             detail.config(state='disabled')
#         lb.bind('<<ListboxSelect>>',show_detail)

#         bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=6,pady=4)
#         def jump():
#             idxs=lb.curselection()
#             if not idxs: return
#             win.destroy(); self.goto_chapter(rows[idxs[0]]['ch'])
#         def delete():
#             idxs=lb.curselection()
#             if not idxs: return
#             n2=rows.pop(idxs[0]); lb.delete(idxs[0])
#             self.notes[self.book_path]=[x for x in self.notes.get(self.book_path,[]) if x is not n2]
#             _jsave(NOTES_FILE,self.notes); self._update_nav()
#             detail.config(state='normal'); detail.delete('1.0','end'); detail.config(state='disabled')
#         tk.Button(bf,text='跳转章节',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=jump).pack(side='left',padx=4)
#         tk.Button(bf,text='删除笔记',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=delete).pack(side='left')
#         lb.bind('<Double-Button-1>',lambda e:jump())
#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'360x480+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 章节目录
#     # ─────────────────────────────────────────────────
#     def open_chapters(self):
#         if not self.chapters: messagebox.showinfo('提示','请先打开小说'); return
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         mark_set={m['ch'] for m in self.marks.get(self.book_path,[])}
#         note_set={n2['ch'] for n2 in self.notes.get(self.book_path,[])}
#         win=tk.Toplevel(self.root); win.title('章节目录'); win.geometry('300x500')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='📑 章节目录',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
#         sf=tk.Frame(win,bg=bg); sf.pack(fill='x',padx=6,pady=(6,2))
#         sv=tk.StringVar()
#         se=tk.Entry(sf,textvariable=sv,font=('',9),bg=bg,fg=fg,insertbackground=fg,relief='groove')
#         se.pack(fill='x',ipady=3)
#         PH='搜索章节名...'
#         se.insert(0,PH); se.config(fg='gray')
#         se.bind('<FocusIn>',lambda e:(se.delete(0,'end'),se.config(fg=fg)) if se.get()==PH else None)
#         se.bind('<FocusOut>',lambda e:(se.insert(0,PH),se.config(fg='gray')) if not se.get() else None)
#         lf=tk.Frame(win,bg=bg); lf.pack(fill='both',expand=True,padx=4,pady=4)
#         sb2=tk.Scrollbar(lf); sb2.pack(side='right',fill='y')
#         lb=tk.Listbox(lf,font=('',10),relief='flat',bg=bg,fg=fg,selectbackground=sel,
#                       selectforeground=fg,borderwidth=0,highlightthickness=0,
#                       activestyle='none',yscrollcommand=sb2.set)
#         lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
#         btn_j=tk.Button(win,text='↩ 跳转',font=('',9,'bold'),bg=bar,fg=fg,relief='flat',pady=5)
#         btn_j.pack(fill='x',padx=6,pady=4)
#         all_ch=list(self.chapters); visible=list(range(len(all_ch)))
#         def fill(indices):
#             visible.clear(); visible.extend(indices); lb.delete(0,'end')
#             for i in indices:
#                 flags=('🔖' if i in mark_set else '')+('✏' if i in note_set else '')
#                 cur='▶ ' if i==self.cur_ch else '  '
#                 lb.insert('end',f'{cur}{i+1}. {all_ch[i]["title"]}{flags}')
#         fill(range(len(all_ch)))
#         try: lb.see(self.cur_ch); lb.selection_set(self.cur_ch)
#         except: pass
#         def on_search(*_):
#             q=sv.get().strip()
#             fill(range(len(all_ch))) if q in ('',PH) else fill([i for i,c in enumerate(all_ch) if q in c['title']])
#         sv.trace_add('write',on_search)
#         def jump(e=None):
#             idxs=lb.curselection()
#             if not idxs: return
#             win.destroy(); self.goto_chapter(visible[idxs[0]])
#         btn_j.config(command=jump); lb.bind('<Double-Button-1>',jump); lb.bind('<Return>',jump)
#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'300x500+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # Toast 提示
#     # ─────────────────────────────────────────────────
#     def _toast(self,msg,ms=1500):
#         t=self._cur_theme()
#         try:
#             for w in self.root.winfo_children():
#                 if isinstance(w,tk.Label) and getattr(w,'_is_toast',False): w.destroy()
#         except: pass
#         toast=tk.Label(self.root,text=msg,font=('',8),bg=t['bar'],fg=t['fg'],
#                        padx=10,pady=4,relief='flat')
#         toast._is_toast=True
#         toast.place(relx=0.5,rely=0.06,anchor='n')
#         self.root.after(ms,lambda: (toast.winfo_exists() and toast.destroy()))

#     # ─────────────────────────────────────────────────
#     # 欢迎页
#     # ─────────────────────────────────────────────────
#     def _show_welcome(self):
#         self.txt.config(state='normal'); self.txt.delete('1.0','end')
#         self.txt.insert('1.0',(
#             '\n\n\n'
#             '        📚  摸鱼阅读器  v8\n\n'
#             '  支持：TXT  /  EPUB  /  MD\n\n'
#             '  顶部按钮：书架  目录  笔记  书签  打开\n\n'
#             '  操作：\n'
#             '    滚轮 / 拖拽右侧滚动条  章内滚动\n'
#             '    滚到章末再滚           切下一章\n'
#             '    点击左侧 28% / 右侧    切上下章\n'
#             '    ← →  切章   S/↓  翻屏\n\n'
#             '  快捷键：\n'
#             '    O        添加书签\n'
#             '    N        添加笔记\n'
#             '    F5       开始/停止朗读\n'
#             '    D+E      最小化\n'
#         ))
#         self.txt.config(state='disabled')

#     # ─────────────────────────────────────────────────
#     # 最小化
#     # ─────────────────────────────────────────────────
#     def toggle_minimize(self):
#         self._minimized=not self._minimized
#         if self._minimized:
#             self._saved_h=self.root.winfo_height()
#             for w in (self.setbar,self.sep,self.txt_frame,self.bot_area): w.pack_forget()
#             self.root.geometry(f'{self.root.winfo_width()}x30')
#         else:
#             self.root.geometry(f'{self.root.winfo_width()}x{self._saved_h}')
#             self.sep.pack(fill='x',after=self.topbar)
#             if self._settings_open: self.setbar.pack(fill='x',after=self.topbar); self._retheme_setbar()
#             self.txt_frame.pack(fill='both',expand=True)
#             self.bot_area.pack(fill='x',side='bottom')

#     def toggle_settings(self):
#         self._settings_open=not self._settings_open
#         if self._settings_open: self.setbar.pack(fill='x',after=self.topbar); self._retheme_setbar()
#         else: self.setbar.pack_forget()

#     # ─────────────────────────────────────────────────
#     # 关闭时保存
#     # ─────────────────────────────────────────────────
#     def _on_close(self):
#         self.tts.stop()
#         self._shelf_update()
#         self.root.destroy()

#     # ─────────────────────────────────────────────────
#     # 快捷键
#     # ─────────────────────────────────────────────────
#     def _bind_keys(self):
#         r=self.root
#         r.bind('<KeyPress-s>',   lambda e: self._scroll_down())
#         r.bind('<KeyPress-S>',   lambda e: self._scroll_down())
#         r.bind('<Right>',        lambda e: self.next_chapter())
#         r.bind('<Left>',         lambda e: self.prev_chapter())
#         r.bind('<Down>',         lambda e: self._scroll_down())
#         r.bind('<Up>',           lambda e: self.txt.yview_scroll(-3,'units'))
#         r.bind('<KeyPress-o>',   lambda e: self.add_mark())
#         r.bind('<KeyPress-O>',   lambda e: self.add_mark())
#         r.bind('<KeyPress-n>',   lambda e: self.add_note())
#         r.bind('<KeyPress-N>',   lambda e: self.add_note())
#         r.bind('<F5>',           lambda e: self.toggle_tts())
#         r.bind('<KeyPress-d>',   self._dp)
#         r.bind('<KeyPress-D>',   self._dp)
#         r.bind('<KeyRelease-d>', self._dr)
#         r.bind('<KeyRelease-D>', self._dr)
#         r.bind('<KeyPress-e>',   self._ep)
#         r.bind('<KeyPress-E>',   self._ep)
#         r.focus_set()

#     def _dp(self,e): self._d_held=True
#     def _dr(self,e): self._d_held=False
#     def _ep(self,e):
#         if self._d_held: self.toggle_minimize()


# # ══════════════════════════════════════════════════════════════
# if __name__ == '__main__':
#     try:
#         from ctypes import windll
#         windll.shcore.SetProcessDpiAwareness(1)
#     except: pass
#     App()

# """
# 摸鱼阅读器 v8.0  —  全功能版
# 功能：
#   阅读体验：章节滚动、翻页、字号/行距/字色/背景/护眼模式、透明度、屏幕取色
#   书架管理：添加/删除/重命名书籍、显示封面/进度/上次阅读时间
#   阅读进度：自动记录、书架显示进度条
#   笔记系统：N键在当前章节创建笔记、查看/编辑/删除笔记
#   书签系统：O键快速书签、书签列表跳转删除
#   听书TTS ：F5启动/停止，支持语速调整（需系统 pyttsx3 或 espeak）
#   竖向拖拽滚动条、目录跳转、搜索

# 运行：python novel_reader.py
# 依赖：pip install pyttsx3   （TTS，可选）
#       pip install pillow     （屏幕取色，可选）
# """

# import tkinter as tk
# from tkinter import ttk, filedialog, colorchooser, messagebox, scrolledtext
# import os, re, zipfile, sys, json, copy, threading, time, datetime
# from html.parser import HTMLParser


# # ══════════════════════════════════════════════════════════════
# # HTML → 纯文本
# # ══════════════════════════════════════════════════════════════
# class _H2T(HTMLParser):
#     SKIP  = {'script','style','head','meta','link'}
#     BLOCK = {'p','div','br','h1','h2','h3','h4','h5',
#              'h6','li','tr','td','th','section','article'}
#     def __init__(self): super().__init__(); self.out, self._s = [], 0
#     def handle_starttag(self, tag, _):
#         if tag in self.SKIP:  self._s += 1
#         if tag in self.BLOCK: self.out.append('\n')
#     def handle_endtag(self, tag):
#         if tag in self.SKIP:  self._s = max(0, self._s-1)
#         if tag in self.BLOCK: self.out.append('\n')
#     def handle_data(self, d):
#         if not self._s: self.out.append(d)
#     def text(self): return re.sub(r'\n{3,}','\n\n',''.join(self.out)).strip()

# def html2text(s):
#     p = _H2T()
#     try: p.feed(s)
#     except: pass
#     return p.text()


# # ══════════════════════════════════════════════════════════════
# # EPUB
# # ══════════════════════════════════════════════════════════════
# def read_epub(path):
#     import xml.etree.ElementTree as ET
#     title = os.path.splitext(os.path.basename(path))[0]
#     body  = ''
#     try:
#         with zipfile.ZipFile(path) as z:
#             ns = z.namelist()
#             opf, odir = '', ''
#             if 'META-INF/container.xml' in ns:
#                 for el in ET.fromstring(z.read('META-INF/container.xml')).iter():
#                     if el.tag.endswith('rootfile'):
#                         opf = el.get('full-path',''); odir = opf.rsplit('/',1)[0] if '/' in opf else ''; break
#             items, spine = {}, []
#             if opf and opf in ns:
#                 root = ET.fromstring(z.read(opf))
#                 for el in root.iter():
#                     tag = el.tag.split('}')[-1]
#                     if tag == 'item':
#                         mid,href,mt = el.get('id',''),el.get('href',''),el.get('media-type','')
#                         if href and ('html' in mt or href.endswith(('.html','.xhtml','.htm'))):
#                             items[mid] = (odir+'/'+href).lstrip('/') if odir else href
#                     elif tag == 'itemref':
#                         r = el.get('idref','')
#                         if r in items: spine.append(items[r])
#                     elif tag == 'title' and el.text: title = el.text
#             if not spine:
#                 spine = sorted(f for f in ns if re.search(r'\.(html|htm|xhtml)$',f,re.I)
#                                and 'toc' not in f.lower() and 'nav' not in f.lower())
#             for href in spine:
#                 if href in ns:
#                     try: body += html2text(z.read(href).decode('utf-8','replace')) + '\n\n'
#                     except: pass
#     except Exception as e: body = f'[EPUB解析失败: {e}]'
#     return title, body.strip()


# # ══════════════════════════════════════════════════════════════
# # 章节切割
# # ══════════════════════════════════════════════════════════════
# _CH = re.compile(
#     r'^(第\s*[零一二三四五六七八九十百千万\d〇]+\s*[章节卷集回部篇][^\n]{0,40}'
#     r'|Chapter\s*\d+[^\n]{0,40}|CHAPTER\s*\d+[^\n]{0,40}|【[^\n]{1,30}】)', re.I)

# def split_chapters(text):
#     bounds = []
#     for m in re.finditer(r'^.+$', text, re.M):
#         line = m.group().strip()
#         if line and _CH.match(line): bounds.append((m.start(), line))
#     if not bounds: return [{'title':'全文','body':text}]
#     chs = []
#     for i,(pos,title) in enumerate(bounds):
#         end = bounds[i+1][0] if i+1<len(bounds) else len(text)
#         chs.append({'title':title,'body':text[pos:end]})
#     return chs


# # ══════════════════════════════════════════════════════════════
# # 数据存储
# # ══════════════════════════════════════════════════════════════
# DATA_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.moyu_data')
# os.makedirs(DATA_DIR, exist_ok=True)
# SHELF_FILE = os.path.join(DATA_DIR, 'shelf.json')
# NOTES_FILE = os.path.join(DATA_DIR, 'notes.json')
# MARKS_FILE = os.path.join(DATA_DIR, 'marks.json')

# def _jload(f):
#     try:
#         with open(f, encoding='utf-8') as fp: return json.load(fp)
#     except: return {}

# def _jsave(f, d):
#     try:
#         with open(f, 'w', encoding='utf-8') as fp: json.dump(d, fp, ensure_ascii=False, indent=2)
#     except: pass

# def _inject_api_key():
#     """
#     从程序目录的 api_key.txt 自动读取智谱 API Key。
#     用户把 Key 粘贴进 api_key.txt 即可，无需手动配置环境变量。
#     返回 key 字符串，失败返回空字符串。
#     """
#     key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_key.txt')
#     if os.path.exists(key_file):
#         try:
#             key = open(key_file, encoding='utf-8').read().strip()
#             if key:
#                 os.environ['ZHIPU_API_KEY'] = key
#                 return key
#         except: pass
#     return os.environ.get('ZHIPU_API_KEY', '')


# # ══════════════════════════════════════════════════════════════
# # TTS 引擎（可选）
# # ══════════════════════════════════════════════════════════════
# class TTS:
#     def __init__(self):
#         self._engine = None
#         self._thread = None
#         self._stop   = threading.Event()
#         self._text   = ''
#         self._rate   = 180
#         self._avail  = False
#         self._init()

#     def _init(self):
#         try:
#             import pyttsx3
#             self._engine = pyttsx3.init()
#             self._avail  = True
#         except:
#             self._avail = False

#     @property
#     def available(self): return self._avail

#     def set_rate(self, rate):
#         self._rate = int(rate)
#         if self._engine:
#             try: self._engine.setProperty('rate', self._rate)
#             except: pass

#     def speak(self, text, on_done=None):
#         if not self._avail: return
#         self.stop()
#         self._stop.clear()
#         self._text = text

#         def run():
#             try:
#                 import pyttsx3
#                 eng = pyttsx3.init()
#                 eng.setProperty('rate', self._rate)
#                 # 逐段朗读，支持中途停止
#                 paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
#                 for para in paragraphs:
#                     if self._stop.is_set(): break
#                     eng.say(para)
#                     eng.runAndWait()
#                 eng.stop()
#             except: pass
#             if on_done: on_done()

#         self._thread = threading.Thread(target=run, daemon=True)
#         self._thread.start()

#     def stop(self):
#         self._stop.set()
#         if self._engine:
#             try: self._engine.stop()
#             except: pass


# # ══════════════════════════════════════════════════════════════
# # 屏幕取色器
# # ══════════════════════════════════════════════════════════════
# def screen_color_picker(callback):
#     try: from PIL import ImageGrab
#     except ImportError:
#         c = colorchooser.askcolor(title='选择颜色')
#         if c and c[1]: callback(c[1])
#         return
#     from PIL import ImageGrab, Image, ImageTk
#     ZOOM,HALF = 10,5; CS = (HALF*2+1)*ZOOM
#     preview = tk.Toplevel(); preview.overrideredirect(True)
#     preview.attributes('-topmost',True); preview.configure(bg='#1a1a1a')
#     preview.geometry(f'{CS+4}x{CS+28}+200+200')
#     canvas = tk.Canvas(preview,width=CS,height=CS,bg='#000',highlightthickness=1,
#                        highlightbackground='#555',cursor='none')
#     canvas.pack(padx=2,pady=(2,0))
#     lbl = tk.Label(preview,text='#000000',font=('Consolas',9,'bold'),bg='#1a1a1a',fg='white',pady=1)
#     lbl.pack()
#     cur,ph,aid,done = ['#000000'],[None],[None],[False]
#     def update():
#         if done[0]: return
#         try:
#             mx,my = preview.winfo_pointerx(),preview.winfo_pointery()
#             img = ImageGrab.grab(bbox=(mx-HALF,my-HALF,mx+HALF+1,my+HALF+1))
#             zoomed = img.resize((CS,CS),Image.NEAREST); ph[0]=ImageTk.PhotoImage(zoomed)
#             canvas.delete('all'); canvas.create_image(0,0,anchor='nw',image=ph[0])
#             c2=CS//2
#             canvas.create_line(c2,0,c2,CS,fill='white',width=1)
#             canvas.create_line(0,c2,CS,c2,fill='white',width=1)
#             canvas.create_rectangle(c2-ZOOM,c2-ZOOM,c2+ZOOM,c2+ZOOM,outline='white',width=2)
#             px=img.getpixel((HALF,HALF)); hx='#{:02x}{:02x}{:02x}'.format(px[0],px[1],px[2])
#             cur[0]=hx; lbl.config(text=hx)
#             sw,sh=preview.winfo_screenwidth(),preview.winfo_screenheight()
#             ox,oy=mx+18,my+18
#             if ox+CS+10>sw: ox=mx-CS-22
#             if oy+CS+32>sh: oy=my-CS-34
#             preview.geometry(f'+{ox}+{oy}')
#         except: pass
#         aid[0]=preview.after(40,update)
#     def finish():
#         done[0]=True
#         if aid[0]:
#             try: preview.after_cancel(aid[0])
#             except: pass
#         for w in (overlay,preview):
#             try: w.destroy()
#             except: pass
#     overlay = tk.Toplevel(); overlay.overrideredirect(True)
#     overlay.attributes('-topmost',True); overlay.attributes('-alpha',0.01)
#     sw,sh=overlay.winfo_screenwidth(),overlay.winfo_screenheight()
#     overlay.geometry(f'{sw}x{sh}+0+0'); overlay.configure(bg='white',cursor='crosshair')
#     overlay.bind('<Button-1>',lambda e:(finish(),callback(cur[0])))
#     overlay.bind('<Escape>',lambda e:finish())
#     overlay.focus_force(); aid[0]=preview.after(40,update)


# # ══════════════════════════════════════════════════════════════
# # 自定义竖向滚动条
# # ══════════════════════════════════════════════════════════════
# class SmoothScrollbar:
#     W = 10
#     def __init__(self, parent, on_scroll):
#         self.on_scroll = on_scroll
#         self._lo,self._hi = 0.0,1.0
#         self._dragging = False; self._drag_start_y = 0; self._drag_start_lo = 0.0
#         self.c_bg='#ebdbb2'; self.c_track='#d5c4a1'; self.c_thumb='#b8a882'; self.c_hover='#8f7a55'
#         self.cv = tk.Canvas(parent, width=self.W, highlightthickness=0, cursor='arrow')
#         self.cv.pack(side='right', fill='y')
#         self.cv.bind('<Configure>', lambda e: self._draw())
#         self.cv.bind('<ButtonPress-1>',   self._press)
#         self.cv.bind('<B1-Motion>',       self._drag)
#         self.cv.bind('<ButtonRelease-1>', self._release)
#         self.cv.bind('<Enter>', lambda e: self._hover(True))
#         self.cv.bind('<Leave>', lambda e: self._hover(False))
#         self._hovered = False

#     def set(self, lo, hi): self._lo,self._hi = float(lo),float(hi); self._draw()

#     def set_colors(self, bg, track, thumb, thumb_hover):
#         self.c_bg=bg; self.c_track=track; self.c_thumb=thumb; self.c_hover=thumb_hover; self._draw()

#     def _draw(self):
#         cv=self.cv; W=self.W; H=cv.winfo_height()
#         if H<4: return
#         cv.delete('all'); PAD=2
#         cv.create_rectangle(0,0,W,H,fill=self.c_bg,outline='')
#         tx=W//2
#         cv.create_line(tx,PAD,tx,H-PAD,fill=self.c_track,width=W-4,capstyle='round')
#         th=max(20,int((self._hi-self._lo)*(H-2*PAD))); ty=PAD+int(self._lo*(H-2*PAD))
#         ty2=min(H-PAD,ty+th); color=self.c_hover if self._hovered else self.c_thumb
#         r=(W-4)//2; x1,x2=2,W-2; y1,y2=ty,ty2
#         if y2-y1>=2*r:
#             cv.create_rectangle(x1,y1+r,x2,y2-r,fill=color,outline='')
#             cv.create_oval(x1,y1,x2,y1+2*r,fill=color,outline='')
#             cv.create_oval(x1,y2-2*r,x2,y2,fill=color,outline='')
#         else: cv.create_oval(x1,y1,x2,y2,fill=color,outline='')

#     def _hover(self, v): self._hovered=v; self._draw()

#     def _y_to_frac(self,y):
#         H=self.cv.winfo_height(); PAD=2
#         return max(0.0,min(1.0,(y-PAD)/max(1,H-2*PAD)))

#     def _thumb_range(self):
#         H=self.cv.winfo_height(); PAD=2
#         th=max(20,int((self._hi-self._lo)*(H-2*PAD))); ty=PAD+int(self._lo*(H-2*PAD))
#         return ty,ty+th

#     def _press(self, e):
#         ty1,ty2=self._thumb_range()
#         if ty1<=e.y<=ty2:
#             self._dragging=True; self._drag_start_y=e.y; self._drag_start_lo=self._lo
#         else:
#             frac=self._y_to_frac(e.y); span=self._hi-self._lo
#             self.on_scroll(max(0.0,min(1.0-span,frac-span/2)))

#     def _drag(self, e):
#         if not self._dragging: return
#         H=self.cv.winfo_height(); PAD=2; dy=e.y-self._drag_start_y
#         delta=dy/max(1,H-2*PAD); span=self._hi-self._lo
#         target=max(0.0,min(1.0-span,self._drag_start_lo+delta))
#         self._lo=target; self._hi=target+span; self._draw(); self.on_scroll(target)

#     def _release(self, e): self._dragging=False


# # ══════════════════════════════════════════════════════════════
# # 主程序
# # ══════════════════════════════════════════════════════════════
# class App:

#     THEMES = {
#         '暖黄': dict(bg='#fdf6e3',fg='#3c3836',bar='#ebdbb2',sel='#d5c4a1',thumb='#b8a882',thumb_h='#8f7a55'),
#         '夜间': dict(bg='#1e1e2e',fg='#cdd6f4',bar='#181825',sel='#313244',thumb='#45475a',thumb_h='#6c7086'),
#         '护眼': dict(bg='#1a2f1a',fg='#a8d5a2',bar='#152315',sel='#2d5a2d',thumb='#3a6b3a',thumb_h='#57c454'),
#         '纸张': dict(bg='#f5f0e8',fg='#2c2416',bar='#ede4d0',sel='#c8b89a',thumb='#c8a882',thumb_h='#8b6045'),
#         '白底': dict(bg='#ffffff',fg='#1a1a1a',bar='#f0f0f0',sel='#dddddd',thumb='#bbbbbb',thumb_h='#888888'),
#     }

#     def __init__(self):
#         self.root = tk.Tk()
#         self.root.title('摸鱼阅读器')
#         self.root.geometry('440x600')
#         self.root.minsize(320, 400)
#         self.root.attributes('-topmost', True)

#         # 数据
#         self.shelf   = _jload(SHELF_FILE)   # {path: {title,last_ch,total_ch,last_time,read_time}}
#         self.notes   = _jload(NOTES_FILE)   # {path: [{ch,title,content,time}]}
#         self.marks   = _jload(MARKS_FILE)   # {path: [{ch,ch_title,time}]}

#         self.book_path  = ''
#         self.book_title = ''
#         self.chapters   = []
#         self.cur_ch     = 0

#         # UI 状态
#         self.theme_name     = '暖黄'
#         self.custom_bg      = None
#         self.custom_bar     = None
#         self.font_size      = 14
#         self.line_spacing   = 6
#         self.font_fam       = ('宋体' if sys.platform=='win32'
#                                else 'Songti SC' if sys.platform=='darwin'
#                                else 'Noto Serif CJK SC')
#         self._d_held        = False
#         self._minimized     = False
#         self._settings_open = False
#         self._wheel_accum   = 0
#         self._tts_playing   = False

#         self.tts = TTS()

#         self._build_ui()
#         self._apply_theme()
#         self._bind_keys()
#         self.root.protocol('WM_DELETE_WINDOW', self._on_close)
#         self.root.mainloop()

#     # ─────────────────────────────────────────────────
#     # UI 构建
#     # ─────────────────────────────────────────────────
#     def _build_ui(self):
#         r = self.root

#         # 顶部栏
#         self.topbar = tk.Frame(r, height=30)
#         self.topbar.pack(fill='x')
#         self.topbar.pack_propagate(False)

#         dots = tk.Frame(self.topbar)
#         dots.pack(side='left', padx=6, pady=5)
#         self._dot(dots, '#ff5f57', self.toggle_minimize)
#         self._dot(dots, '#ffbd2e', self.toggle_settings)
#         self._dot(dots, '#28ca41', self.open_file)

#         self.lbl_title = tk.Label(self.topbar, text='摸鱼阅读器', font=('',9))
#         self.lbl_title.pack(side='left', fill='x', expand=True)

#         rbf = tk.Frame(self.topbar); rbf.pack(side='right', padx=2)
#         self._tbtn(rbf, '书架', self.open_shelf)
#         self._tbtn(rbf, '目录', self.open_chapters)
#         self._tbtn(rbf, '搜索', self.open_search)
#         self._tbtn(rbf, '摘要', self.open_summary)
#         self._tbtn(rbf, '笔记', self.open_notes)
#         self._tbtn(rbf, '书签', self.open_marks)
#         self._tbtn(rbf, '打开', self.open_file)
#         self._tbtn(rbf, '×',   r.destroy)

#         for w in (self.topbar, self.lbl_title):
#             w.bind('<ButtonPress-1>', self._drag_start)
#             w.bind('<B1-Motion>',     self._drag_move)

#         # 设置栏
#         self.setbar = tk.Frame(r)
#         self._build_setbar()

#         # 分隔线
#         self.sep = tk.Frame(r, height=1)
#         self.sep.pack(fill='x')

#         # 文本区
#         self.txt_frame = tk.Frame(r)
#         self.txt_frame.pack(fill='both', expand=True)

#         self.vsb = SmoothScrollbar(self.txt_frame,
#                                    on_scroll=lambda f: self.txt.yview_moveto(f))

#         self.txt = tk.Text(
#             self.txt_frame, wrap='word',
#             relief='flat', padx=16, pady=10,
#             state='disabled', cursor='arrow',
#             font=(self.font_fam, self.font_size),
#             borderwidth=0, highlightthickness=0,
#             spacing1=self.line_spacing,
#             spacing2=self.line_spacing//2,
#             spacing3=self.line_spacing,
#             yscrollcommand=self._on_yscroll,
#         )
#         self.txt.pack(side='left', fill='both', expand=True)
#         self.txt.bind('<Button-1>',   self._on_click)
#         self.txt.bind('<MouseWheel>', self._on_wheel)
#         self.txt.bind('<Button-4>',   self._on_wheel)
#         self.txt.bind('<Button-5>',   self._on_wheel)
#         self._show_welcome()

#         # 底部
#         self.bot_area = tk.Frame(r)
#         self.bot_area.pack(fill='x', side='bottom')

#         self.botbar = tk.Frame(self.bot_area, height=28)
#         self.botbar.pack(fill='x')
#         self.botbar.pack_propagate(False)

#         self.btn_prev = tk.Button(self.botbar, text='◀', font=('',9),
#                                   relief='flat', padx=4, command=self.prev_chapter)
#         self.btn_prev.pack(side='left', padx=4, pady=3)

#         self.lbl_prog = tk.Label(self.botbar, text='', font=('',8))
#         self.lbl_prog.pack(side='left', expand=True)

#         self.btn_tts = tk.Button(self.botbar, text='🔊', font=('',9),
#                                  relief='flat', padx=3, command=self.toggle_tts)
#         self.btn_tts.pack(side='right', padx=2, pady=3)

#         self.btn_note = tk.Button(self.botbar, text='✏', font=('',9),
#                                   relief='flat', padx=3, command=self.add_note)
#         self.btn_note.pack(side='right', padx=2, pady=3)

#         self.btn_mark = tk.Button(self.botbar, text='🔖', font=('',9),
#                                   relief='flat', padx=2, command=self.add_mark)
#         self.btn_mark.pack(side='right', padx=2, pady=3)

#         self.btn_next = tk.Button(self.botbar, text='▶', font=('',9),
#                                   relief='flat', padx=4, command=self.next_chapter)
#         self.btn_next.pack(side='right', padx=4, pady=3)

#     def _tbtn(self, parent, text, cmd):
#         tk.Button(parent, text=text, font=('',8), relief='flat',
#                   padx=3, command=cmd).pack(side='left', padx=1)

#     def _dot(self, p, color, cmd):
#         lb = tk.Label(p, text='⬤', fg=color, font=('',12), cursor='hand2')
#         lb.pack(side='left', padx=2)
#         lb.bind('<Button-1>', lambda e: cmd())

#     # ─────────────────────────────────────────────────
#     # 设置栏
#     # ─────────────────────────────────────────────────
#     def _build_setbar(self):
#         def row(): f=tk.Frame(self.setbar); f.pack(fill='x',padx=8,pady=2); return f

#         r1 = row()
#         tk.Label(r1,text='字号',font=('',8)).pack(side='left')
#         self.sl_font = tk.Scale(r1,from_=10,to=32,orient='horizontal',length=70,
#                                 showvalue=True,font=('',7),command=self._on_font_size)
#         self.sl_font.set(self.font_size); self.sl_font.pack(side='left',padx=2)
#         tk.Label(r1,text='行距',font=('',8)).pack(side='left',padx=(8,0))
#         self.sl_spacing = tk.Scale(r1,from_=0,to=24,orient='horizontal',length=70,
#                                    showvalue=True,font=('',7),command=self._on_spacing)
#         self.sl_spacing.set(self.line_spacing); self.sl_spacing.pack(side='left',padx=2)

#         r2 = row()
#         tk.Label(r2,text='透明',font=('',8)).pack(side='left')
#         self.sl_alpha = tk.Scale(r2,from_=20,to=100,orient='horizontal',length=80,
#                                  showvalue=True,font=('',7),
#                                  command=lambda v: self.root.attributes('-alpha',int(v)/100))
#         self.sl_alpha.set(100); self.sl_alpha.pack(side='left',padx=2)
#         # TTS 语速
#         tk.Label(r2,text='语速',font=('',8)).pack(side='left',padx=(8,0))
#         self.sl_tts_rate = tk.Scale(r2,from_=80,to=300,orient='horizontal',length=70,
#                                     showvalue=True,font=('',7),
#                                     command=lambda v: self.tts.set_rate(int(v)))
#         self.sl_tts_rate.set(180); self.sl_tts_rate.pack(side='left',padx=2)

#         r3 = row()
#         tk.Label(r3,text='字色',font=('',8)).pack(side='left')
#         self.btn_fg_color = tk.Button(r3,text='  ',relief='groove',width=2,
#                                       font=('',8),command=self._pick_fg)
#         self.btn_fg_color.pack(side='left',padx=2)
#         tk.Label(r3,text='背景',font=('',8)).pack(side='left',padx=(6,0))
#         self.btn_bg_color = tk.Button(r3,text='  ',relief='groove',width=2,
#                                       font=('',8),command=self._pick_bg)
#         self.btn_bg_color.pack(side='left',padx=2)
#         tk.Button(r3,text='🎨取色',font=('',8),relief='flat',padx=4,
#                   command=self._screen_pick).pack(side='left',padx=4)
#         tk.Button(r3,text='重置',font=('',8),relief='flat',padx=4,
#                   command=self._reset_colors).pack(side='left',padx=2)

#         r4 = row()
#         tk.Label(r4,text='主题',font=('',8)).pack(side='left')
#         self.var_theme = tk.StringVar(value=self.theme_name)
#         cb = ttk.Combobox(r4,textvariable=self.var_theme,
#                           values=list(self.THEMES.keys()),width=7,font=('',8),state='readonly')
#         cb.pack(side='left',padx=4); cb.bind('<<ComboboxSelected>>',self._on_theme)
#         # 快速护眼切换
#         tk.Button(r4,text='☘护眼',font=('',8),relief='flat',padx=4,
#                   command=lambda: (self.var_theme.set('护眼'),self._on_theme())).pack(side='left',padx=2)
#         tk.Button(r4,text='🌙夜间',font=('',8),relief='flat',padx=4,
#                   command=lambda: (self.var_theme.set('夜间'),self._on_theme())).pack(side='left',padx=2)

#     # ─────────────────────────────────────────────────
#     # 颜色
#     # ─────────────────────────────────────────────────
#     def _pick_fg(self):
#         t=self._cur_theme(); c=colorchooser.askcolor(color=t['fg'],title='字体颜色')
#         if c and c[1]: self.THEMES[self.theme_name]['fg']=c[1]; self.txt.config(fg=c[1]); self.btn_fg_color.config(bg=c[1])

#     def _pick_bg(self):
#         c=colorchooser.askcolor(color=self._cur_theme()['bg'],title='背景颜色')
#         if c and c[1]: self._apply_custom_bg(c[1])

#     def _screen_pick(self):
#         alpha=self.sl_alpha.get()/100; self.root.attributes('-alpha',0.0)
#         def on(hx): self.root.after(100,lambda:self.root.attributes('-alpha',alpha)); self._apply_custom_bg(hx)
#         self.root.after(120, lambda: screen_color_picker(on))

#     def _apply_custom_bg(self,hx):
#         self.custom_bg=hx; self.custom_bar=self._darken(hx,0.88); self._apply_theme()
#         try: self.btn_bg_color.config(bg=hx)
#         except: pass

#     def _reset_colors(self): self.custom_bg=self.custom_bar=None; self._apply_theme()
#     def _darken(self,hx,f=0.88):
#         h=hx.lstrip('#')
#         return '#{:02x}{:02x}{:02x}'.format(int(int(h[0:2],16)*f),int(int(h[2:4],16)*f),int(int(h[4:6],16)*f))

#     def _cur_theme(self):
#         t=copy.copy(self.THEMES[self.theme_name])
#         if self.custom_bg:  t['bg']=self.custom_bg
#         if self.custom_bar: t['bar']=self.custom_bar
#         return t

#     def _on_theme(self, e=None):
#         self.theme_name=self.var_theme.get(); self.custom_bg=self.custom_bar=None; self._apply_theme()

#     def _apply_theme(self):
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         self.root.configure(bg=bar)
#         self._cf(self.topbar,bar,fg); self._cf(self.botbar,bar,fg); self._cf(self.bot_area,bar,fg)
#         self.sep.config(bg=sel); self.txt_frame.config(bg=bg)
#         self.vsb.cv.config(bg=bg)
#         self.vsb.set_colors(bg=bg,track=sel,thumb=t.get('thumb',sel),thumb_hover=t.get('thumb_h',fg))
#         self.txt.config(bg=bg,fg=fg,insertbackground=fg,selectbackground=sel)
#         self.lbl_prog.config(bg=bar,fg=fg)
#         for b in (self.btn_prev,self.btn_next,self.btn_mark,self.btn_note,self.btn_tts):
#             b.config(bg=bar,fg=fg,activebackground=sel)
#         self._retheme_setbar()
#         try:
#             if self.custom_bg: self.btn_bg_color.config(bg=self.custom_bg)
#         except: pass

#     def _cf(self,fr,bg,fg):
#         try: fr.config(bg=bg)
#         except: pass
#         for w in fr.winfo_children():
#             try: w.config(bg=bg,fg=fg,activebackground=bg)
#             except: pass
#             for w2 in w.winfo_children():
#                 try: w2.config(bg=bg,fg=fg,activebackground=bg)
#                 except: pass

#     def _retheme_setbar(self):
#         t=self._cur_theme(); bg,fg,sel=t['bar'],t['fg'],t['sel']
#         self._cf(self.setbar,bg,fg)
#         for sl in (self.sl_font,self.sl_alpha,self.sl_spacing,self.sl_tts_rate):
#             try: sl.config(bg=bg,fg=fg,troughcolor=sel,activebackground=sel)
#             except: pass
#         try: self.btn_fg_color.config(bg=fg)
#         except: pass

#     # ─────────────────────────────────────────────────
#     # 字号 / 行距
#     # ─────────────────────────────────────────────────
#     def _on_font_size(self,val):
#         self.font_size=int(float(val)); self.txt.config(font=(self.font_fam,self.font_size))

#     def _on_spacing(self,val):
#         sp=int(float(val)); self.line_spacing=sp
#         self.txt.config(spacing1=sp,spacing2=sp//2,spacing3=sp)

#     # ─────────────────────────────────────────────────
#     # 拖动窗口
#     # ─────────────────────────────────────────────────
#     def _drag_start(self,e): self._dx=e.x_root-self.root.winfo_x(); self._dy=e.y_root-self.root.winfo_y()
#     def _drag_move(self,e):  self.root.geometry(f'+{e.x_root-self._dx}+{e.y_root-self._dy}')

#     # ─────────────────────────────────────────────────
#     # 打开文件
#     # ─────────────────────────────────────────────────
#     def open_file(self, path=None):
#         if path is None:
#             path = filedialog.askopenfilename(
#                 title='打开小说',
#                 filetypes=[('小说文件','*.txt *.epub *.md'),('所有文件','*.*')])
#         if not path: return
#         ext = os.path.splitext(path)[1].lower()
#         if ext == '.epub': title,text = read_epub(path)
#         else:
#             title = os.path.splitext(os.path.basename(path))[0]
#             try:
#                 with open(path,encoding='utf-8',errors='replace') as f: text=f.read()
#             except Exception as e: messagebox.showerror('错误',str(e)); return
#         self.book_path=path; self.book_title=title
#         self.lbl_title.config(text=f'  {title}'); self.root.title(f'摸鱼阅读器 — {title}')
#         self._load(text)

#     def _load(self,text):
#         self.chapters = split_chapters(text)
#         # 恢复上次阅读位置
#         si = self.shelf.get(self.book_path,{})
#         self.cur_ch = max(0,min(si.get('last_ch',0),len(self.chapters)-1))
#         # 更新书架
#         self._shelf_update()
#         self._render_chapter()

#     # ─────────────────────────────────────────────────
#     # 书架管理
#     # ─────────────────────────────────────────────────
#     def _shelf_update(self):
#         p = self.book_path
#         prev = self.shelf.get(p,{})
#         self.shelf[p] = {
#             'title':      self.book_title,
#             'path':       p,
#             'last_ch':    self.cur_ch,
#             'total_ch':   len(self.chapters),
#             'last_time':  datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
#             'added_time': prev.get('added_time', datetime.datetime.now().strftime('%Y-%m-%d')),
#         }
#         _jsave(SHELF_FILE, self.shelf)

#     def open_shelf(self):
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('书架'); win.geometry('380x460')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)

#         hdr=tk.Frame(win,bg=bar,height=30); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='📚 书架',font=('',10,'bold'),bg=bar,fg=fg).pack(side='left',padx=10,pady=5)
#         tk.Button(hdr,text='+添加',font=('',8),relief='flat',bg=bar,fg=fg,
#                   command=lambda:self._shelf_add(win)).pack(side='right',padx=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,
#                   command=win.destroy).pack(side='right',padx=4)

#         # 书籍列表
#         frame=tk.Frame(win,bg=bg); frame.pack(fill='both',expand=True,padx=6,pady=6)
#         sb2=tk.Scrollbar(frame); sb2.pack(side='right',fill='y')
#         canvas=tk.Canvas(frame,bg=bg,highlightthickness=0,yscrollcommand=sb2.set)
#         canvas.pack(fill='both',expand=True); sb2.config(command=canvas.yview)
#         inner=tk.Frame(canvas,bg=bg); canvas.create_window((0,0),window=inner,anchor='nw')

#         def refresh():
#             for w in inner.winfo_children(): w.destroy()
#             if not self.shelf:
#                 tk.Label(inner,text='书架空空，快去添加书吧',font=('',10),bg=bg,fg=sel).pack(pady=30)
#             for path,info in sorted(self.shelf.items(),key=lambda x:x[1].get('last_time',''),reverse=True):
#                 self._shelf_card(inner,path,info,bg,fg,bar,sel,win,refresh)
#             inner.update_idletasks()
#             canvas.config(scrollregion=canvas.bbox('all'))
#         refresh()

#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'380x460+{rx}+{ry}')

#     def _shelf_card(self,parent,path,info,bg,fg,bar,sel,shelf_win,refresh):
#         card=tk.Frame(parent,bg=bar,relief='flat',bd=0)
#         card.pack(fill='x',padx=4,pady=3)
#         # 封面色块
#         colors=['#8f3f71','#458588','#d79921','#689d6a','#cc241d']
#         ccolor=colors[hash(path)%len(colors)]
#         cover=tk.Frame(card,bg=ccolor,width=36,height=50); cover.pack(side='left',padx=6,pady=6); cover.pack_propagate(False)
#         tk.Label(cover,text='📖',font=('',14),bg=ccolor).pack(expand=True)
#         # 信息
#         info_f=tk.Frame(card,bg=bar); info_f.pack(side='left',fill='both',expand=True,pady=4)
#         tk.Label(info_f,text=info.get('title','未知'),font=('',9,'bold'),bg=bar,fg=fg,anchor='w').pack(fill='x')
#         lc=info.get('last_ch',0); tc=info.get('total_ch',1)
#         pct=int(lc/max(1,tc-1)*100) if tc>1 else 0
#         tk.Label(info_f,text=f'第{lc+1}/{tc}章  {pct}%',font=('',8),bg=bar,fg=sel,anchor='w').pack(fill='x')
#         # 进度条
#         pb_f=tk.Frame(info_f,bg=bar,height=4); pb_f.pack(fill='x',pady=2); pb_f.pack_propagate(False)
#         pb_done=tk.Frame(pb_f,bg=ccolor,height=4); pb_done.place(x=0,y=0,relwidth=pct/100,relheight=1)
#         tk.Frame(pb_f,bg=sel,height=4).place(x=0,y=0,relwidth=1,relheight=1)
#         pb_done.lift()
#         tk.Label(info_f,text=f'上次：{info.get("last_time","")}',font=('',7),bg=bar,fg=sel,anchor='w').pack(fill='x')
#         # 按钮
#         btn_f=tk.Frame(card,bg=bar); btn_f.pack(side='right',padx=6,pady=4)
#         def open_it(p=path):
#             shelf_win.destroy(); self.open_file(p)
#         def del_it(p=path):
#             if messagebox.askyesno('删除','从书架移除此书？',parent=shelf_win):
#                 del self.shelf[p]; _jsave(SHELF_FILE,self.shelf); refresh()
#         tk.Button(btn_f,text='阅读',font=('',8),relief='flat',bg=ccolor,fg='white',
#                   padx=6,command=open_it).pack(pady=2)
#         tk.Button(btn_f,text='移除',font=('',7),relief='flat',bg=bar,fg=sel,
#                   padx=4,command=del_it).pack(pady=2)

#     def _shelf_add(self, shelf_win):
#         path=filedialog.askopenfilename(title='选择书籍',
#             filetypes=[('小说文件','*.txt *.epub *.md'),('所有文件','*.*')])
#         if not path: return
#         if path not in self.shelf:
#             title=os.path.splitext(os.path.basename(path))[0]
#             self.shelf[path]={'title':title,'path':path,'last_ch':0,'total_ch':0,
#                               'last_time':'','added_time':datetime.datetime.now().strftime('%Y-%m-%d')}
#             _jsave(SHELF_FILE,self.shelf)
#         shelf_win.destroy(); self.open_shelf()

#     # ─────────────────────────────────────────────────
#     # 渲染章节
#     # ─────────────────────────────────────────────────
#     def _render_chapter(self, scroll_to_top=True):
#         if not self.chapters: return
#         self.cur_ch=max(0,min(self.cur_ch,len(self.chapters)-1))
#         ch=self.chapters[self.cur_ch]
#         self.txt.config(state='normal'); self.txt.delete('1.0','end')
#         self.txt.insert('1.0', ch['body']); self.txt.config(state='disabled')
#         if scroll_to_top: self.txt.yview_moveto(0.0)
#         self._update_nav(); self._wheel_accum=0
#         self._shelf_update()

#     def _update_nav(self):
#         n=len(self.chapters); idx=self.cur_ch+1
#         # 有无书签/笔记标记
#         m_chs={m['ch'] for m in self.marks.get(self.book_path,[])}
#         n_chs={n2['ch'] for n2 in self.notes.get(self.book_path,[])}
#         flags=('🔖' if self.cur_ch in m_chs else '')+('✏' if self.cur_ch in n_chs else '')
#         self.lbl_prog.config(text=f'{flags}  第{idx}/{n}章')
#         self.btn_prev.config(state='normal' if self.cur_ch>0   else 'disabled')
#         self.btn_next.config(state='normal' if self.cur_ch<n-1 else 'disabled')

#     def _on_yscroll(self,lo,hi): self.vsb.set(lo,hi)

#     # ─────────────────────────────────────────────────
#     # 翻章
#     # ─────────────────────────────────────────────────
#     def next_chapter(self):
#         if self.chapters and self.cur_ch<len(self.chapters)-1:
#             self.cur_ch+=1; self._render_chapter()

#     def prev_chapter(self):
#         if self.chapters and self.cur_ch>0:
#             self.cur_ch-=1; self._render_chapter()

#     def goto_chapter(self,idx):
#         if not self.chapters: return
#         self.cur_ch=max(0,min(idx,len(self.chapters)-1)); self._render_chapter()

#     def _on_click(self,e):
#         w=self.txt.winfo_width()
#         if   e.x<w*0.28: self.prev_chapter()
#         elif e.x>w*0.72: self.next_chapter()

#     def _on_wheel(self,e):
#         delta=1 if e.num==4 else (-1 if e.num==5 else (1 if e.delta>0 else -1))
#         top,bot=self.txt.yview()
#         if delta<0:
#             if bot>=0.999:
#                 self._wheel_accum-=1
#                 if self._wheel_accum<=-3: self.next_chapter(); return
#             else: self._wheel_accum=0; self.txt.yview_scroll(3,'units')
#         else:
#             if top<=0.001:
#                 self._wheel_accum+=1
#                 if self._wheel_accum>=3:
#                     self.prev_chapter(); self.root.after(30,lambda:self.txt.yview_moveto(1.0)); return
#             else: self._wheel_accum=0; self.txt.yview_scroll(-3,'units')

#     def _scroll_down(self):
#         _,bot=self.txt.yview()
#         if bot>=0.999: self.next_chapter()
#         else: self.txt.yview_scroll(1,'pages')

#     # ─────────────────────────────────────────────────
#     # TTS 听书
#     # ─────────────────────────────────────────────────
#     def toggle_tts(self):
#         if not self.tts.available:
#             messagebox.showinfo('提示','请先安装 pyttsx3：\npip install pyttsx3'); return
#         if self._tts_playing:
#             self.tts.stop(); self._tts_playing=False
#             self.btn_tts.config(text='🔊')
#             self._toast('⏹ 已停止朗读')
#         else:
#             if not self.chapters: return
#             ch=self.chapters[self.cur_ch]
#             self._tts_playing=True; self.btn_tts.config(text='⏸')
#             self._toast('▶ 开始朗读…')
#             def done(): self.root.after(0,self._tts_done)
#             self.tts.speak(ch['body'],on_done=done)

#     def _tts_done(self):
#         self._tts_playing=False; self.btn_tts.config(text='🔊')

#     # ─────────────────────────────────────────────────
#     # 书签（O 键）
#     # ─────────────────────────────────────────────────
#     def add_mark(self):
#         if not self.book_path: messagebox.showinfo('提示','请先打开书'); return
#         marks=self.marks.setdefault(self.book_path,[])
#         ch=self.chapters[self.cur_ch]; now=datetime.datetime.now().strftime('%m-%d %H:%M')
#         existing=next((m for m in marks if m['ch']==self.cur_ch),None)
#         entry={'ch':self.cur_ch,'ch_title':ch['title'],'time':now}
#         if existing: existing.update(entry); self._toast('🔖 书签已更新')
#         else: marks.append(entry); self._toast(f'🔖 书签已添加  第{self.cur_ch+1}章')
#         _jsave(MARKS_FILE,self.marks); self._update_nav()

#     def open_marks(self):
#         marks=self.marks.get(self.book_path,[])
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('书签'); win.geometry('300x360')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='🔖 书签列表',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
#         lf=tk.Frame(win,bg=bg); lf.pack(fill='both',expand=True,padx=4,pady=4)
#         sb2=tk.Scrollbar(lf); sb2.pack(side='right',fill='y')
#         lb=tk.Listbox(lf,font=('',10),relief='flat',bg=bg,fg=fg,selectbackground=sel,
#                       selectforeground=fg,borderwidth=0,highlightthickness=0,
#                       activestyle='none',yscrollcommand=sb2.set)
#         lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
#         rows=list(marks)
#         for m in rows: lb.insert('end',f"  🏴 第{m['ch']+1}章  {m['ch_title']}  {m['time']}")
#         bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=6,pady=4)
#         def jump():
#             idxs=lb.curselection()
#             if not idxs: return
#             win.destroy(); self.goto_chapter(rows[idxs[0]]['ch'])
#         def delete():
#             idxs=lb.curselection()
#             if not idxs: return
#             m=rows.pop(idxs[0]); lb.delete(idxs[0])
#             self.marks[self.book_path]=[x for x in self.marks.get(self.book_path,[]) if x is not m]
#             _jsave(MARKS_FILE,self.marks); self._update_nav()
#         tk.Button(bf,text='跳转',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=jump).pack(side='left',padx=4)
#         tk.Button(bf,text='删除',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=delete).pack(side='left')
#         lb.bind('<Double-Button-1>',lambda e:jump())
#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'300x360+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 笔记（N 键）
#     # ─────────────────────────────────────────────────
#     def add_note(self):
#         if not self.book_path: messagebox.showinfo('提示','请先打开书'); return
#         ch=self.chapters[self.cur_ch]
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('添加笔记'); win.geometry('340x260')
#         win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text=f'✏ 笔记 — {ch["title"][:20]}',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
#         # 选中文字自动填入
#         sel_text=''
#         try: sel_text=self.txt.get(tk.SEL_FIRST,tk.SEL_LAST)
#         except: pass
#         if sel_text:
#             tk.Label(win,text='引用文字：',font=('',8),bg=bg,fg=fg).pack(anchor='w',padx=8,pady=(6,0))
#             ref=tk.Label(win,text=sel_text[:80]+'…' if len(sel_text)>80 else sel_text,
#                         font=('',8,'italic'),bg=sel,fg=fg,wraplength=300,anchor='w',justify='left')
#             ref.pack(fill='x',padx=8,pady=2)
#         tk.Label(win,text='笔记内容：',font=('',8),bg=bg,fg=fg).pack(anchor='w',padx=8,pady=(6,0))
#         ta=tk.Text(win,height=6,font=('',10),bg=bg,fg=fg,insertbackground=fg,
#                    relief='flat',padx=8,pady=4,wrap='word',borderwidth=1,highlightthickness=1,
#                    highlightbackground=sel,highlightcolor=fg)
#         ta.pack(fill='both',expand=True,padx=8,pady=4); ta.focus()
#         def save():
#             content=ta.get('1.0','end').strip()
#             if not content: win.destroy(); return
#             notes=self.notes.setdefault(self.book_path,[])
#             now=datetime.datetime.now().strftime('%m-%d %H:%M')
#             notes.append({'ch':self.cur_ch,'ch_title':ch['title'],'content':content,
#                           'quote':sel_text,'time':now})
#             _jsave(NOTES_FILE,self.notes); self._update_nav(); win.destroy()
#             self._toast('✏ 笔记已保存')
#         bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=8,pady=4)
#         tk.Button(bf,text='保存笔记',font=('',9,'bold'),bg=bar,fg=fg,relief='flat',
#                   padx=10,command=save).pack(side='right',padx=4)
#         win.bind('<Control-Return>',lambda e:save())

#     def open_notes(self):
#         notes=self.notes.get(self.book_path,[])
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('笔记'); win.geometry('360x480')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='✏ 笔记列表',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)

#         # 列表 + 详情
#         paned=tk.PanedWindow(win,orient='vertical',bg=bg,sashwidth=4,sashrelief='flat')
#         paned.pack(fill='both',expand=True,padx=4,pady=4)

#         top_f=tk.Frame(paned,bg=bg); paned.add(top_f,height=200)
#         sb2=tk.Scrollbar(top_f); sb2.pack(side='right',fill='y')
#         lb=tk.Listbox(top_f,font=('',9),relief='flat',bg=bg,fg=fg,selectbackground=sel,
#                       selectforeground=fg,borderwidth=0,highlightthickness=0,
#                       activestyle='none',yscrollcommand=sb2.set)
#         lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
#         rows=list(notes)
#         for n2 in rows: lb.insert('end',f"  第{n2['ch']+1}章  {n2['ch_title'][:16]}  {n2['time']}")

#         bot_f=tk.Frame(paned,bg=bg); paned.add(bot_f)
#         detail=tk.Text(bot_f,font=('',10),bg=bg,fg=fg,insertbackground=fg,
#                        relief='flat',padx=8,pady=6,wrap='word',state='disabled',
#                        borderwidth=0,highlightthickness=0)
#         detail.pack(fill='both',expand=True)

#         def show_detail(event=None):
#             idxs=lb.curselection()
#             if not idxs: return
#             n2=rows[idxs[0]]
#             detail.config(state='normal'); detail.delete('1.0','end')
#             if n2.get('quote'): detail.insert('end',f'引用：{n2["quote"]}\n\n','quote')
#             detail.insert('end',n2['content'])
#             detail.config(state='disabled')
#         lb.bind('<<ListboxSelect>>',show_detail)

#         bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=6,pady=4)
#         def jump():
#             idxs=lb.curselection()
#             if not idxs: return
#             win.destroy(); self.goto_chapter(rows[idxs[0]]['ch'])
#         def delete():
#             idxs=lb.curselection()
#             if not idxs: return
#             n2=rows.pop(idxs[0]); lb.delete(idxs[0])
#             self.notes[self.book_path]=[x for x in self.notes.get(self.book_path,[]) if x is not n2]
#             _jsave(NOTES_FILE,self.notes); self._update_nav()
#             detail.config(state='normal'); detail.delete('1.0','end'); detail.config(state='disabled')
#         tk.Button(bf,text='跳转章节',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=jump).pack(side='left',padx=4)
#         tk.Button(bf,text='删除笔记',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=delete).pack(side='left')
#         lb.bind('<Double-Button-1>',lambda e:jump())
#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'360x480+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 章节目录
#     # ─────────────────────────────────────────────────
#     def open_chapters(self):
#         if not self.chapters: messagebox.showinfo('提示','请先打开小说'); return
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         mark_set={m['ch'] for m in self.marks.get(self.book_path,[])}
#         note_set={n2['ch'] for n2 in self.notes.get(self.book_path,[])}
#         win=tk.Toplevel(self.root); win.title('章节目录'); win.geometry('300x500')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='📑 章节目录',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
#         sf=tk.Frame(win,bg=bg); sf.pack(fill='x',padx=6,pady=(6,2))
#         sv=tk.StringVar()
#         se=tk.Entry(sf,textvariable=sv,font=('',9),bg=bg,fg=fg,insertbackground=fg,relief='groove')
#         se.pack(fill='x',ipady=3)
#         PH='搜索章节名...'
#         se.insert(0,PH); se.config(fg='gray')
#         se.bind('<FocusIn>',lambda e:(se.delete(0,'end'),se.config(fg=fg)) if se.get()==PH else None)
#         se.bind('<FocusOut>',lambda e:(se.insert(0,PH),se.config(fg='gray')) if not se.get() else None)
#         lf=tk.Frame(win,bg=bg); lf.pack(fill='both',expand=True,padx=4,pady=4)
#         sb2=tk.Scrollbar(lf); sb2.pack(side='right',fill='y')
#         lb=tk.Listbox(lf,font=('',10),relief='flat',bg=bg,fg=fg,selectbackground=sel,
#                       selectforeground=fg,borderwidth=0,highlightthickness=0,
#                       activestyle='none',yscrollcommand=sb2.set)
#         lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
#         btn_j=tk.Button(win,text='↩ 跳转',font=('',9,'bold'),bg=bar,fg=fg,relief='flat',pady=5)
#         btn_j.pack(fill='x',padx=6,pady=4)
#         all_ch=list(self.chapters); visible=list(range(len(all_ch)))
#         def fill(indices):
#             visible.clear(); visible.extend(indices); lb.delete(0,'end')
#             for i in indices:
#                 flags=('🔖' if i in mark_set else '')+('✏' if i in note_set else '')
#                 cur='▶ ' if i==self.cur_ch else '  '
#                 lb.insert('end',f'{cur}{i+1}. {all_ch[i]["title"]}{flags}')
#         fill(range(len(all_ch)))
#         try: lb.see(self.cur_ch); lb.selection_set(self.cur_ch)
#         except: pass
#         def on_search(*_):
#             q=sv.get().strip()
#             fill(range(len(all_ch))) if q in ('',PH) else fill([i for i,c in enumerate(all_ch) if q in c['title']])
#         sv.trace_add('write',on_search)
#         def jump(e=None):
#             idxs=lb.curselection()
#             if not idxs: return
#             win.destroy(); self.goto_chapter(visible[idxs[0]])
#         btn_j.config(command=jump); lb.bind('<Double-Button-1>',jump); lb.bind('<Return>',jump)
#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'300x500+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # Toast 提示
#     # ─────────────────────────────────────────────────
#     def _toast(self,msg,ms=1500):
#         t=self._cur_theme()
#         try:
#             for w in self.root.winfo_children():
#                 if isinstance(w,tk.Label) and getattr(w,'_is_toast',False): w.destroy()
#         except: pass
#         toast=tk.Label(self.root,text=msg,font=('',8),bg=t['bar'],fg=t['fg'],
#                        padx=10,pady=4,relief='flat')
#         toast._is_toast=True
#         toast.place(relx=0.5,rely=0.06,anchor='n')
#         self.root.after(ms,lambda: (toast.winfo_exists() and toast.destroy()))

#     # ─────────────────────────────────────────────────
#     # 欢迎页
#     # ─────────────────────────────────────────────────
#     def _show_welcome(self):
#         self.txt.config(state='normal'); self.txt.delete('1.0','end')
#         self.txt.insert('1.0',(
#             '\n\n\n'
#             '        📚  摸鱼阅读器  v8\n\n'
#             '  支持：TXT  /  EPUB  /  MD\n\n'
#             '  顶部按钮：书架  目录  笔记  书签  打开\n\n'
#             '  操作：\n'
#             '    滚轮 / 拖拽右侧滚动条  章内滚动\n'
#             '    滚到章末再滚           切下一章\n'
#             '    点击左侧 28% / 右侧    切上下章\n'
#             '    ← →  切章   S/↓  翻屏\n\n'
#             '  快捷键：\n'
#             '    O        添加书签\n'
#             '    N        添加笔记\n'
#             '    F5       开始/停止朗读\n'
#             '    D+E      最小化\n'
#         ))
#         self.txt.config(state='disabled')

#     # ─────────────────────────────────────────────────
#     # 最小化
#     # ─────────────────────────────────────────────────
#     def toggle_minimize(self):
#         self._minimized=not self._minimized
#         if self._minimized:
#             self._saved_h=self.root.winfo_height()
#             for w in (self.setbar,self.sep,self.txt_frame,self.bot_area): w.pack_forget()
#             self.root.geometry(f'{self.root.winfo_width()}x30')
#         else:
#             self.root.geometry(f'{self.root.winfo_width()}x{self._saved_h}')
#             self.sep.pack(fill='x',after=self.topbar)
#             if self._settings_open: self.setbar.pack(fill='x',after=self.topbar); self._retheme_setbar()
#             self.txt_frame.pack(fill='both',expand=True)
#             self.bot_area.pack(fill='x',side='bottom')

#     def toggle_settings(self):
#         self._settings_open=not self._settings_open
#         if self._settings_open: self.setbar.pack(fill='x',after=self.topbar); self._retheme_setbar()
#         else: self.setbar.pack_forget()

#     # ─────────────────────────────────────────────────
#     # 全文搜索（Ctrl+F）
#     # ─────────────────────────────────────────────────
#     def open_search(self):
#         if not self.chapters:
#             messagebox.showinfo('提示', '请先打开小说'); return

#         t = self._cur_theme()
#         bg, fg, bar, sel = t['bg'], t['fg'], t['bar'], t['sel']

#         # 若搜索窗已存在则聚焦
#         if hasattr(self, '_search_win') and self._search_win.winfo_exists():
#             self._search_win.lift(); self._search_win.focus_force(); return

#         win = tk.Toplevel(self.root)
#         win.title('全文搜索')
#         win.geometry('480x560')
#         win.resizable(True, True)
#         win.attributes('-topmost', True)
#         win.configure(bg=bg)
#         self._search_win = win

#         # ── 顶部搜索框 ────────────────────────────────
#         top = tk.Frame(win, bg=bar); top.pack(fill='x', padx=0, pady=0)
#         tk.Label(top, text='🔍', font=('',11), bg=bar, fg=fg).pack(side='left', padx=8, pady=6)

#         sv = tk.StringVar()
#         entry = tk.Entry(top, textvariable=sv, font=('',11), bg=bg, fg=fg,
#                          insertbackground=fg, relief='flat', bd=0)
#         entry.pack(side='left', fill='x', expand=True, ipady=4)

#         # 大小写 / 正则 选项
#         var_case  = tk.BooleanVar(value=False)
#         var_regex = tk.BooleanVar(value=False)
#         tk.Checkbutton(top, text='Aa', variable=var_case, font=('',8),
#                        bg=bar, fg=fg, activebackground=bar,
#                        selectcolor=bg).pack(side='left', padx=2)
#         tk.Checkbutton(top, text='.*', variable=var_regex, font=('',8),
#                        bg=bar, fg=fg, activebackground=bar,
#                        selectcolor=bg).pack(side='left', padx=2)

#         lbl_count = tk.Label(top, text='', font=('',8), bg=bar, fg=sel)
#         lbl_count.pack(side='left', padx=6)
#         tk.Button(top, text='×', relief='flat', font=('',10),
#                   bg=bar, fg=fg, command=win.destroy).pack(side='right', padx=6)

#         sep2 = tk.Frame(win, height=1, bg=sel); sep2.pack(fill='x')

#         # ── 结果列表 ──────────────────────────────────
#         list_frame = tk.Frame(win, bg=bg); list_frame.pack(fill='both', expand=True)
#         sb2 = tk.Scrollbar(list_frame); sb2.pack(side='right', fill='y')
#         lb = tk.Listbox(list_frame, font=('',9), relief='flat', bg=bg, fg=fg,
#                         selectbackground=sel, selectforeground=fg,
#                         borderwidth=0, highlightthickness=0,
#                         activestyle='none', yscrollcommand=sb2.set)
#         lb.pack(fill='both', expand=True); sb2.config(command=lb.yview)

#         # ── 预览区 ────────────────────────────────────
#         sep3 = tk.Frame(win, height=1, bg=sel); sep3.pack(fill='x')
#         preview_frame = tk.Frame(win, bg=bg, height=130)
#         preview_frame.pack(fill='x', padx=0); preview_frame.pack_propagate(False)

#         preview = tk.Text(preview_frame, font=('',9), bg=bg, fg=fg,
#                           relief='flat', padx=12, pady=6, wrap='word',
#                           state='disabled', borderwidth=0, highlightthickness=0)
#         preview.pack(fill='both', expand=True)
#         preview.tag_config('hit',  background='#d79921', foreground='#1d2021')
#         preview.tag_config('info', foreground=sel)

#         # 底部跳转栏
#         bot_f = tk.Frame(win, bg=bar, height=30)
#         bot_f.pack(fill='x'); bot_f.pack_propagate(False)
#         lbl_loc = tk.Label(bot_f, text='', font=('',8), bg=bar, fg=fg)
#         lbl_loc.pack(side='left', padx=8, pady=4)
#         btn_jump = tk.Button(bot_f, text='↩ 跳转到此处', font=('',8,'bold'),
#                              bg=bar, fg=fg, relief='flat', padx=8,
#                              state='disabled')
#         btn_jump.pack(side='right', padx=8, pady=3)

#         # ── 搜索逻辑 ──────────────────────────────────
#         results = []   # [(ch_idx, start_in_body, end_in_body, snippet)]

#         def do_search(*_):
#             results.clear(); lb.delete(0, 'end')
#             query = sv.get().strip()
#             if not query:
#                 lbl_count.config(text=''); return

#             flags = 0 if var_case.get() else re.IGNORECASE
#             try:
#                 if var_regex.get():
#                     pat = re.compile(query, flags)
#                 else:
#                     pat = re.compile(re.escape(query), flags)
#             except re.error as e:
#                 lbl_count.config(text=f'正则错误: {e}'); return

#             CONTEXT = 40   # 匹配前后各取多少字符
#             for ci, ch in enumerate(self.chapters):
#                 for m in pat.finditer(ch['body']):
#                     s, e2 = m.start(), m.end()
#                     pre  = ch['body'][max(0, s-CONTEXT):s].replace('\n', ' ')
#                     hit  = ch['body'][s:e2]
#                     post = ch['body'][e2:min(len(ch['body']), e2+CONTEXT)].replace('\n', ' ')
#                     snippet = (pre, hit, post)
#                     results.append((ci, s, e2, snippet))

#             lbl_count.config(text=f'共 {len(results)} 处')
#             for ci, s, e2, (pre, hit, post) in results:
#                 ch_title = self.chapters[ci]['title']
#                 display  = f"  第{ci+1}章  {ch_title[:14]}…  「{hit[:20]}」"
#                 lb.insert('end', display)

#             # 清空预览
#             preview.config(state='normal'); preview.delete('1.0','end')
#             preview.config(state='disabled')
#             lbl_loc.config(text='')
#             btn_jump.config(state='disabled')

#         sv.trace_add('write', do_search)
#         var_case.trace_add('write',  do_search)
#         var_regex.trace_add('write', do_search)

#         def on_select(event=None):
#             idxs = lb.curselection()
#             if not idxs: return
#             ci, s, e2, (pre, hit, post) = results[idxs[0]]
#             ch = self.chapters[ci]

#             # 更新预览
#             preview.config(state='normal'); preview.delete('1.0','end')
#             preview.insert('end', f'第{ci+1}章  {ch["title"]}\n', 'info')
#             preview.insert('end', '…' + pre)
#             preview.insert('end', hit, 'hit')
#             preview.insert('end', post + '…')
#             preview.config(state='disabled')

#             lbl_loc.config(text=f'第{ci+1}章 · 位置 {s}')
#             btn_jump.config(state='normal',
#                             command=lambda: _jump(ci, s, e2, hit))

#         def _jump(ci, s, e2, hit):
#             # 跳转到章节，并高亮匹配文字
#             self.goto_chapter(ci)
#             win.lift()
#             # 在 txt 里找到并高亮
#             self.root.after(80, lambda: _highlight_in_txt(hit))

#         def _highlight_in_txt(hit):
#             self.txt.tag_remove('search_hit', '1.0', 'end')
#             self.txt.tag_config('search_hit', background='#d79921', foreground='#1d2021')
#             start = '1.0'
#             while True:
#                 pos = self.txt.search(hit, start, nocase=not var_case.get(), stopindex='end')
#                 if not pos: break
#                 end_pos = f'{pos}+{len(hit)}c'
#                 self.txt.tag_add('search_hit', pos, end_pos)
#                 self.txt.see(pos)
#                 start = end_pos

#         lb.bind('<<ListboxSelect>>', on_select)
#         lb.bind('<Double-Button-1>', lambda e: btn_jump.invoke())
#         lb.bind('<Return>',         lambda e: btn_jump.invoke())

#         entry.focus()
#         # 如果有选中文字，自动填入搜索框
#         try:
#             sel_text = self.txt.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
#             if sel_text and '\n' not in sel_text:
#                 sv.set(sel_text)
#         except: pass

#         rx = self.root.winfo_x() + self.root.winfo_width() + 8
#         ry = self.root.winfo_y()
#         win.geometry(f'480x560+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 章节摘要（Ctrl+M）—— 调用 Claude API
#     # ─────────────────────────────────────────────────
#     def open_summary(self):
#         if not self.chapters:
#             messagebox.showinfo('提示', '请先打开小说'); return

#         ch  = self.chapters[self.cur_ch]
#         t   = self._cur_theme()
#         bg, fg, bar, sel = t['bg'], t['fg'], t['bar'], t['sel']

#         win = tk.Toplevel(self.root)
#         win.title('章节摘要')
#         win.geometry('400x440')
#         win.resizable(True, True)
#         win.attributes('-topmost', True)
#         win.configure(bg=bg)

#         hdr = tk.Frame(win, bg=bar, height=30); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr, text=f'✨ 摘要 — {ch["title"][:24]}',
#                  font=('',9,'bold'), bg=bar, fg=fg).pack(side='left', padx=8, pady=5)
#         tk.Button(hdr, text='×', relief='flat', font=('',10),
#                   bg=bar, fg=fg, command=win.destroy).pack(side='right', padx=6)

#         # 选项行：摘要长度 / 风格
#         opt = tk.Frame(win, bg=bar); opt.pack(fill='x', padx=8, pady=4)
#         tk.Label(opt, text='长度', font=('',8), bg=bar, fg=fg).pack(side='left')
#         var_len = tk.StringVar(value='简短')
#         for lbl in ('简短','标准','详细'):
#             tk.Radiobutton(opt, text=lbl, variable=var_len, value=lbl,
#                            font=('',8), bg=bar, fg=fg,
#                            activebackground=bar, selectcolor=bg).pack(side='left', padx=4)

#         tk.Label(opt, text='风格', font=('',8), bg=bar, fg=fg).pack(side='left', padx=(10,0))
#         var_style = tk.StringVar(value='客观')
#         for lbl in ('客观','活泼','学术'):
#             tk.Radiobutton(opt, text=lbl, variable=var_style, value=lbl,
#                            font=('',8), bg=bar, fg=fg,
#                            activebackground=bar, selectcolor=bg).pack(side='left', padx=4)

#         sep2 = tk.Frame(win, height=1, bg=sel); sep2.pack(fill='x')

#         # 摘要展示区
#         txt_box = tk.Text(win, font=('',10), bg=bg, fg=fg,
#                           insertbackground=fg, relief='flat',
#                           padx=14, pady=10, wrap='word',
#                           borderwidth=0, highlightthickness=0)
#         txt_box.pack(fill='both', expand=True)
#         txt_box.tag_config('title', font=('',10,'bold'), foreground=fg)
#         txt_box.tag_config('body',  font=('',10))
#         txt_box.tag_config('dim',   foreground=sel)
#         txt_box.tag_config('warn',  foreground='#cc241d')

#         # 底部按钮栏
#         bot = tk.Frame(win, bg=bar, height=32); bot.pack(fill='x'); bot.pack_propagate(False)
#         btn_gen  = tk.Button(bot, text='✨ 生成摘要', font=('',9,'bold'),
#                              bg=bar, fg=fg, relief='flat', padx=10)
#         btn_gen.pack(side='left', padx=8, pady=4)
#         btn_copy = tk.Button(bot, text='复制', font=('',8),
#                              bg=bar, fg=fg, relief='flat', padx=6, state='disabled')
#         btn_copy.pack(side='left', padx=2, pady=4)
#         btn_note_it = tk.Button(bot, text='存为笔记', font=('',8),
#                                 bg=bar, fg=fg, relief='flat', padx=6, state='disabled')
#         btn_note_it.pack(side='left', padx=2, pady=4)
#         lbl_status = tk.Label(bot, text='', font=('',8), bg=bar, fg=sel)
#         lbl_status.pack(side='right', padx=8)

#         generated = ['']   # 用列表保存摘要文本（方便闭包修改）

#         def _set_text(content, tag='body'):
#             txt_box.config(state='normal')
#             txt_box.delete('1.0', 'end')
#             txt_box.insert('end', content, tag)
#             txt_box.config(state='disabled')

#         def _build_prompt():
#             length_map = {'简短': '100字以内', '标准': '200字左右', '详细': '400字左右'}
#             style_map  = {'客观': '客观简洁', '活泼': '生动活泼，可适当使用emoji',
#                           '学术': '学术严谨，条理清晰'}
#             words = ch['body'][:4000]   # 避免超长章节
#             return (
#                 f"请对以下小说章节内容做摘要，要求：\n"
#                 f"1. 长度：{length_map[var_len.get()]}\n"
#                 f"2. 风格：{style_map[var_style.get()]}\n"
#                 f"3. 包含：主要人物、核心情节、关键转折\n"
#                 f"4. 直接输出摘要内容，不要任何前缀\n\n"
#                 f"章节标题：{ch['title']}\n\n"
#                 f"章节内容：\n{words}"
#             )

#         def generate():
#             btn_gen.config(state='disabled', text='生成中…')
#             btn_copy.config(state='disabled')
#             btn_note_it.config(state='disabled')
#             lbl_status.config(text='')
#             _set_text('正在调用智谱 GLM 生成摘要，请稍候…', 'dim')

#             def run():
#                 import urllib.request, urllib.error, json as _json

#                 # 读取 API Key
#                 api_key = _inject_api_key()
#                 if not api_key:
#                     win.after(0, lambda: _on_error('NO_KEY'))
#                     return

#                 prompt = _build_prompt()
#                 payload = _json.dumps({
#                     'model':      'glm-4-flash',   # 免费模型，也可改 glm-4-plus / glm-4
#                     'max_tokens': 1024,
#                     'temperature': 0.7,
#                     'messages':   [{'role': 'user', 'content': prompt}]
#                 }).encode('utf-8')

#                 req = urllib.request.Request(
#                     'https://open.bigmodel.cn/api/paas/v4/chat/completions',
#                     data    = payload,
#                     headers = {
#                         'Content-Type':  'application/json',
#                         'Authorization': f'Bearer {api_key}',
#                     },
#                     method  = 'POST',
#                 )
#                 try:
#                     with urllib.request.urlopen(req, timeout=30) as resp:
#                         data    = _json.loads(resp.read().decode('utf-8'))
#                         summary = data['choices'][0]['message']['content'].strip()
#                     win.after(0, lambda: _on_success(summary))
#                 except urllib.error.HTTPError as e:
#                     body = e.read().decode('utf-8', errors='replace')
#                     try:
#                         err_detail = _json.loads(body)
#                         err_msg = err_detail.get('error', {}).get('message', body)
#                         err_code = str(e.code)
#                     except:
#                         err_msg = body[:300]
#                         err_code = str(e.code)
#                     win.after(0, lambda: _on_error(f'HTTP {err_code}: {err_msg}'))
#                 except Exception as e:
#                     win.after(0, lambda: _on_error(str(e)))

#             threading.Thread(target=run, daemon=True).start()

#         def _on_success(summary):
#             generated[0] = summary
#             _set_text(summary)
#             btn_gen.config(state='normal', text='✨ 重新生成')
#             btn_copy.config(state='normal')
#             btn_note_it.config(state='normal')
#             lbl_status.config(text=f'约 {len(summary)} 字')

#         def _on_error(msg):
#             btn_gen.config(state='normal', text='✨ 生成摘要')
#             if msg == 'NO_KEY':
#                 tip = (
#                     '⚠ 未找到 API Key\n\n'
#                     '请在程序同目录创建 api_key.txt 文件，\n'
#                     '将您的智谱 API Key 粘贴进去保存。\n\n'
#                     '获取地址：https://open.bigmodel.cn\n'
#                     '注册后在「API Keys」页面创建即可。\n'
#                     'GLM-4-Flash 模型对新用户有免费额度。'
#                 )
#             elif '401' in msg:
#                 tip = (
#                     '⚠ API Key 无效或已过期\n\n'
#                     '请检查 api_key.txt 中的 Key 是否正确，\n'
#                     '可前往 https://open.bigmodel.cn 重新获取。\n\n'
#                     f'错误详情：{msg}'
#                 )
#             elif '429' in msg:
#                 tip = (
#                     '⚠ 请求频率过高\n\n'
#                     '智谱 API 有速率限制，请稍等几秒后重试。\n\n'
#                     f'错误详情：{msg}'
#                 )
#             else:
#                 tip = f'⚠ 生成失败\n\n{msg}'
#             _set_text(tip, 'warn')

#         def copy_summary():
#             win.clipboard_clear()
#             win.clipboard_append(generated[0])
#             lbl_status.config(text='已复制！')
#             win.after(1500, lambda: lbl_status.config(text=f'约 {len(generated[0])} 字'))

#         def save_as_note():
#             if not generated[0]: return
#             notes = self.notes.setdefault(self.book_path, [])
#             now   = datetime.datetime.now().strftime('%m-%d %H:%M')
#             notes.append({'ch': self.cur_ch, 'ch_title': ch['title'],
#                           'content': f'[AI摘要]\n{generated[0]}',
#                           'quote': '', 'time': now})
#             _jsave(NOTES_FILE, self.notes)
#             self._update_nav()
#             self._toast('✏ 摘要已存为笔记')
#             lbl_status.config(text='已保存为笔记')

#         btn_gen.config(command=generate)
#         btn_copy.config(command=copy_summary)
#         btn_note_it.config(command=save_as_note)

#         # 读取 api_key.txt（若存在）
#         api_key_exists = bool(_inject_api_key())

#         # 显示当前章节简介（字数、段落数）
#         char_count = len(ch['body'])
#         para_count = len([p for p in ch['body'].split('\n') if p.strip()])
#         key_hint = '' if api_key_exists else '\n⚠ 未检测到 api_key.txt，点击生成时将提示配置方法。'
#         _set_text(
#             f'📖 {ch["title"]}\n\n'
#             f'本章约 {char_count} 字，{para_count} 段。\n\n'
#             f'点击「✨ 生成摘要」，智谱 GLM 将为您总结本章主要内容。\n\n'
#             f'💡 提示：可先调整上方「长度」和「风格」选项。'
#             f'{key_hint}',
#             'dim'
#         )

#         rx = self.root.winfo_x() + self.root.winfo_width() + 8
#         ry = self.root.winfo_y()
#         win.geometry(f'400x440+{rx}+{ry}')


#     # ─────────────────────────────────────────────────
#     # 关闭时保存
#     # ─────────────────────────────────────────────────
#     def _on_close(self):
#         self.tts.stop()
#         self._shelf_update()
#         self.root.destroy()

#     # ─────────────────────────────────────────────────
#     # 快捷键
#     # ─────────────────────────────────────────────────
#     def _bind_keys(self):
#         r=self.root
#         r.bind('<KeyPress-s>',   lambda e: self._scroll_down())
#         r.bind('<KeyPress-S>',   lambda e: self._scroll_down())
#         r.bind('<Right>',        lambda e: self.next_chapter())
#         r.bind('<Left>',         lambda e: self.prev_chapter())
#         r.bind('<Down>',         lambda e: self._scroll_down())
#         r.bind('<Up>',           lambda e: self.txt.yview_scroll(-3,'units'))
#         r.bind('<KeyPress-o>',   lambda e: self.add_mark())
#         r.bind('<KeyPress-O>',   lambda e: self.add_mark())
#         r.bind('<KeyPress-n>',   lambda e: self.add_note())
#         r.bind('<KeyPress-N>',   lambda e: self.add_note())
#         r.bind('<F5>',           lambda e: self.toggle_tts())
#         r.bind('<Control-f>',    lambda e: self.open_search())
#         r.bind('<Control-F>',    lambda e: self.open_search())
#         r.bind('<Control-m>',    lambda e: self.open_summary())
#         r.bind('<Control-M>',    lambda e: self.open_summary())
#         r.bind('<KeyPress-d>',   self._dp)
#         r.bind('<KeyPress-D>',   self._dp)
#         r.bind('<KeyRelease-d>', self._dr)
#         r.bind('<KeyRelease-D>', self._dr)
#         r.bind('<KeyPress-e>',   self._ep)
#         r.bind('<KeyPress-E>',   self._ep)
#         r.focus_set()

#     def _dp(self,e): self._d_held=True
#     def _dr(self,e): self._d_held=False
#     def _ep(self,e):
#         if self._d_held: self.toggle_minimize()


# # ══════════════════════════════════════════════════════════════
# if __name__ == '__main__':
#     try:
#         from ctypes import windll
#         windll.shcore.SetProcessDpiAwareness(1)
#     except: pass
#     App()

# """
# 摸鱼阅读器 v8.0  —  全功能版
# 功能：
#   阅读体验：章节滚动、翻页、字号/行距/字色/背景/护眼模式、透明度、屏幕取色
#   书架管理：添加/删除/重命名书籍、显示封面/进度/上次阅读时间
#   阅读进度：自动记录、书架显示进度条
#   笔记系统：N键在当前章节创建笔记、查看/编辑/删除笔记
#   书签系统：O键快速书签、书签列表跳转删除
#   听书TTS ：F5启动/停止，支持语速调整（需系统 pyttsx3 或 espeak）
#   竖向拖拽滚动条、目录跳转、搜索

# 运行：python novel_reader.py
# 依赖：pip install pyttsx3   （TTS，可选）
#       pip install pillow     （屏幕取色，可选）
# """

# import tkinter as tk
# from tkinter import ttk, filedialog, colorchooser, messagebox, scrolledtext
# import os, re, zipfile, sys, json, copy, threading, time, datetime
# from html.parser import HTMLParser


# # ══════════════════════════════════════════════════════════════
# # HTML → 纯文本
# # ══════════════════════════════════════════════════════════════
# class _H2T(HTMLParser):
#     SKIP  = {'script','style','head','meta','link'}
#     BLOCK = {'p','div','br','h1','h2','h3','h4','h5',
#              'h6','li','tr','td','th','section','article'}
#     def __init__(self): super().__init__(); self.out, self._s = [], 0
#     def handle_starttag(self, tag, _):
#         if tag in self.SKIP:  self._s += 1
#         if tag in self.BLOCK: self.out.append('\n')
#     def handle_endtag(self, tag):
#         if tag in self.SKIP:  self._s = max(0, self._s-1)
#         if tag in self.BLOCK: self.out.append('\n')
#     def handle_data(self, d):
#         if not self._s: self.out.append(d)
#     def text(self): return re.sub(r'\n{3,}','\n\n',''.join(self.out)).strip()

# def html2text(s):
#     p = _H2T()
#     try: p.feed(s)
#     except: pass
#     return p.text()


# # ══════════════════════════════════════════════════════════════
# # EPUB
# # ══════════════════════════════════════════════════════════════
# def read_epub(path):
#     import xml.etree.ElementTree as ET
#     title = os.path.splitext(os.path.basename(path))[0]
#     body  = ''
#     try:
#         with zipfile.ZipFile(path) as z:
#             ns = z.namelist()
#             opf, odir = '', ''
#             if 'META-INF/container.xml' in ns:
#                 for el in ET.fromstring(z.read('META-INF/container.xml')).iter():
#                     if el.tag.endswith('rootfile'):
#                         opf = el.get('full-path',''); odir = opf.rsplit('/',1)[0] if '/' in opf else ''; break
#             items, spine = {}, []
#             if opf and opf in ns:
#                 root = ET.fromstring(z.read(opf))
#                 for el in root.iter():
#                     tag = el.tag.split('}')[-1]
#                     if tag == 'item':
#                         mid,href,mt = el.get('id',''),el.get('href',''),el.get('media-type','')
#                         if href and ('html' in mt or href.endswith(('.html','.xhtml','.htm'))):
#                             items[mid] = (odir+'/'+href).lstrip('/') if odir else href
#                     elif tag == 'itemref':
#                         r = el.get('idref','')
#                         if r in items: spine.append(items[r])
#                     elif tag == 'title' and el.text: title = el.text
#             if not spine:
#                 spine = sorted(f for f in ns if re.search(r'\.(html|htm|xhtml)$',f,re.I)
#                                and 'toc' not in f.lower() and 'nav' not in f.lower())
#             for href in spine:
#                 if href in ns:
#                     try: body += html2text(z.read(href).decode('utf-8','replace')) + '\n\n'
#                     except: pass
#     except Exception as e: body = f'[EPUB解析失败: {e}]'
#     return title, body.strip()


# # ══════════════════════════════════════════════════════════════
# # 章节切割
# # ══════════════════════════════════════════════════════════════
# _CH = re.compile(
#     r'^(第\s*[零一二三四五六七八九十百千万\d〇]+\s*[章节卷集回部篇][^\n]{0,40}'
#     r'|Chapter\s*\d+[^\n]{0,40}|CHAPTER\s*\d+[^\n]{0,40}|【[^\n]{1,30}】)', re.I)

# def split_chapters(text):
#     bounds = []
#     for m in re.finditer(r'^.+$', text, re.M):
#         line = m.group().strip()
#         if line and _CH.match(line): bounds.append((m.start(), line))
#     if not bounds: return [{'title':'全文','body':text}]
#     chs = []
#     for i,(pos,title) in enumerate(bounds):
#         end = bounds[i+1][0] if i+1<len(bounds) else len(text)
#         chs.append({'title':title,'body':text[pos:end]})
#     return chs


# # ══════════════════════════════════════════════════════════════
# # 数据存储
# # ══════════════════════════════════════════════════════════════
# DATA_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.moyu_data')
# os.makedirs(DATA_DIR, exist_ok=True)
# SHELF_FILE = os.path.join(DATA_DIR, 'shelf.json')
# NOTES_FILE = os.path.join(DATA_DIR, 'notes.json')
# MARKS_FILE = os.path.join(DATA_DIR, 'marks.json')

# def _jload(f):
#     try:
#         with open(f, encoding='utf-8') as fp: return json.load(fp)
#     except: return {}

# def _jsave(f, d):
#     try:
#         with open(f, 'w', encoding='utf-8') as fp: json.dump(d, fp, ensure_ascii=False, indent=2)
#     except: pass

# def _inject_api_key():
#     """
#     从程序目录的 api_key.txt 自动读取智谱 API Key。
#     用户把 Key 粘贴进 api_key.txt 即可，无需手动配置环境变量。
#     返回 key 字符串，失败返回空字符串。
#     """
#     key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_key.txt')
#     if os.path.exists(key_file):
#         try:
#             key = open(key_file, encoding='utf-8').read().strip()
#             if key:
#                 os.environ['ZHIPU_API_KEY'] = key
#                 return key
#         except: pass
#     return os.environ.get('ZHIPU_API_KEY', '')


# # ══════════════════════════════════════════════════════════════
# # TTS 引擎（可选）
# # ══════════════════════════════════════════════════════════════
# class TTS:
#     def __init__(self):
#         self._engine = None
#         self._thread = None
#         self._stop   = threading.Event()
#         self._text   = ''
#         self._rate   = 180
#         self._avail  = False
#         self._init()

#     def _init(self):
#         try:
#             import pyttsx3
#             self._engine = pyttsx3.init()
#             self._avail  = True
#         except:
#             self._avail = False

#     @property
#     def available(self): return self._avail

#     def set_rate(self, rate):
#         self._rate = int(rate)
#         if self._engine:
#             try: self._engine.setProperty('rate', self._rate)
#             except: pass

#     def speak(self, text, on_done=None):
#         if not self._avail: return
#         self.stop()
#         self._stop.clear()
#         self._text = text

#         def run():
#             try:
#                 import pyttsx3
#                 eng = pyttsx3.init()
#                 eng.setProperty('rate', self._rate)
#                 # 逐段朗读，支持中途停止
#                 paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
#                 for para in paragraphs:
#                     if self._stop.is_set(): break
#                     eng.say(para)
#                     eng.runAndWait()
#                 eng.stop()
#             except: pass
#             if on_done: on_done()

#         self._thread = threading.Thread(target=run, daemon=True)
#         self._thread.start()

#     def stop(self):
#         self._stop.set()
#         if self._engine:
#             try: self._engine.stop()
#             except: pass


# # ══════════════════════════════════════════════════════════════
# # 屏幕取色器
# # ══════════════════════════════════════════════════════════════
# def screen_color_picker(callback):
#     try: from PIL import ImageGrab
#     except ImportError:
#         c = colorchooser.askcolor(title='选择颜色')
#         if c and c[1]: callback(c[1])
#         return
#     from PIL import ImageGrab, Image, ImageTk
#     ZOOM,HALF = 10,5; CS = (HALF*2+1)*ZOOM
#     preview = tk.Toplevel(); preview.overrideredirect(True)
#     preview.attributes('-topmost',True); preview.configure(bg='#1a1a1a')
#     preview.geometry(f'{CS+4}x{CS+28}+200+200')
#     canvas = tk.Canvas(preview,width=CS,height=CS,bg='#000',highlightthickness=1,
#                        highlightbackground='#555',cursor='none')
#     canvas.pack(padx=2,pady=(2,0))
#     lbl = tk.Label(preview,text='#000000',font=('Consolas',9,'bold'),bg='#1a1a1a',fg='white',pady=1)
#     lbl.pack()
#     cur,ph,aid,done = ['#000000'],[None],[None],[False]
#     def update():
#         if done[0]: return
#         try:
#             mx,my = preview.winfo_pointerx(),preview.winfo_pointery()
#             img = ImageGrab.grab(bbox=(mx-HALF,my-HALF,mx+HALF+1,my+HALF+1))
#             zoomed = img.resize((CS,CS),Image.NEAREST); ph[0]=ImageTk.PhotoImage(zoomed)
#             canvas.delete('all'); canvas.create_image(0,0,anchor='nw',image=ph[0])
#             c2=CS//2
#             canvas.create_line(c2,0,c2,CS,fill='white',width=1)
#             canvas.create_line(0,c2,CS,c2,fill='white',width=1)
#             canvas.create_rectangle(c2-ZOOM,c2-ZOOM,c2+ZOOM,c2+ZOOM,outline='white',width=2)
#             px=img.getpixel((HALF,HALF)); hx='#{:02x}{:02x}{:02x}'.format(px[0],px[1],px[2])
#             cur[0]=hx; lbl.config(text=hx)
#             sw,sh=preview.winfo_screenwidth(),preview.winfo_screenheight()
#             ox,oy=mx+18,my+18
#             if ox+CS+10>sw: ox=mx-CS-22
#             if oy+CS+32>sh: oy=my-CS-34
#             preview.geometry(f'+{ox}+{oy}')
#         except: pass
#         aid[0]=preview.after(40,update)
#     def finish():
#         done[0]=True
#         if aid[0]:
#             try: preview.after_cancel(aid[0])
#             except: pass
#         for w in (overlay,preview):
#             try: w.destroy()
#             except: pass
#     overlay = tk.Toplevel(); overlay.overrideredirect(True)
#     overlay.attributes('-topmost',True); overlay.attributes('-alpha',0.01)
#     sw,sh=overlay.winfo_screenwidth(),overlay.winfo_screenheight()
#     overlay.geometry(f'{sw}x{sh}+0+0'); overlay.configure(bg='white',cursor='crosshair')
#     overlay.bind('<Button-1>',lambda e:(finish(),callback(cur[0])))
#     overlay.bind('<Escape>',lambda e:finish())
#     overlay.focus_force(); aid[0]=preview.after(40,update)


# # ══════════════════════════════════════════════════════════════
# # 自定义竖向滚动条
# # ══════════════════════════════════════════════════════════════
# class SmoothScrollbar:
#     W = 10
#     def __init__(self, parent, on_scroll):
#         self.on_scroll = on_scroll
#         self._lo,self._hi = 0.0,1.0
#         self._dragging = False; self._drag_start_y = 0; self._drag_start_lo = 0.0
#         self.c_bg='#ebdbb2'; self.c_track='#d5c4a1'; self.c_thumb='#b8a882'; self.c_hover='#8f7a55'
#         self.cv = tk.Canvas(parent, width=self.W, highlightthickness=0, cursor='arrow')
#         self.cv.pack(side='right', fill='y')
#         self.cv.bind('<Configure>', lambda e: self._draw())
#         self.cv.bind('<ButtonPress-1>',   self._press)
#         self.cv.bind('<B1-Motion>',       self._drag)
#         self.cv.bind('<ButtonRelease-1>', self._release)
#         self.cv.bind('<Enter>', lambda e: self._hover(True))
#         self.cv.bind('<Leave>', lambda e: self._hover(False))
#         self._hovered = False

#     def set(self, lo, hi): self._lo,self._hi = float(lo),float(hi); self._draw()

#     def set_colors(self, bg, track, thumb, thumb_hover):
#         self.c_bg=bg; self.c_track=track; self.c_thumb=thumb; self.c_hover=thumb_hover; self._draw()

#     def _draw(self):
#         cv=self.cv; W=self.W; H=cv.winfo_height()
#         if H<4: return
#         cv.delete('all'); PAD=2
#         cv.create_rectangle(0,0,W,H,fill=self.c_bg,outline='')
#         tx=W//2
#         cv.create_line(tx,PAD,tx,H-PAD,fill=self.c_track,width=W-4,capstyle='round')
#         th=max(20,int((self._hi-self._lo)*(H-2*PAD))); ty=PAD+int(self._lo*(H-2*PAD))
#         ty2=min(H-PAD,ty+th); color=self.c_hover if self._hovered else self.c_thumb
#         r=(W-4)//2; x1,x2=2,W-2; y1,y2=ty,ty2
#         if y2-y1>=2*r:
#             cv.create_rectangle(x1,y1+r,x2,y2-r,fill=color,outline='')
#             cv.create_oval(x1,y1,x2,y1+2*r,fill=color,outline='')
#             cv.create_oval(x1,y2-2*r,x2,y2,fill=color,outline='')
#         else: cv.create_oval(x1,y1,x2,y2,fill=color,outline='')

#     def _hover(self, v): self._hovered=v; self._draw()

#     def _y_to_frac(self,y):
#         H=self.cv.winfo_height(); PAD=2
#         return max(0.0,min(1.0,(y-PAD)/max(1,H-2*PAD)))

#     def _thumb_range(self):
#         H=self.cv.winfo_height(); PAD=2
#         th=max(20,int((self._hi-self._lo)*(H-2*PAD))); ty=PAD+int(self._lo*(H-2*PAD))
#         return ty,ty+th

#     def _press(self, e):
#         ty1,ty2=self._thumb_range()
#         if ty1<=e.y<=ty2:
#             self._dragging=True; self._drag_start_y=e.y; self._drag_start_lo=self._lo
#         else:
#             frac=self._y_to_frac(e.y); span=self._hi-self._lo
#             self.on_scroll(max(0.0,min(1.0-span,frac-span/2)))

#     def _drag(self, e):
#         if not self._dragging: return
#         H=self.cv.winfo_height(); PAD=2; dy=e.y-self._drag_start_y
#         delta=dy/max(1,H-2*PAD); span=self._hi-self._lo
#         target=max(0.0,min(1.0-span,self._drag_start_lo+delta))
#         self._lo=target; self._hi=target+span; self._draw(); self.on_scroll(target)

#     def _release(self, e): self._dragging=False


# # ══════════════════════════════════════════════════════════════
# # 主程序
# # ══════════════════════════════════════════════════════════════
# class App:

#     THEMES = {
#         '暖黄': dict(bg='#fdf6e3',fg='#3c3836',bar='#ebdbb2',sel='#d5c4a1',thumb='#b8a882',thumb_h='#8f7a55'),
#         '夜间': dict(bg='#1e1e2e',fg='#cdd6f4',bar='#181825',sel='#313244',thumb='#45475a',thumb_h='#6c7086'),
#         '护眼': dict(bg='#1a2f1a',fg='#a8d5a2',bar='#152315',sel='#2d5a2d',thumb='#3a6b3a',thumb_h='#57c454'),
#         '纸张': dict(bg='#f5f0e8',fg='#2c2416',bar='#ede4d0',sel='#c8b89a',thumb='#c8a882',thumb_h='#8b6045'),
#         '白底': dict(bg='#ffffff',fg='#1a1a1a',bar='#f0f0f0',sel='#dddddd',thumb='#bbbbbb',thumb_h='#888888'),
#     }

#     def __init__(self):
#         self.root = tk.Tk()
#         self.root.title('摸鱼阅读器')
#         self.root.geometry('440x600')
#         self.root.minsize(320, 400)
#         self.root.attributes('-topmost', True)

#         # 数据
#         self.shelf   = _jload(SHELF_FILE)   # {path: {title,last_ch,total_ch,last_time,read_time}}
#         self.notes   = _jload(NOTES_FILE)   # {path: [{ch,title,content,time}]}
#         self.marks   = _jload(MARKS_FILE)   # {path: [{ch,ch_title,time}]}

#         self.book_path  = ''
#         self.book_title = ''
#         self.chapters   = []
#         self.cur_ch     = 0

#         # UI 状态
#         self.theme_name     = '暖黄'
#         self.custom_bg      = None
#         self.custom_bar     = None
#         self.font_size      = 14
#         self.line_spacing   = 6
#         self.font_fam       = ('宋体' if sys.platform=='win32'
#                                else 'Songti SC' if sys.platform=='darwin'
#                                else 'Noto Serif CJK SC')
#         self._d_held        = False
#         self._minimized     = False
#         self._settings_open = False
#         self._wheel_accum   = 0
#         self._tts_playing   = False

#         self.tts = TTS()

#         self._build_ui()
#         self._apply_theme()
#         self._bind_keys()
#         self.root.protocol('WM_DELETE_WINDOW', self._on_close)
#         self.root.mainloop()

#     # ─────────────────────────────────────────────────
#     # UI 构建
#     # ─────────────────────────────────────────────────
#     def _build_ui(self):
#         r = self.root

#         # 顶部栏
#         self.topbar = tk.Frame(r, height=30)
#         self.topbar.pack(fill='x')
#         self.topbar.pack_propagate(False)

#         dots = tk.Frame(self.topbar)
#         dots.pack(side='left', padx=6, pady=5)
#         self._dot(dots, '#ff5f57', self.toggle_minimize)
#         self._dot(dots, '#ffbd2e', self.toggle_settings)
#         self._dot(dots, '#28ca41', self.open_file)

#         self.lbl_title = tk.Label(self.topbar, text='摸鱼阅读器', font=('',9))
#         self.lbl_title.pack(side='left', fill='x', expand=True)

#         rbf = tk.Frame(self.topbar); rbf.pack(side='right', padx=2)
#         self._tbtn(rbf, '书架', self.open_shelf)
#         self._tbtn(rbf, '目录', self.open_chapters)
#         self._tbtn(rbf, '搜索', self.open_search)
#         self._tbtn(rbf, '摘要', self.open_summary)
#         self._tbtn(rbf, '笔记', self.open_notes)
#         self._tbtn(rbf, '书签', self.open_marks)
#         self._tbtn(rbf, '打开', self.open_file)
#         self._tbtn(rbf, '×',   r.destroy)

#         for w in (self.topbar, self.lbl_title):
#             w.bind('<ButtonPress-1>', self._drag_start)
#             w.bind('<B1-Motion>',     self._drag_move)

#         # 设置栏
#         self.setbar = tk.Frame(r)
#         self._build_setbar()

#         # 分隔线
#         self.sep = tk.Frame(r, height=1)
#         self.sep.pack(fill='x')

#         # 文本区
#         self.txt_frame = tk.Frame(r)
#         self.txt_frame.pack(fill='both', expand=True)

#         self.vsb = SmoothScrollbar(self.txt_frame,
#                                    on_scroll=lambda f: self.txt.yview_moveto(f))

#         self.txt = tk.Text(
#             self.txt_frame, wrap='word',
#             relief='flat', padx=16, pady=10,
#             state='disabled', cursor='arrow',
#             font=(self.font_fam, self.font_size),
#             borderwidth=0, highlightthickness=0,
#             spacing1=self.line_spacing,
#             spacing2=self.line_spacing//2,
#             spacing3=self.line_spacing,
#             yscrollcommand=self._on_yscroll,
#         )
#         self.txt.pack(side='left', fill='both', expand=True)
#         self.txt.bind('<Button-1>',   self._on_click)
#         self.txt.bind('<MouseWheel>', self._on_wheel)
#         self.txt.bind('<Button-4>',   self._on_wheel)
#         self.txt.bind('<Button-5>',   self._on_wheel)
#         self._show_welcome()

#         # 底部
#         self.bot_area = tk.Frame(r)
#         self.bot_area.pack(fill='x', side='bottom')

#         self.botbar = tk.Frame(self.bot_area, height=28)
#         self.botbar.pack(fill='x')
#         self.botbar.pack_propagate(False)

#         self.btn_prev = tk.Button(self.botbar, text='◀', font=('',9),
#                                   relief='flat', padx=4, command=self.prev_chapter)
#         self.btn_prev.pack(side='left', padx=4, pady=3)

#         self.lbl_prog = tk.Label(self.botbar, text='', font=('',8))
#         self.lbl_prog.pack(side='left', expand=True)

#         self.btn_tts = tk.Button(self.botbar, text='🔊', font=('',9),
#                                  relief='flat', padx=3, command=self.toggle_tts)
#         self.btn_tts.pack(side='right', padx=2, pady=3)

#         self.btn_note = tk.Button(self.botbar, text='✏', font=('',9),
#                                   relief='flat', padx=3, command=self.add_note)
#         self.btn_note.pack(side='right', padx=2, pady=3)

#         self.btn_mark = tk.Button(self.botbar, text='🔖', font=('',9),
#                                   relief='flat', padx=2, command=self.add_mark)
#         self.btn_mark.pack(side='right', padx=2, pady=3)

#         self.btn_next = tk.Button(self.botbar, text='▶', font=('',9),
#                                   relief='flat', padx=4, command=self.next_chapter)
#         self.btn_next.pack(side='right', padx=4, pady=3)

#     def _tbtn(self, parent, text, cmd):
#         tk.Button(parent, text=text, font=('',8), relief='flat',
#                   padx=3, command=cmd).pack(side='left', padx=1)

#     def _dot(self, p, color, cmd):
#         lb = tk.Label(p, text='⬤', fg=color, font=('',12), cursor='hand2')
#         lb.pack(side='left', padx=2)
#         lb.bind('<Button-1>', lambda e: cmd())

#     # ─────────────────────────────────────────────────
#     # 设置栏
#     # ─────────────────────────────────────────────────
#     def _build_setbar(self):
#         def row(): f=tk.Frame(self.setbar); f.pack(fill='x',padx=8,pady=2); return f

#         r1 = row()
#         tk.Label(r1,text='字号',font=('',8)).pack(side='left')
#         self.sl_font = tk.Scale(r1,from_=10,to=32,orient='horizontal',length=70,
#                                 showvalue=True,font=('',7),command=self._on_font_size)
#         self.sl_font.set(self.font_size); self.sl_font.pack(side='left',padx=2)
#         tk.Label(r1,text='行距',font=('',8)).pack(side='left',padx=(8,0))
#         self.sl_spacing = tk.Scale(r1,from_=0,to=24,orient='horizontal',length=70,
#                                    showvalue=True,font=('',7),command=self._on_spacing)
#         self.sl_spacing.set(self.line_spacing); self.sl_spacing.pack(side='left',padx=2)

#         r2 = row()
#         tk.Label(r2,text='透明',font=('',8)).pack(side='left')
#         self.sl_alpha = tk.Scale(r2,from_=20,to=100,orient='horizontal',length=80,
#                                  showvalue=True,font=('',7),
#                                  command=lambda v: self.root.attributes('-alpha',int(v)/100))
#         self.sl_alpha.set(100); self.sl_alpha.pack(side='left',padx=2)
#         # TTS 语速
#         tk.Label(r2,text='语速',font=('',8)).pack(side='left',padx=(8,0))
#         self.sl_tts_rate = tk.Scale(r2,from_=80,to=300,orient='horizontal',length=70,
#                                     showvalue=True,font=('',7),
#                                     command=lambda v: self.tts.set_rate(int(v)))
#         self.sl_tts_rate.set(180); self.sl_tts_rate.pack(side='left',padx=2)

#         r3 = row()
#         tk.Label(r3,text='字色',font=('',8)).pack(side='left')
#         self.btn_fg_color = tk.Button(r3,text='  ',relief='groove',width=2,
#                                       font=('',8),command=self._pick_fg)
#         self.btn_fg_color.pack(side='left',padx=2)
#         tk.Label(r3,text='背景',font=('',8)).pack(side='left',padx=(6,0))
#         self.btn_bg_color = tk.Button(r3,text='  ',relief='groove',width=2,
#                                       font=('',8),command=self._pick_bg)
#         self.btn_bg_color.pack(side='left',padx=2)
#         tk.Button(r3,text='🎨取色',font=('',8),relief='flat',padx=4,
#                   command=self._screen_pick).pack(side='left',padx=4)
#         tk.Button(r3,text='重置',font=('',8),relief='flat',padx=4,
#                   command=self._reset_colors).pack(side='left',padx=2)

#         r4 = row()
#         tk.Label(r4,text='主题',font=('',8)).pack(side='left')
#         self.var_theme = tk.StringVar(value=self.theme_name)
#         cb = ttk.Combobox(r4,textvariable=self.var_theme,
#                           values=list(self.THEMES.keys()),width=7,font=('',8),state='readonly')
#         cb.pack(side='left',padx=4); cb.bind('<<ComboboxSelected>>',self._on_theme)
#         # 快速护眼切换
#         tk.Button(r4,text='☘护眼',font=('',8),relief='flat',padx=4,
#                   command=lambda: (self.var_theme.set('护眼'),self._on_theme())).pack(side='left',padx=2)
#         tk.Button(r4,text='🌙夜间',font=('',8),relief='flat',padx=4,
#                   command=lambda: (self.var_theme.set('夜间'),self._on_theme())).pack(side='left',padx=2)

#     # ─────────────────────────────────────────────────
#     # 颜色
#     # ─────────────────────────────────────────────────
#     def _pick_fg(self):
#         t=self._cur_theme(); c=colorchooser.askcolor(color=t['fg'],title='字体颜色')
#         if c and c[1]: self.THEMES[self.theme_name]['fg']=c[1]; self.txt.config(fg=c[1]); self.btn_fg_color.config(bg=c[1])

#     def _pick_bg(self):
#         c=colorchooser.askcolor(color=self._cur_theme()['bg'],title='背景颜色')
#         if c and c[1]: self._apply_custom_bg(c[1])

#     def _screen_pick(self):
#         alpha=self.sl_alpha.get()/100; self.root.attributes('-alpha',0.0)
#         def on(hx): self.root.after(100,lambda:self.root.attributes('-alpha',alpha)); self._apply_custom_bg(hx)
#         self.root.after(120, lambda: screen_color_picker(on))

#     def _apply_custom_bg(self,hx):
#         self.custom_bg=hx; self.custom_bar=self._darken(hx,0.88); self._apply_theme()
#         try: self.btn_bg_color.config(bg=hx)
#         except: pass

#     def _reset_colors(self): self.custom_bg=self.custom_bar=None; self._apply_theme()
#     def _darken(self,hx,f=0.88):
#         h=hx.lstrip('#')
#         return '#{:02x}{:02x}{:02x}'.format(int(int(h[0:2],16)*f),int(int(h[2:4],16)*f),int(int(h[4:6],16)*f))

#     def _cur_theme(self):
#         t=copy.copy(self.THEMES[self.theme_name])
#         if self.custom_bg:  t['bg']=self.custom_bg
#         if self.custom_bar: t['bar']=self.custom_bar
#         return t

#     def _on_theme(self, e=None):
#         self.theme_name=self.var_theme.get(); self.custom_bg=self.custom_bar=None; self._apply_theme()

#     def _apply_theme(self):
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         self.root.configure(bg=bar)
#         self._cf(self.topbar,bar,fg); self._cf(self.botbar,bar,fg); self._cf(self.bot_area,bar,fg)
#         self.sep.config(bg=sel); self.txt_frame.config(bg=bg)
#         self.vsb.cv.config(bg=bg)
#         self.vsb.set_colors(bg=bg,track=sel,thumb=t.get('thumb',sel),thumb_hover=t.get('thumb_h',fg))
#         self.txt.config(bg=bg,fg=fg,insertbackground=fg,selectbackground=sel)
#         self.lbl_prog.config(bg=bar,fg=fg)
#         for b in (self.btn_prev,self.btn_next,self.btn_mark,self.btn_note,self.btn_tts):
#             b.config(bg=bar,fg=fg,activebackground=sel)
#         self._retheme_setbar()
#         try:
#             if self.custom_bg: self.btn_bg_color.config(bg=self.custom_bg)
#         except: pass

#     def _cf(self,fr,bg,fg):
#         try: fr.config(bg=bg)
#         except: pass
#         for w in fr.winfo_children():
#             try: w.config(bg=bg,fg=fg,activebackground=bg)
#             except: pass
#             for w2 in w.winfo_children():
#                 try: w2.config(bg=bg,fg=fg,activebackground=bg)
#                 except: pass

#     def _retheme_setbar(self):
#         t=self._cur_theme(); bg,fg,sel=t['bar'],t['fg'],t['sel']
#         self._cf(self.setbar,bg,fg)
#         for sl in (self.sl_font,self.sl_alpha,self.sl_spacing,self.sl_tts_rate):
#             try: sl.config(bg=bg,fg=fg,troughcolor=sel,activebackground=sel)
#             except: pass
#         try: self.btn_fg_color.config(bg=fg)
#         except: pass

#     # ─────────────────────────────────────────────────
#     # 字号 / 行距
#     # ─────────────────────────────────────────────────
#     def _on_font_size(self,val):
#         self.font_size=int(float(val)); self.txt.config(font=(self.font_fam,self.font_size))

#     def _on_spacing(self,val):
#         sp=int(float(val)); self.line_spacing=sp
#         self.txt.config(spacing1=sp,spacing2=sp//2,spacing3=sp)

#     # ─────────────────────────────────────────────────
#     # 拖动窗口
#     # ─────────────────────────────────────────────────
#     def _drag_start(self,e): self._dx=e.x_root-self.root.winfo_x(); self._dy=e.y_root-self.root.winfo_y()
#     def _drag_move(self,e):  self.root.geometry(f'+{e.x_root-self._dx}+{e.y_root-self._dy}')

#     # ─────────────────────────────────────────────────
#     # 打开文件
#     # ─────────────────────────────────────────────────
#     def open_file(self, path=None):
#         if path is None:
#             path = filedialog.askopenfilename(
#                 title='打开小说',
#                 filetypes=[('小说文件','*.txt *.epub *.md'),('所有文件','*.*')])
#         if not path: return
#         ext = os.path.splitext(path)[1].lower()
#         if ext == '.epub': title,text = read_epub(path)
#         else:
#             title = os.path.splitext(os.path.basename(path))[0]
#             try:
#                 with open(path,encoding='utf-8',errors='replace') as f: text=f.read()
#             except Exception as e: messagebox.showerror('错误',str(e)); return
#         self.book_path=path; self.book_title=title
#         self.lbl_title.config(text=f'  {title}'); self.root.title(f'摸鱼阅读器 — {title}')
#         self._load(text)

#     def _load(self,text):
#         self.chapters = split_chapters(text)
#         # 恢复上次阅读位置
#         si = self.shelf.get(self.book_path,{})
#         self.cur_ch = max(0,min(si.get('last_ch',0),len(self.chapters)-1))
#         # 更新书架
#         self._shelf_update()
#         self._render_chapter()

#     # ─────────────────────────────────────────────────
#     # 书架管理
#     # ─────────────────────────────────────────────────
#     def _shelf_update(self):
#         p = self.book_path
#         prev = self.shelf.get(p,{})
#         self.shelf[p] = {
#             'title':      self.book_title,
#             'path':       p,
#             'last_ch':    self.cur_ch,
#             'total_ch':   len(self.chapters),
#             'last_time':  datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
#             'added_time': prev.get('added_time', datetime.datetime.now().strftime('%Y-%m-%d')),
#         }
#         _jsave(SHELF_FILE, self.shelf)

#     def open_shelf(self):
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('书架'); win.geometry('380x460')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)

#         hdr=tk.Frame(win,bg=bar,height=30); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='📚 书架',font=('',10,'bold'),bg=bar,fg=fg).pack(side='left',padx=10,pady=5)
#         tk.Button(hdr,text='+添加',font=('',8),relief='flat',bg=bar,fg=fg,
#                   command=lambda:self._shelf_add(win)).pack(side='right',padx=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,
#                   command=win.destroy).pack(side='right',padx=4)

#         # 书籍列表
#         frame=tk.Frame(win,bg=bg); frame.pack(fill='both',expand=True,padx=6,pady=6)
#         sb2=tk.Scrollbar(frame); sb2.pack(side='right',fill='y')
#         canvas=tk.Canvas(frame,bg=bg,highlightthickness=0,yscrollcommand=sb2.set)
#         canvas.pack(fill='both',expand=True); sb2.config(command=canvas.yview)
#         inner=tk.Frame(canvas,bg=bg); canvas.create_window((0,0),window=inner,anchor='nw')

#         def refresh():
#             for w in inner.winfo_children(): w.destroy()
#             if not self.shelf:
#                 tk.Label(inner,text='书架空空，快去添加书吧',font=('',10),bg=bg,fg=sel).pack(pady=30)
#             for path,info in sorted(self.shelf.items(),key=lambda x:x[1].get('last_time',''),reverse=True):
#                 self._shelf_card(inner,path,info,bg,fg,bar,sel,win,refresh)
#             inner.update_idletasks()
#             canvas.config(scrollregion=canvas.bbox('all'))
#         refresh()

#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'380x460+{rx}+{ry}')

#     def _shelf_card(self,parent,path,info,bg,fg,bar,sel,shelf_win,refresh):
#         card=tk.Frame(parent,bg=bar,relief='flat',bd=0)
#         card.pack(fill='x',padx=4,pady=3)
#         # 封面色块
#         colors=['#8f3f71','#458588','#d79921','#689d6a','#cc241d']
#         ccolor=colors[hash(path)%len(colors)]
#         cover=tk.Frame(card,bg=ccolor,width=36,height=50); cover.pack(side='left',padx=6,pady=6); cover.pack_propagate(False)
#         tk.Label(cover,text='📖',font=('',14),bg=ccolor).pack(expand=True)
#         # 信息
#         info_f=tk.Frame(card,bg=bar); info_f.pack(side='left',fill='both',expand=True,pady=4)
#         tk.Label(info_f,text=info.get('title','未知'),font=('',9,'bold'),bg=bar,fg=fg,anchor='w').pack(fill='x')
#         lc=info.get('last_ch',0); tc=info.get('total_ch',1)
#         pct=int(lc/max(1,tc-1)*100) if tc>1 else 0
#         tk.Label(info_f,text=f'第{lc+1}/{tc}章  {pct}%',font=('',8),bg=bar,fg=sel,anchor='w').pack(fill='x')
#         # 进度条
#         pb_f=tk.Frame(info_f,bg=bar,height=4); pb_f.pack(fill='x',pady=2); pb_f.pack_propagate(False)
#         pb_done=tk.Frame(pb_f,bg=ccolor,height=4); pb_done.place(x=0,y=0,relwidth=pct/100,relheight=1)
#         tk.Frame(pb_f,bg=sel,height=4).place(x=0,y=0,relwidth=1,relheight=1)
#         pb_done.lift()
#         tk.Label(info_f,text=f'上次：{info.get("last_time","")}',font=('',7),bg=bar,fg=sel,anchor='w').pack(fill='x')
#         # 按钮
#         btn_f=tk.Frame(card,bg=bar); btn_f.pack(side='right',padx=6,pady=4)
#         def open_it(p=path):
#             shelf_win.destroy(); self.open_file(p)
#         def del_it(p=path):
#             if messagebox.askyesno('删除','从书架移除此书？',parent=shelf_win):
#                 del self.shelf[p]; _jsave(SHELF_FILE,self.shelf); refresh()
#         tk.Button(btn_f,text='阅读',font=('',8),relief='flat',bg=ccolor,fg='white',
#                   padx=6,command=open_it).pack(pady=2)
#         tk.Button(btn_f,text='移除',font=('',7),relief='flat',bg=bar,fg=sel,
#                   padx=4,command=del_it).pack(pady=2)

#     def _shelf_add(self, shelf_win):
#         path=filedialog.askopenfilename(title='选择书籍',
#             filetypes=[('小说文件','*.txt *.epub *.md'),('所有文件','*.*')])
#         if not path: return
#         if path not in self.shelf:
#             title=os.path.splitext(os.path.basename(path))[0]
#             self.shelf[path]={'title':title,'path':path,'last_ch':0,'total_ch':0,
#                               'last_time':'','added_time':datetime.datetime.now().strftime('%Y-%m-%d')}
#             _jsave(SHELF_FILE,self.shelf)
#         shelf_win.destroy(); self.open_shelf()

#     # ─────────────────────────────────────────────────
#     # 渲染章节
#     # ─────────────────────────────────────────────────
#     def _render_chapter(self, scroll_to_top=True):
#         if not self.chapters: return
#         self.cur_ch=max(0,min(self.cur_ch,len(self.chapters)-1))
#         ch=self.chapters[self.cur_ch]
#         self.txt.config(state='normal'); self.txt.delete('1.0','end')
#         self.txt.insert('1.0', ch['body']); self.txt.config(state='disabled')
#         if scroll_to_top: self.txt.yview_moveto(0.0)
#         self._update_nav(); self._wheel_accum=0
#         self._shelf_update()

#     def _update_nav(self):
#         n=len(self.chapters); idx=self.cur_ch+1
#         # 有无书签/笔记标记
#         m_chs={m['ch'] for m in self.marks.get(self.book_path,[])}
#         n_chs={n2['ch'] for n2 in self.notes.get(self.book_path,[])}
#         flags=('🔖' if self.cur_ch in m_chs else '')+('✏' if self.cur_ch in n_chs else '')
#         self.lbl_prog.config(text=f'{flags}  第{idx}/{n}章')
#         self.btn_prev.config(state='normal' if self.cur_ch>0   else 'disabled')
#         self.btn_next.config(state='normal' if self.cur_ch<n-1 else 'disabled')

#     def _on_yscroll(self,lo,hi): self.vsb.set(lo,hi)

#     # ─────────────────────────────────────────────────
#     # 翻章
#     # ─────────────────────────────────────────────────
#     def next_chapter(self):
#         if self.chapters and self.cur_ch<len(self.chapters)-1:
#             self.cur_ch+=1; self._render_chapter()

#     def prev_chapter(self):
#         if self.chapters and self.cur_ch>0:
#             self.cur_ch-=1; self._render_chapter()

#     def goto_chapter(self,idx):
#         if not self.chapters: return
#         self.cur_ch=max(0,min(idx,len(self.chapters)-1)); self._render_chapter()

#     def _on_click(self,e):
#         w=self.txt.winfo_width()
#         if   e.x<w*0.28: self.prev_chapter()
#         elif e.x>w*0.72: self.next_chapter()

#     def _on_wheel(self,e):
#         delta=1 if e.num==4 else (-1 if e.num==5 else (1 if e.delta>0 else -1))
#         top,bot=self.txt.yview()
#         if delta<0:
#             if bot>=0.999:
#                 self._wheel_accum-=1
#                 if self._wheel_accum<=-3: self.next_chapter(); return
#             else: self._wheel_accum=0; self.txt.yview_scroll(3,'units')
#         else:
#             if top<=0.001:
#                 self._wheel_accum+=1
#                 if self._wheel_accum>=3:
#                     self.prev_chapter(); self.root.after(30,lambda:self.txt.yview_moveto(1.0)); return
#             else: self._wheel_accum=0; self.txt.yview_scroll(-3,'units')

#     def _scroll_down(self):
#         _,bot=self.txt.yview()
#         if bot>=0.999: self.next_chapter()
#         else: self.txt.yview_scroll(1,'pages')

#     # ─────────────────────────────────────────────────
#     # TTS 听书
#     # ─────────────────────────────────────────────────
#     def toggle_tts(self):
#         if not self.tts.available:
#             messagebox.showinfo('提示','请先安装 pyttsx3：\npip install pyttsx3'); return
#         if self._tts_playing:
#             self.tts.stop(); self._tts_playing=False
#             self.btn_tts.config(text='🔊')
#             self._toast('⏹ 已停止朗读')
#         else:
#             if not self.chapters: return
#             ch=self.chapters[self.cur_ch]
#             self._tts_playing=True; self.btn_tts.config(text='⏸')
#             self._toast('▶ 开始朗读…')
#             def done(): self.root.after(0,self._tts_done)
#             self.tts.speak(ch['body'],on_done=done)

#     def _tts_done(self):
#         self._tts_playing=False; self.btn_tts.config(text='🔊')

#     # ─────────────────────────────────────────────────
#     # 书签（O 键）
#     # ─────────────────────────────────────────────────
#     def add_mark(self):
#         if not self.book_path: messagebox.showinfo('提示','请先打开书'); return
#         marks=self.marks.setdefault(self.book_path,[])
#         ch=self.chapters[self.cur_ch]; now=datetime.datetime.now().strftime('%m-%d %H:%M')
#         existing=next((m for m in marks if m['ch']==self.cur_ch),None)
#         entry={'ch':self.cur_ch,'ch_title':ch['title'],'time':now}
#         if existing: existing.update(entry); self._toast('🔖 书签已更新')
#         else: marks.append(entry); self._toast(f'🔖 书签已添加  第{self.cur_ch+1}章')
#         _jsave(MARKS_FILE,self.marks); self._update_nav()

#     def open_marks(self):
#         marks=self.marks.get(self.book_path,[])
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('书签'); win.geometry('300x360')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='🔖 书签列表',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
#         lf=tk.Frame(win,bg=bg); lf.pack(fill='both',expand=True,padx=4,pady=4)
#         sb2=tk.Scrollbar(lf); sb2.pack(side='right',fill='y')
#         lb=tk.Listbox(lf,font=('',10),relief='flat',bg=bg,fg=fg,selectbackground=sel,
#                       selectforeground=fg,borderwidth=0,highlightthickness=0,
#                       activestyle='none',yscrollcommand=sb2.set)
#         lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
#         rows=list(marks)
#         for m in rows: lb.insert('end',f"  🏴 第{m['ch']+1}章  {m['ch_title']}  {m['time']}")
#         bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=6,pady=4)
#         def jump():
#             idxs=lb.curselection()
#             if not idxs: return
#             win.destroy(); self.goto_chapter(rows[idxs[0]]['ch'])
#         def delete():
#             idxs=lb.curselection()
#             if not idxs: return
#             m=rows.pop(idxs[0]); lb.delete(idxs[0])
#             self.marks[self.book_path]=[x for x in self.marks.get(self.book_path,[]) if x is not m]
#             _jsave(MARKS_FILE,self.marks); self._update_nav()
#         tk.Button(bf,text='跳转',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=jump).pack(side='left',padx=4)
#         tk.Button(bf,text='删除',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=delete).pack(side='left')
#         lb.bind('<Double-Button-1>',lambda e:jump())
#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'300x360+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 笔记（N 键）
#     # ─────────────────────────────────────────────────
#     def add_note(self):
#         if not self.book_path: messagebox.showinfo('提示','请先打开书'); return
#         ch=self.chapters[self.cur_ch]
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('添加笔记'); win.geometry('340x260')
#         win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text=f'✏ 笔记 — {ch["title"][:20]}',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
#         # 选中文字自动填入
#         sel_text=''
#         try: sel_text=self.txt.get(tk.SEL_FIRST,tk.SEL_LAST)
#         except: pass
#         if sel_text:
#             tk.Label(win,text='引用文字：',font=('',8),bg=bg,fg=fg).pack(anchor='w',padx=8,pady=(6,0))
#             ref=tk.Label(win,text=sel_text[:80]+'…' if len(sel_text)>80 else sel_text,
#                         font=('',8,'italic'),bg=sel,fg=fg,wraplength=300,anchor='w',justify='left')
#             ref.pack(fill='x',padx=8,pady=2)
#         tk.Label(win,text='笔记内容：',font=('',8),bg=bg,fg=fg).pack(anchor='w',padx=8,pady=(6,0))
#         ta=tk.Text(win,height=6,font=('',10),bg=bg,fg=fg,insertbackground=fg,
#                    relief='flat',padx=8,pady=4,wrap='word',borderwidth=1,highlightthickness=1,
#                    highlightbackground=sel,highlightcolor=fg)
#         ta.pack(fill='both',expand=True,padx=8,pady=4); ta.focus()
#         def save():
#             content=ta.get('1.0','end').strip()
#             if not content: win.destroy(); return
#             notes=self.notes.setdefault(self.book_path,[])
#             now=datetime.datetime.now().strftime('%m-%d %H:%M')
#             notes.append({'ch':self.cur_ch,'ch_title':ch['title'],'content':content,
#                           'quote':sel_text,'time':now})
#             _jsave(NOTES_FILE,self.notes); self._update_nav(); win.destroy()
#             self._toast('✏ 笔记已保存')
#         bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=8,pady=4)
#         tk.Button(bf,text='保存笔记',font=('',9,'bold'),bg=bar,fg=fg,relief='flat',
#                   padx=10,command=save).pack(side='right',padx=4)
#         win.bind('<Control-Return>',lambda e:save())

#     def open_notes(self):
#         notes=self.notes.get(self.book_path,[])
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('笔记'); win.geometry('360x480')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='✏ 笔记列表',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)

#         # 列表 + 详情
#         paned=tk.PanedWindow(win,orient='vertical',bg=bg,sashwidth=4,sashrelief='flat')
#         paned.pack(fill='both',expand=True,padx=4,pady=4)

#         top_f=tk.Frame(paned,bg=bg); paned.add(top_f,height=200)
#         sb2=tk.Scrollbar(top_f); sb2.pack(side='right',fill='y')
#         lb=tk.Listbox(top_f,font=('',9),relief='flat',bg=bg,fg=fg,selectbackground=sel,
#                       selectforeground=fg,borderwidth=0,highlightthickness=0,
#                       activestyle='none',yscrollcommand=sb2.set)
#         lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
#         rows=list(notes)
#         for n2 in rows: lb.insert('end',f"  第{n2['ch']+1}章  {n2['ch_title'][:16]}  {n2['time']}")

#         bot_f=tk.Frame(paned,bg=bg); paned.add(bot_f)
#         detail=tk.Text(bot_f,font=('',10),bg=bg,fg=fg,insertbackground=fg,
#                        relief='flat',padx=8,pady=6,wrap='word',state='disabled',
#                        borderwidth=0,highlightthickness=0)
#         detail.pack(fill='both',expand=True)

#         def show_detail(event=None):
#             idxs=lb.curselection()
#             if not idxs: return
#             n2=rows[idxs[0]]
#             detail.config(state='normal'); detail.delete('1.0','end')
#             if n2.get('quote'): detail.insert('end',f'引用：{n2["quote"]}\n\n','quote')
#             detail.insert('end',n2['content'])
#             detail.config(state='disabled')
#         lb.bind('<<ListboxSelect>>',show_detail)

#         bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=6,pady=4)
#         def jump():
#             idxs=lb.curselection()
#             if not idxs: return
#             win.destroy(); self.goto_chapter(rows[idxs[0]]['ch'])
#         def delete():
#             idxs=lb.curselection()
#             if not idxs: return
#             n2=rows.pop(idxs[0]); lb.delete(idxs[0])
#             self.notes[self.book_path]=[x for x in self.notes.get(self.book_path,[]) if x is not n2]
#             _jsave(NOTES_FILE,self.notes); self._update_nav()
#             detail.config(state='normal'); detail.delete('1.0','end'); detail.config(state='disabled')
#         tk.Button(bf,text='跳转章节',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=jump).pack(side='left',padx=4)
#         tk.Button(bf,text='删除笔记',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=delete).pack(side='left')
#         lb.bind('<Double-Button-1>',lambda e:jump())
#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'360x480+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 章节目录
#     # ─────────────────────────────────────────────────
#     def open_chapters(self):
#         if not self.chapters: messagebox.showinfo('提示','请先打开小说'); return
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         mark_set={m['ch'] for m in self.marks.get(self.book_path,[])}
#         note_set={n2['ch'] for n2 in self.notes.get(self.book_path,[])}
#         win=tk.Toplevel(self.root); win.title('章节目录'); win.geometry('300x500')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='📑 章节目录',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
#         sf=tk.Frame(win,bg=bg); sf.pack(fill='x',padx=6,pady=(6,2))
#         sv=tk.StringVar()
#         se=tk.Entry(sf,textvariable=sv,font=('',9),bg=bg,fg=fg,insertbackground=fg,relief='groove')
#         se.pack(fill='x',ipady=3)
#         PH='搜索章节名...'
#         se.insert(0,PH); se.config(fg='gray')
#         se.bind('<FocusIn>',lambda e:(se.delete(0,'end'),se.config(fg=fg)) if se.get()==PH else None)
#         se.bind('<FocusOut>',lambda e:(se.insert(0,PH),se.config(fg='gray')) if not se.get() else None)
#         lf=tk.Frame(win,bg=bg); lf.pack(fill='both',expand=True,padx=4,pady=4)
#         sb2=tk.Scrollbar(lf); sb2.pack(side='right',fill='y')
#         lb=tk.Listbox(lf,font=('',10),relief='flat',bg=bg,fg=fg,selectbackground=sel,
#                       selectforeground=fg,borderwidth=0,highlightthickness=0,
#                       activestyle='none',yscrollcommand=sb2.set)
#         lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
#         btn_j=tk.Button(win,text='↩ 跳转',font=('',9,'bold'),bg=bar,fg=fg,relief='flat',pady=5)
#         btn_j.pack(fill='x',padx=6,pady=4)
#         all_ch=list(self.chapters); visible=list(range(len(all_ch)))
#         def fill(indices):
#             visible.clear(); visible.extend(indices); lb.delete(0,'end')
#             for i in indices:
#                 flags=('🔖' if i in mark_set else '')+('✏' if i in note_set else '')
#                 cur='▶ ' if i==self.cur_ch else '  '
#                 lb.insert('end',f'{cur}{i+1}. {all_ch[i]["title"]}{flags}')
#         fill(range(len(all_ch)))
#         try: lb.see(self.cur_ch); lb.selection_set(self.cur_ch)
#         except: pass
#         def on_search(*_):
#             q=sv.get().strip()
#             fill(range(len(all_ch))) if q in ('',PH) else fill([i for i,c in enumerate(all_ch) if q in c['title']])
#         sv.trace_add('write',on_search)
#         def jump(e=None):
#             idxs=lb.curselection()
#             if not idxs: return
#             win.destroy(); self.goto_chapter(visible[idxs[0]])
#         btn_j.config(command=jump); lb.bind('<Double-Button-1>',jump); lb.bind('<Return>',jump)
#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'300x500+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # Toast 提示
#     # ─────────────────────────────────────────────────
#     def _toast(self,msg,ms=1500):
#         t=self._cur_theme()
#         try:
#             for w in self.root.winfo_children():
#                 if isinstance(w,tk.Label) and getattr(w,'_is_toast',False): w.destroy()
#         except: pass
#         toast=tk.Label(self.root,text=msg,font=('',8),bg=t['bar'],fg=t['fg'],
#                        padx=10,pady=4,relief='flat')
#         toast._is_toast=True
#         toast.place(relx=0.5,rely=0.06,anchor='n')
#         self.root.after(ms,lambda: (toast.winfo_exists() and toast.destroy()))

#     # ─────────────────────────────────────────────────
#     # 欢迎页
#     # ─────────────────────────────────────────────────
#     def _show_welcome(self):
#         self.txt.config(state='normal'); self.txt.delete('1.0','end')
#         self.txt.insert('1.0',(
#             '\n\n\n'
#             '        📚  摸鱼阅读器  v8\n\n'
#             '  支持：TXT  /  EPUB  /  MD\n\n'
#             '  顶部按钮：书架  目录  笔记  书签  打开\n\n'
#             '  操作：\n'
#             '    滚轮 / 拖拽右侧滚动条  章内滚动\n'
#             '    滚到章末再滚           切下一章\n'
#             '    点击左侧 28% / 右侧    切上下章\n'
#             '    ← →  切章   S/↓  翻屏\n\n'
#             '  快捷键：\n'
#             '    O        添加书签\n'
#             '    N        添加笔记\n'
#             '    F5       开始/停止朗读\n'
#             '    D+E      最小化\n'
#         ))
#         self.txt.config(state='disabled')

#     # ─────────────────────────────────────────────────
#     # 最小化
#     # ─────────────────────────────────────────────────
#     def toggle_minimize(self):
#         self._minimized=not self._minimized
#         if self._minimized:
#             self._saved_h=self.root.winfo_height()
#             for w in (self.setbar,self.sep,self.txt_frame,self.bot_area): w.pack_forget()
#             self.root.geometry(f'{self.root.winfo_width()}x30')
#         else:
#             self.root.geometry(f'{self.root.winfo_width()}x{self._saved_h}')
#             self.sep.pack(fill='x',after=self.topbar)
#             if self._settings_open: self.setbar.pack(fill='x',after=self.topbar); self._retheme_setbar()
#             self.txt_frame.pack(fill='both',expand=True)
#             self.bot_area.pack(fill='x',side='bottom')

#     def toggle_settings(self):
#         self._settings_open=not self._settings_open
#         if self._settings_open: self.setbar.pack(fill='x',after=self.topbar); self._retheme_setbar()
#         else: self.setbar.pack_forget()

#     # ─────────────────────────────────────────────────
#     # 全文搜索（Ctrl+F）
#     # ─────────────────────────────────────────────────
#     def open_search(self):
#         if not self.chapters:
#             messagebox.showinfo('提示', '请先打开小说'); return

#         t = self._cur_theme()
#         bg, fg, bar, sel = t['bg'], t['fg'], t['bar'], t['sel']

#         # 若搜索窗已存在则聚焦
#         if hasattr(self, '_search_win') and self._search_win.winfo_exists():
#             self._search_win.lift(); self._search_win.focus_force(); return

#         win = tk.Toplevel(self.root)
#         win.title('全文搜索')
#         win.geometry('480x560')
#         win.resizable(True, True)
#         win.attributes('-topmost', True)
#         win.configure(bg=bg)
#         self._search_win = win

#         # ── 顶部搜索框 ────────────────────────────────
#         top = tk.Frame(win, bg=bar); top.pack(fill='x', padx=0, pady=0)
#         tk.Label(top, text='🔍', font=('',11), bg=bar, fg=fg).pack(side='left', padx=8, pady=6)

#         sv = tk.StringVar()
#         entry = tk.Entry(top, textvariable=sv, font=('',11), bg=bg, fg=fg,
#                          insertbackground=fg, relief='flat', bd=0)
#         entry.pack(side='left', fill='x', expand=True, ipady=4)

#         # 大小写 / 正则 选项
#         var_case  = tk.BooleanVar(value=False)
#         var_regex = tk.BooleanVar(value=False)
#         tk.Checkbutton(top, text='Aa', variable=var_case, font=('',8),
#                        bg=bar, fg=fg, activebackground=bar,
#                        selectcolor=bg).pack(side='left', padx=2)
#         tk.Checkbutton(top, text='.*', variable=var_regex, font=('',8),
#                        bg=bar, fg=fg, activebackground=bar,
#                        selectcolor=bg).pack(side='left', padx=2)

#         lbl_count = tk.Label(top, text='', font=('',8), bg=bar, fg=sel)
#         lbl_count.pack(side='left', padx=6)
#         tk.Button(top, text='×', relief='flat', font=('',10),
#                   bg=bar, fg=fg, command=win.destroy).pack(side='right', padx=6)

#         sep2 = tk.Frame(win, height=1, bg=sel); sep2.pack(fill='x')

#         # ── 结果列表 ──────────────────────────────────
#         list_frame = tk.Frame(win, bg=bg); list_frame.pack(fill='both', expand=True)
#         sb2 = tk.Scrollbar(list_frame); sb2.pack(side='right', fill='y')
#         lb = tk.Listbox(list_frame, font=('',9), relief='flat', bg=bg, fg=fg,
#                         selectbackground=sel, selectforeground=fg,
#                         borderwidth=0, highlightthickness=0,
#                         activestyle='none', yscrollcommand=sb2.set)
#         lb.pack(fill='both', expand=True); sb2.config(command=lb.yview)

#         # ── 预览区 ────────────────────────────────────
#         sep3 = tk.Frame(win, height=1, bg=sel); sep3.pack(fill='x')
#         preview_frame = tk.Frame(win, bg=bg, height=130)
#         preview_frame.pack(fill='x', padx=0); preview_frame.pack_propagate(False)

#         preview = tk.Text(preview_frame, font=('',9), bg=bg, fg=fg,
#                           relief='flat', padx=12, pady=6, wrap='word',
#                           state='disabled', borderwidth=0, highlightthickness=0)
#         preview.pack(fill='both', expand=True)
#         preview.tag_config('hit',  background='#d79921', foreground='#1d2021')
#         preview.tag_config('info', foreground=sel)

#         # 底部跳转栏
#         bot_f = tk.Frame(win, bg=bar, height=30)
#         bot_f.pack(fill='x'); bot_f.pack_propagate(False)
#         lbl_loc = tk.Label(bot_f, text='', font=('',8), bg=bar, fg=fg)
#         lbl_loc.pack(side='left', padx=8, pady=4)
#         btn_jump = tk.Button(bot_f, text='↩ 跳转到此处', font=('',8,'bold'),
#                              bg=bar, fg=fg, relief='flat', padx=8,
#                              state='disabled')
#         btn_jump.pack(side='right', padx=8, pady=3)

#         # ── 搜索逻辑 ──────────────────────────────────
#         results = []   # [(ch_idx, start_in_body, end_in_body, snippet)]

#         def do_search(*_):
#             results.clear(); lb.delete(0, 'end')
#             query = sv.get().strip()
#             if not query:
#                 lbl_count.config(text=''); return

#             flags = 0 if var_case.get() else re.IGNORECASE
#             try:
#                 if var_regex.get():
#                     pat = re.compile(query, flags)
#                 else:
#                     pat = re.compile(re.escape(query), flags)
#             except re.error as e:
#                 lbl_count.config(text=f'正则错误: {e}'); return

#             CONTEXT = 40   # 匹配前后各取多少字符
#             for ci, ch in enumerate(self.chapters):
#                 for m in pat.finditer(ch['body']):
#                     s, e2 = m.start(), m.end()
#                     pre  = ch['body'][max(0, s-CONTEXT):s].replace('\n', ' ')
#                     hit  = ch['body'][s:e2]
#                     post = ch['body'][e2:min(len(ch['body']), e2+CONTEXT)].replace('\n', ' ')
#                     snippet = (pre, hit, post)
#                     results.append((ci, s, e2, snippet))

#             lbl_count.config(text=f'共 {len(results)} 处')
#             for ci, s, e2, (pre, hit, post) in results:
#                 ch_title = self.chapters[ci]['title']
#                 display  = f"  第{ci+1}章  {ch_title[:14]}…  「{hit[:20]}」"
#                 lb.insert('end', display)

#             # 清空预览
#             preview.config(state='normal'); preview.delete('1.0','end')
#             preview.config(state='disabled')
#             lbl_loc.config(text='')
#             btn_jump.config(state='disabled')

#         sv.trace_add('write', do_search)
#         var_case.trace_add('write',  do_search)
#         var_regex.trace_add('write', do_search)

#         def on_select(event=None):
#             idxs = lb.curselection()
#             if not idxs: return
#             ci, s, e2, (pre, hit, post) = results[idxs[0]]
#             ch = self.chapters[ci]

#             # 更新预览
#             preview.config(state='normal'); preview.delete('1.0','end')
#             preview.insert('end', f'第{ci+1}章  {ch["title"]}\n', 'info')
#             preview.insert('end', '…' + pre)
#             preview.insert('end', hit, 'hit')
#             preview.insert('end', post + '…')
#             preview.config(state='disabled')

#             lbl_loc.config(text=f'第{ci+1}章 · 位置 {s}')
#             btn_jump.config(state='normal',
#                             command=lambda: _jump(ci, s, e2, hit))

#         def _jump(ci, s, e2, hit):
#             # 跳转到章节，并高亮匹配文字
#             self.goto_chapter(ci)
#             win.lift()
#             # 在 txt 里找到并高亮
#             self.root.after(80, lambda: _highlight_in_txt(hit))

#         def _highlight_in_txt(hit):
#             self.txt.tag_remove('search_hit', '1.0', 'end')
#             self.txt.tag_config('search_hit', background='#d79921', foreground='#1d2021')
#             start = '1.0'
#             while True:
#                 pos = self.txt.search(hit, start, nocase=not var_case.get(), stopindex='end')
#                 if not pos: break
#                 end_pos = f'{pos}+{len(hit)}c'
#                 self.txt.tag_add('search_hit', pos, end_pos)
#                 self.txt.see(pos)
#                 start = end_pos

#         lb.bind('<<ListboxSelect>>', on_select)
#         lb.bind('<Double-Button-1>', lambda e: btn_jump.invoke())
#         lb.bind('<Return>',         lambda e: btn_jump.invoke())

#         entry.focus()
#         # 如果有选中文字，自动填入搜索框
#         try:
#             sel_text = self.txt.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
#             if sel_text and '\n' not in sel_text:
#                 sv.set(sel_text)
#         except: pass

#         rx = self.root.winfo_x() + self.root.winfo_width() + 8
#         ry = self.root.winfo_y()
#         win.geometry(f'480x560+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 章节摘要（Ctrl+M）—— 调用智谱 GLM API
#     # ─────────────────────────────────────────────────
#     def open_summary(self):
#         if not self.chapters:
#             messagebox.showinfo('提示', '请先打开小说'); return

#         # ── 把所有内部状态装进一个对象，避免闭包变量遮蔽 ────
#         class State:
#             ch_body  = self.chapters[self.cur_ch]['body']
#             ch_title = self.chapters[self.cur_ch]['title']
#             ch_idx   = self.cur_ch
#             result   = ''   # 生成的摘要文本

#         st = State()
#         t  = self._cur_theme()
#         bg, fg, bar, sel = t['bg'], t['fg'], t['bar'], t['sel']

#         dlg = tk.Toplevel(self.root)
#         dlg.title('章节摘要')
#         dlg.geometry('420x460')
#         dlg.resizable(True, True)
#         dlg.attributes('-topmost', True)
#         dlg.configure(bg=bg)

#         # 标题栏
#         hdr = tk.Frame(dlg, bg=bar, height=30)
#         hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr, text=f'✨ 摘要 — {st.ch_title[:24]}',
#                  font=('',9,'bold'), bg=bar, fg=fg).pack(side='left', padx=8, pady=5)
#         tk.Button(hdr, text='×', relief='flat', font=('',10),
#                   bg=bar, fg=fg, command=dlg.destroy).pack(side='right', padx=6)

#         # 选项行
#         opt = tk.Frame(dlg, bg=bar); opt.pack(fill='x', padx=8, pady=4)
#         tk.Label(opt, text='长度', font=('',8), bg=bar, fg=fg).pack(side='left')
#         v_len = tk.StringVar(value='标准')
#         for lbl_text in ('简短','标准','详细'):
#             tk.Radiobutton(opt, text=lbl_text, variable=v_len, value=lbl_text,
#                            font=('',8), bg=bar, fg=fg,
#                            activebackground=bar, selectcolor=bg).pack(side='left', padx=3)

#         tk.Label(opt, text='  风格', font=('',8), bg=bar, fg=fg).pack(side='left')
#         v_style = tk.StringVar(value='客观')
#         for lbl_text in ('客观','活泼','学术'):
#             tk.Radiobutton(opt, text=lbl_text, variable=v_style, value=lbl_text,
#                            font=('',8), bg=bar, fg=fg,
#                            activebackground=bar, selectcolor=bg).pack(side='left', padx=3)

#         tk.Frame(dlg, height=1, bg=sel).pack(fill='x')

#         # 文本展示区
#         out = tk.Text(dlg, font=('',10), bg=bg, fg=fg,
#                       insertbackground=fg, relief='flat',
#                       padx=14, pady=10, wrap='word',
#                       borderwidth=0, highlightthickness=0,
#                       state='disabled')
#         out.pack(fill='both', expand=True)
#         out.tag_config('dim',  foreground=sel)
#         out.tag_config('warn', foreground='#cc241d')

#         # 底部按钮行
#         bf = tk.Frame(dlg, bg=bar, height=34)
#         bf.pack(fill='x', side='bottom'); bf.pack_propagate(False)

#         b_gen  = tk.Button(bf, text='✨ 生成摘要', font=('',9,'bold'),
#                            bg=bar, fg=fg, relief='flat', padx=10)
#         b_gen.pack(side='left', padx=8, pady=4)
#         b_copy = tk.Button(bf, text='复制', font=('',8),
#                            bg=bar, fg=fg, relief='flat', padx=6, state='disabled')
#         b_copy.pack(side='left', padx=2, pady=4)
#         b_note = tk.Button(bf, text='存笔记', font=('',8),
#                            bg=bar, fg=fg, relief='flat', padx=6, state='disabled')
#         b_note.pack(side='left', padx=2, pady=4)
#         lbl_st = tk.Label(bf, text='', font=('',8), bg=bar, fg=sel)
#         lbl_st.pack(side='right', padx=8)

#         # ── 工具函数 ──────────────────────────────────
#         def show(text, tag=''):
#             out.config(state='normal')
#             out.delete('1.0', 'end')
#             if tag:
#                 out.insert('end', text, tag)
#             else:
#                 out.insert('end', text)
#             out.config(state='disabled')

#         def build_prompt():
#             length_map = {'简短':'100字以内','标准':'200字左右','详细':'400字左右'}
#             style_map  = {'客观':'客观简洁','活泼':'生动活泼，可适当使用emoji','学术':'学术严谨，条理清晰'}
#             body_clip  = st.ch_body[:4000]
#             return (
#                 f"请对以下小说章节内容做摘要，要求：\n"
#                 f"1. 长度：{length_map[v_len.get()]}\n"
#                 f"2. 风格：{style_map[v_style.get()]}\n"
#                 f"3. 包含：主要人物、核心情节、关键转折\n"
#                 f"4. 直接输出摘要内容，不要任何前缀\n\n"
#                 f"章节标题：{st.ch_title}\n\n"
#                 f"章节内容：\n{body_clip}"
#             )

#         def on_success(text):
#             st.result = text
#             show(text)
#             b_gen.config(state='normal', text='✨ 重新生成')
#             b_copy.config(state='normal')
#             b_note.config(state='normal')
#             lbl_st.config(text=f'约 {len(text)} 字')

#         def on_error(msg):
#             b_gen.config(state='normal', text='✨ 生成摘要')
#             if msg == 'NO_KEY':
#                 show(
#                     '⚠ 未找到 API Key\n\n'
#                     '请在程序同目录新建 api_key.txt，\n'
#                     '把智谱 API Key 粘贴进去保存。\n\n'
#                     '获取地址：https://open.bigmodel.cn\n'
#                     'GLM-4-Flash 对新用户有免费额度。',
#                     'warn'
#                 )
#             else:
#                 show(f'⚠ 生成失败\n\n{msg}', 'warn')

#         def do_generate():
#             b_gen.config(state='disabled', text='生成中…')
#             b_copy.config(state='disabled')
#             b_note.config(state='disabled')
#             lbl_st.config(text='')
#             show('正在调用智谱 GLM，请稍候…', 'dim')

#             # 【修复关键】必须在主线程获取 Tkinter 的变量，提前拼接好字符串
#             try:
#                 _prompt = build_prompt()
#             except Exception as e:
#                 on_error(f"构建提示词失败: {e}")
#                 return

#             # 在后台线程执行网络请求，全部用局部变量
#             def worker():
#                 import urllib.request as _req_mod
#                 import urllib.error  as _err_mod
#                 import json          as _json_mod

#                 try:
#                     _api_key = _inject_api_key()
#                     if not _api_key:
#                         dlg.after(0, lambda: on_error('NO_KEY'))
#                         return

#                     _payload = _json_mod.dumps({
#                         'model':       'glm-4-flash',
#                         'max_tokens':  1024,
#                         'temperature': 0.7,
#                         'messages':    [{'role': 'user', 'content': _prompt}],
#                     }).encode('utf-8')

#                     _request = _req_mod.Request(
#                         'https://open.bigmodel.cn/api/paas/v4/chat/completions',
#                         data    = _payload,
#                         headers = {
#                             'Content-Type':  'application/json',
#                             'Authorization': f'Bearer {_api_key}',
#                         },
#                         method  = 'POST',
#                     )
                    
#                     with _req_mod.urlopen(_request, timeout=30) as _resp:
#                         _raw     = _resp.read().decode('utf-8')
#                         _parsed  = _json_mod.loads(_raw)
#                         _summary = _parsed['choices'][0]['message']['content'].strip()
#                     dlg.after(0, lambda s=_summary: on_success(s))
                    
#                 except _err_mod.HTTPError as _he:
#                     _body = _he.read().decode('utf-8', errors='replace')
#                     try:
#                         _eobj = _json_mod.loads(_body)
#                         _emsg = _eobj.get('error', {}).get('message', _body)
#                     except Exception:
#                         _emsg = _body[:300]
#                     _code = str(_he.code)
#                     dlg.after(0, lambda c=_code, m=_emsg: on_error(f'HTTP {c}: {m}'))
#                 except Exception as _ex:
#                     _msg = str(_ex)
#                     dlg.after(0, lambda m=_msg: on_error(m))

#             threading.Thread(target=worker, daemon=True).start()

#         def do_copy():
#             if not st.result: return
#             dlg.clipboard_clear()
#             dlg.clipboard_append(st.result)
#             lbl_st.config(text='已复制！')
#             dlg.after(1500, lambda: lbl_st.config(text=f'约 {len(st.result)} 字'))

#         def do_save_note():
#             if not st.result: return
#             note_list = self.notes.setdefault(self.book_path, [])
#             note_list.append({
#                 'ch':       st.ch_idx,
#                 'ch_title': st.ch_title,
#                 'content':  f'[AI摘要]\n{st.result}',
#                 'quote':    '',
#                 'time':     datetime.datetime.now().strftime('%m-%d %H:%M'),
#             })
#             _jsave(NOTES_FILE, self.notes)
#             self._update_nav()
#             self._toast('✏ 摘要已存为笔记')
#             lbl_st.config(text='已保存为笔记')

#         b_gen.config(command=do_generate)
#         b_copy.config(command=do_copy)
#         b_note.config(command=do_save_note)

#         # 初始提示
#         _has_key = bool(_inject_api_key())
#         _key_tip = '' if _has_key else '\n\n⚠ 未检测到 api_key.txt，点击生成后会显示配置说明。'
#         show(
#             f'📖 {st.ch_title}\n\n'
#             f'本章约 {len(st.ch_body)} 字。\n'
#             f'点击「✨ 生成摘要」开始。'
#             f'{_key_tip}',
#             'dim'
#         )

#         _rx = self.root.winfo_x() + self.root.winfo_width() + 8
#         _ry = self.root.winfo_y()
#         dlg.geometry(f'420x460+{_rx}+{_ry}')

#     # ─────────────────────────────────────────────────
#     # 关闭时保存
#     # ─────────────────────────────────────────────────
#     def _on_close(self):
#         self.tts.stop()
#         self._shelf_update()
#         self.root.destroy()

#     # ─────────────────────────────────────────────────
#     # 快捷键
#     # ─────────────────────────────────────────────────
#     def _bind_keys(self):
#         r=self.root
#         r.bind('<KeyPress-s>',   lambda e: self._scroll_down())
#         r.bind('<KeyPress-S>',   lambda e: self._scroll_down())
#         r.bind('<Right>',        lambda e: self.next_chapter())
#         r.bind('<Left>',         lambda e: self.prev_chapter())
#         r.bind('<Down>',         lambda e: self._scroll_down())
#         r.bind('<Up>',           lambda e: self.txt.yview_scroll(-3,'units'))
#         r.bind('<KeyPress-o>',   lambda e: self.add_mark())
#         r.bind('<KeyPress-O>',   lambda e: self.add_mark())
#         r.bind('<KeyPress-n>',   lambda e: self.add_note())
#         r.bind('<KeyPress-N>',   lambda e: self.add_note())
#         r.bind('<F5>',           lambda e: self.toggle_tts())
#         r.bind('<Control-f>',    lambda e: self.open_search())
#         r.bind('<Control-F>',    lambda e: self.open_search())
#         r.bind('<Control-m>',    lambda e: self.open_summary())
#         r.bind('<Control-M>',    lambda e: self.open_summary())
#         r.bind('<KeyPress-d>',   self._dp)
#         r.bind('<KeyPress-D>',   self._dp)
#         r.bind('<KeyRelease-d>', self._dr)
#         r.bind('<KeyRelease-D>', self._dr)
#         r.bind('<KeyPress-e>',   self._ep)
#         r.bind('<KeyPress-E>',   self._ep)
#         r.focus_set()

#     def _dp(self,e): self._d_held=True
#     def _dr(self,e): self._d_held=False
#     def _ep(self,e):
#         if self._d_held: self.toggle_minimize()


# # ══════════════════════════════════════════════════════════════
# if __name__ == '__main__':
#     try:
#         from ctypes import windll
#         windll.shcore.SetProcessDpiAwareness(1)
#     except: pass
#     App()

# """
# 摸鱼阅读器 v8.0  —  全功能版
# 功能：
#   阅读体验：章节滚动、翻页、字号/行距/字色/背景/护眼模式、透明度、屏幕取色
#   书架管理：添加/删除/重命名书籍、显示封面/进度/上次阅读时间
#   阅读进度：自动记录、书架显示进度条
#   笔记系统：N键在当前章节创建笔记、查看/编辑/删除笔记
#   书签系统：O键快速书签、书签列表跳转删除
#   听书TTS ：F5启动/停止，支持语速调整（需系统 pyttsx3 或 espeak）
#   竖向拖拽滚动条、目录跳转、搜索

# 运行：python novel_reader.py
# 依赖：pip install pyttsx3   （TTS，可选）
#       pip install pillow     （屏幕取色，可选）
# """

# import tkinter as tk
# from tkinter import ttk, filedialog, colorchooser, messagebox, scrolledtext
# import os, re, zipfile, sys, json, copy, threading, time, datetime
# from html.parser import HTMLParser


# # ══════════════════════════════════════════════════════════════
# # HTML → 纯文本
# # ══════════════════════════════════════════════════════════════
# class _H2T(HTMLParser):
#     SKIP  = {'script','style','head','meta','link'}
#     BLOCK = {'p','div','br','h1','h2','h3','h4','h5',
#              'h6','li','tr','td','th','section','article'}
#     def __init__(self): super().__init__(); self.out, self._s = [], 0
#     def handle_starttag(self, tag, _):
#         if tag in self.SKIP:  self._s += 1
#         if tag in self.BLOCK: self.out.append('\n')
#     def handle_endtag(self, tag):
#         if tag in self.SKIP:  self._s = max(0, self._s-1)
#         if tag in self.BLOCK: self.out.append('\n')
#     def handle_data(self, d):
#         if not self._s: self.out.append(d)
#     def text(self): return re.sub(r'\n{3,}','\n\n',''.join(self.out)).strip()

# def html2text(s):
#     p = _H2T()
#     try: p.feed(s)
#     except: pass
#     return p.text()


# # ══════════════════════════════════════════════════════════════
# # EPUB
# # ══════════════════════════════════════════════════════════════
# def read_epub(path):
#     import xml.etree.ElementTree as ET
#     title = os.path.splitext(os.path.basename(path))[0]
#     body  = ''
#     try:
#         with zipfile.ZipFile(path) as z:
#             ns = z.namelist()
#             opf, odir = '', ''
#             if 'META-INF/container.xml' in ns:
#                 for el in ET.fromstring(z.read('META-INF/container.xml')).iter():
#                     if el.tag.endswith('rootfile'):
#                         opf = el.get('full-path',''); odir = opf.rsplit('/',1)[0] if '/' in opf else ''; break
#             items, spine = {}, []
#             if opf and opf in ns:
#                 root = ET.fromstring(z.read(opf))
#                 for el in root.iter():
#                     tag = el.tag.split('}')[-1]
#                     if tag == 'item':
#                         mid,href,mt = el.get('id',''),el.get('href',''),el.get('media-type','')
#                         if href and ('html' in mt or href.endswith(('.html','.xhtml','.htm'))):
#                             items[mid] = (odir+'/'+href).lstrip('/') if odir else href
#                     elif tag == 'itemref':
#                         r = el.get('idref','')
#                         if r in items: spine.append(items[r])
#                     elif tag == 'title' and el.text: title = el.text
#             if not spine:
#                 spine = sorted(f for f in ns if re.search(r'\.(html|htm|xhtml)$',f,re.I)
#                                and 'toc' not in f.lower() and 'nav' not in f.lower())
#             for href in spine:
#                 if href in ns:
#                     try: body += html2text(z.read(href).decode('utf-8','replace')) + '\n\n'
#                     except: pass
#     except Exception as e: body = f'[EPUB解析失败: {e}]'
#     return title, body.strip()


# # ══════════════════════════════════════════════════════════════
# # 章节切割
# # ══════════════════════════════════════════════════════════════
# _CH = re.compile(
#     r'^(第\s*[零一二三四五六七八九十百千万\d〇]+\s*[章节卷集回部篇][^\n]{0,40}'
#     r'|Chapter\s*\d+[^\n]{0,40}|CHAPTER\s*\d+[^\n]{0,40}|【[^\n]{1,30}】)', re.I)

# def split_chapters(text):
#     bounds = []
#     for m in re.finditer(r'^.+$', text, re.M):
#         line = m.group().strip()
#         if line and _CH.match(line): bounds.append((m.start(), line))
#     if not bounds: return [{'title':'全文','body':text}]
#     chs = []
#     for i,(pos,title) in enumerate(bounds):
#         end = bounds[i+1][0] if i+1<len(bounds) else len(text)
#         chs.append({'title':title,'body':text[pos:end]})
#     return chs


# # ══════════════════════════════════════════════════════════════
# # 数据存储
# # ══════════════════════════════════════════════════════════════
# DATA_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.moyu_data')
# os.makedirs(DATA_DIR, exist_ok=True)
# SHELF_FILE = os.path.join(DATA_DIR, 'shelf.json')
# NOTES_FILE = os.path.join(DATA_DIR, 'notes.json')
# MARKS_FILE = os.path.join(DATA_DIR, 'marks.json')

# def _jload(f):
#     try:
#         with open(f, encoding='utf-8') as fp: return json.load(fp)
#     except: return {}

# def _jsave(f, d):
#     try:
#         with open(f, 'w', encoding='utf-8') as fp: json.dump(d, fp, ensure_ascii=False, indent=2)
#     except: pass

# def _inject_api_key():
#     """
#     从程序目录的 api_key.txt 自动读取智谱 API Key。
#     用户把 Key 粘贴进 api_key.txt 即可，无需手动配置环境变量。
#     返回 key 字符串，失败返回空字符串。
#     """
#     key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_key.txt')
#     if os.path.exists(key_file):
#         try:
#             key = open(key_file, encoding='utf-8').read().strip()
#             if key:
#                 os.environ['ZHIPU_API_KEY'] = key
#                 return key
#         except: pass
#     return os.environ.get('ZHIPU_API_KEY', '')


# # ══════════════════════════════════════════════════════════════
# # TTS 引擎（可选）
# # ══════════════════════════════════════════════════════════════
# class TTS:
#     def __init__(self):
#         self._engine = None
#         self._thread = None
#         self._stop   = threading.Event()
#         self._text   = ''
#         self._rate   = 180
#         self._avail  = False
#         self._init()

#     def _init(self):
#         try:
#             import pyttsx3
#             self._engine = pyttsx3.init()
#             self._avail  = True
#         except:
#             self._avail = False

#     @property
#     def available(self): return self._avail

#     def set_rate(self, rate):
#         self._rate = int(rate)
#         if self._engine:
#             try: self._engine.setProperty('rate', self._rate)
#             except: pass

#     def speak(self, text, on_done=None):
#         if not self._avail: return
#         self.stop()
#         self._stop.clear()
#         self._text = text

#         def run():
#             try:
#                 import pyttsx3
#                 eng = pyttsx3.init()
#                 eng.setProperty('rate', self._rate)
#                 # 逐段朗读，支持中途停止
#                 paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
#                 for para in paragraphs:
#                     if self._stop.is_set(): break
#                     eng.say(para)
#                     eng.runAndWait()
#                 eng.stop()
#             except: pass
#             if on_done: on_done()

#         self._thread = threading.Thread(target=run, daemon=True)
#         self._thread.start()

#     def stop(self):
#         self._stop.set()
#         if self._engine:
#             try: self._engine.stop()
#             except: pass


# # ══════════════════════════════════════════════════════════════
# # 屏幕取色器
# # ══════════════════════════════════════════════════════════════
# def screen_color_picker(callback):
#     try: from PIL import ImageGrab
#     except ImportError:
#         c = colorchooser.askcolor(title='选择颜色')
#         if c and c[1]: callback(c[1])
#         return
#     from PIL import ImageGrab, Image, ImageTk
#     ZOOM,HALF = 10,5; CS = (HALF*2+1)*ZOOM
#     preview = tk.Toplevel(); preview.overrideredirect(True)
#     preview.attributes('-topmost',True); preview.configure(bg='#1a1a1a')
#     preview.geometry(f'{CS+4}x{CS+28}+200+200')
#     canvas = tk.Canvas(preview,width=CS,height=CS,bg='#000',highlightthickness=1,
#                        highlightbackground='#555',cursor='none')
#     canvas.pack(padx=2,pady=(2,0))
#     lbl = tk.Label(preview,text='#000000',font=('Consolas',9,'bold'),bg='#1a1a1a',fg='white',pady=1)
#     lbl.pack()
#     cur,ph,aid,done = ['#000000'],[None],[None],[False]
#     def update():
#         if done[0]: return
#         try:
#             mx,my = preview.winfo_pointerx(),preview.winfo_pointery()
#             img = ImageGrab.grab(bbox=(mx-HALF,my-HALF,mx+HALF+1,my+HALF+1))
#             zoomed = img.resize((CS,CS),Image.NEAREST); ph[0]=ImageTk.PhotoImage(zoomed)
#             canvas.delete('all'); canvas.create_image(0,0,anchor='nw',image=ph[0])
#             c2=CS//2
#             canvas.create_line(c2,0,c2,CS,fill='white',width=1)
#             canvas.create_line(0,c2,CS,c2,fill='white',width=1)
#             canvas.create_rectangle(c2-ZOOM,c2-ZOOM,c2+ZOOM,c2+ZOOM,outline='white',width=2)
#             px=img.getpixel((HALF,HALF)); hx='#{:02x}{:02x}{:02x}'.format(px[0],px[1],px[2])
#             cur[0]=hx; lbl.config(text=hx)
#             sw,sh=preview.winfo_screenwidth(),preview.winfo_screenheight()
#             ox,oy=mx+18,my+18
#             if ox+CS+10>sw: ox=mx-CS-22
#             if oy+CS+32>sh: oy=my-CS-34
#             preview.geometry(f'+{ox}+{oy}')
#         except: pass
#         aid[0]=preview.after(40,update)
#     def finish():
#         done[0]=True
#         if aid[0]:
#             try: preview.after_cancel(aid[0])
#             except: pass
#         for w in (overlay,preview):
#             try: w.destroy()
#             except: pass
#     overlay = tk.Toplevel(); overlay.overrideredirect(True)
#     overlay.attributes('-topmost',True); overlay.attributes('-alpha',0.01)
#     sw,sh=overlay.winfo_screenwidth(),overlay.winfo_screenheight()
#     overlay.geometry(f'{sw}x{sh}+0+0'); overlay.configure(bg='white',cursor='crosshair')
#     overlay.bind('<Button-1>',lambda e:(finish(),callback(cur[0])))
#     overlay.bind('<Escape>',lambda e:finish())
#     overlay.focus_force(); aid[0]=preview.after(40,update)


# # ══════════════════════════════════════════════════════════════
# # 自定义竖向滚动条
# # ══════════════════════════════════════════════════════════════
# class SmoothScrollbar:
#     W = 10
#     def __init__(self, parent, on_scroll):
#         self.on_scroll = on_scroll
#         self._lo,self._hi = 0.0,1.0
#         self._dragging = False; self._drag_start_y = 0; self._drag_start_lo = 0.0
#         self.c_bg='#ebdbb2'; self.c_track='#d5c4a1'; self.c_thumb='#b8a882'; self.c_hover='#8f7a55'
#         self.cv = tk.Canvas(parent, width=self.W, highlightthickness=0, cursor='arrow')
#         self.cv.pack(side='right', fill='y')
#         self.cv.bind('<Configure>', lambda e: self._draw())
#         self.cv.bind('<ButtonPress-1>',   self._press)
#         self.cv.bind('<B1-Motion>',       self._drag)
#         self.cv.bind('<ButtonRelease-1>', self._release)
#         self.cv.bind('<Enter>', lambda e: self._hover(True))
#         self.cv.bind('<Leave>', lambda e: self._hover(False))
#         self._hovered = False

#     def set(self, lo, hi): self._lo,self._hi = float(lo),float(hi); self._draw()

#     def set_colors(self, bg, track, thumb, thumb_hover):
#         self.c_bg=bg; self.c_track=track; self.c_thumb=thumb; self.c_hover=thumb_hover; self._draw()

#     def _draw(self):
#         cv=self.cv; W=self.W; H=cv.winfo_height()
#         if H<4: return
#         cv.delete('all'); PAD=2
#         cv.create_rectangle(0,0,W,H,fill=self.c_bg,outline='')
#         tx=W//2
#         cv.create_line(tx,PAD,tx,H-PAD,fill=self.c_track,width=W-4,capstyle='round')
#         th=max(20,int((self._hi-self._lo)*(H-2*PAD))); ty=PAD+int(self._lo*(H-2*PAD))
#         ty2=min(H-PAD,ty+th); color=self.c_hover if self._hovered else self.c_thumb
#         r=(W-4)//2; x1,x2=2,W-2; y1,y2=ty,ty2
#         if y2-y1>=2*r:
#             cv.create_rectangle(x1,y1+r,x2,y2-r,fill=color,outline='')
#             cv.create_oval(x1,y1,x2,y1+2*r,fill=color,outline='')
#             cv.create_oval(x1,y2-2*r,x2,y2,fill=color,outline='')
#         else: cv.create_oval(x1,y1,x2,y2,fill=color,outline='')

#     def _hover(self, v): self._hovered=v; self._draw()

#     def _y_to_frac(self,y):
#         H=self.cv.winfo_height(); PAD=2
#         return max(0.0,min(1.0,(y-PAD)/max(1,H-2*PAD)))

#     def _thumb_range(self):
#         H=self.cv.winfo_height(); PAD=2
#         th=max(20,int((self._hi-self._lo)*(H-2*PAD))); ty=PAD+int(self._lo*(H-2*PAD))
#         return ty,ty+th

#     def _press(self, e):
#         ty1,ty2=self._thumb_range()
#         if ty1<=e.y<=ty2:
#             self._dragging=True; self._drag_start_y=e.y; self._drag_start_lo=self._lo
#         else:
#             frac=self._y_to_frac(e.y); span=self._hi-self._lo
#             self.on_scroll(max(0.0,min(1.0-span,frac-span/2)))

#     def _drag(self, e):
#         if not self._dragging: return
#         H=self.cv.winfo_height(); PAD=2; dy=e.y-self._drag_start_y
#         delta=dy/max(1,H-2*PAD); span=self._hi-self._lo
#         target=max(0.0,min(1.0-span,self._drag_start_lo+delta))
#         self._lo=target; self._hi=target+span; self._draw(); self.on_scroll(target)

#     def _release(self, e): self._dragging=False


# # ══════════════════════════════════════════════════════════════
# # 主程序
# # ══════════════════════════════════════════════════════════════
# class App:

#     THEMES = {
#         '暖黄': dict(bg='#fdf6e3',fg='#3c3836',bar='#ebdbb2',sel='#d5c4a1',thumb='#b8a882',thumb_h='#8f7a55'),
#         '夜间': dict(bg='#1e1e2e',fg='#cdd6f4',bar='#181825',sel='#313244',thumb='#45475a',thumb_h='#6c7086'),
#         '护眼': dict(bg='#1a2f1a',fg='#a8d5a2',bar='#152315',sel='#2d5a2d',thumb='#3a6b3a',thumb_h='#57c454'),
#         '纸张': dict(bg='#f5f0e8',fg='#2c2416',bar='#ede4d0',sel='#c8b89a',thumb='#c8a882',thumb_h='#8b6045'),
#         '白底': dict(bg='#ffffff',fg='#1a1a1a',bar='#f0f0f0',sel='#dddddd',thumb='#bbbbbb',thumb_h='#888888'),
#     }

#     def __init__(self):
#         self.root = tk.Tk()
#         self.root.title('摸鱼阅读器')
#         self.root.geometry('440x600')
#         self.root.minsize(320, 400)
#         self.root.attributes('-topmost', True)

#         # 数据
#         self.shelf   = _jload(SHELF_FILE)   # {path: {title,last_ch,total_ch,last_time,read_time}}
#         self.notes   = _jload(NOTES_FILE)   # {path: [{ch,title,content,time}]}
#         self.marks   = _jload(MARKS_FILE)   # {path: [{ch,ch_title,time}]}

#         self.book_path  = ''
#         self.book_title = ''
#         self.chapters   = []
#         self.cur_ch     = 0

#         # UI 状态
#         self.theme_name     = '暖黄'
#         self.custom_bg      = None
#         self.custom_bar     = None
#         self.font_size      = 14
#         self.line_spacing   = 6
#         self.font_fam       = ('宋体' if sys.platform=='win32'
#                                else 'Songti SC' if sys.platform=='darwin'
#                                else 'Noto Serif CJK SC')
#         self._d_held        = False
#         self._minimized     = False
#         self._settings_open = False
#         self._wheel_accum   = 0
#         self._tts_playing   = False

#         self.tts = TTS()

#         self._build_ui()
#         self._apply_theme()
#         self._bind_keys()
#         self.root.protocol('WM_DELETE_WINDOW', self._on_close)
#         self.root.mainloop()

#     # ─────────────────────────────────────────────────
#     # UI 构建
#     # ─────────────────────────────────────────────────
#     def _build_ui(self):
#         r = self.root

#         # 顶部栏
#         self.topbar = tk.Frame(r, height=30)
#         self.topbar.pack(fill='x')
#         self.topbar.pack_propagate(False)

#         dots = tk.Frame(self.topbar)
#         dots.pack(side='left', padx=6, pady=5)
#         self._dot(dots, '#ff5f57', self.toggle_minimize)
#         self._dot(dots, '#ffbd2e', self.toggle_settings)
#         self._dot(dots, '#28ca41', self.open_file)

#         self.lbl_title = tk.Label(self.topbar, text='摸鱼阅读器', font=('',9))
#         self.lbl_title.pack(side='left', fill='x', expand=True)

#         rbf = tk.Frame(self.topbar); rbf.pack(side='right', padx=2)
#         self._tbtn(rbf, '书架', self.open_shelf)
#         self._tbtn(rbf, '目录', self.open_chapters)
#         self._tbtn(rbf, '搜索', self.open_search)
#         self._tbtn(rbf, '摘要', self.open_summary)
#         self._tbtn(rbf, '笔记', self.open_notes)
#         self._tbtn(rbf, '书签', self.open_marks)
#         self._tbtn(rbf, '打开', self.open_file)
#         self._tbtn(rbf, '×',   r.destroy)

#         for w in (self.topbar, self.lbl_title):
#             w.bind('<ButtonPress-1>', self._drag_start)
#             w.bind('<B1-Motion>',     self._drag_move)

#         # 设置栏
#         self.setbar = tk.Frame(r)
#         self._build_setbar()

#         # 分隔线
#         self.sep = tk.Frame(r, height=1)
#         self.sep.pack(fill='x')

#         # 文本区
#         self.txt_frame = tk.Frame(r)
#         self.txt_frame.pack(fill='both', expand=True)

#         self.vsb = SmoothScrollbar(self.txt_frame,
#                                    on_scroll=lambda f: self.txt.yview_moveto(f))

#         self.txt = tk.Text(
#             self.txt_frame, wrap='word',
#             relief='flat', padx=16, pady=10,
#             state='disabled', cursor='arrow',
#             font=(self.font_fam, self.font_size),
#             borderwidth=0, highlightthickness=0,
#             spacing1=self.line_spacing,
#             spacing2=self.line_spacing//2,
#             spacing3=self.line_spacing,
#             yscrollcommand=self._on_yscroll,
#         )
#         self.txt.pack(side='left', fill='both', expand=True)
#         self.txt.bind('<Button-1>',   self._on_click)
#         self.txt.bind('<MouseWheel>', self._on_wheel)
#         self.txt.bind('<Button-4>',   self._on_wheel)
#         self.txt.bind('<Button-5>',   self._on_wheel)
#         self._show_welcome()

#         # 底部
#         self.bot_area = tk.Frame(r)
#         self.bot_area.pack(fill='x', side='bottom')

#         self.botbar = tk.Frame(self.bot_area, height=28)
#         self.botbar.pack(fill='x')
#         self.botbar.pack_propagate(False)

#         self.btn_prev = tk.Button(self.botbar, text='◀', font=('',9),
#                                   relief='flat', padx=4, command=self.prev_chapter)
#         self.btn_prev.pack(side='left', padx=4, pady=3)

#         self.lbl_prog = tk.Label(self.botbar, text='', font=('',8))
#         self.lbl_prog.pack(side='left', expand=True)

#         self.btn_tts = tk.Button(self.botbar, text='🔊', font=('',9),
#                                  relief='flat', padx=3, command=self.toggle_tts)
#         self.btn_tts.pack(side='right', padx=2, pady=3)

#         self.btn_note = tk.Button(self.botbar, text='✏', font=('',9),
#                                   relief='flat', padx=3, command=self.add_note)
#         self.btn_note.pack(side='right', padx=2, pady=3)

#         self.btn_mark = tk.Button(self.botbar, text='🔖', font=('',9),
#                                   relief='flat', padx=2, command=self.add_mark)
#         self.btn_mark.pack(side='right', padx=2, pady=3)

#         self.btn_next = tk.Button(self.botbar, text='▶', font=('',9),
#                                   relief='flat', padx=4, command=self.next_chapter)
#         self.btn_next.pack(side='right', padx=4, pady=3)

#     def _tbtn(self, parent, text, cmd):
#         tk.Button(parent, text=text, font=('',8), relief='flat',
#                   padx=3, command=cmd).pack(side='left', padx=1)

#     def _dot(self, p, color, cmd):
#         lb = tk.Label(p, text='⬤', fg=color, font=('',12), cursor='hand2')
#         lb.pack(side='left', padx=2)
#         lb.bind('<Button-1>', lambda e: cmd())

#     # ─────────────────────────────────────────────────
#     # 设置栏
#     # ─────────────────────────────────────────────────
#     def _build_setbar(self):
#         def row(): f=tk.Frame(self.setbar); f.pack(fill='x',padx=8,pady=2); return f

#         r1 = row()
#         tk.Label(r1,text='字号',font=('',8)).pack(side='left')
#         self.sl_font = tk.Scale(r1,from_=10,to=32,orient='horizontal',length=70,
#                                 showvalue=True,font=('',7),command=self._on_font_size)
#         self.sl_font.set(self.font_size); self.sl_font.pack(side='left',padx=2)
#         tk.Label(r1,text='行距',font=('',8)).pack(side='left',padx=(8,0))
#         self.sl_spacing = tk.Scale(r1,from_=0,to=24,orient='horizontal',length=70,
#                                    showvalue=True,font=('',7),command=self._on_spacing)
#         self.sl_spacing.set(self.line_spacing); self.sl_spacing.pack(side='left',padx=2)

#         r2 = row()
#         tk.Label(r2,text='透明',font=('',8)).pack(side='left')
#         self.sl_alpha = tk.Scale(r2,from_=20,to=100,orient='horizontal',length=80,
#                                  showvalue=True,font=('',7),
#                                  command=lambda v: self.root.attributes('-alpha',int(v)/100))
#         self.sl_alpha.set(100); self.sl_alpha.pack(side='left',padx=2)
#         # TTS 语速
#         tk.Label(r2,text='语速',font=('',8)).pack(side='left',padx=(8,0))
#         self.sl_tts_rate = tk.Scale(r2,from_=80,to=300,orient='horizontal',length=70,
#                                     showvalue=True,font=('',7),
#                                     command=lambda v: self.tts.set_rate(int(v)))
#         self.sl_tts_rate.set(180); self.sl_tts_rate.pack(side='left',padx=2)

#         r3 = row()
#         tk.Label(r3,text='字色',font=('',8)).pack(side='left')
#         self.btn_fg_color = tk.Button(r3,text='  ',relief='groove',width=2,
#                                       font=('',8),command=self._pick_fg)
#         self.btn_fg_color.pack(side='left',padx=2)
#         tk.Label(r3,text='背景',font=('',8)).pack(side='left',padx=(6,0))
#         self.btn_bg_color = tk.Button(r3,text='  ',relief='groove',width=2,
#                                       font=('',8),command=self._pick_bg)
#         self.btn_bg_color.pack(side='left',padx=2)
#         tk.Button(r3,text='🎨取色',font=('',8),relief='flat',padx=4,
#                   command=self._screen_pick).pack(side='left',padx=4)
#         tk.Button(r3,text='重置',font=('',8),relief='flat',padx=4,
#                   command=self._reset_colors).pack(side='left',padx=2)

#         r4 = row()
#         tk.Label(r4,text='主题',font=('',8)).pack(side='left')
#         self.var_theme = tk.StringVar(value=self.theme_name)
#         cb = ttk.Combobox(r4,textvariable=self.var_theme,
#                           values=list(self.THEMES.keys()),width=7,font=('',8),state='readonly')
#         cb.pack(side='left',padx=4); cb.bind('<<ComboboxSelected>>',self._on_theme)
#         # 快速护眼切换
#         tk.Button(r4,text='☘护眼',font=('',8),relief='flat',padx=4,
#                   command=lambda: (self.var_theme.set('护眼'),self._on_theme())).pack(side='left',padx=2)
#         tk.Button(r4,text='🌙夜间',font=('',8),relief='flat',padx=4,
#                   command=lambda: (self.var_theme.set('夜间'),self._on_theme())).pack(side='left',padx=2)

#     # ─────────────────────────────────────────────────
#     # 颜色
#     # ─────────────────────────────────────────────────
#     def _pick_fg(self):
#         t=self._cur_theme(); c=colorchooser.askcolor(color=t['fg'],title='字体颜色')
#         if c and c[1]: self.THEMES[self.theme_name]['fg']=c[1]; self.txt.config(fg=c[1]); self.btn_fg_color.config(bg=c[1])

#     def _pick_bg(self):
#         c=colorchooser.askcolor(color=self._cur_theme()['bg'],title='背景颜色')
#         if c and c[1]: self._apply_custom_bg(c[1])

#     def _screen_pick(self):
#         alpha=self.sl_alpha.get()/100; self.root.attributes('-alpha',0.0)
#         def on(hx): self.root.after(100,lambda:self.root.attributes('-alpha',alpha)); self._apply_custom_bg(hx)
#         self.root.after(120, lambda: screen_color_picker(on))

#     def _apply_custom_bg(self,hx):
#         self.custom_bg=hx; self.custom_bar=self._darken(hx,0.88); self._apply_theme()
#         try: self.btn_bg_color.config(bg=hx)
#         except: pass

#     def _reset_colors(self): self.custom_bg=self.custom_bar=None; self._apply_theme()
#     def _darken(self,hx,f=0.88):
#         h=hx.lstrip('#')
#         return '#{:02x}{:02x}{:02x}'.format(int(int(h[0:2],16)*f),int(int(h[2:4],16)*f),int(int(h[4:6],16)*f))

#     def _cur_theme(self):
#         t=copy.copy(self.THEMES[self.theme_name])
#         if self.custom_bg:  t['bg']=self.custom_bg
#         if self.custom_bar: t['bar']=self.custom_bar
#         return t

#     def _on_theme(self, e=None):
#         self.theme_name=self.var_theme.get(); self.custom_bg=self.custom_bar=None; self._apply_theme()

#     def _apply_theme(self):
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         self.root.configure(bg=bar)
#         self._cf(self.topbar,bar,fg); self._cf(self.botbar,bar,fg); self._cf(self.bot_area,bar,fg)
#         self.sep.config(bg=sel); self.txt_frame.config(bg=bg)
#         self.vsb.cv.config(bg=bg)
#         self.vsb.set_colors(bg=bg,track=sel,thumb=t.get('thumb',sel),thumb_hover=t.get('thumb_h',fg))
#         self.txt.config(bg=bg,fg=fg,insertbackground=fg,selectbackground=sel)
#         self.lbl_prog.config(bg=bar,fg=fg)
#         for b in (self.btn_prev,self.btn_next,self.btn_mark,self.btn_note,self.btn_tts):
#             b.config(bg=bar,fg=fg,activebackground=sel)
#         self._retheme_setbar()
#         try:
#             if self.custom_bg: self.btn_bg_color.config(bg=self.custom_bg)
#         except: pass

#     def _cf(self,fr,bg,fg):
#         try: fr.config(bg=bg)
#         except: pass
#         for w in fr.winfo_children():
#             try: w.config(bg=bg,fg=fg,activebackground=bg)
#             except: pass
#             for w2 in w.winfo_children():
#                 try: w2.config(bg=bg,fg=fg,activebackground=bg)
#                 except: pass

#     def _retheme_setbar(self):
#         t=self._cur_theme(); bg,fg,sel=t['bar'],t['fg'],t['sel']
#         self._cf(self.setbar,bg,fg)
#         for sl in (self.sl_font,self.sl_alpha,self.sl_spacing,self.sl_tts_rate):
#             try: sl.config(bg=bg,fg=fg,troughcolor=sel,activebackground=sel)
#             except: pass
#         try: self.btn_fg_color.config(bg=fg)
#         except: pass

#     # ─────────────────────────────────────────────────
#     # 字号 / 行距
#     # ─────────────────────────────────────────────────
#     def _on_font_size(self,val):
#         self.font_size=int(float(val)); self.txt.config(font=(self.font_fam,self.font_size))

#     def _on_spacing(self,val):
#         sp=int(float(val)); self.line_spacing=sp
#         self.txt.config(spacing1=sp,spacing2=sp//2,spacing3=sp)

#     # ─────────────────────────────────────────────────
#     # 拖动窗口
#     # ─────────────────────────────────────────────────
#     def _drag_start(self,e): self._dx=e.x_root-self.root.winfo_x(); self._dy=e.y_root-self.root.winfo_y()
#     def _drag_move(self,e):  self.root.geometry(f'+{e.x_root-self._dx}+{e.y_root-self._dy}')

#     # ─────────────────────────────────────────────────
#     # 打开文件
#     # ─────────────────────────────────────────────────
#     def open_file(self, path=None):
#         if path is None:
#             path = filedialog.askopenfilename(
#                 title='打开小说',
#                 filetypes=[('小说文件','*.txt *.epub *.md'),('所有文件','*.*')])
#         if not path: return
#         ext = os.path.splitext(path)[1].lower()
#         if ext == '.epub': title,text = read_epub(path)
#         else:
#             title = os.path.splitext(os.path.basename(path))[0]
#             try:
#                 with open(path,encoding='utf-8',errors='replace') as f: text=f.read()
#             except Exception as e: messagebox.showerror('错误',str(e)); return
#         self.book_path=path; self.book_title=title
#         self.lbl_title.config(text=f'  {title}'); self.root.title(f'摸鱼阅读器 — {title}')
#         self._load(text)

#     def _load(self,text):
#         self.chapters = split_chapters(text)
#         # 恢复上次阅读位置
#         si = self.shelf.get(self.book_path,{})
#         self.cur_ch = max(0,min(si.get('last_ch',0),len(self.chapters)-1))
#         # 更新书架
#         self._shelf_update()
#         self._render_chapter()

#     # ─────────────────────────────────────────────────
#     # 书架管理
#     # ─────────────────────────────────────────────────
#     def _shelf_update(self):
#         p = self.book_path
#         prev = self.shelf.get(p,{})
#         self.shelf[p] = {
#             'title':      self.book_title,
#             'path':       p,
#             'last_ch':    self.cur_ch,
#             'total_ch':   len(self.chapters),
#             'last_time':  datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
#             'added_time': prev.get('added_time', datetime.datetime.now().strftime('%Y-%m-%d')),
#         }
#         _jsave(SHELF_FILE, self.shelf)

#     def open_shelf(self):
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('书架'); win.geometry('380x460')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)

#         hdr=tk.Frame(win,bg=bar,height=30); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='📚 书架',font=('',10,'bold'),bg=bar,fg=fg).pack(side='left',padx=10,pady=5)
#         tk.Button(hdr,text='+添加',font=('',8),relief='flat',bg=bar,fg=fg,
#                   command=lambda:self._shelf_add(win)).pack(side='right',padx=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,
#                   command=win.destroy).pack(side='right',padx=4)

#         # 书籍列表
#         frame=tk.Frame(win,bg=bg); frame.pack(fill='both',expand=True,padx=6,pady=6)
#         sb2=tk.Scrollbar(frame); sb2.pack(side='right',fill='y')
#         canvas=tk.Canvas(frame,bg=bg,highlightthickness=0,yscrollcommand=sb2.set)
#         canvas.pack(fill='both',expand=True); sb2.config(command=canvas.yview)
#         inner=tk.Frame(canvas,bg=bg); canvas.create_window((0,0),window=inner,anchor='nw')

#         def refresh():
#             for w in inner.winfo_children(): w.destroy()
#             if not self.shelf:
#                 tk.Label(inner,text='书架空空，快去添加书吧',font=('',10),bg=bg,fg=sel).pack(pady=30)
#             for path,info in sorted(self.shelf.items(),key=lambda x:x[1].get('last_time',''),reverse=True):
#                 self._shelf_card(inner,path,info,bg,fg,bar,sel,win,refresh)
#             inner.update_idletasks()
#             canvas.config(scrollregion=canvas.bbox('all'))
#         refresh()

#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'380x460+{rx}+{ry}')

#     def _shelf_card(self,parent,path,info,bg,fg,bar,sel,shelf_win,refresh):
#         card=tk.Frame(parent,bg=bar,relief='flat',bd=0)
#         card.pack(fill='x',padx=4,pady=3)
#         # 封面色块
#         colors=['#8f3f71','#458588','#d79921','#689d6a','#cc241d']
#         ccolor=colors[hash(path)%len(colors)]
#         cover=tk.Frame(card,bg=ccolor,width=36,height=50); cover.pack(side='left',padx=6,pady=6); cover.pack_propagate(False)
#         tk.Label(cover,text='📖',font=('',14),bg=ccolor).pack(expand=True)
#         # 信息
#         info_f=tk.Frame(card,bg=bar); info_f.pack(side='left',fill='both',expand=True,pady=4)
#         tk.Label(info_f,text=info.get('title','未知'),font=('',9,'bold'),bg=bar,fg=fg,anchor='w').pack(fill='x')
#         lc=info.get('last_ch',0); tc=info.get('total_ch',1)
#         pct=int(lc/max(1,tc-1)*100) if tc>1 else 0
#         tk.Label(info_f,text=f'第{lc+1}/{tc}章  {pct}%',font=('',8),bg=bar,fg=sel,anchor='w').pack(fill='x')
#         # 进度条
#         pb_f=tk.Frame(info_f,bg=bar,height=4); pb_f.pack(fill='x',pady=2); pb_f.pack_propagate(False)
#         pb_done=tk.Frame(pb_f,bg=ccolor,height=4); pb_done.place(x=0,y=0,relwidth=pct/100,relheight=1)
#         tk.Frame(pb_f,bg=sel,height=4).place(x=0,y=0,relwidth=1,relheight=1)
#         pb_done.lift()
#         tk.Label(info_f,text=f'上次：{info.get("last_time","")}',font=('',7),bg=bar,fg=sel,anchor='w').pack(fill='x')
#         # 按钮
#         btn_f=tk.Frame(card,bg=bar); btn_f.pack(side='right',padx=6,pady=4)
#         def open_it(p=path):
#             shelf_win.destroy(); self.open_file(p)
#         def del_it(p=path):
#             if messagebox.askyesno('删除','从书架移除此书？',parent=shelf_win):
#                 del self.shelf[p]; _jsave(SHELF_FILE,self.shelf); refresh()
#         tk.Button(btn_f,text='阅读',font=('',8),relief='flat',bg=ccolor,fg='white',
#                   padx=6,command=open_it).pack(pady=2)
#         tk.Button(btn_f,text='移除',font=('',7),relief='flat',bg=bar,fg=sel,
#                   padx=4,command=del_it).pack(pady=2)

#     def _shelf_add(self, shelf_win):
#         path=filedialog.askopenfilename(title='选择书籍',
#             filetypes=[('小说文件','*.txt *.epub *.md'),('所有文件','*.*')])
#         if not path: return
#         if path not in self.shelf:
#             title=os.path.splitext(os.path.basename(path))[0]
#             self.shelf[path]={'title':title,'path':path,'last_ch':0,'total_ch':0,
#                               'last_time':'','added_time':datetime.datetime.now().strftime('%Y-%m-%d')}
#             _jsave(SHELF_FILE,self.shelf)
#         shelf_win.destroy(); self.open_shelf()

#     # ─────────────────────────────────────────────────
#     # 渲染章节
#     # ─────────────────────────────────────────────────
#     def _render_chapter(self, scroll_to_top=True):
#         if not self.chapters: return
#         self.cur_ch=max(0,min(self.cur_ch,len(self.chapters)-1))
#         ch=self.chapters[self.cur_ch]
#         self.txt.config(state='normal'); self.txt.delete('1.0','end')
#         self.txt.insert('1.0', ch['body']); self.txt.config(state='disabled')
#         if scroll_to_top: self.txt.yview_moveto(0.0)
#         self._update_nav(); self._wheel_accum=0
#         self._shelf_update()

#     def _update_nav(self):
#         n=len(self.chapters); idx=self.cur_ch+1
#         # 有无书签/笔记标记
#         m_chs={m['ch'] for m in self.marks.get(self.book_path,[])}
#         n_chs={n2['ch'] for n2 in self.notes.get(self.book_path,[])}
#         flags=('🔖' if self.cur_ch in m_chs else '')+('✏' if self.cur_ch in n_chs else '')
#         self.lbl_prog.config(text=f'{flags}  第{idx}/{n}章')
#         self.btn_prev.config(state='normal' if self.cur_ch>0   else 'disabled')
#         self.btn_next.config(state='normal' if self.cur_ch<n-1 else 'disabled')

#     def _on_yscroll(self,lo,hi): self.vsb.set(lo,hi)

#     # ─────────────────────────────────────────────────
#     # 翻章
#     # ─────────────────────────────────────────────────
#     def next_chapter(self):
#         if self.chapters and self.cur_ch<len(self.chapters)-1:
#             self.cur_ch+=1; self._render_chapter()

#     def prev_chapter(self):
#         if self.chapters and self.cur_ch>0:
#             self.cur_ch-=1; self._render_chapter()

#     def goto_chapter(self,idx):
#         if not self.chapters: return
#         self.cur_ch=max(0,min(idx,len(self.chapters)-1)); self._render_chapter()

#     def _on_click(self,e):
#         w=self.txt.winfo_width()
#         if   e.x<w*0.28: self.prev_chapter()
#         elif e.x>w*0.72: self.next_chapter()

#     def _on_wheel(self,e):
#         delta=1 if e.num==4 else (-1 if e.num==5 else (1 if e.delta>0 else -1))
#         top,bot=self.txt.yview()
#         if delta<0:
#             if bot>=0.999:
#                 self._wheel_accum-=1
#                 if self._wheel_accum<=-3: self.next_chapter(); return
#             else: self._wheel_accum=0; self.txt.yview_scroll(3,'units')
#         else:
#             if top<=0.001:
#                 self._wheel_accum+=1
#                 if self._wheel_accum>=3:
#                     self.prev_chapter(); self.root.after(30,lambda:self.txt.yview_moveto(1.0)); return
#             else: self._wheel_accum=0; self.txt.yview_scroll(-3,'units')

#     def _scroll_down(self):
#         _,bot=self.txt.yview()
#         if bot>=0.999: self.next_chapter()
#         else: self.txt.yview_scroll(1,'pages')

#     # ─────────────────────────────────────────────────
#     # TTS 听书
#     # ─────────────────────────────────────────────────
#     def toggle_tts(self):
#         if not self.tts.available:
#             messagebox.showinfo('提示','请先安装 pyttsx3：\npip install pyttsx3'); return
#         if self._tts_playing:
#             self.tts.stop(); self._tts_playing=False
#             self.btn_tts.config(text='🔊')
#             self._toast('⏹ 已停止朗读')
#         else:
#             if not self.chapters: return
#             ch=self.chapters[self.cur_ch]
#             self._tts_playing=True; self.btn_tts.config(text='⏸')
#             self._toast('▶ 开始朗读…')
#             def done(): self.root.after(0,self._tts_done)
#             self.tts.speak(ch['body'],on_done=done)

#     def _tts_done(self):
#         self._tts_playing=False; self.btn_tts.config(text='🔊')

#     # ─────────────────────────────────────────────────
#     # 书签（O 键）
#     # ─────────────────────────────────────────────────
#     def add_mark(self):
#         if not self.book_path: messagebox.showinfo('提示','请先打开书'); return
#         marks=self.marks.setdefault(self.book_path,[])
#         ch=self.chapters[self.cur_ch]; now=datetime.datetime.now().strftime('%m-%d %H:%M')
#         existing=next((m for m in marks if m['ch']==self.cur_ch),None)
#         entry={'ch':self.cur_ch,'ch_title':ch['title'],'time':now}
#         if existing: existing.update(entry); self._toast('🔖 书签已更新')
#         else: marks.append(entry); self._toast(f'🔖 书签已添加  第{self.cur_ch+1}章')
#         _jsave(MARKS_FILE,self.marks); self._update_nav()

#     def open_marks(self):
#         marks=self.marks.get(self.book_path,[])
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('书签'); win.geometry('300x360')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='🔖 书签列表',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
#         lf=tk.Frame(win,bg=bg); lf.pack(fill='both',expand=True,padx=4,pady=4)
#         sb2=tk.Scrollbar(lf); sb2.pack(side='right',fill='y')
#         lb=tk.Listbox(lf,font=('',10),relief='flat',bg=bg,fg=fg,selectbackground=sel,
#                       selectforeground=fg,borderwidth=0,highlightthickness=0,
#                       activestyle='none',yscrollcommand=sb2.set)
#         lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
#         rows=list(marks)
#         for m in rows: lb.insert('end',f"  🏴 第{m['ch']+1}章  {m['ch_title']}  {m['time']}")
#         bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=6,pady=4)
#         def jump():
#             idxs=lb.curselection()
#             if not idxs: return
#             win.destroy(); self.goto_chapter(rows[idxs[0]]['ch'])
#         def delete():
#             idxs=lb.curselection()
#             if not idxs: return
#             m=rows.pop(idxs[0]); lb.delete(idxs[0])
#             self.marks[self.book_path]=[x for x in self.marks.get(self.book_path,[]) if x is not m]
#             _jsave(MARKS_FILE,self.marks); self._update_nav()
#         tk.Button(bf,text='跳转',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=jump).pack(side='left',padx=4)
#         tk.Button(bf,text='删除',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=delete).pack(side='left')
#         lb.bind('<Double-Button-1>',lambda e:jump())
#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'300x360+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 笔记（N 键）
#     # ─────────────────────────────────────────────────
#     def add_note(self):
#         if not self.book_path: messagebox.showinfo('提示','请先打开书'); return
#         ch=self.chapters[self.cur_ch]
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('添加笔记'); win.geometry('340x260')
#         win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text=f'✏ 笔记 — {ch["title"][:20]}',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
#         # 选中文字自动填入
#         sel_text=''
#         try: sel_text=self.txt.get(tk.SEL_FIRST,tk.SEL_LAST)
#         except: pass
#         if sel_text:
#             tk.Label(win,text='引用文字：',font=('',8),bg=bg,fg=fg).pack(anchor='w',padx=8,pady=(6,0))
#             ref=tk.Label(win,text=sel_text[:80]+'…' if len(sel_text)>80 else sel_text,
#                         font=('',8,'italic'),bg=sel,fg=fg,wraplength=300,anchor='w',justify='left')
#             ref.pack(fill='x',padx=8,pady=2)
#         tk.Label(win,text='笔记内容：',font=('',8),bg=bg,fg=fg).pack(anchor='w',padx=8,pady=(6,0))
#         ta=tk.Text(win,height=6,font=('',10),bg=bg,fg=fg,insertbackground=fg,
#                    relief='flat',padx=8,pady=4,wrap='word',borderwidth=1,highlightthickness=1,
#                    highlightbackground=sel,highlightcolor=fg)
#         ta.pack(fill='both',expand=True,padx=8,pady=4); ta.focus()
#         def save():
#             content=ta.get('1.0','end').strip()
#             if not content: win.destroy(); return
#             notes=self.notes.setdefault(self.book_path,[])
#             now=datetime.datetime.now().strftime('%m-%d %H:%M')
#             notes.append({'ch':self.cur_ch,'ch_title':ch['title'],'content':content,
#                           'quote':sel_text,'time':now})
#             _jsave(NOTES_FILE,self.notes); self._update_nav(); win.destroy()
#             self._toast('✏ 笔记已保存')
#         bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=8,pady=4)
#         tk.Button(bf,text='保存笔记',font=('',9,'bold'),bg=bar,fg=fg,relief='flat',
#                   padx=10,command=save).pack(side='right',padx=4)
#         win.bind('<Control-Return>',lambda e:save())

#     def open_notes(self):
#         notes=self.notes.get(self.book_path,[])
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('笔记'); win.geometry('360x480')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='✏ 笔记列表',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)

#         # 列表 + 详情
#         paned=tk.PanedWindow(win,orient='vertical',bg=bg,sashwidth=4,sashrelief='flat')
#         paned.pack(fill='both',expand=True,padx=4,pady=4)

#         top_f=tk.Frame(paned,bg=bg); paned.add(top_f,height=200)
#         sb2=tk.Scrollbar(top_f); sb2.pack(side='right',fill='y')
#         lb=tk.Listbox(top_f,font=('',9),relief='flat',bg=bg,fg=fg,selectbackground=sel,
#                       selectforeground=fg,borderwidth=0,highlightthickness=0,
#                       activestyle='none',yscrollcommand=sb2.set)
#         lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
#         rows=list(notes)
#         for n2 in rows: lb.insert('end',f"  第{n2['ch']+1}章  {n2['ch_title'][:16]}  {n2['time']}")

#         bot_f=tk.Frame(paned,bg=bg); paned.add(bot_f)
#         detail=tk.Text(bot_f,font=('',10),bg=bg,fg=fg,insertbackground=fg,
#                        relief='flat',padx=8,pady=6,wrap='word',state='disabled',
#                        borderwidth=0,highlightthickness=0)
#         detail.pack(fill='both',expand=True)

#         def show_detail(event=None):
#             idxs=lb.curselection()
#             if not idxs: return
#             n2=rows[idxs[0]]
#             detail.config(state='normal'); detail.delete('1.0','end')
#             if n2.get('quote'): detail.insert('end',f'引用：{n2["quote"]}\n\n','quote')
#             detail.insert('end',n2['content'])
#             detail.config(state='disabled')
#         lb.bind('<<ListboxSelect>>',show_detail)

#         bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=6,pady=4)
#         def jump():
#             idxs=lb.curselection()
#             if not idxs: return
#             win.destroy(); self.goto_chapter(rows[idxs[0]]['ch'])
#         def delete():
#             idxs=lb.curselection()
#             if not idxs: return
#             n2=rows.pop(idxs[0]); lb.delete(idxs[0])
#             self.notes[self.book_path]=[x for x in self.notes.get(self.book_path,[]) if x is not n2]
#             _jsave(NOTES_FILE,self.notes); self._update_nav()
#             detail.config(state='normal'); detail.delete('1.0','end'); detail.config(state='disabled')
#         tk.Button(bf,text='跳转章节',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=jump).pack(side='left',padx=4)
#         tk.Button(bf,text='删除笔记',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=delete).pack(side='left')
#         lb.bind('<Double-Button-1>',lambda e:jump())
#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'360x480+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 章节目录
#     # ─────────────────────────────────────────────────
#     def open_chapters(self):
#         if not self.chapters: messagebox.showinfo('提示','请先打开小说'); return
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         mark_set={m['ch'] for m in self.marks.get(self.book_path,[])}
#         note_set={n2['ch'] for n2 in self.notes.get(self.book_path,[])}
#         win=tk.Toplevel(self.root); win.title('章节目录'); win.geometry('300x500')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='📑 章节目录',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
#         sf=tk.Frame(win,bg=bg); sf.pack(fill='x',padx=6,pady=(6,2))
#         sv=tk.StringVar()
#         se=tk.Entry(sf,textvariable=sv,font=('',9),bg=bg,fg=fg,insertbackground=fg,relief='groove')
#         se.pack(fill='x',ipady=3)
#         PH='搜索章节名...'
#         se.insert(0,PH); se.config(fg='gray')
#         se.bind('<FocusIn>',lambda e:(se.delete(0,'end'),se.config(fg=fg)) if se.get()==PH else None)
#         se.bind('<FocusOut>',lambda e:(se.insert(0,PH),se.config(fg='gray')) if not se.get() else None)
#         lf=tk.Frame(win,bg=bg); lf.pack(fill='both',expand=True,padx=4,pady=4)
#         sb2=tk.Scrollbar(lf); sb2.pack(side='right',fill='y')
#         lb=tk.Listbox(lf,font=('',10),relief='flat',bg=bg,fg=fg,selectbackground=sel,
#                       selectforeground=fg,borderwidth=0,highlightthickness=0,
#                       activestyle='none',yscrollcommand=sb2.set)
#         lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
#         btn_j=tk.Button(win,text='↩ 跳转',font=('',9,'bold'),bg=bar,fg=fg,relief='flat',pady=5)
#         btn_j.pack(fill='x',padx=6,pady=4)
#         all_ch=list(self.chapters); visible=list(range(len(all_ch)))
#         def fill(indices):
#             visible.clear(); visible.extend(indices); lb.delete(0,'end')
#             for i in indices:
#                 flags=('🔖' if i in mark_set else '')+('✏' if i in note_set else '')
#                 cur='▶ ' if i==self.cur_ch else '  '
#                 lb.insert('end',f'{cur}{i+1}. {all_ch[i]["title"]}{flags}')
#         fill(range(len(all_ch)))
#         try: lb.see(self.cur_ch); lb.selection_set(self.cur_ch)
#         except: pass
#         def on_search(*_):
#             q=sv.get().strip()
#             fill(range(len(all_ch))) if q in ('',PH) else fill([i for i,c in enumerate(all_ch) if q in c['title']])
#         sv.trace_add('write',on_search)
#         def jump(e=None):
#             idxs=lb.curselection()
#             if not idxs: return
#             win.destroy(); self.goto_chapter(visible[idxs[0]])
#         btn_j.config(command=jump); lb.bind('<Double-Button-1>',jump); lb.bind('<Return>',jump)
#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'300x500+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # Toast 提示
#     # ─────────────────────────────────────────────────
#     def _toast(self,msg,ms=1500):
#         t=self._cur_theme()
#         try:
#             for w in self.root.winfo_children():
#                 if isinstance(w,tk.Label) and getattr(w,'_is_toast',False): w.destroy()
#         except: pass
#         toast=tk.Label(self.root,text=msg,font=('',8),bg=t['bar'],fg=t['fg'],
#                        padx=10,pady=4,relief='flat')
#         toast._is_toast=True
#         toast.place(relx=0.5,rely=0.06,anchor='n')
#         self.root.after(ms,lambda: (toast.winfo_exists() and toast.destroy()))

#     # ─────────────────────────────────────────────────
#     # 欢迎页
#     # ─────────────────────────────────────────────────
#     def _show_welcome(self):
#         self.txt.config(state='normal'); self.txt.delete('1.0','end')
#         self.txt.insert('1.0',(
#             '\n\n\n'
#             '        📚  摸鱼阅读器  v8\n\n'
#             '  支持：TXT  /  EPUB  /  MD\n\n'
#             '  顶部按钮：书架  目录  笔记  书签  打开\n\n'
#             '  操作：\n'
#             '    滚轮 / 拖拽右侧滚动条  章内滚动\n'
#             '    滚到章末再滚           切下一章\n'
#             '    点击左侧 28% / 右侧    切上下章\n'
#             '    ← →  切章   S/↓  翻屏\n\n'
#             '  快捷键：\n'
#             '    O        添加书签\n'
#             '    N        添加笔记\n'
#             '    F5       开始/停止朗读\n'
#             '    D+E      最小化\n'
#         ))
#         self.txt.config(state='disabled')

#     # ─────────────────────────────────────────────────
#     # 最小化
#     # ─────────────────────────────────────────────────
#     def toggle_minimize(self):
#         self._minimized=not self._minimized
#         if self._minimized:
#             self._saved_h=self.root.winfo_height()
#             for w in (self.setbar,self.sep,self.txt_frame,self.bot_area): w.pack_forget()
#             self.root.geometry(f'{self.root.winfo_width()}x30')
#         else:
#             self.root.geometry(f'{self.root.winfo_width()}x{self._saved_h}')
#             self.sep.pack(fill='x',after=self.topbar)
#             if self._settings_open: self.setbar.pack(fill='x',after=self.topbar); self._retheme_setbar()
#             self.txt_frame.pack(fill='both',expand=True)
#             self.bot_area.pack(fill='x',side='bottom')

#     def toggle_settings(self):
#         self._settings_open=not self._settings_open
#         if self._settings_open: self.setbar.pack(fill='x',after=self.topbar); self._retheme_setbar()
#         else: self.setbar.pack_forget()

#     # ─────────────────────────────────────────────────
#     # 全文搜索（Ctrl+F）
#     # ─────────────────────────────────────────────────
#     def open_search(self):
#         if not self.chapters:
#             messagebox.showinfo('提示', '请先打开小说'); return

#         t = self._cur_theme()
#         bg, fg, bar, sel = t['bg'], t['fg'], t['bar'], t['sel']

#         # 若搜索窗已存在则聚焦
#         if hasattr(self, '_search_win') and self._search_win.winfo_exists():
#             self._search_win.lift(); self._search_win.focus_force(); return

#         win = tk.Toplevel(self.root)
#         win.title('全文搜索')
#         win.geometry('480x560')
#         win.resizable(True, True)
#         win.attributes('-topmost', True)
#         win.configure(bg=bg)
#         self._search_win = win

#         # ── 顶部搜索框 ────────────────────────────────
#         top = tk.Frame(win, bg=bar); top.pack(fill='x', padx=0, pady=0)
#         tk.Label(top, text='🔍', font=('',11), bg=bar, fg=fg).pack(side='left', padx=8, pady=6)

#         sv = tk.StringVar()
#         entry = tk.Entry(top, textvariable=sv, font=('',11), bg=bg, fg=fg,
#                          insertbackground=fg, relief='flat', bd=0)
#         entry.pack(side='left', fill='x', expand=True, ipady=4)

#         # 大小写 / 正则 选项
#         var_case  = tk.BooleanVar(value=False)
#         var_regex = tk.BooleanVar(value=False)
#         tk.Checkbutton(top, text='Aa', variable=var_case, font=('',8),
#                        bg=bar, fg=fg, activebackground=bar,
#                        selectcolor=bg).pack(side='left', padx=2)
#         tk.Checkbutton(top, text='.*', variable=var_regex, font=('',8),
#                        bg=bar, fg=fg, activebackground=bar,
#                        selectcolor=bg).pack(side='left', padx=2)

#         lbl_count = tk.Label(top, text='', font=('',8), bg=bar, fg=sel)
#         lbl_count.pack(side='left', padx=6)
#         tk.Button(top, text='×', relief='flat', font=('',10),
#                   bg=bar, fg=fg, command=win.destroy).pack(side='right', padx=6)

#         sep2 = tk.Frame(win, height=1, bg=sel); sep2.pack(fill='x')

#         # ── 结果列表 ──────────────────────────────────
#         list_frame = tk.Frame(win, bg=bg); list_frame.pack(fill='both', expand=True)
#         sb2 = tk.Scrollbar(list_frame); sb2.pack(side='right', fill='y')
#         lb = tk.Listbox(list_frame, font=('',9), relief='flat', bg=bg, fg=fg,
#                         selectbackground=sel, selectforeground=fg,
#                         borderwidth=0, highlightthickness=0,
#                         activestyle='none', yscrollcommand=sb2.set)
#         lb.pack(fill='both', expand=True); sb2.config(command=lb.yview)

#         # ── 预览区 ────────────────────────────────────
#         sep3 = tk.Frame(win, height=1, bg=sel); sep3.pack(fill='x')
#         preview_frame = tk.Frame(win, bg=bg, height=130)
#         preview_frame.pack(fill='x', padx=0); preview_frame.pack_propagate(False)

#         preview = tk.Text(preview_frame, font=('',9), bg=bg, fg=fg,
#                           relief='flat', padx=12, pady=6, wrap='word',
#                           state='disabled', borderwidth=0, highlightthickness=0)
#         preview.pack(fill='both', expand=True)
#         preview.tag_config('hit',  background='#d79921', foreground='#1d2021')
#         preview.tag_config('info', foreground=sel)

#         # 底部跳转栏
#         bot_f = tk.Frame(win, bg=bar, height=30)
#         bot_f.pack(fill='x'); bot_f.pack_propagate(False)
#         lbl_loc = tk.Label(bot_f, text='', font=('',8), bg=bar, fg=fg)
#         lbl_loc.pack(side='left', padx=8, pady=4)
#         btn_jump = tk.Button(bot_f, text='↩ 跳转到此处', font=('',8,'bold'),
#                              bg=bar, fg=fg, relief='flat', padx=8,
#                              state='disabled')
#         btn_jump.pack(side='right', padx=8, pady=3)

#         # ── 搜索逻辑 ──────────────────────────────────
#         results = []   # [(ch_idx, start_in_body, end_in_body, snippet)]

#         def do_search(*_):
#             results.clear(); lb.delete(0, 'end')
#             query = sv.get().strip()
#             if not query:
#                 lbl_count.config(text=''); return

#             flags = 0 if var_case.get() else re.IGNORECASE
#             try:
#                 if var_regex.get():
#                     pat = re.compile(query, flags)
#                 else:
#                     pat = re.compile(re.escape(query), flags)
#             except re.error as e:
#                 lbl_count.config(text=f'正则错误: {e}'); return

#             CONTEXT = 40   # 匹配前后各取多少字符
#             for ci, ch in enumerate(self.chapters):
#                 for m in pat.finditer(ch['body']):
#                     s, e2 = m.start(), m.end()
#                     pre  = ch['body'][max(0, s-CONTEXT):s].replace('\n', ' ')
#                     hit  = ch['body'][s:e2]
#                     post = ch['body'][e2:min(len(ch['body']), e2+CONTEXT)].replace('\n', ' ')
#                     snippet = (pre, hit, post)
#                     results.append((ci, s, e2, snippet))

#             lbl_count.config(text=f'共 {len(results)} 处')
#             for ci, s, e2, (pre, hit, post) in results:
#                 ch_title = self.chapters[ci]['title']
#                 display  = f"  第{ci+1}章  {ch_title[:14]}…  「{hit[:20]}」"
#                 lb.insert('end', display)

#             # 清空预览
#             preview.config(state='normal'); preview.delete('1.0','end')
#             preview.config(state='disabled')
#             lbl_loc.config(text='')
#             btn_jump.config(state='disabled')

#         sv.trace_add('write', do_search)
#         var_case.trace_add('write',  do_search)
#         var_regex.trace_add('write', do_search)

#         def on_select(event=None):
#             idxs = lb.curselection()
#             if not idxs: return
#             ci, s, e2, (pre, hit, post) = results[idxs[0]]
#             ch = self.chapters[ci]

#             # 更新预览
#             preview.config(state='normal'); preview.delete('1.0','end')
#             preview.insert('end', f'第{ci+1}章  {ch["title"]}\n', 'info')
#             preview.insert('end', '…' + pre)
#             preview.insert('end', hit, 'hit')
#             preview.insert('end', post + '…')
#             preview.config(state='disabled')

#             lbl_loc.config(text=f'第{ci+1}章 · 位置 {s}')
#             btn_jump.config(state='normal',
#                             command=lambda: _jump(ci, s, e2, hit))

#         def _jump(ci, s, e2, hit):
#             # 跳转到章节，并高亮匹配文字
#             self.goto_chapter(ci)
#             win.lift()
#             # 在 txt 里找到并高亮
#             self.root.after(80, lambda: _highlight_in_txt(hit))

#         def _highlight_in_txt(hit):
#             self.txt.tag_remove('search_hit', '1.0', 'end')
#             self.txt.tag_config('search_hit', background='#d79921', foreground='#1d2021')
#             start = '1.0'
#             while True:
#                 pos = self.txt.search(hit, start, nocase=not var_case.get(), stopindex='end')
#                 if not pos: break
#                 end_pos = f'{pos}+{len(hit)}c'
#                 self.txt.tag_add('search_hit', pos, end_pos)
#                 self.txt.see(pos)
#                 start = end_pos

#         lb.bind('<<ListboxSelect>>', on_select)
#         lb.bind('<Double-Button-1>', lambda e: btn_jump.invoke())
#         lb.bind('<Return>',         lambda e: btn_jump.invoke())

#         entry.focus()
#         # 如果有选中文字，自动填入搜索框
#         try:
#             sel_text = self.txt.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
#             if sel_text and '\n' not in sel_text:
#                 sv.set(sel_text)
#         except: pass

#         rx = self.root.winfo_x() + self.root.winfo_width() + 8
#         ry = self.root.winfo_y()
#         win.geometry(f'480x560+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 章节摘要（Ctrl+M）—— 调用智谱 GLM API
#     # ─────────────────────────────────────────────────
#     def open_summary(self):
#         if not self.chapters:
#             messagebox.showinfo('提示', '请先打开小说'); return

#         # ── 把所有内部状态装进一个对象，避免闭包变量遮蔽 ────
#         class State:
#             ch_body  = self.chapters[self.cur_ch]['body']
#             ch_title = self.chapters[self.cur_ch]['title']
#             ch_idx   = self.cur_ch
#             result   = ''   # 生成的摘要文本

#         st = State()
#         t  = self._cur_theme()
#         bg, fg, bar, sel = t['bg'], t['fg'], t['bar'], t['sel']

#         dlg = tk.Toplevel(self.root)
#         dlg.title('章节摘要')
#         dlg.geometry('420x460')
#         dlg.resizable(True, True)
#         dlg.attributes('-topmost', True)
#         dlg.configure(bg=bg)

#         # 标题栏
#         hdr = tk.Frame(dlg, bg=bar, height=30)
#         hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr, text=f'✨ 摘要 — {st.ch_title[:24]}',
#                  font=('',9,'bold'), bg=bar, fg=fg).pack(side='left', padx=8, pady=5)
#         tk.Button(hdr, text='×', relief='flat', font=('',10),
#                   bg=bar, fg=fg, command=dlg.destroy).pack(side='right', padx=6)

#         # 选项行
#         opt = tk.Frame(dlg, bg=bar); opt.pack(fill='x', padx=8, pady=4)
#         tk.Label(opt, text='长度', font=('',8), bg=bar, fg=fg).pack(side='left')
#         v_len = tk.StringVar(value='标准')
#         for lbl_text in ('简短','标准','详细'):
#             tk.Radiobutton(opt, text=lbl_text, variable=v_len, value=lbl_text,
#                            font=('',8), bg=bar, fg=fg,
#                            activebackground=bar, selectcolor=bg).pack(side='left', padx=3)

#         tk.Label(opt, text='  风格', font=('',8), bg=bar, fg=fg).pack(side='left')
#         v_style = tk.StringVar(value='客观')
#         for lbl_text in ('客观','活泼','学术'):
#             tk.Radiobutton(opt, text=lbl_text, variable=v_style, value=lbl_text,
#                            font=('',8), bg=bar, fg=fg,
#                            activebackground=bar, selectcolor=bg).pack(side='left', padx=3)

#         tk.Frame(dlg, height=1, bg=sel).pack(fill='x')

#         # 文本展示区
#         out = tk.Text(dlg, font=('',10), bg=bg, fg=fg,
#                       insertbackground=fg, relief='flat',
#                       padx=14, pady=10, wrap='word',
#                       borderwidth=0, highlightthickness=0,
#                       state='disabled')
#         out.pack(fill='both', expand=True)
#         out.tag_config('dim',  foreground=sel)
#         out.tag_config('warn', foreground='#cc241d')

#         # 底部按钮行
#         bf = tk.Frame(dlg, bg=bar, height=34)
#         bf.pack(fill='x', side='bottom'); bf.pack_propagate(False)

#         b_gen  = tk.Button(bf, text='✨ 生成摘要', font=('',9,'bold'),
#                            bg=bar, fg=fg, relief='flat', padx=10)
#         b_gen.pack(side='left', padx=8, pady=4)
#         b_copy = tk.Button(bf, text='复制', font=('',8),
#                            bg=bar, fg=fg, relief='flat', padx=6, state='disabled')
#         b_copy.pack(side='left', padx=2, pady=4)
#         b_note = tk.Button(bf, text='存笔记', font=('',8),
#                            bg=bar, fg=fg, relief='flat', padx=6, state='disabled')
#         b_note.pack(side='left', padx=2, pady=4)
#         lbl_st = tk.Label(bf, text='', font=('',8), bg=bar, fg=sel)
#         lbl_st.pack(side='right', padx=8)

#         # ── 工具函数 ──────────────────────────────────
#         def show(text, tag=''):
#             out.config(state='normal')
#             out.delete('1.0', 'end')
#             if tag:
#                 out.insert('end', text, tag)
#             else:
#                 out.insert('end', text)
#             out.config(state='disabled')

#         def build_prompt():
#             length_map = {'简短':'100字以内','标准':'200字左右','详细':'400字左右'}
#             style_map  = {'客观':'客观简洁','活泼':'生动活泼，可适当使用emoji','学术':'学术严谨，条理清晰'}
#             body_clip  = st.ch_body[:4000]
#             return (
#                 f"请对以下小说章节内容做摘要，要求：\n"
#                 f"1. 长度：{length_map[v_len.get()]}\n"
#                 f"2. 风格：{style_map[v_style.get()]}\n"
#                 f"3. 包含：主要人物、核心情节、关键转折\n"
#                 f"4. 直接输出摘要内容，不要任何前缀\n\n"
#                 f"章节标题：{st.ch_title}\n\n"
#                 f"章节内容：\n{body_clip}"
#             )

#         def on_success(text):
#             st.result = text
#             show(text)
#             b_gen.config(state='normal', text='✨ 重新生成')
#             b_copy.config(state='normal')
#             b_note.config(state='normal')
#             lbl_st.config(text=f'约 {len(text)} 字')

#         def on_error(msg):
#             b_gen.config(state='normal', text='✨ 生成摘要')
#             if msg == 'NO_KEY':
#                 show(
#                     '⚠ 未找到 API Key\n\n'
#                     '请在程序同目录新建 api_key.txt，\n'
#                     '把智谱 API Key 粘贴进去保存。\n\n'
#                     '获取地址：https://open.bigmodel.cn\n'
#                     'GLM-4-Flash 对新用户有免费额度。',
#                     'warn'
#                 )
#             else:
#                 show(f'⚠ 生成失败\n\n{msg}', 'warn')

#         def do_generate():
#             b_gen.config(state='disabled', text='生成中…')
#             b_copy.config(state='disabled')
#             b_note.config(state='disabled')
#             lbl_st.config(text='')
#             show('正在调用智谱 GLM，请稍候…', 'dim')

#             # 【修复关键】必须在主线程获取 Tkinter 的变量，提前拼接好字符串
#             try:
#                 _prompt = build_prompt()
#             except Exception as e:
#                 on_error(f"构建提示词失败: {e}")
#                 return

#             # 在后台线程执行网络请求，全部用局部变量
#             def worker():
#                 import urllib.request as _req_mod
#                 import urllib.error  as _err_mod
#                 import json          as _json_mod

#                 try:
#                     _api_key = _inject_api_key()
#                     if not _api_key:
#                         dlg.after(0, lambda: on_error('NO_KEY'))
#                         return

#                     _payload = _json_mod.dumps({
#                         'model':       'glm-4-flash',
#                         'max_tokens':  1024,
#                         'temperature': 0.7,
#                         'messages':    [{'role': 'user', 'content': _prompt}],
#                     }).encode('utf-8')

#                     _request = _req_mod.Request(
#                         'https://open.bigmodel.cn/api/paas/v4/chat/completions',
#                         data    = _payload,
#                         headers = {
#                             'Content-Type':  'application/json',
#                             'Authorization': f'Bearer {_api_key}',
#                         },
#                         method  = 'POST',
#                     )
                    
#                     with _req_mod.urlopen(_request, timeout=30) as _resp:
#                         _raw     = _resp.read().decode('utf-8')
#                         _parsed  = _json_mod.loads(_raw)
#                         _summary = _parsed['choices'][0]['message']['content'].strip()
#                     dlg.after(0, lambda s=_summary: on_success(s))
                    
#                 except _err_mod.HTTPError as _he:
#                     _body = _he.read().decode('utf-8', errors='replace')
#                     try:
#                         _eobj = _json_mod.loads(_body)
#                         _emsg = _eobj.get('error', {}).get('message', _body)
#                     except Exception:
#                         _emsg = _body[:300]
#                     _code = str(_he.code)
#                     dlg.after(0, lambda c=_code, m=_emsg: on_error(f'HTTP {c}: {m}'))
#                 except Exception as _ex:
#                     _msg = str(_ex)
#                     dlg.after(0, lambda m=_msg: on_error(m))

#             threading.Thread(target=worker, daemon=True).start()

#         def do_copy():
#             if not st.result: return
#             dlg.clipboard_clear()
#             dlg.clipboard_append(st.result)
#             lbl_st.config(text='已复制！')
#             dlg.after(1500, lambda: lbl_st.config(text=f'约 {len(st.result)} 字'))

#         def do_save_note():
#             if not st.result: return
#             note_list = self.notes.setdefault(self.book_path, [])
#             note_list.append({
#                 'ch':       st.ch_idx,
#                 'ch_title': st.ch_title,
#                 'content':  f'[AI摘要]\n{st.result}',
#                 'quote':    '',
#                 'time':     datetime.datetime.now().strftime('%m-%d %H:%M'),
#             })
#             _jsave(NOTES_FILE, self.notes)
#             self._update_nav()
#             self._toast('✏ 摘要已存为笔记')
#             lbl_st.config(text='已保存为笔记')

#         b_gen.config(command=do_generate)
#         b_copy.config(command=do_copy)
#         b_note.config(command=do_save_note)

#         # 初始提示
#         _has_key = bool(_inject_api_key())
#         _key_tip = '' if _has_key else '\n\n⚠ 未检测到 api_key.txt，点击生成后会显示配置说明。'
#         show(
#             f'📖 {st.ch_title}\n\n'
#             f'本章约 {len(st.ch_body)} 字。\n'
#             f'点击「✨ 生成摘要」开始。'
#             f'{_key_tip}',
#             'dim'
#         )

#         _rx = self.root.winfo_x() + self.root.winfo_width() + 8
#         _ry = self.root.winfo_y()
#         dlg.geometry(f'420x460+{_rx}+{_ry}')

#     # ─────────────────────────────────────────────────
#     # 关闭时保存
#     # ─────────────────────────────────────────────────
#     def _on_close(self):
#         self.tts.stop()
#         self._shelf_update()
#         self.root.destroy()

#     # ─────────────────────────────────────────────────
#     # 快捷键
#     # ─────────────────────────────────────────────────
#     def _bind_keys(self):
#         r=self.root
#         r.bind('<KeyPress-s>',   lambda e: self._scroll_down())
#         r.bind('<KeyPress-S>',   lambda e: self._scroll_down())
#         r.bind('<Right>',        lambda e: self.next_chapter())
#         r.bind('<Left>',         lambda e: self.prev_chapter())
#         r.bind('<Down>',         lambda e: self._scroll_down())
#         r.bind('<Up>',           lambda e: self.txt.yview_scroll(-3,'units'))
#         r.bind('<KeyPress-o>',   lambda e: self.add_mark())
#         r.bind('<KeyPress-O>',   lambda e: self.add_mark())
#         r.bind('<KeyPress-n>',   lambda e: self.add_note())
#         r.bind('<KeyPress-N>',   lambda e: self.add_note())
#         r.bind('<F5>',           lambda e: self.toggle_tts())
#         r.bind('<Control-f>',    lambda e: self.open_search())
#         r.bind('<Control-F>',    lambda e: self.open_search())
#         r.bind('<Control-m>',    lambda e: self.open_summary())
#         r.bind('<Control-M>',    lambda e: self.open_summary())
#         r.bind('<KeyPress-d>',   self._dp)
#         r.bind('<KeyPress-D>',   self._dp)
#         r.bind('<KeyRelease-d>', self._dr)
#         r.bind('<KeyRelease-D>', self._dr)
#         r.bind('<KeyPress-e>',   self._ep)
#         r.bind('<KeyPress-E>',   self._ep)
#         r.focus_set()

#     def _dp(self,e): self._d_held=True
#     def _dr(self,e): self._d_held=False
#     def _ep(self,e):
#         if self._d_held: self.toggle_minimize()


# # ══════════════════════════════════════════════════════════════
# if __name__ == '__main__':
#     try:
#         from ctypes import windll
#         windll.shcore.SetProcessDpiAwareness(1)
#     except: pass
#     App()

# """
# 摸鱼阅读器 v8.0  —  全功能版
# 功能：
#   阅读体验：章节滚动、翻页、字号/行距/字色/背景/护眼模式、透明度、屏幕取色
#   书架管理：添加/删除/重命名书籍、显示封面/进度/上次阅读时间
#   阅读进度：自动记录、书架显示进度条
#   笔记系统：N键在当前章节创建笔记、查看/编辑/删除笔记
#   书签系统：O键快速书签、书签列表跳转删除
#   听书TTS ：F5启动/停止，支持语速调整（需系统 pyttsx3 或 espeak）
#   竖向拖拽滚动条、目录跳转、搜索

# 运行：python novel_reader.py
# 依赖：pip install pyttsx3   （TTS，可选）
#       pip install pillow     （屏幕取色，可选）
# """

# import tkinter as tk
# from tkinter import ttk, filedialog, colorchooser, messagebox, scrolledtext
# import os, re, zipfile, sys, json, copy, threading, time, datetime
# from html.parser import HTMLParser


# # ══════════════════════════════════════════════════════════════
# # HTML → 纯文本
# # ══════════════════════════════════════════════════════════════
# class _H2T(HTMLParser):
#     SKIP  = {'script','style','head','meta','link'}
#     BLOCK = {'p','div','br','h1','h2','h3','h4','h5',
#              'h6','li','tr','td','th','section','article'}
#     def __init__(self): super().__init__(); self.out, self._s = [], 0
#     def handle_starttag(self, tag, _):
#         if tag in self.SKIP:  self._s += 1
#         if tag in self.BLOCK: self.out.append('\n')
#     def handle_endtag(self, tag):
#         if tag in self.SKIP:  self._s = max(0, self._s-1)
#         if tag in self.BLOCK: self.out.append('\n')
#     def handle_data(self, d):
#         if not self._s: self.out.append(d)
#     def text(self): return re.sub(r'\n{3,}','\n\n',''.join(self.out)).strip()

# def html2text(s):
#     p = _H2T()
#     try: p.feed(s)
#     except: pass
#     return p.text()


# # ══════════════════════════════════════════════════════════════
# # EPUB
# # ══════════════════════════════════════════════════════════════
# def read_epub(path):
#     import xml.etree.ElementTree as ET
#     title = os.path.splitext(os.path.basename(path))[0]
#     body  = ''
#     try:
#         with zipfile.ZipFile(path) as z:
#             ns = z.namelist()
#             opf, odir = '', ''
#             if 'META-INF/container.xml' in ns:
#                 for el in ET.fromstring(z.read('META-INF/container.xml')).iter():
#                     if el.tag.endswith('rootfile'):
#                         opf = el.get('full-path',''); odir = opf.rsplit('/',1)[0] if '/' in opf else ''; break
#             items, spine = {}, []
#             if opf and opf in ns:
#                 root = ET.fromstring(z.read(opf))
#                 for el in root.iter():
#                     tag = el.tag.split('}')[-1]
#                     if tag == 'item':
#                         mid,href,mt = el.get('id',''),el.get('href',''),el.get('media-type','')
#                         if href and ('html' in mt or href.endswith(('.html','.xhtml','.htm'))):
#                             items[mid] = (odir+'/'+href).lstrip('/') if odir else href
#                     elif tag == 'itemref':
#                         r = el.get('idref','')
#                         if r in items: spine.append(items[r])
#                     elif tag == 'title' and el.text: title = el.text
#             if not spine:
#                 spine = sorted(f for f in ns if re.search(r'\.(html|htm|xhtml)$',f,re.I)
#                                and 'toc' not in f.lower() and 'nav' not in f.lower())
#             for href in spine:
#                 if href in ns:
#                     try: body += html2text(z.read(href).decode('utf-8','replace')) + '\n\n'
#                     except: pass
#     except Exception as e: body = f'[EPUB解析失败: {e}]'
#     return title, body.strip()


# # ══════════════════════════════════════════════════════════════
# # 章节切割
# # ══════════════════════════════════════════════════════════════
# _CH = re.compile(
#     r'^(第\s*[零一二三四五六七八九十百千万\d〇]+\s*[章节卷集回部篇][^\n]{0,40}'
#     r'|Chapter\s*\d+[^\n]{0,40}|CHAPTER\s*\d+[^\n]{0,40}|【[^\n]{1,30}】)', re.I)

# def split_chapters(text):
#     bounds = []
#     for m in re.finditer(r'^.+$', text, re.M):
#         line = m.group().strip()
#         if line and _CH.match(line): bounds.append((m.start(), line))
#     if not bounds: return [{'title':'全文','body':text}]
#     chs = []
#     for i,(pos,title) in enumerate(bounds):
#         end = bounds[i+1][0] if i+1<len(bounds) else len(text)
#         chs.append({'title':title,'body':text[pos:end]})
#     return chs


# # ══════════════════════════════════════════════════════════════
# # 数据存储
# # ══════════════════════════════════════════════════════════════
# DATA_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.moyu_data')
# os.makedirs(DATA_DIR, exist_ok=True)
# SHELF_FILE = os.path.join(DATA_DIR, 'shelf.json')
# NOTES_FILE = os.path.join(DATA_DIR, 'notes.json')
# MARKS_FILE = os.path.join(DATA_DIR, 'marks.json')

# def _jload(f):
#     try:
#         with open(f, encoding='utf-8') as fp: return json.load(fp)
#     except: return {}

# def _jsave(f, d):
#     try:
#         with open(f, 'w', encoding='utf-8') as fp: json.dump(d, fp, ensure_ascii=False, indent=2)
#     except: pass

# def _inject_api_key():
#     """
#     从程序目录的 api_key.txt 自动读取智谱 API Key。
#     用户把 Key 粘贴进 api_key.txt 即可，无需手动配置环境变量。
#     返回 key 字符串，失败返回空字符串。
#     """
#     key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_key.txt')
#     if os.path.exists(key_file):
#         try:
#             key = open(key_file, encoding='utf-8').read().strip()
#             if key:
#                 os.environ['ZHIPU_API_KEY'] = key
#                 return key
#         except: pass
#     return os.environ.get('ZHIPU_API_KEY', '')


# # ══════════════════════════════════════════════════════════════
# # TTS 引擎（可选）
# # ══════════════════════════════════════════════════════════════
# class TTS:
#     def __init__(self):
#         self._engine = None
#         self._thread = None
#         self._stop   = threading.Event()
#         self._text   = ''
#         self._rate   = 180
#         self._avail  = False
#         self._init()

#     def _init(self):
#         try:
#             import pyttsx3
#             self._engine = pyttsx3.init()
#             self._avail  = True
#         except:
#             self._avail = False

#     @property
#     def available(self): return self._avail

#     def set_rate(self, rate):
#         self._rate = int(rate)
#         if self._engine:
#             try: self._engine.setProperty('rate', self._rate)
#             except: pass

#     def speak(self, text, on_done=None):
#         if not self._avail: return
#         self.stop()
#         self._stop.clear()
#         self._text = text

#         def run():
#             try:
#                 import pyttsx3
#                 eng = pyttsx3.init()
#                 eng.setProperty('rate', self._rate)
#                 # 逐段朗读，支持中途停止
#                 paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
#                 for para in paragraphs:
#                     if self._stop.is_set(): break
#                     eng.say(para)
#                     eng.runAndWait()
#                 eng.stop()
#             except: pass
#             if on_done: on_done()

#         self._thread = threading.Thread(target=run, daemon=True)
#         self._thread.start()

#     def stop(self):
#         self._stop.set()
#         if self._engine:
#             try: self._engine.stop()
#             except: pass


# # ══════════════════════════════════════════════════════════════
# # 屏幕取色器
# # ══════════════════════════════════════════════════════════════
# def screen_color_picker(callback):
#     try: from PIL import ImageGrab
#     except ImportError:
#         c = colorchooser.askcolor(title='选择颜色')
#         if c and c[1]: callback(c[1])
#         return
#     from PIL import ImageGrab, Image, ImageTk
#     ZOOM,HALF = 10,5; CS = (HALF*2+1)*ZOOM
#     preview = tk.Toplevel(); preview.overrideredirect(True)
#     preview.attributes('-topmost',True); preview.configure(bg='#1a1a1a')
#     preview.geometry(f'{CS+4}x{CS+28}+200+200')
#     canvas = tk.Canvas(preview,width=CS,height=CS,bg='#000',highlightthickness=1,
#                        highlightbackground='#555',cursor='none')
#     canvas.pack(padx=2,pady=(2,0))
#     lbl = tk.Label(preview,text='#000000',font=('Consolas',9,'bold'),bg='#1a1a1a',fg='white',pady=1)
#     lbl.pack()
#     cur,ph,aid,done = ['#000000'],[None],[None],[False]
#     def update():
#         if done[0]: return
#         try:
#             mx,my = preview.winfo_pointerx(),preview.winfo_pointery()
#             img = ImageGrab.grab(bbox=(mx-HALF,my-HALF,mx+HALF+1,my+HALF+1))
#             zoomed = img.resize((CS,CS),Image.NEAREST); ph[0]=ImageTk.PhotoImage(zoomed)
#             canvas.delete('all'); canvas.create_image(0,0,anchor='nw',image=ph[0])
#             c2=CS//2
#             canvas.create_line(c2,0,c2,CS,fill='white',width=1)
#             canvas.create_line(0,c2,CS,c2,fill='white',width=1)
#             canvas.create_rectangle(c2-ZOOM,c2-ZOOM,c2+ZOOM,c2+ZOOM,outline='white',width=2)
#             px=img.getpixel((HALF,HALF)); hx='#{:02x}{:02x}{:02x}'.format(px[0],px[1],px[2])
#             cur[0]=hx; lbl.config(text=hx)
#             sw,sh=preview.winfo_screenwidth(),preview.winfo_screenheight()
#             ox,oy=mx+18,my+18
#             if ox+CS+10>sw: ox=mx-CS-22
#             if oy+CS+32>sh: oy=my-CS-34
#             preview.geometry(f'+{ox}+{oy}')
#         except: pass
#         aid[0]=preview.after(40,update)
#     def finish():
#         done[0]=True
#         if aid[0]:
#             try: preview.after_cancel(aid[0])
#             except: pass
#         for w in (overlay,preview):
#             try: w.destroy()
#             except: pass
#     overlay = tk.Toplevel(); overlay.overrideredirect(True)
#     overlay.attributes('-topmost',True); overlay.attributes('-alpha',0.01)
#     sw,sh=overlay.winfo_screenwidth(),overlay.winfo_screenheight()
#     overlay.geometry(f'{sw}x{sh}+0+0'); overlay.configure(bg='white',cursor='crosshair')
#     overlay.bind('<Button-1>',lambda e:(finish(),callback(cur[0])))
#     overlay.bind('<Escape>',lambda e:finish())
#     overlay.focus_force(); aid[0]=preview.after(40,update)


# # ══════════════════════════════════════════════════════════════
# # 自定义竖向滚动条
# # ══════════════════════════════════════════════════════════════
# class SmoothScrollbar:
#     W = 10
#     def __init__(self, parent, on_scroll):
#         self.on_scroll = on_scroll
#         self._lo,self._hi = 0.0,1.0
#         self._dragging = False; self._drag_start_y = 0; self._drag_start_lo = 0.0
#         self.c_bg='#ebdbb2'; self.c_track='#d5c4a1'; self.c_thumb='#b8a882'; self.c_hover='#8f7a55'
#         self.cv = tk.Canvas(parent, width=self.W, highlightthickness=0, cursor='arrow')
#         self.cv.pack(side='right', fill='y')
#         self.cv.bind('<Configure>', lambda e: self._draw())
#         self.cv.bind('<ButtonPress-1>',   self._press)
#         self.cv.bind('<B1-Motion>',       self._drag)
#         self.cv.bind('<ButtonRelease-1>', self._release)
#         self.cv.bind('<Enter>', lambda e: self._hover(True))
#         self.cv.bind('<Leave>', lambda e: self._hover(False))
#         self._hovered = False

#     def set(self, lo, hi): self._lo,self._hi = float(lo),float(hi); self._draw()

#     def set_colors(self, bg, track, thumb, thumb_hover):
#         self.c_bg=bg; self.c_track=track; self.c_thumb=thumb; self.c_hover=thumb_hover; self._draw()

#     def _draw(self):
#         cv=self.cv; W=self.W; H=cv.winfo_height()
#         if H<4: return
#         cv.delete('all'); PAD=2
#         cv.create_rectangle(0,0,W,H,fill=self.c_bg,outline='')
#         tx=W//2
#         cv.create_line(tx,PAD,tx,H-PAD,fill=self.c_track,width=W-4,capstyle='round')
#         th=max(20,int((self._hi-self._lo)*(H-2*PAD))); ty=PAD+int(self._lo*(H-2*PAD))
#         ty2=min(H-PAD,ty+th); color=self.c_hover if self._hovered else self.c_thumb
#         r=(W-4)//2; x1,x2=2,W-2; y1,y2=ty,ty2
#         if y2-y1>=2*r:
#             cv.create_rectangle(x1,y1+r,x2,y2-r,fill=color,outline='')
#             cv.create_oval(x1,y1,x2,y1+2*r,fill=color,outline='')
#             cv.create_oval(x1,y2-2*r,x2,y2,fill=color,outline='')
#         else: cv.create_oval(x1,y1,x2,y2,fill=color,outline='')

#     def _hover(self, v): self._hovered=v; self._draw()

#     def _y_to_frac(self,y):
#         H=self.cv.winfo_height(); PAD=2
#         return max(0.0,min(1.0,(y-PAD)/max(1,H-2*PAD)))

#     def _thumb_range(self):
#         H=self.cv.winfo_height(); PAD=2
#         th=max(20,int((self._hi-self._lo)*(H-2*PAD))); ty=PAD+int(self._lo*(H-2*PAD))
#         return ty,ty+th

#     def _press(self, e):
#         ty1,ty2=self._thumb_range()
#         if ty1<=e.y<=ty2:
#             self._dragging=True; self._drag_start_y=e.y; self._drag_start_lo=self._lo
#         else:
#             frac=self._y_to_frac(e.y); span=self._hi-self._lo
#             self.on_scroll(max(0.0,min(1.0-span,frac-span/2)))

#     def _drag(self, e):
#         if not self._dragging: return
#         H=self.cv.winfo_height(); PAD=2; dy=e.y-self._drag_start_y
#         delta=dy/max(1,H-2*PAD); span=self._hi-self._lo
#         target=max(0.0,min(1.0-span,self._drag_start_lo+delta))
#         self._lo=target; self._hi=target+span; self._draw(); self.on_scroll(target)

#     def _release(self, e): self._dragging=False


# # ══════════════════════════════════════════════════════════════
# # 主程序
# # ══════════════════════════════════════════════════════════════
# class App:

#     THEMES = {
#         '暖黄': dict(bg='#fdf6e3',fg='#3c3836',bar='#ebdbb2',sel='#d5c4a1',thumb='#b8a882',thumb_h='#8f7a55'),
#         '夜间': dict(bg='#1e1e2e',fg='#cdd6f4',bar='#181825',sel='#313244',thumb='#45475a',thumb_h='#6c7086'),
#         '护眼': dict(bg='#1a2f1a',fg='#a8d5a2',bar='#152315',sel='#2d5a2d',thumb='#3a6b3a',thumb_h='#57c454'),
#         '纸张': dict(bg='#f5f0e8',fg='#2c2416',bar='#ede4d0',sel='#c8b89a',thumb='#c8a882',thumb_h='#8b6045'),
#         '白底': dict(bg='#ffffff',fg='#1a1a1a',bar='#f0f0f0',sel='#dddddd',thumb='#bbbbbb',thumb_h='#888888'),
#     }

#     def __init__(self):
#         self.root = tk.Tk()
#         self.root.title('摸鱼阅读器')
#         self.root.geometry('440x600')
#         self.root.minsize(320, 400)
#         self.root.attributes('-topmost', True)

#         # 数据
#         self.shelf   = _jload(SHELF_FILE)   # {path: {title,last_ch,total_ch,last_time,read_time}}
#         self.notes   = _jload(NOTES_FILE)   # {path: [{ch,title,content,time}]}
#         self.marks   = _jload(MARKS_FILE)   # {path: [{ch,ch_title,time}]}

#         self.book_path  = ''
#         self.book_title = ''
#         self.chapters   = []
#         self.cur_ch     = 0

#         # UI 状态
#         self.theme_name     = '暖黄'
#         self.custom_bg      = None
#         self.custom_bar     = None
#         self.font_size      = 14
#         self.line_spacing   = 6
#         self.font_fam       = ('宋体' if sys.platform=='win32'
#                                else 'Songti SC' if sys.platform=='darwin'
#                                else 'Noto Serif CJK SC')
#         self._d_held        = False
#         self._minimized     = False
#         self._settings_open = False
#         self._wheel_accum   = 0
#         self._tts_playing   = False

#         self.tts = TTS()

#         self._build_ui()
#         self._apply_theme()
#         self._bind_keys()
#         self.root.protocol('WM_DELETE_WINDOW', self._on_close)
#         self.root.mainloop()

#     # ─────────────────────────────────────────────────
#     # UI 构建
#     # ─────────────────────────────────────────────────
#     def _build_ui(self):
#         r = self.root

#         # 顶部栏
#         self.topbar = tk.Frame(r, height=30)
#         self.topbar.pack(fill='x')
#         self.topbar.pack_propagate(False)

#         dots = tk.Frame(self.topbar)
#         dots.pack(side='left', padx=6, pady=5)
#         self._dot(dots, '#ff5f57', self.toggle_minimize)
#         self._dot(dots, '#ffbd2e', self.toggle_settings)
#         self._dot(dots, '#28ca41', self.open_file)

#         self.lbl_title = tk.Label(self.topbar, text='摸鱼阅读器', font=('',9))
#         self.lbl_title.pack(side='left', fill='x', expand=True)

#         rbf = tk.Frame(self.topbar); rbf.pack(side='right', padx=2)
#         self._tbtn(rbf, '书架', self.open_shelf)
#         self._tbtn(rbf, '目录', self.open_chapters)
#         self._tbtn(rbf, '搜索', self.open_search)
#         self._tbtn(rbf, '摘要', self.open_summary)
#         self._tbtn(rbf, '笔记', self.open_notes)
#         self._tbtn(rbf, '书签', self.open_marks)
#         self._tbtn(rbf, '打开', self.open_file)
#         self._tbtn(rbf, '×',   r.destroy)

#         for w in (self.topbar, self.lbl_title):
#             w.bind('<ButtonPress-1>', self._drag_start)
#             w.bind('<B1-Motion>',     self._drag_move)

#         # 设置栏
#         self.setbar = tk.Frame(r)
#         self._build_setbar()

#         # 分隔线
#         self.sep = tk.Frame(r, height=1)
#         self.sep.pack(fill='x')

#         # 文本区
#         self.txt_frame = tk.Frame(r)
#         self.txt_frame.pack(fill='both', expand=True)

#         self.vsb = SmoothScrollbar(self.txt_frame,
#                                    on_scroll=lambda f: self.txt.yview_moveto(f))

#         self.txt = tk.Text(
#             self.txt_frame, wrap='word',
#             relief='flat', padx=16, pady=10,
#             state='disabled', cursor='arrow',
#             font=(self.font_fam, self.font_size),
#             borderwidth=0, highlightthickness=0,
#             spacing1=self.line_spacing,
#             spacing2=self.line_spacing//2,
#             spacing3=self.line_spacing,
#             yscrollcommand=self._on_yscroll,
#         )
#         self.txt.pack(side='left', fill='both', expand=True)
#         self.txt.bind('<Button-1>',   self._on_click)
#         self.txt.bind('<MouseWheel>', self._on_wheel)
#         self.txt.bind('<Button-4>',   self._on_wheel)
#         self.txt.bind('<Button-5>',   self._on_wheel)
#         self._show_welcome()

#         # 底部
#         self.bot_area = tk.Frame(r)
#         self.bot_area.pack(fill='x', side='bottom')

#         self.botbar = tk.Frame(self.bot_area, height=28)
#         self.botbar.pack(fill='x')
#         self.botbar.pack_propagate(False)

#         self.btn_prev = tk.Button(self.botbar, text='◀', font=('',9),
#                                   relief='flat', padx=4, command=self.prev_chapter)
#         self.btn_prev.pack(side='left', padx=4, pady=3)

#         self.lbl_prog = tk.Label(self.botbar, text='', font=('',8))
#         self.lbl_prog.pack(side='left', expand=True)

#         self.btn_tts = tk.Button(self.botbar, text='🔊', font=('',9),
#                                  relief='flat', padx=3, command=self.toggle_tts)
#         self.btn_tts.pack(side='right', padx=2, pady=3)

#         self.btn_note = tk.Button(self.botbar, text='✏', font=('',9),
#                                   relief='flat', padx=3, command=self.add_note)
#         self.btn_note.pack(side='right', padx=2, pady=3)

#         self.btn_mark = tk.Button(self.botbar, text='🔖', font=('',9),
#                                   relief='flat', padx=2, command=self.add_mark)
#         self.btn_mark.pack(side='right', padx=2, pady=3)

#         self.btn_next = tk.Button(self.botbar, text='▶', font=('',9),
#                                   relief='flat', padx=4, command=self.next_chapter)
#         self.btn_next.pack(side='right', padx=4, pady=3)

#     def _tbtn(self, parent, text, cmd):
#         tk.Button(parent, text=text, font=('',8), relief='flat',
#                   padx=3, command=cmd).pack(side='left', padx=1)

#     def _dot(self, p, color, cmd):
#         lb = tk.Label(p, text='⬤', fg=color, font=('',12), cursor='hand2')
#         lb.pack(side='left', padx=2)
#         lb.bind('<Button-1>', lambda e: cmd())

#     # ─────────────────────────────────────────────────
#     # 设置栏
#     # ─────────────────────────────────────────────────
#     def _build_setbar(self):
#         def row(): f=tk.Frame(self.setbar); f.pack(fill='x',padx=8,pady=2); return f

#         r1 = row()
#         tk.Label(r1,text='字号',font=('',8)).pack(side='left')
#         self.sl_font = tk.Scale(r1,from_=10,to=32,orient='horizontal',length=70,
#                                 showvalue=True,font=('',7),command=self._on_font_size)
#         self.sl_font.set(self.font_size); self.sl_font.pack(side='left',padx=2)
#         tk.Label(r1,text='行距',font=('',8)).pack(side='left',padx=(8,0))
#         self.sl_spacing = tk.Scale(r1,from_=0,to=24,orient='horizontal',length=70,
#                                    showvalue=True,font=('',7),command=self._on_spacing)
#         self.sl_spacing.set(self.line_spacing); self.sl_spacing.pack(side='left',padx=2)

#         r2 = row()
#         tk.Label(r2,text='透明',font=('',8)).pack(side='left')
#         self.sl_alpha = tk.Scale(r2,from_=20,to=100,orient='horizontal',length=80,
#                                  showvalue=True,font=('',7),
#                                  command=lambda v: self.root.attributes('-alpha',int(v)/100))
#         self.sl_alpha.set(100); self.sl_alpha.pack(side='left',padx=2)
#         # TTS 语速
#         tk.Label(r2,text='语速',font=('',8)).pack(side='left',padx=(8,0))
#         self.sl_tts_rate = tk.Scale(r2,from_=80,to=300,orient='horizontal',length=70,
#                                     showvalue=True,font=('',7),
#                                     command=lambda v: self.tts.set_rate(int(v)))
#         self.sl_tts_rate.set(180); self.sl_tts_rate.pack(side='left',padx=2)

#         r3 = row()
#         tk.Label(r3,text='字色',font=('',8)).pack(side='left')
#         self.btn_fg_color = tk.Button(r3,text='  ',relief='groove',width=2,
#                                       font=('',8),command=self._pick_fg)
#         self.btn_fg_color.pack(side='left',padx=2)
#         tk.Label(r3,text='背景',font=('',8)).pack(side='left',padx=(6,0))
#         self.btn_bg_color = tk.Button(r3,text='  ',relief='groove',width=2,
#                                       font=('',8),command=self._pick_bg)
#         self.btn_bg_color.pack(side='left',padx=2)
#         tk.Button(r3,text='🎨取色',font=('',8),relief='flat',padx=4,
#                   command=self._screen_pick).pack(side='left',padx=4)
#         tk.Button(r3,text='重置',font=('',8),relief='flat',padx=4,
#                   command=self._reset_colors).pack(side='left',padx=2)

#         r4 = row()
#         tk.Label(r4,text='主题',font=('',8)).pack(side='left')
#         self.var_theme = tk.StringVar(value=self.theme_name)
#         cb = ttk.Combobox(r4,textvariable=self.var_theme,
#                           values=list(self.THEMES.keys()),width=7,font=('',8),state='readonly')
#         cb.pack(side='left',padx=4); cb.bind('<<ComboboxSelected>>',self._on_theme)
#         # 快速护眼切换
#         tk.Button(r4,text='☘护眼',font=('',8),relief='flat',padx=4,
#                   command=lambda: (self.var_theme.set('护眼'),self._on_theme())).pack(side='left',padx=2)
#         tk.Button(r4,text='🌙夜间',font=('',8),relief='flat',padx=4,
#                   command=lambda: (self.var_theme.set('夜间'),self._on_theme())).pack(side='left',padx=2)

#     # ─────────────────────────────────────────────────
#     # 颜色
#     # ─────────────────────────────────────────────────
#     def _pick_fg(self):
#         t=self._cur_theme(); c=colorchooser.askcolor(color=t['fg'],title='字体颜色')
#         if c and c[1]: self.THEMES[self.theme_name]['fg']=c[1]; self.txt.config(fg=c[1]); self.btn_fg_color.config(bg=c[1])

#     def _pick_bg(self):
#         c=colorchooser.askcolor(color=self._cur_theme()['bg'],title='背景颜色')
#         if c and c[1]: self._apply_custom_bg(c[1])

#     def _screen_pick(self):
#         alpha=self.sl_alpha.get()/100; self.root.attributes('-alpha',0.0)
#         def on(hx): self.root.after(100,lambda:self.root.attributes('-alpha',alpha)); self._apply_custom_bg(hx)
#         self.root.after(120, lambda: screen_color_picker(on))

#     def _apply_custom_bg(self,hx):
#         self.custom_bg=hx; self.custom_bar=self._darken(hx,0.88); self._apply_theme()
#         try: self.btn_bg_color.config(bg=hx)
#         except: pass

#     def _reset_colors(self): self.custom_bg=self.custom_bar=None; self._apply_theme()
#     def _darken(self,hx,f=0.88):
#         h=hx.lstrip('#')
#         return '#{:02x}{:02x}{:02x}'.format(int(int(h[0:2],16)*f),int(int(h[2:4],16)*f),int(int(h[4:6],16)*f))

#     def _cur_theme(self):
#         t=copy.copy(self.THEMES[self.theme_name])
#         if self.custom_bg:  t['bg']=self.custom_bg
#         if self.custom_bar: t['bar']=self.custom_bar
#         return t

#     def _on_theme(self, e=None):
#         self.theme_name=self.var_theme.get(); self.custom_bg=self.custom_bar=None; self._apply_theme()

#     def _apply_theme(self):
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         self.root.configure(bg=bar)
#         self._cf(self.topbar,bar,fg); self._cf(self.botbar,bar,fg); self._cf(self.bot_area,bar,fg)
#         self.sep.config(bg=sel); self.txt_frame.config(bg=bg)
#         self.vsb.cv.config(bg=bg)
#         self.vsb.set_colors(bg=bg,track=sel,thumb=t.get('thumb',sel),thumb_hover=t.get('thumb_h',fg))
#         self.txt.config(bg=bg,fg=fg,insertbackground=fg,selectbackground=sel)
#         self.lbl_prog.config(bg=bar,fg=fg)
#         for b in (self.btn_prev,self.btn_next,self.btn_mark,self.btn_note,self.btn_tts):
#             b.config(bg=bar,fg=fg,activebackground=sel)
#         self._retheme_setbar()
#         try:
#             if self.custom_bg: self.btn_bg_color.config(bg=self.custom_bg)
#         except: pass

#     def _cf(self,fr,bg,fg):
#         try: fr.config(bg=bg)
#         except: pass
#         for w in fr.winfo_children():
#             try: w.config(bg=bg,fg=fg,activebackground=bg)
#             except: pass
#             for w2 in w.winfo_children():
#                 try: w2.config(bg=bg,fg=fg,activebackground=bg)
#                 except: pass

#     def _retheme_setbar(self):
#         t=self._cur_theme(); bg,fg,sel=t['bar'],t['fg'],t['sel']
#         self._cf(self.setbar,bg,fg)
#         for sl in (self.sl_font,self.sl_alpha,self.sl_spacing,self.sl_tts_rate):
#             try: sl.config(bg=bg,fg=fg,troughcolor=sel,activebackground=sel)
#             except: pass
#         try: self.btn_fg_color.config(bg=fg)
#         except: pass

#     # ─────────────────────────────────────────────────
#     # 字号 / 行距
#     # ─────────────────────────────────────────────────
#     def _on_font_size(self,val):
#         self.font_size=int(float(val)); self.txt.config(font=(self.font_fam,self.font_size))

#     def _on_spacing(self,val):
#         sp=int(float(val)); self.line_spacing=sp
#         self.txt.config(spacing1=sp,spacing2=sp//2,spacing3=sp)

#     # ─────────────────────────────────────────────────
#     # 拖动窗口
#     # ─────────────────────────────────────────────────
#     def _drag_start(self,e): self._dx=e.x_root-self.root.winfo_x(); self._dy=e.y_root-self.root.winfo_y()
#     def _drag_move(self,e):  self.root.geometry(f'+{e.x_root-self._dx}+{e.y_root-self._dy}')

#     # ─────────────────────────────────────────────────
#     # 打开文件
#     # ─────────────────────────────────────────────────
#     def open_file(self, path=None):
#         if path is None:
#             path = filedialog.askopenfilename(
#                 title='打开小说',
#                 filetypes=[('小说文件','*.txt *.epub *.md'),('所有文件','*.*')])
#         if not path: return
#         ext = os.path.splitext(path)[1].lower()
#         if ext == '.epub': title,text = read_epub(path)
#         else:
#             title = os.path.splitext(os.path.basename(path))[0]
#             try:
#                 with open(path,encoding='utf-8',errors='replace') as f: text=f.read()
#             except Exception as e: messagebox.showerror('错误',str(e)); return
#         self.book_path=path; self.book_title=title
#         self.lbl_title.config(text=f'  {title}'); self.root.title(f'摸鱼阅读器 — {title}')
#         self._load(text)

#     def _load(self,text):
#         self.chapters = split_chapters(text)
#         # 恢复上次阅读位置
#         si = self.shelf.get(self.book_path,{})
#         self.cur_ch = max(0,min(si.get('last_ch',0),len(self.chapters)-1))
#         # 更新书架
#         self._shelf_update()
#         self._render_chapter()

#     # ─────────────────────────────────────────────────
#     # 书架管理
#     # ─────────────────────────────────────────────────
#     def _shelf_update(self):
#         p = self.book_path
#         prev = self.shelf.get(p,{})
#         self.shelf[p] = {
#             'title':      self.book_title,
#             'path':       p,
#             'last_ch':    self.cur_ch,
#             'total_ch':   len(self.chapters),
#             'last_time':  datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
#             'added_time': prev.get('added_time', datetime.datetime.now().strftime('%Y-%m-%d')),
#         }
#         _jsave(SHELF_FILE, self.shelf)

#     def open_shelf(self):
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('书架'); win.geometry('380x460')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)

#         hdr=tk.Frame(win,bg=bar,height=30); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='📚 书架',font=('',10,'bold'),bg=bar,fg=fg).pack(side='left',padx=10,pady=5)
#         tk.Button(hdr,text='+添加',font=('',8),relief='flat',bg=bar,fg=fg,
#                   command=lambda:self._shelf_add(win)).pack(side='right',padx=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,
#                   command=win.destroy).pack(side='right',padx=4)

#         # 书籍列表
#         frame=tk.Frame(win,bg=bg); frame.pack(fill='both',expand=True,padx=6,pady=6)
#         sb2=tk.Scrollbar(frame); sb2.pack(side='right',fill='y')
#         canvas=tk.Canvas(frame,bg=bg,highlightthickness=0,yscrollcommand=sb2.set)
#         canvas.pack(fill='both',expand=True); sb2.config(command=canvas.yview)
#         inner=tk.Frame(canvas,bg=bg); canvas.create_window((0,0),window=inner,anchor='nw')

#         def refresh():
#             for w in inner.winfo_children(): w.destroy()
#             if not self.shelf:
#                 tk.Label(inner,text='书架空空，快去添加书吧',font=('',10),bg=bg,fg=sel).pack(pady=30)
#             for path,info in sorted(self.shelf.items(),key=lambda x:x[1].get('last_time',''),reverse=True):
#                 self._shelf_card(inner,path,info,bg,fg,bar,sel,win,refresh)
#             inner.update_idletasks()
#             canvas.config(scrollregion=canvas.bbox('all'))
#         refresh()

#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'380x460+{rx}+{ry}')

#     def _shelf_card(self,parent,path,info,bg,fg,bar,sel,shelf_win,refresh):
#         card=tk.Frame(parent,bg=bar,relief='flat',bd=0)
#         card.pack(fill='x',padx=4,pady=3)
#         # 封面色块
#         colors=['#8f3f71','#458588','#d79921','#689d6a','#cc241d']
#         ccolor=colors[hash(path)%len(colors)]
#         cover=tk.Frame(card,bg=ccolor,width=36,height=50); cover.pack(side='left',padx=6,pady=6); cover.pack_propagate(False)
#         tk.Label(cover,text='📖',font=('',14),bg=ccolor).pack(expand=True)
#         # 信息
#         info_f=tk.Frame(card,bg=bar); info_f.pack(side='left',fill='both',expand=True,pady=4)
#         tk.Label(info_f,text=info.get('title','未知'),font=('',9,'bold'),bg=bar,fg=fg,anchor='w').pack(fill='x')
#         lc=info.get('last_ch',0); tc=info.get('total_ch',1)
#         pct=int(lc/max(1,tc-1)*100) if tc>1 else 0
#         tk.Label(info_f,text=f'第{lc+1}/{tc}章  {pct}%',font=('',8),bg=bar,fg=sel,anchor='w').pack(fill='x')
#         # 进度条
#         pb_f=tk.Frame(info_f,bg=bar,height=4); pb_f.pack(fill='x',pady=2); pb_f.pack_propagate(False)
#         pb_done=tk.Frame(pb_f,bg=ccolor,height=4); pb_done.place(x=0,y=0,relwidth=pct/100,relheight=1)
#         tk.Frame(pb_f,bg=sel,height=4).place(x=0,y=0,relwidth=1,relheight=1)
#         pb_done.lift()
#         tk.Label(info_f,text=f'上次：{info.get("last_time","")}',font=('',7),bg=bar,fg=sel,anchor='w').pack(fill='x')
#         # 按钮
#         btn_f=tk.Frame(card,bg=bar); btn_f.pack(side='right',padx=6,pady=4)
#         def open_it(p=path):
#             shelf_win.destroy(); self.open_file(p)
#         def del_it(p=path):
#             if messagebox.askyesno('删除','从书架移除此书？',parent=shelf_win):
#                 del self.shelf[p]; _jsave(SHELF_FILE,self.shelf); refresh()
#         tk.Button(btn_f,text='阅读',font=('',8),relief='flat',bg=ccolor,fg='white',
#                   padx=6,command=open_it).pack(pady=2)
#         tk.Button(btn_f,text='移除',font=('',7),relief='flat',bg=bar,fg=sel,
#                   padx=4,command=del_it).pack(pady=2)

#     def _shelf_add(self, shelf_win):
#         path=filedialog.askopenfilename(title='选择书籍',
#             filetypes=[('小说文件','*.txt *.epub *.md'),('所有文件','*.*')])
#         if not path: return
#         if path not in self.shelf:
#             title=os.path.splitext(os.path.basename(path))[0]
#             self.shelf[path]={'title':title,'path':path,'last_ch':0,'total_ch':0,
#                               'last_time':'','added_time':datetime.datetime.now().strftime('%Y-%m-%d')}
#             _jsave(SHELF_FILE,self.shelf)
#         shelf_win.destroy(); self.open_shelf()

#     # ─────────────────────────────────────────────────
#     # 渲染章节
#     # ─────────────────────────────────────────────────
#     def _render_chapter(self, scroll_to_top=True):
#         if not self.chapters: return
#         self.cur_ch=max(0,min(self.cur_ch,len(self.chapters)-1))
#         ch=self.chapters[self.cur_ch]
#         self.txt.config(state='normal'); self.txt.delete('1.0','end')
#         self.txt.insert('1.0', ch['body']); self.txt.config(state='disabled')
#         if scroll_to_top: self.txt.yview_moveto(0.0)
#         self._update_nav(); self._wheel_accum=0
#         self._shelf_update()

#     def _update_nav(self):
#         n=len(self.chapters); idx=self.cur_ch+1
#         # 有无书签/笔记标记
#         m_chs={m['ch'] for m in self.marks.get(self.book_path,[])}
#         n_chs={n2['ch'] for n2 in self.notes.get(self.book_path,[])}
#         flags=('🔖' if self.cur_ch in m_chs else '')+('✏' if self.cur_ch in n_chs else '')
#         self.lbl_prog.config(text=f'{flags}  第{idx}/{n}章')
#         self.btn_prev.config(state='normal' if self.cur_ch>0   else 'disabled')
#         self.btn_next.config(state='normal' if self.cur_ch<n-1 else 'disabled')

#     def _on_yscroll(self,lo,hi): self.vsb.set(lo,hi)

#     # ─────────────────────────────────────────────────
#     # 翻章
#     # ─────────────────────────────────────────────────
#     def next_chapter(self):
#         if self.chapters and self.cur_ch<len(self.chapters)-1:
#             self.cur_ch+=1; self._render_chapter()

#     def prev_chapter(self):
#         if self.chapters and self.cur_ch>0:
#             self.cur_ch-=1; self._render_chapter()

#     def goto_chapter(self,idx):
#         if not self.chapters: return
#         self.cur_ch=max(0,min(idx,len(self.chapters)-1)); self._render_chapter()

#     def _on_click(self,e):
#         w=self.txt.winfo_width()
#         if   e.x<w*0.28: self.prev_chapter()
#         elif e.x>w*0.72: self.next_chapter()

#     def _on_wheel(self,e):
#         delta=1 if e.num==4 else (-1 if e.num==5 else (1 if e.delta>0 else -1))
#         top,bot=self.txt.yview()
#         if delta<0:
#             if bot>=0.999:
#                 self._wheel_accum-=1
#                 if self._wheel_accum<=-3: self.next_chapter(); return
#             else: self._wheel_accum=0; self.txt.yview_scroll(3,'units')
#         else:
#             if top<=0.001:
#                 self._wheel_accum+=1
#                 if self._wheel_accum>=3:
#                     self.prev_chapter(); self.root.after(30,lambda:self.txt.yview_moveto(1.0)); return
#             else: self._wheel_accum=0; self.txt.yview_scroll(-3,'units')

#     def _scroll_down(self):
#         _,bot=self.txt.yview()
#         if bot>=0.999: self.next_chapter()
#         else: self.txt.yview_scroll(1,'pages')

#     # ─────────────────────────────────────────────────
#     # TTS 听书
#     # ─────────────────────────────────────────────────
#     def toggle_tts(self):
#         if not self.tts.available:
#             messagebox.showinfo('提示','请先安装 pyttsx3：\npip install pyttsx3'); return
#         if self._tts_playing:
#             self.tts.stop(); self._tts_playing=False
#             self.btn_tts.config(text='🔊')
#             self._toast('⏹ 已停止朗读')
#         else:
#             if not self.chapters: return
#             ch=self.chapters[self.cur_ch]
#             self._tts_playing=True; self.btn_tts.config(text='⏸')
#             self._toast('▶ 开始朗读…')
#             def done(): self.root.after(0,self._tts_done)
#             self.tts.speak(ch['body'],on_done=done)

#     def _tts_done(self):
#         self._tts_playing=False; self.btn_tts.config(text='🔊')

#     # ─────────────────────────────────────────────────
#     # 书签（O 键）
#     # ─────────────────────────────────────────────────
#     def add_mark(self):
#         if not self.book_path: messagebox.showinfo('提示','请先打开书'); return
#         marks=self.marks.setdefault(self.book_path,[])
#         ch=self.chapters[self.cur_ch]; now=datetime.datetime.now().strftime('%m-%d %H:%M')
#         existing=next((m for m in marks if m['ch']==self.cur_ch),None)
#         entry={'ch':self.cur_ch,'ch_title':ch['title'],'time':now}
#         if existing: existing.update(entry); self._toast('🔖 书签已更新')
#         else: marks.append(entry); self._toast(f'🔖 书签已添加  第{self.cur_ch+1}章')
#         _jsave(MARKS_FILE,self.marks); self._update_nav()

#     def open_marks(self):
#         marks=self.marks.get(self.book_path,[])
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('书签'); win.geometry('300x360')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='🔖 书签列表',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
#         lf=tk.Frame(win,bg=bg); lf.pack(fill='both',expand=True,padx=4,pady=4)
#         sb2=tk.Scrollbar(lf); sb2.pack(side='right',fill='y')
#         lb=tk.Listbox(lf,font=('',10),relief='flat',bg=bg,fg=fg,selectbackground=sel,
#                       selectforeground=fg,borderwidth=0,highlightthickness=0,
#                       activestyle='none',yscrollcommand=sb2.set)
#         lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
#         rows=list(marks)
#         for m in rows: lb.insert('end',f"  🏴 第{m['ch']+1}章  {m['ch_title']}  {m['time']}")
#         bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=6,pady=4)
#         def jump():
#             idxs=lb.curselection()
#             if not idxs: return
#             win.destroy(); self.goto_chapter(rows[idxs[0]]['ch'])
#         def delete():
#             idxs=lb.curselection()
#             if not idxs: return
#             m=rows.pop(idxs[0]); lb.delete(idxs[0])
#             self.marks[self.book_path]=[x for x in self.marks.get(self.book_path,[]) if x is not m]
#             _jsave(MARKS_FILE,self.marks); self._update_nav()
#         tk.Button(bf,text='跳转',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=jump).pack(side='left',padx=4)
#         tk.Button(bf,text='删除',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=delete).pack(side='left')
#         lb.bind('<Double-Button-1>',lambda e:jump())
#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'300x360+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 笔记（N 键）
#     # ─────────────────────────────────────────────────
#     def add_note(self):
#         if not self.book_path: messagebox.showinfo('提示','请先打开书'); return
#         ch=self.chapters[self.cur_ch]
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('添加笔记'); win.geometry('340x260')
#         win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text=f'✏ 笔记 — {ch["title"][:20]}',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
#         # 选中文字自动填入
#         sel_text=''
#         try: sel_text=self.txt.get(tk.SEL_FIRST,tk.SEL_LAST)
#         except: pass
#         if sel_text:
#             tk.Label(win,text='引用文字：',font=('',8),bg=bg,fg=fg).pack(anchor='w',padx=8,pady=(6,0))
#             ref=tk.Label(win,text=sel_text[:80]+'…' if len(sel_text)>80 else sel_text,
#                         font=('',8,'italic'),bg=sel,fg=fg,wraplength=300,anchor='w',justify='left')
#             ref.pack(fill='x',padx=8,pady=2)
#         tk.Label(win,text='笔记内容：',font=('',8),bg=bg,fg=fg).pack(anchor='w',padx=8,pady=(6,0))
#         ta=tk.Text(win,height=6,font=('',10),bg=bg,fg=fg,insertbackground=fg,
#                    relief='flat',padx=8,pady=4,wrap='word',borderwidth=1,highlightthickness=1,
#                    highlightbackground=sel,highlightcolor=fg)
#         ta.pack(fill='both',expand=True,padx=8,pady=4); ta.focus()
#         def save():
#             content=ta.get('1.0','end').strip()
#             if not content: win.destroy(); return
#             notes=self.notes.setdefault(self.book_path,[])
#             now=datetime.datetime.now().strftime('%m-%d %H:%M')
#             notes.append({'ch':self.cur_ch,'ch_title':ch['title'],'content':content,
#                           'quote':sel_text,'time':now})
#             _jsave(NOTES_FILE,self.notes); self._update_nav(); win.destroy()
#             self._toast('✏ 笔记已保存')
#         bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=8,pady=4)
#         tk.Button(bf,text='保存笔记',font=('',9,'bold'),bg=bar,fg=fg,relief='flat',
#                   padx=10,command=save).pack(side='right',padx=4)
#         win.bind('<Control-Return>',lambda e:save())

#     def open_notes(self):
#         notes=self.notes.get(self.book_path,[])
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         win=tk.Toplevel(self.root); win.title('笔记'); win.geometry('360x480')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='✏ 笔记列表',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)

#         # 列表 + 详情
#         paned=tk.PanedWindow(win,orient='vertical',bg=bg,sashwidth=4,sashrelief='flat')
#         paned.pack(fill='both',expand=True,padx=4,pady=4)

#         top_f=tk.Frame(paned,bg=bg); paned.add(top_f,height=200)
#         sb2=tk.Scrollbar(top_f); sb2.pack(side='right',fill='y')
#         lb=tk.Listbox(top_f,font=('',9),relief='flat',bg=bg,fg=fg,selectbackground=sel,
#                       selectforeground=fg,borderwidth=0,highlightthickness=0,
#                       activestyle='none',yscrollcommand=sb2.set)
#         lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
#         rows=list(notes)
#         for n2 in rows: lb.insert('end',f"  第{n2['ch']+1}章  {n2['ch_title'][:16]}  {n2['time']}")

#         bot_f=tk.Frame(paned,bg=bg); paned.add(bot_f)
#         detail=tk.Text(bot_f,font=('',10),bg=bg,fg=fg,insertbackground=fg,
#                        relief='flat',padx=8,pady=6,wrap='word',state='disabled',
#                        borderwidth=0,highlightthickness=0)
#         detail.pack(fill='both',expand=True)

#         def show_detail(event=None):
#             idxs=lb.curselection()
#             if not idxs: return
#             n2=rows[idxs[0]]
#             detail.config(state='normal'); detail.delete('1.0','end')
#             if n2.get('quote'): detail.insert('end',f'引用：{n2["quote"]}\n\n','quote')
#             detail.insert('end',n2['content'])
#             detail.config(state='disabled')
#         lb.bind('<<ListboxSelect>>',show_detail)

#         bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=6,pady=4)
#         def jump():
#             idxs=lb.curselection()
#             if not idxs: return
#             win.destroy(); self.goto_chapter(rows[idxs[0]]['ch'])
#         def delete():
#             idxs=lb.curselection()
#             if not idxs: return
#             n2=rows.pop(idxs[0]); lb.delete(idxs[0])
#             self.notes[self.book_path]=[x for x in self.notes.get(self.book_path,[]) if x is not n2]
#             _jsave(NOTES_FILE,self.notes); self._update_nav()
#             detail.config(state='normal'); detail.delete('1.0','end'); detail.config(state='disabled')
#         tk.Button(bf,text='跳转章节',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=jump).pack(side='left',padx=4)
#         tk.Button(bf,text='删除笔记',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=delete).pack(side='left')
#         lb.bind('<Double-Button-1>',lambda e:jump())
#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'360x480+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 章节目录
#     # ─────────────────────────────────────────────────
#     def open_chapters(self):
#         if not self.chapters: messagebox.showinfo('提示','请先打开小说'); return
#         t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
#         mark_set={m['ch'] for m in self.marks.get(self.book_path,[])}
#         note_set={n2['ch'] for n2 in self.notes.get(self.book_path,[])}
#         win=tk.Toplevel(self.root); win.title('章节目录'); win.geometry('300x500')
#         win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
#         hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
#         tk.Label(hdr,text='📑 章节目录',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
#         tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
#         sf=tk.Frame(win,bg=bg); sf.pack(fill='x',padx=6,pady=(6,2))
#         sv=tk.StringVar()
#         se=tk.Entry(sf,textvariable=sv,font=('',9),bg=bg,fg=fg,insertbackground=fg,relief='groove')
#         se.pack(fill='x',ipady=3)
#         PH='搜索章节名...'
#         se.insert(0,PH); se.config(fg='gray')
#         se.bind('<FocusIn>',lambda e:(se.delete(0,'end'),se.config(fg=fg)) if se.get()==PH else None)
#         se.bind('<FocusOut>',lambda e:(se.insert(0,PH),se.config(fg='gray')) if not se.get() else None)
#         lf=tk.Frame(win,bg=bg); lf.pack(fill='both',expand=True,padx=4,pady=4)
#         sb2=tk.Scrollbar(lf); sb2.pack(side='right',fill='y')
#         lb=tk.Listbox(lf,font=('',10),relief='flat',bg=bg,fg=fg,selectbackground=sel,
#                       selectforeground=fg,borderwidth=0,highlightthickness=0,
#                       activestyle='none',yscrollcommand=sb2.set)
#         lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
#         btn_j=tk.Button(win,text='↩ 跳转',font=('',9,'bold'),bg=bar,fg=fg,relief='flat',pady=5)
#         btn_j.pack(fill='x',padx=6,pady=4)
#         all_ch=list(self.chapters); visible=list(range(len(all_ch)))
#         def fill(indices):
#             visible.clear(); visible.extend(indices); lb.delete(0,'end')
#             for i in indices:
#                 flags=('🔖' if i in mark_set else '')+('✏' if i in note_set else '')
#                 cur='▶ ' if i==self.cur_ch else '  '
#                 lb.insert('end',f'{cur}{i+1}. {all_ch[i]["title"]}{flags}')
#         fill(range(len(all_ch)))
#         try: lb.see(self.cur_ch); lb.selection_set(self.cur_ch)
#         except: pass
#         def on_search(*_):
#             q=sv.get().strip()
#             fill(range(len(all_ch))) if q in ('',PH) else fill([i for i,c in enumerate(all_ch) if q in c['title']])
#         sv.trace_add('write',on_search)
#         def jump(e=None):
#             idxs=lb.curselection()
#             if not idxs: return
#             win.destroy(); self.goto_chapter(visible[idxs[0]])
#         btn_j.config(command=jump); lb.bind('<Double-Button-1>',jump); lb.bind('<Return>',jump)
#         rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
#         win.geometry(f'300x500+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # Toast 提示
#     # ─────────────────────────────────────────────────
#     def _toast(self,msg,ms=1500):
#         t=self._cur_theme()
#         try:
#             for w in self.root.winfo_children():
#                 if isinstance(w,tk.Label) and getattr(w,'_is_toast',False): w.destroy()
#         except: pass
#         toast=tk.Label(self.root,text=msg,font=('',8),bg=t['bar'],fg=t['fg'],
#                        padx=10,pady=4,relief='flat')
#         toast._is_toast=True
#         toast.place(relx=0.5,rely=0.06,anchor='n')
#         self.root.after(ms,lambda: (toast.winfo_exists() and toast.destroy()))

#     # ─────────────────────────────────────────────────
#     # 欢迎页
#     # ─────────────────────────────────────────────────
#     def _show_welcome(self):
#         self.txt.config(state='normal'); self.txt.delete('1.0','end')
#         self.txt.insert('1.0',(
#             '\n\n\n'
#             '        📚  摸鱼阅读器  v8\n\n'
#             '  支持：TXT  /  EPUB  /  MD\n\n'
#             '  顶部按钮：书架  目录  笔记  书签  打开\n\n'
#             '  操作：\n'
#             '    滚轮 / 拖拽右侧滚动条  章内滚动\n'
#             '    滚到章末再滚           切下一章\n'
#             '    点击左侧 28% / 右侧    切上下章\n'
#             '    ← →  切章   S/↓  翻屏\n\n'
#             '  快捷键：\n'
#             '    O        添加书签\n'
#             '    N        添加笔记\n'
#             '    F5       开始/停止朗读\n'
#             '    D+E      最小化\n'
#         ))
#         self.txt.config(state='disabled')

#     # ─────────────────────────────────────────────────
#     # 最小化
#     # ─────────────────────────────────────────────────
#     def toggle_minimize(self):
#         self._minimized=not self._minimized
#         if self._minimized:
#             self._saved_h=self.root.winfo_height()
#             for w in (self.setbar,self.sep,self.txt_frame,self.bot_area): w.pack_forget()
#             self.root.geometry(f'{self.root.winfo_width()}x30')
#         else:
#             self.root.geometry(f'{self.root.winfo_width()}x{self._saved_h}')
#             self.sep.pack(fill='x',after=self.topbar)
#             if self._settings_open: self.setbar.pack(fill='x',after=self.topbar); self._retheme_setbar()
#             self.txt_frame.pack(fill='both',expand=True)
#             self.bot_area.pack(fill='x',side='bottom')

#     def toggle_settings(self):
#         self._settings_open=not self._settings_open
#         if self._settings_open: self.setbar.pack(fill='x',after=self.topbar); self._retheme_setbar()
#         else: self.setbar.pack_forget()

#     # ─────────────────────────────────────────────────
#     # 全文搜索（Ctrl+F）
#     # ─────────────────────────────────────────────────
#     def open_search(self):
#         if not self.chapters:
#             messagebox.showinfo('提示', '请先打开小说'); return

#         t = self._cur_theme()
#         bg, fg, bar, sel = t['bg'], t['fg'], t['bar'], t['sel']

#         # 若搜索窗已存在则聚焦
#         if hasattr(self, '_search_win') and self._search_win.winfo_exists():
#             self._search_win.lift(); self._search_win.focus_force(); return

#         win = tk.Toplevel(self.root)
#         win.title('全文搜索')
#         win.geometry('480x560')
#         win.resizable(True, True)
#         win.attributes('-topmost', True)
#         win.configure(bg=bg)
#         self._search_win = win

#         # ── 顶部搜索框 ────────────────────────────────
#         top = tk.Frame(win, bg=bar); top.pack(fill='x', padx=0, pady=0)
#         tk.Label(top, text='🔍', font=('',11), bg=bar, fg=fg).pack(side='left', padx=8, pady=6)

#         sv = tk.StringVar()
#         entry = tk.Entry(top, textvariable=sv, font=('',11), bg=bg, fg=fg,
#                          insertbackground=fg, relief='flat', bd=0)
#         entry.pack(side='left', fill='x', expand=True, ipady=4)

#         # 大小写 / 正则 选项
#         var_case  = tk.BooleanVar(value=False)
#         var_regex = tk.BooleanVar(value=False)
#         tk.Checkbutton(top, text='Aa', variable=var_case, font=('',8),
#                        bg=bar, fg=fg, activebackground=bar,
#                        selectcolor=bg).pack(side='left', padx=2)
#         tk.Checkbutton(top, text='.*', variable=var_regex, font=('',8),
#                        bg=bar, fg=fg, activebackground=bar,
#                        selectcolor=bg).pack(side='left', padx=2)

#         lbl_count = tk.Label(top, text='', font=('',8), bg=bar, fg=sel)
#         lbl_count.pack(side='left', padx=6)
#         tk.Button(top, text='×', relief='flat', font=('',10),
#                   bg=bar, fg=fg, command=win.destroy).pack(side='right', padx=6)

#         sep2 = tk.Frame(win, height=1, bg=sel); sep2.pack(fill='x')

#         # ── 结果列表 ──────────────────────────────────
#         list_frame = tk.Frame(win, bg=bg); list_frame.pack(fill='both', expand=True)
#         sb2 = tk.Scrollbar(list_frame); sb2.pack(side='right', fill='y')
#         lb = tk.Listbox(list_frame, font=('',9), relief='flat', bg=bg, fg=fg,
#                         selectbackground=sel, selectforeground=fg,
#                         borderwidth=0, highlightthickness=0,
#                         activestyle='none', yscrollcommand=sb2.set)
#         lb.pack(fill='both', expand=True); sb2.config(command=lb.yview)

#         # ── 预览区 ────────────────────────────────────
#         sep3 = tk.Frame(win, height=1, bg=sel); sep3.pack(fill='x')
#         preview_frame = tk.Frame(win, bg=bg, height=130)
#         preview_frame.pack(fill='x', padx=0); preview_frame.pack_propagate(False)

#         preview = tk.Text(preview_frame, font=('',9), bg=bg, fg=fg,
#                           relief='flat', padx=12, pady=6, wrap='word',
#                           state='disabled', borderwidth=0, highlightthickness=0)
#         preview.pack(fill='both', expand=True)
#         preview.tag_config('hit',  background='#d79921', foreground='#1d2021')
#         preview.tag_config('info', foreground=sel)

#         # 底部跳转栏
#         bot_f = tk.Frame(win, bg=bar, height=30)
#         bot_f.pack(fill='x'); bot_f.pack_propagate(False)
#         lbl_loc = tk.Label(bot_f, text='', font=('',8), bg=bar, fg=fg)
#         lbl_loc.pack(side='left', padx=8, pady=4)
#         btn_jump = tk.Button(bot_f, text='↩ 跳转到此处', font=('',8,'bold'),
#                              bg=bar, fg=fg, relief='flat', padx=8,
#                              state='disabled')
#         btn_jump.pack(side='right', padx=8, pady=3)

#         # ── 搜索逻辑 ──────────────────────────────────
#         results = []   # [(ch_idx, start_in_body, end_in_body, snippet)]

#         def do_search(*_):
#             results.clear(); lb.delete(0, 'end')
#             query = sv.get().strip()
#             if not query:
#                 lbl_count.config(text=''); return

#             flags = 0 if var_case.get() else re.IGNORECASE
#             try:
#                 if var_regex.get():
#                     pat = re.compile(query, flags)
#                 else:
#                     pat = re.compile(re.escape(query), flags)
#             except re.error as e:
#                 lbl_count.config(text=f'正则错误: {e}'); return

#             CONTEXT = 40   # 匹配前后各取多少字符
#             for ci, ch in enumerate(self.chapters):
#                 for m in pat.finditer(ch['body']):
#                     s, e2 = m.start(), m.end()
#                     pre  = ch['body'][max(0, s-CONTEXT):s].replace('\n', ' ')
#                     hit  = ch['body'][s:e2]
#                     post = ch['body'][e2:min(len(ch['body']), e2+CONTEXT)].replace('\n', ' ')
#                     snippet = (pre, hit, post)
#                     results.append((ci, s, e2, snippet))

#             lbl_count.config(text=f'共 {len(results)} 处')
#             for ci, s, e2, (pre, hit, post) in results:
#                 ch_title = self.chapters[ci]['title']
#                 display  = f"  第{ci+1}章  {ch_title[:14]}…  「{hit[:20]}」"
#                 lb.insert('end', display)

#             # 清空预览
#             preview.config(state='normal'); preview.delete('1.0','end')
#             preview.config(state='disabled')
#             lbl_loc.config(text='')
#             btn_jump.config(state='disabled')

#         sv.trace_add('write', do_search)
#         var_case.trace_add('write',  do_search)
#         var_regex.trace_add('write', do_search)

#         def on_select(event=None):
#             idxs = lb.curselection()
#             if not idxs: return
#             ci, s, e2, (pre, hit, post) = results[idxs[0]]
#             ch = self.chapters[ci]

#             # 更新预览
#             preview.config(state='normal'); preview.delete('1.0','end')
#             preview.insert('end', f'第{ci+1}章  {ch["title"]}\n', 'info')
#             preview.insert('end', '…' + pre)
#             preview.insert('end', hit, 'hit')
#             preview.insert('end', post + '…')
#             preview.config(state='disabled')

#             lbl_loc.config(text=f'第{ci+1}章 · 位置 {s}')
#             btn_jump.config(state='normal',
#                             command=lambda: _jump(ci, s, e2, hit))

#         def _jump(ci, s, e2, hit):
#             # 跳转到章节，并高亮匹配文字
#             self.goto_chapter(ci)
#             win.lift()
#             # 在 txt 里找到并高亮
#             self.root.after(80, lambda: _highlight_in_txt(hit))

#         def _highlight_in_txt(hit):
#             self.txt.tag_remove('search_hit', '1.0', 'end')
#             self.txt.tag_config('search_hit', background='#d79921', foreground='#1d2021')
#             start = '1.0'
#             while True:
#                 pos = self.txt.search(hit, start, nocase=not var_case.get(), stopindex='end')
#                 if not pos: break
#                 end_pos = f'{pos}+{len(hit)}c'
#                 self.txt.tag_add('search_hit', pos, end_pos)
#                 self.txt.see(pos)
#                 start = end_pos

#         lb.bind('<<ListboxSelect>>', on_select)
#         lb.bind('<Double-Button-1>', lambda e: btn_jump.invoke())
#         lb.bind('<Return>',         lambda e: btn_jump.invoke())

#         entry.focus()
#         # 如果有选中文字，自动填入搜索框
#         try:
#             sel_text = self.txt.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
#             if sel_text and '\n' not in sel_text:
#                 sv.set(sel_text)
#         except: pass

#         rx = self.root.winfo_x() + self.root.winfo_width() + 8
#         ry = self.root.winfo_y()
#         win.geometry(f'480x560+{rx}+{ry}')

#     # ─────────────────────────────────────────────────
#     # 章节摘要（Ctrl+M）—— 调用智谱 GLM API
#     # ─────────────────────────────────────────────────
#     def open_summary(self):
#         """章节摘要窗口 —— 调用智谱 GLM，简洁核心风格"""
#         if not self.chapters:
#             messagebox.showinfo('提示', '请先打开小说'); return

#         # 所有共享状态封装进 State，彻底避免闭包变量遮蔽
#         class State:
#             ch_body  = self.chapters[self.cur_ch]['body']
#             ch_title = self.chapters[self.cur_ch]['title']
#             ch_idx   = self.cur_ch
#             result   = ''
#             running  = False

#         st = State()
#         _t  = self._cur_theme()
#         _bg, _fg, _bar, _sel = _t['bg'], _t['fg'], _t['bar'], _t['sel']

#         # ── 窗口 ──────────────────────────────────────
#         dlg = tk.Toplevel(self.root)
#         dlg.title('章节摘要')
#         dlg.geometry('460x500')
#         dlg.resizable(True, True)
#         dlg.attributes('-topmost', True)
#         dlg.configure(bg=_bg)

#         # ── 顶部：章节信息 ────────────────────────────
#         info_bar = tk.Frame(dlg, bg=_bar, height=36)
#         info_bar.pack(fill='x')
#         info_bar.pack_propagate(False)

#         _char_count = len(st.ch_body)
#         _para_count = len([p for p in st.ch_body.split('\n') if p.strip()])
#         tk.Label(info_bar,
#                  text=f'  📖  {st.ch_title}',
#                  font=('', 9, 'bold'), bg=_bar, fg=_fg,
#                  anchor='w').pack(side='left', fill='x', expand=True, padx=6, pady=8)
#         tk.Label(info_bar,
#                  text=f'{_char_count} 字  {_para_count} 段  ',
#                  font=('', 8), bg=_bar, fg=_sel).pack(side='right', padx=6)
#         tk.Button(info_bar, text='×', relief='flat', font=('', 11),
#                   bg=_bar, fg=_fg, bd=0,
#                   command=dlg.destroy).pack(side='right', padx=4)

#         tk.Frame(dlg, height=1, bg=_sel).pack(fill='x')

#         # ── 摘要展示区 ────────────────────────────────
#         out_frame = tk.Frame(dlg, bg=_bg)
#         out_frame.pack(fill='both', expand=True, padx=0, pady=0)

#         _vsb = tk.Scrollbar(out_frame, width=6)
#         _vsb.pack(side='right', fill='y')

#         out = tk.Text(out_frame,
#                       font=(self.font_fam, self.font_size + 1),
#                       bg=_bg, fg=_fg,
#                       insertbackground=_fg,
#                       selectbackground=_sel,
#                       relief='flat', padx=20, pady=16,
#                       wrap='word',
#                       borderwidth=0, highlightthickness=0,
#                       state='disabled',
#                       yscrollcommand=_vsb.set,
#                       spacing1=4, spacing3=4)
#         out.pack(side='left', fill='both', expand=True)
#         _vsb.config(command=out.yview)

#         # 文字样式标签
#         out.tag_config('hint',    foreground=_sel, font=(self.font_fam, self.font_size))
#         out.tag_config('warn',    foreground='#cc241d', font=(self.font_fam, self.font_size))
#         out.tag_config('result',  foreground=_fg, font=(self.font_fam, self.font_size + 1),
#                        spacing1=6, spacing3=6)
#         out.tag_config('loading', foreground=_sel,
#                        font=(self.font_fam, self.font_size, 'italic'))

#         tk.Frame(dlg, height=1, bg=_sel).pack(fill='x')

#         # ── 底部操作区 ────────────────────────────────
#         btn_bar = tk.Frame(dlg, bg=_bar, height=52)
#         btn_bar.pack(fill='x', side='bottom')
#         btn_bar.pack_propagate(False)

#         # 主按钮（大、居中、醒目）
#         btn_generate = tk.Button(
#             btn_bar,
#             text='▶  开始生成摘要',
#             font=('', 11, 'bold'),
#             bg=_fg, fg=_bg,
#             activebackground=_sel, activeforeground=_fg,
#             relief='flat', bd=0,
#             padx=20, pady=6,
#             cursor='hand2',
#         )
#         btn_generate.pack(side='left', padx=14, pady=10)

#         # 副按钮
#         btn_copy = tk.Button(btn_bar, text='复制', font=('', 9),
#                              bg=_bar, fg=_fg, relief='flat', padx=8,
#                              state='disabled', cursor='hand2')
#         btn_copy.pack(side='left', padx=4, pady=10)

#         btn_note = tk.Button(btn_bar, text='存为笔记', font=('', 9),
#                              bg=_bar, fg=_fg, relief='flat', padx=8,
#                              state='disabled', cursor='hand2')
#         btn_note.pack(side='left', padx=4, pady=10)

#         lbl_status = tk.Label(btn_bar, text='', font=('', 8),
#                               bg=_bar, fg=_sel)
#         lbl_status.pack(side='right', padx=14)

#         # ── 内部函数 ──────────────────────────────────
#         def _show(text, tag='result'):
#             out.config(state='normal')
#             out.delete('1.0', 'end')
#             out.insert('end', text, tag)
#             out.config(state='disabled')
#             out.yview_moveto(0.0)

#         def _on_success(text):
#             st.result  = text
#             st.running = False
#             _show(text, 'result')
#             btn_generate.config(state='normal', text='↺  重新生成')
#             btn_copy.config(state='normal')
#             btn_note.config(state='normal')
#             lbl_status.config(text=f'已生成  {len(text)} 字')

#         def _on_error(msg):
#             st.running = False
#             btn_generate.config(state='normal', text='▶  开始生成摘要')
#             if msg == 'NO_KEY':
#                 _show(
#                     '⚠  未找到 API Key\n\n'
#                     '请在程序同目录新建文件：api_key.txt\n'
#                     '将智谱 API Key 粘贴进去保存即可。\n\n'
#                     '申请地址：https://open.bigmodel.cn\n'
#                     '（注册后在"API Keys"页面创建，新用户有免费额度）',
#                     'warn'
#                 )
#             else:
#                 _show(f'⚠  生成失败\n\n{msg}', 'warn')

#         def _do_generate():
#             if st.running: return
#             st.running = True
#             btn_generate.config(state='disabled', text='生成中…')
#             btn_copy.config(state='disabled')
#             btn_note.config(state='disabled')
#             lbl_status.config(text='')
#             _show('正在调用智谱 GLM-4-Flash，请稍候…', 'loading')

#             def worker():
#                 import urllib.request as _ureq
#                 import urllib.error   as _uerr
#                 import json           as _ujson

#                 _key = _inject_api_key()
#                 if not _key:
#                     dlg.after(0, lambda: _on_error('NO_KEY'))
#                     return

#                 # Prompt：简短抓核心
#                 _body_clip = st.ch_body[:5000]
#                 _prompt = (
#                     f"请用100字以内对以下小说章节做简短摘要，"
#                     f"只需抓住：核心人物、关键事件、重要转折。"
#                     f"直接输出摘要，不要标题和前缀。\n\n"
#                     f"【{st.ch_title}】\n{_body_clip}"
#                 )

#                 _payload = _ujson.dumps({
#                     'model':       'glm-4-flash',
#                     'max_tokens':  300,
#                     'temperature': 0.5,
#                     'messages':    [{'role': 'user', 'content': _prompt}],
#                 }).encode('utf-8')

#                 _req = _ureq.Request(
#                     'https://open.bigmodel.cn/api/paas/v4/chat/completions',
#                     data    = _payload,
#                     headers = {
#                         'Content-Type':  'application/json',
#                         'Authorization': f'Bearer {_key}',
#                     },
#                     method = 'POST',
#                 )
#                 try:
#                     with _ureq.urlopen(_req, timeout=30) as _resp:
#                         _raw    = _resp.read().decode('utf-8')
#                         _parsed = _ujson.loads(_raw)
#                         _text   = _parsed['choices'][0]['message']['content'].strip()
#                     dlg.after(0, lambda t=_text: _on_success(t))
#                 except _uerr.HTTPError as _he:
#                     _hbody = _he.read().decode('utf-8', errors='replace')
#                     try:
#                         _hemsg = _ujson.loads(_hbody).get('error', {}).get('message', _hbody)
#                     except Exception:
#                         _hemsg = _hbody[:200]
#                     _hcode = str(_he.code)
#                     dlg.after(0, lambda c=_hcode, m=_hemsg: _on_error(f'HTTP {c}：{m}'))
#                 except Exception as _exc:
#                     _emsg = str(_exc)
#                     dlg.after(0, lambda m=_emsg: _on_error(m))

#             threading.Thread(target=worker, daemon=True).start()

#         def _do_copy():
#             if not st.result: return
#             dlg.clipboard_clear()
#             dlg.clipboard_append(st.result)
#             lbl_status.config(text='已复制 ✓')
#             dlg.after(1800, lambda: lbl_status.config(text=f'已生成  {len(st.result)} 字'))

#         def _do_save_note():
#             if not st.result: return
#             _note_list = self.notes.setdefault(self.book_path, [])
#             _note_list.append({
#                 'ch':       st.ch_idx,
#                 'ch_title': st.ch_title,
#                 'content':  f'[AI摘要]\n{st.result}',
#                 'quote':    '',
#                 'time':     datetime.datetime.now().strftime('%m-%d %H:%M'),
#             })
#             _jsave(NOTES_FILE, self.notes)
#             self._update_nav()
#             self._toast('✏ 摘要已存为笔记')
#             lbl_status.config(text='已保存为笔记 ✓')

#         btn_generate.config(command=_do_generate)
#         btn_copy.config(command=_do_copy)
#         btn_note.config(command=_do_save_note)

#         # 初始提示文字
#         _has_key  = bool(_inject_api_key())
#         _key_hint = (
#             '\n\n💡 首次使用请在程序目录新建 api_key.txt\n   填入您的智谱 API Key 后重新打开摘要。'
#             if not _has_key else ''
#         )
#         _show(
#             f'点击下方「▶ 开始生成摘要」按钮，\n'
#             f'AI 将用 100 字内概括本章核心内容。'
#             f'{_key_hint}',
#             'hint'
#         )

#         # 定位弹窗
#         _rx = self.root.winfo_x() + self.root.winfo_width() + 10
#         _ry = self.root.winfo_y()
#         dlg.geometry(f'460x500+{_rx}+{_ry}')


#     # ─────────────────────────────────────────────────
#     # 关闭时保存
#     # ─────────────────────────────────────────────────
#     def _on_close(self):
#         self.tts.stop()
#         self._shelf_update()
#         self.root.destroy()

#     # ─────────────────────────────────────────────────
#     # 快捷键
#     # ─────────────────────────────────────────────────
#     def _bind_keys(self):
#         r=self.root
#         r.bind('<KeyPress-s>',   lambda e: self._scroll_down())
#         r.bind('<KeyPress-S>',   lambda e: self._scroll_down())
#         r.bind('<Right>',        lambda e: self.next_chapter())
#         r.bind('<Left>',         lambda e: self.prev_chapter())
#         r.bind('<Down>',         lambda e: self._scroll_down())
#         r.bind('<Up>',           lambda e: self.txt.yview_scroll(-3,'units'))
#         r.bind('<KeyPress-o>',   lambda e: self.add_mark())
#         r.bind('<KeyPress-O>',   lambda e: self.add_mark())
#         r.bind('<KeyPress-n>',   lambda e: self.add_note())
#         r.bind('<KeyPress-N>',   lambda e: self.add_note())
#         r.bind('<F5>',           lambda e: self.toggle_tts())
#         r.bind('<Control-f>',    lambda e: self.open_search())
#         r.bind('<Control-F>',    lambda e: self.open_search())
#         r.bind('<Control-m>',    lambda e: self.open_summary())
#         r.bind('<Control-M>',    lambda e: self.open_summary())
#         r.bind('<KeyPress-d>',   self._dp)
#         r.bind('<KeyPress-D>',   self._dp)
#         r.bind('<KeyRelease-d>', self._dr)
#         r.bind('<KeyRelease-D>', self._dr)
#         r.bind('<KeyPress-e>',   self._ep)
#         r.bind('<KeyPress-E>',   self._ep)
#         r.focus_set()

#     def _dp(self,e): self._d_held=True
#     def _dr(self,e): self._d_held=False
#     def _ep(self,e):
#         if self._d_held: self.toggle_minimize()


# # ══════════════════════════════════════════════════════════════
# if __name__ == '__main__':
#     try:
#         from ctypes import windll
#         windll.shcore.SetProcessDpiAwareness(1)
#     except: pass
#     App()

"""
摸鱼阅读器 v8.0  —  全功能版
功能：
  阅读体验：章节滚动、翻页、字号/行距/字色/背景/护眼模式、透明度、屏幕取色
  书架管理：添加/删除/重命名书籍、显示封面/进度/上次阅读时间
  阅读进度：自动记录、书架显示进度条
  笔记系统：N键在当前章节创建笔记、查看/编辑/删除笔记
  书签系统：O键快速书签、书签列表跳转删除
  听书TTS ：F5启动/停止，支持语速调整（需系统 pyttsx3 或 espeak）
  竖向拖拽滚动条、目录跳转、搜索

运行：python novel_reader.py
依赖：pip install pyttsx3   （TTS，可选）
      pip install pillow     （屏幕取色，可选）
"""

import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox, scrolledtext
import os, re, zipfile, sys, json, copy, threading, time, datetime
from html.parser import HTMLParser


# ══════════════════════════════════════════════════════════════
# HTML → 纯文本
# ══════════════════════════════════════════════════════════════
class _H2T(HTMLParser):
    SKIP  = {'script','style','head','meta','link'}
    BLOCK = {'p','div','br','h1','h2','h3','h4','h5',
             'h6','li','tr','td','th','section','article'}
    def __init__(self): super().__init__(); self.out, self._s = [], 0
    def handle_starttag(self, tag, _):
        if tag in self.SKIP:  self._s += 1
        if tag in self.BLOCK: self.out.append('\n')
    def handle_endtag(self, tag):
        if tag in self.SKIP:  self._s = max(0, self._s-1)
        if tag in self.BLOCK: self.out.append('\n')
    def handle_data(self, d):
        if not self._s: self.out.append(d)
    def text(self): return re.sub(r'\n{3,}','\n\n',''.join(self.out)).strip()

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
                        opf = el.get('full-path',''); odir = opf.rsplit('/',1)[0] if '/' in opf else ''; break
            items, spine = {}, []
            if opf and opf in ns:
                root = ET.fromstring(z.read(opf))
                for el in root.iter():
                    tag = el.tag.split('}')[-1]
                    if tag == 'item':
                        mid,href,mt = el.get('id',''),el.get('href',''),el.get('media-type','')
                        if href and ('html' in mt or href.endswith(('.html','.xhtml','.htm'))):
                            items[mid] = (odir+'/'+href).lstrip('/') if odir else href
                    elif tag == 'itemref':
                        r = el.get('idref','')
                        if r in items: spine.append(items[r])
                    elif tag == 'title' and el.text: title = el.text
            if not spine:
                spine = sorted(f for f in ns if re.search(r'\.(html|htm|xhtml)$',f,re.I)
                               and 'toc' not in f.lower() and 'nav' not in f.lower())
            for href in spine:
                if href in ns:
                    try: body += html2text(z.read(href).decode('utf-8','replace')) + '\n\n'
                    except: pass
    except Exception as e: body = f'[EPUB解析失败: {e}]'
    return title, body.strip()


# ══════════════════════════════════════════════════════════════
# 章节切割
# ══════════════════════════════════════════════════════════════
_CH = re.compile(
    r'^(第\s*[零一二三四五六七八九十百千万\d〇]+\s*[章节卷集回部篇][^\n]{0,40}'
    r'|Chapter\s*\d+[^\n]{0,40}|CHAPTER\s*\d+[^\n]{0,40}|【[^\n]{1,30}】)', re.I)

def split_chapters(text):
    bounds = []
    for m in re.finditer(r'^.+$', text, re.M):
        line = m.group().strip()
        if line and _CH.match(line): bounds.append((m.start(), line))
    if not bounds: return [{'title':'全文','body':text}]
    chs = []
    for i,(pos,title) in enumerate(bounds):
        end = bounds[i+1][0] if i+1<len(bounds) else len(text)
        chs.append({'title':title,'body':text[pos:end]})
    return chs


# ══════════════════════════════════════════════════════════════
# 数据存储
# ══════════════════════════════════════════════════════════════
DATA_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.moyu_data')
os.makedirs(DATA_DIR, exist_ok=True)
SHELF_FILE = os.path.join(DATA_DIR, 'shelf.json')
NOTES_FILE = os.path.join(DATA_DIR, 'notes.json')
MARKS_FILE = os.path.join(DATA_DIR, 'marks.json')

def _jload(f):
    try:
        with open(f, encoding='utf-8') as fp: return json.load(fp)
    except: return {}

def _jsave(f, d):
    try:
        with open(f, 'w', encoding='utf-8') as fp: json.dump(d, fp, ensure_ascii=False, indent=2)
    except: pass

def _inject_api_key():
    """
    从程序目录的 api_key.txt 自动读取智谱 API Key。
    用户把 Key 粘贴进 api_key.txt 即可，无需手动配置环境变量。
    返回 key 字符串，失败返回空字符串。
    """
    key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_key.txt')
    if os.path.exists(key_file):
        try:
            key = open(key_file, encoding='utf-8').read().strip()
            if key:
                os.environ['ZHIPU_API_KEY'] = key
                return key
        except: pass
    return os.environ.get('ZHIPU_API_KEY', '')


# ══════════════════════════════════════════════════════════════
# TTS 引擎（可选）
# ══════════════════════════════════════════════════════════════
class TTS:
    def __init__(self):
        self._engine = None
        self._thread = None
        self._stop   = threading.Event()
        self._text   = ''
        self._rate   = 180
        self._avail  = False
        self._init()

    def _init(self):
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._avail  = True
        except:
            self._avail = False

    @property
    def available(self): return self._avail

    def set_rate(self, rate):
        self._rate = int(rate)
        if self._engine:
            try: self._engine.setProperty('rate', self._rate)
            except: pass

    def speak(self, text, on_done=None):
        if not self._avail: return
        self.stop()
        self._stop.clear()
        self._text = text

        def run():
            try:
                import pyttsx3
                eng = pyttsx3.init()
                eng.setProperty('rate', self._rate)
                # 逐段朗读，支持中途停止
                paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
                for para in paragraphs:
                    if self._stop.is_set(): break
                    eng.say(para)
                    eng.runAndWait()
                eng.stop()
            except: pass
            if on_done: on_done()

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._engine:
            try: self._engine.stop()
            except: pass


# ══════════════════════════════════════════════════════════════
# 屏幕取色器
# ══════════════════════════════════════════════════════════════
def screen_color_picker(callback):
    try: from PIL import ImageGrab
    except ImportError:
        c = colorchooser.askcolor(title='选择颜色')
        if c and c[1]: callback(c[1])
        return
    from PIL import ImageGrab, Image, ImageTk
    ZOOM,HALF = 10,5; CS = (HALF*2+1)*ZOOM
    preview = tk.Toplevel(); preview.overrideredirect(True)
    preview.attributes('-topmost',True); preview.configure(bg='#1a1a1a')
    preview.geometry(f'{CS+4}x{CS+28}+200+200')
    canvas = tk.Canvas(preview,width=CS,height=CS,bg='#000',highlightthickness=1,
                       highlightbackground='#555',cursor='none')
    canvas.pack(padx=2,pady=(2,0))
    lbl = tk.Label(preview,text='#000000',font=('Consolas',9,'bold'),bg='#1a1a1a',fg='white',pady=1)
    lbl.pack()
    cur,ph,aid,done = ['#000000'],[None],[None],[False]
    def update():
        if done[0]: return
        try:
            mx,my = preview.winfo_pointerx(),preview.winfo_pointery()
            img = ImageGrab.grab(bbox=(mx-HALF,my-HALF,mx+HALF+1,my+HALF+1))
            zoomed = img.resize((CS,CS),Image.NEAREST); ph[0]=ImageTk.PhotoImage(zoomed)
            canvas.delete('all'); canvas.create_image(0,0,anchor='nw',image=ph[0])
            c2=CS//2
            canvas.create_line(c2,0,c2,CS,fill='white',width=1)
            canvas.create_line(0,c2,CS,c2,fill='white',width=1)
            canvas.create_rectangle(c2-ZOOM,c2-ZOOM,c2+ZOOM,c2+ZOOM,outline='white',width=2)
            px=img.getpixel((HALF,HALF)); hx='#{:02x}{:02x}{:02x}'.format(px[0],px[1],px[2])
            cur[0]=hx; lbl.config(text=hx)
            sw,sh=preview.winfo_screenwidth(),preview.winfo_screenheight()
            ox,oy=mx+18,my+18
            if ox+CS+10>sw: ox=mx-CS-22
            if oy+CS+32>sh: oy=my-CS-34
            preview.geometry(f'+{ox}+{oy}')
        except: pass
        aid[0]=preview.after(40,update)
    def finish():
        done[0]=True
        if aid[0]:
            try: preview.after_cancel(aid[0])
            except: pass
        for w in (overlay,preview):
            try: w.destroy()
            except: pass
    overlay = tk.Toplevel(); overlay.overrideredirect(True)
    overlay.attributes('-topmost',True); overlay.attributes('-alpha',0.01)
    sw,sh=overlay.winfo_screenwidth(),overlay.winfo_screenheight()
    overlay.geometry(f'{sw}x{sh}+0+0'); overlay.configure(bg='white',cursor='crosshair')
    overlay.bind('<Button-1>',lambda e:(finish(),callback(cur[0])))
    overlay.bind('<Escape>',lambda e:finish())
    overlay.focus_force(); aid[0]=preview.after(40,update)


# ══════════════════════════════════════════════════════════════
# 自定义竖向滚动条
# ══════════════════════════════════════════════════════════════
class SmoothScrollbar:
    W = 10
    def __init__(self, parent, on_scroll):
        self.on_scroll = on_scroll
        self._lo,self._hi = 0.0,1.0
        self._dragging = False; self._drag_start_y = 0; self._drag_start_lo = 0.0
        self.c_bg='#ebdbb2'; self.c_track='#d5c4a1'; self.c_thumb='#b8a882'; self.c_hover='#8f7a55'
        self.cv = tk.Canvas(parent, width=self.W, highlightthickness=0, cursor='arrow')
        self.cv.pack(side='right', fill='y')
        self.cv.bind('<Configure>', lambda e: self._draw())
        self.cv.bind('<ButtonPress-1>',   self._press)
        self.cv.bind('<B1-Motion>',       self._drag)
        self.cv.bind('<ButtonRelease-1>', self._release)
        self.cv.bind('<Enter>', lambda e: self._hover(True))
        self.cv.bind('<Leave>', lambda e: self._hover(False))
        self._hovered = False

    def set(self, lo, hi): self._lo,self._hi = float(lo),float(hi); self._draw()

    def set_colors(self, bg, track, thumb, thumb_hover):
        self.c_bg=bg; self.c_track=track; self.c_thumb=thumb; self.c_hover=thumb_hover; self._draw()

    def _draw(self):
        cv=self.cv; W=self.W; H=cv.winfo_height()
        if H<4: return
        cv.delete('all'); PAD=2
        cv.create_rectangle(0,0,W,H,fill=self.c_bg,outline='')
        tx=W//2
        cv.create_line(tx,PAD,tx,H-PAD,fill=self.c_track,width=W-4,capstyle='round')
        th=max(20,int((self._hi-self._lo)*(H-2*PAD))); ty=PAD+int(self._lo*(H-2*PAD))
        ty2=min(H-PAD,ty+th); color=self.c_hover if self._hovered else self.c_thumb
        r=(W-4)//2; x1,x2=2,W-2; y1,y2=ty,ty2
        if y2-y1>=2*r:
            cv.create_rectangle(x1,y1+r,x2,y2-r,fill=color,outline='')
            cv.create_oval(x1,y1,x2,y1+2*r,fill=color,outline='')
            cv.create_oval(x1,y2-2*r,x2,y2,fill=color,outline='')
        else: cv.create_oval(x1,y1,x2,y2,fill=color,outline='')

    def _hover(self, v): self._hovered=v; self._draw()

    def _y_to_frac(self,y):
        H=self.cv.winfo_height(); PAD=2
        return max(0.0,min(1.0,(y-PAD)/max(1,H-2*PAD)))

    def _thumb_range(self):
        H=self.cv.winfo_height(); PAD=2
        th=max(20,int((self._hi-self._lo)*(H-2*PAD))); ty=PAD+int(self._lo*(H-2*PAD))
        return ty,ty+th

    def _press(self, e):
        ty1,ty2=self._thumb_range()
        if ty1<=e.y<=ty2:
            self._dragging=True; self._drag_start_y=e.y; self._drag_start_lo=self._lo
        else:
            frac=self._y_to_frac(e.y); span=self._hi-self._lo
            self.on_scroll(max(0.0,min(1.0-span,frac-span/2)))

    def _drag(self, e):
        if not self._dragging: return
        H=self.cv.winfo_height(); PAD=2; dy=e.y-self._drag_start_y
        delta=dy/max(1,H-2*PAD); span=self._hi-self._lo
        target=max(0.0,min(1.0-span,self._drag_start_lo+delta))
        self._lo=target; self._hi=target+span; self._draw(); self.on_scroll(target)

    def _release(self, e): self._dragging=False


# ══════════════════════════════════════════════════════════════
# 主程序
# ══════════════════════════════════════════════════════════════
class App:

    THEMES = {
        '暖黄': dict(bg='#fdf6e3',fg='#3c3836',bar='#ebdbb2',sel='#d5c4a1',thumb='#b8a882',thumb_h='#8f7a55'),
        '夜间': dict(bg='#1e1e2e',fg='#cdd6f4',bar='#181825',sel='#313244',thumb='#45475a',thumb_h='#6c7086'),
        '护眼': dict(bg='#1a2f1a',fg='#a8d5a2',bar='#152315',sel='#2d5a2d',thumb='#3a6b3a',thumb_h='#57c454'),
        '纸张': dict(bg='#f5f0e8',fg='#2c2416',bar='#ede4d0',sel='#c8b89a',thumb='#c8a882',thumb_h='#8b6045'),
        '白底': dict(bg='#ffffff',fg='#1a1a1a',bar='#f0f0f0',sel='#dddddd',thumb='#bbbbbb',thumb_h='#888888'),
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title('摸鱼阅读器')
        self.root.geometry('440x600')
        self.root.minsize(320, 400)
        self.root.attributes('-topmost', True)

        # 数据
        self.shelf   = _jload(SHELF_FILE)   # {path: {title,last_ch,total_ch,last_time,read_time}}
        self.notes   = _jload(NOTES_FILE)   # {path: [{ch,title,content,time}]}
        self.marks   = _jload(MARKS_FILE)   # {path: [{ch,ch_title,time}]}

        self.book_path  = ''
        self.book_title = ''
        self.chapters   = []
        self.cur_ch     = 0

        # UI 状态
        self.theme_name     = '暖黄'
        self.custom_bg      = None
        self.custom_bar     = None
        self.font_size      = 14
        self.line_spacing   = 6
        self.font_fam       = ('宋体' if sys.platform=='win32'
                               else 'Songti SC' if sys.platform=='darwin'
                               else 'Noto Serif CJK SC')
        self._d_held        = False
        self._minimized     = False
        self._settings_open = False
        self._wheel_accum   = 0
        self._tts_playing   = False

        self.tts = TTS()

        self._build_ui()
        self._apply_theme()
        self._bind_keys()
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)
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

        self.lbl_title = tk.Label(self.topbar, text='摸鱼阅读器', font=('',9))
        self.lbl_title.pack(side='left', fill='x', expand=True)

        rbf = tk.Frame(self.topbar); rbf.pack(side='right', padx=2)
        self._tbtn(rbf, '书架', self.open_shelf)
        self._tbtn(rbf, '目录', self.open_chapters)
        self._tbtn(rbf, '搜索', self.open_search)
        self._tbtn(rbf, '摘要', self.open_summary)
        self._tbtn(rbf, '找章', self.open_chapter_finder)
        self._tbtn(rbf, '笔记', self.open_notes)
        self._tbtn(rbf, '书签', self.open_marks)
        self._tbtn(rbf, '打开', self.open_file)
        self._tbtn(rbf, '×',   r.destroy)

        for w in (self.topbar, self.lbl_title):
            w.bind('<ButtonPress-1>', self._drag_start)
            w.bind('<B1-Motion>',     self._drag_move)

        # 设置栏
        self.setbar = tk.Frame(r)
        self._build_setbar()

        # 分隔线
        self.sep = tk.Frame(r, height=1)
        self.sep.pack(fill='x')

        # 文本区
        self.txt_frame = tk.Frame(r)
        self.txt_frame.pack(fill='both', expand=True)

        self.vsb = SmoothScrollbar(self.txt_frame,
                                   on_scroll=lambda f: self.txt.yview_moveto(f))

        self.txt = tk.Text(
            self.txt_frame, wrap='word',
            relief='flat', padx=16, pady=10,
            state='disabled', cursor='arrow',
            font=(self.font_fam, self.font_size),
            borderwidth=0, highlightthickness=0,
            spacing1=self.line_spacing,
            spacing2=self.line_spacing//2,
            spacing3=self.line_spacing,
            yscrollcommand=self._on_yscroll,
        )
        self.txt.pack(side='left', fill='both', expand=True)
        self.txt.bind('<Button-1>',   self._on_click)
        self.txt.bind('<MouseWheel>', self._on_wheel)
        self.txt.bind('<Button-4>',   self._on_wheel)
        self.txt.bind('<Button-5>',   self._on_wheel)
        self._show_welcome()

        # 底部
        self.bot_area = tk.Frame(r)
        self.bot_area.pack(fill='x', side='bottom')

        self.botbar = tk.Frame(self.bot_area, height=28)
        self.botbar.pack(fill='x')
        self.botbar.pack_propagate(False)

        self.btn_prev = tk.Button(self.botbar, text='◀', font=('',9),
                                  relief='flat', padx=4, command=self.prev_chapter)
        self.btn_prev.pack(side='left', padx=4, pady=3)

        self.lbl_prog = tk.Label(self.botbar, text='', font=('',8))
        self.lbl_prog.pack(side='left', expand=True)

        self.btn_tts = tk.Button(self.botbar, text='🔊', font=('',9),
                                 relief='flat', padx=3, command=self.toggle_tts)
        self.btn_tts.pack(side='right', padx=2, pady=3)

        self.btn_note = tk.Button(self.botbar, text='✏', font=('',9),
                                  relief='flat', padx=3, command=self.add_note)
        self.btn_note.pack(side='right', padx=2, pady=3)

        self.btn_mark = tk.Button(self.botbar, text='🔖', font=('',9),
                                  relief='flat', padx=2, command=self.add_mark)
        self.btn_mark.pack(side='right', padx=2, pady=3)

        self.btn_next = tk.Button(self.botbar, text='▶', font=('',9),
                                  relief='flat', padx=4, command=self.next_chapter)
        self.btn_next.pack(side='right', padx=4, pady=3)

    def _tbtn(self, parent, text, cmd):
        tk.Button(parent, text=text, font=('',8), relief='flat',
                  padx=3, command=cmd).pack(side='left', padx=1)

    def _dot(self, p, color, cmd):
        lb = tk.Label(p, text='⬤', fg=color, font=('',12), cursor='hand2')
        lb.pack(side='left', padx=2)
        lb.bind('<Button-1>', lambda e: cmd())

    # ─────────────────────────────────────────────────
    # 设置栏
    # ─────────────────────────────────────────────────
    def _build_setbar(self):
        def row(): f=tk.Frame(self.setbar); f.pack(fill='x',padx=8,pady=2); return f

        r1 = row()
        tk.Label(r1,text='字号',font=('',8)).pack(side='left')
        self.sl_font = tk.Scale(r1,from_=10,to=32,orient='horizontal',length=70,
                                showvalue=True,font=('',7),command=self._on_font_size)
        self.sl_font.set(self.font_size); self.sl_font.pack(side='left',padx=2)
        tk.Label(r1,text='行距',font=('',8)).pack(side='left',padx=(8,0))
        self.sl_spacing = tk.Scale(r1,from_=0,to=24,orient='horizontal',length=70,
                                   showvalue=True,font=('',7),command=self._on_spacing)
        self.sl_spacing.set(self.line_spacing); self.sl_spacing.pack(side='left',padx=2)

        r2 = row()
        tk.Label(r2,text='透明',font=('',8)).pack(side='left')
        self.sl_alpha = tk.Scale(r2,from_=20,to=100,orient='horizontal',length=80,
                                 showvalue=True,font=('',7),
                                 command=lambda v: self.root.attributes('-alpha',int(v)/100))
        self.sl_alpha.set(100); self.sl_alpha.pack(side='left',padx=2)
        # TTS 语速
        tk.Label(r2,text='语速',font=('',8)).pack(side='left',padx=(8,0))
        self.sl_tts_rate = tk.Scale(r2,from_=80,to=300,orient='horizontal',length=70,
                                    showvalue=True,font=('',7),
                                    command=lambda v: self.tts.set_rate(int(v)))
        self.sl_tts_rate.set(180); self.sl_tts_rate.pack(side='left',padx=2)

        r3 = row()
        tk.Label(r3,text='字色',font=('',8)).pack(side='left')
        self.btn_fg_color = tk.Button(r3,text='  ',relief='groove',width=2,
                                      font=('',8),command=self._pick_fg)
        self.btn_fg_color.pack(side='left',padx=2)
        tk.Label(r3,text='背景',font=('',8)).pack(side='left',padx=(6,0))
        self.btn_bg_color = tk.Button(r3,text='  ',relief='groove',width=2,
                                      font=('',8),command=self._pick_bg)
        self.btn_bg_color.pack(side='left',padx=2)
        tk.Button(r3,text='🎨取色',font=('',8),relief='flat',padx=4,
                  command=self._screen_pick).pack(side='left',padx=4)
        tk.Button(r3,text='重置',font=('',8),relief='flat',padx=4,
                  command=self._reset_colors).pack(side='left',padx=2)

        r4 = row()
        tk.Label(r4,text='主题',font=('',8)).pack(side='left')
        self.var_theme = tk.StringVar(value=self.theme_name)
        cb = ttk.Combobox(r4,textvariable=self.var_theme,
                          values=list(self.THEMES.keys()),width=7,font=('',8),state='readonly')
        cb.pack(side='left',padx=4); cb.bind('<<ComboboxSelected>>',self._on_theme)
        # 快速护眼切换
        tk.Button(r4,text='☘护眼',font=('',8),relief='flat',padx=4,
                  command=lambda: (self.var_theme.set('护眼'),self._on_theme())).pack(side='left',padx=2)
        tk.Button(r4,text='🌙夜间',font=('',8),relief='flat',padx=4,
                  command=lambda: (self.var_theme.set('夜间'),self._on_theme())).pack(side='left',padx=2)

    # ─────────────────────────────────────────────────
    # 颜色
    # ─────────────────────────────────────────────────
    def _pick_fg(self):
        t=self._cur_theme(); c=colorchooser.askcolor(color=t['fg'],title='字体颜色')
        if c and c[1]: self.THEMES[self.theme_name]['fg']=c[1]; self.txt.config(fg=c[1]); self.btn_fg_color.config(bg=c[1])

    def _pick_bg(self):
        c=colorchooser.askcolor(color=self._cur_theme()['bg'],title='背景颜色')
        if c and c[1]: self._apply_custom_bg(c[1])

    def _screen_pick(self):
        alpha=self.sl_alpha.get()/100; self.root.attributes('-alpha',0.0)
        def on(hx): self.root.after(100,lambda:self.root.attributes('-alpha',alpha)); self._apply_custom_bg(hx)
        self.root.after(120, lambda: screen_color_picker(on))

    def _apply_custom_bg(self,hx):
        self.custom_bg=hx; self.custom_bar=self._darken(hx,0.88); self._apply_theme()
        try: self.btn_bg_color.config(bg=hx)
        except: pass

    def _reset_colors(self): self.custom_bg=self.custom_bar=None; self._apply_theme()
    def _darken(self,hx,f=0.88):
        h=hx.lstrip('#')
        return '#{:02x}{:02x}{:02x}'.format(int(int(h[0:2],16)*f),int(int(h[2:4],16)*f),int(int(h[4:6],16)*f))

    def _cur_theme(self):
        t=copy.copy(self.THEMES[self.theme_name])
        if self.custom_bg:  t['bg']=self.custom_bg
        if self.custom_bar: t['bar']=self.custom_bar
        return t

    def _on_theme(self, e=None):
        self.theme_name=self.var_theme.get(); self.custom_bg=self.custom_bar=None; self._apply_theme()

    def _apply_theme(self):
        t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
        self.root.configure(bg=bar)
        self._cf(self.topbar,bar,fg); self._cf(self.botbar,bar,fg); self._cf(self.bot_area,bar,fg)
        self.sep.config(bg=sel); self.txt_frame.config(bg=bg)
        self.vsb.cv.config(bg=bg)
        self.vsb.set_colors(bg=bg,track=sel,thumb=t.get('thumb',sel),thumb_hover=t.get('thumb_h',fg))
        self.txt.config(bg=bg,fg=fg,insertbackground=fg,selectbackground=sel)
        self.lbl_prog.config(bg=bar,fg=fg)
        for b in (self.btn_prev,self.btn_next,self.btn_mark,self.btn_note,self.btn_tts):
            b.config(bg=bar,fg=fg,activebackground=sel)
        self._retheme_setbar()
        try:
            if self.custom_bg: self.btn_bg_color.config(bg=self.custom_bg)
        except: pass

    def _cf(self,fr,bg,fg):
        try: fr.config(bg=bg)
        except: pass
        for w in fr.winfo_children():
            try: w.config(bg=bg,fg=fg,activebackground=bg)
            except: pass
            for w2 in w.winfo_children():
                try: w2.config(bg=bg,fg=fg,activebackground=bg)
                except: pass

    def _retheme_setbar(self):
        t=self._cur_theme(); bg,fg,sel=t['bar'],t['fg'],t['sel']
        self._cf(self.setbar,bg,fg)
        for sl in (self.sl_font,self.sl_alpha,self.sl_spacing,self.sl_tts_rate):
            try: sl.config(bg=bg,fg=fg,troughcolor=sel,activebackground=sel)
            except: pass
        try: self.btn_fg_color.config(bg=fg)
        except: pass

    # ─────────────────────────────────────────────────
    # 字号 / 行距
    # ─────────────────────────────────────────────────
    def _on_font_size(self,val):
        self.font_size=int(float(val)); self.txt.config(font=(self.font_fam,self.font_size))

    def _on_spacing(self,val):
        sp=int(float(val)); self.line_spacing=sp
        self.txt.config(spacing1=sp,spacing2=sp//2,spacing3=sp)

    # ─────────────────────────────────────────────────
    # 拖动窗口
    # ─────────────────────────────────────────────────
    def _drag_start(self,e): self._dx=e.x_root-self.root.winfo_x(); self._dy=e.y_root-self.root.winfo_y()
    def _drag_move(self,e):  self.root.geometry(f'+{e.x_root-self._dx}+{e.y_root-self._dy}')

    # ─────────────────────────────────────────────────
    # 打开文件
    # ─────────────────────────────────────────────────
    def open_file(self, path=None):
        if path is None:
            path = filedialog.askopenfilename(
                title='打开小说',
                filetypes=[('小说文件','*.txt *.epub *.md'),('所有文件','*.*')])
        if not path: return
        ext = os.path.splitext(path)[1].lower()
        if ext == '.epub': title,text = read_epub(path)
        else:
            title = os.path.splitext(os.path.basename(path))[0]
            try:
                with open(path,encoding='utf-8',errors='replace') as f: text=f.read()
            except Exception as e: messagebox.showerror('错误',str(e)); return
        self.book_path=path; self.book_title=title
        self.lbl_title.config(text=f'  {title}'); self.root.title(f'摸鱼阅读器 — {title}')
        self._load(text)

    def _load(self,text):
        self.chapters = split_chapters(text)
        # 恢复上次阅读位置
        si = self.shelf.get(self.book_path,{})
        self.cur_ch = max(0,min(si.get('last_ch',0),len(self.chapters)-1))
        # 更新书架
        self._shelf_update()
        self._render_chapter()

    # ─────────────────────────────────────────────────
    # 书架管理
    # ─────────────────────────────────────────────────
    def _shelf_update(self):
        p = self.book_path
        prev = self.shelf.get(p,{})
        self.shelf[p] = {
            'title':      self.book_title,
            'path':       p,
            'last_ch':    self.cur_ch,
            'total_ch':   len(self.chapters),
            'last_time':  datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
            'added_time': prev.get('added_time', datetime.datetime.now().strftime('%Y-%m-%d')),
        }
        _jsave(SHELF_FILE, self.shelf)

    def open_shelf(self):
        t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
        win=tk.Toplevel(self.root); win.title('书架'); win.geometry('380x460')
        win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)

        hdr=tk.Frame(win,bg=bar,height=30); hdr.pack(fill='x'); hdr.pack_propagate(False)
        tk.Label(hdr,text='📚 书架',font=('',10,'bold'),bg=bar,fg=fg).pack(side='left',padx=10,pady=5)
        tk.Button(hdr,text='+添加',font=('',8),relief='flat',bg=bar,fg=fg,
                  command=lambda:self._shelf_add(win)).pack(side='right',padx=4)
        tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,
                  command=win.destroy).pack(side='right',padx=4)

        # 书籍列表
        frame=tk.Frame(win,bg=bg); frame.pack(fill='both',expand=True,padx=6,pady=6)
        sb2=tk.Scrollbar(frame); sb2.pack(side='right',fill='y')
        canvas=tk.Canvas(frame,bg=bg,highlightthickness=0,yscrollcommand=sb2.set)
        canvas.pack(fill='both',expand=True); sb2.config(command=canvas.yview)
        inner=tk.Frame(canvas,bg=bg); canvas.create_window((0,0),window=inner,anchor='nw')

        def refresh():
            for w in inner.winfo_children(): w.destroy()
            if not self.shelf:
                tk.Label(inner,text='书架空空，快去添加书吧',font=('',10),bg=bg,fg=sel).pack(pady=30)
            for path,info in sorted(self.shelf.items(),key=lambda x:x[1].get('last_time',''),reverse=True):
                self._shelf_card(inner,path,info,bg,fg,bar,sel,win,refresh)
            inner.update_idletasks()
            canvas.config(scrollregion=canvas.bbox('all'))
        refresh()

        rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
        win.geometry(f'380x460+{rx}+{ry}')

    def _shelf_card(self,parent,path,info,bg,fg,bar,sel,shelf_win,refresh):
        card=tk.Frame(parent,bg=bar,relief='flat',bd=0)
        card.pack(fill='x',padx=4,pady=3)
        # 封面色块
        colors=['#8f3f71','#458588','#d79921','#689d6a','#cc241d']
        ccolor=colors[hash(path)%len(colors)]
        cover=tk.Frame(card,bg=ccolor,width=36,height=50); cover.pack(side='left',padx=6,pady=6); cover.pack_propagate(False)
        tk.Label(cover,text='📖',font=('',14),bg=ccolor).pack(expand=True)
        # 信息
        info_f=tk.Frame(card,bg=bar); info_f.pack(side='left',fill='both',expand=True,pady=4)
        tk.Label(info_f,text=info.get('title','未知'),font=('',9,'bold'),bg=bar,fg=fg,anchor='w').pack(fill='x')
        lc=info.get('last_ch',0); tc=info.get('total_ch',1)
        pct=int(lc/max(1,tc-1)*100) if tc>1 else 0
        tk.Label(info_f,text=f'第{lc+1}/{tc}章  {pct}%',font=('',8),bg=bar,fg=sel,anchor='w').pack(fill='x')
        # 进度条
        pb_f=tk.Frame(info_f,bg=bar,height=4); pb_f.pack(fill='x',pady=2); pb_f.pack_propagate(False)
        pb_done=tk.Frame(pb_f,bg=ccolor,height=4); pb_done.place(x=0,y=0,relwidth=pct/100,relheight=1)
        tk.Frame(pb_f,bg=sel,height=4).place(x=0,y=0,relwidth=1,relheight=1)
        pb_done.lift()
        tk.Label(info_f,text=f'上次：{info.get("last_time","")}',font=('',7),bg=bar,fg=sel,anchor='w').pack(fill='x')
        # 按钮
        btn_f=tk.Frame(card,bg=bar); btn_f.pack(side='right',padx=6,pady=4)
        def open_it(p=path):
            shelf_win.destroy(); self.open_file(p)
        def del_it(p=path):
            if messagebox.askyesno('删除','从书架移除此书？',parent=shelf_win):
                del self.shelf[p]; _jsave(SHELF_FILE,self.shelf); refresh()
        tk.Button(btn_f,text='阅读',font=('',8),relief='flat',bg=ccolor,fg='white',
                  padx=6,command=open_it).pack(pady=2)
        tk.Button(btn_f,text='移除',font=('',7),relief='flat',bg=bar,fg=sel,
                  padx=4,command=del_it).pack(pady=2)

    def _shelf_add(self, shelf_win):
        path=filedialog.askopenfilename(title='选择书籍',
            filetypes=[('小说文件','*.txt *.epub *.md'),('所有文件','*.*')])
        if not path: return
        if path not in self.shelf:
            title=os.path.splitext(os.path.basename(path))[0]
            self.shelf[path]={'title':title,'path':path,'last_ch':0,'total_ch':0,
                              'last_time':'','added_time':datetime.datetime.now().strftime('%Y-%m-%d')}
            _jsave(SHELF_FILE,self.shelf)
        shelf_win.destroy(); self.open_shelf()

    # ─────────────────────────────────────────────────
    # 渲染章节
    # ─────────────────────────────────────────────────
    def _render_chapter(self, scroll_to_top=True):
        if not self.chapters: return
        self.cur_ch=max(0,min(self.cur_ch,len(self.chapters)-1))
        ch=self.chapters[self.cur_ch]
        self.txt.config(state='normal'); self.txt.delete('1.0','end')
        self.txt.insert('1.0', ch['body']); self.txt.config(state='disabled')
        if scroll_to_top: self.txt.yview_moveto(0.0)
        self._update_nav(); self._wheel_accum=0
        self._shelf_update()

    def _update_nav(self):
        n=len(self.chapters); idx=self.cur_ch+1
        # 有无书签/笔记标记
        m_chs={m['ch'] for m in self.marks.get(self.book_path,[])}
        n_chs={n2['ch'] for n2 in self.notes.get(self.book_path,[])}
        flags=('🔖' if self.cur_ch in m_chs else '')+('✏' if self.cur_ch in n_chs else '')
        self.lbl_prog.config(text=f'{flags}  第{idx}/{n}章')
        self.btn_prev.config(state='normal' if self.cur_ch>0   else 'disabled')
        self.btn_next.config(state='normal' if self.cur_ch<n-1 else 'disabled')

    def _on_yscroll(self,lo,hi): self.vsb.set(lo,hi)

    # ─────────────────────────────────────────────────
    # 翻章
    # ─────────────────────────────────────────────────
    def next_chapter(self):
        if self.chapters and self.cur_ch<len(self.chapters)-1:
            self.cur_ch+=1; self._render_chapter()

    def prev_chapter(self):
        if self.chapters and self.cur_ch>0:
            self.cur_ch-=1; self._render_chapter()

    def goto_chapter(self,idx):
        if not self.chapters: return
        self.cur_ch=max(0,min(idx,len(self.chapters)-1)); self._render_chapter()

    def _on_click(self,e):
        w=self.txt.winfo_width()
        if   e.x<w*0.28: self.prev_chapter()
        elif e.x>w*0.72: self.next_chapter()

    def _on_wheel(self,e):
        delta=1 if e.num==4 else (-1 if e.num==5 else (1 if e.delta>0 else -1))
        top,bot=self.txt.yview()
        if delta<0:
            if bot>=0.999:
                self._wheel_accum-=1
                if self._wheel_accum<=-3: self.next_chapter(); return
            else: self._wheel_accum=0; self.txt.yview_scroll(3,'units')
        else:
            if top<=0.001:
                self._wheel_accum+=1
                if self._wheel_accum>=3:
                    self.prev_chapter(); self.root.after(30,lambda:self.txt.yview_moveto(1.0)); return
            else: self._wheel_accum=0; self.txt.yview_scroll(-3,'units')

    def _scroll_down(self):
        _,bot=self.txt.yview()
        if bot>=0.999: self.next_chapter()
        else: self.txt.yview_scroll(1,'pages')

    # ─────────────────────────────────────────────────
    # TTS 听书
    # ─────────────────────────────────────────────────
    def toggle_tts(self):
        if not self.tts.available:
            messagebox.showinfo('提示','请先安装 pyttsx3：\npip install pyttsx3'); return
        if self._tts_playing:
            self.tts.stop(); self._tts_playing=False
            self.btn_tts.config(text='🔊')
            self._toast('⏹ 已停止朗读')
        else:
            if not self.chapters: return
            ch=self.chapters[self.cur_ch]
            self._tts_playing=True; self.btn_tts.config(text='⏸')
            self._toast('▶ 开始朗读…')
            def done(): self.root.after(0,self._tts_done)
            self.tts.speak(ch['body'],on_done=done)

    def _tts_done(self):
        self._tts_playing=False; self.btn_tts.config(text='🔊')

    # ─────────────────────────────────────────────────
    # 书签（O 键）
    # ─────────────────────────────────────────────────
    def add_mark(self):
        if not self.book_path: messagebox.showinfo('提示','请先打开书'); return
        marks=self.marks.setdefault(self.book_path,[])
        ch=self.chapters[self.cur_ch]; now=datetime.datetime.now().strftime('%m-%d %H:%M')
        existing=next((m for m in marks if m['ch']==self.cur_ch),None)
        entry={'ch':self.cur_ch,'ch_title':ch['title'],'time':now}
        if existing: existing.update(entry); self._toast('🔖 书签已更新')
        else: marks.append(entry); self._toast(f'🔖 书签已添加  第{self.cur_ch+1}章')
        _jsave(MARKS_FILE,self.marks); self._update_nav()

    def open_marks(self):
        marks=self.marks.get(self.book_path,[])
        t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
        win=tk.Toplevel(self.root); win.title('书签'); win.geometry('300x360')
        win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
        hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
        tk.Label(hdr,text='🔖 书签列表',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
        tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
        lf=tk.Frame(win,bg=bg); lf.pack(fill='both',expand=True,padx=4,pady=4)
        sb2=tk.Scrollbar(lf); sb2.pack(side='right',fill='y')
        lb=tk.Listbox(lf,font=('',10),relief='flat',bg=bg,fg=fg,selectbackground=sel,
                      selectforeground=fg,borderwidth=0,highlightthickness=0,
                      activestyle='none',yscrollcommand=sb2.set)
        lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
        rows=list(marks)
        for m in rows: lb.insert('end',f"  🏴 第{m['ch']+1}章  {m['ch_title']}  {m['time']}")
        bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=6,pady=4)
        def jump():
            idxs=lb.curselection()
            if not idxs: return
            win.destroy(); self.goto_chapter(rows[idxs[0]]['ch'])
        def delete():
            idxs=lb.curselection()
            if not idxs: return
            m=rows.pop(idxs[0]); lb.delete(idxs[0])
            self.marks[self.book_path]=[x for x in self.marks.get(self.book_path,[]) if x is not m]
            _jsave(MARKS_FILE,self.marks); self._update_nav()
        tk.Button(bf,text='跳转',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=jump).pack(side='left',padx=4)
        tk.Button(bf,text='删除',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=delete).pack(side='left')
        lb.bind('<Double-Button-1>',lambda e:jump())
        rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
        win.geometry(f'300x360+{rx}+{ry}')

    # ─────────────────────────────────────────────────
    # 笔记（N 键）
    # ─────────────────────────────────────────────────
    def add_note(self):
        if not self.book_path: messagebox.showinfo('提示','请先打开书'); return
        ch=self.chapters[self.cur_ch]
        t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
        win=tk.Toplevel(self.root); win.title('添加笔记'); win.geometry('340x260')
        win.attributes('-topmost',True); win.configure(bg=bg)
        hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
        tk.Label(hdr,text=f'✏ 笔记 — {ch["title"][:20]}',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
        tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
        # 选中文字自动填入
        sel_text=''
        try: sel_text=self.txt.get(tk.SEL_FIRST,tk.SEL_LAST)
        except: pass
        if sel_text:
            tk.Label(win,text='引用文字：',font=('',8),bg=bg,fg=fg).pack(anchor='w',padx=8,pady=(6,0))
            ref=tk.Label(win,text=sel_text[:80]+'…' if len(sel_text)>80 else sel_text,
                        font=('',8,'italic'),bg=sel,fg=fg,wraplength=300,anchor='w',justify='left')
            ref.pack(fill='x',padx=8,pady=2)
        tk.Label(win,text='笔记内容：',font=('',8),bg=bg,fg=fg).pack(anchor='w',padx=8,pady=(6,0))
        ta=tk.Text(win,height=6,font=('',10),bg=bg,fg=fg,insertbackground=fg,
                   relief='flat',padx=8,pady=4,wrap='word',borderwidth=1,highlightthickness=1,
                   highlightbackground=sel,highlightcolor=fg)
        ta.pack(fill='both',expand=True,padx=8,pady=4); ta.focus()
        def save():
            content=ta.get('1.0','end').strip()
            if not content: win.destroy(); return
            notes=self.notes.setdefault(self.book_path,[])
            now=datetime.datetime.now().strftime('%m-%d %H:%M')
            notes.append({'ch':self.cur_ch,'ch_title':ch['title'],'content':content,
                          'quote':sel_text,'time':now})
            _jsave(NOTES_FILE,self.notes); self._update_nav(); win.destroy()
            self._toast('✏ 笔记已保存')
        bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=8,pady=4)
        tk.Button(bf,text='保存笔记',font=('',9,'bold'),bg=bar,fg=fg,relief='flat',
                  padx=10,command=save).pack(side='right',padx=4)
        win.bind('<Control-Return>',lambda e:save())

    def open_notes(self):
        notes=self.notes.get(self.book_path,[])
        t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
        win=tk.Toplevel(self.root); win.title('笔记'); win.geometry('360x480')
        win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
        hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
        tk.Label(hdr,text='✏ 笔记列表',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
        tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)

        # 列表 + 详情
        paned=tk.PanedWindow(win,orient='vertical',bg=bg,sashwidth=4,sashrelief='flat')
        paned.pack(fill='both',expand=True,padx=4,pady=4)

        top_f=tk.Frame(paned,bg=bg); paned.add(top_f,height=200)
        sb2=tk.Scrollbar(top_f); sb2.pack(side='right',fill='y')
        lb=tk.Listbox(top_f,font=('',9),relief='flat',bg=bg,fg=fg,selectbackground=sel,
                      selectforeground=fg,borderwidth=0,highlightthickness=0,
                      activestyle='none',yscrollcommand=sb2.set)
        lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
        rows=list(notes)
        for n2 in rows: lb.insert('end',f"  第{n2['ch']+1}章  {n2['ch_title'][:16]}  {n2['time']}")

        bot_f=tk.Frame(paned,bg=bg); paned.add(bot_f)
        detail=tk.Text(bot_f,font=('',10),bg=bg,fg=fg,insertbackground=fg,
                       relief='flat',padx=8,pady=6,wrap='word',state='disabled',
                       borderwidth=0,highlightthickness=0)
        detail.pack(fill='both',expand=True)

        def show_detail(event=None):
            idxs=lb.curselection()
            if not idxs: return
            n2=rows[idxs[0]]
            detail.config(state='normal'); detail.delete('1.0','end')
            if n2.get('quote'): detail.insert('end',f'引用：{n2["quote"]}\n\n','quote')
            detail.insert('end',n2['content'])
            detail.config(state='disabled')
        lb.bind('<<ListboxSelect>>',show_detail)

        bf=tk.Frame(win,bg=bar); bf.pack(fill='x',padx=6,pady=4)
        def jump():
            idxs=lb.curselection()
            if not idxs: return
            win.destroy(); self.goto_chapter(rows[idxs[0]]['ch'])
        def delete():
            idxs=lb.curselection()
            if not idxs: return
            n2=rows.pop(idxs[0]); lb.delete(idxs[0])
            self.notes[self.book_path]=[x for x in self.notes.get(self.book_path,[]) if x is not n2]
            _jsave(NOTES_FILE,self.notes); self._update_nav()
            detail.config(state='normal'); detail.delete('1.0','end'); detail.config(state='disabled')
        tk.Button(bf,text='跳转章节',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=jump).pack(side='left',padx=4)
        tk.Button(bf,text='删除笔记',font=('',9),bg=bar,fg=fg,relief='flat',padx=8,command=delete).pack(side='left')
        lb.bind('<Double-Button-1>',lambda e:jump())
        rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
        win.geometry(f'360x480+{rx}+{ry}')

    # ─────────────────────────────────────────────────
    # 章节目录
    # ─────────────────────────────────────────────────
    def open_chapters(self):
        if not self.chapters: messagebox.showinfo('提示','请先打开小说'); return
        t=self._cur_theme(); bg,fg,bar,sel=t['bg'],t['fg'],t['bar'],t['sel']
        mark_set={m['ch'] for m in self.marks.get(self.book_path,[])}
        note_set={n2['ch'] for n2 in self.notes.get(self.book_path,[])}
        win=tk.Toplevel(self.root); win.title('章节目录'); win.geometry('300x500')
        win.resizable(True,True); win.attributes('-topmost',True); win.configure(bg=bg)
        hdr=tk.Frame(win,bg=bar,height=28); hdr.pack(fill='x'); hdr.pack_propagate(False)
        tk.Label(hdr,text='📑 章节目录',font=('',9,'bold'),bg=bar,fg=fg).pack(side='left',padx=8,pady=4)
        tk.Button(hdr,text='×',relief='flat',font=('',10),bg=bar,fg=fg,command=win.destroy).pack(side='right',padx=6)
        sf=tk.Frame(win,bg=bg); sf.pack(fill='x',padx=6,pady=(6,2))
        sv=tk.StringVar()
        se=tk.Entry(sf,textvariable=sv,font=('',9),bg=bg,fg=fg,insertbackground=fg,relief='groove')
        se.pack(fill='x',ipady=3)
        PH='搜索章节名...'
        se.insert(0,PH); se.config(fg='gray')
        se.bind('<FocusIn>',lambda e:(se.delete(0,'end'),se.config(fg=fg)) if se.get()==PH else None)
        se.bind('<FocusOut>',lambda e:(se.insert(0,PH),se.config(fg='gray')) if not se.get() else None)
        lf=tk.Frame(win,bg=bg); lf.pack(fill='both',expand=True,padx=4,pady=4)
        sb2=tk.Scrollbar(lf); sb2.pack(side='right',fill='y')
        lb=tk.Listbox(lf,font=('',10),relief='flat',bg=bg,fg=fg,selectbackground=sel,
                      selectforeground=fg,borderwidth=0,highlightthickness=0,
                      activestyle='none',yscrollcommand=sb2.set)
        lb.pack(fill='both',expand=True); sb2.config(command=lb.yview)
        btn_j=tk.Button(win,text='↩ 跳转',font=('',9,'bold'),bg=bar,fg=fg,relief='flat',pady=5)
        btn_j.pack(fill='x',padx=6,pady=4)
        all_ch=list(self.chapters); visible=list(range(len(all_ch)))
        def fill(indices):
            visible.clear(); visible.extend(indices); lb.delete(0,'end')
            for i in indices:
                flags=('🔖' if i in mark_set else '')+('✏' if i in note_set else '')
                cur='▶ ' if i==self.cur_ch else '  '
                lb.insert('end',f'{cur}{i+1}. {all_ch[i]["title"]}{flags}')
        fill(range(len(all_ch)))
        try: lb.see(self.cur_ch); lb.selection_set(self.cur_ch)
        except: pass
        def on_search(*_):
            q=sv.get().strip()
            fill(range(len(all_ch))) if q in ('',PH) else fill([i for i,c in enumerate(all_ch) if q in c['title']])
        sv.trace_add('write',on_search)
        def jump(e=None):
            idxs=lb.curselection()
            if not idxs: return
            win.destroy(); self.goto_chapter(visible[idxs[0]])
        btn_j.config(command=jump); lb.bind('<Double-Button-1>',jump); lb.bind('<Return>',jump)
        rx=self.root.winfo_x()+self.root.winfo_width()+8; ry=self.root.winfo_y()
        win.geometry(f'300x500+{rx}+{ry}')

    # ─────────────────────────────────────────────────
    # Toast 提示
    # ─────────────────────────────────────────────────
    def _toast(self,msg,ms=1500):
        t=self._cur_theme()
        try:
            for w in self.root.winfo_children():
                if isinstance(w,tk.Label) and getattr(w,'_is_toast',False): w.destroy()
        except: pass
        toast=tk.Label(self.root,text=msg,font=('',8),bg=t['bar'],fg=t['fg'],
                       padx=10,pady=4,relief='flat')
        toast._is_toast=True
        toast.place(relx=0.5,rely=0.06,anchor='n')
        self.root.after(ms,lambda: (toast.winfo_exists() and toast.destroy()))

    # ─────────────────────────────────────────────────
    # 欢迎页
    # ─────────────────────────────────────────────────
    def _show_welcome(self):
        self.txt.config(state='normal'); self.txt.delete('1.0','end')
        self.txt.insert('1.0',(
            '\n\n\n'
            '        📚  摸鱼阅读器  v8\n\n'
            '  支持：TXT  /  EPUB  /  MD\n\n'
            '  顶部按钮：书架  目录  笔记  书签  打开\n\n'
            '  操作：\n'
            '    滚轮 / 拖拽右侧滚动条  章内滚动\n'
            '    滚到章末再滚           切下一章\n'
            '    点击左侧 28% / 右侧    切上下章\n'
            '    ← →  切章   S/↓  翻屏\n\n'
            '  快捷键：\n'
            '    O        添加书签\n'
            '    N        添加笔记\n'
            '    F5       开始/停止朗读\n'
            '    D+E      最小化\n'
        ))
        self.txt.config(state='disabled')

    # ─────────────────────────────────────────────────
    # 最小化
    # ─────────────────────────────────────────────────
    def toggle_minimize(self):
        self._minimized=not self._minimized
        if self._minimized:
            self._saved_h=self.root.winfo_height()
            for w in (self.setbar,self.sep,self.txt_frame,self.bot_area): w.pack_forget()
            self.root.geometry(f'{self.root.winfo_width()}x30')
        else:
            self.root.geometry(f'{self.root.winfo_width()}x{self._saved_h}')
            self.sep.pack(fill='x',after=self.topbar)
            if self._settings_open: self.setbar.pack(fill='x',after=self.topbar); self._retheme_setbar()
            self.txt_frame.pack(fill='both',expand=True)
            self.bot_area.pack(fill='x',side='bottom')

    def toggle_settings(self):
        self._settings_open=not self._settings_open
        if self._settings_open: self.setbar.pack(fill='x',after=self.topbar); self._retheme_setbar()
        else: self.setbar.pack_forget()

    # ─────────────────────────────────────────────────
    # 全文搜索（Ctrl+F）
    # ─────────────────────────────────────────────────
    def open_search(self):
        if not self.chapters:
            messagebox.showinfo('提示', '请先打开小说'); return

        t = self._cur_theme()
        bg, fg, bar, sel = t['bg'], t['fg'], t['bar'], t['sel']

        # 若搜索窗已存在则聚焦
        if hasattr(self, '_search_win') and self._search_win.winfo_exists():
            self._search_win.lift(); self._search_win.focus_force(); return

        win = tk.Toplevel(self.root)
        win.title('全文搜索')
        win.geometry('480x560')
        win.resizable(True, True)
        win.attributes('-topmost', True)
        win.configure(bg=bg)
        self._search_win = win

        # ── 顶部搜索框 ────────────────────────────────
        top = tk.Frame(win, bg=bar); top.pack(fill='x', padx=0, pady=0)
        tk.Label(top, text='🔍', font=('',11), bg=bar, fg=fg).pack(side='left', padx=8, pady=6)

        sv = tk.StringVar()
        entry = tk.Entry(top, textvariable=sv, font=('',11), bg=bg, fg=fg,
                         insertbackground=fg, relief='flat', bd=0)
        entry.pack(side='left', fill='x', expand=True, ipady=4)

        # 大小写 / 正则 选项
        var_case  = tk.BooleanVar(value=False)
        var_regex = tk.BooleanVar(value=False)
        tk.Checkbutton(top, text='Aa', variable=var_case, font=('',8),
                       bg=bar, fg=fg, activebackground=bar,
                       selectcolor=bg).pack(side='left', padx=2)
        tk.Checkbutton(top, text='.*', variable=var_regex, font=('',8),
                       bg=bar, fg=fg, activebackground=bar,
                       selectcolor=bg).pack(side='left', padx=2)

        lbl_count = tk.Label(top, text='', font=('',8), bg=bar, fg=sel)
        lbl_count.pack(side='left', padx=6)
        tk.Button(top, text='×', relief='flat', font=('',10),
                  bg=bar, fg=fg, command=win.destroy).pack(side='right', padx=6)

        sep2 = tk.Frame(win, height=1, bg=sel); sep2.pack(fill='x')

        # ── 结果列表 ──────────────────────────────────
        list_frame = tk.Frame(win, bg=bg); list_frame.pack(fill='both', expand=True)
        sb2 = tk.Scrollbar(list_frame); sb2.pack(side='right', fill='y')
        lb = tk.Listbox(list_frame, font=('',9), relief='flat', bg=bg, fg=fg,
                        selectbackground=sel, selectforeground=fg,
                        borderwidth=0, highlightthickness=0,
                        activestyle='none', yscrollcommand=sb2.set)
        lb.pack(fill='both', expand=True); sb2.config(command=lb.yview)

        # ── 预览区 ────────────────────────────────────
        sep3 = tk.Frame(win, height=1, bg=sel); sep3.pack(fill='x')
        preview_frame = tk.Frame(win, bg=bg, height=130)
        preview_frame.pack(fill='x', padx=0); preview_frame.pack_propagate(False)

        preview = tk.Text(preview_frame, font=('',9), bg=bg, fg=fg,
                          relief='flat', padx=12, pady=6, wrap='word',
                          state='disabled', borderwidth=0, highlightthickness=0)
        preview.pack(fill='both', expand=True)
        preview.tag_config('hit',  background='#d79921', foreground='#1d2021')
        preview.tag_config('info', foreground=sel)

        # 底部跳转栏
        bot_f = tk.Frame(win, bg=bar, height=30)
        bot_f.pack(fill='x'); bot_f.pack_propagate(False)
        lbl_loc = tk.Label(bot_f, text='', font=('',8), bg=bar, fg=fg)
        lbl_loc.pack(side='left', padx=8, pady=4)
        btn_jump = tk.Button(bot_f, text='↩ 跳转到此处', font=('',8,'bold'),
                             bg=bar, fg=fg, relief='flat', padx=8,
                             state='disabled')
        btn_jump.pack(side='right', padx=8, pady=3)

        # ── 搜索逻辑 ──────────────────────────────────
        results = []   # [(ch_idx, start_in_body, end_in_body, snippet)]

        def do_search(*_):
            results.clear(); lb.delete(0, 'end')
            query = sv.get().strip()
            if not query:
                lbl_count.config(text=''); return

            flags = 0 if var_case.get() else re.IGNORECASE
            try:
                if var_regex.get():
                    pat = re.compile(query, flags)
                else:
                    pat = re.compile(re.escape(query), flags)
            except re.error as e:
                lbl_count.config(text=f'正则错误: {e}'); return

            CONTEXT = 40   # 匹配前后各取多少字符
            for ci, ch in enumerate(self.chapters):
                for m in pat.finditer(ch['body']):
                    s, e2 = m.start(), m.end()
                    pre  = ch['body'][max(0, s-CONTEXT):s].replace('\n', ' ')
                    hit  = ch['body'][s:e2]
                    post = ch['body'][e2:min(len(ch['body']), e2+CONTEXT)].replace('\n', ' ')
                    snippet = (pre, hit, post)
                    results.append((ci, s, e2, snippet))

            lbl_count.config(text=f'共 {len(results)} 处')
            for ci, s, e2, (pre, hit, post) in results:
                ch_title = self.chapters[ci]['title']
                display  = f"  第{ci+1}章  {ch_title[:14]}…  「{hit[:20]}」"
                lb.insert('end', display)

            # 清空预览
            preview.config(state='normal'); preview.delete('1.0','end')
            preview.config(state='disabled')
            lbl_loc.config(text='')
            btn_jump.config(state='disabled')

        sv.trace_add('write', do_search)
        var_case.trace_add('write',  do_search)
        var_regex.trace_add('write', do_search)

        def on_select(event=None):
            idxs = lb.curselection()
            if not idxs: return
            ci, s, e2, (pre, hit, post) = results[idxs[0]]
            ch = self.chapters[ci]

            # 更新预览
            preview.config(state='normal'); preview.delete('1.0','end')
            preview.insert('end', f'第{ci+1}章  {ch["title"]}\n', 'info')
            preview.insert('end', '…' + pre)
            preview.insert('end', hit, 'hit')
            preview.insert('end', post + '…')
            preview.config(state='disabled')

            lbl_loc.config(text=f'第{ci+1}章 · 位置 {s}')
            btn_jump.config(state='normal',
                            command=lambda: _jump(ci, s, e2, hit))

        def _jump(ci, s, e2, hit):
            # 跳转到章节，并高亮匹配文字
            self.goto_chapter(ci)
            win.lift()
            # 在 txt 里找到并高亮
            self.root.after(80, lambda: _highlight_in_txt(hit))

        def _highlight_in_txt(hit):
            self.txt.tag_remove('search_hit', '1.0', 'end')
            self.txt.tag_config('search_hit', background='#d79921', foreground='#1d2021')
            start = '1.0'
            while True:
                pos = self.txt.search(hit, start, nocase=not var_case.get(), stopindex='end')
                if not pos: break
                end_pos = f'{pos}+{len(hit)}c'
                self.txt.tag_add('search_hit', pos, end_pos)
                self.txt.see(pos)
                start = end_pos

        lb.bind('<<ListboxSelect>>', on_select)
        lb.bind('<Double-Button-1>', lambda e: btn_jump.invoke())
        lb.bind('<Return>',         lambda e: btn_jump.invoke())

        entry.focus()
        # 如果有选中文字，自动填入搜索框
        try:
            sel_text = self.txt.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
            if sel_text and '\n' not in sel_text:
                sv.set(sel_text)
        except: pass

        rx = self.root.winfo_x() + self.root.winfo_width() + 8
        ry = self.root.winfo_y()
        win.geometry(f'480x560+{rx}+{ry}')

    # ─────────────────────────────────────────────────
    # 章节摘要（Ctrl+M）—— 调用智谱 GLM API
    # ─────────────────────────────────────────────────
    def open_summary(self):
        """章节摘要——多模式，调用智谱 GLM"""
        if not self.chapters:
            messagebox.showinfo('提示', '请先打开小说'); return

        class State:
            ch_body  = self.chapters[self.cur_ch]['body']
            ch_title = self.chapters[self.cur_ch]['title']
            ch_idx   = self.cur_ch
            result   = ''
            running  = False

        st  = State()
        _t  = self._cur_theme()
        _bg, _fg, _bar, _sel = _t['bg'], _t['fg'], _t['bar'], _t['sel']

        dlg = tk.Toplevel(self.root)
        dlg.title('章节摘要')
        dlg.geometry('480x540')
        dlg.resizable(True, True)
        dlg.attributes('-topmost', True)
        dlg.configure(bg=_bg)

        # ── 顶部信息栏 ────────────────────────────────
        top = tk.Frame(dlg, bg=_bar, height=34)
        top.pack(fill='x'); top.pack_propagate(False)
        _cc = len(st.ch_body)
        _pc = len([p for p in st.ch_body.split('\n') if p.strip()])
        tk.Label(top, text=f'  ✨  {st.ch_title}',
                 font=('',9,'bold'), bg=_bar, fg=_fg, anchor='w'
                 ).pack(side='left', fill='x', expand=True, padx=6, pady=7)
        tk.Label(top, text=f'{_cc} 字  {_pc} 段',
                 font=('',8), bg=_bar, fg=_sel).pack(side='right', padx=6)
        tk.Button(top, text='×', relief='flat', font=('',11),
                  bg=_bar, fg=_fg, bd=0, command=dlg.destroy).pack(side='right', padx=4)

        tk.Frame(dlg, height=1, bg=_sel).pack(fill='x')

        # ── 选项行 ────────────────────────────────────
        opt = tk.Frame(dlg, bg=_bar)
        opt.pack(fill='x', padx=10, pady=6)

        # 长度
        tk.Label(opt, text='长度', font=('',8,'bold'), bg=_bar, fg=_fg).pack(side='left')
        v_len = tk.StringVar(value='简短')
        _len_opts = [
            ('简短', '简短', '50~80字，一句话总结'),
            ('标准', '标准', '150字，含人物/情节/转折'),
            ('详细', '详细', '300字，完整剧情分析'),
        ]
        for _val, _lbl, _tip in _len_opts:
            _rb = tk.Radiobutton(opt, text=_lbl, variable=v_len, value=_val,
                                 font=('',8), bg=_bar, fg=_fg,
                                 activebackground=_bar, selectcolor=_bg)
            _rb.pack(side='left', padx=4)

        tk.Label(opt, text='   风格', font=('',8,'bold'), bg=_bar, fg=_fg).pack(side='left')
        v_style = tk.StringVar(value='客观')
        _style_opts = [('客观','客观'), ('活泼','活泼'), ('学术','学术')]
        for _val, _lbl in _style_opts:
            tk.Radiobutton(opt, text=_lbl, variable=v_style, value=_val,
                           font=('',8), bg=_bar, fg=_fg,
                           activebackground=_bar, selectcolor=_bg).pack(side='left', padx=4)

        tk.Frame(dlg, height=1, bg=_sel).pack(fill='x')

        # ── 摘要展示区 ────────────────────────────────
        mid = tk.Frame(dlg, bg=_bg)
        mid.pack(fill='both', expand=True)
        _vsb2 = tk.Scrollbar(mid, width=6)
        _vsb2.pack(side='right', fill='y')
        out = tk.Text(mid, font=(self.font_fam, self.font_size+1),
                      bg=_bg, fg=_fg, insertbackground=_fg, selectbackground=_sel,
                      relief='flat', padx=20, pady=16, wrap='word',
                      borderwidth=0, highlightthickness=0, state='disabled',
                      yscrollcommand=_vsb2.set, spacing1=4, spacing3=4)
        out.pack(side='left', fill='both', expand=True)
        _vsb2.config(command=out.yview)
        out.tag_config('hint',    foreground=_sel)
        out.tag_config('warn',    foreground='#cc241d')
        out.tag_config('loading', foreground=_sel, font=(self.font_fam, self.font_size, 'italic'))
        out.tag_config('result',  foreground=_fg,
                       font=(self.font_fam, self.font_size+1), spacing1=6, spacing3=4)

        tk.Frame(dlg, height=1, bg=_sel).pack(fill='x')

        # ── 底部操作栏 ────────────────────────────────
        bot = tk.Frame(dlg, bg=_bar, height=50)
        bot.pack(fill='x', side='bottom'); bot.pack_propagate(False)

        btn_gen = tk.Button(bot, text='▶  开始生成摘要',
                            font=('',10,'bold'),
                            bg=_fg, fg=_bg,
                            activebackground=_sel, activeforeground=_fg,
                            relief='flat', bd=0, padx=18, pady=5, cursor='hand2')
        btn_gen.pack(side='left', padx=12, pady=10)

        btn_copy = tk.Button(bot, text='复制', font=('',9),
                             bg=_bar, fg=_fg, relief='flat', padx=8,
                             state='disabled', cursor='hand2')
        btn_copy.pack(side='left', padx=3, pady=10)

        btn_note = tk.Button(bot, text='存为笔记', font=('',9),
                             bg=_bar, fg=_fg, relief='flat', padx=8,
                             state='disabled', cursor='hand2')
        btn_note.pack(side='left', padx=3, pady=10)

        lbl_st = tk.Label(bot, text='', font=('',8), bg=_bar, fg=_sel)
        lbl_st.pack(side='right', padx=12)

        # ── 工具函数 ──────────────────────────────────
        def _show(text, tag='result'):
            out.config(state='normal')
            out.delete('1.0', 'end')
            out.insert('end', text, tag)
            out.config(state='disabled')
            out.yview_moveto(0.0)

        def _build_prompt():
            _len_map = {
                '简短': '50~80字，用一两句话概括最核心的内容',
                '标准': '150字左右，包含主要人物、核心情节、关键转折',
                '详细': '300字左右，完整分析人物行为、情节发展、伏笔与高潮',
            }
            _sty_map = {
                '客观': '语言客观简洁，不带情感色彩',
                '活泼': '语言生动活泼，适当使用emoji增加趣味',
                '学术': '语言严谨，条理清晰，使用文学分析术语',
            }
            _clip = st.ch_body[:5000]
            return (
                f"请对以下小说章节做摘要。\n"
                f"要求长度：{_len_map[v_len.get()]}\n"
                f"要求风格：{_sty_map[v_style.get()]}\n"
                f"直接输出摘要，不要标题、序号、前缀。\n\n"
                f"【{st.ch_title}】\n{_clip}"
            )

        def _on_ok(text):
            st.result  = text
            st.running = False
            _show(text, 'result')
            btn_gen.config(state='normal', text='↺  重新生成')
            btn_copy.config(state='normal')
            btn_note.config(state='normal')
            lbl_st.config(text=f'已生成 · {len(text)} 字')

        def _on_err(msg):
            st.running = False
            btn_gen.config(state='normal', text='▶  开始生成摘要')
            if msg == 'NO_KEY':
                _show(
                    '⚠  未找到 API Key\n\n'
                    '请在程序同目录新建文件：api_key.txt\n'
                    '将智谱 API Key 粘贴进去保存即可。\n\n'
                    '申请地址：https://open.bigmodel.cn\n'
                    '（新用户有免费额度，GLM-4-Flash 完全免费）',
                    'warn'
                )
            else:
                _show(f'⚠  生成失败\n\n{msg}', 'warn')

        def _do_gen():
            if st.running: return
            st.running = True
            btn_gen.config(state='disabled', text='生成中…')
            btn_copy.config(state='disabled')
            btn_note.config(state='disabled')
            lbl_st.config(text='')
            _len_label = v_len.get()
            _sty_label = v_style.get()
            _show(f'正在生成【{_len_label}·{_sty_label}】摘要，请稍候…', 'loading')

            def worker():
                import urllib.request as _ureq
                import urllib.error   as _uerr
                import json           as _ujson

                _key = _inject_api_key()
                if not _key:
                    dlg.after(0, lambda: _on_err('NO_KEY'))
                    return

                _tok_map = {'简短': 150, '标准': 400, '详细': 700}
                _maxtok  = _tok_map.get(_len_label, 400)
                _prompt  = _build_prompt()
                _payload = _ujson.dumps({
                    'model':       'glm-4-flash',
                    'max_tokens':  _maxtok,
                    'temperature': 0.6,
                    'messages':    [{'role': 'user', 'content': _prompt}],
                }).encode('utf-8')

                _req = _ureq.Request(
                    'https://open.bigmodel.cn/api/paas/v4/chat/completions',
                    data    = _payload,
                    headers = {'Content-Type': 'application/json',
                               'Authorization': f'Bearer {_key}'},
                    method  = 'POST',
                )
                try:
                    with _ureq.urlopen(_req, timeout=30) as _resp:
                        _raw   = _resp.read().decode('utf-8')
                        _pdata = _ujson.loads(_raw)
                        _text  = _pdata['choices'][0]['message']['content'].strip()
                    dlg.after(0, lambda t=_text: _on_ok(t))
                except _uerr.HTTPError as _he:
                    _hbody = _he.read().decode('utf-8', errors='replace')
                    try:    _hemsg = _ujson.loads(_hbody).get('error',{}).get('message', _hbody)
                    except: _hemsg = _hbody[:200]
                    _hcode = str(_he.code)
                    dlg.after(0, lambda c=_hcode, m=_hemsg: _on_err(f'HTTP {c}：{m}'))
                except Exception as _exc:
                    _emsg = str(_exc)
                    dlg.after(0, lambda m=_emsg: _on_err(m))

            threading.Thread(target=worker, daemon=True).start()

        def _do_copy():
            if not st.result: return
            dlg.clipboard_clear(); dlg.clipboard_append(st.result)
            lbl_st.config(text='已复制 ✓')
            dlg.after(1800, lambda: lbl_st.config(text=f'已生成 · {len(st.result)} 字'))

        def _do_save():
            if not st.result: return
            _nl = self.notes.setdefault(self.book_path, [])
            _nl.append({'ch': st.ch_idx, 'ch_title': st.ch_title,
                        'content': f'[AI摘要·{v_len.get()}·{v_style.get()}]\n{st.result}',
                        'quote': '', 'time': datetime.datetime.now().strftime('%m-%d %H:%M')})
            _jsave(NOTES_FILE, self.notes)
            self._update_nav()
            self._toast('✏ 摘要已存为笔记')
            lbl_st.config(text='已保存为笔记 ✓')

        btn_gen.config(command=_do_gen)
        btn_copy.config(command=_do_copy)
        btn_note.config(command=_do_save)

        _hk = bool(_inject_api_key())
        _ktip = '' if _hk else '\n\n💡 未检测到 api_key.txt，点击生成后会显示配置说明。'
        _show(
            f'选择长度和风格，点击「▶ 开始生成摘要」。\n'
            f'· 简短：一两句话抓核心\n'
            f'· 标准：150字含人物/情节/转折\n'
            f'· 详细：300字完整分析{_ktip}',
            'hint'
        )

        _rx = self.root.winfo_x() + self.root.winfo_width() + 10
        _ry = self.root.winfo_y()
        dlg.geometry(f'480x540+{_rx}+{_ry}')


    # ─────────────────────────────────────────────────
    # AI 章节查找（Ctrl+G）—— 完善版：分块搜索与范围控制
    # ─────────────────────────────────────────────────
    def open_chapter_finder(self):
        """用自然语言描述模糊记忆，AI 分析最匹配的章节"""
        if not self.chapters:
            messagebox.showinfo('提示', '请先打开小说'); return

        class State:
            running = False
            results = []   # [{'rank':int,'ch_idx':int,'ch_title':str,'reason':str,'score':int}]

        st  = State()
        _t  = self._cur_theme()
        _bg, _fg, _bar, _sel = _t['bg'], _t['fg'], _t['bar'], _t['sel']

        dlg = tk.Toplevel(self.root)
        dlg.title('AI 章节查找')
        dlg.geometry('500x620')  # 稍微增高一点容纳新 UI
        dlg.resizable(True, True)
        dlg.attributes('-topmost', True)
        dlg.configure(bg=_bg)

        # ── 顶部标题栏 ────────────────────────────────
        top = tk.Frame(dlg, bg=_bar, height=34)
        top.pack(fill='x'); top.pack_propagate(False)
        tk.Label(top, text='  🔍  AI 章节查找',
                 font=('',10,'bold'), bg=_bar, fg=_fg).pack(side='left', padx=8, pady=7)
        tk.Label(top, text=f'共 {len(self.chapters)} 章',
                 font=('',8), bg=_bar, fg=_sel).pack(side='right', padx=8)
        tk.Button(top, text='×', relief='flat', font=('',11),
                  bg=_bar, fg=_fg, bd=0, command=dlg.destroy).pack(side='right', padx=4)

        tk.Frame(dlg, height=1, bg=_sel).pack(fill='x')

        # ── 输入区 ────────────────────────────────────
        inp_wrap = tk.Frame(dlg, bg=_bg)
        inp_wrap.pack(fill='x', padx=12, pady=(10, 0))

        tk.Label(inp_wrap,
                 text='描述你记得的情节、场景、人物对话或感受：',
                 font=('',9), bg=_bg, fg=_fg, anchor='w').pack(fill='x')

        inp = tk.Text(inp_wrap,
                      font=(self.font_fam, self.font_size),
                      bg=_bar, fg=_fg, insertbackground=_fg,
                      relief='flat', padx=10, pady=8,
                      wrap='word', height=4,
                      borderwidth=1, highlightthickness=1,
                      highlightbackground=_sel, highlightcolor=_fg)
        inp.pack(fill='x', pady=(4, 0))

        _PH = '例如：有一章写到主角第一次失败，很沮丧，在雨中独自走路……'
        inp.insert('1.0', _PH); inp.config(fg=_sel)
        def _focus_in(e):
            if inp.get('1.0','end-1c') == _PH:
                inp.delete('1.0','end'); inp.config(fg=_fg)
        def _focus_out(e):
            if not inp.get('1.0','end-1c').strip():
                inp.insert('1.0', _PH); inp.config(fg=_sel)
        inp.bind('<FocusIn>',  _focus_in)
        inp.bind('<FocusOut>', _focus_out)

        # ── 【核心优化】范围与参数配置行 ───────────────
        opt_frame = tk.Frame(inp_wrap, bg=_bg)
        opt_frame.pack(fill='x', pady=(8,0))
        
        # 1. 搜索范围选择器
        tk.Label(opt_frame, text='搜索范围：', font=('',8), bg=_bg, fg=_fg).pack(side='left')
        
        CHUNK_SIZE = 500  # 每块 500 章，确保 Token 极度安全
        total_ch = len(self.chapters)
        range_opts = []
        for i in range(0, total_ch, CHUNK_SIZE):
            end = min(i + CHUNK_SIZE, total_ch)
            range_opts.append(f"第{i+1}-{end}章")
        
        if total_ch > CHUNK_SIZE:
            range_opts.append("全书 (仅匹配标题不含正文)") # 安全的全书兜底模式
            
        v_range = tk.StringVar(value=range_opts[0] if range_opts else "全部")
        cb_range = ttk.Combobox(opt_frame, textvariable=v_range, values=range_opts,
                                width=18, font=('',8), state='readonly')
        cb_range.pack(side='left', padx=2)

        # 2. 返回数量
        tk.Label(opt_frame, text='  返回数：', font=('',8), bg=_bg, fg=_fg).pack(side='left', padx=(6,0))
        v_cnt = tk.IntVar(value=3)
        cb_cnt = ttk.Combobox(opt_frame, textvariable=v_cnt, values=[1, 3, 5],
                              width=3, font=('',8), state='readonly')
        cb_cnt.pack(side='left', padx=2)

        tk.Frame(dlg, height=1, bg=_sel).pack(fill='x', pady=(10,0))

        # ── 结果展示区（上：列表 / 下：详情） ─────────
        pane = tk.PanedWindow(dlg, orient='vertical', bg=_bg,
                              sashwidth=5, sashrelief='flat', sashpad=2)
        pane.pack(fill='both', expand=True, padx=0, pady=0)

        list_frame = tk.Frame(pane, bg=_bg)
        pane.add(list_frame, height=180)
        _lsb = tk.Scrollbar(list_frame, width=6)
        _lsb.pack(side='right', fill='y')
        result_lb = tk.Listbox(list_frame, font=('',10), relief='flat',
                               bg=_bg, fg=_fg, selectbackground=_sel, selectforeground=_fg,
                               borderwidth=0, highlightthickness=0,
                               activestyle='none', yscrollcommand=_lsb.set)
        result_lb.pack(fill='both', expand=True)
        _lsb.config(command=result_lb.yview)

        detail_frame = tk.Frame(pane, bg=_bg)
        pane.add(detail_frame, height=140)
        detail = tk.Text(detail_frame, font=(self.font_fam, self.font_size),
                         bg=_bar, fg=_fg, insertbackground=_fg, relief='flat',
                         padx=14, pady=10, wrap='word', borderwidth=0, highlightthickness=0, state='disabled')
        detail.pack(fill='both', expand=True)
        detail.tag_config('title',  font=(self.font_fam, self.font_size, 'bold'))
        detail.tag_config('score',  foreground=_sel)
        detail.tag_config('reason', foreground=_fg)
        detail.tag_config('hint',   foreground=_sel, font=(self.font_fam, self.font_size, 'italic'))
        detail.tag_config('warn',   foreground='#cc241d')

        tk.Frame(dlg, height=1, bg=_sel).pack(fill='x')

        # ── 底部操作栏 ────────────────────────────────
        bot = tk.Frame(dlg, bg=_bar, height=46)
        bot.pack(fill='x', side='bottom'); bot.pack_propagate(False)

        btn_find = tk.Button(bot, text='🔍  开始分析', font=('',10,'bold'),
                             bg=_fg, fg=_bg, activebackground=_sel, activeforeground=_fg,
                             relief='flat', bd=0, padx=16, pady=4, cursor='hand2')
        btn_find.pack(side='left', padx=12, pady=8)

        btn_goto = tk.Button(bot, text='↩ 跳转到此章', font=('',9),
                             bg=_bar, fg=_fg, relief='flat', padx=8,
                             state='disabled', cursor='hand2')
        btn_goto.pack(side='left', padx=4, pady=8)

        lbl_st2 = tk.Label(bot, text='', font=('',8), bg=_bar, fg=_sel)
        lbl_st2.pack(side='right', padx=12)

        # ── 内部函数 ──────────────────────────────────
        def _show_detail(text, tag='hint'):
            detail.config(state='normal'); detail.delete('1.0', 'end')
            detail.insert('end', text, tag); detail.config(state='disabled')

        def _show_detail_rich(title, score, reason):
            detail.config(state='normal'); detail.delete('1.0', 'end')
            detail.insert('end', f'{title}\n', 'title')
            detail.insert('end', f'匹配度：{"★" * min(score,5)}{"☆" * max(0,5-score)}  {score}/5\n', 'score')
            detail.insert('end', f'\n{reason}', 'reason')
            detail.config(state='disabled')

        def _on_select(event=None):
            idxs = result_lb.curselection()
            if not idxs or not st.results: return
            _item = st.results[idxs[0]]
            _show_detail_rich(_item['ch_title'], _item['score'], _item['reason'])
            btn_goto.config(state='normal', command=lambda i=_item['ch_idx']: (dlg.destroy(), self.goto_chapter(i)))

        result_lb.bind('<<ListboxSelect>>', _on_select)
        result_lb.bind('<Double-Button-1>', lambda e: btn_goto.invoke() if btn_goto['state']=='normal' else None)

        def _on_find_success(results):
            st.running = False; st.results = results
            btn_find.config(state='normal', text='🔍  重新分析')
            result_lb.delete(0, 'end')
            if not results:
                _show_detail('未找到匹配章节，请尝试扩大范围或换一种描述。', 'hint')
                lbl_st2.config(text='未找到结果'); return
            for _r in results:
                _stars = '★' * min(_r['score'], 5)
                result_lb.insert('end', f"  第{_r['ch_idx']+1}章  {_r['ch_title'][:24]}  {_stars}")
            lbl_st2.config(text=f'找到 {len(results)} 个匹配')
            result_lb.selection_set(0); _on_select()

        def _on_find_error(msg):
            st.running = False
            btn_find.config(state='normal', text='🔍  开始分析')
            if msg == 'NO_KEY':
                _show_detail('⚠  未找到 API Key\n请在程序同目录新建 api_key.txt', 'warn')
            else:
                _show_detail(f'⚠  分析失败\n\n{msg}', 'warn')
            lbl_st2.config(text='')

        def _do_find():
            _query = inp.get('1.0','end-1c').strip()
            if not _query or _query == _PH: inp.focus(); return
            if st.running: return
            st.running = True; st.results = []; result_lb.delete(0, 'end')
            btn_find.config(state='disabled', text='分析中…')
            btn_goto.config(state='disabled'); lbl_st2.config(text='')
            
            _selected_range = v_range.get()
            _show_detail(f'正在分析 [{_selected_range}]，请稍候…', 'hint')
            _top_n = v_cnt.get()

            # ── 【核心逻辑】根据选择的范围构建 prompt ──
            _toc_lines = []
            _start_idx, _end_idx = 0, total_ch
            
            if "全书" in _selected_range:
                # 全书模式：极其克制，仅发送章节序号和标题，无正文
                for _i, _ch in enumerate(self.chapters):
                    _toc_lines.append(f"[{_i}]《{_ch['title']}》")
            else:
                # 分块模式：提取范围，例如 "第1-500章"
                import re
                m = re.search(r'第(\d+)-(\d+)章', _selected_range)
                if m:
                    _start_idx = int(m.group(1)) - 1
                    _end_idx = int(m.group(2))
                
                # 在分块内，安全提取前 50 字作为预览
                for _i in range(_start_idx, min(_end_idx, total_ch)):
                    _ch = self.chapters[_i]
                    _preview = _ch['body'][:50].replace('\n', ' ').strip()
                    _toc_lines.append(f"[{_i}]《{_ch['title']}》：{_preview}…")
            
            _toc_text = '\n'.join(_toc_lines)

            def worker():
                import urllib.request as _ureq
                import urllib.error   as _uerr
                import json           as _ujson

                _key = _inject_api_key()
                if not _key:
                    dlg.after(0, lambda: _on_find_error('NO_KEY')); return

                _prompt = (
                    f"我在读一本小说，对某个章节有模糊印象，请帮我找出最匹配的章节。\n\n"
                    f"【我的描述】\n{_query}\n\n"
                    f"【候选章节列表】(格式为 [序号]《标题》：预览)\n{_toc_text}\n\n"
                    f"请从候选列表中选出最匹配的 {_top_n} 个，"
                    f"以 JSON 数组格式返回，每项包含：\n"
                    f"  ch_idx（必须严格使用上面列表括号[]中的数字序号，整数）\n"
                    f"  ch_title（章节标题）\n"
                    f"  score（匹配度1-5分，整数）\n"
                    f"  reason（50字内说明匹配原因）\n\n"
                    f"只返回 JSON，不要其他文字，格式示例：\n"
                    f'[{{"ch_idx":2,"ch_title":"第三章","score":4,"reason":"..."}}]'
                )

                _payload = _ujson.dumps({
                    'model':       'glm-4-flash',
                    'max_tokens':  600,
                    'temperature': 0.2,
                    'messages':    [{'role': 'user', 'content': _prompt}],
                }).encode('utf-8')

                _req = _ureq.Request(
                    'https://open.bigmodel.cn/api/paas/v4/chat/completions',
                    data    = _payload,
                    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {_key}'},
                    method  = 'POST',
                )
                try:
                    with _ureq.urlopen(_req, timeout=40) as _resp:
                        _raw   = _resp.read().decode('utf-8')
                        _pdata = _ujson.loads(_raw)
                        _text  = _pdata['choices'][0]['message']['content'].strip()

                    _text = re.sub(r'^```[a-z]*\s*', '', _text, flags=re.I)
                    _text = re.sub(r'\s*```$', '', _text)
                    _parsed = _ujson.loads(_text)

                    _results = []
                    for _item in _parsed[:_top_n]:
                        _ci = int(_item.get('ch_idx', 0))
                        # 确保 AI 返回的序号在有效范围内
                        if 0 <= _ci < len(self.chapters):
                            _results.append({
                                'rank':     len(_results)+1,
                                'ch_idx':   _ci,
                                'ch_title': self.chapters[_ci]['title'],
                                'score':    max(1, min(5, int(_item.get('score', 3)))),
                                'reason':   str(_item.get('reason', ''))[:120],
                            })
                    dlg.after(0, lambda r=_results: _on_find_success(r))

                except _uerr.HTTPError as _he:
                    _hbody = _he.read().decode('utf-8', errors='replace')
                    try:    _hemsg = _ujson.loads(_hbody).get('error',{}).get('message', _hbody)
                    except: _hemsg = _hbody[:150]
                    dlg.after(0, lambda c=str(_he.code), m=_hemsg: _on_find_error(f'HTTP {c}：{m}'))
                except Exception as _exc:
                    dlg.after(0, lambda m=str(_exc): _on_find_error(m))

            import threading
            threading.Thread(target=worker, daemon=True).start()

        btn_find.config(command=_do_find)
        inp.bind('<Control-Return>', lambda e: _do_find())

        _show_detail('选择【搜索范围】，输入回忆的情节，AI 将精准定位。\n💡 范围越小，API 请求越快，匹配越精准。', 'hint')
        _rx = self.root.winfo_x() + self.root.winfo_width() + 10
        _ry = self.root.winfo_y()
        dlg.geometry(f'500x620+{_rx}+{_ry}')

    # # ─────────────────────────────────────────────────
    # # AI 章节查找（Ctrl+G）—— 模糊描述找章节
    # # ─────────────────────────────────────────────────
    # def open_chapter_finder(self):
    #     """用自然语言描述模糊记忆，AI 分析最匹配的章节"""
    #     if not self.chapters:
    #         messagebox.showinfo('提示', '请先打开小说'); return

    #     class State:
    #         running = False
    #         results = []   # [{'rank':int,'ch_idx':int,'ch_title':str,'reason':str,'score':int}]

    #     st  = State()
    #     _t  = self._cur_theme()
    #     _bg, _fg, _bar, _sel = _t['bg'], _t['fg'], _t['bar'], _t['sel']

    #     dlg = tk.Toplevel(self.root)
    #     dlg.title('AI 章节查找')
    #     dlg.geometry('500x580')
    #     dlg.resizable(True, True)
    #     dlg.attributes('-topmost', True)
    #     dlg.configure(bg=_bg)

    #     # ── 顶部标题栏 ────────────────────────────────
    #     top = tk.Frame(dlg, bg=_bar, height=34)
    #     top.pack(fill='x'); top.pack_propagate(False)
    #     tk.Label(top, text='  🔍  AI 章节查找',
    #              font=('',10,'bold'), bg=_bar, fg=_fg).pack(side='left', padx=8, pady=7)
    #     tk.Label(top, text=f'共 {len(self.chapters)} 章',
    #              font=('',8), bg=_bar, fg=_sel).pack(side='right', padx=8)
    #     tk.Button(top, text='×', relief='flat', font=('',11),
    #               bg=_bar, fg=_fg, bd=0, command=dlg.destroy).pack(side='right', padx=4)

    #     tk.Frame(dlg, height=1, bg=_sel).pack(fill='x')

    #     # ── 输入区 ────────────────────────────────────
    #     inp_wrap = tk.Frame(dlg, bg=_bg)
    #     inp_wrap.pack(fill='x', padx=12, pady=(10, 0))

    #     tk.Label(inp_wrap,
    #              text='描述你记得的情节、场景、人物对话或感受（越具体越准确）：',
    #              font=('',9), bg=_bg, fg=_fg, anchor='w').pack(fill='x')

    #     inp = tk.Text(inp_wrap,
    #                   font=(self.font_fam, self.font_size),
    #                   bg=_bar, fg=_fg, insertbackground=_fg,
    #                   relief='flat', padx=10, pady=8,
    #                   wrap='word', height=4,
    #                   borderwidth=1, highlightthickness=1,
    #                   highlightbackground=_sel, highlightcolor=_fg)
    #     inp.pack(fill='x', pady=(4, 0))

    #     # 占位提示文字
    #     _PH = '例如：有一章写到主角第一次失败，很沮丧，在雨中独自走路……'
    #     inp.insert('1.0', _PH)
    #     inp.config(fg=_sel)
    #     def _focus_in(e):
    #         if inp.get('1.0','end-1c') == _PH:
    #             inp.delete('1.0','end'); inp.config(fg=_fg)
    #     def _focus_out(e):
    #         if not inp.get('1.0','end-1c').strip():
    #             inp.insert('1.0', _PH); inp.config(fg=_sel)
    #     inp.bind('<FocusIn>',  _focus_in)
    #     inp.bind('<FocusOut>', _focus_out)

    #     # 返回数量选择
    #     cnt_row = tk.Frame(inp_wrap, bg=_bg)
    #     cnt_row.pack(fill='x', pady=(6,0))
    #     tk.Label(cnt_row, text='返回结果数：', font=('',8), bg=_bg, fg=_fg).pack(side='left')
    #     v_cnt = tk.IntVar(value=3)
    #     for _n in (1, 3, 5):
    #         tk.Radiobutton(cnt_row, text=f'Top {_n}', variable=v_cnt, value=_n,
    #                        font=('',8), bg=_bg, fg=_fg,
    #                        activebackground=_bg, selectcolor=_bar).pack(side='left', padx=6)
    #     tk.Label(cnt_row, text='（范围越小越精准）',
    #              font=('',8), bg=_bg, fg=_sel).pack(side='left', padx=4)

    #     tk.Frame(dlg, height=1, bg=_sel).pack(fill='x', pady=(10,0))

    #     # ── 结果展示区（上：列表 / 下：详情） ─────────
    #     pane = tk.PanedWindow(dlg, orient='vertical', bg=_bg,
    #                           sashwidth=5, sashrelief='flat', sashpad=2)
    #     pane.pack(fill='both', expand=True, padx=0, pady=0)

    #     # 上半：结果列表
    #     list_frame = tk.Frame(pane, bg=_bg)
    #     pane.add(list_frame, height=200)

    #     _lsb = tk.Scrollbar(list_frame, width=6)
    #     _lsb.pack(side='right', fill='y')
    #     result_lb = tk.Listbox(list_frame,
    #                            font=('',10), relief='flat',
    #                            bg=_bg, fg=_fg,
    #                            selectbackground=_sel, selectforeground=_fg,
    #                            borderwidth=0, highlightthickness=0,
    #                            activestyle='none', yscrollcommand=_lsb.set)
    #     result_lb.pack(fill='both', expand=True)
    #     _lsb.config(command=result_lb.yview)

    #     # 下半：理由详情
    #     detail_frame = tk.Frame(pane, bg=_bg)
    #     pane.add(detail_frame, height=140)

    #     detail = tk.Text(detail_frame,
    #                      font=(self.font_fam, self.font_size),
    #                      bg=_bar, fg=_fg,
    #                      insertbackground=_fg, relief='flat',
    #                      padx=14, pady=10, wrap='word',
    #                      borderwidth=0, highlightthickness=0, state='disabled')
    #     detail.pack(fill='both', expand=True)
    #     detail.tag_config('title',  font=(self.font_fam, self.font_size, 'bold'))
    #     detail.tag_config('score',  foreground=_sel)
    #     detail.tag_config('reason', foreground=_fg)
    #     detail.tag_config('hint',   foreground=_sel,
    #                       font=(self.font_fam, self.font_size, 'italic'))
    #     detail.tag_config('warn',   foreground='#cc241d')

    #     tk.Frame(dlg, height=1, bg=_sel).pack(fill='x')

    #     # ── 底部操作栏 ────────────────────────────────
    #     bot = tk.Frame(dlg, bg=_bar, height=46)
    #     bot.pack(fill='x', side='bottom'); bot.pack_propagate(False)

    #     btn_find = tk.Button(bot, text='🔍  开始分析',
    #                          font=('',10,'bold'),
    #                          bg=_fg, fg=_bg,
    #                          activebackground=_sel, activeforeground=_fg,
    #                          relief='flat', bd=0, padx=16, pady=4, cursor='hand2')
    #     btn_find.pack(side='left', padx=12, pady=8)

    #     btn_goto = tk.Button(bot, text='↩ 跳转到此章', font=('',9),
    #                          bg=_bar, fg=_fg, relief='flat', padx=8,
    #                          state='disabled', cursor='hand2')
    #     btn_goto.pack(side='left', padx=4, pady=8)

    #     lbl_st2 = tk.Label(bot, text='', font=('',8), bg=_bar, fg=_sel)
    #     lbl_st2.pack(side='right', padx=12)

    #     # ── 内部函数 ──────────────────────────────────
    #     def _show_detail(text, tag='hint'):
    #         detail.config(state='normal')
    #         detail.delete('1.0', 'end')
    #         detail.insert('end', text, tag)
    #         detail.config(state='disabled')

    #     def _show_detail_rich(title, score, reason):
    #         """带格式地展示单条匹配理由"""
    #         detail.config(state='normal')
    #         detail.delete('1.0', 'end')
    #         detail.insert('end', f'{title}\n', 'title')
    #         detail.insert('end', f'匹配度：{"★" * min(score,5)}{"☆" * max(0,5-score)}  {score}/5\n', 'score')
    #         detail.insert('end', f'\n{reason}', 'reason')
    #         detail.config(state='disabled')

    #     def _on_select(event=None):
    #         idxs = result_lb.curselection()
    #         if not idxs or not st.results: return
    #         _item = st.results[idxs[0]]
    #         _show_detail_rich(_item['ch_title'], _item['score'], _item['reason'])
    #         btn_goto.config(state='normal',
    #                         command=lambda i=_item['ch_idx']: (dlg.destroy(), self.goto_chapter(i)))

    #     result_lb.bind('<<ListboxSelect>>', _on_select)
    #     result_lb.bind('<Double-Button-1>',
    #                    lambda e: btn_goto.invoke() if btn_goto['state']=='normal' else None)

    #     def _on_find_success(results):
    #         st.running = False
    #         st.results = results
    #         btn_find.config(state='normal', text='🔍  重新分析')
    #         result_lb.delete(0, 'end')
    #         if not results:
    #             _show_detail('未找到匹配章节，请换一种描述方式。', 'hint')
    #             lbl_st2.config(text='未找到结果')
    #             return
    #         for _r in results:
    #             _stars = '★' * min(_r['score'], 5)
    #             result_lb.insert('end',
    #                 f"  第{_r['ch_idx']+1}章  {_r['ch_title'][:24]}  {_stars}")
    #         lbl_st2.config(text=f'找到 {len(results)} 个匹配')
    #         # 自动选中第一条
    #         result_lb.selection_set(0)
    #         _on_select()

    #     def _on_find_error(msg):
    #         st.running = False
    #         btn_find.config(state='normal', text='🔍  开始分析')
    #         if msg == 'NO_KEY':
    #             _show_detail(
    #                 '⚠  未找到 API Key\n\n'
    #                 '请在程序同目录新建 api_key.txt，\n'
    #                 '填入智谱 API Key 保存即可。\n'
    #                 '申请：https://open.bigmodel.cn',
    #                 'warn'
    #             )
    #         else:
    #             _show_detail(f'⚠  分析失败\n\n{msg}', 'warn')
    #         lbl_st2.config(text='')

    #     def _do_find():
    #         _query = inp.get('1.0','end-1c').strip()
    #         if not _query or _query == _PH:
    #             inp.focus(); return
    #         if st.running: return
    #         st.running = True
    #         st.results = []
    #         result_lb.delete(0, 'end')
    #         btn_find.config(state='disabled', text='分析中…')
    #         btn_goto.config(state='disabled')
    #         lbl_st2.config(text='')
    #         _show_detail('正在分析全书章节，请稍候…', 'hint')

    #         _top_n = v_cnt.get()
    #         # 构建章节目录摘要（每章取前120字）
    #         _toc_lines = []
    #         for _i, _ch in enumerate(self.chapters):
    #             _preview = _ch['body'][:30].replace('\n', ' ').strip()
    #             _toc_lines.append(f"第{_i+1}章《{_ch['title']}》：{_preview}…")
    #         _toc_text = '\n'.join(_toc_lines)

    #         def worker():
    #             import urllib.request as _ureq
    #             import urllib.error   as _uerr
    #             import json           as _ujson

    #             _key = _inject_api_key()
    #             if not _key:
    #                 dlg.after(0, lambda: _on_find_error('NO_KEY'))
    #                 return

    #             _prompt = (
    #                 f"我在读一本小说，对某个章节有模糊印象，请帮我找出最匹配的章节。\n\n"
    #                 f"【我的描述】\n{_query}\n\n"
    #                 f"【全书章节目录与内容预览】\n{_toc_text}\n\n"
    #                 f"请从上面的章节中选出最匹配的 {_top_n} 个，"
    #                 f"以 JSON 数组格式返回，每项包含：\n"
    #                 f"  ch_idx（从0开始的章节序号，整数）\n"
    #                 f"  ch_title（章节标题）\n"
    #                 f"  score（匹配度1-5分，整数）\n"
    #                 f"  reason（50字内说明匹配原因）\n\n"
    #                 f"只返回 JSON，不要任何其他文字，格式示例：\n"
    #                 f'[{{"ch_idx":2,"ch_title":"第三章","score":4,"reason":"..."}}]'
    #             )

    #             _payload = _ujson.dumps({
    #                 'model':       'glm-4-flash',
    #                 'max_tokens':  800,
    #                 'temperature': 0.3,
    #                 'messages':    [{'role': 'user', 'content': _prompt}],
    #             }).encode('utf-8')

    #             _req = _ureq.Request(
    #                 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
    #                 data    = _payload,
    #                 headers = {'Content-Type': 'application/json',
    #                            'Authorization': f'Bearer {_key}'},
    #                 method  = 'POST',
    #             )
    #             try:
    #                 with _ureq.urlopen(_req, timeout=40) as _resp:
    #                     _raw   = _resp.read().decode('utf-8')
    #                     _pdata = _ujson.loads(_raw)
    #                     _text  = _pdata['choices'][0]['message']['content'].strip()

    #                 # 清洗 JSON（模型可能带```json包裹）
    #                 _text = re.sub(r'^```[a-z]*\s*', '', _text, flags=re.I)
    #                 _text = re.sub(r'\s*```$', '', _text)
    #                 _parsed = _ujson.loads(_text)

    #                 # 校验并裁剪
    #                 _results = []
    #                 for _item in _parsed[:_top_n]:
    #                     _ci = int(_item.get('ch_idx', 0))
    #                     if 0 <= _ci < len(self.chapters):
    #                         _results.append({
    #                             'rank':     len(_results)+1,
    #                             'ch_idx':   _ci,
    #                             'ch_title': self.chapters[_ci]['title'],
    #                             'score':    max(1, min(5, int(_item.get('score', 3)))),
    #                             'reason':   str(_item.get('reason', ''))[:120],
    #                         })
    #                 dlg.after(0, lambda r=_results: _on_find_success(r))

    #             except _uerr.HTTPError as _he:
    #                 _hbody = _he.read().decode('utf-8', errors='replace')
    #                 try:    _hemsg = _ujson.loads(_hbody).get('error',{}).get('message', _hbody)
    #                 except: _hemsg = _hbody[:200]
    #                 _hcode = str(_he.code)
    #                 dlg.after(0, lambda c=_hcode, m=_hemsg: _on_find_error(f'HTTP {c}：{m}'))
    #             except Exception as _exc:
    #                 _emsg = str(_exc)
    #                 dlg.after(0, lambda m=_emsg: _on_find_error(m))

    #         threading.Thread(target=worker, daemon=True).start()

    #     btn_find.config(command=_do_find)
    #     inp.bind('<Control-Return>', lambda e: _do_find())

    #     # 初始提示
    #     _show_detail(
    #         '在上方输入框描述你记得的情节，\n'
    #         'AI 会分析全书章节目录，找出最匹配的章节。\n\n'
    #         '💡 描述越具体，匹配越准确。\n'
    #         '   可以描述场景、人物、对话、情绪，甚至只是一种感觉。',
    #         'hint'
    #     )

    #     _rx = self.root.winfo_x() + self.root.winfo_width() + 10
    #     _ry = self.root.winfo_y()
    #     dlg.geometry(f'500x580+{_rx}+{_ry}')
    # ─────────────────────────────────────────────────
    # 关闭时保存
    # ─────────────────────────────────────────────────
    def _on_close(self):
        self.tts.stop()
        self._shelf_update()
        self.root.destroy()

    # ─────────────────────────────────────────────────
    # 快捷键
    # ─────────────────────────────────────────────────
    def _bind_keys(self):
        r=self.root
        r.bind('<KeyPress-s>',   lambda e: self._scroll_down())
        r.bind('<KeyPress-S>',   lambda e: self._scroll_down())
        r.bind('<Right>',        lambda e: self.next_chapter())
        r.bind('<Left>',         lambda e: self.prev_chapter())
        r.bind('<Down>',         lambda e: self._scroll_down())
        r.bind('<Up>',           lambda e: self.txt.yview_scroll(-3,'units'))
        r.bind('<KeyPress-o>',   lambda e: self.add_mark())
        r.bind('<KeyPress-O>',   lambda e: self.add_mark())
        r.bind('<KeyPress-n>',   lambda e: self.add_note())
        r.bind('<KeyPress-N>',   lambda e: self.add_note())
        r.bind('<F5>',           lambda e: self.toggle_tts())
        r.bind('<Control-f>',    lambda e: self.open_search())
        r.bind('<Control-F>',    lambda e: self.open_search())
        r.bind('<Control-m>',    lambda e: self.open_summary())
        r.bind('<Control-M>',    lambda e: self.open_summary())
        r.bind('<Control-g>',    lambda e: self.open_chapter_finder())
        r.bind('<Control-G>',    lambda e: self.open_chapter_finder())
        r.bind('<KeyPress-d>',   self._dp)
        r.bind('<KeyPress-D>',   self._dp)
        r.bind('<KeyRelease-d>', self._dr)
        r.bind('<KeyRelease-D>', self._dr)
        r.bind('<KeyPress-e>',   self._ep)
        r.bind('<KeyPress-E>',   self._ep)
        r.focus_set()

    def _dp(self,e): self._d_held=True
    def _dr(self,e): self._d_held=False
    def _ep(self,e):
        if self._d_held: self.toggle_minimize()


# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    App()