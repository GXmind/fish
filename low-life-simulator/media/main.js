const vscode = acquireVsCodeApi();
const boot = window.lowLifeBootstrap || {};
const groupLabels = boot.groupLabels || {};
const achievementTitles = boot.achievementTitles || {};

let current = null;
let actions = [];
let stats = [];
let activeTab = "status";

const elements = {
  subtitle: document.getElementById("subtitle"),
  clock: document.getElementById("clock"),
  startBtn: document.getElementById("startBtn"),
  bossBtn: document.getElementById("bossBtn"),
  resetBtn: document.getElementById("resetBtn"),
  stats: document.getElementById("stats"),
  eventTitle: document.getElementById("eventTitle"),
  eventText: document.getElementById("eventText"),
  summaryPanel: document.getElementById("summaryPanel"),
  actionsPanel: document.getElementById("actionsPanel"),
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
  renderStats();
  renderEvent();
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
    const row = document.createElement("div");
    row.className = `stat-row ${stat.key}`;
    row.innerHTML =
      `<span>${escapeHtml(stat.label)}</span>` +
      `<div class="bar"><span style="width:${percent}%"></span></div>` +
      `<span>${value}</span>`;
    elements.stats.appendChild(row);
  }
}

function renderEvent() {
  const last = current.lastEvent || { title: "事件", text: "" };
  elements.eventTitle.textContent = last.title;
  elements.eventText.textContent = last.text;
}

function renderSummary() {
  if (!current.summary) {
    elements.summaryPanel.hidden = true;
    elements.summaryPanel.innerHTML = "";
    return;
  }

  elements.summaryPanel.hidden = false;
  elements.summaryPanel.innerHTML =
    `<div class="event-title">今日结算</div>` +
    `<p class="event-text"><strong>${escapeHtml(current.summary.title)}</strong><br>` +
    `${escapeHtml(current.summary.text)}<br>金币 +${current.summary.reward}</p>`;
}

function renderActions() {
  elements.actionsPanel.innerHTML = "";
  const disabled = current.phase === "ended";
  const grouped = actions.reduce((bucket, action) => {
    bucket[action.group] = bucket[action.group] || [];
    bucket[action.group].push(action);
    return bucket;
  }, {});

  for (const group of ["work", "slack", "rest", "risky"]) {
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
      button.title = `${action.minutes} 分钟`;
      button.textContent = action.label;
      button.addEventListener("click", () => {
        vscode.postMessage({ type: "action", actionId: action.id });
      });
      grid.appendChild(button);
    }

    elements.actionsPanel.appendChild(section);
  }

  if (disabled) {
    const hint = document.createElement("p");
    hint.className = "muted";
    hint.textContent = "今天已经下班。开始新的一天可以继续挑战。";
    elements.actionsPanel.appendChild(hint);
  }
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
  elements.fakeTerminal.textContent =
    "> npm run analyze-workday\n" +
    "[info] scanning active workspace...\n" +
    "[info] resolving productivity graph...\n" +
    "[info] current branch: feature/workday-simulation\n" +
    `[metric] performance_index=${performance}\n` +
    `[metric] context_risk=${risk}\n` +
    `[ok] report generated at ${new Date().toLocaleTimeString()}\n\n` +
    "Press Esc to return.";
}

function subtitleText(state) {
  if (state.phase === "ready") {
    return "藏在侧边栏里的文字打工游戏";
  }
  if (state.phase === "ended") {
    return `Day ${state.day} 已下班`;
  }
  return `Day ${state.day} 工位存活中`;
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
