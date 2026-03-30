// API配置文件

// 验证并规范化 BASE_URL
const normalizeBaseUrl = (url: string | undefined): string => {
  const defaultUrl = 'http://127.0.0.1:8200';
  
  if (!url) return defaultUrl;
  
  // 如果只是端口号，补全为完整URL
  if (/^\d+$/.test(url)) {
    console.warn(`[config] BASE_URL "${url}" 只是端口号，已自动补全为 http://127.0.0.1:${url}`);
    return `http://127.0.0.1:${url}`;
  }
  
  // 如果缺少协议，添加 http://
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    console.warn(`[config] BASE_URL "${url}" 缺少协议，已自动添加 http://`);
    return `http://${url}`;
  }
  
  return url;
};

export const API_URLS = {
  // 基础API地址，使用环境变量或默认值
  BASE_URL: normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL),
  
  // 聊天相关API
  // 使用融合后的Chat API（支持代码执行、任务感知等功能）
  // model参数支持 "config_123" 格式以使用LLM Manager渠道
  CHAT_COMPLETIONS: '/v1/chat/completions',
  // 旧版代理路由（已废弃，保留作为备用参考）
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
  
  // 后端基础URL
  BACKEND_BASE_URL: normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL),
  
  // HTTP文件服务器基础URL（继承原始项目设计）
  FILE_SERVER_BASE: process.env.NEXT_PUBLIC_FILE_SERVER_BASE || 'http://localhost:8100',
};

// 完整的API URL生成函数
export const getApiUrl = (path: string): string => {
  const baseUrl = API_URLS.BASE_URL.endsWith('/') 
    ? API_URLS.BASE_URL.slice(0, -1) 
    : API_URLS.BASE_URL;
  
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