const STATS = [
  { key: "energy", label: "精力", max: 100, dangerLow: true },
  { key: "mood", label: "心情", max: 100, dangerLow: true },
  { key: "performance", label: "绩效", max: 100, dangerLow: true },
  { key: "slack", label: "摸鱼", max: 100 },
  { key: "risk", label: "风险", max: 100, dangerHigh: true },
  { key: "money", label: "金币", max: 220, dangerLow: true }
];

const ACTIONS = [
  {
    id: "code",
    label: "写代码",
    group: "work",
    minutes: 30,
    requires: { energy: 14 },
    effects: { energy: -11, mood: -4, performance: 15, slack: -8, risk: -4, money: 4 },
    log: "你开始写代码。变量名想了三分钟，最终选择了 data。"
  },
  {
    id: "debug",
    label: "改 Bug",
    group: "work",
    minutes: 30,
    requires: { energy: 18 },
    effects: { energy: -14, mood: -8, performance: 19, risk: 1, money: 5 },
    log: "你盯着报错看了很久。报错没有变，你变成熟了。"
  },
  {
    id: "docs",
    label: "看文档",
    group: "work",
    minutes: 15,
    requires: { energy: 8 },
    effects: { energy: -4, mood: -2, performance: 7, risk: -2, money: 1 },
    log: "你打开文档，发现示例代码写得像一个谜语。"
  },
  {
    id: "test",
    label: "跑测试",
    group: "work",
    minutes: 15,
    requires: { energy: 10 },
    effects: { energy: -7, mood: -3, performance: 9, risk: -1, money: 2 },
    log: "你跑了一遍测试。进度条很安静，空气很紧张。"
  },
  {
    id: "meeting",
    label: "开会",
    group: "work",
    minutes: 30,
    requires: { energy: 10, mood: 8 },
    effects: { energy: -10, mood: -11, performance: 6, slack: 4, risk: -2, money: 2 },
    log: "你参加会议，并熟练说出：我们先对齐一下。"
  },
  {
    id: "reply",
    label: "回复消息",
    group: "work",
    minutes: 15,
    requires: { energy: 8 },
    effects: { energy: -5, mood: -3, performance: 8, risk: -2, money: 2 },
    log: "你回复了三条消息，其中两条都包含收到。"
  },
  {
    id: "urgentTask",
    label: "接紧急小活",
    group: "work",
    minutes: 30,
    requires: { energy: 24 },
    effects: { energy: -18, mood: -8, performance: 18, risk: -6, money: 12 },
    log: "你接了一个紧急小活，完成后钱包和黑眼圈一起变明显。"
  },
  {
    id: "think",
    label: "假装思考",
    group: "slack",
    minutes: 15,
    effects: { energy: 1, mood: 2, performance: 1, slack: 5, risk: 4 },
    log: "你皱着眉看向屏幕，气场像在解决分布式一致性。"
  },
  {
    id: "read",
    label: "看点东西",
    group: "slack",
    minutes: 15,
    effects: { energy: 4, mood: 9, performance: -4, slack: 13, risk: 10 },
    log: "你读了一篇很有启发的文章，标题不适合出现在工位上。"
  },
  {
    id: "github",
    label: "逛 GitHub",
    group: "slack",
    minutes: 15,
    effects: { energy: 1, mood: 6, performance: 2, slack: 8, risk: 6 },
    log: "你逛 GitHub，顺便收藏了一个大概率不会再打开的仓库。"
  },
  {
    id: "miniGame",
    label: "玩一分钟",
    group: "slack",
    minutes: 15,
    effects: { energy: 3, mood: 12, performance: -8, slack: 16, risk: 15 },
    log: "你玩了一分钟小游戏。时间显示它可能不止一分钟。"
  },
  {
    id: "coffee",
    label: "喝咖啡",
    group: "rest",
    minutes: 15,
    cost: 10,
    effects: { energy: 20, mood: 3, money: -10, risk: 2 },
    log: "你喝下咖啡，短暂获得了人造清醒。"
  },
  {
    id: "tea",
    label: "点奶茶",
    group: "rest",
    minutes: 15,
    cost: 16,
    effects: { energy: 4, mood: 16, money: -16, slack: 3 },
    log: "你点了一杯奶茶。钱包失血，灵魂回血。"
  },
  {
    id: "snack",
    label: "吃零食",
    group: "rest",
    minutes: 15,
    cost: 6,
    effects: { energy: 8, mood: 7, money: -6, risk: 1 },
    log: "你拆开零食，声音不大，但快乐很脆。"
  },
  {
    id: "stretch",
    label: "伸展回血",
    group: "rest",
    minutes: 15,
    effects: { energy: 10, mood: 5, risk: -4 },
    log: "你站起来活动了一下，身体提醒你它还在。"
  },
  {
    id: "nap",
    label: "午睡",
    group: "risky",
    minutes: 30,
    effects: { energy: 28, mood: 8, performance: -8, slack: 17, risk: 18 },
    log: "你闭眼休息，醒来时世界像重新编译过。"
  },
  {
    id: "fakeMeeting",
    label: "假装开会",
    group: "risky",
    minutes: 30,
    effects: { energy: 6, mood: 10, performance: -10, slack: 18, risk: 23 },
    log: "你把状态改成会议中。这个会议只有你和你的良心参加。"
  }
];

