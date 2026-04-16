const vscode = require("vscode");
const { STATS, ACTIONS } = require("./gameData");
const {
  createInitialState,
  migrateState,
  startNewDay,
  setMode,
  setAiTasks,
  setAiStatus,
  applyAction,
  resolvePendingEvent,
  formatTime,
  achievementTitleMap
} = require("./gameEngine");

const STORAGE_KEY = "lowLifeSimulator.state";
const SECRET_KEY = "lowLifeSimulator.minimaxApiKey";

class LowLifeProvider {
  constructor(context) {
    this.context = context;
    this.view = undefined;
    this.hasApiKey = false;
    this.state = migrateState(context.globalState.get(STORAGE_KEY) || createInitialState());
    this.statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 80);
    this.statusBar.command = "lowLifeSimulator.open";
    context.subscriptions.push(this.statusBar);
    this.refreshApiKeyState();
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

  async setApiKey() {
    const apiKey = await vscode.window.showInputBox({
      title: "设置 MiniMax API Key",
      prompt: "API Key 会保存到 VS Code SecretStorage。",
      password: true,
      ignoreFocusOut: true
    });

    if (!apiKey) {
      return;
    }

    await this.context.secrets.store(SECRET_KEY, apiKey.trim());
    this.hasApiKey = true;
    vscode.window.showInformationMessage("MiniMax API Key 已保存。");
    this.postState();
  }

  async clearApiKey() {
    await this.context.secrets.delete(SECRET_KEY);
    this.hasApiKey = false;
    vscode.window.showInformationMessage("MiniMax API Key 已清除。");
    this.postState();
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

    if (message.type === "mode") {
      this.state = setMode(this.state, message.mode);
      await this.persistAndRender();
      return;
    }

    if (message.type === "action") {
      await this.takeAction(message.actionId);
      return;
    }

    if (message.type === "resolveEvent") {
      this.state = resolvePendingEvent(this.state, message.optionId);
      await this.persistAndRender();
      return;
    }

    if (message.type === "generateAiTasks") {
      await this.generateAiTasks();
      return;
    }

    if (message.type === "setApiKey") {
      await this.setApiKey();
    }
  }

  async takeAction(actionId) {
    const action =
      ACTIONS.find((item) => item.id === actionId) ||
      (this.state.ai.tasks || []).find((item) => item.id === actionId);
    if (!action) {
      return;
    }

    if (this.state.phase !== "playing") {
      this.state = startNewDay(this.state);
    }

    this.state = applyAction(this.state, action);
    await this.persistAndRender();
  }

  async generateAiTasks() {
    this.state = setMode(this.state, "ai");
    this.state = setAiStatus(this.state, "loading", "正在请求 MiniMax 生成任务...");
    await this.persistAndRender();

    const apiKey = await this.context.secrets.get(SECRET_KEY);
    if (!apiKey) {
      this.hasApiKey = false;
      this.state = setAiStatus(this.state, "error", "还没有设置 MiniMax API Key。");
      await this.persistAndRender();
      vscode.window.showWarningMessage("请先设置 MiniMax API Key。", "设置").then((answer) => {
        if (answer === "设置") {
          this.setApiKey();
        }
      });
      return;
    }

    this.hasApiKey = true;

    try {
      const result = await requestMiniMaxTasks({
        apiKey,
        state: this.state,
        configuration: vscode.workspace.getConfiguration("lowLifeSimulator")
      });
      this.state = setAiTasks(this.state, result.tasks, result.message);
    } catch (error) {
      const message = error && error.message ? error.message : String(error);
      this.state = setAiStatus(this.state, "error", `AI 任务生成失败：${message}`);
      vscode.window.showWarningMessage(`低配人生 AI 任务生成失败：${message}`);
    }

    await this.persistAndRender();
  }

  async refreshApiKeyState() {
    this.hasApiKey = Boolean(await this.context.secrets.get(SECRET_KEY));
    this.postState();
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
      actions: ACTIONS.map(({ id, label, group, minutes, cost, requires }) => ({
        id,
        label,
        group,
        minutes,
        cost: cost || 0,
        requires: requires || null
      })),
      stats: STATS,
      hasApiKey: this.hasApiKey
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

    const mode = this.state.mode === "ai" ? "AI" : "离线";
    this.statusBar.text = `$(briefcase) ${mode} ${formatTime(this.state.time)} 风险 ${this.state.stats.risk}%`;
    this.statusBar.tooltip = `绩效 ${this.state.stats.performance}，心情 ${this.state.stats.mood}，金币 ${this.state.stats.money}`;
    this.statusBar.show();
  }

