const vscode = require("vscode");

const DIRECTION_GLYPHS = {
  up: "^",
  down: "v",
  left: "<",
  right: ">"
};

const BITE_FRAMES = ["@", "*", "."];
const BITE_FRAME_MS = 70;
const COMBO_WINDOW_MS = 900;
const STATUS_PULSE_MS = 500;

class GameSession {
  constructor(editor) {
    this.uri = editor.document.uri.toString();
    this.eol = editor.document.eol === vscode.EndOfLine.CRLF ? "\r\n" : "\n";
    this.direction = "right";
    this.originalSelections = editor.selections.map((selection) => selection);
    this.visible = false;
    this.eaten = new Set();
    this.biteBursts = new Map();
    this.baseLines = [];
    this.baseText = "";
    this.totalPellets = 0;
    this.player = { row: 0, col: 0 };

    this.resetFromDocument(editor.document);
  }

  matchesEditor(editor) {
    return Boolean(editor) && editor.document.uri.toString() === this.uri;
  }

  resetFromDocument(document) {
    this.baseLines = Array.from({ length: document.lineCount }, (_, index) =>
      document.lineAt(index).text
    );
    this.baseText = this.baseLines.join(this.eol);
    this.totalPellets = countPellets(this.baseLines);
    this.eaten = new Set();
    this.biteBursts = new Map();

    const start = findFirstCell(this.baseLines);
    this.player = start || { row: 0, col: 0 };
    this.consume(this.player.row, this.player.col, { silent: true });
  }

  hasPlayableCells() {
    return this.baseLines.some((line) => line.length > 0);
  }

  get score() {
    return this.eaten.size;
  }

  get remaining() {
    return Math.max(this.totalPellets - this.score, 0);
  }

  consume(row, col, options = {}) {
    const { silent = false } = options;
    const line = this.baseLines[row];
    if (!line || col < 0 || col >= line.length) {
      return false;
    }

    if (!isWhitespace(line[col])) {
      const key = toKey(row, col);
      const isNew = !this.eaten.has(key);
      this.eaten.add(key);

      if (isNew && !silent) {
        this.biteBursts.set(key, Date.now());
      }

      return isNew;
    }

    return false;
  }

  move(direction) {
    this.direction = direction;

    const currentLine = this.baseLines[this.player.row] || "";
    let next = null;

    if (direction === "left" && this.player.col > 0) {
      next = { row: this.player.row, col: this.player.col - 1 };
    }

    if (direction === "right" && this.player.col < currentLine.length - 1) {
      next = { row: this.player.row, col: this.player.col + 1 };
    }

    if (direction === "up" || direction === "down") {
      const delta = direction === "up" ? -1 : 1;
      for (
        let row = this.player.row + delta;
        row >= 0 && row < this.baseLines.length;
        row += delta
      ) {
        const targetLine = this.baseLines[row];
        if (!targetLine || targetLine.length === 0) {
          continue;
        }

        next = {
          row,
          col: Math.min(this.player.col, targetLine.length - 1)
        };
        break;
      }
    }

    if (!next) {
      return { moved: false, consumed: false };
    }

    this.player = next;
    const consumed = this.consume(next.row, next.col);
    return { moved: true, consumed };
  }

  render() {
    this.pruneBursts();
    const glyph = DIRECTION_GLYPHS[this.direction] || DIRECTION_GLYPHS.right;
    const now = Date.now();

    return this.baseLines
      .map((line, row) => {
        if (!line.length) {
          return "";
        }

        const chars = Array.from(line);
        for (let col = 0; col < chars.length; col += 1) {
          if (row === this.player.row && col === this.player.col) {
            chars[col] = glyph;
            continue;
          }

          const key = toKey(row, col);
          const burstStartedAt = this.biteBursts.get(key);
          if (burstStartedAt) {
            const frameIndex = Math.min(
              Math.floor((now - burstStartedAt) / BITE_FRAME_MS),
              BITE_FRAMES.length - 1
            );
            chars[col] = BITE_FRAMES[frameIndex];
            continue;
          }

          if (!isWhitespace(line[col]) && this.eaten.has(key)) {
            chars[col] = " ";
          }
        }

        return chars.join("");
      })
      .join(this.eol);
  }

  pruneBursts() {
    const expiresAfter = BITE_FRAMES.length * BITE_FRAME_MS;
    const now = Date.now();

    for (const [key, startedAt] of this.biteBursts.entries()) {
      if (now - startedAt >= expiresAfter) {
        this.biteBursts.delete(key);
      }
    }
  }

  hasActiveBursts() {
    this.pruneBursts();
    return this.biteBursts.size > 0;
  }
}

class CodePacmanController {
  constructor(context) {
    this.context = context;
    this.session = null;
    this.isInternalEdit = false;
    this.animationTimer = undefined;
    this.combo = 0;
    this.lastChompAt = 0;
    this.statusPulseUntil = 0;
    this.statusBar = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left
    );

