"use client";

/**
 * useAuthInfo — 用户管理模块 批次2 Phase11
 *
 * 统一探测：
 * 1. `/auth/mode`：是否启用认证（单用户模式下 auth_enabled=false，前端应完全
 *    不渲染登录/账户设置/用户管理等相关UI，详见 docs/user_management_module_design.md §2.4/§15.0）
 * 2. `/auth/me`：当前登录用户的角色/个人信息/是否需要强制改密（must_change_password，TD4）
 *
 * 说明：`three-panel-interface.tsx` 中批次1 Phase1 已有一份独立的 `/auth/me` 调用
 * （仅用于取 username 覆盖 sessionId），本 Hook 是批次2 新增、职责不同（角色权限
 * 判断+强制改密弹窗触发），两者共存会各自发一次 `/auth/me` 请求——这是为了不改动
 * 已上线批次1逻辑而做的保守取舍，接口开销极小（本地/内网请求），可接受。
 */

import { useState, useEffect, useCallback } from "react";
import { authFetch, getApiUrl } from "@/lib/config";

export interface AuthUserInfo {
  username: string | null;
  authenticated: boolean;
  display_name?: string | null;
  role?: "admin" | "user" | null;
  org?: string | null;
  description?: string | null;
  valid_until?: string | null;
  must_change_password?: boolean;
}

export interface UseAuthInfoResult {
  /** null = 尚未探测完成（加载中），探测完成后为 true/false */
  authEnabled: boolean | null;
  user: AuthUserInfo | null;
  loading: boolean;
  isAdmin: boolean;
  /** 重新拉取 /auth/me（改密/编辑资料成功后调用，刷新 must_change_password 等状态） */
  refreshUser: () => Promise<void>;
}

export function useAuthInfo(): UseAuthInfoResult {
  const [authEnabled, setAuthEnabled] = useState<boolean | null>(null);
  const [user, setUser] = useState<AuthUserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const res = await authFetch(getApiUrl("/auth/me"));
      if (res.ok) {
        const data = await res.json();
        setUser(data);
      }
    } catch (e) {
      // 静默失败：网络异常时维持现状，不阻塞主界面渲染
      console.warn("[useAuthInfo] /auth/me 请求失败:", e);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      // `/auth/mode` 在认证白名单内，无需认证即可探测，用普通 fetch 避免触发登录弹窗
      try {
        const res = await fetch(getApiUrl("/auth/mode"));
        if (!cancelled && res.ok) {
          const data = await res.json();
          setAuthEnabled(!!data.auth_enabled);
        } else if (!cancelled) {
          setAuthEnabled(false);
        }
      } catch {
        if (!cancelled) setAuthEnabled(false);
      }

      await refreshUser();
      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshUser]);

  return {
    authEnabled,
    user,
    loading,
    isAdmin: user?.role === "admin",
    refreshUser,
  };
}
