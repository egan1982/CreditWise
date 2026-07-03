// 在开发环境中使用代理API路径，在生产环境中使用完整的LLM Manager API路径
// 根据当前端口动态设置API_BASE
const API_BASE = (window.location.port === '3001' || window.location.port === '3000') 
    ? '/llm-manager/api' 
    : '/llm-manager/api';

// 用户管理模块 批次3（2026-07-03）：403 无权限统一提示。
//
// 背景：`/llm-manager` 页面壳子已从"未认证/非admin直接403拒绝加载整页"改为
// "页面壳子公开，真正的admin权限边界下放到具体管理API"（详见
// API/auth_middleware.py 中 AUTH_WHITELIST_EXACT 上方注释）。这意味着非admin
// 用户现在**能**打开这个页面，但调用 /manage/channels、/logs、/monitoring/*
// 等接口仍会收到403——此前各 loadXxx() 函数遇到非0 code/非200状态统一走
// `showError()`（本质是浏览器原生 `alert()`），技术性文案（如"请求失败，状态码:
// 403"）+ 弹窗关闭后原容器仍停留在初始"加载中"骨架，给人"一直加载中、没有任何
// 提示"的错觉，容易被误以为是bug而非"你没有权限"。这里单独拦截403，直接把
// 目标容器替换成明确的"无权限"提示，不依赖容易被忽略/误关闭的 alert()。
function renderPermissionDenied(containerId, featureName) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = `
        <div class="empty-state bg-white rounded-lg shadow-md p-6 mb-5 text-center">
            <div class="text-4xl mb-2">🔒</div>
            <div class="text-lg font-medium mb-2 text-gray-800">无权限访问${featureName}</div>
            <div class="text-gray-600">此功能仅管理员可用，请联系管理员获取权限</div>
        </div>
    `;
}

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
    const contentElement = document.getElementById(tabName + '-tab');
    if (contentElement) {
        contentElement.classList.add('active');
    } else {
        console.error('找不到内容元素:', tabName + '-tab');
        return;
    }

    // 设置当前导航项为活动状态
    let navItem;
    if (event && event.target) {
        navItem = event.target.closest('.nav-item');
    } else {
        // 如果没有event参数，通过tabName查找对应的导航项
        navItem = document.querySelector(`.nav-item[onclick*="${tabName}"]`);
    }
    
    if (navItem) {
        navItem.classList.add('active');
    }

    // 加载数据
    if (tabName === 'channels') loadChannels();
    else if (tabName === 'logs') loadLogs();
    else if (tabName === 'stats') loadStats();
    else if (tabName === 'settings') loadSystemInfo();
}

