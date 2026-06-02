"use client";

import type React from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import {
  oneDark,
  oneLight,
} from "react-syntax-highlighter/dist/esm/styles/prism";
import Editor from "@monaco-editor/react";
import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { API_URLS, API_CONFIG, getApiUrl, authFetch } from "@/lib/config";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable";
import {
  Send,
  Sparkles,
  User,
  Paperclip,
  X,
  FileText,
  ImageIcon,
  ChevronDown,
  ChevronRight,
  CheckSquare,
  Square,
  Trash2,
  Download,
  Play,
  Save,
  FolderOpen,
  RefreshCw,
  Moon,
  Sun,
  Eraser,
  Copy,
  Check,
  Edit,
  Upload,
  Square,
  Code2,
  BrainCircuit,
  Loader2,
} from "lucide-react";
import { Tree, NodeApi } from "react-arborist";
import { useToast } from "@/hooks/use-toast";
import { FileIcon, defaultStyles } from "react-file-icon";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import ModelSelector from "./ModelSelector";
import { 
  TaskSelector, 
  TaskConfigPanel,
  TaskProgress, 
  RuleMiningResults, 
  ScorecardResults, 
  SopStageController, 
  StageOutputPreview, 
  ExecutionLogPanel,
  ModeSelector,
  TaskHistoryCompact,
} from "./sop";
import type { TaskHistoryCompactRef } from "./sop";
import { sopService, ExecutionStatus, StageProgress } from "@/lib/sopService";
import { ModeProvider, useModeContext, useIsExpertMode, InteractionMode } from "@/hooks/use-mode";
import { FileReference, FileReferenceList, formatFileReferencesForMessage } from "./FileReferenceTag";
import { isTaskParamJson } from "@/lib/taskParamParser";
import { TaskConfirmCard, CardStatus } from "./sop/TaskConfirmCard";
import { SensitiveCheckDialog } from "./sop/SensitiveCheckDialog";
import type { SensitiveCheckResult } from "./sop/SensitiveCheckDialog";

// 模型配置类型定义（与后端API响应匹配）
interface ModelConfig {
  id: number;
  name: string;
  type: string;
  models: string;
  has_model_config: boolean;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  system_prompt?: string;
  enable_web_search?: boolean;
  enable_deep_thinking?: boolean;
  thinking_budget?: number;
  include_thoughts?: boolean;
}

interface Message {
  id: string;
  content: string;
  sender: "user" | "ai";
  timestamp: Date;
  attachments?: FileAttachment[];
  localOnly?: boolean;
}

interface FileAttachment {
  id: string;
  name: string;
  size: number;
  type: string;
  url: string;
}

interface WorkspaceFile {
  name: string;
  size: number;
  extension: string;
  icon: string;
  download_url: string;
  preview_url?: string;
}

type WorkspaceNode = {
  name: string;
  path: string; // relative path
  is_dir: boolean;
  size?: number;
  extension?: string;
  icon?: string;
  download_url?: string;
  children?: WorkspaceNode[];
  is_generated?: boolean; // 标识是否为代码生成的文件或文件夹
};

interface AnalysisSection {
  type: "Analyze" | "Understand" | "Code" | "Execute" | "Answer";
  content: string;
  icon: string;
  color: string;
}

// 阶段执行顺序后备定义（用于API未返回stage_order时的兼容）
const TASK_STAGE_ORDER_FALLBACK: Record<string, string[]> = {
  scorecard_dev: ["data_loading", "woe_binning", "feature_selection", "model_training", "score_scaling", "model_evaluation", "report_generation"],
  rule_mining: ["preprocessing", "feature_engineering", "generating_rules", "rule_filtering", "selecting_rules", "report_generation"],
};

// 获取阶段执行顺序：优先使用API返回的stage_order，后备使用硬编码
function getStageOrder(status: { task_id: string; stage_order?: string[] } | null): string[] {
  if (status?.stage_order && status.stage_order.length > 0) {
    return status.stage_order;
  }
  return status?.task_id ? (TASK_STAGE_ORDER_FALLBACK[status.task_id] || []) : [];
}

