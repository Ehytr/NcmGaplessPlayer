# GaplessPlayer

> 给网易云音乐 PC 版做的**真无缝**播放引擎：把「下一首」提前排到「这一首」的最后一个采样上，切歌间隙从几百毫秒压到 **0**。

一个 [BetterNCM](https://github.com/std-microblock/BetterNCM) 插件。它自己用 Web Audio 接管播放链。

```
网易云 UI ── channel.call("audioplayer.*") ──▶ [拦截层]
                                                ├─ 播放引擎（AudioBufferSourceNode）
                                                ├─ 预载调度器（下一首提前下完 + 解码）
                                                └─ 事件伪造器（让 UI 以为一切照旧）
```

---

## 它能做什么

- **真无缝**：自然播完 → 下一首，间隙 **0 ms**。不是淡入淡出、不是盖一层静音，是采样级接缝
- **提前预载**：当前歌还在响的时候，下一首已经下完并解码好，切歌不用等
- **开机预下**：记住上次播的那首，一开机就先把「马上就要播的这首」下好
- **两条播放路径**：能预载就走缓冲（可无缝），不能就 `<audio>` 边下边播（~0.5 s 出声），自动选
- **不乱猜**：只有能确认是顺序播放时才预约；随机播放押不中会自动关掉预载，不白耗流量
- **只管播放**：只截下播放相关的几条命令，其余一律放行给原生 —— 网易云的其它功能不受影响
- **可随时刹车**：四个控制台开关，改了立刻生效，不用重新打包

## 效果

| 场景 | 未启用本插件 | GaplessPlayer |
| --- | --- | --- |
| 自然播完 → 下一首 | 卡 150~500 ms | **0 ms**（采样级接缝） |
| 点「下一首」 | 立刻 | 立刻 |
| 歌单第一首 / 预载未命中 | 等下载 + 解码 2~7 s | ~0.5 s（边下边播） |
| 开机第一首 | 等下载 | 开机就预下（记住上次那首） |

## 安装

1. 装好 [BetterNCM](https://github.com/std-microblock/BetterNCM)（本插件在 **网易云 2.10.13** 上开发、实测）。
2. 下载 [Releases](../../releases) 里的 `gapless-player-<version>.plugin`，
   放进 `C:\betterncm\plugins\`。
3. 重启网易云音乐。

**建议同时启用 [LibEAPIRequest](https://github.com/BetterNCM/LibEAPIRequest)**（「网易云 API 请求库」）。
不装也能用：能正常播放，但**预载和无缝预约会关闭**，退化成一首一首的流式播放。

## 工作原理（三段）

**1. 拦截**
插件在 `plugin.onLoad` 里用 `Object.defineProperty` 锁住 `channel.call`，只截下这几条：

`audioplayer.load` / `play` / `pause` / `stop` / `seek` / `setVolume`（另有 `player.addListElement`、`player.setCurrentPlay` 只旁听不放行改写）。
其余命令一律 `return false` 放行给原生播放器。

启动时先 `channel.call("audioplayer.pause", …)` 把原生播放器按住，否则会和插件的音频双声道。

**2. 播放**
- 预载命中 → `AudioBufferSourceNode` 直接起播（0 等待）
- 没命中 → `<audio>` 流式，`loadedmetadata` 一到就出声（~0.5s）
- 下一首在当前歌还在响的时候就已经下完 + 解码好，放在「预载槽」里

**3. 伪造事件**
UI 靠 `audioplayer.onLoad` / `onPlayState` / `onPlayProgress` / `onSeek` / `onVolume` / `onEnd` 这几个事件驱动。
插件自己维护 `window.registeredCalls` 注册表（`startup_script.js` 在页面最早期就注入），
既调用 UI 注册在 JS 侧的处理器，也 `legacyNativeCmder.triggerRegisterCall` 通知原生 —— 少任何一步 UI 都不动。

## 无缝是怎么做到的

当前曲目还剩 **0.3~1.5 s** 时，插件自己建一个 `AudioBufferSourceNode`，
`src.start(上一首的结束采样, 0)` 把它排上去。音频线程在「最后一个采样之后的下一个采样」精确执行 → 0 间隙。
UI 的 `load` 大约 **120 ms 后**才到，到了就按 trackId **认领**已在响的那一路，不重启。

三段状态机（`S.sched.phase`）：

| 阶段 | 含义 | 关键点 |
| --- | --- | --- |
| `armed` | 已排上，A 还在播 | 绝不能动 `S.source`，否则 A 的 `onended` 守卫失败 → 不发 `[end]` → UI 永不推进 |
| `live` | A 已播完，B 已在响，UI 还没来 load | 抑制进度上报（否则进度条从 0 闪一下） |
| `claimed` | UI 的 load 到了，已认领 | 等首个 play，补发 `onPlayState(1)`，不重启 |

预约要过三道闸门：缓冲路径 + 在播；预载槽里正是「列表里的下一首」且 ready；
能确认是顺序播放（读 `localStorage` 的 `NM_SETTING_PLAYER.mode`，读不到就退回「连续命中 2 次」）。

## 已知限制

- **网易云原本的歌词会失效**：因为拦截了网易云本身的播放，原来的歌词会变得没法用  解决方法：可使用[RuLyric原版](https://github.com/BetterNCM/RuLyric)或[Releases](../../releases)中的Rulyrc改版(加上了锁定歌词与置于最前功能)
- 只在网易云 **2.10.x** 上验证过。hijack 的 chunk 文件名变了就要跟着改 manifest。  解决方法：BetterNCM插件商店中可降低到该版本
- 依赖网易云的内部接口（`channel.call` / `legacyNativeCmder`），**它一升级就可能全部失效**。


日志在 `C:\betterncm\gapless-player.log`（滚动 900 条）。


## 致谢

- [BetterNCM](https://github.com/std-microblock/BetterNCM) —— 插件加载器与生态
- [LibEAPIRequest](https://github.com/BetterNCM/LibEAPIRequest) —— 查播放地址
- [RuLyric](https://github.com/BetterNCM/RuLyric) —— 桌面歌词

## License

[MIT](LICENSE)
