const STATS = [
  { key: "energy", label: "精力", max: 100 },
  { key: "mood", label: "心情", max: 100 },
  { key: "performance", label: "绩效", max: 100 },
  { key: "slack", label: "摸鱼", max: 100 },
  { key: "risk", label: "风险", max: 100 },
  { key: "money", label: "金币", max: 120 }
];

const ACTIONS = [
  { id: "code", label: "写代码", group: "work", minutes: 30, effects: { energy: -9, mood: -4, performance: 14, slack: -7, risk: -3 }, log: "你开始写代码。变量名想了三分钟，最终选择了 data。" },
  { id: "debug", label: "改 Bug", group: "work", minutes: 30, effects: { energy: -12, mood: -7, performance: 18, risk: 2 }, log: "你盯着报错看了很久。报错没有变，你变成熟了。" },
  { id: "docs", label: "看文档", group: "work", minutes: 15, effects: { energy: -4, mood: -2, performance: 6, risk: -2 }, log: "你打开文档，发现示例代码写得像一个谜语。" },
  { id: "test", label: "跑测试", group: "work", minutes: 15, effects: { energy: -6, mood: -3, performance: 8, risk: -1 }, log: "你跑了一遍测试。进度条很安静，空气很紧张。" },
  { id: "meeting", label: "开会", group: "work", minutes: 30, effects: { energy: -10, mood: -10, performance: 5, slack: 4, risk: -2 }, log: "你参加会议，并熟练说出：我们先对齐一下。" },
  { id: "reply", label: "回复消息", group: "work", minutes: 15, effects: { energy: -5, mood: -3, performance: 7, risk: -1 }, log: "你回复了三条消息，其中两条都包含收到。" },
  { id: "think", label: "假装思考", group: "slack", minutes: 15, effects: { energy: -1, mood: 2, performance: 1, slack: 5, risk: 4 }, log: "你皱着眉看向屏幕，气场像在解决分布式一致性。" },
  { id: "read", label: "看点东西", group: "slack", minutes: 15, effects: { energy: 4, mood: 8, performance: -4, slack: 12, risk: 9 }, log: "你读了一篇很有启发的文章，标题不适合出现在工位上。" },
  { id: "github", label: "逛 GitHub", group: "slack", minutes: 15, effects: { energy: 1, mood: 5, performance: 2, slack: 7, risk: 5 }, log: "你逛 GitHub，顺便收藏了一个大概率不会再打开的仓库。" },
  { id: "coffee", label: "喝咖啡", group: "rest", minutes: 15, effects: { energy: 18, mood: 3, money: -8, risk: 2 }, log: "你喝下咖啡，短暂获得了人造清醒。" },
  { id: "tea", label: "点奶茶", group: "rest", minutes: 15, effects: { energy: 4, mood: 14, money: -12, slack: 3 }, log: "你点了一杯奶茶。钱包失血，灵魂回血。" },
  { id: "nap", label: "午睡", group: "risky", minutes: 30, effects: { energy: 25, mood: 8, performance: -8, slack: 16, risk: 18 }, log: "你闭眼休息，醒来时世界像重新编译过。" },
  { id: "fakeMeeting", label: "假装开会", group: "risky", minutes: 30, effects: { energy: 5, mood: 9, performance: -10, slack: 18, risk: 22 }, log: "你把状态改成会议中。这个会议只有你和你的良心参加。" }
];

