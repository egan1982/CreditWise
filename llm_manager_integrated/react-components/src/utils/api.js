/**
 * API客户端工具
 * 
 * 提供统一的API请求接口
 */

import axios from 'axios';

// 创建默认axios实例
const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加全局请求处理，如添加token
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // 添加请求时间戳
    config.metadata = { startTime: new Date() };
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    // 计算请求耗时
    const endTime = new Date();
    const duration = endTime - response.config.metadata.startTime;
    response.config.metadata.duration = duration;
    
    // 可以在这里添加全局响应处理
    return response;
  },
  (error) => {
    // 处理通用错误
    if (error.response) {
      const { status, data } = error.response;
      
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
  }
);

// 导出默认实例和工厂函数
export default apiClient;

// 创建自定义API客户端的工厂函数
export const createApiClient = (config = {}) => {
  const customClient = axios.create({
    baseURL: config.baseURL || '',
    timeout: config.timeout || 30000,
    headers: {
      'Content-Type': 'application/json',
      ...config.headers
    }
  });
  
  // 应用相同的拦截器
  customClient.interceptors.request.use(apiClient.interceptors.request.handlers[0].fulfilled);
  customClient.interceptors.response.use(
    apiClient.interceptors.response.handlers[0].fulfilled,
    apiClient.interceptors.response.handlers[1].rejected
  );
  
  return customClient;
};