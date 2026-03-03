// 在开发环境中使用代理API路径，在生产环境中使用完整的LLM Manager API路径
const API_BASE = window.location.port === '3000' ? '/api' : '/llm-manager/api';

// 选项卡切换
function switchTab(event, tabName) {
    // 隐藏所有内容
    document.querySelectorAll('.tab-content').forEach(el => {
        el.classList.remove('active');
    });
    document.querySelectorAll('.nav-item').forEach(el => {
        el.classList.remove('active');
    });

    // 显示选中的内容
    document.getElementById(tabName + '-tab').classList.add('active');
    event.target.closest('.nav-item').classList.add('active');

    // 加载数据
    if (tabName === 'channels') loadChannels();
    else if (tabName === 'logs') loadLogs();
    else if (tabName === 'stats') loadStats();
    else if (tabName === 'settings') loadSystemInfo();
}

// 加载渠道列表
async function loadChannels() {
    try {
        const response = await fetch(`${API_BASE}/manage/channels`);
        const result = await response.json();

        if (result.code === 0) {
            const channels = result.data || [];
            if (channels.length === 0) {
                document.getElementById('channels-list').innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">EMPTY</div>
                        <div class="empty-state-text">暂无渠道</div>
                        <div class="empty-state-subtext">点击"新建渠道"添加第一个渠道</div>
                    </div>
                `;
            } else {
                let html = '<table class="table"><thead><tr><th>名称</th><th>类型</th><th>模型</th><th>状态</th><th>操作</th></tr></thead><tbody>';
                channels.forEach(ch => {
                    html += `
                        <tr>
                            <td>${ch.name}</td>
                            <td>${ch.type}</td>
                            <td>${ch.models}</td>
                            <td>
                                <button 
                                    class="btn ${ch.status ? 'btn-success' : 'btn-secondary'}" 
                                    onclick="toggleChannelStatus(${ch.id}, ${ch.status})"
                                    style="padding: 4px 12px; font-size: 12px; font-weight: 600;"
                                    title="${ch.status ? '点击禁用此渠道（将停用所有渠道）' : '点击启用此渠道（将自动禁用其他渠道）'}"
                                >
                                    ${ch.status ? '✓ 已启用' : '○ 已禁用'}
                                </button>
                            </td>
                            <td>
                                <button class="btn btn-success" onclick="testChannel(${ch.id})" style="padding: 4px 8px; font-size: 12px;">测试</button>
                                <button class="btn btn-primary" onclick="editChannel(${ch.id})" style="padding: 4px 8px; font-size: 12px;">编辑</button>
                                <button class="btn btn-danger" onclick="deleteChannel(${ch.id})" style="padding: 4px 8px; font-size: 12px;">删除</button>
                            </td>
                        </tr>
                    `;
                });
                html += '</tbody></table>';
                document.getElementById('channels-list').innerHTML = html;
            }
        } else {
            showError('加载渠道失败: ' + result.message);
        }
    } catch (error) {
        showError('加载渠道异常: ' + error.message);
    }
}

// 加载日志列表
async function loadLogs() {
    try {
        const response = await fetch(`${API_BASE}/logs?limit=10`);
        const result = await response.json();

        if (result.code === 0) {
            const logs = result.data || [];
            if (logs.length === 0) {
                document.getElementById('logs-list').innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">EMPTY</div>
                        <div class="empty-state-text">暂无日志</div>
                    </div>
                `;
            } else {
                let html = '<table class="table"><thead><tr><th>模型</th><th>渠道</th><th>状态</th><th>时间</th></tr></thead><tbody>';
                logs.forEach(log => {
                    html += `
                        <tr>
                            <td>${log.model_name}</td>
                            <td>${log.channel_name || '-'}</td>
                            <td><span class="status-badge ${log.status === 'success' ? 'success' : 'error'}">${log.status}</span></td>
                            <td>${new Date(log.timestamp).toLocaleString()}</td>
                        </tr>
                    `;
                });
                html += '</tbody></table>';
                document.getElementById('logs-list').innerHTML = html;
            }
        } else {
            showError('加载日志失败: ' + result.message);
        }
    } catch (error) {
        showError('加载日志异常: ' + error.message);
    }
}