// 加载渠道列表
async function loadChannels() {
    try {
        console.log('正在加载配置，API地址:', API_BASE + '/manage/channels');
        const response = await fetch(`${API_BASE}/manage/channels`);
        
        if (response.status === 403) {
            renderPermissionDenied('channels-list', 'LLM渠道管理');
            return;
        }
        if (!response.ok) {
            console.error('请求失败，状态码:', response.status);
            showError(`请求失败，状态码: ${response.status}`);
            return;
        }
        
        const result = await response.json();
        console.log('API响应:', result);

        if (result.code === 0) {
            const channels = result.data || [];
            if (channels.length === 0) {
                document.getElementById('channels-list').innerHTML = `
                    <div class="empty-state bg-white rounded-lg shadow-md p-6 mb-5">
                        <div class="text-4xl mb-2">📡</div>
                        <div class="text-lg font-medium mb-2">暂无配置</div>
                        <div class="text-gray-600">点击"新建配置"添加第一个配置</div>
                    </div>
                `;
            } else {
                let html = '<table class="table border-collapse border border-gray-200 w-full"><thead><tr><th class="border border-gray-200 px-4 py-2 text-left bg-gray-50 font-medium text-gray-700">名称</th><th class="border border-gray-200 px-4 py-2 text-left bg-gray-50 font-medium text-gray-700">类型</th><th class="border border-gray-200 px-4 py-2 text-left bg-gray-50 font-medium text-gray-700">模型配置</th><th class="border border-gray-200 px-4 py-2 text-left bg-gray-50 font-medium text-gray-700">状态</th><th class="border border-gray-200 px-4 py-2 text-left bg-gray-50 font-medium text-gray-700">操作</th></tr></thead><tbody>';
                channels.forEach(ch => {
                    // 构建能力图标
                    let capabilityIcons = '';
                    if (ch.enable_web_search) {
                        capabilityIcons += '<span class="capability-icon-list web-search" title="已开启联网搜索">🌐</span>';
                    }
                    if (ch.enable_deep_thinking) {
                        capabilityIcons += '<span class="capability-icon-list deep-thinking" title="已开启深度思考">🧠</span>';
                    }
                    
                    html += `
                        <tr>
                            <td class="border border-gray-200 px-4 py-2">${ch.name}</td>
                            <td class="border border-gray-200 px-4 py-2">${ch.type}</td>
                            <td class="border border-gray-200 px-4 py-2">
                                <div class="model-config-display">
                                    <span class="model-name">${ch.models}</span>
                                    ${capabilityIcons}
                                    <button class="btn-config bg-blue-100 text-blue-700 hover:bg-blue-200 px-2 py-1 rounded text-xs font-medium cursor-pointer transition-all duration-300" 
                                            onclick="openModelConfigModal(${ch.id})" 
                                            title="配置模型参数">
                                        ⚙️ 参数配置
                                    </button>
                                    <span class="config-status text-xs">
                                        ${ch.has_model_config ? '✅ 已配置' : '⚠️ 默认'}
                                    </span>
                                </div>
                            </td>
                            <td class="border border-gray-200 px-4 py-2">
                                <button 
                                    class="btn ${ch.status ? 'bg-green-600 text-white hover:bg-green-700' : 'bg-gray-200 text-gray-800 hover:bg-gray-300'} px-4 py-2 rounded-md font-medium text-sm cursor-pointer transition-all duration-300 inline-flex items-center gap-2" 
                                    onclick="toggleChannelStatus(${ch.id}, ${ch.status})"
                                    title="${ch.status ? '点击禁用此配置' : '点击启用此配置'}"
                                >
                                    ${ch.status ? '✓ 已启用' : '○ 已禁用'}
                                </button>
                            </td>
                            <td class="border border-gray-200 px-4 py-2">
                                <button class="bg-green-600 text-white hover:bg-green-700 px-4 py-2 rounded-md font-medium text-sm cursor-pointer transition-all duration-300 inline-flex items-center gap-2" 
                                        onclick="testChannel(${ch.id})" 
                                        title="测试已保存配置的API连接">测试</button>
                                <button class="bg-blue-600 text-white hover:bg-blue-700 px-4 py-2 rounded-md font-medium text-sm cursor-pointer transition-all duration-300 inline-flex items-center gap-2" onclick="editChannel(${ch.id})">编辑</button>
                                <button class="bg-red-600 text-white hover:bg-red-700 px-4 py-2 rounded-md font-medium text-sm cursor-pointer transition-all duration-300 inline-flex items-center gap-2" onclick="deleteChannel(${ch.id})">删除</button>
                            </td>
                        </tr>
                    `;
                });
                html += '</tbody></table>';
                document.getElementById('channels-list').innerHTML = html;
            }
        } else {
            console.error('API返回错误:', result);
            const message = result.message || result.detail || '未知错误';
            showError('加载配置失败: ' + message);
        }
    } catch (error) {
        console.error('请求异常:', error);
        const message = error.message || error || '未知错误';
        showError('加载配置异常: ' + message);
    }
}

