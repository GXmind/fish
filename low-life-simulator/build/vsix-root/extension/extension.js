const vscode = require("vscode");
const { STATS, ACTIONS } = require("./gameData");
const {
  createInitialState,
  startNewDay,
  applyAction,
  formatTime,
  achievementTitleMap
} = require("./gameEngine");

const STORAGE_KEY = "lowLifeSimulator.state";

class LowLifeProvider {
  constructor(context) {
    this.context = context;
    this.view = undefined;
    this.state = context.globalState.get(STORAGE_KEY) || createInitialState();
    this.statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 80);
    this.statusBar.command = "lowLifeSimulator.open";
    context.subscriptions.push(this.statusBar);
    this.updateStatusBar();
  }

  resolveWebviewView(webviewView) {
    this.view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.context.extensionUri, "media")]
    };
    webviewView.webview.html = this.getHtml(webviewView.webview);
    webviewView.webview.onDidReceiveMessage((message) => this.handleMessage(message));
    this.postState();
  }

  async open() {
    await vscode.commands.executeCommand("workbench.view.extension.lowLifeSimulator");
    this.postState();
  }

  async startDay() {
    this.state = startNewDay(this.state);
    await this.persistAndRender();
  }

  async reset() {
    const answer = await vscode.window.showWarningMessage(
      "确定要重置低配人生的本地存档吗？",
      { modal: true },
      "重置"
    );
    if (answer !== "重置") {
      return;
    }

    this.state = createInitialState();
    await this.persistAndRender();
  }

  async handleMessage(message) {
    if (!message || typeof message.type !== "string") {
      return;
    }

    if (message.type === "ready") {
      this.postState();
      return;
    }

    if (message.type === "start") {
      await this.startDay();
      return;
    }

    if (message.type === "reset") {
      this.state = createInitialState();
      await this.persistAndRender();
      return;
    }

    if (message.type === "action") {
      await this.takeAction(message.actionId);
    }
  }

  async takeAction(actionId) {
    const action = ACTIONS.find((item) => item.id === actionId);
    if (!action) {
      return;
    }

    if (this.state.phase !== "playing") {
      this.state = startNewDay(this.state);
    }

    this.state = applyAction(this.state, action);
    await this.persistAndRender();
  }

  async persistAndRender() {
    await this.context.globalState.update(STORAGE_KEY, this.state);
    this.updateStatusBar();
    this.postState();
  }

  postState() {
    if (!this.view) {
      return;
    }

    this.view.webview.postMessage({
      type: "state",
      state: this.state,
      actions: ACTIONS.map(({ id, label, group, minutes }) => ({ id, label, group, minutes })),
      stats: STATS
    });
  }

  updateStatusBar() {
    if (!this.state || this.state.phase === "ready") {
      this.statusBar.text = "$(briefcase) 低配人生";
      this.statusBar.tooltip = "打开工位模拟器";
      this.statusBar.show();
      return;
    }

    if (this.state.phase === "ended") {
      this.statusBar.text = `$(briefcase) 低配人生 Day ${this.state.day} 已下班`;
      this.statusBar.tooltip = this.state.summary ? this.state.summary.title : "今日已结算";
      this.statusBar.show();
      return;
    }

    this.statusBar.text = `$(briefcase) ${formatTime(this.state.time)} 风险 ${this.state.stats.risk}%`;
    this.statusBar.tooltip = `低配人生：绩效 ${this.state.stats.performance}，心情 ${this.state.stats.mood}`;
    this.statusBar.show();
  }

  getHtml(webview) {
    const nonce = getNonce();
    const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, "media", "style.css"));
    const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, "media", "main.js"));
    const cspSource = webview.cspSource;
    const groupLabels = { work: "工作", slack: "摸鱼", rest: "补给", risky: "高风险" };

    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="${styleUri}">
  <title>低配人生</title>
</head>
<body>
  <main class="shell">
    <section class="topline">
      <div class="title">
        <h1>低配人生</h1>
        <div id="subtitle" class="muted">工位模拟器</div>
      </div>
      <div id="clock" class="clock">--:--</div>
    </section>

    <section class="toolbar">
      <button id="startBtn">开始新的一天</button>
      <button id="bossBtn" class="secondary">老板键</button>
      <button id="resetBtn" class="ghost">重置</button>
    </section>

    <nav class="tabs">
      <button class="active" data-tab="status">状态</button>
      <button data-tab="logs">日志</button>
      <button data-tab="achievements">成就</button>
    </nav>

    <section id="statusTab" class="tab-view">
      <div class="panel stats" id="stats"></div>
      <div class="panel">
        <div id="eventTitle" class="event-title">事件</div>
        <p id="eventText" class="event-text"></p>
      </div>
      <div class="panel" id="summaryPanel" hidden></div>
      <div class="panel" id="actionsPanel"></div>
    </section>

    <section id="logsTab" class="tab-view" hidden>
      <div class="panel">
        <div id="logs" class="log-list"></div>
      </div>
    </section>

    <section id="achievementsTab" class="tab-view" hidden>
      <div class="panel">
        <div id="achievements" class="achievement-list"></div>
      </div>
    </section>
  </main>

  <aside class="fake-terminal" id="fakeTerminal"></aside>

  <script nonce="${nonce}">
    window.lowLifeBootstrap = {
      groupLabels: ${JSON.stringify(groupLabels)},
      achievementTitles: ${JSON.stringify(achievementTitleMap())}
    };
  </script>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
  }
}

function getNonce() {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let text = "";
  for (let i = 0; i < 32; i += 1) {
    text += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return text;
}

function activate(context) {
  const provider = new LowLifeProvider(context);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider("lowLifeSimulator.sidebar", provider),
    vscode.commands.registerCommand("lowLifeSimulator.open", () => provider.open()),
    vscode.commands.registerCommand("lowLifeSimulator.startDay", () => provider.startDay()),
    vscode.commands.registerCommand("lowLifeSimulator.reset", () => provider.reset())
  );
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
};
