const vscode = acquireVsCodeApi();
const boot = window.lowLifeBootstrap || {};
const groupLabels = boot.groupLabels || {};
const achievementTitles = boot.achievementTitles || {};

let current = null;
let actions = [];
let stats = [];
let hasApiKey = false;
let activeTab = "status";

const elements = {
  subtitle: document.getElementById("subtitle"),
  clock: document.getElementById("clock"),
  startBtn: document.getElementById("startBtn"),
  bossBtn: document.getElementById("bossBtn"),
  resetBtn: document.getElementById("resetBtn"),
  offlineModeBtn: document.getElementById("offlineModeBtn"),
  aiModeBtn: document.getElementById("aiModeBtn"),
  setApiKeyBtn: document.getElementById("setApiKeyBtn"),
  stats: document.getElementById("stats"),
  pendingPanel: document.getElementById("pendingPanel"),
  eventTitle: document.getElementById("eventTitle"),
  eventText: document.getElementById("eventText"),
  summaryPanel: document.getElementById("summaryPanel"),
  actionsPanel: document.getElementById("actionsPanel"),
  aiPanel: document.getElementById("aiPanel"),
  logs: document.getElementById("logs"),
  achievements: document.getElementById("achievements"),
  fakeTerminal: document.getElementById("fakeTerminal")
};

window.addEventListener("message", (event) => {
  const message = event.data;
  if (!message || message.type !== "state") {
    return;
  }

  current = message.state;
  actions = message.actions || [];
  stats = message.stats || [];
  hasApiKey = Boolean(message.hasApiKey);
  render();
});

document.querySelectorAll(".tabs button").forEach((button) => {
  button.addEventListener("click", () => {
    activeTab = button.dataset.tab;
    renderTabs();
  });
});

elements.startBtn.addEventListener("click", () => {
  vscode.postMessage({ type: "start" });
});

elements.resetBtn.addEventListener("click", () => {
  if (confirm("重置低配人生的本地存档？")) {
    vscode.postMessage({ type: "reset" });
  }
});

elements.bossBtn.addEventListener("click", () => {
  document.body.classList.toggle("disguise");
  renderFakeTerminal();
});

elements.offlineModeBtn.addEventListener("click", () => {
  vscode.postMessage({ type: "mode", mode: "offline" });
});

elements.aiModeBtn.addEventListener("click", () => {
  vscode.postMessage({ type: "mode", mode: "ai" });
});

elements.setApiKeyBtn.addEventListener("click", () => {
  vscode.postMessage({ type: "setApiKey" });
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && document.body.classList.contains("disguise")) {
    document.body.classList.remove("disguise");
  }
});

function render() {
  if (!current) {
    return;
  }

  elements.clock.textContent = current.phase === "ready" ? "--:--" : formatTime(current.time);
  elements.subtitle.textContent = subtitleText(current);
  elements.startBtn.textContent = current.phase === "playing" ? "重新开始" : "开始新的一天";
  elements.offlineModeBtn.classList.toggle("active", current.mode !== "ai");
  elements.aiModeBtn.classList.toggle("active", current.mode === "ai");
  elements.setApiKeyBtn.textContent = hasApiKey ? "API Key 已设" : "API Key";

  renderStats();
  renderPendingEvent();
  renderEvent();
  renderAiPanel();
  renderSummary();
  renderActions();
  renderLogs();
  renderAchievements();
  renderTabs();
  renderFakeTerminal();
}

function renderStats() {
  elements.stats.innerHTML = "";
  for (const stat of stats) {
    const value = current.stats[stat.key] || 0;
    const percent = Math.round((value / stat.max) * 100);
    const danger =
      (stat.dangerLow && percent <= 15) ||
      (stat.dangerHigh && percent >= 85);
    const row = document.createElement("div");
    row.className = `stat-row ${stat.key}${danger ? " danger" : ""}`;
    row.innerHTML =
      `<span>${escapeHtml(stat.label)}</span>` +
      `<div class="bar"><span style="width:${percent}%"></span></div>` +
      `<span>${value}</span>`;
    elements.stats.appendChild(row);
  }
}