const EVENTS = [
  { id: "boss_low", title: "老板路过", tags: ["slack", "risky"], condition: (s) => s.stats.risk < 55, effects: { risk: -10, performance: 2 }, text: "你淡定切回代码窗口，甚至顺手滚动了一下。" },
  { id: "boss_high", title: "老板路过", tags: ["slack", "risky"], condition: (s) => s.stats.risk >= 55, effects: { risk: 14, performance: -12, mood: -8 }, text: "屏幕内容过于精彩，空气安静了半秒。" },
  { id: "meeting_cancelled", title: "会议取消", tags: ["work", "rest", "any"], effects: { energy: 5, mood: 12, risk: -4 }, text: "日历弹出取消通知。你忽然相信世界还有秩序。" },
  { id: "requirement_change", title: "需求变更", tags: ["work", "any"], effects: { energy: -8, mood: -10, performance: -5 }, text: "产品说这个应该很简单吧。你听见灵魂轻轻叹气。" },
  { id: "ci_red", title: "CI 又红了", tags: ["work"], effects: { energy: -7, mood: -6, performance: -4, risk: 8 }, text: "你不知道为什么，但大家都看向了你。" },
  { id: "milk_tea", title: "同事请奶茶", tags: ["any", "rest"], effects: { mood: 16, energy: 3 }, text: "你短暂相信人间值得，甚至想写两个单元测试。" },
  { id: "quick_fix", title: "一行修复", tags: ["work"], effects: { performance: 12, mood: 6, risk: -3 }, text: "你删掉一行代码，问题好了。工程学有时像玄学。" },
  { id: "prod_alert", title: "线上告警", tags: ["work", "slack", "risky"], effects: { energy: -12, mood: -12, performance: 6, risk: 12 }, text: "群里突然有人 @全体成员。你的心率完成一次小上线。" },
  { id: "silent_hour", title: "办公室安静", tags: ["work", "rest", "any"], effects: { energy: 4, performance: 5, risk: -5 }, text: "没人讲话，键盘声像雨。你难得进入状态。" },
  { id: "manager_ping", title: "领导私聊", tags: ["any"], effects: { energy: -5, mood: -7, risk: 6 }, text: "消息只有两个字：在吗。你看出了悬疑片的质感。" },
  { id: "great_excuse", title: "完美借口", tags: ["slack", "risky"], effects: { mood: 8, risk: -12 }, text: "你说正在定位偶现问题。没有人能反驳偶现。" },
  { id: "bad_coffee", title: "咖啡过量", tags: ["rest"], condition: (s) => s.counters.coffee >= 2, effects: { energy: 4, mood: -7, risk: 5 }, text: "你很清醒，但清醒得有点像系统告警。" },
  { id: "review_pass", title: "Code Review 通过", tags: ["work"], effects: { mood: 10, performance: 8, risk: -4 }, text: "评论只有 LGTM。你感到一种被世界轻轻放过的幸福。" },
  { id: "review_wall", title: "Review 留言", tags: ["work"], effects: { mood: -8, performance: 3, energy: -5 }, text: "对方写了三段建议。每个字都很礼貌，每句话都很重。" },
  { id: "desk_clean", title: "整理桌面", tags: ["rest", "slack"], effects: { mood: 6, slack: 4, risk: -3 }, text: "你把杯子挪到左边。工作环境焕然一新，工作本身毫无变化。" },
  { id: "keyboard_stuck", title: "键盘卡键", tags: ["any"], effects: { energy: -3, mood: -4 }, text: "空格键短暂罢工。你开始理解基础设施的重要性。" },
  { id: "branch_name", title: "分支名很长", tags: ["work"], effects: { performance: 3, mood: -3 }, text: "你发现当前分支名像一份事故报告。" },
  { id: "snack_supply", title: "零食补给", tags: ["rest", "any"], effects: { energy: 6, mood: 8, money: -5 }, text: "你用一点金币换来一点精神稳定。" }
];

const ACHIEVEMENTS = [
  { id: "on_time", title: "准点下班主义者", test: (s) => s.phase === "ended" && s.stats.risk < 60 },
  { id: "suspicious_efficient", title: "可疑但高效", test: (s) => s.phase === "ended" && s.stats.performance >= 70 && s.stats.slack >= 45 },
  { id: "coffee_engine", title: "咖啡因驱动开发者", test: (s) => s.counters.coffee >= 3 },
  { id: "meeting_survivor", title: "会议幸存者", test: (s) => s.counters.meeting >= 3 },
  { id: "bug_reader", title: "报错鉴赏家", test: (s) => s.counters.debug >= 3 },
  { id: "desk_ninja", title: "工位忍者", test: (s) => s.stats.risk >= 70 && s.stats.performance >= 55 }
];

module.exports = { STATS, ACTIONS, EVENTS, ACHIEVEMENTS };
