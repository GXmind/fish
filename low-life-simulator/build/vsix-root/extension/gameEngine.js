const { STATS, EVENTS, EMERGENCY_EVENTS, ACHIEVEMENTS } = require("./gameData");

const WORK_START = 9 * 60 + 30;
const WORK_END = 18 * 60;

function createInitialState() {
  return {
    version: 2,
    day: 0,
    phase: "ready",
    mode: "offline",
    time: WORK_START,
    stats: {
      energy: 68,
      mood: 56,
      performance: 38,
      slack: 18,
      risk: 12,
      money: 70
    },
    counters: {
      coffee: 0,
      meeting: 0,
      debug: 0,
      actions: 0,
      caught: 0,
      emergenciesResolved: 0,
      aiTasksCompleted: 0
    },
    achievements: [],
    ai: {
      status: "idle",
      message: "",
      tasks: []
    },
    pendingEvent: null,
    lastEvent: {
      title: "等待开工",
      text: "今天还没有开始。深呼吸，先假装自己很有计划。"
    },
    logs: [],
    summary: null
  };
}

function migrateState(saved) {
  const fresh = createInitialState();
  if (!saved || typeof saved !== "object") {
    return fresh;
  }

  return {
    ...fresh,
    ...saved,
    version: 2,
    stats: { ...fresh.stats, ...(saved.stats || {}) },
    counters: { ...fresh.counters, ...(saved.counters || {}) },
    ai: { ...fresh.ai, ...(saved.ai || {}) },
    pendingEvent: saved.pendingEvent || null,
    achievements: saved.achievements || [],
    logs: saved.logs || []
  };
}

function startNewDay(previous) {
  const migrated = migrateState(previous);
  const nextDay = migrated.phase === "ready" && migrated.day === 0 ? 1 : migrated.day + 1;
  return {
    ...createInitialState(),
    day: nextDay,
    phase: "playing",
    mode: migrated.mode || "offline",
    achievements: migrated.achievements || [],
    lastEvent: {
      title: "打卡成功",
      text: "你坐到工位前，屏幕亮起，今天的存活挑战开始了。"
    },
    logs: [
      {
        time: formatTime(WORK_START),
        title: "打卡成功",
        text: "你坐到工位前，屏幕亮起，今天的存活挑战开始了。"
      }
    ]
  };
}

function setMode(state, mode) {
  const next = migrateState(state);
  next.mode = mode === "ai" ? "ai" : "offline";
  if (next.mode === "offline") {
    next.ai.status = "idle";
    next.ai.message = "";
    next.ai.tasks = [];
  }
  addLog(next, next.mode === "ai" ? "已切换到 AI 模式。" : "已切换到离线模式。", "模式切换");
  unlockAchievements(next);
  return next;
}

function setAiTasks(state, tasks, message = "") {
  const next = migrateState(state);
  next.ai = {
    status: "ready",
    message: message || "AI 已根据当前状态生成任务。",
    tasks: sanitizeAiTasks(tasks)
  };
  addLog(next, next.ai.message, "AI 任务");
  return next;
}

function setAiStatus(state, status, message) {
  const next = migrateState(state);
  next.ai.status = status;
  next.ai.message = message || "";
  return next;
}

