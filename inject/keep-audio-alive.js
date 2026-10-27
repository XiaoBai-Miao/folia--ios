/* 让 Web Audio 在切后台时保持运行（iOS WKWebView 会挂起 AudioContext） */
(function () {
  'use strict';

  var contexts = [];
  var OrigAC = window.AudioContext || window.webkitAudioContext;
  if (!OrigAC) return;

  function track(ctx) {
    if (contexts.indexOf(ctx) === -1) contexts.push(ctx);
    return ctx;
  }

  // 包装构造函数，记录所有 AudioContext 实例

  // 页面里已存在的实例（如果先于本脚本创建）
  try {
    if (window.__foliaAudioContexts) {
      window.__foliaAudioContexts.forEach(track);
    }
  } catch (e) {}

  function resumeAll(reason) {
    contexts.forEach(function (ctx) {
      try {
        if (ctx.state === 'suspended' || ctx.state === 'interrupted') {
          ctx.resume().then(function () {
            console.log('[keep-audio] resumed:', reason, ctx.state);
          }).catch(function () {});
        }
      } catch (e) {}
    });
  }

  // 切后台/回前台都尝试恢复
  document.addEventListener('visibilitychange', function () {
    resumeAll(document.hidden ? 'background' : 'foreground');
  });
  window.addEventListener('pagehide', function () { resumeAll('pagehide'); });
  window.addEventListener('blur', function () { resumeAll('blur'); });

  // 定时兜底：每 2 秒检查一次（后台时定时器可能被限流，但仍会跑）
  setInterval(function () { resumeAll('interval'); }, 2000);

  // 静音保活：在【已有的】AudioContext 里加静音节点
  // 不新建 AudioContext，避免抢走 mediaSession 的音频源（否则锁屏播放器会消失）
  function attachSilentNode(ctx) {
    try {
      if (!ctx || ctx.__keepAliveAttached) return;
      ctx.__keepAliveAttached = true;
      var osc = ctx.createOscillator();
      var gain = ctx.createGain();
      gain.gain.value = 0.00005;   // 近乎无声
      osc.frequency.value = 20;     // 极低频，人耳听不到
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      console.log('[keep-audio] silent node attached to existing context');
    } catch (e) {
      console.warn('[keep-audio] attach silent node failed:', e && e.message);
    }
  }

  // 包装构造函数：创建时记录，并在用户首次交互后附加静音节点
  function WrappedAC2() {
    var ctx = new OrigAC(arguments[0]);
    track(ctx);
    // 延迟附加，等 Folia 建好图之后再挂
    setTimeout(function () { attachSilentNode(ctx); }, 1500);
    return ctx;
  }
  WrappedAC2.prototype = OrigAC.prototype;
  window.AudioContext = WrappedAC2;
  if (window.webkitAudioContext) window.webkitAudioContext = WrappedAC2;

  console.log('[keep-audio] installed, contexts tracked');
})();