    context.subscriptions.push(this.statusBar);
    context.subscriptions.push(
      vscode.commands.registerCommand("codePacman.toggle", () => this.toggle()),
      vscode.commands.registerCommand("codePacman.exit", () => this.exit()),
      vscode.commands.registerCommand("codePacman.moveUp", () => this.move("up")),
      vscode.commands.registerCommand("codePacman.moveDown", () => this.move("down")),
      vscode.commands.registerCommand("codePacman.moveLeft", () => this.move("left")),
      vscode.commands.registerCommand("codePacman.moveRight", () => this.move("right")),
      vscode.workspace.onDidChangeTextDocument((event) =>
        this.handleExternalChange(event)
      ),
      vscode.window.onDidChangeVisibleTextEditors(() =>
        this.handleVisibleEditorsChange()
      )
    );
  }

  async toggle() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showWarningMessage("先打开一个代码编辑器，再启动 Code Pacman。");
      return;
    }

    if (this.session && !this.session.matchesEditor(editor)) {
      const previousEditor = this.findSessionEditor();
      if (previousEditor && this.session.visible) {
        await this.hide(previousEditor, { keepSession: true, restoreSelections: true });
      } else if (this.session.visible) {
        vscode.window.showWarningMessage(
          "请先回到游戏所在文件，按 Ctrl+D 恢复代码后再切换到别的文件。"
        );
        return;
      }
    }

    if (this.session && this.session.matchesEditor(editor)) {
      if (this.session.visible) {
        await this.hide(editor, { keepSession: true, restoreSelections: true });
        vscode.window.setStatusBarMessage("Code Pacman 已隐藏，再按 Ctrl+D 继续。", 2000);
        return;
      }

      if (editor.document.getText() !== this.session.baseText) {
        this.session.resetFromDocument(editor.document);
        vscode.window.showWarningMessage(
          "检测到你在隐藏期间改了代码，关卡已按最新代码重新生成。"
        );
      }

      await this.show(editor);
      return;
    }

    await this.start(editor);
  }

  async start(editor) {
    const session = new GameSession(editor);
    if (!session.hasPlayableCells()) {
      vscode.window.showWarningMessage("当前文件没有可玩的文本内容。");
      return;
    }

    this.session = session;
    await this.show(editor);

    this.combo = 0;
    this.lastChompAt = 0;
    this.statusPulseUntil = 0;
    const saveHint = editor.document.isDirty
      ? "当前文件本身就有未保存改动，建议谨慎试玩。"
      : "游戏期间不要保存文件，Esc 可安全退出并恢复代码。";

    vscode.window.showInformationMessage(
      `Code Pacman 已启动。Alt+方向键移动，Ctrl+D 秒切回代码，Esc 退出。${saveHint}`
    );
  }

  async show(editor) {
    if (!this.session || !this.session.matchesEditor(editor)) {
      return;
    }

    await this.replaceDocument(editor, this.session.render());
    this.session.visible = true;
    await vscode.commands.executeCommand("setContext", "codePacman.running", true);
    this.updateStatusBar();
    this.revealPlayer(editor);
  }

  async hide(editor, options = {}) {
    const { keepSession = false, restoreSelections = false } = options;
    if (!this.session || !this.session.matchesEditor(editor)) {
      return;
    }

    if (this.session.visible) {
      await this.replaceDocument(editor, this.session.baseText);
      this.session.visible = false;
    }

    if (restoreSelections) {
      editor.selections = this.session.originalSelections;
    }

    await vscode.commands.executeCommand("setContext", "codePacman.running", false);

    if (!keepSession) {
      this.session = null;
      this.combo = 0;
      this.lastChompAt = 0;
      this.statusPulseUntil = 0;
    }

    this.stopAnimationLoop();
    this.updateStatusBar();
  }

  async exit() {
    if (!this.session) {
      return;
    }

    const editor = this.findSessionEditor() || vscode.window.activeTextEditor;
    if (editor && this.session.matchesEditor(editor)) {
      await this.hide(editor, { keepSession: false, restoreSelections: true });
    } else {
      this.session = null;
      await vscode.commands.executeCommand("setContext", "codePacman.running", false);
      this.updateStatusBar();
    }

    vscode.window.setStatusBarMessage("Code Pacman 已退出，代码已恢复。", 2000);
  }

  async move(direction) {
    const editor = vscode.window.activeTextEditor;
    if (!this.session || !this.session.visible || !this.session.matchesEditor(editor)) {
      return;
    }

    const result = this.session.move(direction);
    if (!result.moved) {
      return;
    }

    if (result.consumed) {
      this.registerChomp();
    }

    await this.replaceDocument(editor, this.session.render());
    this.updateStatusBar();
    this.revealPlayer(editor);
    this.scheduleAnimationFrame();

    if (this.session.remaining === 0) {
      vscode.window.showInformationMessage("这一页代码已经被你吃光了。");
    }
  }

  async handleExternalChange(event) {
    if (!this.session || this.isInternalEdit) {
      return;
    }

    if (event.document.uri.toString() !== this.session.uri) {
      return;
    }

    if (this.session.visible) {
      const editor = this.findSessionEditor();
      if (editor) {
        await this.hide(editor, { keepSession: true, restoreSelections: true });
      } else {
        this.session.visible = false;
        await vscode.commands.executeCommand("setContext", "codePacman.running", false);
      }
    }

    this.session.resetFromDocument(event.document);
    this.combo = 0;
    this.lastChompAt = 0;
    this.statusPulseUntil = 0;
    this.stopAnimationLoop();
    this.updateStatusBar();
  }

  async handleVisibleEditorsChange() {
    if (!this.session || !this.session.visible) {
      return;
    }

    const editor = this.findSessionEditor();
    if (editor) {
      return;
    }

    this.session.visible = false;
    await vscode.commands.executeCommand("setContext", "codePacman.running", false);
    this.stopAnimationLoop();
    this.updateStatusBar();
  }

  findSessionEditor() {
    if (!this.session) {
      return undefined;
    }

    return vscode.window.visibleTextEditors.find(
      (editor) => editor.document.uri.toString() === this.session.uri
    );
  }

  async replaceDocument(editor, nextText) {
    const document = editor.document;
    const lastLine = document.lineAt(document.lineCount - 1);
    const fullRange = new vscode.Range(
      new vscode.Position(0, 0),
      new vscode.Position(document.lineCount - 1, lastLine.text.length)
    );

    this.isInternalEdit = true;
    try {
      await editor.edit(
        (editBuilder) => {
          editBuilder.replace(fullRange, nextText);
        },
        { undoStopBefore: false, undoStopAfter: false }
      );
    } finally {
      this.isInternalEdit = false;
    }
  }

  revealPlayer(editor) {
    if (!this.session || !this.session.matchesEditor(editor)) {
      return;
    }

    const row = this.session.player.row;
    const col = this.session.player.col;
    const position = new vscode.Position(row, col);
    editor.selection = new vscode.Selection(position, position);
    editor.revealRange(new vscode.Range(position, position), vscode.TextEditorRevealType.InCenterIfOutsideViewport);
  }

  registerChomp() {
    const now = Date.now();
    this.combo = now - this.lastChompAt <= COMBO_WINDOW_MS ? this.combo + 1 : 1;
    this.lastChompAt = now;
    this.statusPulseUntil = now + STATUS_PULSE_MS;
  }

  scheduleAnimationFrame() {
    if (this.animationTimer) {
      return;
    }

    this.animationTimer = setTimeout(async () => {
      this.animationTimer = undefined;

      if (!this.session || !this.session.visible || !this.session.hasActiveBursts()) {
        this.updateStatusBar();
        return;
      }

      const editor = this.findSessionEditor();
      if (!editor) {
        return;
      }

      await this.replaceDocument(editor, this.session.render());
      this.updateStatusBar();
      this.scheduleAnimationFrame();
    }, BITE_FRAME_MS);
  }

  stopAnimationLoop() {
    if (!this.animationTimer) {
      return;
    }

    clearTimeout(this.animationTimer);
    this.animationTimer = undefined;
  }

  updateStatusBar() {
    if (!this.session) {
      this.statusBar.hide();
      return;
    }

    const isPulsing = Date.now() < this.statusPulseUntil;

    if (this.session.visible) {
      const comboText = isPulsing ? `  CHOMP x${this.combo}` : "";
      this.statusBar.text = `Code Pacman ${this.session.score}/${this.session.totalPellets}${comboText}  Alt+方向移动  Ctrl+D 隐藏  Esc 退出`;
      this.statusBar.tooltip = isPulsing
        ? "刚刚吃到代码了，连着吃会叠加连击。"
        : "游戏显示中。不要保存文件，按 Ctrl+D 可快速恢复代码。";
    } else {
      this.statusBar.text = `Code Pacman 已隐藏  Ctrl+D 继续  Esc 放弃`;
      this.statusBar.tooltip = "代码已经恢复显示，再按 Ctrl+D 可以继续游戏。";
    }

    this.statusBar.backgroundColor = isPulsing
      ? new vscode.ThemeColor("statusBarItem.warningBackground")
      : undefined;
    this.statusBar.show();
  }
}

function countPellets(lines) {
  let total = 0;
  for (const line of lines) {
    for (const char of line) {
      if (!isWhitespace(char)) {
        total += 1;
      }
    }
  }

  return total;
}

function findFirstCell(lines) {
  for (let row = 0; row < lines.length; row += 1) {
    const line = lines[row];
    if (!line.length) {
      continue;
    }

    for (let col = 0; col < line.length; col += 1) {
      if (!isWhitespace(line[col])) {
        return { row, col };
      }
    }

    return { row, col: 0 };
  }

  return null;
}

function isWhitespace(char) {
  return /\s/.test(char);
}

function toKey(row, col) {
  return `${row}:${col}`;
}

function activate(context) {
  const controller = new CodePacmanController(context);
  context.subscriptions.push({
    dispose: () => controller.exit()
  });
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
};