function applyAction(state, action) {
  const migrated = migrateState(state);
  if (migrated.phase !== "playing") {
    return startNewDay(migrated);
  }

  if (migrated.pendingEvent) {
    return withBlockedMessage(migrated, "先处理紧急事件", "当前有紧急事件未解决，普通行动已暂停。");
  }

  const blocked = getActionBlock(migrated, action);
  if (blocked) {
    return blocked;
  }

  if (isEntertainment(action) && shouldBeCaught(migrated, action)) {
    return applyCaughtEvent(migrated, action);
  }

  const next = cloneState(migrated);
  next.summary = null;
  next.counters.actions += 1;
  bumpCounters(next, action);

  applyEffects(next.stats, action.effects);
  advanceTime(next, action.minutes);
  addLog(next, action.log, action.source === "ai" ? "AI 任务" : "行动");

  const emergency = findEmergency(next);
  if (emergency) {
    setPendingEvent(next, emergency);
    unlockAchievements(next);
    return next;
  }

  const event = rollEvent(next, action);
  if (event) {
    applyEffects(next.stats, event.effects || {});
    next.lastEvent = { title: event.title, text: event.text };
    addLog(next, event.text, event.title);
  } else {
    next.lastEvent = {
      title: "平稳推进",
      text: "没有突发状况。办公室暂时维持表面和平。"
    };
  }

  if (action.source === "ai") {
    next.counters.aiTasksCompleted += 1;
    next.ai.tasks = (next.ai.tasks || []).filter((task) => task.id !== action.id);
  }

  unlockAchievements(next);
  maybeFinishDay(next);
  return next;
}

function resolvePendingEvent(state, optionId) {
  const migrated = migrateState(state);
  if (!migrated.pendingEvent) {
    return migrated;
  }

  const option = migrated.pendingEvent.options.find((item) => item.id === optionId);
  if (!option) {
    return migrated;
  }

  const blocked = getOptionBlock(migrated, option);
  if (blocked) {
    return blocked;
  }

  const next = cloneState(migrated);
  next.pendingEvent = null;
  next.counters.emergenciesResolved += 1;
  applyEffects(next.stats, option.effects || {});
  advanceTime(next, option.minutes || 0);
  next.lastEvent = {
    title: "紧急事件处理完成",
    text: option.result || "你处理了眼前的麻烦。"
  };
  addLog(next, option.result || "你处理了眼前的麻烦。", "紧急事件");

  const chained = findEmergency(next);
  if (chained) {
    setPendingEvent(next, chained);
  }

  unlockAchievements(next);
  maybeFinishDay(next);
  return next;
}

function getActionBlock(state, action) {
  if (action.group === "work" && state.stats.energy <= 12) {
    return withEmergency(state, "energy_crash");
  }

  if (action.group === "work" && state.stats.mood <= 6) {
    return withEmergency(state, "mood_crash");
  }

  if (action.cost && state.stats.money < action.cost) {
    return withBlockedMessage(
      state,
      "金币不足",
      `金币不足，无法执行「${action.label}」。先工作赚一点，或者选择不花钱的恢复方式。`
    );
  }

  if (action.requires) {
    const missing = Object.entries(action.requires).find(([key, min]) => state.stats[key] < min);
    if (missing) {
      const [key, min] = missing;
      return withBlockedMessage(state, "状态不足", `${statLabel(key)}低于 ${min}，无法执行「${action.label}」。`);
    }
  }

  return null;
}

function getOptionBlock(state, option) {
  if (option.cost && state.stats.money < option.cost) {
    return withBlockedMessage(state, "金币不足", `金币不足，无法选择「${option.label}」。`);
  }

  if (option.requires) {
    const missing = Object.entries(option.requires).find(([key, min]) => state.stats[key] < min);
    if (missing) {
      const [key, min] = missing;
      return withBlockedMessage(state, "状态不足", `${statLabel(key)}低于 ${min}，无法选择「${option.label}」。`);
    }
  }

  return null;
}

