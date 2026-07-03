"use client";

/**
 * AccountSettingsDialog — 用户管理模块 批次2 Phase11
 *
 * 「账户设置」弹窗（所有角色通用，仅编辑自己），详见
 * docs/user_management_module_design.md §15.2：
 * - 改密码分区排在最前（高频操作优先）
 * - 个人信息编辑区（显示名/部门备注/描述）在后
 * - username 只读灰色展示
 *
 * 改密码成功后：立即用新密码更新本地 localStorage 凭证（saveAuth），
 * 不强制重新登录，Toast 提示"密码已更新"。
 */

import { useState, useEffect, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Eye, EyeOff } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { authFetch, getApiUrl, saveAuth, clearAuth } from "@/lib/config";
import type { AuthUserInfo } from "@/hooks/use-auth-info";

interface AccountSettingsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  user: AuthUserInfo | null;
  /** 保存成功后回调，供父组件刷新 /auth/me 状态 */
  onUpdated?: () => void;
  /**
   * 强制改密模式（must_change_password=true 时）：
   * - 隐藏取消按钮 / 禁止 Esc 关闭
   * - 只展示改密分区，隐藏个人信息编辑区
   * - 改密成功后自动关闭并触发 onForceChangeSuccess
   */
  forceMode?: boolean;
  onForceChangeSuccess?: () => void;
}

const MIN_PASSWORD_LENGTH = 6;

