/**
 * LLM API Manager - Statistics 组件
 * 
 * 可集成到任何React应用的统计分析组件
 * 
 * @version 1.0.0
 */

import React, { useState, useEffect, useContext } from 'react';
import PropTypes from 'prop-types';
import { LLMManagerContext } from './contexts/LLMManagerContext';
import apiClient from './utils/api';

/**
 * Statistics 组件
 * 
 * @param {Object} props - 组件属性
 * @param {string} props.apiEndpoint - API端点
 * @param {Object} props.headers - 请求头
 * @param {Object} props.customStyles - 自定义样式
 * @param {Object} props.theme - 主题配置
 * @param {Function} props.onApiError - API错误回调
 * @param {boolean} props.showFilters - 是否显示过滤器
 */
const Statistics = ({ 
  apiEndpoint = '/api/logs/stats', 
  headers = {},
  customStyles = {},
  theme = {},
  showFilters = true,
  onApiError
}) => {
  // 从上下文获取全局配置
  const { globalHeaders, globalTheme } = useContext(LLMManagerContext);
  
  // 合并全局配置
  const mergedHeaders = { ...globalHeaders, ...headers };
  const mergedTheme = { ...globalTheme, ...theme };
  
  // 组件状态
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timeRange, setTimeRange] = useState('7'); // 默认7天
  const [chartType, setChartType] = useState('calls'); // calls, cost, tokens
  const [excludeTestData, setExcludeTestData] = useState(false);

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
    filterSelect: {
      padding: '8px 12px',
      border: `1px solid ${mergedTheme.borderColor || '#ddd'}`,
      borderRadius: '4px',
      backgroundColor: '#fff'
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
    statsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
      gap: '15px',
      marginBottom: '30px'
    },
    statCard: {
      backgroundColor: mergedTheme.cardBgColor || '#f8f9fa',
      padding: '15px',
      borderRadius: '8px',
      border: `1px solid ${mergedTheme.borderColor || '#eee'}`
    },
    statTitle: {
      fontSize: '14px',
      color: mergedTheme.secondaryTextColor || '#666',
      marginBottom: '8px'
    },
    statValue: {
      fontSize: '24px',
      fontWeight: 'bold',
      color: mergedTheme.primaryColor || '#3498db'
    },
    chartContainer: {
      backgroundColor: mergedTheme.cardBgColor || '#f8f9fa',
      padding: '20px',
      borderRadius: '8px',
      border: `1px solid ${mergedTheme.borderColor || '#eee'}`
    }
  };

  // 合并自定义样式
  const styles = { ...defaultStyles, ...customStyles };

  // 获取统计数据
  useEffect(() => {
    fetchData();
  }, [apiEndpoint, mergedHeaders, timeRange, excludeTestData]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [statsResponse, logsResponse] = await Promise.all([
        apiClient.get(apiEndpoint, { 
          params: { 
            time_range: timeRange, 
            exclude_test_data: excludeTestData 
          },
          headers: mergedHeaders
        }),
        apiClient.get('/api/logs', { 
          params: { 
            limit: 1000, 
            time_range: timeRange,
            exclude_test_data: excludeTestData
          },
          headers: mergedHeaders
        })
      ]);
      
      if (statsResponse.data && statsResponse.data.status === 'success') {
        setStats(statsResponse.data.data || {});
      }
      
      if (logsResponse.data && logsResponse.data.status === 'success') {
        setLogs(logsResponse.data.data || []);
      }
    } catch (err) {
      const errorMsg = '获取统计数据失败';
      setError(errorMsg);
      if (onApiError) {
        onApiError(err);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTestData = async () => {
    if (!window.confirm('确定要删除所有测试数据吗？此操作不可撤销。')) return;
    
    try {
      const response = await apiClient.delete('/api/logs/test-data', {
        headers: mergedHeaders
      });
      
      if (response.data && response.data.status === 'success') {
        alert(response.data.message || '测试数据删除成功');
        fetchData(); // 重新获取数据
      } else {
        alert(`删除失败: ${response.data?.message || '未知错误'}`);
      }
    } catch (err) {
      alert('删除请求失败');
    }
  };

  // 处理图表数据
  const processChartData = () => {
    if (!logs.length) return [];
    
    // 按日期分组
    const groupedByDate = {};
    
    logs.forEach(log => {
      const date = new Date(log.created_at).toLocaleDateString();
      if (!groupedByDate[date]) {
        groupedByDate[date] = {
          date,
          calls: 0,
          success: 0,
          error: 0,
          tokens: 0,
          cost: 0
        };
      }
      
      groupedByDate[date].calls += 1;
      if (log.status === 'success') {
        groupedByDate[date].success += 1;
      } else {
        groupedByDate[date].error += 1;
      }
      
      // 如果日志中有token和cost信息
      groupedByDate[date].tokens += log.tokens || 0;
      groupedByDate[date].cost += log.cost || 0;
    });
    
    // 转换为数组并排序
    return Object.values(groupedByDate).sort((a, b) => 
      new Date(a.date) - new Date(b.date)
    );
  };

  // 渲染加载状态
  if (loading) {
    return (
      <div style={styles.container}>
        <div>加载中...</div>
      </div>
    );
  }

  // 渲染错误状态
  if (error) {
    return (
      <div style={styles.container}>
        <div style={{ color: mergedTheme.dangerColor || '#e74c3c' }}>
          错误: {error}
        </div>
      </div>
    );
  }

  const chartData = processChartData();

  // 渲染统计界面
  return (
    <div style={styles.container}>
      <h2>统计分析</h2>
      
      <div style={styles.toolbar}>
        <div>
          <span>API调用统计</span>
        </div>
      </div>
      
      {showFilters && (
        <div style={styles.filterContainer}>
          <div>
            <label>时间范围: </label>
            <select 
              style={styles.filterSelect}
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
            >
              <option value="7">最近7天</option>
              <option value="30">最近30天</option>
              <option value="90">最近90天</option>
            </select>
          </div>
          
          <div>
            <label>
              <input 
                type="checkbox"
                checked={excludeTestData}
                onChange={(e) => setExcludeTestData(e.target.checked)}
              />
              排除测试数据
            </label>
          </div>
          
          <button 
            style={{ ...styles.button, ...styles.dangerButton }}
            onClick={handleDeleteTestData}
          >
            删除测试数据
          </button>
        </div>
      )}
      
      {/* 统计卡片 */}
      <div style={styles.statsGrid}>
        <div style={styles.statCard}>
          <div style={styles.statTitle}>总调用次数</div>
          <div style={styles.statValue}>
            {stats?.total_calls || 0}
          </div>
        </div>
        
        <div style={styles.statCard}>
          <div style={styles.statTitle}>成功调用</div>
          <div style={{ ...styles.statValue, color: mergedTheme.successColor || '#2ecc71' }}>
            {stats?.success_calls || 0}
          </div>
        </div>
        
        <div style={styles.statCard}>
          <div style={styles.statTitle}>失败调用</div>
          <div style={{ ...styles.statValue, color: mergedTheme.dangerColor || '#e74c3c' }}>
            {stats?.error_calls || 0}
          </div>
        </div>
        
        <div style={styles.statCard}>
          <div style={styles.statTitle}>成功率</div>
          <div style={styles.statValue}>
            {stats?.total_calls ? 
              `${((stats.success_calls / stats.total_calls) * 100).toFixed(1)}%` : 
              '0%'
            }
          </div>
        </div>
        
        <div style={styles.statCard}>
          <div style={styles.statTitle}>总Token数</div>
          <div style={styles.statValue}>
            {stats?.total_tokens || 0}
          </div>
        </div>
        
        <div style={styles.statCard}>
          <div style={styles.statTitle}>总花费</div>
          <div style={styles.statValue}>
            ${stats?.total_cost || '0.00'}
          </div>
        </div>
      </div>
      
      {/* 图表区域 */}
      <div style={styles.chartContainer}>
        <div style={{ marginBottom: '15px' }}>
          <label>图表类型: </label>
          <select 
            style={styles.filterSelect}
            value={chartType}
            onChange={(e) => setChartType(e.target.value)}
          >
            <option value="calls">调用次数</option>
            <option value="tokens">Token使用量</option>
            <option value="cost">花费</option>
          </select>
        </div>
        
        {/* 简单的图表实现（实际项目中可以使用recharts等图表库） */}
        <div style={{ height: '300px', position: 'relative' }}>
          {chartData.length > 0 ? (
            <div style={{ 
              display: 'flex', 
              alignItems: 'flex-end', 
              height: '100%',
              gap: '10px'
            }}>
              {chartData.map((item, index) => {
                let value = 0;
                if (chartType === 'calls') value = item.calls;
                else if (chartType === 'tokens') value = item.tokens / 1000; // 转换为千tokens
                else if (chartType === 'cost') value = parseFloat(item.cost) * 100; // 放大显示
                
                const maxValue = Math.max(...chartData.map(d => {
                  if (chartType === 'calls') return d.calls;
                  else if (chartType === 'tokens') return d.tokens / 1000;
                  else if (chartType === 'cost') return parseFloat(d.cost) * 100;
                  return 0;
                }));
                
                const height = maxValue > 0 ? (value / maxValue) * 250 : 0;
                
                return (
                  <div 
                    key={index}
                    style={{ 
                      flex: 1,
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center'
                    }}
                  >
                    <div 
                      style={{ 
                        height: `${height}px`,
                        width: '80%',
                        backgroundColor: mergedTheme.primaryColor || '#3498db',
                        borderRadius: '4px 4px 0 0',
                        position: 'relative'
                      }}
                      title={`${item.date}: ${value}`}
                    >
                      <div style={{
                        position: 'absolute',
                        top: '-20px',
                        left: 0,
                        right: 0,
                        textAlign: 'center',
                        fontSize: '12px'
                      }}>
                        {value}
                      </div>
                    </div>
                    <div style={{ 
                      marginTop: '5px', 
                      fontSize: '12px',
                      textAlign: 'center'
                    }}>
                      {new Date(item.date).toLocaleDateString('zh-CN', {
                        month: 'short',
                        day: 'numeric'
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ 
              display: 'flex', 
              justifyContent: 'center', 
              alignItems: 'center', 
              height: '100%',
              color: mergedTheme.secondaryTextColor || '#666'
            }}>
              暂无数据
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

Statistics.propTypes = {
  apiEndpoint: PropTypes.string,
  headers: PropTypes.object,
  customStyles: PropTypes.object,
  theme: PropTypes.object,
  showFilters: PropTypes.bool,
  onApiError: PropTypes.func
};

export default Statistics;