// 加载统计数据
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/monitoring/stats`);
        const result = await response.json();

        if (result.code === 0) {
            const stats = result.data || {};
            const html = `
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
                    <div style="padding: 16px; background: #f8f9fa; border-radius: 6px;">
                        <div style="font-size: 12px; color: #666; margin-bottom: 8px;">系统状态</div>
                        <div style="font-size: 20px; font-weight: 600; color: #667eea;">${stats.status || '未知'}</div>
                    </div>
                    <div style="padding: 16px; background: #f8f9fa; border-radius: 6px;">
                        <div style="font-size: 12px; color: #666; margin-bottom: 8px;">更新时间</div>
                        <div style="font-size: 14px; color: #333;">${new Date(stats.timestamp).toLocaleString()}</div>
                    </div>
                </div>
            `;
            document.getElementById('stats-content').innerHTML = html;
        } else {
            showError('加载统计数据失败: ' + result.message);
        }
    } catch (error) {
        showError('加载统计数据异常: ' + error.message);
    }
}

// 加载系统信息
async function loadSystemInfo() {
    try {
        const response = await fetch(`${API_BASE}/monitoring/health`);
        const result = await response.json();

        if (result.code === 0) {
            const data = result.data || {};
            let html = '';
            for (const [key, value] of Object.entries(data)) {
                if (typeof value === 'object') {
                    html += `<div style="margin-bottom: 8px;"><strong>${key}:</strong> ${JSON.stringify(value, null, 2)}</div>`;
                } else {
                    html += `<div style="margin-bottom: 8px;"><strong>${key}:</strong> ${value}</div>`;
                }
            }
            document.getElementById('system-info').innerHTML = html;
        } else {
            showError('加载系统信息失败: ' + result.message);
        }
    } catch (error) {
        showError('加载系统信息异常: ' + error.message);
    }
}

// 打开创建渠道模态框
function openCreateChannelModal() {
    document.getElementById('create-channel-modal').classList.add('active');
    document.getElementById('channel-form').reset();
    document.getElementById('modal-alert').innerHTML = '';
}

// 关闭创建渠道模态框
function closeCreateChannelModal() {
    document.getElementById('create-channel-modal').classList.remove('active');
}

// 提交渠道表单
async function submitChannelForm(event) {
    event.preventDefault();

    const form = document.getElementById('channel-form');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);

    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.querySelector('#submit-spinner').innerHTML = '<span class="spinner"></span>';

    try {
        const response = await fetch(`${API_BASE}/manage/channels`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.code === 0) {
            showSuccess('渠道创建成功!');
            closeCreateChannelModal();
            loadChannels();
        } else {
            showAlert('error', '创建失败: ' + result.message);
        }
    } catch (error) {
        showAlert('error', '创建异常: ' + error.message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.querySelector('#submit-spinner').innerHTML = '';
    }
}

// 测试渠道
async function testChannel(channelId) {
    try {
        const response = await fetch(`${API_BASE}/manage/channels/${channelId}/test`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.code === 0) {
            alert('渠道连接成功!');
        } else {
            alert('渠道连接失败: ' + result.message);
        }
    } catch (error) {
        alert('测试异常: ' + error.message);
    }
}

// 删除渠道
async function deleteChannel(channelId) {
    if (confirm('确定要删除此渠道吗?')) {
        try {
            const response = await fetch(`${API_BASE}/manage/channels/${channelId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.code === 0) {
                showSuccess('渠道删除成功!');
                loadChannels();
            } else {
                showError('删除失败: ' + result.message);
            }
        } catch (error) {
            showError('删除异常: ' + error.message);
        }
    }
}

