/*
 * GaplessPlayer —— startup_script.js
 *
 * 作用：尽早建立「UI 事件处理器注册表」window.registeredCalls。
 *
 * 为什么需要（真机实测，GaplessPlayer v0.1.3）：
 *   网易云 UI 通过 channel.registerCall / legacyNativeCmder.appendRegisterCall
 *   注册事件处理器（Load / PlayProgress / PlayState …）。
 *   而 legacyNativeCmder.triggerRegisterCall 只把事件「通知原生」，
 *   **并不会调用 UI 注册在 JS 侧的处理器** —— 所以只调它，UI 完全不反应：
 *   不点播放、不算总时长、不进「播放中」→ 暂停按钮点了没反应。
 *
 *   LibFrontendPlay 的做法就是自己记一份（它的 startup_script.js + manifest 里的 hijacks），
 *   然后自己调用这些处理器。本文件照做。
 *
 * 本文件按 BetterNCM 的约定（插件包内名为 startup_script.js）在页面启动阶段被注入。
 */
(function () {
  "use strict";

  var reg = (window.registeredCalls = window.registeredCalls || {});

  /** 记一笔；同一个函数只记一次（startup_script 与 main.js 可能都挂钩子） */
  function record(key, handler) {
    if (!key || typeof handler !== "function") return;
    var arr = (reg[key] = reg[key] || []);
    if (arr.indexOf(handler) < 0) arr.push(handler);
  }

  /** 包 channel.registerCall(name, handler) */
  function wrapRegisterCall() {
    try {
      if (typeof channel === "undefined" || !channel) return false;
      var orig = channel.registerCall;
      if (typeof orig !== "function" || orig.__gpWrapped) return true;
      var w = function (name, handler) {
        record(String(name), handler);
        return orig.apply(this, arguments);
      };
      w.__gpWrapped = true;
      channel.registerCall = w;
      return true;
    } catch (e) {
      return false;
    }
  }

  /** 包 legacyNativeCmder.appendRegisterCall(name, ns, handler) */
  function wrapAppend() {
    try {
      if (typeof legacyNativeCmder === "undefined" || !legacyNativeCmder) return false;
      var orig = legacyNativeCmder.appendRegisterCall;
      if (typeof orig !== "function" || orig.__gpWrapped) return true;
      var w = function (name, ns, handler) {
        record(String(ns) + ".on" + String(name), handler);
        return orig.apply(this, arguments);
      };
      w.__gpWrapped = true;
      legacyNativeCmder.appendRegisterCall = w;
      return true;
    } catch (e) {
      return false;
    }
  }

  function tick() {
    wrapRegisterCall();
    wrapAppend();
  }

  tick();
  // legacyNativeCmder / channel 可能晚一点才出现，重试一段时间（约 15 秒）
  var n = 0;
  var t = setInterval(function () {
    tick();
    if (++n > 750) clearInterval(t);
  }, 20);
})();
