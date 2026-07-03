/**
 * LLM Manager 前端 Basic Auth 支持
 *
 * 用户管理模块 批次2 补充加固（2026-07-02）
 *
 * 背景：LLM Manager 是一套独立的原生 JS 前端（main.js 等），此前从未适配过
 * 多用户模式（ENABLE_AUTH=true）——所有 fetch() 调用都不带任何认证信息，
 * 在开启鉴权后全部收到 401，表现为"渠道列表卡在加载中、各Tab点击无响应"。
 *
 * 本文件必须在 main.js / model-config.js 等其他脚本【之前】加载（见 index.html
 * 的 <script> 顺序），职责：
 *   1. 从 localStorage 读取 Basic Auth 凭证并全局注入到所有同源 fetch 请求
 *      （localStorage key 复用 'creditwise_auth'，与 demo/chat 前端保持一致——
 *      生产同源部署下两个前端同源，凭证可以直接共享，用户在主界面登录后点开
 *      「LLM渠道管理」不需要再登录一次；开发模式下 3001 与 3000 是不同 origin，
 *      localStorage 天然隔离，仍需要单独登录一次，这是预期行为）
 *   2. 请求收到 401 时清除本地凭证、弹出登录框，用户输入后重试原始请求
 *
 * 不使用浏览器原生 Basic Auth 弹窗（会在部分内嵌 WebView 环境下卡死且体验反直觉），
 * 后端 API/auth_middleware.py 已针对 AJAX 请求去掉 WWW-Authenticate 响应头，
 * 保证 401 只会走到这里的自定义登录框，不会触发原生弹窗。
 */
