/* 后台音频保活（保守版）
   原则：只做最小干预，不干扰 Folia 的音频图 */
(function () {
  'use strict';

  var OrigAC = window.AudioContext || window.webkitAudioContext;
  if (!OrigAC) return;

  var activeCtx = null;
  var silentAttached = false;

  // 包装构造函数：只记录当前活跃的 context（不累积）
  function WrappedAC() {
    var ctx = new OrigAC(arguments[0]);
    activeCtx = ctx;
    return ctx;
  }
  WrappedAC.prototype = OrigAC.prototype;
  window.AudioContext = WrappedAC;
  if (window.webkitAudioContext) window.webkitAudioContext = WrappedAC;

  // 只挂一次静音节点，用极低频率避免干扰音频图
  function attachSilentOnce() {
    if (silentAttached || !activeCtx) return;
    try {
      if (activeCtx.state === 'closed') return;
      var osc = activeCtx.createOscillator();
      var gain = activeCtx.createGain();
      gain.gain.value = 0.00001;      // 几乎为 0
      osc.frequency.value = 1;        // 1Hz，远低于音频范围
      osc.connect(gain);
      gain.connect(activeCtx.destination);
      osc.start();
      silentAttached = true;
      console.log('[keep-audio] silent node attached (1Hz)');
    } catch (e) {
      console.warn('[keep-audio] attach failed:', e && e.message);
    }
  }

  // 只在切后台/回前台时处理，不做定时轮询（避免干扰音频状态）
  document.addEventListener('visibilitychange', function () {
    if (!activeCtx) return;
    try {
      if (document.hidden) {
        // 进后台：确保 context 是 running，并挂静音节点
        if (activeCtx.state !== 'running') {
          activeCtx.resume().catch(function () {});
        }
        attachSilentOnce();
      } else {
        // 回前台：恢复
        if (activeCtx.state !== 'running') {
          activeCtx.resume().catch(function () {});
        }
      }
    } catch (e) {}
  });

  // 首次用户交互时初始化（iOS 要求用户手势后才能 start AudioContext）
  var inited = false;
  function initOnce() {
    if (inited) return;
    inited = true;
    attachSilentOnce();
  }
  ['touchstart', 'click', 'keydown'].forEach(function (ev) {
    document.addEventListener(ev, initOnce, { once: true, passive: true });
  });

  console.log('[keep-audio] installed (conservative mode)');
})();
