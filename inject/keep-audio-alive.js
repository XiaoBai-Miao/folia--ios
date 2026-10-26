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
  function WrappedAC() {
    var ctx = new OrigAC(arguments[0]);
    return track(ctx);
  }
  WrappedAC.prototype = OrigAC.prototype;
  window.AudioContext = WrappedAC;
  if (window.webkitAudioContext) window.webkitAudioContext = WrappedAC;

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

  // 静音音频保活：iOS 需要一个持续播放的音频元素来维持后台
  function keepAlive() {
    try {
      if (window.__keepAliveAudio) return;
      var silent = new OrigAC();
      var osc = silent.createOscillator();
      var gain = silent.createGain();
      gain.gain.value = 0.0001;
      osc.connect(gain);
      gain.connect(silent.destination);
      osc.start();
      window.__keepAliveAudio = { ctx: silent, osc: osc };
      track(silent);
      console.log('[keep-audio] silent oscillator started');
    } catch (e) {
      console.warn('[keep-audio] keepAlive failed:', e && e.message);
    }
  }
  keepAlive();

  console.log('[keep-audio] installed, contexts tracked');
})();
