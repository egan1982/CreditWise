/**
 * LLM API Manager - APILogs 组件
 * 
 * 可集成到任何React应用的API日志组件
 * 
 * @version 1.0.0
 */

import React, { useState, useEffect, useContext } from 'react';
import PropTypes from 'prop-types';
import { LLMManagerContext } from './contexts/LLMManagerContext';
import apiClient from './utils/api';

/**
 * APILogs 组件
 * 
 * @param {Object} props - 组件属性
 * @param {string} props.apiEndpoint - API端点
 * @param {Object} props.headers - 请求头
 * @param {Object} props.customStyles - 自定义样式
 * @param {Object} props.theme - 主题配置
 * @param {boolean} props.showFilters - 是否显示过滤器
 * @param {Function} props.onApiError - API错误回调
 * @param {number} props.pageSize - 每页显示数量
 */
const APILogs = ({ 
  apiEndpoint = '/api/logs', 
  headers = {},
  customStyles = {},
  theme = {},
  showFilters = true,
  onApiError,
  pageSize = 20
}) => {
  // 从上下文获取全局配置
  const { globalHeaders, globalTheme } = useContext(LLMManagerContext);
  
  // 合并全局配置
  const mergedHeaders = { ...globalHeaders, ...headers };
  const mergedTheme = { ...globalTheme, ...theme };
  
  // 组件状态
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalLogs, setTotalLogs] = useState(0);
  const [filterModel, setFilterModel] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [expandedLog, setExpandedLog] = useState(null);

  // 默认样式
  const defaultStyles = {
    container: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif',
      backgroundColor: '#fff',
      padding: '20px',
      borderRadius: '8px',
      boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
      color: mergedTheme.textColor || '#333'
    },
    toolbar: {
      display: 'flex',
      justifyContent: 'space-between',
      marginBottom: '20px',
      alignItems: 'center',
      flexWrap: 'wrap',
      gap: '10px'
    },
    filterContainer: {
      display: 'flex',
      gap: '10px',
      alignItems: 'center',
      marginBottom: '20px'
    },
    filterInput: {
      padding: '8px 12px',
      border: `1px solid ${mergedTheme.borderColor || '#ddd'}`,
      borderRadius: '4px'
    },
    filterSelect: {
      padding: '8px 12px',
      border: `1px solid ${mergedTheme.borderColor || '#ddd'}`,
      borderRadius: '4px',
      backgroundColor: '#fff'
    },
    table: {
      width: '100%',
      borderCollapse: 'collapse',
      marginTop: '20px',
      backgroundColor: '#fff'
    },
    th: {
      backgroundColor: mergedTheme.headerBgColor || '#f2f2f2',
      padding: '12px 15px',
      textAlign: 'left',
      borderBottom: '1px solid #ddd',
      fontWeight: 'bold'
    },
    td: {
      padding: '12px 15px',
      borderBottom: '1px solid #ddd',
      wordBreak: 'break-word'
    },
    button: {
      padding: '6px 12px',
      margin: '0 5px',
      border: 'none',
      borderRadius: '4px',
      cursor: 'pointer',
      fontWeight: '500'
    },
    primaryButton: {
      backgroundColor: mergedTheme.primaryColor || '#3498db',
      color: '#fff'
    },
    dangerButton: {
      backgroundColor: mergedTheme.dangerColor || '#e74c3c',
      color: '#fff'
    },
    pagination: {
      display: 'flex',
      justifyContent: 'center',
      marginTop: '20px',
      gap: '10px'
    },
    pageButton: {
      padding: '6px 12px',
      border: `1px solid ${mergedTheme.borderColor || '#ddd'}`,
      borderRadius: '4px',
      cursor: 'pointer',
      backgroundColor: '#fff'
    },
    activePageButton: {
      backgroundColor: mergedTheme.primaryColor || '#3498db',
      color: '#fff',
      borderColor: mergedTheme.primaryColor || '#3498db'
    },
    logDetail: {
      backgroundColor: mergedTheme.detailBgColor || '#f8f9fa',
      padding: '15px',
      marginTop: '10px',
      borderRadius: '4px',
      borderLeft: `4px solid ${mergedTheme.primaryColor || '#3498db'}`
    }
  };

  // 合并自定义样式
  const styles = { ...defaultStyles, ...customStyles };

  // 获取日志数据
  useEffect(() => {
    fetchLogs();
    fetchStats();
  }, [apiEndpoint, mergedHeaders, currentPage, filterModel, filterStatus]);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = {
        skip: (currentPage - 1) * pageSize,
        limit: pageSize
      };
      
      if (filterModel) params.model_name = filterModel;
      if (filterStatus) params.status = filterStatus;
      
      const response = await apiClient.get(apiEndpoint, {
        params,
        headers: mergedHeaders
      });
      
      if (response.data && response.data.status === 'success') {
        setLogs(response.data.data || []);
        // 注意：实际API可能需要返回总数，这里假设总数等于当前返回的日志数
        setTotalLogs(response.data.data?.length || 0);
      } else {
        setError(response.data?.message || '获取日志失败');
        if (onApiError) {
          onApiError(new Error(response.data?.message || '获取日志失败'));
        }
      }
    } catch (err) {
      const errorMsg = '网络请求失败';
      setError(errorMsg);
      if (onApiError) {
        onApiError(err);
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await apiClient.get(`${apiEndpoint}/stats`, {
        headers: mergedHeaders
      });
      
      if (response.data && response.data.status === 'success') {
        setStats(response.data.data || {});
      }
    } catch (err) {
      console.error('获取统计信息失败:', err);
    }
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const handleClearLogs = async () => {
    if (!window.confirm('确定要清除30天前的日志吗？')) return;
    
    try {
      const response = await apiClient.delete(`${apiEndpoint}?days=30`, {
        headers: mergedHeaders
      });
      
      if (response.data && response.data.status === 'success') {
        alert(response.data.message || '日志清除成功');
        fetchLogs(); // 重新获取日志
        fetchStats(); // 重新获取统计
      } else {
        alert(`清除失败: ${response.data?.message || '未知错误'}`);
      }
    } catch (err) {
      alert('清除请求失败');
    }
  };

  const toggleLogDetail = (logId) => {
    setExpandedLog(expandedLog === logId ? null : logId);
  };

  // 渲染加载状态
  if (loading && logs.length === 0) {
    return (
      <div style={styles.container}>
        <div>加载中...</div>
      </div>
    );
  }

  // 渲染错误状态
  if (error && logs.length === 0) {
    return (
      <div style={styles.container}>
        <div style={{ color: mergedTheme.dangerColor || '#e74c3c' }}>
          错误: {error}
        </div>
      </div>
    );
  }

  // 渲染日志界面
  return (
    <div style={styles.container}>
      <h2>API调用日志</h2>
      
      <div style={styles.toolbar}>
        <div>
          <span>共 {totalLogs} 条日志</span>
          {stats && (
            <span style={{ marginLeft: '15px' }}>
              今日调用: {stats.today_calls || 0}
            </span>
          )}
        </div>
        <button 
          style={{ ...styles.button, ...styles.dangerButton }}
          onClick={handleClearLogs}
        >
          清除30天前日志
        </button>
      </div>
      
      {showFilters && (
        <div style={styles.filterContainer}>
          <div>
            <label>模型筛选: </label>
            <input 
              type="text"
              style={styles.filterInput}
              value={filterModel}
              onChange={(e) => {
                setFilterModel(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="输入模型名称"
            />
          </div>
          <div>
            <label>状态筛选: </label>
            <select 
              style={styles.filterSelect}
              value={filterStatus}
              onChange={(e) => {
                setFilterStatus(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="">全部</option>
              <option value="success">成功</option>
              <option value="error">失败</option>
            </select>
          </div>
        </div>
      )}
      
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>ID</th>
            <th style={styles.th}>模型</th>
            <th style={styles.th}>状态</th>
            <th style={styles.th}>时间</th>
            <th style={styles.th}>操作</th>
          </tr>
        </thead>
        <tbody>
          {logs.map(log => (
            <React.Fragment key={log.id}>
              <tr>
                <td style={styles.td}>{log.id}</td>
                <td style={styles.td}>{log.model_name}</td>
                <td style={styles.td}>
                  <span style={{ 
                    color: log.status === 'success' 
                      ? (mergedTheme.successColor || '#2ecc71') 
                      : (mergedTheme.dangerColor || '#e74c3c'),
                    fontWeight: 'bold'
                  }}>
                    {log.status === 'success' ? '成功' : '失败'}
                  </span>
                </td>
                <td style={styles.td}>
                  {new Date(log.created_at).toLocaleString()}
                </td>
                <td style={styles.td}>
                  <button 
                    style={{ ...styles.button, ...styles.primaryButton }}
                    onClick={() => toggleLogDetail(log.id)}
                  >
                    {expandedLog === log.id ? '收起' : '详情'}
                  </button>
                </td>
              </tr>
              {expandedLog === log.id && (
                <tr>
                  <td colSpan="5" style={{ padding: '0' }}>
                    <div style={styles.logDetail}>
                      <pre style={{ 
                        margin: 0, 
                        whiteSpace: 'pre-wrap', 
                        fontSize: '14px',
                        maxHeight: '200px',
                        overflow: 'auto'
                      }}>
                        {JSON.stringify(log, null, 2)}
                      </pre>
                    </div>
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
      
      {/* 分页 */}
      <div style={styles.pagination}>
        <button 
          style={styles.pageButton}
          disabled={currentPage === 1}
          onClick={() => handlePageChange(currentPage - 1)}
        >
          上一页
        </button>
        
        <span style={{ margin: '0 10px' }}>
          第 {currentPage} 页
        </span>
        
        <button 
          style={styles.pageButton}
          disabled={logs.length < pageSize}
          onClick={() => handlePageChange(currentPage + 1)}
        >
          下一页
        </button>
      </div>
    </div>
  );
};

APILogs.propTypes = {
  apiEndpoint: PropTypes.string,
  headers: PropTypes.object,
  customStyles: PropTypes.object,
  theme: PropTypes.object,
  showFilters: PropTypes.bool,
  onApiError: PropTypes.func,
  pageSize: PropTypes.number
};

export default APILogs;