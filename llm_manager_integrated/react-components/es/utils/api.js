function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) { var o = Object.getOwnPropertySymbols(e); r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o); } return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) { var t = null != arguments[r] ? arguments[r] : {}; r % 2 ? ownKeys(Object(t), !0).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); }); } return e; }
function _defineProperty(e, r, t) { return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: !0, configurable: !0, writable: !0 }) : e[r] = t, e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == _typeof(i) ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != _typeof(t) || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r || "default"); if ("object" != _typeof(i)) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
/**
 * API客户端工具
 * 
 * 提供统一的API请求接口
 */

import axios from 'axios';

// 创建默认axios实例
var apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 请求拦截器
apiClient.interceptors.request.use(function (config) {
  // 可以在这里添加全局请求处理，如添加token
  var token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = "Bearer ".concat(token);
  }

  // 添加请求时间戳
  config.metadata = {
    startTime: new Date()
  };
  return config;
}, function (error) {
  return Promise.reject(error);
});

// 响应拦截器
apiClient.interceptors.response.use(function (response) {
  // 计算请求耗时
  var endTime = new Date();
  var duration = endTime - response.config.metadata.startTime;
  response.config.metadata.duration = duration;

  // 可以在这里添加全局响应处理
  return response;
}, function (error) {
  // 处理通用错误
  if (error.response) {
    var _error$response = error.response,
      status = _error$response.status,
      data = _error$response.data;
    switch (status) {
      case 401:
        // 未授权，可能需要重新登录
        console.error('API请求未授权:', data.message);
        break;
      case 403:
        // 禁止访问
        console.error('API请求禁止访问:', data.message);
        break;
      case 404:
        // 资源不存在
        console.error('API资源不存在:', data.message);
        break;
      case 500:
        // 服务器错误
        console.error('API服务器错误:', data.message);
        break;
      default:
        console.error('API请求错误:', data.message || '未知错误');
    }
  } else if (error.request) {
    // 请求已发出但没有收到响应
    console.error('API请求无响应:', error.message);
  } else {
    // 设置请求时发生错误
    console.error('API请求配置错误:', error.message);
  }
  return Promise.reject(error);
});

// 导出默认实例和工厂函数
export default apiClient;

// 创建自定义API客户端的工厂函数
export var createApiClient = function createApiClient() {
  var config = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
  var customClient = axios.create({
    baseURL: config.baseURL || '',
    timeout: config.timeout || 30000,
    headers: _objectSpread({
      'Content-Type': 'application/json'
    }, config.headers)
  });

  // 应用相同的拦截器
  customClient.interceptors.request.use(apiClient.interceptors.request.handlers[0].fulfilled);
  customClient.interceptors.response.use(apiClient.interceptors.response.handlers[0].fulfilled, apiClient.interceptors.response.handlers[1].rejected);
  return customClient;
};