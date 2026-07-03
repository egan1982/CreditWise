"use client";

/**
 * LoginDialog — 替代 window.prompt 的 React 登录弹窗
 *
 * 使用方式：
 *   1. 在根布局中挂载 <LoginDialog />
 *   2. 组件挂载后自动向 config.ts 注册异步弹窗回调
 *   3. authFetch 调用 promptLogin() 时触发此弹窗，用户提交后 Promise resolve
 */

import React, { useState, useEffect, useRef, useCallback } from "react";
import { registerLoginCallback, saveAuth, getApiUrl } from "@/lib/config";

type ResolveFn = (value: string | null) => void;

export default function LoginDialog() {
  const [visible, setVisible] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const resolveRef = useRef<ResolveFn | null>(null);
  const usernameRef = useRef<HTMLInputElement>(null);

  // 注册登录回调，供 authFetch 调用
  useEffect(() => {
    registerLoginCallback(() => {
      return new Promise<string | null>((resolve) => {
        resolveRef.current = resolve;
        setUsername("");
        setPassword("");
        setError("");
        setLoading(false);
        setVisible(true);
      });
    });
  }, []);

  // 弹窗出现时聚焦用户名输入框
  useEffect(() => {
    if (visible) {
      setTimeout(() => usernameRef.current?.focus(), 50);
    }
  }, [visible]);

  const handleSubmit = useCallback(async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!username.trim()) {
      setError("请输入用户名");
      return;
    }
    if (!password) {
      setError("请输入密码");
      return;
    }
    setLoading(true);
    setError("");

    const trimmedUsername = username.trim();
    // 用户管理模块 批次2 补充加固（2026-07-02）：登录前先校验凭证，不再"盲存"。
    //
    // 背景：此前这里直接把输入框内容 base64 编码存进 localStorage 就关闭弹窗、
    // resolve——从不校验对不对。密码错误/账户被锁定时，弹窗不会有任何提示，
    // 用户"进入了页面"，但Files/TaskType/历史记录等各个区域各自收到401/429后
    // 分别展示自己的通用错误文案（"加载失败"），完全看不出是"密码错、还是
    // 账户被锁、还是别的问题"，体验非常confusing。
    //
    // 这里用刚输入的凭证主动打一次 /auth/me 探测（不经过 authFetch/全局拦截器，
    // 避免其401重试逻辑与这里的校验流程互相干扰），根据结果区分：
    // - 200：凭证有效，才真正保存+关闭弹窗
    // - 401：用户名或密码错误，弹窗原地展示错误，不关闭，允许重新输入
    // - 429：账户被锁定（大概率是此前重复输错密码触发），把后端返回的具体提示
    //   （含剩余锁定时长）原样展示出来，而不是让用户在一堆"加载失败"里自己猜
    // - 403：用户管理模块 批次2 补充加固（2026-07-03新增）：密码本身正确，但
    //   账户已被禁用或已过期（`API/auth_middleware.py::authenticate()`区分
    //   返回）。此前这类情况和"密码错误"一样统一走401，弹窗只会显示"用户名或
    //   密码错误"，实测反馈这个提示在过期/禁用账户场景下有很强的误导性——用户
    //   会以为自己记错了密码，反复重试甚至触发锁定，而真正原因是账户状态问题，
    //   跟密码对不对无关。现在后端已能区分这两种情况并返回具体中文提示
    //   （如"账号已过期，请联系管理员"），这里直接展示后端返回的detail。
    try {
      const encoded = btoa(`${trimmedUsername}:${password}`);
      // 用户管理模块 批次3（2026-07-03）：方案名从 `Basic` 改为自定义
      // `CWAuth`，理由见 lib/config.ts::authFetch 顶部注释——避免浏览器把
      // 这次登录探测识别为标准 Basic Auth 并缓存+后续自动重发，导致"退出
      // 登录"被浏览器原生凭证缓存绕过。
      const res = await fetch(getApiUrl("/auth/me"), {
        headers: { Authorization: `CWAuth ${encoded}` },
      });

      if (!res.ok) {
        let detail = "";
        try {
          const body = await res.json();
          if (body?.detail) detail = body.detail;
        } catch {
          /* 忽略解析失败，走下方各状态码的默认文案 */
        }

        if (res.status === 401) {
          // 后端401的detail是英文"Invalid credentials"（内部通用文案），
          // 前端统一用中文提示替代，不直接展示英文原文
          setError("用户名或密码错误");
        } else if (res.status === 429) {
          setError(detail || "账户已被锁定，请稍后重试");
        } else if (res.status === 403) {
          // 后端detail已是可直接展示的中文提示（"账号已被禁用/已过期，请联系管理员"）
          setError(detail || "账号无法登录，请联系管理员");
        } else {
          setError(detail || `登录失败（HTTP ${res.status}），请重试`);
        }
        setLoading(false);
        return;
      }

      // 校验通过，才真正保存凭证并关闭弹窗
      const auth = saveAuth(trimmedUsername, password);
      setVisible(false);
      resolveRef.current?.(auth);
      resolveRef.current = null;
    } catch (err) {
      console.error("[LoginDialog] 登录校验请求失败:", err);
      setError("网络异常，无法连接服务器，请重试");
      setLoading(false);
    }
  }, [username, password]);

  const handleCancel = useCallback(() => {
    setVisible(false);
    resolveRef.current?.(null);
    resolveRef.current = null;
  }, []);

  if (!visible) return null;

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center"
      style={{ backgroundColor: "rgba(0,0,0,0.6)" }}
    >
      <div
        className="w-80 rounded-xl shadow-2xl p-6"
        style={{ backgroundColor: "#1e1e2e", border: "1px solid #3a3a5c" }}
      >
        {/* 标题 */}
        <h2 className="text-base font-semibold text-white mb-1">登录</h2>
        <p className="text-xs mb-4" style={{ color: "#8888aa" }}>
          {typeof window !== "undefined" ? window.location.host : ""}
        </p>

        <form onSubmit={handleSubmit} autoComplete="on">
          {/* 用户名 */}
          <div className="mb-3">
            <label className="block text-xs mb-1" style={{ color: "#aaaacc" }}>
              用户名
            </label>
            <input
              ref={usernameRef}
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm text-white outline-none"
              style={{
                backgroundColor: "#2a2a3e",
                border: "1px solid #4a4a6a",
              }}
              onFocus={(e) =>
                (e.target.style.border = "1px solid #6b7bff")
              }
              onBlur={(e) =>
                (e.target.style.border = "1px solid #4a4a6a")
              }
            />
          </div>

          {/* 密码 */}
          <div className="mb-4">
            <label className="block text-xs mb-1" style={{ color: "#aaaacc" }}>
              密码
            </label>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm text-white outline-none"
              style={{
                backgroundColor: "#2a2a3e",
                border: "1px solid #4a4a6a",
              }}
              onFocus={(e) =>
                (e.target.style.border = "1px solid #6b7bff")
              }
              onBlur={(e) =>
                (e.target.style.border = "1px solid #4a4a6a")
              }
            />
          </div>

          {/* 错误提示 */}
          {error && (
            <p className="text-xs mb-3" style={{ color: "#ff6b6b" }}>
              {error}
            </p>
          )}

          {/* 按钮 */}
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={handleCancel}
              className="px-4 py-2 rounded-lg text-sm"
              style={{
                backgroundColor: "#2a2a3e",
                color: "#aaaacc",
                border: "1px solid #4a4a6a",
              }}
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded-lg text-sm font-medium text-white"
              style={{
                backgroundColor: loading ? "#4a5aaa" : "#3b4bdf",
                cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              {loading ? "登录中…" : "登录"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