// 内部组件：使用 ModeContext
function ThreePanelInterfaceInner() {
  const { toast } = useToast();
  const [isDarkMode, setIsDarkMode] = useState(false); // 服务端默认 false
  const [mounted, setMounted] = useState(false);
  const [editorHeight, setEditorHeight] = useState(60); // 编辑器高度百分比
  const [collapsedSections, setCollapsedSections] = useState<
    Record<string, boolean>
  >({});
  const [autoCollapseEnabled, setAutoCollapseEnabled] = useState(true);
  const [manualLocks, setManualLocks] = useState<Record<string, boolean>>({});

  // Session ID：用于区分不同浏览器用户（无需登录）
  const [sessionId, setSessionId] = useState<string>("");

  // 步骤导航相关状态
  const [activeSection, setActiveSection] = useState<string>("");
  const stepNavigatorRef = useRef<HTMLDivElement>(null);
  const activeStepRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // 组件挂载后从 localStorage 读取主题
  useEffect(() => {
    setMounted(true);
    if (typeof window !== "undefined") {
      // 初始化或获取 sessionId
      let sid = localStorage.getItem("sessionId");
      if (!sid) {
        sid = `session_${Date.now()}_${Math.random()
          .toString(36)
          .substr(2, 9)}`;
        localStorage.setItem("sessionId", sid);
      }
      setSessionId(sid);

      const savedTheme = localStorage.getItem("theme");
      const shouldBeDark = savedTheme === "dark";
      setIsDarkMode(shouldBeDark);
      updateThemeClass(shouldBeDark);
      const savedAuto = localStorage.getItem("autoCollapseEnabled");
      if (savedAuto !== null) {
        setAutoCollapseEnabled(savedAuto !== "false");
      }
    }
  }, []);

  // 按 session 维度持久化/恢复 折叠状态 与 手动锁
  useEffect(() => {
    if (!sessionId) return;
    try {
      const cs = localStorage.getItem(`collapsedSections:${sessionId}`);
      if (cs) setCollapsedSections(JSON.parse(cs));
      const ml = localStorage.getItem(`manualLocks:${sessionId}`);
      if (ml) setManualLocks(JSON.parse(ml));
    } catch {}
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    try {
      localStorage.setItem(
        `collapsedSections:${sessionId}`,
        JSON.stringify(collapsedSections)
      );
      localStorage.setItem(
        `manualLocks:${sessionId}`,
        JSON.stringify(manualLocks)
      );
    } catch {}
  }, [sessionId, collapsedSections, manualLocks]);

  // 当 activeSection 变化时自动滚动到对应步骤
  useEffect(() => {
    if (activeSection && stepNavigatorRef.current) {
      const activeStepElement = activeStepRefs.current.get(activeSection);
      if (activeStepElement) {
        const container = stepNavigatorRef.current;
        const stepRect = activeStepElement.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();

        // 计算需要滚动的距离
        const scrollLeft =
          activeStepElement.offsetLeft -
          containerRect.width / 2 +
          stepRect.width / 2;

        // 平滑滚动到目标位置
        container.scrollTo({
          left: scrollLeft,
          behavior: "smooth",
        });
      }
    }
  }, [activeSection]);

  // 更新主题 class
  const updateThemeClass = (isDark: boolean) => {
    if (typeof document !== "undefined") {
      if (isDark) {
        document.documentElement.classList.add("dark");
      } else {
        document.documentElement.classList.remove("dark");
      }
    }
  };

  // 获取某条消息之前最近的用户问题内容
  const getPrevUserQuestionText = (index: number): string => {
    for (let i = index - 1; i >= 0; i--) {
      const m = messages[i];
      if (m && m.sender === "user") return m.content || "";
    }
    return "";
  };

  const buildReportFilename = (question: string) => {
    const clean = (question || "").replace(/\s+/g, " ").trim();
    let tokens = clean.split(/\s+/).filter(Boolean);
    let base = "";
    if (tokens.length <= 1) {
      // 中文/无空格：直接取前 5 个字符，不再用下划线
      base = clean.replace(/\s+/g, "").slice(0, 5);
    } else {
      // 英文/有空格：取前 5 个词，用下划线连接
      base = tokens
        .slice(0, 5)
        .map((t) => t.replace(/[\\/:*?"<>|]/g, ""))
        .filter(Boolean)
        .join("_");
    }
    base = base.slice(0, 120);
    return `Report_${base || "Untitled"}.pdf`;
  };

  const exportReportBackend = async () => {
    try {
      const payloadMessages = messages
        .filter((m) => !m.localOnly)
        .map((msg) => ({
          role: msg.sender === "user" ? "user" : "assistant",
          content: msg.content,
        }));
      const title = getPrevUserQuestionText(messages.length);
      const res = await authFetch(getApiUrl(API_URLS.EXPORT_REPORT), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: payloadMessages,
          title,
          session_id: sessionId,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const md = data?.md;
      toast({ description: `已提交并生成: ${md}` });
      await loadWorkspaceFiles();
      await loadWorkspaceTree?.();
    } catch (e) {
      console.error("backend export error", e);
      toast({ description: "导出失败", variant: "destructive" });
    }
  };

  // 切换主题
  const toggleTheme = () => {
    const newDarkMode = !isDarkMode;
    setIsDarkMode(newDarkMode);
    updateThemeClass(newDarkMode);

    // 保存到 localStorage
    if (typeof window !== "undefined") {
      localStorage.setItem("theme", newDarkMode ? "dark" : "light");
    }
  };

  // 处理拖动调整大小
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    const startY = e.clientY;
    const startHeight = editorHeight;

    const handleMouseMove = (e: MouseEvent) => {
      const container = document.querySelector(".editor-container");
      if (!container) return;

      const containerRect = container.getBoundingClientRect();
      const deltaY = e.clientY - startY;
      const containerHeight = containerRect.height;
      const deltaPercent = (deltaY / containerHeight) * 100;

      const newHeight = Math.min(Math.max(startHeight + deltaPercent, 20), 80);
      setEditorHeight(newHeight);
    };

    const handleMouseUp = () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome-1",
      content: "您好！我是CreditWise，您的信贷风控助手。我可以自动执行包括数据处理、分析、建模、可视化和报告生成在内的各类数据任务，同时支持结构化数据（数据库、CSV、Excel）、半结构化数据（JSON、XML、YAML）和非结构化数据（TXT、Markdown）等多种数据源。上传您的数据，让我们开启任务吧！",
      sender: "ai",
      timestamp: new Date(),
      localOnly: true,
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [attachments, setAttachments] = useState<FileAttachment[]>([]);
  const [fileReferences, setFileReferences] = useState<FileReference[]>([]); // 文件引用（右键添加到AI对话）
  const [selectedConfig, setSelectedConfig] = useState<ModelConfig | null>(null); // 模型配置选择
  const [workspaceFiles, setWorkspaceFiles] = useState<WorkspaceFile[]>([]);
  const [workspaceTree, setWorkspaceTree] = useState<WorkspaceNode | null>(
    null
  );
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const treeContainerRef = useRef<HTMLDivElement>(null);
  const [treeSize, setTreeSize] = useState<{ w: number; h: number }>({
    w: 0,
    h: 0,
  });
  
  // SOP任务相关状态
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [showConfigPanel, setShowConfigPanel] = useState(false);
  const [isSOPExecuting, setIsSOPExecuting] = useState(false);
  const [currentExecutionId, setCurrentExecutionId] = useState<string | null>(null);
  const [showResults, setShowResults] = useState(false);
  const [completedExecutionId, setCompletedExecutionId] = useState<string | null>(null);
  const [sopExecutionStatus, setSopExecutionStatus] = useState<ExecutionStatus | null>(null);
  // 轮询重启触发器：paused 状态停止轮询后，用户操作（继续/重试/跳过）时递增此值重启轮询

  // SOP 模式：任意 SOP 面板激活时为 true，此时 Chat 消息区自动隐藏，释放空间给 SOP 工作区
  const isSopMode = showConfigPanel || isSOPExecuting || showResults;
  const [pollTrigger, setPollTrigger] = useState(0);
  const restartPolling = () => setPollTrigger(prev => prev + 1);
  // 结果视图模式：results=显示最终结果，stages=显示阶段详情
  const [resultViewMode, setResultViewMode] = useState<"results" | "stages">("results");
  
  // Roadmap Phase 2: 模式选择状态（通过 ModeContext 集中管理）
  // 注意：engineMode 已废弃，统一使用 Pipeline 执行引擎
  // 使用 ModeContext 替代本地状态，避免 prop drilling
  const { 
    interactionMode, 
    setInteractionMode, 
    historyTaskInteractionMode, 
    setHistoryTaskInteractionMode,
    isExpertMode: isExpertModeTask  // 统一的专家模式判断
  } = useModeContext();
  const [showTaskHistory, setShowTaskHistory] = useState(false);
  
  // Phase 3: 阶段输出预览相关状态
  const [selectedStageId, setSelectedStageId] = useState<string | null>(null);
  const [selectedStageData, setSelectedStageData] = useState<StageProgress | null>(null);
  const [rightPanelMode, setRightPanelMode] = useState<"code" | "log" | "preview">("code");
  // 用户手动选择标记：当用户点击阶段卡片时设为true，自动跟踪时不覆盖用户选择
  const [isUserManualSelection, setIsUserManualSelection] = useState(false);
  
  // 使用ref跟踪最新的selectedStageId，避免useCallback闭包问题
  const selectedStageIdRef = useRef<string | null>(null);
  const isUserManualSelectionRef = useRef(false);
  // 记录上一次轮询时的最后完成阶段ID，用于检测"真正的新阶段完成"
  const lastCompletedStageIdRef = useRef<string | null>(null);
  
  // 同步ref值
  useEffect(() => {
    selectedStageIdRef.current = selectedStageId;
  }, [selectedStageId]);
  
  useEffect(() => {
    isUserManualSelectionRef.current = isUserManualSelection;
  }, [isUserManualSelection]);
  
  // 任务确认卡片相关状态（P2-8 Chat任务入口交互优化）
  // 每个消息的确认卡片状态: pending / confirmed / dismissed
  const [confirmCardStatuses, setConfirmCardStatuses] = useState<Record<string, CardStatus>>({});
  // 会话级记忆：用户已跳过的任务类型，同一会话内不再弹出
  const [dismissedTaskTypes, setDismissedTaskTypes] = useState<Set<string>>(new Set());
  // 暂存 LLM 提取的参数，确认后注入 ConfigPanel
  const [pendingInitialParams, setPendingInitialParams] = useState<Record<string, any> | null>(null);
  
  // AI分析评估相关状态
  const [isAIAnalyzing, setIsAIAnalyzing] = useState(false);
  const [aiAnalysisResult, setAiAnalysisResult] = useState<string | null>(null);
  const [showAIAnalysisPanel, setShowAIAnalysisPanel] = useState(false);
  // 历史任务的执行模式已移至 ModeContext（historyTaskInteractionMode）
  // 历史任务的记录ID（用于 AI 分析持久化，Phase 7）
  const [historyTaskRecordId, setHistoryTaskRecordId] = useState<string | null>(null);
  // Phase 20: 任务执行结果（用于专家模式最后阶段整体分析）
  const [taskExecutionResult, setTaskExecutionResult] = useState<Record<string, any> | null>(null);
  
  const [selectedCodeSection, setSelectedCodeSection] = useState<string>("");
  const [codeEditorContent, setCodeEditorContent] = useState("");
  const [showCodeEditor, setShowCodeEditor] = useState(false);
  const [isExecutingCode, setIsExecutingCode] = useState(false);
  const [codeExecutionResult, setCodeExecutionResult] = useState("");

  // 预览弹窗状态
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [previewTitle, setPreviewTitle] = useState<string>("");
  const [previewContent, setPreviewContent] = useState<string>("");
  const [previewType, setPreviewType] = useState<
    "text" | "image" | "pdf" | "binary"
  >("text");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewDownloadUrl, setPreviewDownloadUrl] = useState<string>("");
  const previewScrollRef = useRef<HTMLDivElement>(null);
  const [deleteConfirmPath, setDeleteConfirmPath] = useState<string | null>(
    null
  );
  const [deleteIsDir, setDeleteIsDir] = useState<boolean>(false);
  const fileRefreshTimerRef = useRef<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const singleClickTimerRef = useRef<number | null>(null);
  const historyCompactRef = useRef<TaskHistoryCompactRef>(null);

  // 敏感信息预检状态
  const [sensitiveResult, setSensitiveResult] = useState<SensitiveCheckResult | null>(null);
  const [sensitiveDialogOpen, setSensitiveDialogOpen] = useState(false);
  const [sensitiveFileName, setSensitiveFileName] = useState<string>("");
  const [sensitiveFilePath, setSensitiveFilePath] = useState<string>(""); // 记录已上传文件路径，用于高危时回滚删除

  // workspace 多选状态
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const [batchDeleteOpen, setBatchDeleteOpen] = useState(false);

  // 收集文件树中所有叶子节点（非文件夹）路径，用于全选
  const collectAllFilePaths = useCallback((node: WorkspaceNode | null): string[] => {
    if (!node) return [];
    if (!node.is_dir) return [node.path];
    return (node.children || []).flatMap(collectAllFilePaths);
  }, []);

  const allFilePaths = useMemo(
    () => collectAllFilePaths(workspaceTree),
    [workspaceTree, collectAllFilePaths]
  );

  const isAllSelected = allFilePaths.length > 0 && allFilePaths.every(p => selectedPaths.has(p));
  const isPartialSelected = !isAllSelected && allFilePaths.some(p => selectedPaths.has(p));

  const toggleSelectAll = () => {
    if (isAllSelected) {
      setSelectedPaths(new Set());
    } else {
      setSelectedPaths(new Set(allFilePaths));
    }
  };

  const toggleSelectPath = (path: string) => {
    setSelectedPaths(prev => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const handleBatchDelete = async () => {
    for (const p of Array.from(selectedPaths)) {
      await deleteFile(p);
    }
    setSelectedPaths(new Set());
    setBatchDeleteOpen(false);
  };
  const [contextPos, setContextPos] = useState<{ x: number; y: number } | null>(
    null
  );
  const [contextTarget, setContextTarget] = useState<WorkspaceNode | null>(
    null
  );
  const [dragOverPath, setDragOverPath] = useState<string | null>(null);
  const [dropActive, setDropActive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string>("");

  const lastScrollTimeRef = useRef(0);
  const scrollRafRef = useRef<number | null>(null);

  // 节流滚动到底部
  const scrollToBottom = useCallback(() => {
    const now = Date.now();
    const timeSinceLastScroll = now - lastScrollTimeRef.current;

    // 节流：至少间隔 100ms
    if (timeSinceLastScroll < 100) {
      return;
    }

    if (scrollRafRef.current) {
      cancelAnimationFrame(scrollRafRef.current);
    }

    scrollRafRef.current = requestAnimationFrame(() => {
      if (messagesContainerRef.current) {
        const container = messagesContainerRef.current;
        container.scrollTop = container.scrollHeight;
        lastScrollTimeRef.current = Date.now();
      }
      scrollRafRef.current = null;
    });
  }, []);

  // AI 输入时持续滚动
  useEffect(() => {
    if (isTyping) {
      // 每 200ms 检查并滚动一次
      const intervalId = setInterval(() => {
        if (messagesContainerRef.current) {
          const container = messagesContainerRef.current;
          // 直接设置到底部
          container.scrollTop = container.scrollHeight;
        }
      }, 200);

      return () => {
        clearInterval(intervalId);
      };
    } else {
      // 输入完成，平滑滚动到底部
      setTimeout(() => {
        if (messagesContainerRef.current) {
          messagesContainerRef.current.scrollTo({
            top: messagesContainerRef.current.scrollHeight,
            behavior: "smooth",
          });
        }
      }, 100);
    }
  }, [isTyping]);

  // 监听消息变化
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // 聊天消息本地缓存：加载与保存
  const CHAT_STORAGE_KEY = "chat_messages_v1";
  const [chatLoaded, setChatLoaded] = useState(false);

  // 挂载后再次从本地覆盖加载，避免 SSR 初始状态覆盖缓存
  useEffect(() => {
    try {
      if (typeof window === "undefined") return;
      const raw = localStorage.getItem(CHAT_STORAGE_KEY);
      if (raw) {
        const arr = JSON.parse(raw) as any[];
        if (Array.isArray(arr) && arr.length) {
          const restored = arr.map((m) => ({
            ...m,
            timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
          })) as Message[];
          
          setMessages(restored);
        } else {
          // 如果localStorage中没有有效消息，不设置状态，使用初始的中文欢迎消息
          // 这样确保新用户看到的是中文欢迎消息
        }
      } else {
        // 如果localStorage中没有消息，不设置状态，使用初始的中文欢迎消息
        // 这样确保新用户看到的是中文欢迎消息
      }
    } catch (e) {
      console.warn("post-mount load chat cache failed", e);
    }
    setChatLoaded(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);



  // 每次消息变更时保存到本地
  useEffect(() => {
    try {
      if (!chatLoaded) return; // 避免首屏用欢迎消息覆盖已有缓存
      if (typeof window === "undefined") return;
      const data = JSON.stringify(
        messages.map((m) => ({
          ...m,
          timestamp: (m.timestamp instanceof Date
            ? m.timestamp
            : new Date(m.timestamp as any)
          ).toISOString(),
        }))
      );
      localStorage.setItem(CHAT_STORAGE_KEY, data);
    } catch (e) {
      console.warn("save chat cache failed", e);
    }
  }, [messages, chatLoaded]);

  // 一键清空聊天：保留欢迎消息（仅本地显示）
  const clearChat = () => {
    if (isTyping) {
      toast({ description: "执行中，暂时无法清空", variant: "destructive" });
      return;
    }
    const welcome: Message = {
      id: `welcome-${Date.now()}`,
      content: "您好！我是CreditWise，您的信贷风控助手。我可以自动执行包括数据处理、分析、建模、可视化和报告生成在内的各类数据任务，同时支持结构化数据（数据库、CSV、Excel）、半结构化数据（JSON、XML、YAML）和非结构化数据（TXT、Markdown）等多种数据源。上传您的数据，让我们开启任务吧！",
      sender: "ai",
      timestamp: new Date(),
      localOnly: true,
    };
    setMessages([welcome]);
    try {
      if (typeof window !== "undefined") {
        localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify([welcome]));
      }
    } catch {}
    toast({ description: "已清空聊天" });
  };

  useEffect(() => {
    if (sessionId) {
      loadWorkspaceFiles();
      loadWorkspaceTree();
    }
  }, [sessionId]);

  useEffect(() => {
    const id = setInterval(() => {
      if (!isUploading) {
        loadWorkspaceTree();
        loadWorkspaceFiles();
      }
    }, 4000);
    return () => clearInterval(id);
  }, [isUploading]);

  useEffect(() => {
    const el = treeContainerRef.current;
    if (!el) return;
    const ro = new (window as any).ResizeObserver((entries: any) => {
      for (const entry of entries) {
        const cr = entry.contentRect as DOMRectReadOnly;
        setTreeSize({
          w: Math.max(0, Math.floor(cr.width)),
          h: Math.max(0, Math.floor(cr.height)),
        });
      }
    });
    ro.observe(el);
    const rect = el.getBoundingClientRect();
    setTreeSize({
      w: Math.max(0, Math.floor(rect.width)),
      h: Math.max(0, Math.floor(rect.height)),
    });
    return () => ro.disconnect();
  }, []);

  const loadWorkspaceFiles = async () => {
    if (!sessionId) return;
    try {
      const response = await authFetch(
        `${getApiUrl(API_URLS.WORKSPACE_FILES)}?session_id=${sessionId}`
      );
      if (response.ok) {
        const data = await response.json();
        setWorkspaceFiles(data.files);
      }
    } catch (error) {
      console.error("Failed to load workspace files:", error);
    }
  };

  const loadWorkspaceTree = async () => {
    if (!sessionId) return;
    try {
      const res = await authFetch(
        `${getApiUrl(API_URLS.WORKSPACE_TREE)}?session_id=${sessionId}`
      );
      if (res.ok) {
        const data = await res.json();
        // 标记 generated 文件夹及其内容
        const markGenerated = (
          node: WorkspaceNode,
          parentIsGenerated = false
        ) => {
          const isGenerated =
            parentIsGenerated ||
            node.name === "generated" ||
            node.path.startsWith("generated/") ||
            node.path.startsWith("generated");
          node.is_generated = isGenerated;
          if (node.children) {
            node.children.forEach((child) => markGenerated(child, isGenerated));
          }
        };
        if (data) {
          markGenerated(data);
        }
        setWorkspaceTree(data);
        // 默认展开根与第一层，包括 generated 文件夹
        const init: Record<string, boolean> = { "": true };
        if (data?.children) {
          data.children.forEach((c: WorkspaceNode) => {
            if (c.is_dir) init[c.path] = true;
          });
        }
        setExpanded(init);
      }
    } catch (e) {
      console.error("load tree error", e);
    }
  };

  const toggleExpand = (p: string) =>
    setExpanded((prev) => ({ ...prev, [p]: !prev[p] }));

  const deleteFile = async (p: string) => {
    try {
      const url = `${getApiUrl(API_URLS.WORKSPACE_DELETE_FILE)}?path=${encodeURIComponent(
        p
      )}&session_id=${encodeURIComponent(sessionId)}`;
      const res = await authFetch(url, { method: "DELETE" });
      if (res.ok) {
        await loadWorkspaceTree();
        await loadWorkspaceFiles();
      }
    } catch (e) {
      console.error("delete file error", e);
    }
  };

  const deleteDir = async (p: string) => {
    try {
      const url = `${getApiUrl(API_URLS.WORKSPACE_DELETE_DIR)}?path=${encodeURIComponent(
        p
      )}&recursive=true&session_id=${encodeURIComponent(sessionId)}`;
      const res = await authFetch(url, { method: "DELETE" });
      if (res.ok) {
        await loadWorkspaceTree();
        await loadWorkspaceFiles();
      }
    } catch (e) {
      console.error("delete dir error", e);
    }
  };

  // 移动：将工作区内的文件/文件夹移动到指定目录（空字符串表示根目录）
  const moveToDir = async (srcPath: string, dstDir: string) => {
    try {
      const url = `${
        API_CONFIG.BACKEND_BASE_URL
      }/workspace/move?src=${encodeURIComponent(
        srcPath
      )}&dst_dir=${encodeURIComponent(dstDir)}&session_id=${encodeURIComponent(
        sessionId
      )}`;
      const res = await authFetch(url, { method: "POST" });
      if (res.ok) {
        await loadWorkspaceTree();
        await loadWorkspaceFiles();
      }
    } catch (e) {
      console.error("move to dir error", e);
    }
  };

  const uploadToDir = async (dirPath: string, files: FileList | File[]) => {
    try {
      setIsUploading(true);
      const form = new FormData();
      const arr: File[] = Array.from(files as File[]);
      arr.forEach((f) => form.append("files", f));
      const url = `${getApiUrl(API_URLS.WORKSPACE_UPLOAD_TO)}?dir=${encodeURIComponent(
        dirPath || ""
      )}&session_id=${encodeURIComponent(sessionId)}`;
      await authFetch(url, { method: "POST", body: form });
      await loadWorkspaceTree();
      await loadWorkspaceFiles();
      setUploadMsg(`上传成功 ${arr.length} 个文件`);
      setTimeout(() => setUploadMsg(""), 2000);

      // 上传成功后对 CSV 文件触发敏感信息预检（个保法合规）
      const csvFiles = arr.filter(f => f.name.toLowerCase().endsWith(".csv"));
      for (const csvFile of csvFiles) {
        try {
          const filePath = dirPath ? `${dirPath}/${csvFile.name}` : csvFile.name;
          const resp = await authFetch(getApiUrl("/sop/data/sensitive-check"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ file_path: filePath, session_id: sessionId, sample_rows: 100 }),
          });
          if (resp.ok) {
            const result: SensitiveCheckResult = await resp.json();
            if (result.has_sensitive && (result.max_level === "high" || result.max_level === "medium")) {
              setSensitiveResult(result);
              setSensitiveFileName(csvFile.name);
              setSensitiveFilePath(filePath);  // 记录路径，高危时回滚删除
              setSensitiveDialogOpen(true);
              break; // 一次只展示一个文件的结果，逐一处理
            }
          }
        } catch (e) {
          // 检测失败静默处理，不阻断正常上传流程
          console.warn("Sensitive check failed for", csvFile.name, e);
        }
      }
    } catch (e) {
      console.error("upload to dir error", e);
      setUploadMsg("上传失败");
      setTimeout(() => setUploadMsg(""), 2500);
    }
    setIsUploading(false);
  };

  const openNode = async (node: WorkspaceNode) => {
    if (node.is_dir) return;
    const ext = (node.extension || "").replace(/^\./, "").toLowerCase();
    // 后端返回的download_url已经是正确的完整路径，无需修正
    const downloadUrl = node.download_url || "";
    const mapped: WorkspaceFile = {
      name: node.name,
      size: node.size || 0,
      extension: ext,
      icon: node.icon || "",
      download_url: downloadUrl,
      preview_url: downloadUrl,
    };
    openPreview(mapped);
  };

  const onContextMenu = (e: React.MouseEvent, node: WorkspaceNode) => {
    e.preventDefault();
    setContextTarget(node);
    setContextPos({ x: e.clientX, y: e.clientY });
  };

  const closeContext = () => {
    setContextPos(null);
    setContextTarget(null);
  };

  // 将后端树转换为 Arborist 数据
  type ArborNode = {
    id: string;
    name: string;
    isDir: boolean;
    icon?: string;
    download_url?: string;
    extension?: string;
    size?: number;
    children?: ArborNode[];
    isGenerated?: boolean; // 标识是否为代码生成的文件
  };

  const toArbor = (node: WorkspaceNode): ArborNode => {
    const filteredChildren = node.children?.map(toArbor);
    
    return {
      id: node.path || "",
      name: node.name || "workspace",
      isDir: node.is_dir,
      icon: node.icon,
      download_url: node.download_url,
      extension: node.extension,
      size: node.size,
      isGenerated: node.is_generated,
      children: filteredChildren,
    };
  };

  const getExt = (name?: string, ext?: string) => {
    const fromExt = (ext || "").replace(/^\./, "").toLowerCase();
    if (fromExt) return fromExt;
    if (!name) return "txt";
    const p = name.lastIndexOf(".");
    return p > -1 ? name.slice(p + 1).toLowerCase() : "txt";
  };

  const Row = ({
    node,
    style,
    dragHandle,
  }: {
    node: NodeApi<ArborNode>;
    style: React.CSSProperties;
    dragHandle?: (el: HTMLDivElement | null) => void;
  }) => {
    const data = node.data;
    const isDir = data.isDir;
    const isGenerated = data.isGenerated || false;
    const isGeneratedFolder = isDir && data.name === "generated";
    const ext = getExt(data.name, data.extension);

    return (
      <div style={style}>
        {/* Generated 分组标题 + 删除按钮（不遮挡、不受折叠影响） */}
        {isGeneratedFolder && (
          <div className="mt-2 mb-1 px-2 flex items-center justify-between select-none">
            <div className="flex items-center gap-2 text-[11px] text-purple-600 dark:text-purple-400">
              <span className="h-px w-4 bg-purple-200 dark:bg-purple-800" />
              <span className="font-medium">代码生成文件</span>
            </div>
            <button
              className="text-red-600 hover:text-red-700 p-1 rounded hover:bg-red-50 dark:hover:bg-red-950/20"
              aria-label="删除生成文件夹"
              title="删除生成文件夹"
              onClick={(e) => {
                e.stopPropagation();
                setDeleteIsDir(true);
                setDeleteConfirmPath(data.id);
              }}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
        <div
          className={`flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-900 rounded px-2 py-1 group ${
            isGenerated ? "bg-purple-50 dark:bg-purple-950/20" : ""
          } ${!isDir && selectedPaths.has(data.id) ? "bg-blue-50 dark:bg-blue-950/20" : ""}`}
          onClick={(e) => {
            if (isDir) {
              node.toggle();
              return;
            }
            if (singleClickTimerRef.current) {
              window.clearTimeout(singleClickTimerRef.current);
              singleClickTimerRef.current = null;
            }
            // 延迟触发预览，若短时间内发生双击会被取消
            singleClickTimerRef.current = window.setTimeout(() => {
              openNode({
                name: data.name,
                path: data.id,
                is_dir: false,
                download_url: data.download_url,
                extension: data.extension,
                size: data.size,
                icon: data.icon,
              } as any);
              singleClickTimerRef.current = null;
            }, 180);
          }}
          onDoubleClick={(e) => {
            if (isDir) return;
            e.stopPropagation();
            if (singleClickTimerRef.current) {
              window.clearTimeout(singleClickTimerRef.current);
              singleClickTimerRef.current = null;
            }
            if (data.download_url) {
              downloadFileByUrl(data.name, data.download_url);
            }
          }}
          onContextMenu={(e) =>
            onContextMenu(
              e as any,
              {
                name: data.name,
                path: data.id,
                is_dir: isDir,
                download_url: data.download_url,
                extension: data.extension,
                size: data.size,
                icon: data.icon,
              } as any
            )
          }
          onDragOver={(e) => {
            if (isDir) {
              e.preventDefault();
              e.dataTransfer.dropEffect = (e.dataTransfer.types || []).includes(
                "text/x-workspace-path"
              )
                ? "move"
                : "copy";
            }
          }}
          onDragEnter={(e) => {
            if (isDir) setDragOverPath(data.id);
          }}
          onDragLeave={(e) => {
            if (isDir) setDragOverPath(null);
          }}
          onDrop={(e) => {
            if (!isDir) return;
            e.preventDefault();
            uploadToDir(data.id, e.dataTransfer.files || []);
            setDragOverPath(null);
          }}
        >
          <div
            className="flex items-center gap-2 text-sm"
            ref={dragHandle}
            draggable={!isDir}
            onDragStart={(e) => {
              if (isDir) return;
              // 将工作区内路径放入自定义 MIME，供目标目录 onDrop 读取
              e.dataTransfer.setData("text/x-workspace-path", data.id);
              // 提示为移动操作
              e.dataTransfer.effectAllowed = "move";
            }}
          >
            {/* 文件行：checkbox 图标（hover 或已选中时显示） */}
            {!isDir && (
              <div
                className={`shrink-0 transition-opacity ${
                  selectedPaths.has(data.id) ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                }`}
                onClick={(e) => {
                  e.stopPropagation();
                  toggleSelectPath(data.id);
                }}
              >
                {selectedPaths.has(data.id) ? (
                  <CheckSquare className="h-3.5 w-3.5 text-blue-500" />
                ) : (
                  <Square className="h-3.5 w-3.5 text-gray-400" />
                )}
              </div>
            )}
            {isDir ? (
              <>
                <span
                  className={
                    isGenerated
                      ? "text-purple-600 dark:text-purple-400"
                      : "text-gray-500"
                  }
                >
                  {node.isOpen ? "▾" : "▸"}
                </span>
                {isGenerated ? (
                  <Code2 className="h-3.5 w-3.5 text-purple-600 dark:text-purple-400" />
                ) : (
                  <FolderOpen className="h-3.5 w-3.5 text-gray-500" />
                )}
              </>
            ) : (
              <div style={{ width: 16, height: 16 }}>
                {/* 动态扩展样式，fallback 到 txt */}
                {/* @ts-ignore */}
                <FileIcon
                  extension={ext}
                  {...((defaultStyles as any)[ext] ||
                    (defaultStyles as any).txt)}
                />
              </div>
            )}
            <Tooltip>
              <TooltipTrigger asChild>
                <span
                  className={`truncate ${
                    isGenerated
                      ? "text-purple-700 dark:text-purple-300 font-medium"
                      : ""
                  }`}
                >
                  {data.name}
                </span>
              </TooltipTrigger>
              <TooltipContent side="right" className="text-xs">
                {isDir ? "右键查看文件夹操作" : "右键查看文件操作（预览 / 下载 / 删除）"}
              </TooltipContent>
            </Tooltip>
            {typeof data.size === "number" && !isDir && (
              <span className="text-[10px] text-gray-400 ml-2 shrink-0">
                {formatFileSize(data.size)}
              </span>
            )}
            {isGenerated && !isDir && (
              <Sparkles className="h-3 w-3 text-purple-500 ml-1 shrink-0" />
            )}
          </div>
          {/* 行尾不再展示下载/删除按钮。双击/点击行为保持不变；右键菜单提供下载/删除。*/}
        </div>
      </div>
    );
  };

  const renderTree = (node: WorkspaceNode, depth = 0) => {
    const isDir = node.is_dir;
    const isGenerated = node.is_generated || false;
    const isGeneratedFolder = isDir && node.name === "generated" && depth === 1;
    const pad = { paddingLeft: `${8 + depth * 14}px` } as React.CSSProperties;

    return (
      <div key={node.path || "root"}>
        {/* Generated 文件夹上方添加分隔线 */}
        {isGeneratedFolder && (
          <div className="mb-2 mt-2 ml-2 border-t-2 border-purple-200 dark:border-purple-800 relative">
            <div className="absolute -top-2.5 left-2 bg-white dark:bg-gray-950 px-2 text-[10px] text-purple-600 dark:text-purple-400 font-medium">
              代码生成文件
            </div>
          </div>
        )}
        <div
          className={`flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-900 rounded px-2 py-1 cursor-default ${
            isGenerated ? "bg-purple-50 dark:bg-purple-950/20" : ""
          }`}
          style={pad}
          onClick={(e) => {
            if (isDir) return toggleExpand(node.path);
            if (singleClickTimerRef.current) {
              window.clearTimeout(singleClickTimerRef.current);
              singleClickTimerRef.current = null;
            }
            singleClickTimerRef.current = window.setTimeout(() => {
              openNode(node);
              singleClickTimerRef.current = null;
            }, 180);
          }}
          onDoubleClick={(e) => {
            if (isDir) return;
            e.stopPropagation();
            if (singleClickTimerRef.current) {
              window.clearTimeout(singleClickTimerRef.current);
              singleClickTimerRef.current = null;
            }
            if (node.download_url) {
              downloadFileByUrl(node.name, node.download_url);
            } else {
              openNode(node);
            }
          }}
          onContextMenu={(e) => onContextMenu(e, node)}
          onDragOver={(e) => {
            if (isDir) e.preventDefault();
          }}
          onDrop={async (e) => {
            if (!isDir) return;
            e.preventDefault();
            const dt = e.dataTransfer;
            // 1) 如果是从 OS 拖入文件
            if (dt.files && dt.files.length) {
              uploadToDir(node.path, dt.files || []);
              return;
            }
            // 2) 如果是从 generated/ 内部拖动的文件，使用自定义 data 传递路径
            const srcPath = dt.getData("text/x-workspace-path");
            if (srcPath) {
              try {
                const url = `${
                  API_CONFIG.BACKEND_BASE_URL
                }/workspace/move?src=${encodeURIComponent(
                  srcPath
                )}&dst_dir=${encodeURIComponent(
                  node.path
                )}&session_id=${encodeURIComponent(sessionId)}`;
                const res = await authFetch(url, { method: "POST" });
                if (res.ok) {
                  await loadWorkspaceTree();
                  await loadWorkspaceFiles();
                }
              } catch (err) {
                console.error("move error", err);
              }
            }
          }}
        >
          <div className="flex items-center gap-2 text-sm">
            {isDir ? (
              <>
                <span
                  className={
                    isGenerated
                      ? "text-purple-600 dark:text-purple-400"
                      : "text-gray-500"
                  }
                >
                  {expanded[node.path] ? "▾" : "▸"}
                </span>
                {isGenerated ? (
                  <Code2
                    className={`h-3.5 w-3.5 ${
                      isGenerated
                        ? "text-purple-600 dark:text-purple-400"
                        : "text-gray-500"
                    }`}
                  />
                ) : (
                  <FolderOpen className="h-3.5 w-3.5 text-gray-500" />
                )}
              </>
            ) : (
              <span
                className={isGenerated ? "text-purple-400" : "text-gray-400"}
              >
                •
              </span>
            )}
            <Tooltip>
              <TooltipTrigger asChild>
                <span
                  className={`truncate ${
                    isGenerated
                      ? "text-purple-700 dark:text-purple-300 font-medium"
                      : ""
                  }`}
                >
                  {node.icon && !isGenerated ? `${node.icon} ` : ""}
                  {node.name || "workspace"}
                </span>
              </TooltipTrigger>
              <TooltipContent side="right" className="text-xs">
                {isDir ? "右键查看文件夹操作" : "右键查看文件操作（预览 / 下载 / 删除）"}
              </TooltipContent>
            </Tooltip>
            {!isDir && typeof node.size === "number" && (
              <span className="text-[10px] text-gray-400 ml-2 shrink-0">
                {formatFileSize(node.size)}
              </span>
            )}
            {isGenerated && !isDir && (
              <Sparkles className="h-3 w-3 text-purple-500 ml-1 shrink-0" />
            )}
          </div>
          {/* 双击/点击行为已经在容器上：目录展开，文件预览/下载保持一致 */}
        </div>
        {isDir && expanded[node.path] && node.children && (
          <div>{node.children.map((c) => renderTree(c, depth + 1))}</div>
        )}
      </div>
    );
  };

  const clearWorkspace = async () => {
    if (!sessionId) return;
    try {
      const response = await authFetch(
        `${getApiUrl(API_URLS.WORKSPACE_CLEAR)}?session_id=${sessionId}`,
        {
          method: "DELETE",
        }
      );
      if (response.ok) {
        setWorkspaceFiles([]);
        await loadWorkspaceTree();
        await loadWorkspaceFiles();
        toast({
          description: "工作区已清空",
        });
      }
    } catch (error) {
      console.error("Failed to clear workspace:", error);
      toast({
        description: "清空失败",
        variant: "destructive",
      });
    }
  };

  const copyToClipboard = async (text: string): Promise<boolean> => {
    try {
      // 优先使用安全的 Clipboard API
      if (
        typeof navigator !== "undefined" &&
        (navigator as any).clipboard &&
        typeof (navigator as any).clipboard.writeText === "function"
      ) {
        await (navigator as any).clipboard.writeText(text);
        return true;
      }
    } catch (e) {
      // 继续尝试后备方案
    }
    try {
      // 后备方案：隐形 textarea + execCommand
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      textarea.style.pointerEvents = "none";
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(textarea);
      return ok;
    } catch (e) {
      return false;
    }
  };

  const extractCode = (content: string): string => {
    const codeBlockMatch = content.match(/```(?:python)?\n?([\s\S]*?)```/);
    return codeBlockMatch ? codeBlockMatch[1].trim() : content;
  };

  const guessLanguageByExtension = (ext: string): string => {
    const e = ext.toLowerCase();
    const map: Record<string, string> = {
      js: "javascript",
      jsx: "jsx",
      ts: "typescript",
      tsx: "tsx",
      json: "json",
      py: "python",
      md: "markdown",
      html: "html",
      css: "css",
      sh: "bash",
      yml: "yaml",
      yaml: "yaml",
      csv: "csv",
      txt: "text",
      go: "go",
      rs: "rust",
      java: "java",
      php: "php",
      sql: "sql",
    };
    return map[e] || "text";
  };

  const normalizeToLocalFileUrl = (rawUrl: string): string => {
    const base =
      (API_CONFIG as any).FILE_SERVER_BASE || "http://localhost:8100";
    const safeBase = base.replace(/\/$/, "");

    if (!rawUrl) return safeBase;
    const trimmed = String(rawUrl).trim();

    // 绝对 http/https 链接：若是 localhost/127.* 或端口为 8100，则重写到 FILE_SERVER_BASE
    if (/^https?:\/\//i.test(trimmed)) {
      try {
        const u = new URL(trimmed);
        const needRewrite =
          u.hostname === "localhost" ||
          u.hostname.startsWith("127.") ||
          u.port === "8100";
        if (needRewrite) {
          const b = new URL(safeBase + "/");
          return `${b.origin}${b.pathname.replace(/\/$/, "")}${u.pathname}${
            u.search
          }${u.hash}`;
        }
        return trimmed;
      } catch {
        // fallthrough to relative handling
      }
    }

    // 处理以 // 开头的协议相对链接
    if (/^\/\//.test(trimmed)) {
      const proto =
        typeof window !== "undefined" ? window.location.protocol : "http:";
      return proto + trimmed;
    }

    // 去掉开头的 ./
    const rel = trimmed.replace(/^\.\//, "");

    // 如果以 /workspace/ 开头，接到文件服务器
    if (/^\/workspace\//.test(rel)) return `${safeBase}${rel}`;
    if (/^workspace\//.test(rel)) return `${safeBase}/${rel}`;

    // 其它相对路径或文件名，也认为位于文件服务器根目录
    return `${safeBase}/${rel.replace(/^\//, "")}`;
  };

  // 若 URL 缺少 generated 目录，则在 session 段后注入 /generated
  const ensureGeneratedInUrl = (url: string): string => {
    try {
      const u = new URL(url);
      // 仅处理指向文件服务器(8100)的链接
      if (!(u.hostname === "localhost" || u.hostname.startsWith("127."))) {
        return url;
      }
      // 路径形如 /session_xxx/xxx.png，则插入 /generated
      const parts = u.pathname.split("/").filter(Boolean);
      if (parts.length >= 2) {
        const [maybeSession, second] = parts;
        if (maybeSession.startsWith("session_") && second !== "generated") {
          const rest = parts.slice(1).join("/");
          u.pathname = `/${maybeSession}/generated/${rest}`;
          return u.toString();
        }
      }
      return url;
    } catch {
      return url;
    }
  };

  const openPreview = async (file: WorkspaceFile) => {
    setPreviewTitle(file.name);
    setPreviewDownloadUrl(file.download_url);
    setIsPreviewOpen(true);
    setPreviewLoading(true);

    const ext = (file.extension || "").toLowerCase();
    // 使用传入的URL，后端已返回正确路径
    const fileUrl = file.preview_url || file.download_url;
    
    if (["png", "jpg", "jpeg", "gif", "svg", "webp"].includes(ext)) {
      setPreviewType("image");
      setPreviewContent(fileUrl);
      setPreviewLoading(false);
      return;
    }
    if (ext === "pdf") {
      setPreviewType("pdf");
      setPreviewContent(fileUrl);
      setPreviewLoading(false);
      return;
    }

    // 二进制文件类型（Excel、Word、压缩包等）- 直接提示下载
    const binaryExtensions = [
      "xlsx", "xls", "xlsm", "xlsb",  // Excel
      "doc", "docx",                   // Word
      "ppt", "pptx",                   // PowerPoint
      "zip", "rar", "7z", "tar", "gz", // 压缩包
      "exe", "dll", "so", "dylib",     // 可执行文件
      "bin", "dat", "db", "sqlite"     // 其他二进制
    ];
    if (binaryExtensions.includes(ext)) {
      setPreviewType("binary");
      setPreviewContent(file.download_url);
      setPreviewLoading(false);
      return;
    }

    // 文本类型文件列表（包括CSV、代码文件等）
    const textExtensions = [
      "csv", "txt", "md", "json", "xml", "yaml", "yml",
      "py", "js", "ts", "tsx", "jsx", "html", "css", "scss",
      "sql", "sh", "bat", "ps1", "log", "ini", "conf", "cfg"
    ];

    try {
      // 对于已知的文本类型文件，通过代理获取内容以避免CORS
      if (textExtensions.includes(ext)) {
        // 通过后端代理以避免 CORS
        const res = await authFetch(
          `${API_CONFIG.BACKEND_BASE_URL}/proxy?url=${encodeURIComponent(fileUrl)}`
        );
        if (res.ok) {
          const text = await res.text();
          setPreviewType("text");
          setPreviewContent(text);
          setPreviewLoading(false);
          return;
        }
      }

      // 其他文件尝试通过代理获取
      const normalized = normalizeToLocalFileUrl(fileUrl);
      // 通过后端代理以避免 CORS
      const res = await authFetch(
        `${API_CONFIG.BACKEND_BASE_URL}/proxy?url=${encodeURIComponent(normalized)}`
      );
      const contentType = res.headers.get("content-type") || "";
      if (!res.ok) throw new Error("failed to fetch preview");
      if (
        contentType.startsWith("text/") ||
        contentType.includes("json") ||
        contentType.includes("xml") ||
        contentType.includes("csv")
      ) {
        const text = await res.text();
        setPreviewType("text");
        setPreviewContent(text);
      } else {
        // 非文本直接提示下载/打开
        setPreviewType("binary");
        setPreviewContent(file.download_url);
      }
    } catch (e) {
      setPreviewType("binary");
      setPreviewContent(file.download_url);
    } finally {
      setPreviewLoading(false);
    }
  };

  useEffect(() => {
    if (isPreviewOpen && !previewLoading && previewScrollRef.current) {
      previewScrollRef.current.scrollTop = 0;
    }
  }, [isPreviewOpen, previewLoading, previewType, previewContent]);

  const handleDownload = async () => {
    try {
      if (previewType === "text" && typeof previewContent === "string") {
        const blob = new Blob([previewContent], {
          type: "text/plain;charset=utf-8",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = previewTitle || "file.txt";
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        return;
      }

      const normalized = normalizeToLocalFileUrl(
        previewDownloadUrl || previewContent
      );
      const target = ensureGeneratedInUrl(normalized);
      const res = await authFetch(
        `${API_CONFIG.BACKEND_BASE_URL}/proxy?url=${encodeURIComponent(target)}`
      );
      if (!res.ok) throw new Error("download failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = previewTitle || "download";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      const url = ensureGeneratedInUrl(previewDownloadUrl || previewContent);
      window.open(url, "_blank");
    }
  };

  const downloadFileByUrl = async (fileName: string, rawUrl: string) => {
    try {
      const normalized = normalizeToLocalFileUrl(rawUrl);
      const target = ensureGeneratedInUrl(normalized);
      const res = await authFetch(
        `${API_CONFIG.BACKEND_BASE_URL}/proxy?url=${encodeURIComponent(target)}`
      );
      if (!res.ok) throw new Error("download failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fileName || "download";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      const fallbackUrl = ensureGeneratedInUrl(rawUrl);
      window.open(fallbackUrl, "_blank");
    }
  };

  const executeCode = async () => {
    setIsExecutingCode(true);
    try {
      const response = await authFetch(getApiUrl(API_URLS.EXECUTE_CODE), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          code: codeEditorContent,
          session_id: sessionId,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setCodeExecutionResult(data.result);
        await loadWorkspaceFiles(); // Refresh file list after execution
      } else {
        setCodeExecutionResult("Error: Failed to execute code");
      }
    } catch (error) {
      setCodeExecutionResult(`Error: ${error}`);
    } finally {
      setIsExecutingCode(false);
    }
  };

  const CodeBlock = ({
    language,
    code,
    showHeader = false,
  }: {
    language: string;
    code: string;
    showHeader?: boolean;
  }) => {
    const [isCollapsed, setIsCollapsed] = useState(false);
    const [isCopied, setIsCopied] = useState(false);

    const handleCopy = async () => {
      try {
        await navigator.clipboard.writeText(code.trim());
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 1500);
        toast({ description: "已复制代码" });
      } catch {
        toast({ description: "复制失败", variant: "destructive" });
      }
    };

    return (
      <div className="code-block my-3 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
        {showHeader && (
          <div className="flex items-center justify-between bg-gray-50 dark:bg-gray-800 px-3 py-2 text-xs">
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsCollapsed(!isCollapsed)}
                className="h-5 w-5 p-0 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                {isCollapsed ? (
                  <ChevronRight className="h-3 w-3" />
                ) : (
                  <ChevronDown className="h-3 w-3" />
                )}
              </Button>
              <span className="text-gray-600 dark:text-gray-300">Code</span>
              <span className="text-gray-500 font-mono">
                {language || "text"}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopy}
                className="h-5 px-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                {isCopied ? (
                  <Check className="h-3 w-3" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setCodeEditorContent(code.trim());
                  setSelectedCodeSection(code);
                  setShowCodeEditor(true);
                }}
                className="h-5 px-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                <Edit className="h-3 w-3" />
              </Button>
            </div>
          </div>
        )}
        {!showHeader || !isCollapsed ? (
          <SyntaxHighlighter
            language={language || "text"}
            style={isDarkMode ? oneDark : oneLight}
            customStyle={{
              margin: 0,
              background: "transparent",
              overflowX: "hidden",
              whiteSpace: "pre-wrap",
            }}
            codeTagProps={{
              style: {
                fontFamily: "var(--font-mono)",
                fontSize: "0.875rem",
                whiteSpace: "pre-wrap",
              },
            }}
          >
            {code.trim()}
          </SyntaxHighlighter>
        ) : null}
      </div>
    );
  };

  const renderMarkdownContent = (
    content: string,
    options?: { withinSection?: boolean }
  ) => {
    const withinSection = options?.withinSection ?? false;
    // 先处理代码块，将其分离出来
    const parts = content.split(/(```[\w]*\n[\s\S]*?```)/g);

    return (
      <div className="prose prose-sm max-w-none dark:prose-invert break-words [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5">
        {parts.map((part, index) => {
          // 检查是否是代码块
          const codeBlockMatch = part.match(/```(\w+)?\n([\s\S]*?)```/);
          if (codeBlockMatch) {
            const [, language, code] = codeBlockMatch;
            return (
              <CodeBlock
                key={index}
                language={language || "python"}
                code={code}
                showHeader={!withinSection}
              />
            );
          }

          // 处理普通 markdown 内容
          if (part.trim()) {
            return (
              <ReactMarkdown
                key={index}
                remarkPlugins={[remarkGfm]}
                components={{
                  code: ({ children, ...props }: any) => (
                    <code
                      className="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded text-sm font-mono"
                      {...props}
                    >
                      {children}
                    </code>
                  ),
                  h1: ({ children }) => (
                    <h1 className="text-2xl font-bold mt-4 mb-2">{children}</h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-xl font-semibold mt-4 mb-2">
                      {children}
                    </h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-lg font-semibold mt-4 mb-2">
                      {children}
                    </h3>
                  ),
                  a: ({ href, children }) => {
                    const normalized = normalizeToLocalFileUrl(
                      String(href || "")
                    );
                    const corrected = ensureGeneratedInUrl(normalized);
                    const proxied = `${
                      API_CONFIG.BACKEND_BASE_URL
                    }/proxy?url=${encodeURIComponent(corrected)}`;
                    return (
                      <a
                        href={proxied}
                        className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {children}
                      </a>
                    );
                  },
                  img: ({ src, alt }: any) => {
                    const normalizedSrc = normalizeToLocalFileUrl(src || "");
                    const correctedSrc = ensureGeneratedInUrl(normalizedSrc);
                    const proxiedSrc = `${
                      API_CONFIG.BACKEND_BASE_URL
                    }/proxy?url=${encodeURIComponent(correctedSrc)}`;
                    return (
                      <img
                        src={proxiedSrc}
                        alt={alt || ""}
                        className="max-w-full h-auto rounded-lg my-2"
                      />
                    );
                  },
                  ol: ({ children }) => (
                    <ol className="list-decimal pl-5 space-y-1">{children}</ol>
                  ),
                  ul: ({ children }) => (
                    <ul className="list-disc pl-5 space-y-1">{children}</ul>
                  ),
                }}
              >
                {part}
              </ReactMarkdown>
            );
          }

          return null;
        })}
      </div>
    );
  };

  const renderSectionContent = (content: string) => {
    return renderMarkdownContent(content, { withinSection: true });
  };

  // 解析 Markdown 中的文件/图片链接，返回用于卡片渲染的数据
  const parseGeneratedFiles = (
    content: string
  ): Array<{ name: string; url: string; isImage: boolean }> => {
    const result: { name: string; url: string; isImage: boolean }[] = [];
    let m: RegExpExecArray | null;
    // 1) 列表形如: - [name](url)
    const linkRe = /\- \[(.*?)\]\((.*?)\)/g;
    while ((m = linkRe.exec(content)) !== null) {
      const name = m[1];
      const url = normalizeToLocalFileUrl(m[2]);
      const isImage = /\.(png|jpg|jpeg|gif|webp|svg)(\?.*)?$/i.test(url);
      result.push({ name, url, isImage });
    }
    // 2) 图片 Markdown: ![name](url)
    const imgRe = /!\[(.*?)\]\((.*?)\)/g;
    while ((m = imgRe.exec(content)) !== null) {
      const name = m[1];
      const url = normalizeToLocalFileUrl(m[2]);
      result.push({ name, url, isImage: true });
    }
    // 3) 兜底：文中出现的裸链接
    const urlRe = /(https?:\/\/[^\s)]+)/g;
    while ((m = urlRe.exec(content)) !== null) {
      const url = normalizeToLocalFileUrl(m[1]);
      const isImage = /\.(png|jpg|jpeg|gif|webp|svg)(\?.*)?$/i.test(url);
      if (isImage)
        result.push({ name: url.split("/")?.pop() || "image", url, isImage });
    }
    // 去重同 url
    const seen = new Set<string>();
    return result.filter((f) =>
      seen.has(f.url) ? false : (seen.add(f.url), true)
    );
  };

  // 提取消息中的所有步骤
  const extractSections = (content: string, messageIndex?: number) => {
    const sectionConfigs = {
      Analyze: { icon: "🔍", color: "bg-blue-500" },
      Understand: { icon: "🧠", color: "bg-cyan-500" },
      Code: { icon: "💻", color: "bg-gray-500" },
      Execute: { icon: "⚡", color: "bg-orange-500" },
      Answer: { icon: "✅", color: "bg-green-500" },
      File: { icon: "📎", color: "bg-purple-500" }, // 添加 File 类型
    };

    const allMatches: Array<{
      type: keyof typeof sectionConfigs;
      position: number;
    }> = [];

    Object.keys(sectionConfigs).forEach((type) => {
      const regex = new RegExp(`<${type}>([\\s\\S]*?)</${type}>`, "g");
      let match;

      while ((match = regex.exec(content)) !== null) {
        allMatches.push({
          type: type as keyof typeof sectionConfigs,
          position: match.index,
        });
      }
    });

    // 按位置排序，然后生成 sectionKey（与 renderMessageWithSections 逻辑一致）
    allMatches.sort((a, b) => a.position - b.position);

    return allMatches.map((m, index) => ({
      type: m.type,
      sectionKey:
        messageIndex !== undefined
          ? `msg${messageIndex}-${m.type}-${index}` // 包含消息索引
          : `${m.type}-${index}`, // 兼容旧逻辑
      config: sectionConfigs[m.type],
    }));
  };

  // 滚动到指定步骤
  const scrollToSection = (sectionKey: string) => {
    const container = messagesContainerRef.current;
    if (!container) {
      console.warn("Container not found");
      return;
    }

    // 展开目标块（如果它是折叠的）
    setCollapsedSections((prev) => {
      const next = { ...prev };
      // 提取 baseKey（去掉 msg{index}- 前缀）
      const baseKey = sectionKey.replace(/^msg\d+-/, "");

      // 如果该块是折叠的，则展开它（同时更新两种格式的 key）
      if (prev[sectionKey] || prev[baseKey]) {
        next[sectionKey] = false;
        next[baseKey] = false;
        return next;
      }
      return prev;
    });

    // 标记为手动操作，防止自动折叠覆盖
    setManualLocks((prev) => {
      const baseKey = sectionKey.replace(/^msg\d+-/, "");
      return {
        ...prev,
        [sectionKey]: true,
        [baseKey]: true,
      };
    });

    // 使用延迟确保 DOM 已更新和展开动画完成
    setTimeout(() => {
      const element = document.querySelector(
        `[data-section-key="${sectionKey}"]`
      );

      if (!element) {
        console.warn(`Element with key ${sectionKey} not found`);
        return;
      }

      const elementRect = element.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();
      const scrollTop = container.scrollTop;

      // 计算目标滚动位置（居中显示）
      const targetScroll =
        scrollTop +
        elementRect.top -
        containerRect.top -
        containerRect.height / 2 +
        elementRect.height / 2;

      container.scrollTo({
        top: Math.max(0, targetScroll),
        behavior: "smooth",
      });

      setActiveSection(sectionKey);
    }, 150);
  };

  // 监听滚动，更新当前激活的步骤
  useEffect(() => {
    const handleScroll = () => {
      const container = messagesContainerRef.current;
      if (!container) return;

      const sections = document.querySelectorAll("[data-section-key]");
      const containerRect = container.getBoundingClientRect();
      const containerMiddle = containerRect.top + containerRect.height / 2;

      let closestSection = "";
      let closestDistance = Infinity;

      sections.forEach((section) => {
        const rect = section.getBoundingClientRect();
        const sectionMiddle = rect.top + rect.height / 2;
        const distance = Math.abs(sectionMiddle - containerMiddle);

        // 找到离容器中心最近的 section
        if (
          distance < closestDistance &&
          rect.top < containerRect.bottom &&
          rect.bottom > containerRect.top
        ) {
          closestDistance = distance;
          closestSection = section.getAttribute("data-section-key") || "";
        }
      });

      if (closestSection) {
        setActiveSection(closestSection);
      }
    };

    const container = messagesContainerRef.current;
    if (container) {
      // 初始化时也触发一次
      handleScroll();

      container.addEventListener("scroll", handleScroll);
      return () => container.removeEventListener("scroll", handleScroll);
    }
  }, [messages]);

  const renderMessageWithSections = (
    content: string,
    messageIndex?: number
  ) => {
    const sectionConfigs = {
      Analyze: {
        icon: "🔍",
        color:
          "bg-blue-50 border-blue-200 dark:bg-blue-950/30 dark:border-blue-800",
      },
      Understand: {
        icon: "🧠",
        color:
          "bg-cyan-50 border-cyan-200 dark:bg-cyan-950/30 dark:border-cyan-800",
      },
      Code: {
        icon: "💻",
        color:
          "bg-gray-50 border-gray-200 dark:bg-gray-950/30 dark:border-gray-700",
      },
      Execute: {
        icon: "⚡",
        color:
          "bg-orange-50 border-orange-200 dark:bg-orange-950/30 dark:border-orange-800",
      },
      Answer: {
        icon: "✅",
        color:
          "bg-green-50 border-green-200 dark:bg-green-950/30 dark:border-green-800",
      },
      File: {
        icon: "📎",
        color:
          "bg-purple-50 border-purple-200 dark:bg-purple-950/30 dark:border-purple-800",
      },
    };

    // 首先分割内容，找出所有标签
    const allMatches: Array<{
      type: keyof typeof sectionConfigs;
      content: string;
      position: number;
      fullMatch: string;
    }> = [];

    Object.keys(sectionConfigs).forEach((type) => {
      // 使用 [\s\S]*? 以兼容不支持 s 标志的环境
      const regex = new RegExp(`<${type}>([\\s\\S]*?)</${type}>`, "g");
      let match;

      while ((match = regex.exec(content)) !== null) {
        allMatches.push({
          type: type as keyof typeof sectionConfigs,
          content: match[1].trim(),
          position: match.index,
          fullMatch: match[0],
        });
      }
    });

    // 如果没有找到结构化标签，检查是否为任务参数JSON
    if (allMatches.length === 0) {
      const taskParamResult = isTaskParamJson(content);
      if (taskParamResult && taskParamResult.task_type) {
        const messageId = messageIndex !== undefined ? `msg-${messageIndex}` : `msg-${Date.now()}`;
        const taskType = taskParamResult.task_type;
        const cardStatus: CardStatus = confirmCardStatuses[messageId] || "pending";

        // 防重复确认机制 §10.6
        // 1. 该 task_type 已被跳过 → 直接走 chat mode（除非包含执行意图词）
        // 2. 该 task_type 在当前会话已有执行中任务 → 不弹确认
        if (cardStatus === "pending") {
          const hasRunningTask = isSOPExecuting && selectedTaskId === taskType;
          if (hasRunningTask) {
            // 执行中跳过：显示友好提示而非 raw JSON
            return (
              <div className="text-sm text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/30 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                <span className="font-medium">📋 已检测到评分卡/规则挖掘任务意图</span>
                <span className="ml-1">— 当前已有同类型任务在执行中，请等待完成后再启动新任务。</span>
              </div>
            );
          }
          if (dismissedTaskTypes.has(taskType)) {
            // 已跳过的 task_type：同样显示友好提示而非 raw JSON
            return (
              <div className="text-sm text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/30 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                已识别到任务意图，您已选择继续对话。如需启动任务，请在左侧任务面板中选择。
              </div>
            );
          }
        }

        return (
          <TaskConfirmCard
            taskType={taskType}
            extractedParams={taskParamResult.params}
            status={cardStatus}
            onConfirm={(tt, params) => {
              // 标记当前消息卡片为 confirmed
              setConfirmCardStatuses(prev => ({ ...prev, [messageId]: "confirmed" }));
              handleTaskConfirmCardConfirm(tt, params);
            }}
            onDismiss={(tt) => {
              // 标记当前消息卡片为 dismissed
              setConfirmCardStatuses(prev => ({ ...prev, [messageId]: "dismissed" }));
              handleTaskConfirmCardDismiss(tt);
            }}
          />
        );
      }
      
      return (
        <div className="markdown-content">{renderMarkdownContent(content)}</div>
      );
    }

    // 按位置排序
    allMatches.sort((a, b) => a.position - b.position);

    const parts = [];
    let lastPosition = 0;

    allMatches.forEach((match, index) => {
      // 添加标签前的普通文本
      if (match.position > lastPosition) {
        const beforeText = content.slice(lastPosition, match.position);
        if (beforeText.trim()) {
          parts.push(
            <div key={`text-${index}`} className="markdown-content mb-2">
              {renderMarkdownContent(beforeText)}
            </div>
          );
        }
      }

      // 添加结构化标签
      const config = sectionConfigs[match.type];
      const baseKey = `${match.type}-${index}`;
      const msgKey =
        messageIndex !== undefined
          ? `msg${messageIndex}-${match.type}-${index}`
          : baseKey;
      const sectionKey = msgKey;
      const isCollapsed =
        (collapsedSections as any)[msgKey] ??
        (collapsedSections as any)[baseKey] ??
        false;

      const toggleSection = () => {
        setCollapsedSections((prev) => {
          const next = { ...prev } as Record<string, boolean>;
          const current =
            (prev as any)[msgKey] ?? (prev as any)[baseKey] ?? false;
          next[msgKey] = !current;
          next[baseKey] = !current;
          return next;
        });
        setManualLocks((prev) => ({
          ...prev,
          [msgKey]: true,
          [baseKey]: true,
        }));
      };

      // 如果是 File 标签，解析其中的链接为卡片
      let sectionBody = match.content;
      let fileGallery: JSX.Element | null = null;

      // 防御性修复：如果 Code 标签内容实际是任务参数 JSON（后端 extraction/code-execution prompt 冲突遗留），
      // 则渲染为 TaskConfirmCard 而非代码块
      if (match.type === "Code") {
        const taskParamInCode = isTaskParamJson(match.content);
        if (taskParamInCode && taskParamInCode.task_type) {
          const messageId = messageIndex !== undefined ? `msg-${messageIndex}` : `msg-${Date.now()}`;
          const taskType = taskParamInCode.task_type;
          const cardStatus: CardStatus = confirmCardStatuses[messageId] || "pending";

          if (cardStatus === "pending") {
            const hasRunningTask = isSOPExecuting && selectedTaskId === taskType;
            if (hasRunningTask || dismissedTaskTypes.has(taskType)) {
              parts.push(
                <div key={sectionKey} className="markdown-content">
                  {renderMarkdownContent(content)}
                </div>
              );
              lastPosition = match.position + match.fullMatch.length;
              return;
            }
          }

          parts.push(
            <TaskConfirmCard
              key={sectionKey}
              taskType={taskType}
              extractedParams={taskParamInCode.params}
              status={cardStatus}
              onConfirm={(tt, params) => {
                setConfirmCardStatuses(prev => ({ ...prev, [messageId]: "confirmed" }));
                handleTaskConfirmCardConfirm(tt, params);
              }}
              onDismiss={(tt) => {
                setConfirmCardStatuses(prev => ({ ...prev, [messageId]: "dismissed" }));
                handleTaskConfirmCardDismiss(tt);
              }}
            />
          );
          lastPosition = match.position + match.fullMatch.length;
          return;
        }
      }

      if (match.type === "File") {
        const files = parseGeneratedFiles(match.content);
        if (files.length) {
          fileGallery = (
            <div className="mt-3">
              <div className="text-xs text-gray-500 mb-2">相关文件</div>
              <div className="grid grid-cols-2 gap-2">
                {files.map((f, i) => {
                  // 通过代理访问图片，并自动修正缺少 generated 的 URL
                  const correctedUrl = ensureGeneratedInUrl(f.url);
                  const proxiedUrl = `${
                    API_CONFIG.BACKEND_BASE_URL
                  }/proxy?url=${encodeURIComponent(correctedUrl)}`;
                  return (
                    <div
                      key={i}
                      className="border border-gray-200 dark:border-gray-700 rounded overflow-hidden bg-white dark:bg-black"
                    >
                      {f.isImage ? (
                        <a href={proxiedUrl} target="_blank" rel="noreferrer">
                          <img
                            src={proxiedUrl}
                            alt={f.name}
                            className="w-full h-28 object-contain bg-white dark:bg-black"
                          />
                        </a>
                      ) : (
                        <a
                          href={proxiedUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="block p-2 text-xs truncate hover:bg-gray-50 dark:hover:bg-gray-900"
                        >
                          {f.name}
                        </a>
                      )}
                      <div className="flex items-center justify-between px-2 py-1 border-t border-gray-200 dark:border-gray-800">
                        <div className="text-[10px] truncate max-w-[70%] text-gray-500">
                          {f.name}
                        </div>
                        <a
                          href={proxiedUrl}
                          download
                          className="text-[10px] text-blue-600 hover:underline"
                        >
                          下载
                        </a>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        }
      }

      parts.push(
        <div
          key={`section-${index}`}
          className="mb-4 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
          data-section={match.type}
          data-section-key={sectionKey}
        >
          <div className="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleSection}
                className="h-5 w-5 p-0 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                {isCollapsed ? (
                  <ChevronRight className="h-3 w-3" />
                ) : (
                  <ChevronDown className="h-3 w-3" />
                )}
              </Button>
              <span className="text-sm">{config.icon}</span>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {match.type}
              </span>
            </div>
            <div className="flex items-center gap-1">
              {match.type === "Answer" && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={async () => {
                    if (isTyping) {
                      toast({
                        description: "执行中，暂时无法导出",
                        variant: "destructive",
                      });
                      return;
                    }
                    await exportReportBackend();
                  }}
                  className="h-5 px-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                  title="后端导出 PDF/MD 到 workspace"
                >
                  <Download className="h-3 w-3" />
                </Button>
              )}
              {(match.type === "Code" ||
                match.type === "Analyze" ||
                match.type === "Understand") && (
                <>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={async () => {
                      const text =
                        match.type === "Code"
                          ? extractCode(match.content)
                          : match.content;
                      const ok = await copyToClipboard(text.trim());
                      toast({
                        description: ok ? "已复制" : "复制失败",
                        variant: ok ? undefined : "destructive",
                      });
                    }}
                    className="h-5 px-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                  >
                    <Copy className="h-3 w-3" />
                  </Button>
                  {match.type === "Code" && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        const code = extractCode(match.content);
                        setCodeEditorContent(code);
                        setSelectedCodeSection(match.content);
                        setShowCodeEditor(true);
                      }}
                      className="h-5 px-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    >
                      <Edit className="h-3 w-3" />
                    </Button>
                  )}
                </>
              )}
              {match.type === "Execute" && (
                <>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={async () => {
                      const before = content.slice(0, match.position);
                      const codeMatches = Array.from(
                        before.matchAll(/<Code>([\s\S]*?)<\/Code>/g)
                      );
                      const last = codeMatches.length
                        ? codeMatches[codeMatches.length - 1]
                        : null;
                      const codeSection = last ? last[1] : "";
                      const code = extractCode(codeSection || "");
                      if (code) {
                        const ok = await copyToClipboard(code.trim());
                        toast({
                          description: ok ? "已复制" : "复制失败",
                          variant: ok ? undefined : "destructive",
                        });
                      }
                    }}
                    className="h-5 px-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    title="复制与此 Execute 对应的代码"
                  >
                    <Copy className="h-3 w-3" />
                  </Button>
                </>
              )}
            </div>
          </div>
          {!isCollapsed && (
            <div
              className={`p-3 ${match.type === "Answer" ? "answer-body" : ""}`}
            >
              {renderSectionContent(sectionBody)}
              {fileGallery}
            </div>
          )}
        </div>
      );

      lastPosition = match.position + match.fullMatch.length;
    });

    // 添加最后剩余的文本
    if (lastPosition < content.length) {
      const afterText = content.slice(lastPosition);
      if (afterText.trim()) {
        parts.push(
          <div key="text-end" className="markdown-content mt-2">
            {renderMarkdownContent(afterText)}
          </div>
        );
      }
    }

    return <>{parts}</>;
  };

  // 根据完整内容自动折叠：除最后一个块外全部折叠
  const autoCollapseForContent = useCallback(
    (content: string) => {
      if (!autoCollapseEnabled) return;
      const sectionTypes = [
        "Analyze",
        "Understand",
        "Code",
        "Execute",
        "File",
        "Answer",
      ] as const;
      const matches: Array<{ type: string; index: number; pos: number }> = [];
      sectionTypes.forEach((t) => {
        const re = new RegExp(`<${t}>([\\s\\S]*?)</${t}>`, "g");
        let m: RegExpExecArray | null;
        let local = 0;
        while ((m = re.exec(content)) !== null) {
          matches.push({ type: t, index: local++, pos: m.index });
        }
      });
      if (matches.length === 0) return;
      matches.sort((a, b) => a.pos - b.pos);
      const next: Record<string, boolean> = {};
      matches.forEach((m, i) => {
        const key = `${m.type}-${i}`;
        next[key] = i !== matches.length - 1; // 最后一个不折叠
      });
      setCollapsedSections((prev) => {
        const merged: Record<string, boolean> = { ...prev };
        // 只在未手动锁定的 key 上更新，保留用户手动状态
        for (const key in next) {
          if (!manualLocks[key]) merged[key] = next[key];
        }
        return merged;
      });
    },
    [autoCollapseEnabled, manualLocks]
  );

  // P2-8: 处理确认卡片 —— 用户点击"使用此任务"
  const handleTaskConfirmCardConfirm = useCallback((taskType: string, extractedParams?: Record<string, any>) => {
    // 如果当前有任务在执行中，提示用户
    if (isSOPExecuting) {
      toast({
        description: `检测到您本会话已有一个任务正在执行，新任务配置将在当前任务完成后可用。`,
      });
    }

    // 暂存 LLM 提取的参数，用于注入 ConfigPanel
    if (extractedParams && Object.keys(extractedParams).length > 0) {
      setPendingInitialParams(extractedParams);
    }

    // 拉起 ConfigPanel
    setSelectedTaskId(taskType);
    setShowConfigPanel(true);
    setShowResults(false);
    setCurrentExecutionId(null);
    setCompletedExecutionId(null);
    setSopExecutionStatus(null);
    setHistoryTaskInteractionMode(null);
    setHistoryTaskRecordId(null);
    setSelectedStageId(null);
    setSelectedStageData(null);
    setRightPanelMode("code");
    setIsUserManualSelection(false);
    lastCompletedStageIdRef.current = null;
    setAiAnalysisResult(null);
    setShowAIAnalysisPanel(false);
  }, [isSOPExecuting, toast]);

  // P2-8: 处理确认卡片 —— 用户点击"继续对话"
  const handleTaskConfirmCardDismiss = useCallback((taskType: string) => {
    // 将该 taskType 记入会话级记忆，同一会话不再弹出
    setDismissedTaskTypes(prev => new Set([...prev, taskType]));
  }, []);

  const handleSendMessage = async () => {
    if (!inputValue.trim() && attachments.length === 0 && fileReferences.length === 0) return;

    // 将文件引用格式化并附加到消息内容
    const fileRefText = formatFileReferencesForMessage(fileReferences);
    const fullContent = inputValue + fileRefText;

    const newMessage: Message = {
      id: Date.now().toString(),
      content: fullContent,
      sender: "user",
      timestamp: new Date(),
      attachments: attachments.length > 0 ? [...attachments] : undefined,
    };

    setMessages((prev) => [...prev, newMessage]);
    setInputValue("");
    setAttachments([]);
    setFileReferences([]); // 清空文件引用
    setIsTyping(true);

    try {
      const response = await authFetch(getApiUrl(API_URLS.CHAT_COMPLETIONS), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          // 使用config_前缀格式，让Chat API通过LLM Manager渠道处理
          // 这样可以获得负载均衡、代码执行、任务感知等全部功能
          model: selectedConfig?.id ? `config_${selectedConfig.id}` : "deepseek-chat",
          messages: [
            ...messages
              .filter((m) => !m.localOnly)
              .map((msg) => ({
                role: msg.sender === "user" ? "user" : "assistant",
                content: msg.content,
              })),
            {
              role: "user",
              content: fullContent,
            },
          ],
          stream: false,
          session_id: sessionId,
          // 传递模型配置参数
          ...(selectedConfig && {
            temperature: selectedConfig.temperature,
            max_tokens: selectedConfig.max_tokens,
            top_p: selectedConfig.top_p,
            // 传递系统提示词（如果配置了）
            system_prompt: selectedConfig.system_prompt || undefined,
          }),
          // Chat API特有参数
          enable_code_execution: true,
          include_task_list: true,
          // 传递当前选中的SOP任务类型，用于任务感知提示词注入
          task_type: selectedTaskId || undefined,
        }),
      });

      const contentType = response.headers.get("content-type") || "";

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // 分两种返回：
      // 1) application/json → 一次性JSON
      // 2) 其他（如 text/plain 流式）→ 多段JSON对象拼接
      if (contentType.includes("application/json")) {
        const data = await response.json();
        const content = data?.choices?.[0]?.message?.content || "";
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            sender: "ai",
            content,
            timestamp: new Date(),
          },
        ]);
        autoCollapseForContent(content);
        // 若包含 <File> 标签，立即刷新工作区
        if (content.includes("<File>")) {
          await loadWorkspaceTree();
          await loadWorkspaceFiles();
        }
        setIsTyping(false); // 设置为 false 会自动触发滚动
        return;
      }

      // 流式读取（后端返回 text/plain 且逐条输出 JSON 对象）
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) {
        // 没有可读流，直接结束加载动画
        setIsTyping(false);
        return;
      }

      // 先插入一个空的 AI 消息，后续流式更新它的 content
      const aiMsgId = `${Date.now()}-${Math.random()}`;
      setMessages((prev) => [
        ...prev,
        {
          id: aiMsgId,
          sender: "ai",
          content: "",
          timestamp: new Date(),
        },
      ]);

      const updateAiMessage = (text: string) => {
        setMessages((prev) => {
          const next = [...prev];
          const idx = next.findIndex((m) => m.id === aiMsgId);
          if (idx >= 0) {
            next[idx] = { ...next[idx], content: text };
          }
          return next;
        });
        // 在流式过程中也做自动折叠：只保留最后一个展开
        autoCollapseForContent(text);
        // 若检测到 <File> 标签，节流触发一次工作区刷新
        if (text.includes("<File>")) {
          if (fileRefreshTimerRef.current) {
            window.clearTimeout(fileRefreshTimerRef.current);
          }
          fileRefreshTimerRef.current = window.setTimeout(async () => {
            await loadWorkspaceTree();
            await loadWorkspaceFiles();
            fileRefreshTimerRef.current = null;
          }, 300);
        }
        // 不需要在这里滚动，isTyping 期间的 interval 会持续滚动
      };

      let buffer = "";
      let lastRendered = "";

      // 从缓冲区提取完整 JSON 对象（按花括号配对，忽略字符串中的括号）
      const extractJsonObjects = (
        text: string
      ): { objects: any[]; rest: string } => {
        const objects: any[] = [];
        let i = 0;
        while (i < text.length) {
          while (i < text.length && text[i] !== "{") i++;
          if (i >= text.length) break;
          let depth = 0,
            inStr = false,
            esc = false;
          let j = i;
          for (; j < text.length; j++) {
            const ch = text[j];
            if (inStr) {
              if (esc) {
                esc = false;
                continue;
              }
              if (ch === "\\") {
                esc = true;
                continue;
              }
              if (ch === '"') {
                inStr = false;
              }
              continue;
            }
            if (ch === '"') {
              inStr = true;
              continue;
            }
            if (ch === "{") {
              depth++;
              continue;
            }
            if (ch === "}") {
              depth--;
              if (depth === 0) {
                j++;
                break;
              }
            }
          }
          if (depth === 0 && j <= text.length) {
            const seg = text.slice(i, j);
            try {
              const obj = JSON.parse(seg);
              objects.push(obj);
              i = j;
              continue;
            } catch {
              break;
            }
          } else {
            break;
          }
        }
        return { objects, rest: text.slice(i) };
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const { objects, rest } = extractJsonObjects(buffer);
        buffer = rest;
        for (const obj of objects) {
          const extracted = obj?.choices?.[0]?.message?.content as
            | string
            | undefined;
          if (typeof extracted === "string" && extracted !== lastRendered) {
            lastRendered = extracted;
            updateAiMessage(extracted);
            if (extracted.includes("</Answer>")) {
              setIsTyping(false);
              autoCollapseForContent(extracted);
            }
          }
        }
      }

      // 流结束后忽略残余不完整 JSON

      await loadWorkspaceFiles();
      setIsTyping(false); // 设置为 false 会自动触发平滑滚动
    } catch (error) {
      console.error("Error sending message:", error);
      setIsTyping(false); // 设置为 false 会自动触发平滑滚动
    }
  };

  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const files = event.target.files;
    if (!files) return;
    await uploadToDir("", files);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // SOP任务选择处理
  // Phase 10 修复：点击TaskType时，完全关闭当前任务的显示，确保配置面板和任务进度/结果互斥
  const handleTaskSelect = (taskId: string) => {
    // 如果当前有任务在执行中，不允许切换任务类型
    if (isSOPExecuting) {
      return;
    }
    
    // 重置所有任务相关状态，确保配置面板与任务进度/结果互斥
    setSelectedTaskId(taskId);
    setShowConfigPanel(true);
    setShowResults(false);
    setCurrentExecutionId(null);
    setCompletedExecutionId(null);
    setSopExecutionStatus(null);
    setHistoryTaskInteractionMode(null);
    setHistoryTaskRecordId(null);
    setSelectedStageId(null);
    setSelectedStageData(null);
    setRightPanelMode("code");
    setIsUserManualSelection(false);
    // Phase 25: 重置lastCompletedStageIdRef，确保新任务能正确检测首个完成阶段
    lastCompletedStageIdRef.current = null;
    // 重置AI分析状态
    setAiAnalysisResult(null);
    setShowAIAnalysisPanel(false);
  };

  // SOP任务执行处理
  const handleSOPExecute = async (params: Record<string, any>, filePath: string) => {
    if (!selectedTaskId || !sessionId) return;

    try {
      setIsSOPExecuting(true);
      setShowResults(false);

      // 从 ModelSelector 获取选中的模型配置
      const model = selectedConfig?.models?.split(",")[0]?.trim() || "deepseek-chat";
      const apiBase = "http://localhost:8200/v1";
      const systemPrompt = selectedConfig?.system_prompt || undefined;
      
      console.log(`[SOP Execute] Using model: ${model}, apiBase: ${apiBase}, hasSystemPrompt: ${!!systemPrompt}`);

      // 传递模式参数和模型配置到后端
      const response = await sopService.executeTask(
        selectedTaskId,
        sessionId,
        filePath,
        params,
        interactionMode,
        model,
        apiBase,
        systemPrompt
      );

      setCurrentExecutionId(response.execution_id);
      setShowConfigPanel(false);

      toast({
        description: `任务已启动 (Pipeline/${interactionMode}): ${response.execution_id}`,
      });
    } catch (err) {
      console.error("Failed to execute SOP task:", err);
      toast({
        description: err instanceof Error ? err.message : "任务执行失败",
        variant: "destructive",
      });
      setIsSOPExecuting(false);
    }
  };

  // SOP任务完成处理
  const handleSOPComplete = (status: ExecutionStatus) => {
    setIsSOPExecuting(false);
    // 任务结束后清除executionId，停止轮询
    setCurrentExecutionId(null);
    // 保留sopExecutionStatus以便查看阶段卡片
    
    // 任务结束（完成/失败/停止）时自动刷新历史记录列表
    historyCompactRef.current?.refresh();
    setSopExecutionStatus(status);
    // Phase 10 修复：任务完成后不再清除historyTaskInteractionMode和historyTaskRecordId
    // 这样可以保持专家模式任务完成后仍然显示专家模式的结果页面，而不是切换到自动模式
    // 同时保留recordId以便AI分析缓存能够正确加载
    // 注意：这些状态会在handleBackToTaskList时清除
    
    // Bug修复：任务完成后锁定交互模式，防止用户切换导致AI评估被重新触发
    // 只有当historyTaskInteractionMode为null时才设置（即新任务，非历史任务恢复）
    if (!historyTaskInteractionMode) {
      setHistoryTaskInteractionMode(interactionMode);
    }
    
    if (status.status === "completed") {
      setCompletedExecutionId(status.execution_id);
      // 自动显示结果面板
      setShowResults(true);
      // Phase 10 修复：专家模式任务完成后默认显示阶段详情（因为各阶段已包含AI分析）
      // 自动模式任务完成后默认显示结果视图
      // 使用 ModeContext 提供的 isExpertModeTask，无需重复判断
      setResultViewMode(isExpertModeTask ? "stages" : "results");
      
      // Phase 20: 任务完成时获取执行结果（用于整体分析，自动模式和专家模式统一）
      // Phase 23: 后端 API 需要 stages 数据获取样本特征等信息
      sopService.getExecutionResult(status.execution_id)
        .then(result => {
          // 从 status.stages 提取各阶段的 output_preview
          const stagesWithOutputPreview: Record<string, any> = {};
          if (status.stages) {
            Object.entries(status.stages).forEach(([stageId, stageData]) => {
              stagesWithOutputPreview[stageId] = {
                output_preview: (stageData as any).output_preview || {}
              };
            });
          }
          // 合并 outputs 和 stages
          setTaskExecutionResult({
            ...result,
            stages: stagesWithOutputPreview
          });
        })
        .catch(err => {
          console.warn("[Phase 20] Failed to load task result:", err);
        });
      
      toast({
        description: "任务执行完成，可切换查看\"任务结果\"或\"阶段详情\"",
      });
    } else if (status.status === "failed") {
      // 失败时也显示面板，让用户可以查看阶段详情
      setShowResults(true);
      setResultViewMode("stages");
      toast({
        description: `任务执行失败: ${status.message}`,
        variant: "destructive",
      });
    } else if (status.status === "cancelled" || status.status === "stopped") {
      // 取消/停止时也显示面板
      setShowResults(true);
      setResultViewMode("stages");
      toast({
        description: "任务已停止",
      });
    }
  };

  // 关闭配置面板
  const handleCloseConfigPanel = () => {
    setShowConfigPanel(false);
  };

  // 关闭进度显示
  // Phase 22: 补充重置阶段选择状态，确保右侧面板也关闭
  const handleCloseProgress = () => {
    setCurrentExecutionId(null);
    setIsSOPExecuting(false);
    setSelectedStageId(null);
    setSelectedStageData(null);
    setRightPanelMode("code");
    setIsUserManualSelection(false);
  };

  // 暂停任务执行
  const handlePauseExecution = async () => {
    if (!currentExecutionId) return;
    
    try {
      await sopService.pauseExecution(currentExecutionId);
      toast({
        description: "暂停请求已发送，任务将在当前阶段完成后暂停",
      });
    } catch (err) {
      console.error("Failed to pause execution:", err);
      toast({
        description: err instanceof Error ? err.message : "暂停任务失败",
        variant: "destructive",
      });
    }
  };

  // 恢复任务执行
  const handleResumeExecution = async () => {
    if (!currentExecutionId) return;
    
    try {
      await sopService.resumeExecution(currentExecutionId);
      
      // 重置手动选择标记，恢复自动跟踪新阶段
      // 这样当下一个阶段开始执行时，页面会自动切换到该阶段
      setIsUserManualSelection(false);
      
      toast({
        description: "恢复请求已发送，任务将继续执行",
      });
      
      // 重启 TaskProgress 轮询（paused 稳定后已停止，需要通过 pollTrigger 重启）
      // 延迟 300ms：给 Pipeline 线程时间从 _check_control 的阻塞中恢复并更新 status 为 RUNNING
      // 否则 TaskProgress 可能拉到旧的 paused 状态，连续 2 次后又停止轮询
      setTimeout(() => restartPolling(), 300);
    } catch (err) {
      console.error("Failed to resume execution:", err);
      toast({
        description: err instanceof Error ? err.message : "恢复任务失败",
        variant: "destructive",
      });
    }
  };

  // 停止任务执行
  const handleStopExecution = async () => {
    if (!currentExecutionId) return;
    
    try {
      await sopService.stopExecution(currentExecutionId);
      toast({
        description: "停止请求已发送，任务将在当前阶段完成后停止",
      });
    } catch (err) {
      console.error("Failed to stop execution:", err);
      toast({
        description: err instanceof Error ? err.message : "停止任务失败",
        variant: "destructive",
      });
    }
  };

  // 跳过阶段（专家模式下）
  const handleSkipStage = async (stageId: string) => {
    if (!currentExecutionId) return;
    
    try {
      await sopService.skipExpertStage(currentExecutionId, stageId, "用户手动跳过");
      toast({
        description: `已跳过阶段: ${stageId}`,
      });
      // 立即刷新状态
      const updatedStatus = await sopService.getExecutionStatus(currentExecutionId);
      if (updatedStatus) {
        setSopExecutionStatus(updatedStatus);
      }
      // 重启轮询（跳过后后端状态可能变化，需要 TaskProgress 继续追踪）
      restartPolling();
    } catch (err) {
      console.error("Failed to skip stage:", err);
      toast({
        description: err instanceof Error ? err.message : "跳过阶段失败",
        variant: "destructive",
      });
    }
  };

  // 查看任务历史详情
  const handleViewTaskDetail = async (recordId: string) => {
    try {
      // 切换任务前先清理之前的执行状态，防止轮询覆盖新任务状态
      setCurrentExecutionId(null);
      setIsSOPExecuting(false);
      // 🔧 修复：切换任务前先清除completedExecutionId，防止旧ID触发组件加载
      // 这会让结果组件先进入loading状态，避免显示旧数据
      setCompletedExecutionId(null);
      // 关闭配置面板，确保与历史任务详情互斥
      setShowConfigPanel(false);
      // Phase 16: 切换任务时重置阶段选择状态，使右侧面板恢复空白
      // 这确保切换到新任务后，用户需要手动选择阶段才能查看阶段结果
      setSelectedStageId(null);
      setSelectedStageData(null);
      setRightPanelMode("code");
      setIsUserManualSelection(false);
      
      const detail = await sopService.getTaskHistoryDetail(recordId);
      // 🔧 始终使用 rec:${recordId} 格式，确保 ScorecardResults 进入场景1（直接获取stages）
      // 避免使用 execution_id 导致的场景2（需要依赖 record_id 二次查询）
      const idToUse = `rec:${recordId}`;
      
      // 根据历史任务类型设置selectedTaskId，确保显示正确的结果组件
      setSelectedTaskId(detail.task_type);
      
      // 如果历史记录包含阶段信息，构造ExecutionStatus以便显示阶段卡片
      if (detail.stages && Object.keys(detail.stages).length > 0) {
        // 正确映射状态：保留paused/stopped等中间状态
        const validStatuses = ['completed', 'failed', 'paused', 'stopped', 'running', 'pending'];
        const mappedStatus = validStatuses.includes(detail.status) ? detail.status : 'failed';
        
        // 处理stages：确保execution_time_ms存在（兼容旧数据）
        const processedStages: Record<string, StageProgress> = {};
        
        Object.entries(detail.stages).forEach(([stageId, stageData]: [string, any]) => {
          let executionTimeMs = stageData.execution_time_ms;
          
          // 如果没有execution_time_ms，尝试从started_at和completed_at计算（兼容旧数据）
          if (executionTimeMs === undefined && stageData.started_at && stageData.completed_at) {
            const startedAt = new Date(stageData.started_at).getTime();
            const completedAt = new Date(stageData.completed_at).getTime();
            executionTimeMs = completedAt - startedAt;
          }
          
          processedStages[stageId] = {
            ...stageData,
            execution_time_ms: executionTimeMs,
          };
        });
        
        const historicalStatus: ExecutionStatus = {
          execution_id: idToUse,
          task_id: detail.task_type,
          status: mappedStatus as ExecutionStatus['status'],
          current_stage: detail.current_stage || '',
          overall_progress: detail.progress || (mappedStatus === 'completed' ? 100 : 0),
          message: detail.message || (mappedStatus === 'paused' ? '任务已暂停' : '任务已完成'),
          started_at: detail.started_at,
          completed_at: detail.completed_at,
          stages: processedStages,
          // Phase 10 修复：添加record_id以便AI分析缓存能够正确加载
          record_id: recordId,
          // 从inputs_summary中获取file_path，用于参数编辑时加载正确的数据列
          file_path: detail.inputs_summary?.file_path
        };
        setSopExecutionStatus(historicalStatus);
        
        // 如果是暂停状态，设置currentExecutionId和isSOPExecuting以启动轮询
        if (mappedStatus === 'paused' && detail.execution_id) {
          setCurrentExecutionId(detail.execution_id);
          setIsSOPExecuting(true);  // 关键：启动轮询，以便恢复后能获取状态更新
        }
      }
      
      // 保存历史任务的执行模式（用于判断AI分析按钮是否禁用）
      setHistoryTaskInteractionMode(detail.interaction_mode);
      // 保存历史任务的记录ID（用于 AI 分析持久化，Phase 7）
      setHistoryTaskRecordId(recordId);
      
      // 重置 AI 分析状态，避免显示上一个任务的结果
      setAiAnalysisResult(null);
      
      // Phase 20: 加载任务结果（用于整体分析，自动模式和专家模式统一）
      // Phase 23: 后端 API 需要 stages 数据获取样本特征等信息
      if (detail.status === "completed") {
        try {
          const historyResult = await sopService.getTaskHistoryResult(recordId);
          if (historyResult.result) {
            // 从 detail.stages 提取各阶段的 output_preview
            const stagesWithOutputPreview: Record<string, any> = {};
            if (detail.stages) {
              Object.entries(detail.stages).forEach(([stageId, stageData]) => {
                stagesWithOutputPreview[stageId] = {
                  output_preview: (stageData as any).output_preview || {}
                };
              });
            }
            // 合并 outputs 和 stages
            setTaskExecutionResult({ 
              outputs: historyResult.result,
              stages: stagesWithOutputPreview
            });
          }
        } catch (err) {
          console.warn("[Phase 20] Failed to load history task result:", err);
          // 即使加载结果失败，也设置 stages 数据，这样整体分析至少能获取阶段信息
          const stagesWithOutputPreview: Record<string, any> = {};
          if (detail.stages) {
            Object.entries(detail.stages).forEach(([stageId, stageData]) => {
              stagesWithOutputPreview[stageId] = {
                output_preview: (stageData as any).output_preview || {}
              };
            });
          }
          if (Object.keys(stagesWithOutputPreview).length > 0) {
            setTaskExecutionResult({ 
              outputs: {},  // 空 outputs，但有 stages
              stages: stagesWithOutputPreview
            });
          }
        }
      } else {
        setTaskExecutionResult(null);
      }
      
      // 加载已保存的任务级 AI 分析结果（自动模式）
      if (detail.interaction_mode !== "expert") {
        try {
          const analysisResponse = await authFetch(getApiUrl(`/sop/history/${recordId}/stages/_task_analysis/analysis`));
          if (analysisResponse.ok) {
            const analysisData = await analysisResponse.json();
            // API 返回结构: { record_id, stage_id, analysis: { analysis_text, model_used } | null }
            if (analysisData.analysis?.analysis_text) {
              setAiAnalysisResult(analysisData.analysis.analysis_text);
            }
          }
        } catch {
          // 静默失败，可能没有保存过分析结果
        }
      }
      
      setCompletedExecutionId(idToUse);
      setShowResults(true);
      // 暂停状态的任务默认显示阶段详情视图（因为没有完整结果）
      setResultViewMode(detail.status === 'paused' ? "stages" : "results");
      setShowTaskHistory(false);
      toast({
        description: `加载任务记录: ${detail.task_type}`,
      });
    } catch (err) {
      console.error("Failed to load task detail:", err);
      toast({
        description: err instanceof Error ? err.message : "加载任务详情失败",
        variant: "destructive",
      });
    }
  };

  // 返回任务列表（完全重置任务状态）
  const handleBackToTaskList = () => {
    setShowResults(false);
    setCompletedExecutionId(null);
    setSopExecutionStatus(null);
    setCurrentExecutionId(null);
    setResultViewMode("results");
    setSelectedTaskId(null);  // 重置任务选择
    setShowConfigPanel(false);  // 关闭配置面板
    setSelectedStageId(null);  // 重置阶段选择
    setSelectedStageData(null);
    setRightPanelMode("code");  // 重置右侧面板模式
    setIsUserManualSelection(false);  // 重置手动选择标记
    // Phase 25: 重置lastCompletedStageIdRef
    lastCompletedStageIdRef.current = null;
    setIsSOPExecuting(false);  // 重置执行状态，解除任务列表禁用
    setHistoryTaskInteractionMode(null); // 清除历史任务执行模式
    setHistoryTaskRecordId(null); // 清除历史任务记录ID（Phase 7）
    setTaskExecutionResult(null); // Phase 20: 清除任务结果
    // 重置AI分析状态
    setAiAnalysisResult(null);
    setShowAIAnalysisPanel(false);
  };

  // AI分析评估：调用LLM对任务结果进行分析
  // 自动模式下，点击按钮后会自动选中最后一个阶段，并在右侧面板展示分析结果
  // 统一使用 taskExecutionResult（任务完成时已设置，包含 outputs + stages）
  const handleAIAnalysis = async () => {
    if (!completedExecutionId || isAIAnalyzing) {
      return;
    }
    
    // 如果 taskExecutionResult 为空，尝试重新获取
    let resultToUse = taskExecutionResult;
    if (!resultToUse) {
      try {
        const result = await sopService.getExecutionResult(completedExecutionId);
        // 从 sopExecutionStatus.stages 提取各阶段的 output_preview
        const stagesWithOutputPreview: Record<string, any> = {};
        if (sopExecutionStatus?.stages) {
          Object.entries(sopExecutionStatus.stages).forEach(([stageId, stageData]) => {
            stagesWithOutputPreview[stageId] = {
              output_preview: (stageData as any).output_preview || {}
            };
          });
        }
        resultToUse = {
          ...result,
          stages: stagesWithOutputPreview
        };
        setTaskExecutionResult(resultToUse);
      } catch (err) {
        console.error("[AI Analysis] Failed to fetch taskExecutionResult:", err);
        toast({
          description: "无法获取任务结果数据",
          variant: "destructive",
        });
        return;
      }
    }
    
    // 自动选中最后一个阶段（report_generation），切换到右侧预览面板
    // 注意：stages 是 Record<string, StageProgress>，需要转换为数组
    if (sopExecutionStatus?.stages) {
      const stagesArray = Object.values(sopExecutionStatus.stages);
      const lastStage = stagesArray[stagesArray.length - 1];
      if (lastStage) {
        setSelectedStageId(lastStage.stage_id);
        setSelectedStageData(lastStage);
        setRightPanelMode("preview");
        setIsUserManualSelection(true);
        // 切换到阶段详情视图，以便用户能看到阶段卡片和右侧预览
        setResultViewMode("stages");
      }
    }
    
    setIsAIAnalyzing(true);
    setAiAnalysisResult(null);
    
    try {
      // Phase 23: 统一使用后端 API 获取 prompt（与专家模式架构一致）
      // 调用后端 /v1/chat/analysis/prompt 接口获取分析提示词
      const promptResponse = await authFetch(getApiUrl("/v1/chat/analysis/prompt"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          analysis_type: "overall",
          task_type: selectedTaskId,
          result: resultToUse,
        }),
      });
      
      if (!promptResponse.ok) {
        throw new Error(`获取分析提示词失败: ${promptResponse.status}`);
      }
      
      const promptData = await promptResponse.json();
      if (!promptData.success || !promptData.prompt) {
        throw new Error(promptData.error || "获取分析提示词失败");
      }
      
      const analysisPrompt = promptData.prompt;
      
      // 调用Chat API进行流式分析
      // 使用 config_${id} 格式，通过 LLM Manager 渠道处理（与专家模式一致）
      const response = await authFetch(getApiUrl("/v1/chat/completions"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: selectedConfig?.id ? `config_${selectedConfig.id}` : "deepseek-chat",
          messages: [
            // Phase 23: 后端 API 返回的 prompt 已包含完整角色设定和输出要求，无需额外system prompt
            {
              role: "user",
              content: analysisPrompt
            }
          ],
          stream: true,
          // AI分析评估专用参数（硬编码）
          // 与任务执行配置解耦，避免"参数推断"预设的frequency_penalty=0导致重复输出
          temperature: 0.3,        // 降低随机性，提高输出稳定性
          frequency_penalty: 0.3,  // 温和抑制重复（1.0过高会破坏语义）
          presence_penalty: 0.2,   // 轻微鼓励多样性（0.8过高会导致语句断裂）
          max_tokens: 4096,
          // 禁用任务感知和代码执行，避免触发参数推断模式（与专家模式一致）
          include_task_list: false,
          enable_code_execution: false,
        })
      });
      
      if (!response.ok) {
        throw new Error(`AI分析请求失败: ${response.status}`);
      }
      
      // 检测响应类型：流式(SSE)或非流式(JSON)
      const contentType = response.headers.get('content-type') || '';
      const isStreamResponse = contentType.includes('text/event-stream');
      
      let fullContent = "";
      
      if (isStreamResponse) {
        // 处理流式响应 (SSE)
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        
        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";
            
            for (const line of lines) {
              if (line.startsWith("data: ")) {
                const data = line.slice(6);
                if (data === "[DONE]") continue;
                
                try {
                  const parsed = JSON.parse(data);
                  const content = parsed.choices?.[0]?.delta?.content || "";
                  if (content) {
                    fullContent += content;
                    setAiAnalysisResult(fullContent);
                  }
                } catch {
                  // 忽略解析错误
                }
              }
            }
          }
        }
      } else {
        // 处理非流式响应 (JSON)
        const responseData = await response.json();
        
        // 提取内容（OpenAI格式）
        if (responseData.choices && responseData.choices[0]) {
          const choice = responseData.choices[0];
          // 非流式响应使用 message.content 而不是 delta.content
          fullContent = choice.message?.content || choice.text || "";
          setAiAnalysisResult(fullContent);
        } else {
          throw new Error("响应格式不正确");
        }
      }
      
      // 保存结果到后端 API（流式和非流式都执行）
      // 使用特殊的 stage_id "_task_analysis" 表示任务级别的 AI 分析
      const recordId = historyTaskRecordId || sopExecutionStatus?.record_id;
      console.log(`[AI Analysis Save] recordId=${recordId}, historyTaskRecordId=${historyTaskRecordId}, sopExecutionStatus.record_id=${sopExecutionStatus?.record_id}`);
      if (recordId && fullContent) {
        try {
          const saveResponse = await authFetch(getApiUrl(`/sop/history/${recordId}/stages/_task_analysis/analysis`), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              analysis_text: fullContent,
              model_used: selectedConfig?.id ? `config_${selectedConfig.id}` : "deepseek-chat"
            })
          });
          if (saveResponse.ok) {
            console.log(`[AI Analysis Save] Successfully saved to record=${recordId}`);
          } else {
            console.error(`[AI Analysis Save] Failed with status=${saveResponse.status}: ${await saveResponse.text()}`);
          }
        } catch (saveError) {
          console.error(`[AI Analysis Save] Network error:`, saveError);
        }
      } else {
        console.warn(`[AI Analysis Save] Skipped: recordId=${recordId}, fullContent.length=${fullContent?.length || 0}`);
      }
      
    } catch (error) {
      console.error("AI分析失败:", error);
      setAiAnalysisResult(`❌ 分析失败: ${error instanceof Error ? error.message : "未知错误"}\n\n请稍后重试，或在对话中直接询问AI进行分析。`);
    } finally {
      setIsAIAnalyzing(false);
    }
  };
  
  // Phase 3: 处理阶段卡片点击 - 显示输出预览
  // 用户手动点击时设置标记，防止自动跟踪覆盖用户选择
  const handleStageClick = (stageId: string, stage: StageProgress) => {
    setSelectedStageId(stageId);
    setSelectedStageData(stage);
    setIsUserManualSelection(true);  // 标记为用户手动选择
    
    // 如果阶段有输出预览数据，切换到预览模式
    if (stage.output_preview) {
      setRightPanelMode("preview");
    } else {
      // 没有预览数据时也切换到预览模式，显示"暂无预览数据"
      setRightPanelMode("preview");
    }
  };

  // Phase 3: 处理SOP执行状态更新（使用useCallback避免重复触发轮询）
  // 自动跟踪当前执行阶段：阶段开始时显示代码，完成时切换到结果
  // 但尊重用户手动选择：如果用户手动点击了某个阶段，不自动切换
  const handleSOPStatusUpdate = useCallback((status: ExecutionStatus) => {
    console.log("[StatusUpdate] Received status:", status.status, "stages:", Object.keys(status.stages));
    
    // 使用ref获取最新值，避免闭包问题
    const currentSelectedStageId = selectedStageIdRef.current;
    const currentIsUserManualSelection = isUserManualSelectionRef.current;
    
    // 详细记录每个阶段的状态
    Object.entries(status.stages).forEach(([stageId, stage]) => {
      console.log(`[StatusUpdate] Stage ${stageId}: ${stage.status} (${stage.progress}%)`);
    });
    
    setSopExecutionStatus(status);
    
    // 找到当前正在执行的阶段（状态为running）
    const runningStageEntry = Object.entries(status.stages).find(
      ([_, stage]) => stage.status === "running"
    );
    
    // 获取阶段执行顺序（优先使用API返回的stage_order）
    const taskStageOrder = getStageOrder(status);
    console.log("[StatusUpdate] taskStageOrder:", taskStageOrder, "from API:", status.stage_order);
    
    // 找到最近完成的阶段（按阶段顺序排序）
    const completedStages = Object.entries(status.stages)
      .filter(([_, stage]) => stage.status === "completed")
      .sort(([idA], [idB]) => {
        const indexA = taskStageOrder.indexOf(idA);
        const indexB = taskStageOrder.indexOf(idB);
        // 如果阶段ID不在预定义顺序中，放到最后
        return (indexA === -1 ? 999 : indexA) - (indexB === -1 ? 999 : indexB);
      });
    
    console.log("[StatusUpdate] Running stage:", runningStageEntry?.[0], "Completed stages (sorted):", completedStages.map(([id]) => id), "currentSelectedStageId:", currentSelectedStageId);
    console.log("[StatusUpdate] Last stage in order:", taskStageOrder[taskStageOrder.length - 1], "Last completed:", completedStages[completedStages.length - 1]?.[0]);
    
    // 自动跟踪：当有阶段开始执行时，自动选中该阶段并显示代码
    // 但如果用户手动选择了其他阶段，则不自动切换
    if (runningStageEntry && !currentIsUserManualSelection) {
      const [runningStageId, runningStage] = runningStageEntry;
      console.log("[StatusUpdate] Auto-selecting running stage:", runningStageId);
      
      // 如果当前没有选中阶段，或选中的不是正在执行的阶段，自动切换
      if (currentSelectedStageId !== runningStageId) {
        setSelectedStageId(runningStageId);
        setSelectedStageData(runningStage);
        setRightPanelMode("preview");  // 切换到预览模式
        // StageOutputPreview 会根据阶段状态自动显示代码或结果
      } else {
        // 更新当前选中阶段的数据
        setSelectedStageData(runningStage);
      }
    }
    
    // 专家模式暂停时或任务完成时：自动选中最近完成的阶段并显示结果
    // 当任务暂停/完成且没有正在运行的阶段时，找到最后一个完成的阶段
    // Phase 24: 修复阶段切换逻辑 - 当有新阶段完成时，即使用户之前手动选择过，也应自动切换
    // Phase 25: 修复暂停时用户查看历史阶段被强制切换的问题
    //          - 使用 lastCompletedStageIdRef 记录上次轮询的最后完成阶段
    //          - 只有"真正的新阶段完成"时才自动切换，暂停状态稳定时尊重用户选择
    if ((status.status === "paused" || status.status === "completed") && !runningStageEntry) {
      console.log("[StatusUpdate] Task paused/completed, checking for auto-switch to last completed stage");
      
      if (completedStages.length > 0) {
        // 选择最后一个完成的阶段
        const [lastCompletedId, lastCompletedStage] = completedStages[completedStages.length - 1];
        console.log("[StatusUpdate] Last completed stage:", lastCompletedId, "current selected:", currentSelectedStageId, "manual selection:", currentIsUserManualSelection);
        
        // Phase 25: 检测是否有"真正的新阶段完成"（与上次轮询比较）
        const previousLastCompleted = lastCompletedStageIdRef.current;
        const hasRealNewCompletedStage = previousLastCompleted !== null && previousLastCompleted !== lastCompletedId;
        
        // 更新记录
        lastCompletedStageIdRef.current = lastCompletedId;
        
        console.log("[StatusUpdate] Previous last completed:", previousLastCompleted, "hasRealNewCompletedStage:", hasRealNewCompletedStage);
        
        // 判断是否需要自动切换：
        // 1. 首次进入paused状态（previousLastCompleted为null或当前未选中）
        // 2. 真正有新阶段完成（previousLastCompleted !== lastCompletedId）
        const shouldAutoSwitch = 
          (previousLastCompleted === null && !currentSelectedStageId) ||  // 首次
          hasRealNewCompletedStage;  // 真正的新阶段
        
        if (shouldAutoSwitch) {
          console.log("[StatusUpdate] Auto-switching to new completed stage:", lastCompletedId);
          setSelectedStageId(lastCompletedId);
          setSelectedStageData(lastCompletedStage);
          setRightPanelMode("preview");
          // 重置手动选择标记，因为我们刚自动切换到了新阶段
          setIsUserManualSelection(false);
        } else if (!currentIsUserManualSelection && currentSelectedStageId === lastCompletedId) {
          // 没有新阶段完成，且用户没有手动选择过，且当前选中的就是最后完成的阶段，更新数据
          console.log("[StatusUpdate] Updating same stage data:", lastCompletedId);
          setSelectedStageData(lastCompletedStage);
        }
        // Phase 25: 用户手动选择了其他历史阶段时，不做任何切换，尊重用户选择
      }
    }
    
    // 强制更新当前选中阶段的数据（确保状态同步）
    // 这是关键修复：即使阶段ID没变，也要确保数据是最新的
    // 注意：只在没有自动切换阶段时才更新，避免覆盖刚设置的新阶段数据
    // Phase 24: 简化判断逻辑 - 只有在running阶段时才强制更新数据
    // paused/completed状态下的更新已在上面的逻辑中处理
    if (runningStageEntry && currentSelectedStageId && status.stages[currentSelectedStageId]) {
      const currentStageData = status.stages[currentSelectedStageId];
      console.log("[StatusUpdate] Force updating current selected stage:", currentSelectedStageId, "status:", currentStageData.status, "progress:", currentStageData.progress);
      setSelectedStageData(currentStageData);
    }
    
    // 当任务完成时，重置手动选择标记，允许下次任务自动跟踪
    // Phase 25: 同时重置lastCompletedStageIdRef，为下次任务准备
    if (status.status === "completed" || status.status === "failed" || status.status === "stopped") {
      setIsUserManualSelection(false);
      lastCompletedStageIdRef.current = null;
    }
  }, []);  // 移除依赖，使用ref获取最新值

  // Phase 3: 返回代码编辑器模式
  // Phase 3: 返回代码编辑器模式，重置手动选择标记
  const handleBackToCodeEditor = () => {
    setRightPanelMode("code");
    setSelectedStageId(null);
    setSelectedStageData(null);
    setIsUserManualSelection(false);  // 重置手动选择标记，恢复自动跟踪
  };

  // 获取工作区文件列表（用于SOP配置面板）
  const getWorkspaceFilesList = useCallback(() => {
    if (!workspaceTree?.children) return [];

    // 辅助函数：从文件名推断文件类型
    const getFileType = (filename: string): string => {
      const ext = filename.toLowerCase();
      if (ext.endsWith('.csv')) return 'csv';
      if (ext.endsWith('.xlsx')) return 'xlsx';
      if (ext.endsWith('.xls')) return 'xls';
      return 'unknown';
    };

    const files: Array<{ name: string; path: string; type: string }> = [];
    const traverse = (nodes: WorkspaceNode[]) => {
      for (const node of nodes) {
        if (!node.is_dir) {
          files.push({
            name: node.name,
            path: node.path,
            type: getFileType(node.name)  // 添加文件类型
          });
        }
        if (node.children) {
          traverse(node.children);
        }
      }
    };
    traverse(workspaceTree.children);
    return files;
  }, [workspaceTree]);

  const removeAttachment = (id: string) => {
    setAttachments((prev) => prev.filter((att) => att.id !== id));
  };

  // 文件引用处理函数
  const addFileReference = useCallback((file: { name: string; path: string }) => {
    setFileReferences((prev) => {
      // 检查是否已存在相同路径的引用
      if (prev.some((ref) => ref.path === file.path)) {
        toast({ description: "该文件已添加到对话中" });
        return prev;
      }
      return [...prev, { id: `ref-${Date.now()}`, name: file.name, path: file.path }];
    });
    toast({ description: `已添加文件引用: ${file.name}` });
  }, [toast]);

  const removeFileReference = useCallback((id: string) => {
    setFileReferences((prev) => prev.filter((ref) => ref.id !== id));
  }, []);

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <>
      <div
        className="h-screen bg-white dark:bg-black text-black dark:text-white"
        suppressHydrationWarning
      >
        <ResizablePanelGroup direction="horizontal" className="h-full">
          {/* Left Panel - Workspace Tree */}
          <ResizablePanel defaultSize={25} minSize={15}>
            <div className="flex flex-col min-h-0 min-w-0 h-full">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800 h-12">
                <h2 className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Files
                </h2>
                <div
                  className="flex items-center gap-1"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={async (e) => {
                    e.preventDefault();
                    const items = Array.from(e.dataTransfer.files || []);
                    if (!items.length) return;
                    const form = new FormData();
                    items.forEach((f) => form.append("files", f));
                    const dir = contextTarget?.is_dir ? contextTarget.path : "";
                    try {
                      const url = `${getApiUrl(API_URLS.WORKSPACE_UPLOAD_TO)}?dir=${encodeURIComponent(
                        dir
                      )}&session_id=${encodeURIComponent(sessionId)}`;
                      await authFetch(url, { method: "POST", body: form });
                      await loadWorkspaceTree();
                      await loadWorkspaceFiles();
                    } catch (err) {
                      console.error(err);
                    }
                  }}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    onChange={handleFileUpload}
                    className="hidden"
                    accept="*"
                  />
                  {/* 全选 / 取消全选 */}
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 px-1.5 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300"
                        onClick={toggleSelectAll}
                        aria-label={isAllSelected ? "取消全选" : "全选文件"}
                      >
                        {isAllSelected ? (
                          <CheckSquare className="h-3.5 w-3.5 text-blue-500" />
                        ) : isPartialSelected ? (
                          <CheckSquare className="h-3.5 w-3.5 text-blue-300" />
                        ) : (
                          <Square className="h-3.5 w-3.5" />
                        )}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" className="text-xs">
                      {isAllSelected ? "取消全选" : "全选文件"}
                    </TooltipContent>
                  </Tooltip>
                  {/* 批量删除（有选中时显示） */}
                  {selectedPaths.size > 0 && (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2 text-xs text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/20"
                          onClick={() => setBatchDeleteOpen(true)}
                        >
                          <Trash2 className="h-3 w-3 mr-1" />
                          {selectedPaths.size}
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent side="bottom" className="text-xs">
                        删除选中的 {selectedPaths.size} 个文件
                      </TooltipContent>
                    </Tooltip>
                  )}
                  {/* 清空 workspace */}
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 px-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300"
                        title="清空 workspace"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>清空 workspace？</AlertDialogTitle>
                        <AlertDialogDescription>
                          将删除 workspace
                          根目录下的所有文件与文件夹，此操作不可撤销。
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>取消</AlertDialogCancel>
                        <AlertDialogAction
                          className="bg-red-600 hover:bg-red-700"
                          onClick={clearWorkspace}
                        >
                          确认清空
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </div>

              <div
                ref={treeContainerRef}
                className="flex-[0.3] min-h-0 overflow-y-auto overflow-x-hidden pl-3 pr-1 py-2"
              >
                <div
                  className={`mb-2 rounded border border-dashed flex items-center justify-center h-20 text-xs select-none ${
                    dropActive
                      ? "bg-blue-50 border-blue-300 text-blue-600"
                      : "bg-gray-50 dark:bg-gray-900/40 border-gray-300 dark:border-gray-700 text-gray-500"
                  }`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDropActive(true);
                  }}
                  onDragLeave={() => setDropActive(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDropActive(false);
                    const files = e.dataTransfer.files;
                    if (files && files.length) uploadToDir("", files);
                  }}
                  onClick={() => fileInputRef.current?.click()}
                >
                  {/* 独立隐藏 input 兼容点击上传 */}
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    onChange={handleFileUpload}
                    className="hidden"
                    accept="*"
                  />
                  <div className="flex items-center gap-2">
                    <Upload className="h-4 w-4" />
                    <span>拖拽或点击此处上传（workspace 根目录）</span>
                  </div>
                </div>
                {uploadMsg && (
                  <div className="px-2 pb-2 text-[11px] text-gray-500">
                    {uploadMsg}
                  </div>
                )}
                {workspaceTree ? (
                  <Tree
                    width={treeSize.w || 300}
                    height={Math.max(0, (treeSize.h || 400) - 100)}
                    data={toArbor(workspaceTree).children || []}
                    openByDefault
                    indent={14}
                    rowHeight={28}
                  >
                    {Row}
                  </Tree>
                ) : (
                  <div className="flex items-center justify-center h-full text-sm text-gray-500">
                    Loading...
                  </div>
                )}
              </div>

              {/* SOP任务选择器 */}
              <div className="flex-[0.7] min-h-0 border-t border-gray-200 dark:border-gray-800 overflow-y-auto">
                <TaskSelector
                  onTaskSelect={handleTaskSelect}
                  selectedTaskId={selectedTaskId}
                  isExecuting={isSOPExecuting}
                />
                
                {/* 模式选择器 - 仅在选择任务后显示，任务发起后锁定不可修改 */}
                {selectedTaskId && (
                  <div className="border-t border-gray-200 dark:border-gray-800 p-3">
                    <ModeSelector
                      interactionMode={historyTaskInteractionMode 
                        ? (historyTaskInteractionMode as InteractionMode)
                        : interactionMode}
                      onInteractionModeChange={setInteractionMode}
                      disabled={isSOPExecuting || !!currentExecutionId || !!historyTaskInteractionMode}
                    />
                    {/* 任务已发起时显示锁定提示 */}
                    {(!!currentExecutionId || !!historyTaskInteractionMode) && !isSOPExecuting && (
                      <div className="mt-2 text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                        </svg>
                        <span>任务已发起，模式不可修改</span>
                      </div>
                    )}
                  </div>
                )}
                
                {/* 任务历史入口 */}
                <div className="border-t border-gray-200 dark:border-gray-800 p-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full justify-start text-xs text-gray-600 dark:text-gray-400"
                    onClick={() => setShowTaskHistory(!showTaskHistory)}
                  >
                    <RefreshCw className="h-3 w-3 mr-2" />
                    {showTaskHistory ? "隐藏任务历史" : "查看任务历史"}
                  </Button>
                </div>

                {/* 任务历史列表（紧凑版，左侧列展示） */}
                {showTaskHistory && (
                  <div className="flex-1 min-h-0 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/30 overflow-hidden">
                    <TaskHistoryCompact
                      ref={historyCompactRef}
                      onViewDetail={handleViewTaskDetail}
                      className="h-full"
                    />
                  </div>
                )}
              </div>
            </div>
          </ResizablePanel>

          <ResizableHandle withHandle />

          {/* Middle Panel - Chat & Analysis */}
          <ResizablePanel defaultSize={40} minSize={25}>
            <div className="flex flex-col min-h-0 min-w-0 h-full">
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800 h-12 shrink-0">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <h1 className="text-sm font-medium">Assistant</h1>
                    {isTyping && (
                      <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                        <div className="w-3 h-3 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
                        <span>执行中…</span>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
                    <span>自动折叠</span>
                    <Switch
                      className="data-[state=unchecked]:bg-gray-200 data-[state=unchecked]:border data-[state=unchecked]:border-gray-300"
                      checked={autoCollapseEnabled}
                      onCheckedChange={(v: boolean) => {
                        setAutoCollapseEnabled(!!v);
                        if (typeof window !== "undefined") {
                          localStorage.setItem(
                            "autoCollapseEnabled",
                            (!!v).toString()
                          );
                        }
                        // 关闭自动折叠时，展开所有块
                        if (!v) {
                          setCollapsedSections({});
                          setManualLocks({});
                        }
                      }}
                    />
                  </div>
                  {/* 旧菜单已移除 */}
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={toggleTheme}
                    className="h-8 w-8 p-0"
                  >
                    {mounted ? (
                      isDarkMode ? (
                        <Sun className="h-4 w-4" />
                      ) : (
                        <Moon className="h-4 w-4" />
                      )
                    ) : (
                      <Moon className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>

              {/* Step Navigator - Top Horizontal */}
              {(() => {
                // 只显示最后一条 AI 消息的步骤
                let lastAiMsgIndex = -1;
                let lastAiMsg = null;

                for (let i = messages.length - 1; i >= 0; i--) {
                  if (messages[i].sender === "ai") {
                    lastAiMsg = messages[i];
                    lastAiMsgIndex = i;
                    break;
                  }
                }

                if (!lastAiMsg || lastAiMsgIndex === -1) return null;

                const allSections = extractSections(
                  lastAiMsg.content,
                  lastAiMsgIndex
                );

                if (allSections.length === 0) return null;

                return (
                  <div className="relative border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-950 px-6 py-4 overflow-hidden">
                    {/* 背景装饰 */}
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-50/50 via-purple-50/30 to-pink-50/50 dark:from-blue-950/20 dark:via-purple-950/10 dark:to-pink-950/20 pointer-events-none" />

                    <div
                      ref={stepNavigatorRef}
                      className="relative flex items-center gap-1 overflow-x-auto pb-1 scrollbar-thin"
                    >
                      {allSections.map((section, idx) => {
                        const isActive = activeSection === section.sectionKey;
                        const activeIdx = allSections.findIndex(
                          (s) => s.sectionKey === activeSection
                        );
                        const isCompleted = activeIdx > idx;
                        const isPending = activeIdx < idx;

                        // 颜色映射
                        const colorMap: Record<
                          string,
                          {
                            bg: string;
                            border: string;
                            glow: string;
                            text: string;
                          }
                        > = {
                          "bg-blue-500": {
                            bg: "bg-blue-500",
                            border: "border-blue-400",
                            glow: "shadow-blue-500/50",
                            text: "text-blue-600",
                          },
                          "bg-cyan-500": {
                            bg: "bg-cyan-500",
                            border: "border-cyan-400",
                            glow: "shadow-cyan-500/50",
                            text: "text-cyan-600",
                          },
                          "bg-gray-500": {
                            bg: "bg-gray-500",
                            border: "border-gray-400",
                            glow: "shadow-gray-500/50",
                            text: "text-gray-600",
                          },
                          "bg-orange-500": {
                            bg: "bg-orange-500",
                            border: "border-orange-400",
                            glow: "shadow-orange-500/50",
                            text: "text-orange-600",
                          },
                          "bg-green-500": {
                            bg: "bg-green-500",
                            border: "border-green-400",
                            glow: "shadow-green-500/50",
                            text: "text-green-600",
                          },
                          "bg-purple-500": {
                            bg: "bg-purple-500",
                            border: "border-purple-400",
                            glow: "shadow-purple-500/50",
                            text: "text-purple-600",
                          },
                        };
                        const colors =
                          colorMap[section.config.color] ||
                          colorMap["bg-gray-500"];

                        return (
                          <div
                            key={section.sectionKey}
                            className="flex items-center shrink-0"
                            ref={(el) => {
                              if (el) {
                                activeStepRefs.current.set(
                                  section.sectionKey,
                                  el
                                );
                              }
                            }}
                          >
                            {/* 步骤节点 */}
                            <button
                              onClick={() =>
                                scrollToSection(section.sectionKey)
                              }
                              className={`group relative flex flex-col items-center gap-1.5 px-2 py-1.5 rounded-lg transition-all duration-300 ${
                                isActive
                                  ? "scale-105"
                                  : "hover:scale-102 hover:bg-gray-50 dark:hover:bg-gray-900/50"
                              }`}
                            >
                              {/* 圆圈容器 */}
                              <div className="relative">
                                {/* 脉动动画背景 */}
                                {isActive && (
                                  <div
                                    className={`absolute inset-0 ${colors.bg} rounded-full animate-ping opacity-20`}
                                  />
                                )}

                                {/* 主圆圈 */}
                                <div
                                  className={`relative w-9 h-9 rounded-full flex items-center justify-center font-semibold text-base transition-all duration-500 ${
                                    isActive
                                      ? `${colors.bg} text-white shadow-lg ${
                                          colors.glow
                                        } ring-2 ring-offset-1 ${colors.border.replace(
                                          "border-",
                                          "ring-"
                                        )} ring-opacity-30 dark:ring-offset-gray-950`
                                      : isCompleted
                                      ? "bg-gradient-to-br from-green-400 to-green-600 text-white shadow-md shadow-green-500/30"
                                      : "bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 border-2 border-gray-300 dark:border-gray-600 text-gray-400 dark:text-gray-500"
                                  } ${
                                    !isActive &&
                                    !isCompleted &&
                                    "group-hover:border-gray-400 dark:group-hover:border-gray-500 group-hover:shadow-md"
                                  }`}
                                >
                                  {/* 内容 */}
                                  {isCompleted ? (
                                    <Check className="w-4 h-4 animate-in zoom-in duration-300" />
                                  ) : (
                                    <span
                                      className={`text-base transition-transform duration-300 ${
                                        isActive
                                          ? "scale-110"
                                          : "group-hover:scale-105"
                                      }`}
                                    >
                                      {section.config.icon}
                                    </span>
                                  )}

                                  {/* 进度指示小点 */}
                                  {isActive && (
                                    <div className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-white dark:bg-gray-950 rounded-full flex items-center justify-center">
                                      <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* 标签 */}
                              <div
                                className={`text-[11px] font-semibold whitespace-nowrap transition-all duration-300 ${
                                  isActive
                                    ? `${colors.text} dark:text-white scale-105`
                                    : isCompleted
                                    ? "text-green-600 dark:text-green-400"
                                    : "text-gray-500 dark:text-gray-400 group-hover:text-gray-700 dark:group-hover:text-gray-300"
                                }`}
                              >
                                {section.type}
                              </div>

                              {/* 序号 */}
                              <div
                                className={`absolute top-0 left-0 w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold transition-all duration-300 ${
                                  isActive
                                    ? `${colors.bg} text-white shadow-sm`
                                    : isCompleted
                                    ? "bg-green-500 text-white"
                                    : "bg-gray-300 dark:bg-gray-600 text-gray-600 dark:text-gray-300"
                                }`}
                              >
                                {idx + 1}
                              </div>
                            </button>

                            {/* 连接线 */}
                            {idx < allSections.length - 1 && (
                              <div className="relative w-16 h-1 mx-1">
                                {/* 背景轨道 */}
                                <div className="absolute inset-0 bg-gray-200 dark:bg-gray-700 rounded-full" />

                                {/* 进度条 */}
                                <div
                                  className={`absolute inset-0 rounded-full transition-all duration-700 ${
                                    isCompleted || isActive
                                      ? "bg-gradient-to-r from-green-400 to-green-500 shadow-sm shadow-green-500/30"
                                      : "bg-transparent"
                                  }`}
                                  style={{
                                    transform: isActive
                                      ? "scaleX(0.5)"
                                      : "scaleX(1)",
                                    transformOrigin: "left",
                                  }}
                                />

                                {/* 流动动画 */}
                                {isActive && (
                                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-50 animate-shimmer" />
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })()}

              {/* SOP配置面板 - 统一使用TaskConfigPanel动态渲染 */}
              {showConfigPanel && selectedTaskId && (
                <div className="border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 flex-1 overflow-y-auto overscroll-contain">
                  <TaskConfigPanel
                    taskId={selectedTaskId}
                    sessionId={sessionId}
                    dataFiles={getWorkspaceFilesList().filter(f => 
                      f.name.endsWith('.csv') || 
                      f.name.endsWith('.xlsx') || 
                      f.name.endsWith('.xls')
                    )}
                    onExecute={(params, filePath) => {
                      // 执行后清除 pendingInitialParams
                      setPendingInitialParams(null);
                      handleSOPExecute(params, filePath);
                    }}
                    onClose={() => {
                      // 关闭时也清除 pendingInitialParams
                      setPendingInitialParams(null);
                      handleCloseConfigPanel();
                    }}
                    isExecuting={isSOPExecuting}
                    initialParams={pendingInitialParams}
                  />
                </div>
              )}

              {/* SOP任务进度 - 仅在执行中显示，头部固定+内容可滚动 */}
              {currentExecutionId && isSOPExecuting && (
                <div className="border-b border-gray-200 dark:border-gray-800 bg-blue-50 dark:bg-blue-900/20 flex flex-col flex-1 min-h-0">
                  {/* 固定头部：模式标签 + 进度条 + 控制按钮 */}
                  <div className="flex-shrink-0 p-4 pb-2">
                    {/* 显示当前模式标签 + 返回按钮 */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-300">
                          Pipeline模式
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-800 text-green-700 dark:text-green-300">
                          {interactionMode === "auto" ? "自动执行" : "专家模式"}
                        </span>
                      </div>
                      {/* 返回任务列表按钮 - 移到右侧 */}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleBackToTaskList}
                        className="h-7 w-7 p-0"
                        title="返回任务列表"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                    
                    {/* 固定的进度条头部（只显示头部，不显示阶段卡片） */}
                    <SopStageController
                      executionStatus={sopExecutionStatus}
                      taskId={sopExecutionStatus?.task_id || selectedTaskId || ""}
                      onStageClick={handleStageClick}
                      onPause={handlePauseExecution}
                      onStop={handleStopExecution}
                      onResume={handleResumeExecution}
                      isPaused={sopExecutionStatus?.status === "paused"}
                      isExpertMode={isExpertModeTask}
                      showHeader={true}
                      showStages={false}
                    />
                  </div>
                  
                  {/* 可滚动的阶段卡片列表（只显示阶段卡片，不显示头部） */}
                  <div className="flex-1 overflow-y-auto px-4 pb-4">
                    <SopStageController
                      executionStatus={sopExecutionStatus}
                      taskId={sopExecutionStatus?.task_id || selectedTaskId || ""}
                      onStageClick={handleStageClick}
                      onSkipStage={isExpertModeTask ? handleSkipStage : undefined}
                      isPaused={sopExecutionStatus?.status === "paused"}
                      isExpertMode={isExpertModeTask}
                      showHeader={false}
                      showStages={true}
                      isRestoredTask={!!historyTaskInteractionMode}
                    />
                  </div>
                  
                  {/* 保留原TaskProgress用于状态轮询 */}
                  <div className="hidden">
                    <TaskProgress
                      executionId={currentExecutionId}
                      pollTrigger={pollTrigger}
                      taskId={sopExecutionStatus?.task_id || selectedTaskId || undefined}
                      onComplete={handleSOPComplete}
                      onClose={handleCloseProgress}
                      onStatusUpdate={handleSOPStatusUpdate}
                    />
                  </div>
                </div>
              )}

              {/* SOP结果/阶段详情展示 - 任务完成后或查看历史时显示 */}
              {/* 显示条件：showResults为true 且 不在执行中（避免与上方执行中视图重复） */}
              {!isSOPExecuting && ((showResults && completedExecutionId) || 
                (sopExecutionStatus && (sopExecutionStatus.status === "completed" || sopExecutionStatus.status === "failed" || sopExecutionStatus.status === "cancelled" || sopExecutionStatus.status === "stopped" || sopExecutionStatus.status === "paused"))) && (
                <div className="border-b border-gray-200 dark:border-gray-800 flex-1 overflow-y-auto min-h-0">
                  {/* 视图切换头部 */}
                  <div className="sticky top-0 z-10 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {/* 视图切换按钮组 */}
                        <div className="flex items-center gap-1 bg-gray-200 dark:bg-gray-700 rounded-lg p-0.5">
                          <button
                            onClick={() => setResultViewMode("results")}
                            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                              resultViewMode === "results"
                                ? "bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm"
                                : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
                            }`}
                          >
                            任务结果
                          </button>
                          <button
                            onClick={() => setResultViewMode("stages")}
                            disabled={!sopExecutionStatus?.stages || Object.keys(sopExecutionStatus.stages).length === 0}
                            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                              resultViewMode === "stages"
                                ? "bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm"
                                : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
                            } ${
                              !sopExecutionStatus?.stages || Object.keys(sopExecutionStatus.stages).length === 0
                                ? "opacity-50 cursor-not-allowed"
                                : ""
                            }`}
                          >
                            阶段详情
                          </button>
                        </div>
                        
                        {/* AI分析评估按钮 - 任务完成时显示（两种视图模式下都可见） */}
                        {completedExecutionId && sopExecutionStatus?.status === "completed" && (
                            <Button
                              onClick={handleAIAnalysis}
                              disabled={isAIAnalyzing || isExpertModeTask}
                              title={isExpertModeTask ? "专家模式下各阶段已包含AI分析" : "对任务结果进行AI智能分析"}
                              className={`h-8 px-3 text-xs font-medium transition-all duration-200 ${
                                isExpertModeTask
                                  ? "bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed"
                                  : "bg-gradient-to-r from-purple-500 to-indigo-500 hover:from-purple-600 hover:to-indigo-600 text-white shadow-md hover:shadow-lg"
                              }`}
                            >
                              {isAIAnalyzing ? (
                                <>
                                  <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                                  分析中...
                                </>
                              ) : (
                                <>
                                  <BrainCircuit className="h-3.5 w-3.5 mr-1.5" />
                                  AI 分析评估
                                </>
                              )}
                            </Button>
                        )}
                      </div>
                      {/* 返回任务列表按钮 - 移到右侧 */}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleBackToTaskList}
                        className="h-7 w-7 p-0"
                        title="返回任务列表"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  
                  {/* 根据视图模式显示不同内容 */}
                  {resultViewMode === "results" ? (
                    <div className="bg-green-50 dark:bg-green-900/20">
                      {completedExecutionId ? (
                        (sopExecutionStatus?.task_id || selectedTaskId) === "scorecard_dev" ? (
                          <ScorecardResults
                            executionId={completedExecutionId}
                          />
                        ) : (
                          <RuleMiningResults
                            executionId={completedExecutionId}
                          />
                        )
                      ) : (
                        <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                          <p>任务尚未完成，暂无结果</p>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setResultViewMode("stages")}
                            className="mt-3"
                          >
                            查看阶段详情
                          </Button>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="bg-blue-50 dark:bg-blue-900/20 flex flex-col">
                      {/* 固定头部：模式标签 + 进度条 + 控制按钮 */}
                      <div className="flex-shrink-0 sticky top-[41px] z-[5] bg-blue-50 dark:bg-blue-900/20 p-4 pb-2 border-b border-blue-100 dark:border-blue-800/50">
                        {/* 显示当前模式标签 */}
                        <div className="flex items-center gap-2 mb-3">
                          <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-300">
                            Pipeline模式
                          </span>
                          <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-800 text-green-700 dark:text-green-300">
                            {isExpertModeTask ? "专家模式" : "自动执行"}
                          </span>
                        </div>
                        
                        {/* 固定的进度条头部（只显示头部，不显示阶段卡片） */}
                        <SopStageController
                          executionStatus={sopExecutionStatus}
                          taskId={sopExecutionStatus?.task_id || selectedTaskId || ""}
                          onStageClick={handleStageClick}
                          onPause={handlePauseExecution}
                          onStop={handleStopExecution}
                          onResume={handleResumeExecution}
                          isPaused={sopExecutionStatus?.status === "paused"}
                          isExpertMode={isExpertModeTask}
                          showHeader={true}
                          showStages={false}
                        />
                      </div>
                      
                      {/* 可滚动的阶段卡片列表 */}
                      <div className="px-4 pb-4">
                        <SopStageController
                          executionStatus={sopExecutionStatus}
                          taskId={sopExecutionStatus?.task_id || selectedTaskId || ""}
                          onStageClick={handleStageClick}
                          onSkipStage={isExpertModeTask ? handleSkipStage : undefined}
                          isPaused={sopExecutionStatus?.status === "paused"}
                          isExpertMode={isExpertModeTask}
                          showHeader={false}
                          showStages={true}
                          isRestoredTask={!!historyTaskInteractionMode}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Chat Messages - SOP 面板激活时收缩为 h-0，让 SOP 面板撑满剩余空间 */}
              <div
                ref={messagesContainerRef}
                className={`min-w-0 overflow-y-auto overflow-x-hidden px-4 py-4 pr-5 space-y-6 ${
                  isTyping ? "scrollbar-hide" : "scrollbar-auto"
                } ${isSopMode ? "h-0 flex-none" : "flex-1 min-h-0"}`}
              >
                {!isSopMode && messages.map((message, msgIdx) => (
                  <div key={message.id} className="space-y-2">
                    {message.sender === "user" ? (
                      <div className="flex items-start justify-end gap-2">
                        <div className="max-w-[80%] bg-black text-white dark:bg-white dark:text-black rounded-lg px-4 py-3 message-bubble message-appear">
                          <div className="text-sm break-words whitespace-pre-wrap">
                            {message.content}
                          </div>
                        </div>
                        <Avatar>
                          <AvatarFallback className="text-[10px]">
                            U
                          </AvatarFallback>
                        </Avatar>
                      </div>
                    ) : (
                      <div className="flex items-start gap-2 min-w-0">
                        <Avatar>
                          <AvatarFallback className="text-[10px]">
                            <Sparkles className="h-3 w-3" />
                          </AvatarFallback>
                        </Avatar>
                        <div className="min-w-0 flex-1 message-appear">
                          <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
                            Assistant
                          </div>
                          <div className="space-y-4 min-w-0">
                            {renderMessageWithSections(message.content, msgIdx)}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
                {/* 加载气泡已移除，改为仅按钮态提示 */}
                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div className="border-t border-gray-200 dark:border-gray-800 shrink-0">
                {/* 文件引用列表 - 显示在输入区域顶部 */}
                <FileReferenceList
                  references={fileReferences}
                  onRemove={removeFileReference}
                />
                <div className="p-4">
                {/* 模型选择器 */}
                <div className="mb-3">
                  <ModelSelector
                    selectedConfig={selectedConfig}
                    onConfigChange={setSelectedConfig}
                  />
                </div>
                <div className="flex gap-3 items-end">
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    onChange={handleFileUpload}
                    className="hidden"
                    accept="*"
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                    className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                  >
                    <Paperclip className="h-4 w-4" />
                  </Button>
                  <div className="flex-1 relative">
                    <Input
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      placeholder="Ask anything..."
                      onKeyPress={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage();
                        }
                      }}
                      className="border-gray-200 dark:border-gray-700 bg-white dark:bg-black rounded-lg"
                    />
                  </div>
                  {/* 将清空按钮移动到发送按钮旁边 */}
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        title="清空聊天"
                        className="h-9 px-2"
                        disabled={isTyping}
                      >
                        <Eraser className="h-4 w-4" />
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>清空聊天？</AlertDialogTitle>
                        <AlertDialogDescription>
                          将删除当前会话内的所有消息，仅保留欢迎提示。
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>取消</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={clearChat}
                          className="bg-red-600 hover:bg-red-700"
                        >
                          确认清空
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                  {isTyping ? (
                    <Button
                      size="sm"
                      className="h-9 w-9 p-0 rounded-full bg-white text-black border border-blue-400/50 dark:bg-white dark:text-black"
                      title="正在生成…"
                      disabled
                    >
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    </Button>
                  ) : (
                    <Button
                      onClick={handleSendMessage}
                      size="sm"
                      disabled={!inputValue.trim() && fileReferences.length === 0}
                      className="bg-black text-white dark:bg-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-200"
                    >
                      <Send className="h-4 w-4" />
                    </Button>
                  )}
                </div>
                </div>
              </div>
            </div>
          </ResizablePanel>

          <ResizableHandle withHandle />

          {/* Right Panel - Code Editor / Stage Output Preview */}
          <ResizablePanel defaultSize={35} minSize={20}>
            <div className="flex flex-col bg-gray-50 dark:bg-gray-900 min-h-0 h-full">
              {/* Phase 3: 根据rightPanelMode显示不同内容 */}
              {rightPanelMode === "preview" && selectedStageData ? (() => {
                // 使用 ModeContext 提供的 isExpertModeTask，无需重复判断
                // 判断是否为最后一个阶段（使用API返回的stage_order，避免Object.values顺序不确定）
                const stageOrder = getStageOrder(sopExecutionStatus || { task_id: selectedTaskId || "" });
                const lastStageId = stageOrder.length > 0 ? stageOrder[stageOrder.length - 1] : null;
                const isLastStage = selectedStageId === lastStageId;
                
                return (
                <StageOutputPreview
                  key={`${selectedStageId}-${selectedStageData.status}`}
                  stageId={selectedStageId || ""}
                  stageName={selectedStageData.stage_name}
                  outputPreview={selectedStageData.output_preview || null}
                  status={selectedStageData.status}
                  onBack={handleBackToCodeEditor}
                  className="h-full"
                  // 专家模式相关属性
                  isExpertMode={isExpertModeTask}
                  stageData={{
                    params: selectedStageData.params || selectedStageData.params_used || {},
                    params_meta: selectedStageData.params_meta,
                    code: selectedStageData.code || "",
                  }}
                  executionTimeMs={selectedStageData.execution_time_ms}
                  onEditParams={(stageId, params) => {
                    // 更新阶段参数 - 使用currentExecutionId（活跃执行）而非sopExecutionStatus.execution_id（可能是历史记录）
                    if (currentExecutionId) {
                      sopService.updateExpertStageParams(currentExecutionId, stageId, params)
                        .then(() => {
                          toast({ description: `阶段 ${stageId} 参数已更新` });
                        })
                        .catch((err) => {
                          const errorMsg = err.message || "参数更新失败";
                          // 检测执行上下文不存在的错误
                          if (errorMsg.includes("not found") || errorMsg.includes("404")) {
                            toast({ 
                              description: "执行上下文已过期，请重新启动任务", 
                              variant: "destructive" 
                            });
                          } else {
                            toast({ description: `参数更新失败: ${errorMsg}`, variant: "destructive" });
                          }
                        });
                    } else {
                      toast({ 
                        description: "无法更新参数：当前没有活跃的执行任务", 
                        variant: "destructive" 
                      });
                    }
                  }}
                  onRetryStage={async (stageId, newParams) => {
                    // 阶段重试：使用新参数重新执行该阶段及后续阶段
                    if (!currentExecutionId) {
                      toast({ 
                        description: "无法重试：当前没有活跃的执行任务", 
                        variant: "destructive" 
                      });
                      return;
                    }
                    
                    try {
                      // 调用阶段重试 API，传递新参数
                      console.log('[Retry Stage] Calling API:', { executionId: currentExecutionId, stageId, newParams });
                      const result = await sopService.retryStage(currentExecutionId, stageId, newParams);
                      console.log('[Retry Stage] API response:', result);
                      
                      if (result.success) {
                        toast({ description: result.message || `阶段 ${stageId} 正在重试` });
                        // 重启轮询（paused 停止后需要 pollTrigger 重启以追踪重试进度）
                        restartPolling();
                      } else {
                        toast({ description: `重试失败: ${result.message}`, variant: "destructive" });
                      }
                    } catch (err: any) {
                      const errorMsg = err.message || "重试失败";
                      if (errorMsg.includes("not found") || errorMsg.includes("404")) {
                        toast({ 
                          description: "执行上下文已过期，请重新启动任务", 
                          variant: "destructive" 
                        });
                      } else if (errorMsg.includes("不是暂停状态")) {
                        toast({ 
                          description: "任务不是暂停状态，无法重试", 
                          variant: "destructive" 
                        });
                      } else {
                        toast({ description: `重试失败: ${errorMsg}`, variant: "destructive" });
                      }
                    }
                  }}
                  sessionId={sessionId}
                  recordId={historyTaskRecordId || sopExecutionStatus?.record_id || undefined}
                  dataFilePath={sopExecutionStatus?.file_path}
                  isDarkMode={isDarkMode}
                  selectedModel={selectedConfig?.id ? `config_${selectedConfig.id}` : undefined}
                  modelConfig={selectedConfig ? {
                    temperature: selectedConfig.temperature,
                    frequency_penalty: selectedConfig.frequency_penalty,
                    presence_penalty: selectedConfig.presence_penalty,
                  } : undefined}
                  // 自动模式 AI 分析：仅在非专家模式且为最后一个阶段时传递
                  // 注意：isExternalAnalyzing 需要在分析中时始终传递，否则加载状态不显示
                  externalAiAnalysis={
                    !isExpertModeTask && isLastStage && aiAnalysisResult
                      ? aiAnalysisResult
                      : undefined
                  }
                  isExternalAnalyzing={!isExpertModeTask && isLastStage && isAIAnalyzing}
                  onExternalReanalyze={handleAIAnalysis}
                  // Phase 20: 专家模式最后阶段整体分析所需
                  isLastStage={isLastStage}
                  taskType={sopExecutionStatus?.task_id || selectedTaskId || undefined}
                  // 修复：taskResult 传递条件与 StageOutputPreview 中 shouldUseOverallAnalysis 保持一致
                  // report_generation 阶段需要整体分析，不再依赖 isLastStage 判断
                  taskResult={isExpertModeTask && selectedStageId === "report_generation" ? taskExecutionResult : null}
                />
                );
              })() : (
                <>
                  <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800 h-12 shrink-0">
                    <h2 className="text-sm font-medium text-gray-600 dark:text-gray-400">
                      Code
                    </h2>
                    {showCodeEditor && (
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setShowCodeEditor(false);
                            setCodeEditorContent("");
                            setSelectedCodeSection("");
                          }}
                          className="h-6 px-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                        >
                          Close
                        </Button>
                        <Button
                          size="sm"
                          onClick={executeCode}
                          disabled={!codeEditorContent || isExecutingCode}
                          className="h-6 px-3 text-xs bg-black text-white dark:bg-white dark:text-black"
                        >
                          {isExecutingCode ? "Running..." : "Run"}
                        </Button>
                      </div>
                    )}
                  </div>

                  {!showCodeEditor ? (
                    <div className="flex-1 flex items-center justify-center text-gray-400">
                      <div className="text-center select-none">
                        <p className="text-sm">Click a code block to edit</p>
                        {isSOPExecuting && (
                          <p className="text-xs mt-2 text-blue-500">
                            点击左侧阶段卡片查看输出预览
                          </p>
                        )}
                      </div>
                    </div>
                  ) : (
                <div className="flex-1 min-h-0 flex flex-col p-4 editor-container overflow-hidden">
                  {/* Code Editor */}
                  <div
                    className="min-h-0 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-black flex flex-col"
                    style={{ height: `${editorHeight}%` }}
                  >
                    <div className="bg-gray-50 dark:bg-gray-800 px-3 py-2 border-b border-gray-200 dark:border-gray-700 shrink-0">
                      <span className="text-xs text-gray-500 font-mono">
                        python
                      </span>
                    </div>
                    <div className="flex-1 min-h-0">
                      <Editor
                        height="100%"
                        defaultLanguage="python"
                        value={codeEditorContent}
                        onChange={(value) => setCodeEditorContent(value || "")}
                        theme={isDarkMode ? "vs-dark" : "light"}
                        options={{
                          fontSize: 14,
                          fontFamily:
                            "var(--font-mono), 'Courier New', monospace",
                          lineNumbers: "on",
                          minimap: { enabled: false },
                          scrollBeyondLastLine: false,
                          automaticLayout: true,
                          tabSize: 4,
                          insertSpaces: true,
                          wordWrap: "on",
                          folding: true,
                          lineDecorationsWidth: 10,
                          lineNumbersMinChars: 3,
                          glyphMargin: false,
                          selectOnLineNumbers: true,
                          roundedSelection: false,
                          readOnly: false,
                          cursorStyle: "line",
                          smoothScrolling: true,
                          formatOnPaste: true,
                          formatOnType: true,
                          suggestOnTriggerCharacters: true,
                          acceptSuggestionOnEnter: "on",
                          tabCompletion: "on",
                          scrollbar: {
                            vertical: "visible",
                            verticalScrollbarSize: 10,
                          },
                        }}
                        loading={
                          <div className="flex items-center justify-center h-full">
                            <div className="flex items-center gap-2 text-muted-foreground">
                              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                              <span className="text-sm">加载编辑器...</span>
                            </div>
                          </div>
                        }
                      />
                    </div>
                  </div>

                  {/* Resizer */}
                  <div
                    className="h-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 cursor-row-resize flex items-center justify-center group"
                    onMouseDown={handleMouseDown}
                  >
                    <div className="w-8 h-1 bg-gray-300 dark:bg-gray-600 rounded group-hover:bg-gray-400 dark:group-hover:bg-gray-500"></div>
                  </div>

                  {/* Terminal Output */}
                  <div
                    className="min-h-0 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-900 flex flex-col"
                    style={{ height: `${100 - editorHeight}%` }}
                  >
                    <div className="bg-gray-50 dark:bg-gray-800 px-3 py-2 border-b border-gray-200 dark:border-gray-700 shrink-0">
                      <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                        Output
                      </span>
                    </div>
                    <div className="flex-1 min-h-0 p-3 overflow-auto font-mono text-sm bg-white dark:bg-black text-gray-800 dark:text-gray-200">
                      {codeExecutionResult ? (
                        <div>
                          <div className="text-gray-500 dark:text-gray-400 mb-1">
                            $ python main.py
                          </div>
                          <pre className="whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                            {codeExecutionResult}
                          </pre>
                          <div className="flex items-center mt-2">
                            <span className="text-gray-500 dark:text-gray-400">
                              $
                            </span>
                            <span className="w-2 h-4 bg-gray-400 dark:bg-gray-500 ml-1 animate-pulse"></span>
                          </div>
                        </div>
                      ) : (
                        <div className="text-gray-400 dark:text-gray-500 italic">
                          Run code to see output...
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
                </>
              )}
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
      {contextPos && contextTarget && (
        <div
          className="fixed z-50 bg-card border border-gray-200 dark:border-gray-700 rounded shadow-sm text-sm"
          style={{ left: contextPos.x, top: contextPos.y, minWidth: 180 }}
          onMouseLeave={closeContext}
        >
          {/* 生成文件专属：移动到普通文件区 */}
          {!contextTarget.is_dir &&
            contextTarget.path.startsWith("generated/") && (
              <button
                className="block w-full text-left px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800"
                onClick={async () => {
                  await moveToDir(contextTarget.path, "");
                  closeContext();
                }}
              >
                移动到普通文件区
              </button>
            )}
          {!contextTarget.is_dir && (
            <button
              className="block w-full text-left px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800"
              onClick={() => {
                openNode(contextTarget);
                closeContext();
              }}
            >
              预览
            </button>
          )}
          {!contextTarget.is_dir && contextTarget.download_url && (
            <a
              className="block px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800"
              href={contextTarget.download_url}
              download={contextTarget.name}
              onClick={closeContext}
            >
              下载
            </a>
          )}
          <button
            className="block w-full text-left px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800"
            onClick={() => {
              copyToClipboard(contextTarget.path)
                .then((ok) =>
                  toast({
                    description: ok ? "已复制路径" : "复制失败",
                    variant: ok ? undefined : "destructive",
                  })
                )
                .catch(() =>
                  toast({ description: "复制失败", variant: "destructive" })
                );
              closeContext();
            }}
          >
            复制路径
          </button>
          {/* 添加到AI对话 - 仅对文件显示 */}
          {!contextTarget.is_dir && (
            <button
              className="block w-full text-left px-3 py-2 hover:bg-blue-50 dark:hover:bg-blue-950/20 text-blue-600 dark:text-blue-400"
              onClick={() => {
                addFileReference({
                  name: contextTarget.name,
                  path: contextTarget.path,
                });
                closeContext();
              }}
            >
              添加到AI对话
            </button>
          )}
          {!contextTarget.is_dir && (
            <button
              className="block w-full text-left px-3 py-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20"
              onClick={() => {
                setDeleteConfirmPath(contextTarget.path);
                setDeleteIsDir(false);
              }}
            >
              删除文件
            </button>
          )}
          {contextTarget.is_dir && contextTarget.name === "generated" && (
            <button
              className="block w-full text-left px-3 py-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20"
              onClick={() => {
                setDeleteConfirmPath(contextTarget.path);
                setDeleteIsDir(true);
              }}
            >
              删除文件夹
            </button>
          )}
        </div>
      )}
      {/* 全局删除确认弹窗 */}
      {/* 右键移动操作已集成到主菜单顶部，移除单独浮层 */}

      {/* 批量删除确认弹窗 */}
      <AlertDialog open={batchDeleteOpen} onOpenChange={(o) => !o && setBatchDeleteOpen(false)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>删除选中的 {selectedPaths.size} 个文件？</AlertDialogTitle>
            <AlertDialogDescription>
              此操作不可撤销，选中的文件将被永久删除。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 hover:bg-red-700"
              onClick={handleBatchDelete}
            >
              确认删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* 全局删除确认弹窗 */}
      <AlertDialog
        open={!!deleteConfirmPath}
        onOpenChange={(o) => !o && setDeleteConfirmPath(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {deleteIsDir ? "确认删除文件夹？" : "确认删除文件？"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {deleteIsDir
                ? "此操作不可撤销，将删除该文件夹及其所有内容。"
                : "此操作不可撤销，将从 workspace 中移除此文件。"}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeleteConfirmPath(null)}>
              取消
            </AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 hover:bg-red-700"
              onClick={async () => {
                if (deleteConfirmPath) {
                  if (deleteIsDir) {
                    await deleteDir(deleteConfirmPath);
                  } else {
                    await deleteFile(deleteConfirmPath);
                  }
                }
                setDeleteConfirmPath(null);
                closeContext();
              }}
            >
              确认删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      {/* 文件预览弹窗 */}
      <Dialog open={isPreviewOpen} onOpenChange={setIsPreviewOpen}>
        <DialogContent
          style={{
            width: "90vw",
            height: "90vh",
            maxWidth: "90vw",
            maxHeight: "90vh",
          }}
          className=" p-0 overflow-hidden flex flex-col"
        >
          <DialogHeader className="px-4 py-3 border-b border-gray-200 dark:border-gray-800">
            <DialogTitle className="text-sm font-medium truncate">
              {previewTitle}
            </DialogTitle>
          </DialogHeader>
          <div
            ref={previewScrollRef}
            className="w-full flex-1 min-h-0 overflow-auto"
          >
            {previewLoading ? (
              <div className="h-full flex items-center justify-center text-sm text-gray-500">
                Loading...
              </div>
            ) : previewType === "image" ? (
              <div className="p-4 h-full flex items-center justify-center">
                <img
                  src={previewContent}
                  alt={previewTitle}
                  className="max-w-full max-h-full object-contain"
                />
              </div>
            ) : previewType === "pdf" ? (
              <iframe src={previewContent} className="w-full h-full" />
            ) : previewType === "text" ? (
              <div className="h-full min-h-0 p-2">
                <div className="h-full min-h-0 border border-gray-200 dark:border-gray-800 rounded-lg overflow-hidden">
                  <div className="h-full min-h-0">
                    <Editor
                      height="100%"
                      defaultLanguage={guessLanguageByExtension(
                        previewTitle.split(".").pop() || "text"
                      )}
                      language={guessLanguageByExtension(
                        previewTitle.split(".").pop() || "text"
                      )}
                      value={previewContent}
                      theme={isDarkMode ? "vs-dark" : "light"}
                      options={{
                        readOnly: true,
                        wordWrap: "on",
                        minimap: { enabled: false },
                        scrollBeyondLastLine: false,
                        fontFamily:
                          "var(--font-mono), 'Courier New', monospace",
                        fontSize: 14,
                        lineNumbers: "on",
                        automaticLayout: true,
                      }}
                    />
                  </div>
                </div>
              </div>
            ) : previewType === "binary" ? (
              <div className="h-full flex flex-col items-center justify-center p-8">
                <div className="text-6xl mb-4">📄</div>
                <div className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {previewTitle}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400 mb-6 text-center">
                  此文件为二进制格式（如Excel、Word等），无法在线预览
                </div>
                <a
                  className="inline-flex items-center px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                  href={previewDownloadUrl || previewContent}
                  target="_blank"
                  rel="noreferrer"
                  download
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  下载文件
                </a>
              </div>
            ) : (
              <div className="p-4">
                <div className="text-xs text-gray-500 mb-2">
                  无法识别类型，尝试以文本方式预览：
                </div>
                <div className="border border-gray-200 dark:border-gray-800 rounded-lg overflow-hidden">
                  <SyntaxHighlighter
                    language={guessLanguageByExtension(
                      previewTitle.split(".").pop() || "text"
                    )}
                    style={isDarkMode ? oneDark : oneLight}
                    customStyle={{ margin: 0 }}
                    codeTagProps={{
                      style: {
                        fontFamily: "var(--font-mono)",
                        fontSize: "0.875rem",
                      },
                    }}
                  >
                    {previewContent}
                  </SyntaxHighlighter>
                </div>
                <div className="mt-3 text-xs text-gray-500">
                  如显示异常，
                  <a
                    className="underline"
                    href={previewDownloadUrl || previewContent}
                    target="_blank"
                    rel="noreferrer"
                  >
                    点击下载/打开
                  </a>
                </div>
              </div>
            )}
          </div>
          <div className="absolute bottom-4 right-4">
            <Button onClick={handleDownload} size="sm" variant="outline">
              <Download className="h-4 w-4" />
              下载
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* 敏感信息预检弹窗 - 文件上传后自动触发（个保法合规） */}
      <SensitiveCheckDialog
        open={sensitiveDialogOpen}
        result={sensitiveResult}
        fileName={sensitiveFileName}
        onConfirm={() => {
          // 中危：用户确认继续，文件保留
          setSensitiveDialogOpen(false);
          setSensitiveResult(null);
          setSensitiveFilePath("");
        }}
        onReselect={async () => {
          // 高危/重选：删除已上传的敏感文件，提示用户重新上传脱敏版本
          setSensitiveDialogOpen(false);
          if (sensitiveFilePath) {
            await deleteFile(sensitiveFilePath);
          }
          setSensitiveResult(null);
          setSensitiveFilePath("");
          // 重新打开文件选择框
          fileInputRef.current?.click();
        }}
      />
    </>
  );
}

/**
 * ThreePanelInterface - 三栏界面主组件
 * 
 * 使用 ModeProvider 包裹，提供统一的模式状态管理：
 * - interactionMode: 当前交互模式（auto/expert）
 * - historyTaskInteractionMode: 历史任务模式
 * - isExpertMode: 统一的专家模式判断
 * 
 * 优化说明（建议1/2/4）：
 * 1. 使用 useIsExpertMode() Hook 替代重复的判断逻辑
 * 2. 使用 ModeContext 集中管理模式状态，避免 prop drilling
 * 4. 默认模式可通过 defaultMode prop 配置（未来可对接用户偏好）
 */
export function ThreePanelInterface() {
  return (
    <ModeProvider defaultMode="expert">
      <ThreePanelInterfaceInner />
    </ModeProvider>
  );
}
