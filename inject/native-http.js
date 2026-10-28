/* 把跨域 fetch 交给 CapacitorHttp 原生层执行，绕开 WKWebView 的 CORS 限制 */
(function () {
  'use strict';
  var Cap = window.Capacitor;
  if (!Cap || !Cap.Plugins || !Cap.Plugins.CapacitorHttp) {
    console.warn('[native-http] CapacitorHttp 不可用，回退到浏览器 fetch');
    return;
  }
  var plugin = Cap.Plugins.CapacitorHttp;
  var origFetch = window.fetch.bind(window);

  function sameOrigin(url) {
    try { return new URL(url, location.href).origin === location.origin; }
    catch (e) { return false; }
  }
  function toHeaders(h) {
    var out = {};
    if (!h) return out;
    if (h instanceof Headers) { h.forEach(function (v, k) { out[k] = v; }); return out; }
    if (Array.isArray(h)) { h.forEach(function (p) { out[p[0]] = p[1]; }); return out; }
    Object.keys(h).forEach(function (k) { out[k] = h[k]; });
    return out;
  }

  window.fetch = async function (input, init) {
    init = init || {};
    var url = typeof input === 'string' ? input : (input && input.url) || '';
    var method = (init.method || (input && input.method) || 'GET').toUpperCase();
    if (!/^https?:\/\//i.test(url) || sameOrigin(url)) return origFetch(input, init);

    var body = init.body;
    var data;
    if (typeof body === 'string') data = body;
    else if (body instanceof URLSearchParams) data = body.toString();
    else if (body) data = String(body);

    try {
      var res = await plugin.request({
        url: url,
        method: method,
        headers: toHeaders(init.headers || (input && input.headers)),
        data: data,
        responseType: 'text',
        connectTimeout: 30000,
        readTimeout: 30000
      });

      // 关键：set-cookie 在浏览器里是 forbidden header，Headers 里读不到。
      // 这里把它单独暴露到 window.__lastSetCookie，供业务代码读取。
      var rawHeaders = res.headers || {};
      var setCookies = [];
      Object.keys(rawHeaders).forEach(function (k) {
        if (String(k).toLowerCase() === 'set-cookie') {
          var v = rawHeaders[k];
          if (Array.isArray(v)) setCookies = setCookies.concat(v);
          else if (typeof v === 'string') setCookies.push(v);
        }
      });
      if (setCookies.length) {
        window.__lastSetCookie = setCookies;
        try {
          window.dispatchEvent(new CustomEvent('capacitor:setcookie', { detail: setCookies }));
        } catch (e) {}
      }

      var payload = res.data;
      if (typeof payload !== 'string') payload = JSON.stringify(payload);
      var headers = new Headers();
      Object.keys(rawHeaders).forEach(function (k) {
        if (String(k).toLowerCase() === 'set-cookie') return;   // 跳过，避免 Headers 报错
        try { headers.set(k, rawHeaders[k]); } catch (e) {}
      });
      return new Response(payload, { status: res.status || 200, statusText: '', headers: headers });
    } catch (e) {
      console.warn('[native-http] 原生请求失败，回退:', url, e && e.message);
      return origFetch(input, init);
    }
  };
  console.log('[native-http] 已接管跨域 fetch（set-cookie 通过 __lastSetCookie 暴露）');
})();