function renderPendingEvent() {
  const event = current.pendingEvent;
  if (!event) {
    elements.pendingPanel.hidden = true;
    elements.pendingPanel.innerHTML = "";
    return;
  }

  elements.pendingPanel.hidden = false;
  elements.pendingPanel.innerHTML =
    `<div class="event-title">紧急事件</div>` +
    `<p class="event-text"><strong>${escapeHtml(event.title)}</strong><br>${escapeHtml(event.text)}</p>` +
    `<div class="option-grid"></div>`;

  const grid = elements.pendingPanel.querySelector(".option-grid");
  for (const option of event.options || []) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "danger-button";
    button.textContent = option.label;
    button.title = optionTooltip(option);
    button.addEventListener("click", () => {
      vscode.postMessage({ type: "resolveEvent", optionId: option.id });
    });
    grid.appendChild(button);
  }
}

function renderEvent() {
  const last = current.lastEvent || { title: "事件", text: "" };
  elements.eventTitle.textContent = last.title;
  elements.eventText.textContent = last.text;
}

function renderAiPanel() {
  if (current.mode !== "ai") {
    elements.aiPanel.hidden = true;
    elements.aiPanel.innerHTML = "";
    return;
  }

  const ai = current.ai || {};
  elements.aiPanel.hidden = false;
  const status = ai.status === "loading" ? "生成中" : ai.status === "error" ? "异常" : "AI 模式";
  elements.aiPanel.innerHTML =
    `<div class="event-title">${status}</div>` +
    `<p class="event-text">${escapeHtml(ai.message || "可以让 MiniMax 根据当前状态生成随机任务。")}</p>` +
    `<div class="toolbar compact"><button id="generateAiBtn" ${ai.status === "loading" ? "disabled" : ""}>生成 AI 任务</button></div>`;

  elements.aiPanel.querySelector("#generateAiBtn").addEventListener("click", () => {
    vscode.postMessage({ type: "generateAiTasks" });
  });
}

function renderSummary() {
  if (!current.summary) {
    elements.summaryPanel.hidden = true;
    elements.summaryPanel.innerHTML = "";
    return;
  }

  const riskTax = current.summary.riskTax ? `<br>风险扣减 -${current.summary.riskTax}` : "";
  elements.summaryPanel.hidden = false;
  elements.summaryPanel.innerHTML =
    `<div class="event-title">今日结算</div>` +
    `<p class="event-text"><strong>${escapeHtml(current.summary.title)}</strong><br>` +
    `${escapeHtml(current.summary.text)}<br>金币 +${current.summary.reward}${riskTax}</p>`;
}

function renderActions() {
  elements.actionsPanel.innerHTML = "";
  const disabled = current.phase === "ended" || Boolean(current.pendingEvent);
  const allActions = actions.concat(current.mode === "ai" ? (current.ai.tasks || []) : []);
  const grouped = allActions.reduce((bucket, action) => {
    bucket[action.group] = bucket[action.group] || [];
    bucket[action.group].push(action);
    return bucket;
  }, {});

  for (const group of ["ai", "work", "slack", "rest", "risky"]) {
    const groupActions = grouped[group] || [];
    if (!groupActions.length) {
      continue;
    }

    const section = document.createElement("div");
    section.className = "group";
    section.innerHTML = `<div class="group-title">${escapeHtml(groupLabels[group] || group)}</div><div class="action-grid"></div>`;
    const grid = section.querySelector(".action-grid");

    for (const action of groupActions) {
      const button = document.createElement("button");
      button.type = "button";
      button.disabled = disabled;
      button.title = actionTooltip(action);
      button.innerHTML = `<span>${escapeHtml(action.label)}</span><small>${escapeHtml(actionMeta(action))}</small>`;
      button.addEventListener("click", () => {
        vscode.postMessage({ type: "action", actionId: action.id });
      });
      grid.appendChild(button);
    }

    elements.actionsPanel.appendChild(section);
  }

  if (current.pendingEvent) {
    appendHint("先处理上方紧急事件，普通行动暂停。");
  } else if (current.phase === "ended") {
    appendHint("今天已经下班。开始新的一天可以继续挑战。");
  }
}

