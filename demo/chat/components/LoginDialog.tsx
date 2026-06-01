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
import { registerLoginCallback, saveAuth } from "@/lib/config";

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
    const auth = saveAuth(username.trim(), password);
    setVisible(false);
    resolveRef.current?.(auth);
    resolveRef.current = null;
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
