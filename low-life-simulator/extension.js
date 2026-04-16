const vscode = require("vscode");
const { STATS, ACTIONS } = require("./gameData");
const {
  createInitialState,
  migrateState,
  startNewDay,
  setMode,
  setAiStatus,
  queueAiScene,
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
    await this.maybeGenerateAiScene("开局");
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
      if (message.mode === "ai") {
        await this.maybeGenerateAiScene("切换模式");
      }
      return;
    }

    if (message.type === "action") {
      await this.takeAction(message.actionId);
      return;
    }

    if (message.type === "resolveEvent") {
      const before = this.state;
      this.state = resolvePendingEvent(this.state, message.optionId);
      await this.persistAndRender();
      if (shouldRequestAiAfterResolve(before, this.state)) {
        await this.maybeGenerateAiScene("事件结算");
      }
      return;
    }

    if (message.type === "setApiKey") {
      await this.setApiKey();
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

    const before = this.state;
    this.state = applyAction(this.state, action);
    await this.persistAndRender();

    if (shouldRequestAiAfterAction(before, this.state)) {
      await this.maybeGenerateAiScene(action.label);
    }
  }

  async maybeGenerateAiScene(trigger) {
    if (!shouldRequestAiScene(this.state)) {
      return;
    }

    const apiKey = await this.context.secrets.get(SECRET_KEY);
    this.hasApiKey = Boolean(apiKey);

    if (!apiKey) {
      this.state = setAiStatus(this.state, "error", "AI 模式已开启，但还没有设置 MiniMax API Key。");
      await this.persistAndRender();
      return;
    }

    this.state = setAiStatus(this.state, "loading", "AI 正在根据当前状态生成事件...");
    await this.persistAndRender();

    try {
      const scene = await requestMiniMaxScene({
        apiKey,
        state: this.state,
        trigger,
        configuration: vscode.workspace.getConfiguration("lowLifeSimulator")
      });
      this.state = queueAiScene(this.state, scene);
    } catch (error) {
      const message = error && error.message ? error.message : String(error);
      this.state = setAiStatus(this.state, "error", `AI 事件生成失败：${message}`);
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
    const status = this.state.ai.status === "loading" ? " · 事件生成中" : "";
    this.statusBar.text = `$(briefcase) ${mode} ${formatTime(this.state.time)} 风险 ${this.state.stats.risk}%${status}`;
    this.statusBar.tooltip = `绩效 ${this.state.stats.performance}，心情 ${this.state.stats.mood}，金币 ${this.state.stats.money}`;
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

    <section class="mode-panel">
      <button id="offlineModeBtn">离线</button>
      <button id="aiModeBtn">AI</button>
      <button id="setApiKeyBtn" class="ghost">API Key</button>
    </section>

    <nav class="tabs">
      <button class="active" data-tab="status">状态</button>
      <button data-tab="logs">日志</button>
      <button data-tab="achievements">成就</button>
    </nav>

    <section id="statusTab" class="tab-view">
      <div class="panel stats" id="stats"></div>
      <div class="panel ai-strip" id="aiStrip" hidden></div>
      <div class="panel warning-panel" id="pendingPanel" hidden></div>
      <div class="panel">
        <div id="eventTitle" class="event-title">事件</div>
        <p id="eventText" class="event-text"></p>
      </div>
      <div class="panel" id="summaryPanel" hidden></div>
      <div class="panel" id="actionsPanel"></div>
    </section>

    <section id="logsTab" class="tab-view" hidden>
      <div class="panel compact-panel">
        <div id="logs" class="log-list"></div>
      </div>
    </section>

    <section id="achievementsTab" class="tab-view" hidden>
      <div class="panel compact-panel">
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

async function requestMiniMaxScene({ apiKey, state, trigger, configuration }) {
  const baseUrl = normalizeBaseUrl(configuration.get("minimaxBaseUrl") || "https://api.minimax.io/v1");
  const model = configuration.get("minimaxModel") || "MiniMax-M2.7-highspeed";
  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model,
      temperature: 0.9,
      messages: [
        {
          role: "system",
          content:
            "你是文字模拟器的回合导演。根据玩家当前数值，生成一个办公室随机事件和2到3个选项。只返回JSON，不要Markdown，不要解释。事件要短、具体、轻微幽默，且必须和当前数值风险相关。"
        },
        {
          role: "user",
          content: buildAiPrompt(state, trigger)
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
  if (!parsed || !parsed.title || !parsed.text) {
    throw new Error("MiniMax 返回内容不是事件 JSON。");
  }

  return parsed;
}

function buildAiPrompt(state, trigger) {
  const recentLogs = (state.logs || []).slice(-5).map((item) => `${item.time} ${item.title}: ${item.text}`);
  return JSON.stringify({
    request: "生成一个状态驱动事件。",
    trigger,
    output_schema: {
      title: "事件标题，12字以内",
      text: "事件描述，40字以内",
      message: "导演旁白，30字以内",
      effects: {
        energy: "可选，-15到15",
        mood: "可选，-15到15",
        performance: "可选，-15到15",
        slack: "可选，-15到15",
        risk: "可选，-15到15",
        money: "可选，-20到20"
      },
      options: [
        {
          label: "选项文案，10字以内",
          minutes: "0/15/30之一",
          effects: {
            energy: "可选，-20到20",
            mood: "可选，-20到20",
            performance: "可选，-20到20",
            slack: "可选，-20到20",
            risk: "可选，-20到20",
            money: "可选，-25到25"
          },
          result: "选项结果，36字以内"
        }
      ]
    },
    rules: [
      "优先根据风险、精力、心情、金币、绩效生成贴合局势的事件。",
      "如果风险高，事件更偏向暴露、问责、临时检查。",
      "如果精力低，事件更偏向疲惫、误操作、强制恢复。",
      "如果金币低，事件更偏向补给受限、额外赚钱机会。",
      "选项必须有取舍，不要全是好事。",
      "options 保持2到3个。"
    ],
    current_state: {
      day: state.day,
      mode: state.mode,
      time: formatTime(state.time),
      stats: state.stats,
      recentLogs
    }
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

function shouldRequestAiScene(state) {
  return state.mode === "ai" && state.phase === "playing" && !state.pendingEvent && state.ai.status !== "loading";
}

function shouldRequestAiAfterAction(before, after) {
  return (
    after.mode === "ai" &&
    after.phase === "playing" &&
    !after.pendingEvent &&
    after.counters.actions > before.counters.actions &&
    after.time > before.time
  );
}

function shouldRequestAiAfterResolve(before, after) {
  return (
    after.mode === "ai" &&
    after.phase === "playing" &&
    !after.pendingEvent &&
    before.pendingEvent &&
    before.pendingEvent.source === "emergency" &&
    after.time >= before.time
  );
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
    vscode.commands.registerCommand("lowLifeSimulator.clearApiKey", () => provider.clearApiKey())
  );
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
};
