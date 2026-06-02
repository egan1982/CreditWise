/**
 * SOP任务服务层
 * 提供与后端SOP API的交互功能
 */

import { getApiUrl, authFetch } from './config';

// =============================================================================
// 缓存配置与类型
// =============================================================================

/** 任务执行结果缓存数据结构 */
interface TaskResultCacheEntry {
  data: {
    record_id: string;
    result: Record<string, any>;
    stages?: Record<string, any>;
  };
  cachedAt: number;  // 缓存时间戳
}

/** 任务历史详情缓存数据结构 */
interface TaskDetailCacheEntry {
  detail: TaskHistoryDetail;
  cachedAt: number;
}

/** 缓存有效期：30分钟（避免数据过期） */
const CACHE_TTL_MS = 30 * 60 * 1000;

/** 任务执行结果缓存（内存） */
const taskResultCache = new Map<string, TaskResultCacheEntry>();

/** 任务历史详情缓存（内存） */
const taskDetailCache = new Map<string, TaskDetailCacheEntry>();

// =============================================================================
// 缓存工具函数
// =============================================================================

/**
 * 检查缓存是否有效
 */
function isCacheValid(cachedAt: number): boolean {
  return Date.now() - cachedAt < CACHE_TTL_MS;
}

/**
 * 清除指定记录的缓存
 * 在删除记录或数据更新时调用
 */
export function clearTaskCache(recordId: string): void {
  taskResultCache.delete(recordId);
  taskDetailCache.delete(recordId);
  console.log('[SOP Cache] Cleared cache for recordId:', recordId);
}

/**
 * 清除所有任务缓存
 * 在需要强制刷新时调用
 */
export function clearAllTaskCache(): void {
  taskResultCache.clear();
  taskDetailCache.clear();
  console.log('[SOP Cache] Cleared all task cache');
}

/**
 * 获取缓存统计信息（调试用）
 */
export function getTaskCacheStats(): { resultCount: number; detailCount: number } {
  return {
    resultCount: taskResultCache.size,
    detailCount: taskDetailCache.size,
  };
}

// =============================================================================
// 类型定义
// =============================================================================

// 交互模式
export type InteractionMode = 'auto' | 'expert';

export interface TaskStage {
  id: string;
  name: string;
  progress_weight: number;
}

export interface TaskParam {
  name: string;
  type: string;
  label: string;
  label_en?: string;
  description?: string;
  required?: boolean;
  default?: any;
  options?: Array<{ value: string; label: string }>;
  min?: number;
  max?: number;
  step?: number;
  show_when?: Record<string, any>;
  allow_empty?: boolean;
  group?: string;  // 参数分组标识，同组参数将在一行显示
  stage?: string;  // 参数所属阶段ID，用于按阶段分组展示
  advanced?: boolean;  // 是否为调优参数，在阶段内二级折叠显示
}

export interface TaskOutput {
  id: string;
  name: string;
  type: string;
  show_when?: Record<string, any>;
}

export interface TaskMeta {
  task_id: string;
  task_name: string;
  task_name_en: string;
  description: string;
  category: string;
  icon: string;
  estimated_time: string;
  stages: TaskStage[];
  required_params: TaskParam[];
  optional_params: TaskParam[];
  outputs: TaskOutput[];
}

export interface TaskListItem {
  task_id: string;
  task_name: string;
  task_name_en: string;
  description: string;
  category: string;
  icon: string;
}

export interface DataColumn {
  name: string;
  dtype: string;
  sample_values: string[];
  null_count: number;
  null_rate: number;
}

export interface DataPreviewResponse {
  columns: DataColumn[];
  preview_data: Record<string, any>[];
  total_rows: number;
  total_columns: number;
}

export interface ParamMeta {
  name: string;
  label: string;
  type: string;  // number, select, checkbox, column_select, etc.
  default?: any;
  description?: string;
  options?: Array<{ value: string; label: string }>;
  // 支持顶层字段（与 TaskParam 一致）和 validation 嵌套（向后兼容）
  min?: number;
  max?: number;
  step?: number;
  validation?: { min?: number; max?: number; step?: number };
  required?: boolean;
  allow_empty?: boolean;  // 是否允许为空（可选参数标识）
  show_when?: Record<string, any>;  // 条件显示
  advanced?: boolean;  // 是否为调优参数，在阶段内二级折叠显示
}