function applyCaughtEvent(state, action) {
  const next = cloneState(state);
  const fine = Math.min(35, Math.max(8, 8 + Math.floor(next.stats.risk / 4)));
  const performanceHit = action.group === "risky" ? -18 : -11;

  next.counters.actions += 1;
  next.counters.caught += 1;
  bumpCounters(next, action);
  applyEffects(next.stats, {
    money: -fine,
    performance: performanceHit,
    mood: -10,
    risk: -22,
    slack: 6,
    energy: -2
  });
  advanceTime(next, action.minutes);

  next.lastEvent = {
    title: "摸鱼被抓",
    text: `风险过高时执行「${action.label}」被抓，扣除 ${fine} 金币，绩效也被记了一笔。`
  };
  addLog(next, next.lastEvent.text, "摸鱼被抓");

  if (next.stats.risk >= 70 || next.stats.performance <= 10) {
    setPendingEvent(next, {
      id: "caught_followup",
      title: "紧急事件：被要求说明情况",
      text: "刚才的抓包还没完全过去，你需要选择一种方式稳住局面。",
      options: [
        { id: "write_report", label: "写进度说明", minutes: 30, effects: { performance: 10, risk: -18, mood: -5 }, result: "你写了一份进度说明，局面被压住了。" },
        { id: "fix_visible_bug", label: "修一个显眼 Bug", minutes: 30, requires: { energy: 14 }, effects: { energy: -12, performance: 16, risk: -20, money: 4 }, result: "你修了一个显眼 Bug，重新获得一点信任。" }
      ]
    });
  }

  unlockAchievements(next);
  maybeFinishDay(next);
  return next;
}

function withEmergency(state, emergencyId) {
  const next = cloneState(state);
  const emergency = EMERGENCY_EVENTS.find((item) => item.id === emergencyId);
  if (emergency) {
    setPendingEvent(next, emergency);
  }
  return next;
}

function withBlockedMessage(state, title, text) {
  const next = cloneState(state);
  next.lastEvent = { title, text };
  addLog(next, text, title);
  return next;
}

function findEmergency(state) {
  return EMERGENCY_EVENTS.find((event) => event.condition(state)) || null;
}

function setPendingEvent(state, event) {
  state.pendingEvent = {
    id: event.id,
    title: event.title,
    text: event.text,
    options: event.options.map((option) => ({
      id: option.id,
      label: option.label,
      minutes: option.minutes || 0,
      cost: option.cost || 0,
      requires: option.requires || null,
      effects: option.effects || {},
      result: option.result || ""
    }))
  };
  state.lastEvent = { title: event.title, text: event.text };
  addLog(state, event.text, event.title);
}

function shouldBeCaught(state, action) {
  if (state.stats.risk >= 85) {
    return true;
  }

  const base = action.group === "risky" ? 0.35 : 0.18;
  const riskBonus = Math.max(0, state.stats.risk - 60) / 100;
  return Math.random() < base + riskBonus;
}

function isEntertainment(action) {
  return action.group === "slack" || action.group === "risky";
}

function rollEvent(state, action) {
  const chance = action.group === "risky" ? 0.7 : action.group === "slack" ? 0.58 : 0.44;
  if (Math.random() > chance) {
    return null;
  }

  const candidates = EVENTS.filter((event) => {
    const hasTag = event.tags.includes("any") || event.tags.includes(action.group);
    const passesCondition = !event.condition || event.condition(state);
    return hasTag && passesCondition;
  });

  if (!candidates.length) {
    return null;
  }

  return candidates[Math.floor(Math.random() * candidates.length)];
}

function finishDay(state) {
  state.phase = "ended";
  state.pendingEvent = null;
  const stats = state.stats;
  let title = "普通存活";
  let text = "你成功撑到了下班。今天没有奇迹，但也没有事故。";
  let reward = 18;

  if (stats.performance >= 82 && stats.risk < 45) {
    title = "稳定输出";
    text = "你看起来很忙，实际上也确实做了不少事。";
    reward = 45;
  } else if (stats.performance >= 72 && stats.slack >= 45) {
    title = "可疑但高效";
    text = "你的摸鱼痕迹不少，但产出居然也说得过去。";
    reward = 36;
  } else if (stats.risk >= 75) {
    title = "危险边缘";
    text = "你离翻车很近，但下班铃声救了你。";
    reward = 8;
  } else if (stats.mood >= 78) {
    title = "情绪稳定";
    text = "工作未必推进很多，但你保住了精神世界。";
    reward = 26;
  } else if (stats.energy <= 18) {
    title = "电量见底";
    text = "你像一个即将休眠的设备，安静而顽强。";
    reward = 14;
  }

  const riskTax = stats.risk >= 70 ? 12 : 0;
  const actualReward = Math.max(0, reward - riskTax);
  state.stats.money = clamp(state.stats.money + actualReward, 0, statMax("money"));
  state.summary = { title, text, reward: actualReward, riskTax };
  state.lastEvent = { title: "今日结算", text: `${title}：${text} 金币 +${actualReward}` };
  addLog(state, `${title}：${text} 金币 +${actualReward}`, "今日结算");
  unlockAchievements(state);
}