// 加载日志列表
async function loadLogs() {
    try {
        const response = await fetch(`${API_BASE}/logs?limit=10`);
        if (response.status === 403) {
            renderPermissionDenied('logs-list', 'API日志');
            return;
        }
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
                let html = '<table class="table"><thead><tr><th>模型</th><th>配置</th><th>状态</th><th>时间</th></tr></thead><tbody>';
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
        if (response.status === 403) {
            renderPermissionDenied('stats-content', '统计信息');
            return;
        }
        const result = await response.json();

        if (result.code === 0) {
            const stats = result.data || {};
            const html = `
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-label">系统状态</div>
                        <div class="stat-value">${stats.status || '未知'}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">更新时间</div>
                        <div class="stat-value">${new Date(stats.timestamp).toLocaleString()}</div>
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
        if (response.status === 403) {
            renderPermissionDenied('system-info', '系统信息');
            return;
        }
        const result = await response.json();

        if (result.code === 0) {
            const data = result.data || {};
            let html = '';
            for (const [key, value] of Object.entries(data)) {
                if (typeof value === 'object') {
                    html += `<div class="info-item"><strong>${key}:</strong> <pre>${JSON.stringify(value, null, 2)}</pre></div>`;
                } else {
                    html += `<div class="info-item"><strong>${key}:</strong> ${value}</div>`;
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

// 测试模型响应
async function testModelResponse(formType) {
    const prefix = formType === 'create' ? '' : 'edit-';
    const spinnerId = `test-${formType}-spinner`;
    const resultId = `test-${formType}-result`;
    
    // 获取表单数据
    const name = document.getElementById(`${prefix}name`).value;
    const type = document.getElementById(`${prefix}type`).value;
    const model = document.getElementById(`${prefix}models`).value;
    const baseUrl = document.getElementById(`${prefix}base_url`).value;
    let apiKey = document.getElementById(`${prefix}api_key`).value;
    
    // 如果是编辑模式且API密钥为空，使用原始密钥
    if (formType === 'edit' && !apiKey) {
        const form = document.getElementById('edit-channel-form');
        apiKey = form.dataset.originalApiKey || '';
    }
    
    // 验证必填字段
    if (!name || !type || !model || !baseUrl || !apiKey) {
        document.getElementById(resultId).innerHTML = `
            <div class="text-red-600">请填写所有必填字段后再测试。编辑模式下如果API密钥字段为空，将使用已保存的密钥进行测试。</div>
        `;
        return;
    }
    
    // 显示加载状态
    document.getElementById(spinnerId).style.display = 'inline-block';
    document.getElementById(resultId).innerHTML = '<div class="text-gray-600">测试中，请稍候...</div>';
    
    try {
        // 构建测试请求
        const testData = {
            name: name,
            type: type,
            models: model,
            base_url: baseUrl,
            api_key: apiKey,
            test_message: "请回复'测试成功'"
        };
        
        console.log('发送测试请求，参数:', testData);
        
        const response = await fetch(`${API_BASE}/manage/test-model-response`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(testData)
        });
        
        console.log('测试响应状态:', response.status, response.statusText);
        
        const result = await response.json();
        
        // 隐藏加载状态
        document.getElementById(spinnerId).style.display = 'none';
        
        if (result.code === 0) {
            document.getElementById(resultId).innerHTML = `
                <div class="text-green-600">
                    <div class="font-medium">✓ 测试成功</div>
                    <div class="text-sm mt-1">模型响应: ${result.data.response || '无响应内容'}</div>
                    <div class="text-xs text-gray-500 mt-1">响应时间: ${result.data.response_time || '未知'}ms</div>
                </div>
            `;
        } else {
            // 提取错误代码（用于判断错误类型）
            const errorCode = result.data ? result.data.error_code : '';
            const responseCode = result.data ? result.data.response_code : '';
            
            // 根据错误类型提供更友好的错误信息和解决建议
            let userMessage = result.message || '模型响应测试失败';
            let suggestions = '';
            
            if (errorCode === 'UNAUTHORIZED') {
                userMessage = 'API密钥无效或已过期';
                suggestions = `
                    <div class="text-xs mt-2 p-2 bg-yellow-50 rounded border border-yellow-200">
                        <div class="font-medium">解决建议:</div>
                        <ul class="list-disc list-inside mt-1">
                            <li>检查API密钥是否正确</li>
                            <li>确认API密钥是否已过期</li>
                            <li>访问 <a href="https://platform.openai.com/account/api-keys" target="_blank" class="text-blue-600 underline">OpenAI API密钥管理页面</a> 获取或更新密钥</li>
                        </ul>
                    </div>
                `;
            } else if (errorCode === 'INVALID_API_KEY_PLACEHOLDER') {
                userMessage = 'API密钥无效，请配置有效的OpenAI API密钥';
                suggestions = `
                    <div class="text-xs mt-2 p-2 bg-yellow-50 rounded border border-yellow-200">
                        <div class="font-medium">解决建议:</div>
                        <ul class="list-disc list-inside mt-1">
                            <li>编辑通道配置，输入有效的OpenAI API密钥</li>
                            <li>访问 <a href="https://platform.openai.com/account/api-keys" target="_blank" class="text-blue-600 underline">OpenAI API密钥管理页面</a> 获取API密钥</li>
                        </ul>
                    </div>
                `;
            } else if (errorCode === 'INVALID_ENDPOINT') {
                userMessage = 'API端点无效或不可访问';
                suggestions = `
                    <div class="text-xs mt-2 p-2 bg-yellow-50 rounded border border-yellow-200">
                        <div class="font-medium">解决建议:</div>
                        <ul class="list-disc list-inside mt-1">
                            <li>检查Base URL是否正确</li>
                            <li>确认URL格式为: https://api.openai.com/v1</li>
                            <li>确保网络可以访问OpenAI API</li>
                        </ul>
                    </div>
                `;
            } else if (errorCode === 'FORBIDDEN') {
                userMessage = 'API密钥权限不足';
                suggestions = `
                    <div class="text-xs mt-2 p-2 bg-yellow-50 rounded border border-yellow-200">
                        <div class="font-medium">解决建议:</div>
                        <ul class="list-disc list-inside mt-1">
                            <li>检查API密钥权限</li>
                            <li>确认账户状态正常</li>
                            <li>检查API使用配额</li>
                        </ul>
                    </div>
                `;
            } else if (responseCode >= 500 || errorCode === 'SERVER_ERROR' || errorCode === 'CONNECTION_ERROR') {
                userMessage = '连接失败，服务暂时不可用';
                suggestions = `
                    <div class="text-xs mt-2 p-2 bg-yellow-50 rounded border border-yellow-200">
                        <div class="font-medium">解决建议:</div>
                        <ul class="list-disc list-inside mt-1">
                            <li>检查网络连接</li>
                            <li>确认Base URL是否正确</li>
                            <li>稍后重试</li>
                        </ul>
                    </div>
                `;
            }
            
            let errorInfo = `
                <div class="font-medium">✗ 测试失败</div>
                <div class="text-sm mt-1">${userMessage}</div>
                ${suggestions}
            `;
            
            document.getElementById(resultId).innerHTML = `
                <div class="text-red-600">
                    ${errorInfo}
                </div>
            `;
        }
    } catch (error) {
        // 隐藏加载状态
        document.getElementById(spinnerId).style.display = 'none';
        document.getElementById(resultId).innerHTML = `
            <div class="text-red-600">
                <div class="font-medium">✗ 测试异常</div>
                <div class="text-sm mt-1">网络错误: ${error.message}</div>
            </div>
        `;
    }
}

// 打开创建配置模态框
function openCreateChannelModal() {
    document.getElementById('create-channel-modal').classList.add('active');
    document.getElementById('channel-form').reset();
    document.getElementById('modal-alert').innerHTML = '';
    // 清空测试结果
    document.getElementById('test-create-result').innerHTML = '';
}

// 关闭创建配置模态框
function closeCreateChannelModal() {
    document.getElementById('create-channel-modal').classList.remove('active');
}

// 提交配置表单
async function submitChannelForm(event) {
    event.preventDefault();

    const form = document.getElementById('channel-form');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    // 处理checkbox - FormData不会包含未选中的checkbox
    data.stream_output = document.getElementById('stream_output').checked;

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
            showSuccess('配置创建成功!');
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

// 切换错误详情显示
function toggleErrorDetails(detailsId) {
    const detailsElement = document.getElementById(detailsId);
    if (detailsElement) {
        detailsElement.classList.toggle('hidden');
    }
}

// 测试配置 - 使用新的代理测试端点
async function testChannel(channelId) {
    try {
        const response = await fetch(`${API_BASE}/manage/channels/${channelId}/test-via-proxy`, {
            method: 'POST'
        });

        // 调试：记录完整的响应以便分析
        console.log('配置连接测试完整响应:', {
            status: response.status,
            statusText: response.statusText,
            ok: response.ok,
            headers: Object.fromEntries(response.headers.entries())
        });
        
        // 先克隆响应以便调试，然后解析JSON
        const responseClone = response.clone();
        const result = await response.json();
        
        // 调试：输出原始响应文本
        responseClone.text().then(text => {
            console.log('原始响应文本:', text);
        });
        
        // 调试：记录解析后的结果
        console.log('解析后的响应结果:', result);
        
        // 处理不同的响应结构
        if (response.ok) {
            // 成功的响应
            alert('配置连接测试通过。');
            return;
        } else {
            // 错误的响应 - 处理不同的错误结构
            console.log('错误响应结构:', result);
            
            // 统一错误处理逻辑
            let errorCode = '';
            let responseCode = '';
            let errorMessage = '配置连接失败';
            let suggestions = '';
            
            // 检查是否有标准格式的错误响应
            if (result.data && result.data.error_code) {
                // 标准格式的错误响应
                errorCode = result.data.error_code;
                responseCode = result.data.response_code || response.status;
                errorMessage = result.message || '配置连接失败';
                console.log('使用标准格式错误响应:', { errorCode, responseCode, errorMessage });
            } else if (result.message && result.code) {
                // 另一种标准格式的错误响应
                errorCode = result.data ? result.data.error_code : '';
                responseCode = result.data ? result.data.response_code : response.status;
                errorMessage = result.message || '配置连接失败';
                console.log('使用另一种标准格式错误响应:', { errorCode, responseCode, errorMessage });
            } else if (typeof result === 'string') {
                // 字符串格式的错误响应
                errorMessage = result;
                // 从错误消息中提取错误代码
                if (errorMessage.includes('401') || errorMessage.includes('unauthorized') || errorMessage.includes('密钥')) {
                    errorCode = 'UNAUTHORIZED';
                } else if (errorMessage.includes('403') || errorMessage.includes('forbidden')) {
                    errorCode = 'FORBIDDEN';
                } else if (errorMessage.includes('404') || errorMessage.includes('not found') || errorMessage.includes('端点')) {
                    errorCode = 'INVALID_ENDPOINT';
                } else if (errorMessage.includes('timeout') || errorMessage.includes('超时')) {
                    errorCode = 'TIMEOUT_ERROR';
                } else if (errorMessage.includes('connection') || errorMessage.includes('网络')) {
                    errorCode = 'CONNECTION_ERROR';
                }
                console.log('使用字符串格式错误响应:', { errorCode, errorMessage });
            } else {
                // 其他格式的错误响应 - 尝试从各个字段中提取信息
                let rawMsg = result.message || result.detail || result.data?.detail || result.data?.message;
                errorMessage = (typeof rawMsg === 'object') ? JSON.stringify(rawMsg) : (rawMsg || '配置连接失败，请检查配置信息是否正确');
                
                // 尝试从result.data中获取错误代码
                if (result.data) {
                    errorCode = result.data.error_code || '';
                    responseCode = result.data.response_code || response.status;
                }
                
                // 如果还是无法获取错误代码，尝试从错误消息中提取
                if (!errorCode && typeof errorMessage === 'string') {
                    if (errorMessage.includes('401') || errorMessage.includes('unauthorized') || errorMessage.includes('密钥')) {
                        errorCode = 'UNAUTHORIZED';
                    } else if (errorMessage.includes('403') || errorMessage.includes('forbidden')) {
                        errorCode = 'FORBIDDEN';
                    } else if (errorMessage.includes('404') || errorMessage.includes('not found') || errorMessage.includes('端点')) {
                        errorCode = 'INVALID_ENDPOINT';
                    } else if (errorMessage.includes('timeout') || errorMessage.includes('超时')) {
                        errorCode = 'TIMEOUT_ERROR';
                    } else if (errorMessage.includes('connection') || errorMessage.includes('网络')) {
                        errorCode = 'CONNECTION_ERROR';
                    }
                }
                
                console.log('使用其他格式错误响应:', { errorCode, responseCode, errorMessage, result });
            }
            
            // 根据错误代码提供更友好的错误信息和解决建议
            if (errorCode === 'UNAUTHORIZED') {
                errorMessage = 'API密钥无效或已过期';
                suggestions = '\n\n解决建议:\n1. 检查API密钥是否正确\n2. 确认API密钥是否已过期\n3. 访问 https://platform.openai.com/account/api-keys 获取或更新密钥';
            } else if (errorCode === 'FORBIDDEN') {
                errorMessage = 'API密钥权限不足';
                suggestions = '\n\n解决建议:\n1. 检查API密钥权限\n2. 确认账户状态正常\n3. 检查API使用配额';
            } else if (errorCode === 'INVALID_ENDPOINT') {
                errorMessage = 'API端点无效或不可访问';
                suggestions = '\n\n解决建议:\n1. 检查Base URL是否正确\n2. 确认URL格式为: https://api.openai.com/v1\n3. 确保网络可以访问OpenAI API';
            } else if (errorCode === 'TIMEOUT_ERROR') {
                errorMessage = '请求超时';
                suggestions = '\n\n解决建议:\n1. 检查网络连接\n2. 稍后重试';
            } else if (errorCode === 'CONNECTION_ERROR') {
                errorMessage = '网络连接失败';
                suggestions = '\n\n解决建议:\n1. 检查网络连接\n2. 确认Base URL是否正确\n3. 检查防火墙设置';
            } else if (responseCode >= 500) {
                errorMessage = '服务器内部错误';
                suggestions = '\n\n解决建议:\n1. 稍后重试\n2. 检查 https://status.openai.com/ 查看服务状态';
            }
            
            // 构建最终显示给用户的错误消息
            const finalMessage = errorMessage + suggestions;
            alert(finalMessage);
        }
    } catch (error) {
        // 捕获网络错误或其他异常，显示用户友好的错误信息
        console.error('测试连接异常:', error);
        
        let errorMessage = '测试连接失败';
        let suggestions = '\n\n解决建议:\n1. 检查网络连接\n2. 确认服务是否正在运行';
        
        // 尝试从错误中提取更多信息
        if (error.message) {
            if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
                errorMessage = '网络连接失败';
                suggestions = '\n\n解决建议:\n1. 检查网络连接\n2. 确认服务是否正在运行\n3. 检查防火墙设置';
            } else if (error.message.includes('timeout') || error.message.includes('超时')) {
                errorMessage = '请求超时';
                suggestions = '\n\n解决建议:\n1. 检查网络连接\n2. 稍后重试';
            }
        }
        
        // 构建最终显示给用户的错误消息
        const finalMessage = errorMessage + suggestions;
        alert(finalMessage);
    }
}

// 删除配置
async function deleteChannel(channelId) {
    if (confirm('确定要删除此配置吗?')) {
        try {
            const response = await fetch(`${API_BASE}/manage/channels/${channelId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.code === 0) {
                showSuccess('配置删除成功!');
                loadChannels();
            } else {
                showError('删除失败: ' + result.message);
            }
        } catch (error) {
            showError('删除异常: ' + error.message);
        }
    }
}