const EVENTS = [
  { id: "meeting_cancelled", title: "会议取消", tags: ["work", "rest", "any"], effects: { energy: 5, mood: 12, risk: -4 }, text: "日历弹出取消通知。你忽然相信世界还有秩序。" },
  { id: "requirement_change", title: "需求变更", tags: ["work", "any"], effects: { energy: -8, mood: -10, performance: -5 }, text: "产品说这个应该很简单吧。你听见灵魂轻轻叹气。" },
  { id: "ci_red", title: "CI 又红了", tags: ["work"], effects: { energy: -7, mood: -6, performance: -4, risk: 8 }, text: "你不知道为什么，但大家都看向了你。" },
  { id: "milk_tea", title: "同事请奶茶", tags: ["any", "rest"], effects: { mood: 16, energy: 3 }, text: "你短暂相信人间值得，甚至想写两个单元测试。" },
  { id: "quick_fix", title: "一行修复", tags: ["work"], effects: { performance: 12, mood: 6, risk: -3, money: 5 }, text: "你删掉一行代码，问题好了。工程学有时像玄学。" },
  { id: "prod_alert", title: "线上告警", tags: ["work", "slack", "risky"], effects: { energy: -12, mood: -12, performance: 6, risk: 12, money: 8 }, text: "群里突然有人 @全体成员。你的心率完成一次小上线。" },
  { id: "silent_hour", title: "办公室安静", tags: ["work", "rest", "any"], effects: { energy: 4, performance: 5, risk: -5 }, text: "没人讲话，键盘声像雨。你难得进入状态。" },
  { id: "manager_ping", title: "领导私聊", tags: ["any"], effects: { energy: -5, mood: -7, risk: 6 }, text: "消息只有两个字：在吗。你看出了悬疑片的质感。" },
  { id: "great_excuse", title: "完美借口", tags: ["slack", "risky"], effects: { mood: 8, risk: -12 }, text: "你说正在定位偶现问题。没有人能反驳偶现。" },
  { id: "bad_coffee", title: "咖啡过量", tags: ["rest"], condition: (s) => s.counters.coffee >= 2, effects: { energy: 4, mood: -7, risk: 5 }, text: "你很清醒，但清醒得有点像系统告警。" },
  { id: "review_pass", title: "Code Review 通过", tags: ["work"], effects: { mood: 10, performance: 8, risk: -4, money: 4 }, text: "评论只有 LGTM。你感到一种被世界轻轻放过的幸福。" },
  { id: "review_wall", title: "Review 留言", tags: ["work"], effects: { mood: -8, performance: 3, energy: -5 }, text: "对方写了三段建议。每个字都很礼貌，每句话都很重。" },
  { id: "desk_clean", title: "整理桌面", tags: ["rest", "slack"], effects: { mood: 6, slack: 4, risk: -3 }, text: "你把杯子挪到左边。工作环境焕然一新，工作本身毫无变化。" },
  { id: "branch_name", title: "分支名很长", tags: ["work"], effects: { performance: 3, mood: -3 }, text: "你发现当前分支名像一份事故报告。" },
  { id: "payday_hint", title: "小额绩效奖励", tags: ["work"], condition: (s) => s.stats.performance >= 60, effects: { money: 10, mood: 3 }, text: "你刚完成的东西被看见了，金币到账，世界短暂合理。" },
  { id: "wallet_bleed", title: "自动续费", tags: ["any"], condition: (s) => s.stats.money >= 20, effects: { money: -12, mood: -4 }, text: "一个你忘记取消的服务扣费了。金币默默减少。" }
];

