// API配置文件

/**
 * 运行时获取 API 基础 URL
 * 
 * 核心逻辑：
 * - 浏览器环境：使用 window.location.origin（同源部署，自动适配任何域名/IP）
 * - 非浏览器环境（SSR/构建）：回退到 127.0.0.1:8200
 * 
 * 注意：不使用 process.env.NEXT_PUBLIC_* ，因为 Next.js output:'export'
 * 模式会在构建时将其替换为字面量，无法在运行时动态获取。
 */
function getBaseUrl(): string {
  if (typeof window !== 'undefined') {
    return window.location.origin;
  }
  return 'http://127.0.0.1:8200';
}

/**
 * 运行时获取文件服务器 URL
 */
function getFileServerBase(): string {
  if (typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.hostname}:8100`;
  }
  return 'http://localhost:8100';
}

export const API_URLS = {
  // 基础API地址 — getter 确保每次访问都是运行时求值
  get BASE_URL() { return getBaseUrl(); },
  
  // 聊天相关API
  CHAT_COMPLETIONS: '/v1/chat/completions',
  CHAT_COMPLETIONS_PROXY: '/llm-manager/api/proxy/chat/completions',
  STREAM_CHAT: '/chat/stream',
  
  // 工作区相关API
  WORKSPACE_LIST: '/workspace/list',
  WORKSPACE_UPLOAD: '/workspace/upload',
  WORKSPACE_DELETE: '/workspace/delete',
  WORKSPACE_DELETE_FILE: '/workspace/file',
  WORKSPACE_DELETE_DIR: '/workspace/file',
  WORKSPACE_UPLOAD_TO: '/workspace/upload',
  WORKSPACE_PREVIEW: '/workspace/preview',
  WORKSPACE_CREATE_FOLDER: '/workspace/create_folder',
  WORKSPACE_FILES: '/workspace/files',
  WORKSPACE_TREE: '/workspace/tree',
  WORKSPACE_CLEAR: '/workspace/clear',
  
  // 执行相关API
  EXECUTE_CODE: '/execute/code',
  
  // 导出相关API
  EXPORT_MARKDOWN: '/export/markdown',
  EXPORT_REPORT: '/export/report',
  
  // 模型相关API
  MODELS_LIST: '/llm-manager/api/models',
};

// API配置选项
export const API_CONFIG = {
  // 请求超时时间（毫秒）
  TIMEOUT: 30000,
  
  // 重试次数
  RETRY_COUNT: 3,
  
  // 启用流式响应
  ENABLE_STREAMING: true,
  
  // 后端基础URL（getter，运行时动态获取）
  get BACKEND_BASE_URL() { return getBaseUrl(); },
  
  // HTTP文件服务器基础URL
  get FILE_SERVER_BASE() { return getFileServerBase(); },
};

// 完整的API URL生成函数（运行时动态计算）
export const getApiUrl = (path: string): string => {
  const baseUrl = getBaseUrl();
  const apiPath = path.startsWith('/') ? path : `/${path}`;
  return `${baseUrl}${apiPath}`;
};

// =============================================================================
// 认证相关
// =============================================================================

const AUTH_STORAGE_KEY = 'creditwise_auth';

/**
 * 获取保存的 Basic Auth 凭证
 */
function getStoredAuth(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(AUTH_STORAGE_KEY);
}

/**
 * 弹出登录提示，保存凭证到 localStorage
 * 返回 Base64 编码的凭证
 */
function promptLogin(): string | null {
  const username = window.prompt('CreditWise 登录 — 用户名:');
  if (!username) return null;
  const password = window.prompt('密码:');
  if (password === null) return null;
  const encoded = btoa(`${username}:${password}`);
  localStorage.setItem(AUTH_STORAGE_KEY, encoded);
  return encoded;
}

/**
 * 带认证的 fetch 封装
 * 
 * - 自动从 localStorage 读取 Basic Auth 凭证并注入 Authorization header
 * - 首次请求或凭证过期（401）时，弹出浏览器 prompt 让用户输入账号密码
 * - 用法与原生 fetch 完全一致
 * 
 * @example
 *   const res = await authFetch(getApiUrl('/sop/tasks'));
 *   const res = await authFetch(getApiUrl('/v1/chat/completions'), { method: 'POST', body: ... });
 */
export const authFetch = async (url: string | URL | Request, init?: RequestInit): Promise<Response> => {
  let auth = getStoredAuth();

  // 如果没有保存的凭证，先弹出登录提示
  if (!auth) {
    auth = promptLogin();
    if (!auth) {
      return new Response(JSON.stringify({ detail: 'Login cancelled' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  }

  // 注入 Authorization header
  const headers = new Headers(init?.headers);
  headers.set('Authorization', `Basic ${auth}`);

  const response = await fetch(url, {
    ...init,
    headers,
  });

  // 如果返回 401，说明凭证无效，清除并重试一次
  if (response.status === 401) {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    const newAuth = promptLogin();
    if (!newAuth) return response;

    const retryHeaders = new Headers(init?.headers);
    retryHeaders.set('Authorization', `Basic ${newAuth}`);
    return fetch(url, {
      ...init,
      headers: retryHeaders,
    });
  }

  return response;
};
