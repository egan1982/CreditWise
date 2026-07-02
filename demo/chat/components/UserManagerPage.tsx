"use client";

/**
 * UserManagerPage — 用户管理模块 批次2 Phase11
 *
 * Admin「用户管理」独立页面（/user-manager），详见
 * docs/user_management_module_design.md §15.0/§15.3：
 * - 用户列表：用户名/显示名/角色/部门/有效期（临期≤7天黄色高亮，已过期红色高亮）/状态
 * - 新建用户：不要求管理员手输密码，保存后系统自动生成随机密码一次性展示（TD4）
 * - 编辑用户：角色/部门/有效期/启用禁用，username只读
 * - 重置密码 / 合并账户
 *
 * 权限：仅 admin 可访问，非 admin/单用户模式下显示提示而非渲染管理界面
 * （前端隐藏不能代替后端校验，后端 /admin/* 已有双重防线，见 user_admin_api.py）。
 */

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Loader2, ArrowLeft, Plus, KeyRound, Users, RefreshCw } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { authFetch, getApiUrl } from "@/lib/config";
import { useAuthInfo } from "@/hooks/use-auth-info";

interface UserRow {
  username: string;
  display_name: string | null;
  role: "admin" | "user";
  org: string | null;
  description: string | null;
  valid_until: string | null;
  enabled: boolean;
  must_change_password: boolean;
  created_at: string | null;
}

const PAGE_SIZE = 50;

function validUntilBadge(validUntil: string | null) {
  if (!validUntil) {
    return <span className="text-xs text-muted-foreground">永久有效</span>;
  }
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const expiry = new Date(validUntil);
  const daysLeft = Math.floor((expiry.getTime() - today.getTime()) / 86400000);

  if (daysLeft < 0) {
    return (
      <Badge variant="destructive" className="text-[11px]">
        已过期（{validUntil}）
      </Badge>
    );
  }
  if (daysLeft <= 7) {
    return (
      <Badge
        variant="outline"
        className="text-[11px] border-amber-400 text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20"
      >
        {daysLeft} 天后过期（{validUntil}）
      </Badge>
    );
  }
  return <span className="text-xs text-muted-foreground">{validUntil} 前有效</span>;
}

