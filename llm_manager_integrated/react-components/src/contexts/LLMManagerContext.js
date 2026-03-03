/**
 * LLM Manager 上下文
 * 
 * 提供全局配置和状态管理
 */

import React, { createContext, useContext, useState, useEffect } from 'react';

// 创建默认上下文
const defaultContext = {
  globalHeaders: {},
  globalTheme: {
    primaryColor: '#3498db',
    secondaryColor: '#95a5a6',
    successColor: '#2ecc71',
    dangerColor: '#e74c3c',
    warningColor: '#f39c12',
    textColor: '#333',
    secondaryTextColor: '#666',
    headerBgColor: '#f2f2f2',
    cardBgColor: '#f8f9fa',
    borderColor: '#ddd',
    selectedBgColor: '#e3f2fd',
    detailBgColor: '#f8f9fa'
  },
  globalConfig: {
    pageSize: 20,
    enableNotifications: true,
    apiTimeout: 30000
  },
  // 设置全局配置的方法
  setGlobalHeaders: () => {},
  setGlobalTheme: () => {},
  setGlobalConfig: () => {}
};

// 创建上下文
const LLMManagerContext = createContext(defaultContext);

/**
 * LLM Manager 上下文提供者
 * 
 * @param {Object} props - 组件属性
 * @param {Object} props.headers - 全局请求头
 * @param {Object} props.theme - 全局主题配置
 * @param {Object} props.config - 全局配置
 * @param {ReactNode} props.children - 子组件
 */
export const LLMManagerProvider = ({ 
  headers = {}, 
  theme = {}, 
  config = {},
  children 
}) => {
  // 状态管理
  const [globalHeaders, setGlobalHeaders] = useState(headers);
  const [globalTheme, setGlobalTheme] = useState({
    ...defaultContext.globalTheme,
    ...theme
  });
  const [globalConfig, setGlobalConfig] = useState({
    ...defaultContext.globalConfig,
    ...config
  });

  // 监听配置变化
  useEffect(() => {
    setGlobalHeaders({ ...globalHeaders, ...headers });
  }, [headers]);

  useEffect(() => {
    setGlobalTheme({ ...globalTheme, ...theme });
  }, [theme]);

  useEffect(() => {
    setGlobalConfig({ ...globalConfig, ...config });
  }, [config]);

  // 上下文值
  const contextValue = {
    globalHeaders,
    globalTheme,
    globalConfig,
    setGlobalHeaders,
    setGlobalTheme,
    setGlobalConfig
  };

  return (
    <LLMManagerContext.Provider value={contextValue}>
      {children}
    </LLMManagerContext.Provider>
  );
};

/**
 * 使用LLM Manager上下文的钩子
 * 
 * @returns {Object} 上下文值
 */
export const useLLMManager = () => {
  const context = useContext(LLMManagerContext);
  
  if (!context) {
    throw new Error('useLLMManager must be used within a LLMManagerProvider');
  }
  
  return context;
};

export { LLMManagerContext as default };