const { STATS, EVENTS, ACHIEVEMENTS } = require("./gameData");

const WORK_START = 9 * 60 + 30;
const WORK_END = 18 * 60;

function createInitialState() {
  return {
    version: 1,
    day: 0,
    phase: "ready",
    time: WORK_START,
    stats: {
      energy: 68,
      mood: 56,
      performance: 38,
      slack: 18,
      risk: 12,
      money: 50
    },
    counters: {
      coffee: 0,
      meeting: 0,
      debug: 0,
      actions: 0
    },
    achievements: [],
    lastEvent: {
      title: "等待开工",
      text: "今天还没有开始。深呼吸，先假装自己很有计划。"
    },
    logs: [],
    summary: null
  };
}

function startNewDay(previous) {
  const nextDay = previous.phase === "ready" && previous.day === 0 ? 1 : previous.day + 1;
  return {
    ...createInitialState(),
    day: nextDay,
    phase: "playing",
    achievements: previous.achievements || [],
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

function applyAction(state, action) {
  const next = cloneState(state);
  next.summary = null;
  next.counters.actions += 1;

  if (action.id === "coffee") {
    next.counters.coffee += 1;
  }
  if (action.id === "meeting" || action.id === "fakeMeeting") {
    next.counters.meeting += 1;
  }
  if (action.id === "debug") {
    next.counters.debug += 1;
  }

  applyEffects(next.stats, action.effects);
  next.time = Math.min(next.time + action.minutes, WORK_END);
  addLog(next, action.log, "行动");

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

  unlockAchievements(next);
  if (next.time >= WORK_END) {
    finishDay(next);
  }

  return next;
}

function rollEvent(state, action) {
  const chance = action.group === "risky" ? 0.74 : action.group === "slack" ? 0.62 : 0.46;
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
  const stats = state.stats;
  let title = "普通存活";
  let text = "你成功撑到了下班。今天没有奇迹，但也没有事故。";
  let reward = 18;

  if (stats.performance >= 75 && stats.risk < 45) {
    title = "稳定输出";
    text = "你看起来很忙，实际上也确实做了不少事。";
    reward = 34;
  } else if (stats.performance >= 70 && stats.slack >= 45) {
    title = "可疑但高效";
    text = "你的摸鱼痕迹不少，但产出居然也说得过去。";
    reward = 30;
  } else if (stats.risk >= 75) {
    title = "危险边缘";
    text = "你离翻车很近，但下班铃声救了你。";
    reward = 10;
  } else if (stats.mood >= 75) {
    title = "情绪稳定";
    text = "工作未必推进很多，但你保住了精神世界。";
    reward = 24;
  } else if (stats.energy <= 20) {
    title = "电量见底";
    text = "你像一个即将休眠的设备，安静而顽强。";
    reward = 16;
  }

  state.stats.money = clamp(state.stats.money + reward, 0, 120);
  state.summary = { title, text, reward };
  state.lastEvent = { title: "今日结算", text: `${title}：${text} 金币 +${reward}` };
  addLog(state, `${title}：${text} 金币 +${reward}`, "今日结算");
  unlockAchievements(state);
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

function applyEffects(stats, effects) {
  for (const [key, delta] of Object.entries(effects)) {
    if (typeof stats[key] !== "number") {
      continue;
    }

    const stat = STATS.find((item) => item.key === key);
    const max = stat ? stat.max : 100;
    stats[key] = clamp(stats[key] + delta, 0, max);
  }
}

function addLog(state, text, title) {
  state.logs.push({ time: formatTime(state.time), title, text });
  if (state.logs.length > 80) {
    state.logs = state.logs.slice(state.logs.length - 80);
  }
}

function formatTime(minutes) {
  const hour = String(Math.floor(minutes / 60)).padStart(2, "0");
  const minute = String(minutes % 60).padStart(2, "0");
  return `${hour}:${minute}`;
}

function achievementTitleMap() {
  return Object.fromEntries(ACHIEVEMENTS.map((item) => [item.id, item.title]));
}

function cloneState(state) {
  return JSON.parse(JSON.stringify(state));
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

module.exports = {
  createInitialState,
  startNewDay,
  applyAction,
  formatTime,
  achievementTitleMap
};