function appendHint(text) {
  const hint = document.createElement("p");
  hint.className = "muted";
  hint.textContent = text;
  elements.actionsPanel.appendChild(hint);
}

function renderLogs() {
  elements.logs.innerHTML = "";
  const logs = (current.logs || []).slice().reverse();
  if (!logs.length) {
    elements.logs.innerHTML = `<div class="empty">暂无日志。</div>`;
    return;
  }

  for (const item of logs) {
    const node = document.createElement("div");
    node.className = "log-item";
    node.innerHTML =
      `<div class="log-meta"><span>${escapeHtml(item.title)}</span><span>${escapeHtml(item.time)}</span></div>` +
      `<div>${escapeHtml(item.text)}</div>`;
    elements.logs.appendChild(node);
  }
}

function renderAchievements() {
  elements.achievements.innerHTML = "";
  const ids = current.achievements || [];
  if (!ids.length) {
    elements.achievements.innerHTML = `<div class="empty">还没有成就。先活到下班。</div>`;
    return;
  }

  for (const id of ids) {
    const node = document.createElement("div");
    node.className = "achievement";
    node.textContent = achievementTitles[id] || id;
    elements.achievements.appendChild(node);
  }
}

function renderTabs() {
  document.querySelectorAll(".tabs button").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === activeTab);
  });
  document.getElementById("statusTab").hidden = activeTab !== "status";
  document.getElementById("logsTab").hidden = activeTab !== "logs";
  document.getElementById("achievementsTab").hidden = activeTab !== "achievements";
}

function renderFakeTerminal() {
  if (!current) {
    return;
  }

  const risk = current.stats ? current.stats.risk : 0;
  const performance = current.stats ? current.stats.performance : 0;
  const money = current.stats ? current.stats.money : 0;
  elements.fakeTerminal.textContent =
    "> npm run analyze-workday\n" +
    "[info] scanning active workspace...\n" +
    "[info] resolving productivity graph...\n" +
    `[info] mode=${current.mode || "offline"}\n` +
    "[info] current branch: feature/workday-simulation\n" +
    `[metric] performance_index=${performance}\n` +
    `[metric] context_risk=${risk}\n` +
    `[metric] budget_coins=${money}\n` +
    `[ok] report generated at ${new Date().toLocaleTimeString()}\n\n` +
    "Press Esc to return.";
}

function subtitleText(state) {
  const mode = state.mode === "ai" ? "AI 模式" : "离线模式";
  if (state.phase === "ready") {
    return `${mode} · 藏在侧边栏里的文字打工游戏`;
  }
  if (state.phase === "ended") {
    return `${mode} · Day ${state.day} 已下班`;
  }
  return `${mode} · Day ${state.day} 工位存活中`;
}

function actionMeta(action) {
  const parts = [`${action.minutes} 分钟`];
  if (action.cost) {
    parts.push(`-${action.cost} 金币`);
  }
  if (action.requires) {
    const requirements = Object.entries(action.requires).map(([key, value]) => `${statName(key)}>${value}`);
    parts.push(requirements.join(" "));
  }
  return parts.join(" · ");
}

function actionTooltip(action) {
  const effects = effectsText(action.effects);
  return effects ? `${actionMeta(action)}\n${effects}` : actionMeta(action);
}

function optionTooltip(option) {
  const parts = [];
  if (option.minutes) {
    parts.push(`${option.minutes} 分钟`);
  }
  if (option.cost) {
    parts.push(`-${option.cost} 金币`);
  }
  const effects = effectsText(option.effects);
  if (effects) {
    parts.push(effects);
  }
  return parts.join("\n");
}

function effectsText(effects) {
  return Object.entries(effects || {})
    .filter(([, value]) => Number(value) !== 0)
    .map(([key, value]) => `${statName(key)} ${Number(value) > 0 ? "+" : ""}${value}`)
    .join("，");
}

function statName(key) {
  const stat = stats.find((item) => item.key === key);
  return stat ? stat.label : key;
}

function formatTime(minutes) {
  const hour = String(Math.floor(minutes / 60)).padStart(2, "0");
  const minute = String(minutes % 60).padStart(2, "0");
  return `${hour}:${minute}`;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

vscode.postMessage({ type: "ready" });
