/**
 * LLM Manager 钩子函数
 * 
 * 提供常用的状态管理和操作
 */

import { useState, useEffect, useCallback } from 'react';
import { useLLMManager } from '../contexts/LLMManagerContext';
import apiClient from '../utils/api';

/**
 * 使用API数据的钩子
 * 
 * @param {string} endpoint - API端点
 * @param {Object} options - 选项
 * @param {Object} options.params - 请求参数
 * @param {Array} options.deps - 依赖数组，变化时重新获取数据
 * @param {boolean} options.immediate - 是否立即获取数据
 * @param {Function} options.transform - 数据转换函数
 * @returns {Object} 状态和操作
 */
export const useApiData = (endpoint, options = {}) => {
  const { globalHeaders } = useLLMManager();
  const {
    params = {},
    deps = [],
    immediate = true,
    transform = data => data
  } = options;
  
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.get(endpoint, {
        params,
        headers: globalHeaders
      });
      
      if (response.data && response.data.status === 'success') {
        setData(transform(response.data.data));
      } else {
        setError(response.data?.message || '获取数据失败');
      }
    } catch (err) {
      setError(err.message || '网络请求失败');
    } finally {
      setLoading(false);
    }
  }, [endpoint, globalHeaders, params, transform]);

  useEffect(() => {
    if (immediate) {
      fetchData();
    }
  }, [fetchData, immediate, ...deps]);

  const refetch = useCallback(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    refetch
  };
};

/**
 * 使用API操作（POST/PUT/DELETE）的钩子
 * 
 * @returns {Object} 操作函数和状态
 */
export const useApiAction = () => {
  const { globalHeaders } = useLLMManager();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const execute = useCallback(async (method, url, data = null) => {
    try {
      setLoading(true);
      setError(null);
      
      const config = { headers: globalHeaders };
      let response;
      
      switch (method.toLowerCase()) {
        case 'post':
          response = await apiClient.post(url, data, config);
          break;
        case 'put':
          response = await apiClient.put(url, data, config);
          break;
        case 'delete':
          response = await apiClient.delete(url, config);
          break;
        default:
          throw new Error(`不支持的HTTP方法: ${method}`);
      }
      
      return response.data;
    } catch (err) {
      setError(err.message || '操作失败');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [globalHeaders]);

  return {
    execute,
    loading,
    error
  };
};

/**
 * 使用通知的钩子
 * 
 * @returns {Object} 通知函数和状态
 */
export const useNotification = () => {
  const { globalConfig } = useLLMManager();
  const [notifications, setNotifications] = useState([]);

  const addNotification = useCallback((type, message, options = {}) => {
    if (!globalConfig.enableNotifications) return;
    
    const notification = {
      id: Date.now(),
      type,
      message,
      autoClose: options.autoClose !== false, // 默认自动关闭
      duration: options.duration || 5000,
      ...options
    };
    
    setNotifications(prev => [...prev, notification]);
    
    if (notification.autoClose) {
      setTimeout(() => {
        removeNotification(notification.id);
      }, notification.duration);
    }
  }, [globalConfig.enableNotifications]);

  const removeNotification = useCallback((id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  return {
    notifications,
    addNotification,
    removeNotification,
    clearNotifications
  };
};

/**
 * 使用本地存储的钩子
 * 
 * @param {string} key - 存储键
 * @param {any} initialValue - 初始值
 * @returns {Array} 值和设置函数
 */
export const useLocalStorage = (key, initialValue) => {
  // 从localStorage获取初始值
  const getStoredValue = () => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error(`从localStorage获取${key}失败:`, error);
      return initialValue;
    }
  };

  const [storedValue, setStoredValue] = useState(getStoredValue);

  // 设置值到localStorage
  const setValue = (value) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error(`设置localStorage ${key} 失败:`, error);
    }
  };

  return [storedValue, setValue];
};

/**
 * 使用防抖的钩子
 * 
 * @param {any} value - 要防抖的值
 * @param {number} delay - 延迟时间（毫秒）
 * @returns {any} 防抖后的值
 */
export const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

// 默认导出useLLMManager
export default useLLMManager;