(function () {
  "use strict";

  var AUTH_STORAGE_KEY = "creditwise_auth";

  function getStoredAuth() {
    try {
      return localStorage.getItem(AUTH_STORAGE_KEY);
    } catch (e) {
      return null;
    }
  }

  function saveAuth(username, password) {
    var encoded = btoa(username + ":" + password);
    try {
      localStorage.setItem(AUTH_STORAGE_KEY, encoded);
    } catch (e) {
      /* ignore storage errors (e.g. 隐私模式) */
    }
    return encoded;
  }

  function clearAuth() {
    try {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    } catch (e) {
      /* ignore */
    }
  }

  // -----------------------------------------------------------------------
  // 登录弹窗（vanilla JS，风格对齐 demo/chat 的 LoginDialog）
  // -----------------------------------------------------------------------
  var _pendingResolve = null;

  function getBackendOrigin() {
    var port = window.location.port;
    if (port === "8200" || port === "") {
      return window.location.origin;
    }
    // 开发模式：LLM Manager 在 3001，后端在 8200
    return window.location.protocol + "//" + window.location.hostname + ":8200";
  }

  function ensureLoginModal() {
    var existing = document.getElementById("llm-manager-login-overlay");
    if (existing) return existing;

    var overlay = document.createElement("div");
    overlay.id = "llm-manager-login-overlay";
    overlay.style.cssText =
      "position:fixed;inset:0;z-index:99999;display:flex;align-items:center;" +
      "justify-content:center;background:rgba(0,0,0,0.6);";

    overlay.innerHTML =
      '<div style="width:320px;border-radius:12px;box-shadow:0 20px 25px -5px rgba(0,0,0,.3);' +
      'padding:24px;background:#1e1e2e;border:1px solid #3a3a5c;">' +
      '  <h2 style="font-size:15px;font-weight:600;color:#fff;margin:0 0 4px;">登录</h2>' +
      '  <p id="llm-manager-login-host" style="font-size:12px;color:#8888aa;margin:0 0 16px;"></p>' +
      '  <form id="llm-manager-login-form" autocomplete="on">' +
      '    <div style="margin-bottom:12px;">' +
      '      <label style="display:block;font-size:12px;color:#aaaacc;margin-bottom:4px;">用户名</label>' +
      '      <input id="llm-manager-login-username" type="text" autocomplete="username" ' +
      '        style="width:100%;box-sizing:border-box;border-radius:8px;padding:8px 12px;' +
      'font-size:13px;color:#fff;background:#2a2a3e;border:1px solid #4a4a6a;outline:none;" />' +
      "    </div>" +
      '    <div style="margin-bottom:16px;">' +
      '      <label style="display:block;font-size:12px;color:#aaaacc;margin-bottom:4px;">密码</label>' +
      '      <input id="llm-manager-login-password" type="password" autocomplete="current-password" ' +
      '        style="width:100%;box-sizing:border-box;border-radius:8px;padding:8px 12px;' +
      'font-size:13px;color:#fff;background:#2a2a3e;border:1px solid #4a4a6a;outline:none;" />' +
      "    </div>" +
      '    <p id="llm-manager-login-error" style="font-size:12px;color:#ff6b6b;margin:0 0 12px;display:none;"></p>' +
      '    <div style="display:flex;justify-content:flex-end;gap:8px;">' +
      '      <button type="button" id="llm-manager-login-cancel" style="padding:8px 16px;' +
      'border-radius:8px;font-size:13px;color:#aaaacc;background:#2a2a3e;border:1px solid #4a4a6a;' +
      'cursor:pointer;">取消</button>' +
      '      <button type="submit" style="padding:8px 16px;border-radius:8px;font-size:13px;' +
      'font-weight:500;color:#fff;background:#3b4bdf;border:none;cursor:pointer;">登录</button>' +
      "    </div>" +
      "  </form>" +
      "</div>";

    document.body.appendChild(overlay);

    var hostEl = overlay.querySelector("#llm-manager-login-host");
    if (hostEl) hostEl.textContent = window.location.host;

    var form = overlay.querySelector("#llm-manager-login-form");
    var usernameInput = overlay.querySelector("#llm-manager-login-username");
    var passwordInput = overlay.querySelector("#llm-manager-login-password");
    var errorEl = overlay.querySelector("#llm-manager-login-error");
    var cancelBtn = overlay.querySelector("#llm-manager-login-cancel");

    var submitBtn = form.querySelector('button[type="submit"]');

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var username = (usernameInput.value || "").trim();
      var password = passwordInput.value || "";
      if (!username) {
        errorEl.textContent = "请输入用户名";
        errorEl.style.display = "block";
        return;
      }
      if (!password) {
        errorEl.textContent = "请输入密码";
        errorEl.style.display = "block";
        return;
      }

      // 用户管理模块 批次2 补充加固（2026-07-02）：登录前先校验凭证，不再"盲存"。
      // 与 demo/chat 的 LoginDialog.tsx 同一bug同一修法——此前直接 saveAuth 后就
      // 关闭弹窗，密码错误/账户锁定时毫无提示，用户"进入了页面"却各个区域各自
      // 收到401/429后展示各自的通用错误文案，完全看不出真实原因。
      errorEl.style.display = "none";
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "登录中…";
      }
      var encoded = btoa(username + ":" + password);
      _originalFetch(getBackendOrigin() + "/auth/me", {
        headers: { Authorization: "Basic " + encoded },
      })
        .then(function (res) {
          if (!res.ok) {
            // 用户管理模块 批次2 补充加固（2026-07-03）：区分"密码错误"与
            // "密码正确但账户已禁用/已过期"（403，与 demo/chat 的 LoginDialog.tsx
            // 同一bug同一修法）。此前401/403统一提示"用户名或密码错误"，对过期/
            // 禁用账户场景有很强误导性（密码明明是对的）。
            return res
              .json()
              .catch(function () {
                return null;
              })
              .then(function (body) {
                var detail = body && body.detail;
                if (res.status === 401) {
                  // 后端401的detail是英文"Invalid credentials"（内部通用文案），
                  // 前端统一用中文提示替代
                  errorEl.textContent = "用户名或密码错误";
                } else if (res.status === 429) {
                  errorEl.textContent = detail || "账户已被锁定，请稍后重试";
                } else if (res.status === 403) {
                  // 后端detail已是可直接展示的中文提示
                  errorEl.textContent = detail || "账号无法登录，请联系管理员";
                } else {
                  errorEl.textContent =
                    detail || "登录失败（HTTP " + res.status + "），请重试";
                }
                errorEl.style.display = "block";
              });
          }
          // 校验通过，才真正保存凭证并关闭弹窗
          var auth = saveAuth(username, password);
          overlay.style.display = "none";
          if (_pendingResolve) {
            var resolve = _pendingResolve;
            _pendingResolve = null;
            resolve(auth);
          }
        })
        .catch(function (err) {
          errorEl.textContent = "网络异常，无法连接服务器，请重试";
          errorEl.style.display = "block";
        })
        .finally(function () {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = "登录";
          }
        });
    });

    cancelBtn.addEventListener("click", function () {
      overlay.style.display = "none";
      if (_pendingResolve) {
        var resolve = _pendingResolve;
        _pendingResolve = null;
        resolve(null);
      }
    });

    return overlay;
  }

  // 用户管理模块 批次2 补充加固（2026-07-02）：并发 401 去重。
  // 背景：页面上多个区域（渠道列表/日志/统计等）会几乎同时发起请求，一旦凭证失效，会
  // 【同时】收到 401，各自独立调用 promptLogin()。但 _pendingResolve 是单个全局变量，
  // 后一次调用会覆盖前一次，导致除最后一次外的所有等待者永久收不到 resolve，对应的
  // fetch 永久挂起（与 demo/chat 的 lib/config.ts 是同一个bug模式，此处同步修复）。
  // 修复：并发调用共享同一个 pending Promise，只弹一次登录框。
  var _pendingLoginPromise = null;

  function promptLogin() {
    if (_pendingLoginPromise) {
      return _pendingLoginPromise;
    }
    _pendingLoginPromise = new Promise(function (resolve) {
      var overlay = ensureLoginModal();
      var usernameInput = overlay.querySelector("#llm-manager-login-username");
      var passwordInput = overlay.querySelector("#llm-manager-login-password");
      var errorEl = overlay.querySelector("#llm-manager-login-error");
      usernameInput.value = "";
      passwordInput.value = "";
      errorEl.style.display = "none";
      overlay.style.display = "flex";
      _pendingResolve = resolve;
      setTimeout(function () {
        usernameInput.focus();
      }, 50);
    }).then(function (result) {
      _pendingLoginPromise = null;
      return result;
    });
    return _pendingLoginPromise;
  }

  // -----------------------------------------------------------------------
  // 全局 fetch 拦截：注入凭证 + 401 时弹登录框重试一次
  // -----------------------------------------------------------------------
  var _originalFetch = window.fetch.bind(window);

  window.fetch = function (input, init) {
    init = init || {};
    var urlStr =
      typeof input === "string"
        ? input
        : input && input.url
        ? input.url
        : String(input);
    var isSameOrigin =
      urlStr.indexOf("/") === 0 || urlStr.indexOf(window.location.origin) === 0;

    var headers = new Headers(init.headers || {});
    if (isSameOrigin && !headers.has("Authorization")) {
      var auth = getStoredAuth();
      if (auth) headers.set("Authorization", "Basic " + auth);
    }

    return _originalFetch(input, Object.assign({}, init, { headers: headers })).then(
      function (response) {
        if (response.status !== 401 || !isSameOrigin) return response;

        clearAuth();
        return promptLogin().then(function (newAuth) {
          if (!newAuth) return response; // 用户取消，返回原始401响应
          var retryHeaders = new Headers(init.headers || {});
          retryHeaders.set("Authorization", "Basic " + newAuth);
          return _originalFetch(
            input,
            Object.assign({}, init, { headers: retryHeaders })
          );
        });
      }
    );
  };
})();
