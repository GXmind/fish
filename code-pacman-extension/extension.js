const vscode = require("vscode");

const PLAYER_GLYPHS = {
  up: "^",
  down: "v",
  left: "<",
  right: ">"
};

const MONSTER_GLYPHS = ["M", "W"];
const BITE_FRAMES = ["@", "*", "."];
const BITE_FRAME_MS = 70;
const ENGINE_TICK_MS = 80;
const MONSTER_STEP_MS = 320;
const COMBO_WINDOW_MS = 900;
const STATUS_PULSE_MS = 500;

class GameSession {
  constructor(editor) {
    this.uri = editor.document.uri.toString();
    this.eol = editor.document.eol === vscode.EndOfLine.CRLF ? "\r\n" : "\n";
    this.originalSelections = editor.selections.map((selection) => selection);
    this.direction = "right";
    this.visible = false;
    this.bounds = createBounds(0, 0);
    this.baseLines = [];
    this.baseText = "";
    this.eaten = new Set();
    this.biteBursts = new Map();
    this.totalPellets = 0;
    this.player = { row: 0, col: 0 };
    this.spawnPoint = { row: 0, col: 0 };
    this.monsters = [];
    this.lives = 3;
    this.nextMonsterTickAt = 0;

    this.resetFromEditor(editor);
  }

  matchesEditor(editor) {
    return Boolean(editor) && editor.document.uri.toString() === this.uri;
  }

  resetFromEditor(editor) {
    this.bounds = resolveVisibleBounds(editor);
    this.resetSnapshot(editor.document);
  }

  resetFromDocument(document) {
    this.resetSnapshot(document);
  }

  resetSnapshot(document) {
    this.baseLines = Array.from({ length: document.lineCount }, (_, index) =>
      document.lineAt(index).text
    );
    this.baseText = this.baseLines.join(this.eol);
    this.bounds = normalizeBounds(this.bounds, this.baseLines.length);
    this.eaten = new Set();
    this.biteBursts = new Map();
    this.totalPellets = countPellets(this.baseLines, this.bounds);
    this.direction = "right";
    this.lives = 3;

    const start =
      findFirstCell(this.baseLines, this.bounds) ||
      findFirstCell(this.baseLines, createBounds(0, this.baseLines.length - 1));

    this.spawnPoint = start || { row: this.bounds.startRow, col: 0 };
    this.player = { ...this.spawnPoint };
    this.consume(this.player.row, this.player.col, { silent: true });
    this.monsters = createMonsterSpawns(this.baseLines, this.bounds, this.spawnPoint);
    this.nextMonsterTickAt = Date.now() + MONSTER_STEP_MS;
  }