export default function UserManagerPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { authEnabled, user: currentUser, isAdmin, loading: authLoading } = useAuthInfo();

  const [users, setUsers] = useState<UserRow[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [listLoading, setListLoading] = useState(false);

  // 新建用户
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newRole, setNewRole] = useState<"admin" | "user">("user");
  const [newOrg, setNewOrg] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newValidUntil, setNewValidUntil] = useState("");
  const [newDisplayName, setNewDisplayName] = useState("");
  const [usernameError, setUsernameError] = useState("");

  // 编辑用户
  const [editTarget, setEditTarget] = useState<UserRow | null>(null);
  const [editRole, setEditRole] = useState<"admin" | "user">("user");
  const [editOrg, setEditOrg] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editValidUntil, setEditValidUntil] = useState("");
  const [editDisplayName, setEditDisplayName] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);

  // 一次性密码展示
  const [revealPassword, setRevealPassword] = useState<{ username: string; password: string } | null>(null);

  // 合并账户
  const [mergeOpen, setMergeOpen] = useState(false);
  const [mergeFrom, setMergeFrom] = useState("");
  const [mergeTo, setMergeTo] = useState("");
  const [merging, setMerging] = useState(false);

  const loadUsers = useCallback(async () => {
    setListLoading(true);
    try {
      const res = await authFetch(
        getApiUrl(`/admin/users?limit=${PAGE_SIZE}&offset=${offset}`)
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setUsers(data.items || []);
      setTotal(data.total || 0);
    } catch (e) {
      toast({
        description: e instanceof Error ? e.message : "加载用户列表失败",
        variant: "destructive",
      });
    } finally {
      setListLoading(false);
    }
  }, [offset, toast]);

  useEffect(() => {
    if (isAdmin) loadUsers();
  }, [isAdmin, loadUsers]);

  const usernamePattern = /^[a-zA-Z0-9_-]+$/;

  const handleCreate = useCallback(async () => {
    const uname = newUsername.trim();
    if (!uname) {
      setUsernameError("请输入用户名");
      return;
    }
    if (!usernamePattern.test(uname)) {
      setUsernameError("仅支持英文字母、数字、下划线、连字符");
      return;
    }
    setUsernameError("");
    setCreating(true);
    try {
      const res = await authFetch(getApiUrl("/admin/users"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: uname,
          role: newRole,
          org: newOrg || null,
          description: newDescription || null,
          valid_until: newValidUntil || null,
          display_name: newDisplayName || null,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        if (res.status === 409) {
          setUsernameError(err.detail || "该用户名已存在");
          return;
        }
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const created = await res.json();
      setCreateOpen(false);
      setNewUsername("");
      setNewOrg("");
      setNewDescription("");
      setNewValidUntil("");
      setNewDisplayName("");
      setNewRole("user");
      toast({ description: `用户 ${uname} 已创建` });
      setRevealPassword({ username: uname, password: created.initial_password });
      loadUsers();
    } catch (e) {
      toast({
        description: e instanceof Error ? e.message : "创建失败",
        variant: "destructive",
      });
    } finally {
      setCreating(false);
    }
  }, [newUsername, newRole, newOrg, newDescription, newValidUntil, newDisplayName, toast, loadUsers]);

  const openEdit = useCallback((row: UserRow) => {
    setEditTarget(row);
    setEditRole(row.role);
    setEditOrg(row.org || "");
    setEditDescription(row.description || "");
    setEditValidUntil(row.valid_until || "");
    setEditDisplayName(row.display_name || "");
  }, []);

  const handleSaveEdit = useCallback(async () => {
    if (!editTarget) return;
    setSavingEdit(true);
    try {
      const res = await authFetch(getApiUrl(`/admin/users/${encodeURIComponent(editTarget.username)}`), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role: editRole,
          org: editOrg,
          description: editDescription,
          valid_until: editValidUntil || null,
          display_name: editDisplayName,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      toast({ description: "已保存" });
      setEditTarget(null);
      loadUsers();
    } catch (e) {
      toast({
        description: e instanceof Error ? e.message : "保存失败",
        variant: "destructive",
      });
    } finally {
      setSavingEdit(false);
    }
  }, [editTarget, editRole, editOrg, editDescription, editValidUntil, editDisplayName, toast, loadUsers]);

  const handleToggleEnabled = useCallback(
    async (row: UserRow) => {
      if (row.username === currentUser?.username) {
        toast({ description: "不能禁用自己当前登录的账户", variant: "destructive" });
        return;
      }
      try {
        if (row.enabled) {
          // 禁用走 DELETE（软删除，enabled=0）
          const res = await authFetch(getApiUrl(`/admin/users/${encodeURIComponent(row.username)}`), {
            method: "DELETE",
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
          }
        } else {
          // 重新启用走 PUT enabled=true
          const res = await authFetch(getApiUrl(`/admin/users/${encodeURIComponent(row.username)}`), {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled: true }),
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
          }
        }
        toast({ description: row.enabled ? `账户 ${row.username} 已禁用` : `账户 ${row.username} 已启用` });
        loadUsers();
      } catch (e) {
        toast({
          description: e instanceof Error ? e.message : "操作失败",
          variant: "destructive",
        });
      }
    },
    [currentUser, toast, loadUsers]
  );

  const handleResetPassword = useCallback(
    async (row: UserRow) => {
      try {
        const res = await authFetch(
          getApiUrl(`/admin/users/${encodeURIComponent(row.username)}/reset-password`),
          { method: "POST" }
        );
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${res.status}`);
        }
        const data = await res.json();
        setRevealPassword({ username: row.username, password: data.new_password });
      } catch (e) {
        toast({
          description: e instanceof Error ? e.message : "重置密码失败",
          variant: "destructive",
        });
      }
    },
    [toast]
  );

  const handleMerge = useCallback(async () => {
    if (!mergeFrom.trim() || !mergeTo.trim()) {
      toast({ description: "请填写来源账户和目标账户", variant: "destructive" });
      return;
    }
    setMerging(true);
    try {
      const res = await authFetch(getApiUrl("/admin/users/merge"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          from_username: mergeFrom.trim(),
          to_username: mergeTo.trim(),
          dry_run: false,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      toast({ description: `账户合并完成：${JSON.stringify(data.merged)}` });
      setMergeOpen(false);
      setMergeFrom("");
      setMergeTo("");
      loadUsers();
    } catch (e) {
      toast({
        description: e instanceof Error ? e.message : "合并失败",
        variant: "destructive",
      });
    } finally {
      setMerging(false);
    }
  }, [mergeFrom, mergeTo, toast, loadUsers]);

  // ---------------------------------------------------------------------
  // 权限门禁：单用户模式 / 非 admin 均不渲染管理界面（后端仍有独立的双重校验）
  // ---------------------------------------------------------------------
  if (authLoading || authEnabled === null) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!authEnabled) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-3 text-center">
        <p className="text-sm text-muted-foreground">该页面仅在多用户模式下可用</p>
        <Button variant="outline" size="sm" onClick={() => router.push("/")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          返回主界面
        </Button>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-3 text-center">
        <p className="text-sm text-muted-foreground">需要管理员权限才能访问此页面</p>
        <Button variant="outline" size="sm" onClick={() => router.push("/")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          返回主界面
        </Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-5xl space-y-4">
        {/* 顶部栏 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => router.push("/")}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              返回
            </Button>
            <h1 className="flex items-center gap-2 text-lg font-semibold">
              <Users className="h-5 w-5" />
              用户管理
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadUsers} disabled={listLoading}>
              <RefreshCw className={`mr-2 h-4 w-4 ${listLoading ? "animate-spin" : ""}`} />
              刷新
            </Button>
            <Button variant="outline" size="sm" onClick={() => setMergeOpen(true)}>
              合并账户
            </Button>
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              新建用户
            </Button>
          </div>
        </div>

        {/* 用户列表 */}
        <div className="rounded-lg border">
          <Table role="table" aria-label="用户列表">
            <TableHeader>
              <TableRow>
                <TableHead>用户名</TableHead>
                <TableHead>显示名</TableHead>
                <TableHead>角色</TableHead>
                <TableHead>部门</TableHead>
                <TableHead>有效期</TableHead>
                <TableHead>状态</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {listLoading ? (
                <TableRow>
                  <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                    <Loader2 className="mx-auto h-5 w-5 animate-spin" />
                  </TableCell>
                </TableRow>
              ) : users.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                    暂无账户
                  </TableCell>
                </TableRow>
              ) : (
                users.map((row) => (
                  <TableRow key={row.username}>
                    <TableCell className="font-medium">
                      {row.username}
                      {row.username === currentUser?.username && (
                        <Badge variant="secondary" className="ml-2 text-[10px]">
                          我
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>{row.display_name || "-"}</TableCell>
                    <TableCell>
                      <Badge variant={row.role === "admin" ? "default" : "outline"} className="text-[11px]">
                        {row.role === "admin" ? "管理员" : "普通用户"}
                      </Badge>
                    </TableCell>
                    <TableCell>{row.org || "-"}</TableCell>
                    <TableCell>{validUntilBadge(row.valid_until)}</TableCell>
                    <TableCell>
                      {row.enabled ? (
                        <Badge variant="outline" className="text-[11px] text-emerald-700 dark:text-emerald-400 border-emerald-400">
                          启用中
                        </Badge>
                      ) : (
                        <Badge variant="secondary" className="text-[11px]">
                          已禁用
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 min-w-[44px]"
                          onClick={() => openEdit(row)}
                        >
                          编辑
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 min-w-[44px]"
                          title="重置密码"
                          onClick={() => handleResetPassword(row)}
                        >
                          <KeyRound className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 min-w-[44px]"
                          disabled={row.username === currentUser?.username}
                          onClick={() => handleToggleEnabled(row)}
                        >
                          {row.enabled ? "禁用" : "启用"}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* 简单分页 */}
        {total > PAGE_SIZE && (
          <div className="flex items-center justify-end gap-2 text-sm">
            <Button
              variant="outline"
              size="sm"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              上一页
            </Button>
            <span className="text-muted-foreground">
              {offset + 1}-{Math.min(offset + PAGE_SIZE, total)} / {total}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              下一页
            </Button>
          </div>
        )}
      </div>

      {/* 新建用户弹窗 */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-[440px]" aria-modal="true">
          <DialogHeader>
            <DialogTitle>新建用户</DialogTitle>
            <DialogDescription>保存后系统自动生成随机密码，一次性展示</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="new-username" className="text-xs">
                用户名
              </Label>
              <Input
                id="new-username"
                value={newUsername}
                onChange={(e) => {
                  setNewUsername(e.target.value);
                  setUsernameError("");
                }}
                placeholder="仅支持英文字母、数字、下划线、连字符"
              />
              {usernameError && (
                <p className="text-[11px] text-destructive">{usernameError}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">角色</Label>
              <Select value={newRole} onValueChange={(v) => setNewRole(v as "admin" | "user")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">普通用户</SelectItem>
                  <SelectItem value="admin">管理员</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="new-display-name" className="text-xs">
                显示名
              </Label>
              <Input id="new-display-name" value={newDisplayName} onChange={(e) => setNewDisplayName(e.target.value)} placeholder="选填" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="new-org" className="text-xs">
                部门备注
              </Label>
              <Input id="new-org" value={newOrg} onChange={(e) => setNewOrg(e.target.value)} placeholder="选填" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="new-valid-until" className="text-xs">
                有效期（留空=永久有效）
              </Label>
              <Input
                id="new-valid-until"
                type="date"
                value={newValidUntil}
                onChange={(e) => setNewValidUntil(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreate} disabled={creating}>
              {creating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  创建中…
                </>
              ) : (
                "创建"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 编辑用户弹窗 */}
      <Dialog open={!!editTarget} onOpenChange={(open) => !open && setEditTarget(null)}>
        <DialogContent className="sm:max-w-[440px]" aria-modal="true">
          <DialogHeader>
            <DialogTitle>编辑用户</DialogTitle>
          </DialogHeader>
          {editTarget && (
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">用户名</Label>
                <Input value={editTarget.username} disabled className="bg-muted text-muted-foreground" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">角色</Label>
                <Select value={editRole} onValueChange={(v) => setEditRole(v as "admin" | "user")}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="user">普通用户</SelectItem>
                    <SelectItem value="admin">管理员</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="edit-display-name" className="text-xs">
                  显示名
                </Label>
                <Input id="edit-display-name" value={editDisplayName} onChange={(e) => setEditDisplayName(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="edit-org" className="text-xs">
                  部门备注
                </Label>
                <Input id="edit-org" value={editOrg} onChange={(e) => setEditOrg(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="edit-description" className="text-xs">
                  描述
                </Label>
                <Input id="edit-description" value={editDescription} onChange={(e) => setEditDescription(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="edit-valid-until" className="text-xs">
                  有效期（留空=永久有效）
                </Label>
                <Input
                  id="edit-valid-until"
                  type="date"
                  value={editValidUntil}
                  onChange={(e) => setEditValidUntil(e.target.value)}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditTarget(null)}>
              取消
            </Button>
            <Button onClick={handleSaveEdit} disabled={savingEdit}>
              {savingEdit ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  保存中…
                </>
              ) : (
                "保存"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 一次性密码展示弹窗（新建用户 / 重置密码 共用） */}
      <Dialog open={!!revealPassword} onOpenChange={(open) => !open && setRevealPassword(null)}>
        <DialogContent className="sm:max-w-[400px]" aria-modal="true">
          <DialogHeader>
            <DialogTitle>初始密码</DialogTitle>
            <DialogDescription>
              此密码不会再次显示，请通过安全渠道告知用户「{revealPassword?.username}」
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-lg border bg-muted p-4 text-center">
            <p className="select-all font-mono text-lg tracking-wider">
              {revealPassword?.password}
            </p>
          </div>
          <p className="text-[11px] text-muted-foreground">
            该用户下次登录时会被强制要求修改密码
          </p>
          <DialogFooter>
            <Button onClick={() => setRevealPassword(null)}>我已记录，关闭</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 合并账户弹窗 */}
      <Dialog open={mergeOpen} onOpenChange={setMergeOpen}>
        <DialogContent className="sm:max-w-[420px]" aria-modal="true">
          <DialogHeader>
            <DialogTitle>合并账户</DialogTitle>
            <DialogDescription>
              把来源账户名下的历史任务数据/workspace文件批量转移到目标账户名下（改名场景使用）
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="merge-from" className="text-xs">
                来源账户（旧）
              </Label>
              <Input id="merge-from" value={mergeFrom} onChange={(e) => setMergeFrom(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="merge-to" className="text-xs">
                目标账户（新）
              </Label>
              <Input id="merge-to" value={mergeTo} onChange={(e) => setMergeTo(e.target.value)} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setMergeOpen(false)}>
              取消
            </Button>
            <Button onClick={handleMerge} disabled={merging}>
              {merging ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  合并中…
                </>
              ) : (
                "确认合并"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