// 切换配置状态
async function toggleChannelStatus(channelId, currentStatus) {
    // 先获取当前配置列表，以便获取配置名称
    try {
        const listResponse = await fetch(`${API_BASE}/manage/channels`);
        const listResult = await listResponse.json();
        
        if (listResult.code !== 0) {
            showError('获取配置列表失败');
            return;
        }
        
        const channels = listResult.data || [];
        const currentChannel = channels.find(ch => ch.id === channelId);
        const channelName = currentChannel ? currentChannel.name : `配置 ID: ${channelId}`;
        
        // 简化确认消息，不再提示会禁用其他配置
        const action = currentStatus ? '禁用' : '启用';
        const confirmMessage = `确定要${action} "${channelName}" 吗？`;
        
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
            showSuccess(`配置${action}成功!`);
            loadChannels();
        } else {
            showError(`${action}失败: ${result.message}`);
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
            document.getElementById('edit-name').value = channel.name;
            document.getElementById('edit-type').value = channel.type;
            document.getElementById('edit-models').value = channel.models;
            document.getElementById('edit-base_url').value = channel.base_url;
            document.getElementById('edit-api_key').value = '';
            // 回显流式输出配置（默认为true）
            document.getElementById('edit-stream_output').checked = channel.stream_output !== false;
            
            // 存储配置ID和API密钥用于提交和测试
            form.dataset.channelId = channelId;
            form.dataset.originalApiKey = channel.api_key || '';
            
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
    // 清空测试结果
    document.getElementById('test-edit-result').innerHTML = '';
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
    
    // 处理checkbox - FormData不会包含未选中的checkbox
    data.stream_output = document.getElementById('edit-stream_output').checked;

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
            showSuccessEdit('配置更新成功!');
            closeEditChannelModal();
            loadChannels();
        } else {
            const msg = result.message || result.detail || result.data?.detail || '未知错误';
            showAlertEdit('error', '更新失败: ' + msg);
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
    console.error('错误信息:', message);
    alert(message);
}

function showAlert(type, message) {
    document.getElementById('modal-alert').innerHTML = `
        <div class="alert ${type}">${message}</div>
    `;
}

function showSuccessEdit(message) {
    document.getElementById('edit-modal-alert').innerHTML = `
        <div class="alert success">${message}</div>
    `;
    setTimeout(() => {
        document.getElementById('edit-modal-alert').innerHTML = '';
    }, 3000);
}

function showAlertEdit(type, message) {
    document.getElementById('edit-modal-alert').innerHTML = `
        <div class="alert ${type}">${message}</div>
    `;
}

// 刷新渠道列表
function refreshChannels() {
    loadChannels();
}

// 刷新日志列表
function refreshLogs() {
    loadLogs();
}



// 确保所有函数都在全局作用域中可用
window.switchTab = switchTab;
window.openCreateChannelModal = openCreateChannelModal;
window.closeCreateChannelModal = closeCreateChannelModal;
window.submitChannelForm = submitChannelForm;
window.testChannel = testChannel;
window.deleteChannel = deleteChannel;
window.toggleChannelStatus = toggleChannelStatus;
window.editChannel = editChannel;
window.closeEditChannelModal = closeEditChannelModal;
window.submitEditChannelForm = submitEditChannelForm;
window.testModelResponse = testModelResponse;
window.toggleErrorDetails = toggleErrorDetails;
window.refreshChannels = refreshChannels;
window.refreshLogs = refreshLogs;
window.refreshStats = loadStats;
window.refreshSystemInfo = loadSystemInfo;
window.showError = showError;
window.showSuccess = showSuccess;
window.showAlert = showAlert;
window.showAlertEdit = showAlertEdit;
window.showSuccessEdit = showSuccessEdit;
window.updateBaseUrl = updateBaseUrl;
window.updateEditBaseUrl = updateEditBaseUrl;

// 各AI供应商的官方API Url
const API_BASE_URLS = {
    'openai': 'https://api.openai.com/v1',
    'google': 'https://generativelanguage.googleapis.com/v1beta',
    'deepseek': 'https://api.deepseek.com/v1',
    'claude': 'https://api.anthropic.com/v1',
    'qwen': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'custom': ''
};

// 各AI供应商的官方文档URL
const API_DOCS = {
    'openai': 'https://platform.openai.com/docs/api-reference',
    'google': 'https://ai.google.dev/docs',
    'deepseek': 'https://platform.deepseek.com/api-docs/',
    'claude': 'https://docs.anthropic.com/claude/reference',
    'qwen': 'https://help.aliyun.com/zh/dashscope/developer-reference/api-reference'
};

// 各AI供应商的模型列表端点（用于测试连接）
const MODELS_ENDPOINTS = {
    'openai': '/models',
    'google': '/models',
    'deepseek': '/models',
    'claude': '/messages/batches', // Claude使用不同的端点
    'qwen': '/models',
    'custom': '/models'
};

// 各AI供应商的聊天端点（用于实际API调用）
const CHAT_ENDPOINTS = {
    'openai': '/chat/completions',
    'google': '/models/{model}:generateContent', // Google使用模型特定的端点
    'deepseek': '/chat/completions',
    'claude': '/messages',
    'qwen': '/chat/completions',
    'custom': '/chat/completions'
};

// 更新创建配置表单中的API Url
function updateBaseUrl() {
    const typeSelect = document.getElementById('type');
    const baseUrlInput = document.getElementById('base_url');
    const selectedType = typeSelect.value;
    
    if (selectedType && API_BASE_URLS[selectedType]) {
        baseUrlInput.value = API_BASE_URLS[selectedType];
        
        // 如果是GoogleAI，也更新模型名称的示例
        if (selectedType === 'google') {
            document.getElementById('models').placeholder = '如: gemini-1.5-flash 或 gemini-2.0-flash-exp';
        } else if (selectedType === 'openai') {
            document.getElementById('models').placeholder = '如: gpt-3.5-turbo';
        } else if (selectedType === 'deepseek') {
            document.getElementById('models').placeholder = '如: deepseek-chat';
        } else if (selectedType === 'claude') {
            document.getElementById('models').placeholder = '如: claude-3-haiku-20240307';
        } else if (selectedType === 'qwen') {
            document.getElementById('models').placeholder = '如: qwen-turbo';
        }
    }
}

// 更新编辑配置表单中的API Url
function updateEditBaseUrl() {
    const typeSelect = document.getElementById('edit-type');
    const baseUrlInput = document.getElementById('edit-base_url');
    const selectedType = typeSelect.value;
    
    if (selectedType && API_BASE_URLS[selectedType]) {
        baseUrlInput.value = API_BASE_URLS[selectedType];
        
        // 如果是GoogleAI，也更新模型名称的示例
        if (selectedType === 'google') {
            document.getElementById('edit-models').placeholder = '如: gemini-1.5-flash 或 gemini-2.0-flash-exp';
        } else if (selectedType === 'openai') {
            document.getElementById('edit-models').placeholder = '如: gpt-3.5-turbo';
        } else if (selectedType === 'deepseek') {
            document.getElementById('edit-models').placeholder = '如: deepseek-chat';
        } else if (selectedType === 'claude') {
            document.getElementById('edit-models').placeholder = '如: claude-3-haiku-20240307';
        } else if (selectedType === 'qwen') {
            document.getElementById('edit-models').placeholder = '如: qwen-turbo';
        }
    }
}

// 导出loadChannels到全局，供model-config.js调用
window.loadChannels = loadChannels;

// 页面加载时初始化
window.addEventListener('load', () => {
    // 初始化模型配置
    initModelConfig();
    
    loadChannels();
});