export interface StageProgress {
  stage_id: string;
  stage_name: string;
  status: string;
  progress: number;
  message: string;
  logs?: string[];  // 阶段日志列表
  code?: string;    // 阶段对应的Python伪代码
  output_preview?: Record<string, any>;  // 阶段输出预览
  params?: Record<string, any>;  // 阶段可编辑参数
  params_used?: Record<string, any>;  // 阶段使用的配置参数（只读）
  params_meta?: ParamMeta[];  // 参数元数据（用于渲染表单）
  execution_time_ms?: number | null;  // 阶段执行时间（毫秒）
  started_at?: string | null;  // 阶段开始时间
  completed_at?: string | null;  // 阶段完成时间
}

export interface ExecutionStatus {
  execution_id: string;
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused' | 'stopped';  // 添加'stopped'以匹配后端TaskStatus枚举
  current_stage: string;
  overall_progress: number;
  message: string;
  started_at: string | null;
  completed_at: string | null;
  stages: Record<string, StageProgress>;
  stage_order?: string[];  // 阶段执行顺序
  record_id?: string | null;  // Phase 9: 添加record_id用于AI分析缓存
  file_path?: string | null;  // 任务使用的数据文件路径
}

export interface ExecutionResult {
  execution_id: string;
  task_id: string;
  status: string;
  record_id?: string | null;  // 任务记录ID，用于获取历史stages数据
  outputs: Record<string, any>;
  errors: string[];
}

// 任务控制相关类型
export interface TaskControlResponse {
  success: boolean;
  message: string;
  execution_id: string;
  current_status?: string;
}

// 任务历史相关类型
export interface TaskHistoryItem {
  record_id: string;
  task_type: string;
  task_category: string;
  execution_id: string | null;
  session_id: string | null;
  interaction_mode: string;
  status: string;
  progress: number;
  current_stage: string | null;
  message: string | null;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
}

export interface TaskHistoryDetail extends TaskHistoryItem {
  params: Record<string, any> | null;
  inputs_summary: Record<string, any> | null;
  outputs_summary: Record<string, any> | null;
  stages: Record<string, any> | null;
  error_message: string | null;
}

export interface TaskHistoryListResponse {
  total: number;
  limit: number;
  offset: number;
  records: TaskHistoryItem[];
}

export interface TaskStatistics {
  total: number;
  completed: number;
  failed: number;
  stopped: number;
  running: number;
  paused: number;
  success_rate: number;
  avg_duration_seconds: number;
  period_days: number;
}

export interface TaskHistoryQuery {
  task_type?: string;
  task_category?: string;
  session_id?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}

// =============================================================================
// SOP服务类
// =============================================================================