export default function AccountSettingsDialog({
  isOpen,
  onClose,
  user,
  onUpdated,
  forceMode = false,
  onForceChangeSuccess,
}: AccountSettingsDialogProps) {
  const { toast } = useToast();

  // 改密码
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);
  // 密码"小眼睛"显示/隐藏切换（默认隐藏，与浏览器原生行为一致）
  const [showOldPassword, setShowOldPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // 个人信息
  const [displayName, setDisplayName] = useState("");
  const [org, setOrg] = useState("");
  const [description, setDescription] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);

  useEffect(() => {
    if (isOpen && user) {
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setShowOldPassword(false);
      setShowNewPassword(false);
      setShowConfirmPassword(false);
      setDisplayName(user.display_name || "");
      setOrg(user.org || "");
      setDescription(user.description || "");
    }
  }, [isOpen, user]);

  const handleChangePassword = useCallback(async () => {
    if (!user?.username) return;
    if (!oldPassword) {
      toast({ description: "请输入旧密码", variant: "destructive" });
      return;
    }
    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      toast({
        description: `新密码长度至少 ${MIN_PASSWORD_LENGTH} 位`,
        variant: "destructive",
      });
      return;
    }
    if (newPassword !== confirmPassword) {
      toast({ description: "两次输入的新密码不一致", variant: "destructive" });
      return;
    }

    setChangingPassword(true);
    try {
      const res = await authFetch(getApiUrl("/auth/change-password"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      // 立即用新密码更新本地凭证，无感衔接，不强制重新登录
      saveAuth(user.username, newPassword);
      toast({ description: "密码已更新" });
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
      onUpdated?.();

      if (forceMode) {
        onForceChangeSuccess?.();
      }
    } catch (e) {
      toast({
        description: e instanceof Error ? e.message : "改密失败",
        variant: "destructive",
      });
    } finally {
      setChangingPassword(false);
    }
  }, [user, oldPassword, newPassword, confirmPassword, onUpdated, forceMode, onForceChangeSuccess, toast]);

  const handleSaveProfile = useCallback(async () => {
    setSavingProfile(true);
    try {
      const res = await authFetch(getApiUrl("/auth/profile"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          display_name: displayName,
          org,
          description,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      toast({ description: "个人信息已保存" });
      onUpdated?.();
    } catch (e) {
      toast({
        description: e instanceof Error ? e.message : "保存失败",
        variant: "destructive",
      });
    } finally {
      setSavingProfile(false);
    }
  }, [displayName, org, description, onUpdated, toast]);

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        // 强制改密模式：唯一例外，禁止通过 Esc/点击遮罩关闭（§15.6 无障碍规范明确规定）
        if (!open && forceMode) return;
        if (!open) onClose();
      }}
    >
      <DialogContent
        className="sm:max-w-[440px]"
        onEscapeKeyDown={(e) => {
          if (forceMode) e.preventDefault();
        }}
        onInteractOutside={(e) => {
          if (forceMode) e.preventDefault();
        }}
        // 强制改密弹窗隐藏右上角关闭按钮
        showCloseButton={!forceMode}
      >
        <DialogHeader>
          <DialogTitle>{forceMode ? "首次登录需修改密码" : "账户设置"}</DialogTitle>
          {forceMode && (
            <DialogDescription>
              为了账户安全，请先设置新密码后再继续使用
            </DialogDescription>
          )}
        </DialogHeader>

        <div className="space-y-4">
          {/* username 只读展示 */}
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">登录名</Label>
            <Input
              value={user?.username || ""}
              disabled
              className="bg-muted text-muted-foreground"
            />
            <p className="text-[11px] text-muted-foreground">登录名创建后不可修改</p>
          </div>

          {/* 改密码分区（排在最前，高频操作优先） */}
          <div className="space-y-2 rounded-lg border p-3">
            <p className="text-sm font-medium">修改密码</p>
            <div className="space-y-1.5">
              <Label htmlFor="old-password" className="text-xs">
                旧密码
              </Label>
              <div className="relative">
                <Input
                  id="old-password"
                  type={showOldPassword ? "text" : "password"}
                  autoComplete="current-password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  className="pr-9"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowOldPassword((v) => !v)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label={showOldPassword ? "隐藏密码" : "显示密码"}
                >
                  {showOldPassword ? (
                    <EyeOff className="h-3.5 w-3.5" />
                  ) : (
                    <Eye className="h-3.5 w-3.5" />
                  )}
                </button>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="new-password" className="text-xs">
                新密码
              </Label>
              <div className="relative">
                <Input
                  id="new-password"
                  type={showNewPassword ? "text" : "password"}
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder={`至少 ${MIN_PASSWORD_LENGTH} 位`}
                  className="pr-9"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowNewPassword((v) => !v)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label={showNewPassword ? "隐藏密码" : "显示密码"}
                >
                  {showNewPassword ? (
                    <EyeOff className="h-3.5 w-3.5" />
                  ) : (
                    <Eye className="h-3.5 w-3.5" />
                  )}
                </button>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="confirm-password" className="text-xs">
                确认新密码
              </Label>
              <div className="relative">
                <Input
                  id="confirm-password"
                  type={showConfirmPassword ? "text" : "password"}
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="pr-9"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowConfirmPassword((v) => !v)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label={showConfirmPassword ? "隐藏密码" : "显示密码"}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-3.5 w-3.5" />
                  ) : (
                    <Eye className="h-3.5 w-3.5" />
                  )}
                </button>
              </div>
            </div>
            <div className="flex items-center justify-between pt-1">
              {/* 用户管理模块 批次2 补充加固（2026-07-02）：强制改密弹窗"无法取消"是
                  刻意设计（不改完密码不能用系统），但没考虑"用户根本不知道旧密码"这种
                  死锁场景（如：admin重置密码时生成的一次性密码没被记录/传达到位）。
                  之前唯一的脱身方式是手动在浏览器控制台清localStorage，普通用户不会
                  操作。这里补一个"退出登录"作为正式的逃生出口——不需要知道旧密码，
                  清除本地凭证后回到未登录状态，可以换个账户登录，或联系admin再要一次
                  重置密码。仅在forceMode下展示（非强制模式下已有"关闭"按钮+右上角❌）。 */}
              {forceMode && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-muted-foreground"
                  onClick={() => {
                    clearAuth();
                    window.location.reload();
                  }}
                >
                  忘记旧密码？退出登录
                </Button>
              )}
              <Button
                size="sm"
                onClick={handleChangePassword}
                disabled={changingPassword}
              >
                {changingPassword ? (
                  <>
                    <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                    修改中…
                  </>
                ) : (
                  "确认修改"
                )}
              </Button>
            </div>
          </div>

          {/* 个人信息编辑区（次要位置；强制改密模式下隐藏） */}
          {!forceMode && (
            <div className="space-y-2 rounded-lg border p-3">
              <p className="text-sm font-medium">个人信息</p>
              <div className="space-y-1.5">
                <Label htmlFor="display-name" className="text-xs">
                  显示名
                </Label>
                <Input
                  id="display-name"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="选填"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="org" className="text-xs">
                  部门备注
                </Label>
                <Input
                  id="org"
                  value={org}
                  onChange={(e) => setOrg(e.target.value)}
                  placeholder="选填"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="description" className="text-xs">
                  描述
                </Label>
                <Input
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="选填"
                />
              </div>
              <div className="flex justify-end pt-1">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleSaveProfile}
                  disabled={savingProfile}
                >
                  {savingProfile ? (
                    <>
                      <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                      保存中…
                    </>
                  ) : (
                    "保存"
                  )}
                </Button>
              </div>
            </div>
          )}

          {!forceMode && (
            <div className="flex justify-end">
              <Button variant="ghost" size="sm" onClick={onClose}>
                关闭
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