function maybeFinishDay(state) {
  if (state.time >= WORK_END) {
    finishDay(state);
  }
}

function unlockAchievements(state) {
  const owned = new Set(state.achievements);
  for (const achievement of ACHIEVEMENTS) {
    if (!owned.has(achievement.id) && achievement.test(state)) {
      owned.add(achievement.id);
      state.achievements.push(achievement.id);
      addLog(state, `解锁成就：${achievement.title}`, "成就");
    }
  }
}

function bumpCounters(state, action) {
  if (action.id === "coffee") {
    state.counters.coffee += 1;
  }
  if (action.id === "meeting" || action.id === "fakeMeeting") {
    state.counters.meeting += 1;
  }
  if (action.id === "debug") {
    state.counters.debug += 1;
  }
}

function applyEffects(stats, effects) {
  for (const [key, delta] of Object.entries(effects || {})) {
    if (typeof stats[key] !== "number") {
      continue;
    }
    stats[key] = clamp(stats[key] + Number(delta || 0), 0, statMax(key));
  }
}

function addLog(state, text, title) {
  state.logs.push({ time: formatTime(state.time), title, text });
  if (state.logs.length > 100) {
    state.logs = state.logs.slice(state.logs.length - 100);
  }
}

function advanceTime(state, minutes) {
  state.time = Math.min(state.time + Number(minutes || 0), WORK_END);
}

function formatTime(minutes) {
  const hour = String(Math.floor(minutes / 60)).padStart(2, "0");
  const minute = String(minutes % 60).padStart(2, "0");
  return `${hour}:${minute}`;
}

function achievementTitleMap() {
  return Object.fromEntries(ACHIEVEMENTS.map((item) => [item.id, item.title]));
}

function statLabel(key) {
  const stat = STATS.find((item) => item.key === key);
  return stat ? stat.label : key;
}

function statMax(key) {
  const stat = STATS.find((item) => item.key === key);
  return stat ? stat.max : 100;
}

function sanitizeAiTasks(tasks) {
  if (!Array.isArray(tasks)) {
    return [];
  }

  return tasks.slice(0, 3).map((task, index) => ({
    id: `ai_${Date.now()}_${index}`,
    source: "ai",
    group: "ai",
    label: clampText(task.label || `AI 任务 ${index + 1}`, 18),
    minutes: clamp(Number(task.minutes || 15), 15, 45),
    effects: sanitizeEffects(task.effects),
    log: clampText(task.log || task.description || "AI 给你安排了一个随机任务。", 80)
  }));
}

function sanitizeEffects(effects) {
  const result = {};
  const allowed = new Set(STATS.map((item) => item.key));
  for (const [key, value] of Object.entries(effects || {})) {
    if (allowed.has(key)) {
      result[key] = clamp(Number(value || 0), -30, 30);
    }
  }
  return result;
}

function clampText(text, maxLength) {
  const value = String(text).replace(/\s+/g, " ").trim();
  return value.length > maxLength ? value.slice(0, maxLength) : value;
}

function cloneState(state) {
  return JSON.parse(JSON.stringify(state));
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

module.exports = {
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
};