  hasPlayableCells() {
    return this.totalPellets > 0;
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
    if (!line || col < 0 || col >= line.length || !isWithinBounds(row, this.bounds)) {
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

  movePlayer(direction) {
    this.direction = direction;

    const next = advancePosition(this.baseLines, this.bounds, this.player, direction);
    if (!next) {
      return { moved: false, consumed: false, caught: false };
    }

    this.player = next;
    const consumed = this.consume(next.row, next.col);
    return {
      moved: true,
      consumed,
      caught: this.hasMonsterAt(this.player)
    };
  }

  stepMonsters(now) {
    if (now < this.nextMonsterTickAt) {
      return { moved: false, caught: false };
    }

    this.nextMonsterTickAt = now + MONSTER_STEP_MS;
    const occupied = new Set();
    let moved = false;

    this.monsters = this.monsters.map((monster, index) => {
      const next = chooseMonsterStep(
        this.baseLines,
        this.bounds,
        monster,
        this.player,
        occupied
      );

      const resolved = next || monster;
      occupied.add(toKey(resolved.row, resolved.col));
      moved = moved || resolved.row !== monster.row || resolved.col !== monster.col;

      return {
        row: resolved.row,
        col: resolved.col,
        glyph: MONSTER_GLYPHS[index % MONSTER_GLYPHS.length]
      };
    });

    return {
      moved,
      caught: this.monsters.some((monster) => samePosition(monster, this.player))
    };
  }

  registerHit() {
    this.lives -= 1;

    if (this.lives <= 0) {
      return { defeated: true };
    }

    this.player = { ...this.spawnPoint };
    this.direction = "right";
    this.monsters = createMonsterSpawns(this.baseLines, this.bounds, this.spawnPoint);
    this.nextMonsterTickAt = Date.now() + MONSTER_STEP_MS;
    this.consume(this.player.row, this.player.col, { silent: true });

    return { defeated: false };
  }

  hasMonsterAt(position) {
    return this.monsters.some((monster) => samePosition(monster, position));
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

  render() {
    this.pruneBursts();
    const now = Date.now();
    const playerGlyph = PLAYER_GLYPHS[this.direction] || PLAYER_GLYPHS.right;
    const monsterMap = new Map(
      this.monsters.map((monster) => [toKey(monster.row, monster.col), monster.glyph])
    );

    return this.baseLines
      .map((line, row) => {
        if (!line.length) {
          return "";
        }

        const chars = Array.from(line);
        for (let col = 0; col < chars.length; col += 1) {
          if (!isWithinBounds(row, this.bounds)) {
            continue;
          }

          if (row === this.player.row && col === this.player.col) {
            chars[col] = playerGlyph;
            continue;
          }

          const key = toKey(row, col);
          const monsterGlyph = monsterMap.get(key);
          if (monsterGlyph) {
            chars[col] = monsterGlyph;
            continue;
          }

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
}

class CodePacmanController {
  constructor(context) {
    this.context = context;
    this.session = null;
    this.isInternalEdit = false;
    this.engineTimer = undefined;
    this.renderDrainScheduled = false;
    this.renderRequested = false;
    this.revealPending = false;
    this.combo = 0;
    this.lastChompAt = 0;
    this.statusPulseUntil = 0;
    this.editorTaskQueue = Promise.resolve();
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
      vscode.window.showWarningMessage("Open a code editor before starting Code Pacman.");
      return;
    }

    if (this.session && !this.session.matchesEditor(editor)) {
      const previousEditor = this.findSessionEditor();
      if (previousEditor && this.session.visible) {
        await this.hide(previousEditor, {
          keepSession: true,
          restoreSelections: true
        });
      } else if (this.session.visible) {
        vscode.window.showWarningMessage(
          "Go back to the game file, hide it with Ctrl+D, then switch files."
        );
        return;
      }
    }

    if (this.session && this.session.matchesEditor(editor)) {
      if (this.session.visible) {
        await this.hide(editor, { keepSession: true, restoreSelections: true });
        vscode.window.setStatusBarMessage(
          "Code Pacman hidden. Press Ctrl+D to resume.",
          2000
        );
        return;
      }

      if (editor.document.getText() !== this.session.baseText) {
        this.session.resetFromEditor(editor);
        vscode.window.showWarningMessage(
          "The code changed while the game was hidden, so the map was rebuilt."
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
      vscode.window.showWarningMessage(
        "There is no playable code in the current visible editor range."
      );
      return;
    }

    this.session = session;
    this.combo = 0;
    this.lastChompAt = 0;
    this.statusPulseUntil = 0;

    await this.show(editor);

    const rangeLabel = `${session.bounds.startRow + 1}-${session.bounds.endRow + 1}`;
    const saveHint = editor.document.isDirty
      ? "The file already has unsaved changes, so avoid saving while you play."
      : "Do not save the file while the game is visible. Esc safely restores the code.";

    vscode.window.showInformationMessage(
      `Code Pacman started in visible range lines ${rangeLabel}. Alt+Arrows move, ghosts chase, Ctrl+D hides, Esc exits. ${saveHint}`
    );
  }

  async show(editor) {
    if (!this.session || !this.session.matchesEditor(editor)) {
      return;
    }

    this.session.visible = true;
    await vscode.commands.executeCommand("setContext", "codePacman.running", true);
    this.updateStatusBar();
    this.requestRender({ revealPlayer: true });
    this.scheduleEngineTick();
  }

  async hide(editor, options = {}) {
    const { keepSession = false, restoreSelections = false } = options;
    if (!this.session || !this.session.matchesEditor(editor)) {
      return;
    }

    this.stopEngineLoop();
    this.session.visible = false;
    this.renderRequested = false;
    this.revealPending = false;

    await this.enqueueEditorTask(async () => {
      await this.replaceDocument(editor, this.session.baseText);
      if (restoreSelections) {
        editor.selections = this.session.originalSelections;
      }
    });

    await vscode.commands.executeCommand("setContext", "codePacman.running", false);

    if (!keepSession) {
      this.session = null;
      this.combo = 0;
      this.lastChompAt = 0;
      this.statusPulseUntil = 0;
    }

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
      this.stopEngineLoop();
      this.session = null;
      this.combo = 0;
      this.lastChompAt = 0;
      this.statusPulseUntil = 0;
      await vscode.commands.executeCommand("setContext", "codePacman.running", false);
      this.updateStatusBar();
    }

    vscode.window.setStatusBarMessage(
      "Code Pacman exited and the code was restored.",
      2000
    );
  }

  async move(direction) {
    const editor = vscode.window.activeTextEditor;
    if (!this.session || !this.session.visible || !this.session.matchesEditor(editor)) {
      return;
    }

    try {
      const result = this.session.movePlayer(direction);
      if (!result.moved) {
        return;
      }

      if (result.consumed) {
        this.registerChomp();
      }

      if (result.caught) {
        await this.handlePlayerCaught(editor);
        return;
      }

      this.requestRender({ revealPlayer: true });

      if (this.session.remaining === 0) {
        vscode.window.showInformationMessage(
          "You cleared the whole visible code range."
        );
      }
    } catch (error) {
      console.error("Code Pacman move failed:", error);
      vscode.window.showErrorMessage(
        "Code Pacman hit an input error and restored your code safely."
      );
      await this.exit();
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
        this.stopEngineLoop();
        this.session.visible = false;
        await vscode.commands.executeCommand("setContext", "codePacman.running", false);
      }
    }

    const editor = this.findSessionEditor();
    if (editor) {
      this.session.resetFromEditor(editor);
    } else {
      this.session.resetFromDocument(event.document);
    }

    this.combo = 0;
    this.lastChompAt = 0;
    this.statusPulseUntil = 0;
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

    this.stopEngineLoop();
    this.session.visible = false;
    await vscode.commands.executeCommand("setContext", "codePacman.running", false);
    this.updateStatusBar();
  }

  async handlePlayerCaught(editor) {
    this.statusPulseUntil = Date.now() + STATUS_PULSE_MS;
    this.combo = 0;

    const result = this.session.registerHit();
    if (result.defeated) {
      vscode.window.showWarningMessage("The ghosts caught you. Game over.");
      await this.hide(editor, { keepSession: false, restoreSelections: true });
      return;
    }

    vscode.window.setStatusBarMessage(
      `A ghost caught you. ${this.session.lives} lives left.`,
      1500
    );
    this.requestRender({ revealPlayer: true });
  }

  registerChomp() {
    const now = Date.now();
    this.combo = now - this.lastChompAt <= COMBO_WINDOW_MS ? this.combo + 1 : 1;
    this.lastChompAt = now;
    this.statusPulseUntil = now + STATUS_PULSE_MS;
  }

  scheduleEngineTick() {
    if (this.engineTimer || !this.session || !this.session.visible) {
      return;
    }

    this.engineTimer = setTimeout(() => {
      this.engineTimer = undefined;
      void this.runEngineTick();
    }, ENGINE_TICK_MS);
  }

  stopEngineLoop() {
    if (!this.engineTimer) {
      return;
    }

    clearTimeout(this.engineTimer);
    this.engineTimer = undefined;
  }

  async runEngineTick() {
    if (!this.session || !this.session.visible) {
      return;
    }

    try {
      const now = Date.now();
      let needsRender = this.session.hasActiveBursts();

      const monsterStep = this.session.stepMonsters(now);
      if (monsterStep.moved) {
        needsRender = true;
      }

      const editor = this.findSessionEditor();
      if (monsterStep.caught && editor) {
        await this.handlePlayerCaught(editor);
      } else if (needsRender) {
        this.requestRender({ revealPlayer: false });
      } else {
        this.updateStatusBar();
      }
    } catch (error) {
      console.error("Code Pacman engine tick failed:", error);
      vscode.window.showErrorMessage(
        "Code Pacman hit a render error and restored your code safely."
      );
      await this.exit();
      return;
    }

    if (this.session && this.session.visible) {
      this.scheduleEngineTick();
    }
  }

  requestRender(options = {}) {
    if (!this.session || !this.session.visible) {
      return;
    }

    if (options.revealPlayer) {
      this.revealPending = true;
    }

    this.renderRequested = true;
    if (this.renderDrainScheduled) {
      return;
    }

    this.renderDrainScheduled = true;
    void this.enqueueEditorTask(async () => {
      this.renderDrainScheduled = false;

      while (this.renderRequested) {
        this.renderRequested = false;

        if (!this.session || !this.session.visible) {
          break;
        }

        const editor = this.findSessionEditor();
        if (!editor) {
          break;
        }

        await this.replaceDocument(editor, this.session.render());
        if (this.revealPending) {
          this.revealPending = false;
          this.revealPlayer(editor);
        }

        this.updateStatusBar();
      }
    });
  }

  enqueueEditorTask(task) {
    this.editorTaskQueue = this.editorTaskQueue
      .then(task)
      .catch((error) => {
        console.error("Code Pacman editor task failed:", error);
      });

    return this.editorTaskQueue;
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

    const position = new vscode.Position(
      this.session.player.row,
      this.session.player.col
    );
    editor.selection = new vscode.Selection(position, position);
    editor.revealRange(
      new vscode.Range(position, position),
      vscode.TextEditorRevealType.InCenterIfOutsideViewport
    );
  }

  updateStatusBar() {
    if (!this.session) {
      this.statusBar.hide();
      return;
    }

    const isPulsing = Date.now() < this.statusPulseUntil;

    if (this.session.visible) {
      const comboText = isPulsing && this.combo > 0 ? `  CHOMP x${this.combo}` : "";
      this.statusBar.text =
        `Code Pacman ${this.session.score}/${this.session.totalPellets}` +
        `  Lives:${this.session.lives}  Ghosts:${this.session.monsters.length}` +
        `${comboText}  Alt+Arrows move  Ctrl+D hide  Esc exit`;
      this.statusBar.tooltip = "The current visible code range is the game map.";
    } else {
      this.statusBar.text =
        "Code Pacman hidden  Ctrl+D resume  Esc abandon";
      this.statusBar.tooltip =
        "The code is restored. Press Ctrl+D to continue the same run.";
    }

    this.statusBar.backgroundColor = isPulsing
      ? new vscode.ThemeColor("statusBarItem.warningBackground")
      : undefined;
    this.statusBar.show();
  }
}

function resolveVisibleBounds(editor) {
  const visibleRange = editor.visibleRanges[0];
  const lineCount = editor.document.lineCount;

  if (!visibleRange) {
    return createBounds(0, lineCount - 1);
  }

  return createBounds(visibleRange.start.line, visibleRange.end.line);
}

function createBounds(startRow, endRow) {
  return {
    startRow: Math.max(0, startRow),
    endRow: Math.max(0, endRow)
  };
}

function normalizeBounds(bounds, lineCount) {
  const maxLine = Math.max(lineCount - 1, 0);
  const startRow = clamp(bounds.startRow, 0, maxLine);
  const endRow = clamp(bounds.endRow, startRow, maxLine);
  return { startRow, endRow };
}

function countPellets(lines, bounds) {
  let total = 0;

  for (let row = bounds.startRow; row <= bounds.endRow; row += 1) {
    const line = lines[row] || "";
    for (const char of line) {
      if (!isWhitespace(char)) {
        total += 1;
      }
    }
  }

  return total;
}

function findFirstCell(lines, bounds) {
  let fallback = null;

  for (let row = bounds.startRow; row <= bounds.endRow; row += 1) {
    const line = lines[row] || "";
    if (!line.length) {
      continue;
    }

    if (!fallback) {
      fallback = { row, col: 0 };
    }

    for (let col = 0; col < line.length; col += 1) {
      if (!isWhitespace(line[col])) {
        return { row, col };
      }
    }
  }

  return fallback;
}

function createMonsterSpawns(lines, bounds, player) {
  const candidates = [];
  const fallbackCandidates = [];

  for (let row = bounds.endRow; row >= bounds.startRow; row -= 1) {
    const line = lines[row] || "";
    if (!line.length) {
      continue;
    }

    for (let col = line.length - 1; col >= 0; col -= 1) {
      const distance = manhattanDistance({ row, col }, player);
      if (distance < 8) {
        continue;
      }

      const entry = { row, col, distance };
      if (isWhitespace(line[col])) {
        fallbackCandidates.push(entry);
      } else {
        candidates.push(entry);
      }
    }
  }

  if (!candidates.length) {
    candidates.push(...fallbackCandidates);
  }

  candidates.sort((left, right) => right.distance - left.distance);
  const desiredCount = candidates.length > 120 ? 2 : 1;
  const monsters = [];
  const reserved = new Set([toKey(player.row, player.col)]);

  for (const candidate of candidates) {
    const key = toKey(candidate.row, candidate.col);
    if (reserved.has(key)) {
      continue;
    }

    reserved.add(key);
    monsters.push({
      row: candidate.row,
      col: candidate.col,
      glyph: MONSTER_GLYPHS[monsters.length % MONSTER_GLYPHS.length]
    });

    if (monsters.length >= desiredCount) {
      break;
    }
  }

  return monsters;
}

function chooseMonsterStep(lines, bounds, monster, player, occupied) {
  const directions = ["left", "right", "up", "down"];
  const options = [];

  for (const direction of directions) {
    const next = advancePosition(lines, bounds, monster, direction);
    if (!next) {
      continue;
    }

    const key = toKey(next.row, next.col);
    if (occupied.has(key) && !samePosition(next, player)) {
      continue;
    }

    options.push({
      position: next,
      score: manhattanDistance(next, player)
    });
  }

  if (!options.length) {
    return null;
  }

  options.sort((left, right) => left.score - right.score);
  return options[0].position;
}

function advancePosition(lines, bounds, from, direction) {
  const currentLine = lines[from.row] || "";

  if (direction === "left" && from.col > 0) {
    return { row: from.row, col: from.col - 1 };
  }

  if (direction === "right" && from.col < currentLine.length - 1) {
    return { row: from.row, col: from.col + 1 };
  }

  if (direction === "up" || direction === "down") {
    const delta = direction === "up" ? -1 : 1;

    for (
      let row = from.row + delta;
      row >= bounds.startRow && row <= bounds.endRow;
      row += delta
    ) {
      const targetLine = lines[row] || "";
      if (!targetLine.length) {
        continue;
      }

      return {
        row,
        col: Math.min(from.col, targetLine.length - 1)
      };
    }
  }

  return null;
}

function isWithinBounds(row, bounds) {
  return row >= bounds.startRow && row <= bounds.endRow;
}

function isWhitespace(char) {
  return /\s/.test(char);
}

function samePosition(left, right) {
  return left.row === right.row && left.col === right.col;
}

function manhattanDistance(left, right) {
  return Math.abs(left.row - right.row) + Math.abs(left.col - right.col);
}

function toKey(row, col) {
  return `${row}:${col}`;
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
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
