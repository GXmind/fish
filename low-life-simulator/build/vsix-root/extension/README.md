# 低配人生：工位模拟器

一个藏在 VS Code 侧边栏里的文字打工游戏。玩家通过选择写代码、改 Bug、开会、摸鱼、喝咖啡等行动，在精力、心情、绩效、摸鱼值、风险和金币之间找平衡，努力活到下班。

## 功能

- VS Code Activity Bar 独立入口
- 从 09:30 到 18:00 的单日循环
- 离线模式：不联网，使用本地规则与事件池
- AI 模式：通过 MiniMax OpenAI-compatible API 在每个回合后自动生成状态驱动事件与选项
- 金币经济：工作、奖励、罚款、补给消耗和日终结算
- 紧急事件：精力、心情、绩效、风险、金币触底或爆表时触发选项
- 高风险娱乐抓包：风险过高时摸鱼会被抓并扣金币
- 日志、成就、本地存档、状态栏提示
- 老板键：切换成看起来像分析日志的终端面板

## MiniMax AI 模式

AI 模式默认使用：

```txt
Base URL: https://api.minimax.io/v1
Model: MiniMax-M2.7-highspeed
```

国内用户可以在 VS Code 设置里把 `lowLifeSimulator.minimaxBaseUrl` 改为：

```txt
https://api.minimaxi.com/v1
```

API Key 不写入项目文件。运行命令 `低配人生: 设置 MiniMax API Key`，插件会把它保存到 VS Code SecretStorage。

## 本地调试

1. 用 VS Code 打开本文件夹。
2. 按 `F5` 启动 Extension Development Host。
3. 在新窗口左侧 Activity Bar 点击“低配人生”。
4. 点击“开始新的一天”。

## 命令

- `低配人生: 打开侧边栏`
- `低配人生: 开始新的一天`
- `低配人生: 重置存档`
- `低配人生: 设置 MiniMax API Key`
- `低配人生: 清除 MiniMax API Key`

## 开发检查

```bash
npm.cmd run check
node --check gameData.js
node --check gameEngine.js
node --check media/main.js
```

## 文件结构

```txt
extension.js        VS Code 插件入口、Webview Provider、状态栏、MiniMax 请求
gameData.js         属性、行动、事件、紧急事件、成就数据
gameEngine.js       游戏状态推进、金币经济、紧急事件、成就解锁
media/main.js       Webview 前端交互
media/style.css     侧边栏样式
media/icon.svg      Activity Bar 图标
```