  getHtml(webview) {
    const nonce = getNonce();
    const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, "media", "style.css"));
    const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, "media", "main.js"));
    const cspSource = webview.cspSource;
    const groupLabels = { work: "工作", slack: "摸鱼", rest: "补给", risky: "高风险", ai: "AI 任务" };

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

    <section class="mode-panel">
      <button id="offlineModeBtn" class="segmented">离线模式</button>
      <button id="aiModeBtn" class="segmented">AI 模式</button>
      <button id="setApiKeyBtn" class="ghost">API Key</button>
    </section>

    <nav class="tabs">
      <button class="active" data-tab="status">状态</button>
      <button data-tab="logs">日志</button>
      <button data-tab="achievements">成就</button>
    </nav>

    <section id="statusTab" class="tab-view">
      <div class="panel stats" id="stats"></div>
      <div class="panel warning-panel" id="pendingPanel" hidden></div>
      <div class="panel">
        <div id="eventTitle" class="event-title">事件</div>
        <p id="eventText" class="event-text"></p>
      </div>
      <div class="panel" id="aiPanel" hidden></div>
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

async function requestMiniMaxTasks({ apiKey, state, configuration }) {
  const baseUrl = normalizeBaseUrl(configuration.get("minimaxBaseUrl") || "https://api.minimax.io/v1");
  const model = configuration.get("minimaxModel") || "MiniMax-M2.7-highspeed";
  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model,
      temperature: 0.9,
      messages: [
        {
          role: "system",
          content:
            "你是一个 VS Code 侧边栏文字游戏的任务导演。只返回 JSON，不要 Markdown。任务要幽默、短小、适合办公室摸鱼模拟器。"
        },
        {
          role: "user",
          content: buildAiPrompt(state)
        }
      ]
    })
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${body.slice(0, 160)}`);
  }

  const data = await response.json();
  const content = data && data.choices && data.choices[0] && data.choices[0].message
    ? data.choices[0].message.content
    : "";
  const parsed = parseJsonFromText(content);
  if (!parsed || !Array.isArray(parsed.tasks)) {
    throw new Error("MiniMax 返回内容不是任务 JSON。");
  }

  return {
    message: parsed.message || "MiniMax 已生成 3 个随机任务。",
    tasks: parsed.tasks
  };
}

function buildAiPrompt(state) {
  const recentLogs = (state.logs || []).slice(-6).map((item) => `${item.time} ${item.title}: ${item.text}`);
  return JSON.stringify({
    request: "根据当前状态生成 3 个可执行任务。",
    output_schema: {
      message: "一句总结",
      tasks: [
        {
          label: "不超过 8 个汉字",
          minutes: "15/30/45 之一",
          effects: {
            energy: "数字 -30 到 30",
            mood: "数字 -30 到 30",
            performance: "数字 -30 到 30",
            slack: "数字 -30 到 30",
            risk: "数字 -30 到 30",
            money: "数字 -30 到 30"
          },
          log: "不超过 40 个汉字的结果描述"
        }
      ]
    },
    current_state: {
      day: state.day,
      time: formatTime(state.time),
      stats: state.stats,
      pendingEvent: state.pendingEvent ? state.pendingEvent.title : null,
      recentLogs
    },
    rules: [
      "任务必须有利弊，不要全是正收益。",
      "风险高时给出稳住局面的任务。",
      "金币低时可以给赚钱任务。",
      "精力低时不要给高强度办公任务。"
    ]
  });
}

function parseJsonFromText(text) {
  const trimmed = String(text || "").trim();
  try {
    return JSON.parse(trimmed);
  } catch {
    const start = trimmed.indexOf("{");
    const end = trimmed.lastIndexOf("}");
    if (start >= 0 && end > start) {
      return JSON.parse(trimmed.slice(start, end + 1));
    }
  }
  return null;
}

function normalizeBaseUrl(value) {
  return String(value || "https://api.minimax.io/v1").replace(/\/+$/, "");
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
    vscode.commands.registerCommand("lowLifeSimulator.reset", () => provider.reset()),
    vscode.commands.registerCommand("lowLifeSimulator.setApiKey", () => provider.setApiKey()),
    vscode.commands.registerCommand("lowLifeSimulator.clearApiKey", () => provider.clearApiKey()),
    vscode.commands.registerCommand("lowLifeSimulator.generateAiTasks", () => provider.generateAiTasks())
  );
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
};