// 切换渠道状态
async function toggleChannelStatus(channelId, currentStatus) {
    // 先获取当前渠道列表，以便获取渠道名称
    try {
        const listResponse = await fetch(`${API_BASE}/manage/channels`);
        const listResult = await listResponse.json();
        
        if (listResult.code !== 0) {
            showError('获取渠道列表失败');
            return;
        }
        
        const channels = listResult.data || [];
        const currentChannel = channels.find(ch => ch.id === channelId);
        const channelName = currentChannel ? currentChannel.name : `渠道 ID: ${channelId}`;
        
        let confirmMessage = '';
        
        if (currentStatus) {
            // 如果是禁用渠道
            confirmMessage = `确定要禁用 "${channelName}" 吗？`;
        } else {
            // 如果是启用渠道
            confirmMessage = `确定要启用 "${channelName}" 吗？`;
            
            // 检查是否有其他已启用的渠道
            const enabledChannels = channels.filter(ch => ch.status && ch.id !== channelId);
            if (enabledChannels.length > 0) {
                const enabledNames = enabledChannels.map(ch => ch.name).join(', ');
                confirmMessage += `\n\n注意：这将自动禁用当前已启用的渠道：${enabledNames}`;
            }
        }
        
        if (!confirm(confirmMessage)) {
            return;
        }
        
        const response = await fetch(`${API_BASE}/manage/channels/${channelId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                status: !currentStatus
            })
        });
        
        const result = await response.json();
        
        if (result.code === 0) {
            const action = currentStatus ? '禁用' : '启用';
            showSuccess(`渠道${action}成功! ${!currentStatus ? ' 已自动禁用其他渠道。' : ''}`);
            loadChannels();
        } else {
            showError(`${currentStatus ? '禁用' : '启用'}失败: ${result.message}`);
        }
    } catch (error) {
        showError(`操作异常: ${error.message}`);
    }
}

// 编辑配置
async function editChannel(channelId) {
    try {
        const response = await fetch(`${API_BASE}/manage/channels/${channelId}`);
        const result = await response.json();

        if (result.code === 0) {
            const channel = result.data;
            const form = document.getElementById('edit-channel-form');
            form.elements['name'].value = channel.name;
            form.elements['type'].value = channel.type;
            form.elements['models'].value = channel.models;
            form.elements['base_url'].value = channel.base_url;
            form.elements['api_key'].value = '';
            
            // 存储渠道ID用于提交
            form.dataset.channelId = channelId;
            
            document.getElementById('edit-channel-modal').classList.add('active');
            document.getElementById('edit-modal-alert').innerHTML = '';
        } else {
            showError('加载渠道失败: ' + result.message);
        }
    } catch (error) {
        showError('加载渠道异常: ' + error.message);
    }
}

// 关闭编辑模态框
function closeEditChannelModal() {
    document.getElementById('edit-channel-modal').classList.remove('active');
}

// 提交编辑配置表单
async function submitEditChannelForm(event) {
    event.preventDefault();

    const form = document.getElementById('edit-channel-form');
    const channelId = form.dataset.channelId;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);

    // 如果API Key为空，则删除该字段
    if (!data.api_key) {
        delete data.api_key;
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.querySelector('#edit-submit-spinner').innerHTML = '<span class="spinner"></span>';

    try {
        const response = await fetch(`${API_BASE}/manage/channels/${channelId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.code === 0) {
            showSuccessEdit('渠道更新成功!');
            closeEditChannelModal();
            loadChannels();
        } else {
            showAlertEdit('error', '更新失败: ' + result.message);
        }
    } catch (error) {
        showAlertEdit('error', '更新异常: ' + error.message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.querySelector('#edit-submit-spinner').innerHTML = '';
    }
}

// 显示提示信息
function showSuccess(message) {
    document.getElementById('modal-alert').innerHTML = `
        <div class="alert success">${message}</div>
    `;
    setTimeout(() => {
        document.getElementById('modal-alert').innerHTML = '';
    }, 3000);
}

function showError(message) {
    alert(message);
}

function showAlert(type, message) {
    document.getElementById('modal-alert').innerHTML = `
        <div class="alert ${type}">${message}</div>
    `;
}

// 页面加载时初始化
window.addEventListener('load', () => {
    loadChannels();
});