const EMERGENCY_EVENTS = [
  {
    id: "energy_crash",
    title: "紧急事件：精力见底",
    text: "你的精力太低，继续办公只会让代码和人格一起变形。先处理状态。",
    condition: (s) => s.stats.energy <= 8,
    options: [
      { id: "power_nap", label: "趴睡 30 分钟", minutes: 30, effects: { energy: 30, mood: 4, risk: 12, slack: 10 }, result: "你趴睡了一会儿，醒来时脸上有键盘印。" },
      { id: "buy_coffee", label: "买咖啡 -10", minutes: 15, cost: 10, effects: { energy: 24, mood: 2, money: -10, risk: 3 }, result: "咖啡续上了，灵魂暂时重启。" },
      { id: "force_work", label: "硬撑", minutes: 15, effects: { energy: -4, mood: -10, performance: -8, risk: 10 }, result: "你硬撑了十五分钟，产出像梦游时写的。" }
    ]
  },
  {
    id: "mood_crash",
    title: "紧急事件：心情归零",
    text: "你的心情已经红灯，继续推进会触发精神层面的熔断。",
    condition: (s) => s.stats.mood <= 8,
    options: [
      { id: "walk", label: "离席走一圈", minutes: 15, effects: { mood: 18, energy: 5, risk: 5, slack: 6 }, result: "你走了一圈，决定先放过自己。" },
      { id: "milk_tea", label: "奶茶回血 -16", minutes: 15, cost: 16, effects: { mood: 28, energy: 4, money: -16 }, result: "糖分抵达大脑，世界边缘变软了一点。" },
      { id: "silent_mode", label: "关闭通知", minutes: 15, effects: { mood: 12, performance: -4, risk: 4 }, result: "你关闭了几个群，心里出现一小块空地。" }
    ]
  },
  {
    id: "risk_max",
    title: "紧急事件：风险爆表",
    text: "你的风险已经压到警戒线。再被抓到一次，今天很可能直接翻车。",
    condition: (s) => s.stats.risk >= 92,
    options: [
      { id: "deliver_patch", label: "交付一个补丁", minutes: 30, requires: { energy: 16 }, effects: { energy: -14, performance: 16, risk: -28, mood: -6, money: 6 }, result: "你用一个补丁证明自己确实在工作。" },
      { id: "status_report", label: "发进度报告", minutes: 15, effects: { performance: 6, risk: -16, mood: -4 }, result: "你发了一份进度报告，风险暂时下降。" },
      { id: "team_tea", label: "请下午茶 -24", minutes: 15, cost: 24, effects: { money: -24, mood: 8, risk: -20 }, result: "下午茶缓和了空气，但金币发出了轻微悲鸣。" }
    ]
  },
  {
    id: "wallet_empty",
    title: "紧急事件：钱包空了",
    text: "金币太少，补给类行动会受限。你需要靠工作把现金流救回来。",
    condition: (s) => s.stats.money <= 0,
    options: [
      { id: "small_ticket", label: "处理小工单 +12", minutes: 30, requires: { energy: 12 }, effects: { energy: -10, performance: 8, money: 12, mood: -3 }, result: "你处理了一个小工单，金币回血。" },
      { id: "no_spend", label: "节流十五分钟", minutes: 15, effects: { mood: -4, risk: -5 }, result: "你什么都没买，钱包没有变厚，但停止流血。" }
    ]
  },
  {
    id: "performance_zero",
    title: "紧急事件：绩效红灯",
    text: "今天的绩效已经非常危险，系统开始怀疑你只是椅子的一部分。",
    condition: (s) => s.stats.performance <= 6,
    options: [
      { id: "quick_doc", label: "补一份文档", minutes: 30, requires: { energy: 10 }, effects: { energy: -8, performance: 16, risk: -8, mood: -4, money: 4 }, result: "你补了一份文档，至少留下了工作痕迹。" },
      { id: "ask_help", label: "找同事同步", minutes: 15, effects: { performance: 8, mood: -2, risk: -5 }, result: "你找同事同步了一下，局势没有更糟。" }
    ]
  }
];

const ACHIEVEMENTS = [
  { id: "on_time", title: "准点下班主义者", test: (s) => s.phase === "ended" && s.stats.risk < 60 },
  { id: "suspicious_efficient", title: "可疑但高效", test: (s) => s.phase === "ended" && s.stats.performance >= 70 && s.stats.slack >= 45 },
  { id: "coffee_engine", title: "咖啡因驱动开发者", test: (s) => s.counters.coffee >= 3 },
  { id: "meeting_survivor", title: "会议幸存者", test: (s) => s.counters.meeting >= 3 },
  { id: "bug_reader", title: "报错鉴赏家", test: (s) => s.counters.debug >= 3 },
  { id: "desk_ninja", title: "工位忍者", test: (s) => s.stats.risk >= 70 && s.stats.performance >= 55 },
  { id: "coin_keeper", title: "金币守门员", test: (s) => s.phase === "ended" && s.stats.money >= 140 },
  { id: "crisis_manager", title: "危机处理专员", test: (s) => s.counters.emergenciesResolved >= 3 },
  { id: "caught_once", title: "公开处刑体验卡", test: (s) => s.counters.caught >= 1 },
  { id: "ai_colleague", title: "AI 同事上线", test: (s) => s.mode === "ai" && s.counters.aiTasksCompleted >= 1 }
];

module.exports = { STATS, ACTIONS, EVENTS, EMERGENCY_EVENTS, ACHIEVEMENTS };
