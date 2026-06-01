// API配置文件

/**
 * 运行时获取 API 基础 URL
 * 
 * 核心逻辑：
 * - 生产模式（同源部署，端口8200）：使用 window.location.origin
 * - 开发模式（Next.js dev server，端口3000）：使用 127.0.0.1:8200
 * - 非浏览器环境（SSR/构建）：回退到 127.0.0.1:8200
 */
function getBaseUrl(): string {
  if (typeof window !== 'undefined') {
    const port = window.location.port;
    // 生产模式：前端和 API 同源（都在 8200）
    if (port === '8200' || port === '') {
      return window.location.origin;
    }
    // 开发模式：前端在 3000，API 在 8200
    return `${window.location.protocol}//${window.location.hostname}:8200`;
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
export function getStoredAuth(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(AUTH_STORAGE_KEY);
}

/**
 * 保存凭证到 localStorage
 */
export function saveAuth(username: string, password: string): string {
  const encoded = btoa(`${username}:${password}`);
  localStorage.setItem(AUTH_STORAGE_KEY, encoded);
  return encoded;
}

/**
 * 清除已保存的凭证
 */
export function clearAuth(): void {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

// -----------------------------------------------------------------------------
// 登录对话框回调注册
// 允许 LoginDialog 组件注册一个异步弹窗函数，供 authFetch 调用
// -----------------------------------------------------------------------------

type LoginCallback = () => Promise<string | null>;
let _loginCallback: LoginCallback | null = null;

export function registerLoginCallback(cb: LoginCallback): void {
  _loginCallback = cb;
}

async function promptLogin(): Promise<string | null> {
  if (_loginCallback) {
    return _loginCallback();
  }
  // 降级：登录组件尚未挂载时用 window.prompt（启动瞬间的极短窗口期）
  const username = window.prompt('CreditWise 登录 — 用户名:');
  if (!username) return null;
  const password = window.prompt('密码:');
  if (password === null) return null;
  return saveAuth(username, password);
}

/**
 * 带认证的 fetch 封装
 *
 * - 自动从 localStorage 读取 Basic Auth 凭证并注入 Authorization header
 * - 首次请求或凭证过期（401）时，通过 LoginDialog 弹窗让用户输入账号密码
 * - 用法与原生 fetch 完全一致
 *
 * @example
 *   const res = await authFetch(getApiUrl('/sop/tasks'));
 *   const res = await authFetch(getApiUrl('/v1/chat/completions'), { method: 'POST', body: ... });
 */
export const authFetch = async (url: string | URL | Request, init?: RequestInit): Promise<Response> => {
  let auth = getStoredAuth();

  // 如果没有保存的凭证，弹出登录对话框
  if (!auth) {
    auth = await promptLogin();
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

  const response = await fetch(url, { ...init, headers });

  // 如果返回 401，说明凭证无效或已过期，清除后重新登录
  if (response.status === 401) {
    clearAuth();
    const newAuth = await promptLogin();
    if (!newAuth) return response;

    const retryHeaders = new Headers(init?.headers);
    retryHeaders.set('Authorization', `Basic ${newAuth}`);
    return fetch(url, { ...init, headers: retryHeaders });
  }

  return response;
};

// -----------------------------------------------------------------------------
// 全局 fetch 拦截器
//
// 目的：所有组件中的裸 fetch() 调用（未使用 authFetch）也能自动携带凭证，
// 避免后端返回 401 + WWW-Authenticate 触发浏览器原生弹窗。
//
// 策略：
//   - 只对本站请求（相对路径 或 同 origin）注入 Authorization
//   - 凭证已存在时注入；不存在时不注入（不触发登录弹窗，让 authFetch 负责登录流程）
//   - 不拦截已带 Authorization 头的请求（authFetch 自身的调用）
// -----------------------------------------------------------------------------

if (typeof window !== 'undefined') {
  const _originalFetch = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const urlStr = typeof input === 'string'
      ? input
      : input instanceof URL
        ? input.href
        : (input as Request).url;

    const isSameOrigin =
      urlStr.startsWith('/') ||
      urlStr.startsWith(window.location.origin);

    if (isSameOrigin) {
      const existingHeaders = new Headers(init?.headers);
      // 仅在尚未带 Authorization 且有已保存凭证时注入
      if (!existingHeaders.has('Authorization')) {
        const auth = getStoredAuth();
        if (auth) {
          existingHeaders.set('Authorization', `Basic ${auth}`);
          return _originalFetch(input, { ...init, headers: existingHeaders });
        }
      }
    }
    return _originalFetch(input, init);
  };
}
