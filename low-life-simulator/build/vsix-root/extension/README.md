# 低配人生：工位模拟器

一个藏在 VS Code 侧边栏里的文字打工游戏。玩家通过选择写代码、改 Bug、开会、摸鱼、喝咖啡等行动，在精力、心情、绩效、摸鱼值和风险之间找平衡，努力活到下班。

## 功能

- VS Code Activity Bar 独立入口
- 侧边栏 Webview 文字游戏界面
- 从 09:30 到 18:00 的单日循环
- 13 个行动按钮
- 随机办公室事件
- 本地存档
- 日志与成就页
- 状态栏显示当前时间和风险
- 老板键：切换成看起来像分析日志的终端面板

## 本地调试

1. 用 VS Code 打开 `low-life-simulator` 文件夹。
2. 按 `F5` 启动 Extension Development Host。
3. 在新窗口左侧 Activity Bar 点击“低配人生”。
4. 点击“开始新的一天”。

## 命令

- `低配人生: 打开侧边栏`
- `低配人生: 开始新的一天`
- `低配人生: 重置存档`

## 开发检查

```bash
npm run check
```

## 文件结构

```txt
extension.js        VS Code 插件入口、Webview Provider、状态栏
gameData.js         属性、行动、事件、成就数据
gameEngine.js       游戏状态推进、事件结算、成就解锁
media/main.js       Webview 前端交互
media/style.css     侧边栏样式
media/icon.svg      Activity Bar 图标
```
