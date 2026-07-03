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

/**
 * 运行时获取 LLM Manager 管理页面入口 URL
 *
 * 用户管理模块 批次2 补充修复（2026-07-02）：头像菜单「LLM渠道管理」此前硬编码跳转
 * 相对路径 `/llm-manager`，在开发模式（Next.js dev server，端口3000）下会被解析为
 * `http://localhost:3000/llm-manager`——3000 是纯前端 dev server，没有这个路由，
 * 导致点击后地址错误/404。
 *
 * 与 getBaseUrl() 保持同一套判断逻辑：
 * - 生产模式（同源部署，端口8200）：`${origin}/llm-manager`（同源子路径，由主API
 *   以 as_subapp 挂载）
 * - 开发模式（端口3000）：LLM Manager 有独立的 Vite dev server（端口3001），
 *   跳转到该端口根路径，而不是拼接 /llm-manager 前缀
 */
export function getLlmManagerUrl(): string {
  if (typeof window !== 'undefined') {
    const port = window.location.port;
    if (port === '8200' || port === '') {
      return `${window.location.origin}/llm-manager`;
    }
    return `${window.location.protocol}//${window.location.hostname}:3001`;
  }
  return 'http://127.0.0.1:8200/llm-manager';
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

// 用户管理模块 批次2 补充加固（2026-07-02）：并发 401 去重。
//
// 背景：页面加载时 Files/Tree/TaskType 等多个接口几乎同时发起请求。一旦当前凭证失效
// （如刚改完密码、浏览器缓存的旧凭证过期），这些请求会【同时】收到 401，每个都独立调用
// promptLogin() → LoginDialog 的回调。但 LoginDialog.tsx 内部只有一个共享的 resolveRef
// 存放"登录成功后要通知谁"——每次新调用都会覆盖上一次的 resolveRef，导致除最后一次调用外，
// 其余更早的 authFetch 调用永远等不到 resolve，对应的 await 永久挂起，表现为界面上某些区域
// （Files/TaskType）一直转圈，即使随后已用正确密码登录成功，那些"掉队"的请求也不会自愈。
//
// 修复：让并发的多次 promptLogin() 调用共享同一个 pending Promise，只弹一次登录框，
// 全部等待者拿到同一个结果后各自继续重试自己的原始请求。
let _pendingLoginPromise: Promise<string | null> | null = null;

async function promptLogin(): Promise<string | null> {
  if (_pendingLoginPromise) {
    return _pendingLoginPromise;
  }

  const run = async (): Promise<string | null> => {
    if (_loginCallback) {
      return _loginCallback();
    }
    // 降级：登录组件尚未挂载时用 window.prompt（启动瞬间的极短窗口期）
    const username = window.prompt('CreditWise 登录 — 用户名:');
    if (!username) return null;
    const password = window.prompt('密码:');
    if (password === null) return null;
    return saveAuth(username, password);
  };

  _pendingLoginPromise = run().finally(() => {
    _pendingLoginPromise = null;
  });
  return _pendingLoginPromise;
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

  // 注入 Authorization header（如有缓存凭证）
  const headers = new Headers(init?.headers);
  if (auth) {
    headers.set('Authorization', `Basic ${auth}`);
  }

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
// 目的：所有组件中的裸 fetch() 调用（未使用 authFetch）也能自动携带凭证 + 支持
// 401 时弹登录框重试，效果与显式调用 authFetch 完全一致。
//
// 用户管理模块 批次2 补充加固（2026-07-02）：修复"开发模式下历史记录/报告导出等
// 使用裸 fetch(getApiUrl(...)) 的调用点一直加载失败"问题。
// 背景：`getApiUrl()` 在开发模式（Next.js dev server 3000，后端 8200）下返回的是
// **跨域**绝对地址（`getBaseUrl()`，如 `http://127.0.0.1:8200/xxx`），此前的
// `isSameOrigin` 判断只认「相对路径」或「与当前页面同源」，跨域到 8200 的请求会被
// 判定为"非本站请求"而不注入任何认证信息——请求直接收到 401，而裸 fetch 调用点
// 大多只做了`if (!response.ok) throw ...`，没有登录重试逻辑，于是表现为对应模块
// （历史记录列表/删除、报告导出、文档预检等十余处）直接报"加载失败"。生产同源部署
// （3000/8200合一）下不会触发，因为那时天然满足同源判断。
//
// 策略：
//   - "信任的后端"判定扩大为：相对路径 / 与当前页面同源 / 与 getBaseUrl() 同源
//     （即 getApiUrl() 实际会请求到的地址，无论是否与当前页面同源）
//   - 命中且已有缓存凭证时注入 Authorization
//   - 命中且响应 401 时：清除失效凭证 → 弹登录框（复用 promptLogin，已做并发去重，
//     见上方 §二十三 说明）→ 用新凭证重试一次；用户取消则原样返回 401 响应
//   - 不拦截已带 Authorization 头的请求（authFetch 自身的调用，避免与其自身的
//     401 重试逻辑重复触发两次登录框；分析见下方“已知交互”）
// -----------------------------------------------------------------------------

if (typeof window !== 'undefined') {
  const _originalFetch = window.fetch.bind(window);
  const backendOrigin = getBaseUrl();

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const urlStr = typeof input === 'string'
      ? input
      : input instanceof URL
        ? input.href
        : (input as Request).url;

    const isTrustedBackend =
      urlStr.startsWith('/') ||
      urlStr.startsWith(window.location.origin) ||
      urlStr.startsWith(backendOrigin);

    if (!isTrustedBackend) {
      return _originalFetch(input, init);
    }

    const existingHeaders = new Headers(init?.headers);
    const hadAuthHeader = existingHeaders.has('Authorization');
    if (!hadAuthHeader) {
      const auth = getStoredAuth();
      if (auth) {
        existingHeaders.set('Authorization', `Basic ${auth}`);
      }
    }

    const response = await _originalFetch(input, { ...init, headers: existingHeaders });

    // 已自带 Authorization 头的请求（即 authFetch 自身发出的调用）不在这里做 401
    // 重试，避免与 authFetch 内部的重试逻辑重复弹两次登录框——交给 authFetch 自己处理。
    if (response.status !== 401 || hadAuthHeader) {
      return response;
    }

    clearAuth();
    const newAuth = await promptLogin();
    if (!newAuth) return response; // 用户取消登录，原样返回 401

    const retryHeaders = new Headers(init?.headers);
    retryHeaders.set('Authorization', `Basic ${newAuth}`);
    return _originalFetch(input, { ...init, headers: retryHeaders });
  };
}