class SOPService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = '';
  }

  /**
   * 获取所有可用的SOP任务类型
   */
  async getAvailableTasks(): Promise<TaskListItem[]> {
    const response = await authFetch(getApiUrl('/sop/tasks'));
    if (!response.ok) {
      throw new Error(`Failed to fetch tasks: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 获取指定任务的详细定义
   */
  async getTaskDefinition(taskId: string): Promise<TaskMeta> {
    const response = await authFetch(getApiUrl(`/sop/tasks/${taskId}`));
    if (!response.ok) {
      throw new Error(`Failed to fetch task definition: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 预览数据文件
   */
  async previewData(filePath: string, rows: number = 10, sessionId: string): Promise<DataPreviewResponse> {
    const response = await authFetch(getApiUrl('/sop/data/preview'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        file_path: filePath, 
        rows,
        session_id: sessionId
      }),
    });
    if (!response.ok) {
      throw new Error(`Failed to preview data: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 执行SOP任务
   * 
   * 使用 Pipeline 执行引擎，LLM 作为智能入口（参数推断器）
   */
  async executeTask(
    taskId: string,
    sessionId: string,
    filePath: string,
    params: Record<string, any>,
    interactionMode: 'auto' | 'expert' = 'auto',
    model: string = 'deepseek-chat',
    apiBase: string = 'http://localhost:8200/v1',
    systemPrompt?: string
  ): Promise<{ execution_id: string; task_id: string; status: string; message: string }> {
    const response = await authFetch(getApiUrl('/sop/execute'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_id: taskId,
        session_id: sessionId,
        file_path: filePath,
        params,
        interaction_mode: interactionMode,
        model: model,
        api_base: apiBase,
        system_prompt: systemPrompt || undefined,
      }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to execute task: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 获取任务执行状态
   */
  async getExecutionStatus(executionId: string): Promise<ExecutionStatus> {
    const response = await authFetch(getApiUrl(`/sop/status/${executionId}`));
    if (!response.ok) {
      throw new Error(`Failed to get execution status: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 获取任务执行结果
   */
  async getExecutionResult(executionId: string): Promise<ExecutionResult> {
    const response = await authFetch(getApiUrl(`/sop/results/${executionId}`));
    if (!response.ok) {
      throw new Error(`Failed to get execution result: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 订阅任务状态更新（SSE）
   */
  subscribeTaskStatus(
    executionId: string,
    onUpdate: (status: ExecutionStatus) => void,
    onComplete: (status: ExecutionStatus) => void,
    onError: (error: Error) => void
  ): EventSource {
    const eventSource = new EventSource(
      getApiUrl(`/sop/status/${executionId}/stream`)
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ExecutionStatus;
        if (data.status === 'completed' || data.status === 'failed') {
          onComplete(data);
          eventSource.close();
        } else {
          onUpdate(data);
        }
      } catch (e) {
        console.error('Failed to parse SSE data:', e);
      }
    };

    eventSource.onerror = (error) => {
      onError(new Error('SSE connection error'));
      eventSource.close();
    };

    return eventSource;
  }

  /**
   * 构建SOP Prompt
   */
  async buildSOPPrompt(
    taskId: string,
    params: Record<string, any>,
    workspaceFilesInfo: string = ''
  ): Promise<string> {
    const response = await authFetch(getApiUrl('/sop/prompt/build'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_id: taskId,
        params,
        workspace_files_info: workspaceFilesInfo,
      }),
    });
    if (!response.ok) {
      throw new Error(`Failed to build SOP prompt: ${response.status}`);
    }
    const data = await response.json();
    return data.prompt;
  }

  // =============================================================================
  // 任务控制方法
  // =============================================================================

  /**
   * 暂停任务执行
   */
  async pauseExecution(executionId: string): Promise<TaskControlResponse> {
    const response = await authFetch(getApiUrl(`/sop/executions/${executionId}/pause`), {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to pause execution: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 停止任务执行
   */
  async stopExecution(executionId: string): Promise<TaskControlResponse> {
    const response = await authFetch(getApiUrl(`/sop/executions/${executionId}/stop`), {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to stop execution: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 恢复已暂停的任务
   */
  async resumeExecution(executionId: string): Promise<TaskControlResponse> {
    const response = await authFetch(getApiUrl(`/sop/executions/${executionId}/resume`), {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to resume execution: ${response.status}`);
    }
    return response.json();
  }

  // =============================================================================
  // 任务历史方法
  // =============================================================================

  /**
   * 查询任务历史记录列表
   */
  async getTaskHistory(query: TaskHistoryQuery = {}): Promise<TaskHistoryListResponse> {
    const params = new URLSearchParams();
    if (query.task_type) params.set('task_type', query.task_type);
    if (query.task_category) params.set('task_category', query.task_category);
    if (query.session_id) params.set('session_id', query.session_id);
    if (query.status) params.set('status', query.status);
    if (query.start_date) params.set('start_date', query.start_date);
    if (query.end_date) params.set('end_date', query.end_date);
    if (query.limit) params.set('limit', String(query.limit));
    if (query.offset) params.set('offset', String(query.offset));

    const response = await authFetch(getApiUrl(`/sop/history?${params.toString()}`));
    if (!response.ok) {
      throw new Error(`Failed to get task history: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 获取任务历史记录详情（带缓存）
   * @param recordId 记录ID
   * @param forceRefresh 是否强制刷新缓存
   */
  async getTaskHistoryDetail(recordId: string, forceRefresh: boolean = false): Promise<TaskHistoryDetail> {
    // 检查缓存
    if (!forceRefresh) {
      const cached = taskDetailCache.get(recordId);
      if (cached && isCacheValid(cached.cachedAt)) {
        console.log('[SOP Cache] Hit taskDetailCache for recordId:', recordId);
        return cached.detail;
      }
    }
    
    // 缓存未命中或强制刷新，调用 API
    console.log('[SOP Cache] Miss taskDetailCache, fetching from API:', recordId);
    const response = await authFetch(getApiUrl(`/sop/history/${recordId}`));
    if (!response.ok) {
      throw new Error(`Failed to get task history detail: ${response.status}`);
    }
    const detail = await response.json();
    
    // 存入缓存
    taskDetailCache.set(recordId, {
      detail,
      cachedAt: Date.now(),
    });
    
    return detail;
  }

  /**
   * 获取历史任务的完整执行结果（带缓存）
   * 返回结果中同时包含stages数据（用于"样本及特征"Tab）
   * @param recordId 记录ID
   * @param forceRefresh 是否强制刷新缓存
   */
  async getTaskHistoryResult(recordId: string, forceRefresh: boolean = false): Promise<{ record_id: string; result: Record<string, any>; stages?: Record<string, any> }> {
    // 检查缓存
    if (!forceRefresh) {
      const cached = taskResultCache.get(recordId);
      if (cached && isCacheValid(cached.cachedAt)) {
        console.log('[SOP Cache] Hit taskResultCache for recordId:', recordId);
        // 直接返回缓存的完整数据对象，确保与 API 响应一致
        return cached.data;
      }
    }
    
    // 缓存未命中或强制刷新，调用 API
    console.log('[SOP Cache] Miss taskResultCache, fetching from API:', recordId);
    const response = await authFetch(getApiUrl(`/sop/history/${recordId}/result`));
    if (!response.ok) {
      throw new Error(`Failed to get task history result: ${response.status}`);
    }
    const data = await response.json();
    
    // 存入缓存（保存完整的 API 响应对象）
    taskResultCache.set(recordId, {
      data: data,
      cachedAt: Date.now(),
    });
    
    return data;
  }

  /**
   * 删除历史记录（同时清除缓存）
   */
  async deleteTaskHistory(recordId: string): Promise<{ success: boolean; message: string }> {
    const response = await authFetch(getApiUrl(`/sop/history/${recordId}`), {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to delete task history: ${response.status}`);
    }
    
    // 删除成功后清除缓存
    clearTaskCache(recordId);
    
    return response.json();
  }

  /**
   * 获取任务统计信息
   */
  async getTaskStatistics(
    taskType?: string,
    taskCategory?: string,
    days: number = 30
  ): Promise<TaskStatistics> {
    const params = new URLSearchParams();
    if (taskType) params.set('task_type', taskType);
    if (taskCategory) params.set('task_category', taskCategory);
    params.set('days', String(days));

    const response = await authFetch(getApiUrl(`/sop/statistics?${params.toString()}`));
    if (!response.ok) {
      throw new Error(`Failed to get task statistics: ${response.status}`);
    }
    return response.json();
  }

  // =============================================================================
  // 专家模式方法
  // =============================================================================

  /**
   * 创建专家模式执行上下文
   */
  async createExpertExecution(
    taskId: string,
    sessionId: string,
    filePath?: string,
    params?: Record<string, any>
  ): Promise<ExpertExecutionResponse> {
    const response = await authFetch(getApiUrl('/sop/expert/create'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_id: taskId,
        session_id: sessionId,
        file_path: filePath,
        params: params || {},
      }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to create expert execution: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 获取专家模式执行上下文
   */
  async getExpertExecution(executionId: string): Promise<ExpertExecutionResponse> {
    const response = await authFetch(getApiUrl(`/sop/expert/${executionId}`));
    if (!response.ok) {
      throw new Error(`Failed to get expert execution: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 执行专家模式单个阶段
   */
  async executeExpertStage(executionId: string, stageId: string): Promise<{ message: string; status: string }> {
    const response = await authFetch(getApiUrl(`/sop/expert/${executionId}/stages/${stageId}/execute`), {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to execute stage: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 跳过专家模式阶段
   */
  async skipExpertStage(executionId: string, stageId: string, reason?: string): Promise<ExpertStageResponse> {
    const params = new URLSearchParams();
    if (reason) params.set('reason', reason);
    
    const response = await authFetch(getApiUrl(`/sop/expert/${executionId}/stages/${stageId}/skip?${params.toString()}`), {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to skip stage: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 重置专家模式阶段
   */
  async resetExpertStage(executionId: string, stageId: string): Promise<ExpertStageResponse> {
    const response = await authFetch(getApiUrl(`/sop/expert/${executionId}/stages/${stageId}/reset`), {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to reset stage: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 更新专家模式阶段参数
   */
  async updateExpertStageParams(
    executionId: string,
    stageId: string,
    params: Record<string, any>
  ): Promise<ExpertStageResponse> {
    const response = await authFetch(getApiUrl(`/sop/expert/${executionId}/stages/${stageId}/params`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ params }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to update stage params: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 更新专家模式阶段代码
   */
  async updateExpertStageCode(
    executionId: string,
    stageId: string,
    code: string
  ): Promise<ExpertStageResponse> {
    const response = await authFetch(getApiUrl(`/sop/expert/${executionId}/stages/${stageId}/code`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to update stage code: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 获取专家模式阶段结果
   */
  async getExpertStageResult(executionId: string, stageId: string): Promise<ExpertStageResultResponse> {
    const response = await authFetch(getApiUrl(`/sop/expert/${executionId}/stages/${stageId}/result`));
    if (!response.ok) {
      throw new Error(`Failed to get stage result: ${response.status}`);
    }
    return response.json();
  }

  // =============================================================================
  // Phase 6: 阶段重试和恢复方法
  // =============================================================================

  /**
   * 重试指定阶段
   * 
   * 重置该阶段及后续阶段的状态，然后恢复执行。
   * 仅在任务暂停状态下可用。
   */
  async retryStage(
    executionId: string,
    stageId: string,
    newParams?: Record<string, any>,
    retryReason?: string
  ): Promise<StageRetryResponse> {
    const response = await authFetch(getApiUrl(`/sop/executions/${executionId}/stages/${stageId}/retry`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_params: newParams, retry_reason: retryReason || null }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to retry stage: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 重置指定阶段状态为 pending
   * 
   * 仅重置状态，不触发执行。
   */
  async resetStage(executionId: string, stageId: string): Promise<TaskControlResponse> {
    const response = await authFetch(getApiUrl(`/sop/executions/${executionId}/stages/${stageId}/reset`), {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to reset stage: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 获取执行的所有检查点
   */
  async getExecutionCheckpoints(executionId: string): Promise<ExecutionCheckpointsResponse> {
    const response = await authFetch(getApiUrl(`/sop/executions/${executionId}/checkpoints`));
    if (!response.ok) {
      throw new Error(`Failed to get checkpoints: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 列出可恢复的任务
   */
  async getRecoverableExecutions(sessionId?: string): Promise<RecoverableExecutionsResponse> {
    const params = new URLSearchParams();
    if (sessionId) params.set('session_id', sessionId);
    
    const response = await authFetch(getApiUrl(`/sop/executions/recoverable?${params.toString()}`));
    if (!response.ok) {
      throw new Error(`Failed to get recoverable executions: ${response.status}`);
    }
    return response.json();
  }

  /**
   * 获取任务恢复信息
   */
  async getRecoveryInfo(executionId: string): Promise<RecoveryInfoResponse> {
    const response = await authFetch(getApiUrl(`/sop/executions/${executionId}/recovery-info`));
    if (!response.ok) {
      throw new Error(`Failed to get recovery info: ${response.status}`);
    }
    return response.json();
  }
}

// 专家模式相关类型
export interface ExpertStageData {
  stage_id: string;
  stage_name: string;
  state: string;
  params: Record<string, any>;
  code?: string;
  code_modified?: boolean;
  params_modified?: boolean;
  has_outputs?: boolean;
  error?: string | null;
  logs?: string[];
  started_at?: string | null;
  completed_at?: string | null;
}

export interface ExpertExecutionResponse {
  execution_id: string;
  task_id: string;
  session_id: string;
  current_stage_index: number;
  current_stage_id: string | null;
  overall_status: string;
  stage_order: string[];
  stages: Record<string, ExpertStageData>;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface ExpertStageResponse {
  success: boolean;
  message: string;
  stage: ExpertStageData;
}

export interface ExpertStageResultResponse {
  execution_id: string;
  stage_id: string;
  has_result: boolean;
  result: Record<string, any> | null;
}

// Phase 6: 阶段重试和恢复相关类型
export interface StageRetryResponse {
  success: boolean;
  message: string;
  execution_id: string;
  retry_stage_id: string;
  previous_stage_id?: string;
  needs_restart?: boolean;  // 是否需要重新启动任务（Pipeline模式下为true）
}

export interface StageCheckpointItem {
  stage_id: string;
  stage_index: number;
  stage_status: string;
  outputs_summary?: Record<string, any>;
  params?: Record<string, any>;
  started_at?: string;
  completed_at?: string;
}

export interface ExecutionCheckpointsResponse {
  execution_id: string;
  checkpoints: StageCheckpointItem[];
}

export interface RecoverableExecutionItem {
  execution_id: string;
  task_id: string;
  session_id?: string;
  record_id?: string;
  status: string;
  pause_stage_id?: string;
  current_stage_id?: string;
  completed_stages_count: number;
  paused_at?: string;
  created_at?: string;
}

export interface RecoverableExecutionsResponse {
  executions: RecoverableExecutionItem[];
}

export interface RecoveryInfoResponse {
  can_resume: boolean;
  reason?: string;
  execution_id: string;
  resume_stage_id?: string;
  completed_stages?: string[];
}

// =============================================================================
// Overall AI Analysis Types
// =============================================================================

export interface OverallAnalysis {
  analysis_text: string;
  model_used?: string;
  task_type?: string;
  created_at?: string;
  updated_at?: string;
}

export interface OverallAnalysisResponse {
  success: boolean;
  exists: boolean;
  analysis: OverallAnalysis | null;
}

export interface BuildPromptResponse {
  success: boolean;
  prompt: string;
  data_description: string;
  config: {
    task_name: string;
    max_words: number;
    focus_areas: string[];
  };
}

// =============================================================================
// Overall AI Analysis Service Functions
// =============================================================================

/**
 * 获取任务整体AI分析结果
 */
export async function getOverallAnalysis(recordId: string): Promise<OverallAnalysisResponse> {
  const response = await authFetch(getApiUrl(`/sop/history/${recordId}/overall-analysis`));
  if (!response.ok) {
    throw new Error(`Failed to get overall analysis: ${response.status}`);
  }
  return response.json();
}

/**
 * 保存任务整体AI分析结果
 */
export async function saveOverallAnalysis(
  recordId: string,
  taskType: string,
  analysisText: string,
  modelUsed?: string
): Promise<{ success: boolean; message: string }> {
  const response = await authFetch(getApiUrl(`/sop/history/${recordId}/overall-analysis`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      record_id: recordId,
      task_type: taskType,
      analysis_text: analysisText,
      model_used: modelUsed
    })
  });
  if (!response.ok) {
    throw new Error(`Failed to save overall analysis: ${response.status}`);
  }
  return response.json();
}

/**
 * 删除任务整体AI分析结果
 */
export async function deleteOverallAnalysis(recordId: string): Promise<{ success: boolean; message: string }> {
  const response = await authFetch(getApiUrl(`/sop/history/${recordId}/overall-analysis`), {
    method: 'DELETE'
  });
  if (!response.ok) {
    throw new Error(`Failed to delete overall analysis: ${response.status}`);
  }
  return response.json();
}

/**
 * 构建整体分析Prompt
 */
export async function buildOverallAnalysisPrompt(
  recordId: string,
  taskType: string,
  executionId?: string
): Promise<BuildPromptResponse> {
  const response = await authFetch(getApiUrl('/sop/overall-analysis/build-prompt'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      record_id: recordId,
      task_type: taskType,
      execution_id: executionId
    })
  });
  if (!response.ok) {
    throw new Error(`Failed to build prompt: ${response.status}`);
  }
  return response.json();
}

// 导出单例
export const sopService = new SOPService();
export default sopService;
