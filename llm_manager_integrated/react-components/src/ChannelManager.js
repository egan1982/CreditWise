/**
 * LLM API Manager - ChannelManager 组件
 * 
 * 可集成到任何React应用的渠道管理组件
 * 
 * @version 1.0.0
 */

import React, { useState, useEffect, useContext } from 'react';
import PropTypes from 'prop-types';
import { LLMManagerContext } from './contexts/LLMManagerContext';
import apiClient from './utils/api';

/**
 * ChannelManager 组件
 * 
 * @param {Object} props - 组件属性
 * @param {string} props.apiEndpoint - API端点
 * @param {Object} props.headers - 请求头
 * @param {Function} props.onChannelSelect - 渠道选择回调
 * @param {boolean} props.showActions - 是否显示操作按钮
 * @param {Object} props.customStyles - 自定义样式
 * @param {Object} props.theme - 主题配置
 * @param {boolean} props.selectable - 是否可选择渠道
 * @param {Function} props.onApiError - API错误回调
 */
const ChannelManager = ({ 
  apiEndpoint = '/api/manage/channels', 
  headers = {},
  onChannelSelect,
  showActions = true,
  customStyles = {},
  theme = {},
  selectable = false,
  onApiError
}) => {
  // 从上下文获取全局配置
  const { globalHeaders, globalTheme } = useContext(LLMManagerContext);
  
  // 合并全局配置
  const mergedHeaders = { ...globalHeaders, ...headers };
  const mergedTheme = { ...globalTheme, ...theme };
  
  // 组件状态
  const [channels, setChannels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedChannel, setSelectedChannel] = useState(null);

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
      alignItems: 'center'
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
      borderBottom: '1px solid #ddd'
    },
    enabledRow: {
      backgroundColor: 'rgba(46, 204, 113, 0.1)',
      boxShadow: '0 1px 3px rgba(0,0,0,0.05) inset'
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
    successButton: {
      backgroundColor: mergedTheme.successColor || '#2ecc71',
      color: '#fff'
    },
    dangerButton: {
      backgroundColor: mergedTheme.dangerColor || '#e74c3c',
      color: '#fff'
    },
    secondaryButton: {
      backgroundColor: mergedTheme.secondaryColor || '#95a5a6',
      color: '#fff'
    }
  };

  // 合并自定义样式
  const styles = { ...defaultStyles, ...customStyles };

  // 获取渠道数据
  useEffect(() => {
    fetchChannels();
  }, [apiEndpoint, mergedHeaders]);

  const fetchChannels = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.get(apiEndpoint, {
        headers: mergedHeaders
      });
      
      if (response.data && response.data.status === 'success') {
        setChannels(response.data.data || []);
      } else {
        setError(response.data?.message || '获取渠道失败');
        if (onApiError) {
          onApiError(new Error(response.data?.message || '获取渠道失败'));
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

  const handleChannelClick = (channel) => {
    setSelectedChannel(channel);
    if (onChannelSelect) {
      onChannelSelect(channel);
    }
  };

  const handleTest = async (channelId) => {
    try {
      const response = await apiClient.post(`${apiEndpoint}/${channelId}/test`, null, {
        headers: mergedHeaders
      });
      
      if (response.data && response.data.status === 'success') {
        alert('渠道测试成功');
      } else {
        alert(`渠道测试失败: ${response.data?.message || '未知错误'}`);
      }
    } catch (err) {
      alert('测试请求失败');
    }
  };

  const handleToggleStatus = async (channelId, currentStatus) => {
    const channel = channels.find(ch => ch.id === channelId);
    const channelName = channel ? channel.name : '此渠道';
    
    // 显示确认对话框
    const action = currentStatus ? '禁用' : '启用';
    if (!window.confirm(`确定要${action} "${channelName}" 吗？`)) {
      return;
    }
    
    try {
      const response = await apiClient.put(
        `${apiEndpoint}/${channelId}`, 
        { status: !currentStatus },
        { headers: mergedHeaders }
      );
      
      if (response.data && response.data.status === 'success') {
        // 只更新当前渠道状态，不影响其他渠道（支持多配置并存）
        setChannels(channels.map(ch => 
          ch.id === channelId ? { ...ch, status: !currentStatus } : ch
        ));
      } else {
        alert(`状态更新失败: ${response.data?.message || '未知错误'}`);
      }
    } catch (err) {
      alert('状态更新请求失败');
    }
  };

  const handleDelete = async (channelId) => {
    if (!window.confirm('确定要删除此渠道吗？')) return;
    
    try {
      const response = await apiClient.delete(`${apiEndpoint}/${channelId}`, {
        headers: mergedHeaders
      });
      
      if (response.data && response.data.status === 'success') {
        // 从本地状态中移除
        setChannels(channels.filter(ch => ch.id !== channelId));
      } else {
        alert(`删除失败: ${response.data?.message || '未知错误'}`);
      }
    } catch (err) {
      alert('删除请求失败');
    }
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

  // 渲染渠道管理界面
  return (
    <div style={styles.container}>
      <h2>渠道管理</h2>
      
      <div style={{
        backgroundColor: mergedTheme.infoBgColor || '#e3f2fd',
        borderLeft: `4px solid ${mergedTheme.infoColor || '#2196f3'}`,
        padding: '10px 15px',
        marginBottom: '15px',
        borderRadius: '4px',
        fontSize: '14px'
      }}>
        <strong>提示：</strong>系统支持多配置并存，可同时启用多个渠道配置。在AI对话时可根据任务类型选择合适的配置。
      </div>
      
      <div style={styles.toolbar}>
        <div>
          <span>共 {channels.length} 个渠道</span>
          {channels.some(ch => ch.status) && (
            <span style={{ 
              marginLeft: '10px',
              color: mergedTheme.successColor || '#2ecc71',
              fontWeight: 'bold'
            }}>
              ({channels.filter(ch => ch.status).length} 个已启用)
            </span>
          )}
        </div>
        {showActions && (
          <div>
            <button 
              style={{ ...styles.button, ...styles.primaryButton }}
              onClick={() => alert('新建渠道功能待实现')}
            >
              新建渠道
            </button>
          </div>
        )}
      </div>
      
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>ID</th>
            <th style={styles.th}>名称</th>
            <th style={styles.th}>类型</th>
            <th style={styles.th}>模型</th>
            <th style={styles.th}>状态</th>
            {showActions && <th style={styles.th}>操作</th>}
          </tr>
        </thead>
        <tbody>
          {channels.map(channel => (
            <tr 
              key={channel.id} 
              onClick={() => selectable && handleChannelClick(channel)}
              style={{ 
                cursor: selectable ? 'pointer' : 'default',
                backgroundColor: selectable && selectedChannel?.id === channel.id 
                  ? (mergedTheme.selectedBgColor || '#e3f2fd') 
                  : 'transparent',
                ...(channel.status && !selectable ? styles.enabledRow : {}),
                ...(channel.status && selectable && selectedChannel?.id !== channel.id ? styles.enabledRow : {})
              }}
            >
              <td style={styles.td}>{channel.id}</td>
              <td style={styles.td}>{channel.name}</td>
              <td style={styles.td}>{channel.type}</td>
              <td style={styles.td}>
                {channel.models}
                {channel.supports_web_search && <span title="支持联网搜索"> 🌐</span>}
                {channel.supports_deep_thinking && <span title="支持深度推理"> 🧠</span>}
              </td>
              <td style={styles.td}>
                {showActions ? (
                  <button 
                    style={{ 
                      ...styles.button, 
                      ...(channel.status ? styles.successButton : styles.secondaryButton),
                      position: 'relative',
                      paddingRight: channel.status ? '25px' : '12px'
                    }}
                    onClick={(e) => { 
                      e.stopPropagation(); 
                      handleToggleStatus(channel.id, channel.status); 
                    }}
                    title={channel.status ? '点击禁用此渠道' : '点击启用此渠道'}
                  >
                    {channel.status ? '已启用' : '已禁用'}
                    {channel.status && (
                      <span style={{ 
                        position: 'absolute', 
                        right: '5px', 
                        top: '50%', 
                        transform: 'translateY(-50%)',
                        fontSize: '12px'
                      }}>
                        ✓
                      </span>
                    )}
                  </button>
                ) : (
                  <span 
                    style={{ 
                      color: channel.status 
                        ? (mergedTheme.successColor || '#2ecc71') 
                        : (mergedTheme.secondaryColor || '#95a5a6'),
                      fontWeight: 'bold'
                    }}
                  >
                    {channel.status ? '✓ 已启用' : '○ 已禁用'}
                  </span>
                )}
              </td>
              {showActions && (
                <td style={styles.td}>
                  <button 
                    style={{ ...styles.button, ...styles.secondaryButton }}
                    onClick={(e) => { e.stopPropagation(); handleTest(channel.id); }}
                  >
                    测试
                  </button>
                  <button 
                    style={{ ...styles.button, ...styles.primaryButton }}
                    onClick={(e) => { e.stopPropagation(); alert('编辑功能待实现'); }}
                  >
                    编辑
                  </button>
                  <button 
                    style={{ ...styles.button, ...styles.dangerButton }}
                    onClick={(e) => { e.stopPropagation(); handleDelete(channel.id); }}
                  >
                    删除
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

ChannelManager.propTypes = {
  apiEndpoint: PropTypes.string,
  headers: PropTypes.object,
  onChannelSelect: PropTypes.func,
  showActions: PropTypes.bool,
  customStyles: PropTypes.object,
  theme: PropTypes.object,
  selectable: PropTypes.bool,
  onApiError: PropTypes.func
};

export default ChannelManager;