// 模型配置管理JavaScript

// 模型能力配置表
const MODEL_CAPABILITIES = {
  // 强制深度思考的模型（推理模型，思考功能内置且不可关闭）
  'deepseek-reasoner': { thinking: 'forced', web_search: false, thinking_budget_default: 8192 },
  'deepseek-r1': { thinking: 'forced', web_search: false, thinking_budget_default: 8192 },
  'o1-preview': { thinking: 'forced', web_search: false },
  'o1-mini': { thinking: 'forced', web_search: false },
  'o1': { thinking: 'forced', web_search: false },
  'o3-mini': { thinking: 'forced', web_search: false },
  'o3': { thinking: 'forced', web_search: false },
  
  // 可选深度思考的模型
  'gemini-2.5-flash': { thinking: 'optional', web_search: true, thinking_budget_default: 8192 },
  'gemini-2.5-pro': { thinking: 'optional', web_search: true, thinking_budget_default: 16384 },
  'gemini-2.0-flash': { thinking: 'optional', web_search: true, thinking_budget_default: 8192 },
  'gemini-2.0-flash-thinking': { thinking: 'optional', web_search: true, thinking_budget_default: 8192 },
  'claude-3-5-sonnet': { thinking: 'optional', web_search: false, thinking_budget_default: 10000 },
  'claude-3.5-sonnet': { thinking: 'optional', web_search: false, thinking_budget_default: 10000 },
  'claude-sonnet-4': { thinking: 'optional', web_search: false, thinking_budget_default: 10000 },
  'claude-opus-4': { thinking: 'optional', web_search: false, thinking_budget_default: 16384 },
  'claude-3-opus': { thinking: 'optional', web_search: false, thinking_budget_default: 16384 },
  
  // 仅支持联网搜索的模型
  'deepseek-chat': { thinking: 'none', web_search: true },
  'gemini-1.5-flash': { thinking: 'none', web_search: true },
  'gemini-1.5-pro': { thinking: 'none', web_search: true },
  
  // 不支持深度思考和联网搜索的模型
  'gpt-4': { thinking: 'none', web_search: false },
  'gpt-4o': { thinking: 'none', web_search: false },
  'gpt-4o-mini': { thinking: 'none', web_search: false },
  'gpt-4-turbo': { thinking: 'none', web_search: false },
  'gpt-3.5-turbo': { thinking: 'none', web_search: false },
  'claude-3-haiku': { thinking: 'none', web_search: false },
  
  // 默认配置（未知模型）
  '_default': { thinking: 'optional', web_search: false, thinking_budget_default: 8192 }
};

// 获取模型能力配置
function getModelCapabilities(modelName) {
  if (!modelName) return MODEL_CAPABILITIES['_default'];
  
  const lowerName = modelName.toLowerCase();
  
  // 精确匹配
  if (MODEL_CAPABILITIES[lowerName]) {
    return MODEL_CAPABILITIES[lowerName];
  }
  
  // 模糊匹配
  for (const [key, value] of Object.entries(MODEL_CAPABILITIES)) {
    if (key !== '_default' && lowerName.includes(key)) {
      return value;
    }
  }
  
  // 基于模型名称推断
  if (lowerName.includes('reasoner') || lowerName.includes('-r1')) {
    return { thinking: 'forced', web_search: false, thinking_budget_default: 8192 };
  }
  if (lowerName.includes('o1') || lowerName.includes('o3')) {
    return { thinking: 'forced', web_search: false };
  }
  if (lowerName.includes('gemini-2')) {
    return { thinking: 'optional', web_search: true, thinking_budget_default: 8192 };
  }
  if (lowerName.includes('claude')) {
    return { thinking: 'optional', web_search: false, thinking_budget_default: 10000 };
  }
  
  return MODEL_CAPABILITIES['_default'];
}

// 当前配置状态
let currentChannelId = null;
let currentModelConfig = null;
let currentModelName = null;

// 初始化模型配置
function initModelConfig() {
  console.log('Initializing model config...');
  // 检查预设配置是否已加载
  if (typeof PRESET_CONFIGS === 'undefined') {
    console.error('预设配置未加载，请确保index.html已正确引入model_task_presets.js');
  } else {
    console.log('模型任务预设已就绪');
  }
  
  // 创建模态框（如果不存在）
  const modal = document.getElementById('model-config-modal');
  console.log('Modal exists on init:', modal);
  if (!modal) {
    console.log('Creating modal on init...');
    // 直接使用基本模态框，避免HTML文件加载问题
    createBasicModelConfigModal();
    console.log('Modal creation complete on init');
    // 添加DOM变化观察器，监控模态框是否被意外移除
    setupModalObserver();
  } else {
    // 即使模态框已存在，也添加观察器
    setupModalObserver();
  }
}

// 设置模态框观察器
function setupModalObserver() {
  const modal = document.getElementById('model-config-modal');
  if (!modal) return;
  
  const observer = new MutationObserver(mutations => {
    mutations.forEach(mutation => {
      if (mutation.type === 'childList') {
        // 检查模态框是否被移除
        const modalExists = document.getElementById('model-config-modal');
        if (!modalExists) {
          console.warn('模态框被意外移除，重新创建...');
          createModelConfigModal();
        }
      }
    });
  });
  
  // 观察document.body的变化
  observer.observe(document.body, {
    childList: true
  });
  
  console.log('Modal observer set up');
}

// 创建模型配置模态框
function createModelConfigModal() {
    return fetch('/shared/html/model-config-modal.html')
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.text();
    })
    .then(html => {
      // 检查是否是有效的HTML内容
      if (!html || !html.includes('model-config-modal')) {
        throw new Error('Invalid HTML content');
      }
      
      const modalDiv = document.createElement('div');
      modalDiv.innerHTML = html;
      const modalElement = modalDiv.firstElementChild;
      console.log('Modal element from HTML file:', modalElement);
      if (modalElement && modalElement.id === 'model-config-modal') {
        document.body.appendChild(modalElement);
        console.log('Modal appended to body from HTML file');
      } else {
        console.error('No valid modal element found in HTML file');
        // 如果HTML文件中没有有效模态框，创建基本模态框
        createBasicModelConfigModal();
      }
    })
    .catch(error => {
      console.error('加载模型配置模态框失败:', error);
      // 如果加载失败，创建基本模态框
      createBasicModelConfigModal();
      // 不再抛出错误，而是返回成功的Promise
      return Promise.resolve();
    });
}

// 创建基本模态框（备用方案）
function createBasicModelConfigModal() {
  console.log('Creating basic model config modal');
  const modalHTML = `
    <div id="model-config-modal" class="modal">
      <div class="modal-backdrop" onclick="closeModalOnBackdrop(event)"></div>
      <div class="modal-content">
        <div class="modal-header">
          <div class="header-left">
            <h3>模型参数配置</h3>
            <span class="model-context">
              <span class="context-badge">通道: <strong id="channel-name"></strong></span>
              <span class="context-badge">模型: <strong id="model-name"></strong></span>
            </span>
          </div>
          <button class="modal-close" onclick="closeModelConfigModal()">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        
        <div class="modal-body">
          <div class="config-tabs">
            <button class="tab-button active" onclick="switchModalTab('basic')">基础参数</button>
            <button class="tab-button" onclick="switchModalTab('advanced')">高级参数</button>
            <button class="tab-button" onclick="switchModalTab('prompt')">系统提示</button>
            <button class="tab-button" onclick="switchModalTab('presets')">预设配置</button>
          </div>
          
          <div class="modal-tab-content active" id="basic-tab">
            <div class="param-grid">
              <div class="param-card">
                <div class="param-header">
                  <label for="temperature">Temperature</label>
                  <span class="param-value" id="temperature-value">0.7</span>
                </div>
                <div class="param-control">
                  <input type="range" id="temperature" min="0" max="2" step="0.1" value="0.7" 
                         oninput="updateParameterDisplay('temperature')" class="styled-range">
                  <div class="range-track">
                    <div class="range-progress" style="width: 35%;"></div>
                  </div>
                </div>
                <div class="param-desc">控制输出的随机性，值越低越确定</div>
              </div>
              
              <div class="param-card">
                <div class="param-header">
                  <label for="top_p">Top P</label>
                  <span class="param-value" id="top_p-value">1.0</span>
                </div>
                <div class="param-control">
                  <input type="range" id="top_p" min="0" max="1" step="0.05" value="1.0" 
                         oninput="updateParameterDisplay('top_p')" class="styled-range">
                  <div class="range-track">
                    <div class="range-progress" style="width: 100%;"></div>
                  </div>
                </div>
                <div class="param-desc">控制生成的词汇范围</div>
              </div>
              
              <div class="param-card">
                <div class="param-header">
                  <label for="max_tokens">Max Tokens</label>
                  <span class="param-value" id="max_tokens-value">2000</span>
                </div>
                <div class="param-control">
                  <input type="range" id="max_tokens" min="100" max="8192" step="1" value="2000" 
                         oninput="updateParameterDisplay('max_tokens')" class="styled-range">
                  <div class="range-track">
                    <div class="range-progress" style="width: 48%;"></div>
                  </div>
                </div>
                <div class="param-desc">控制生成内容的最大长度</div>
              </div>
              
              <div class="param-card">
                <div class="param-header">
                  <label for="frequency_penalty">Frequency Penalty</label>
                  <span class="param-value" id="frequency_penalty-value">0</span>
                </div>
                <div class="param-control">
                  <input type="range" id="frequency_penalty" min="-2" max="2" step="0.1" value="0" 
                         oninput="updateParameterDisplay('frequency_penalty')" class="styled-range">
                  <div class="range-track">
                    <div class="range-progress" style="width: 50%;"></div>
                  </div>
                </div>
                <div class="param-desc">降低重复词汇的出现概率</div>
              </div>
              
              <div class="param-card">
                <div class="param-header">
                  <label for="presence_penalty">Presence Penalty</label>
                  <span class="param-value" id="presence_penalty-value">0</span>
                </div>
                <div class="param-control">
                  <input type="range" id="presence_penalty" min="-2" max="2" step="0.1" value="0" 
                         oninput="updateParameterDisplay('presence_penalty')" class="styled-range">
                  <div class="range-track">
                    <div class="range-progress" style="width: 50%;"></div>
                  </div>
                </div>
                <div class="param-desc">鼓励谈论新的话题</div>
              </div>
            </div>
          </div>
          
          <div class="modal-tab-content" id="advanced-tab">
            <div class="param-grid">
              <div class="param-card">
                <div class="param-header">
                  <label for="stop">Stop Sequences</label>
                </div>
                <div class="param-control">
                  <input type="text" id="stop" placeholder="例如: [\\n, \\"\\"]" class="text-input">
                </div>
                <div class="param-desc">触发停止的字符串序列</div>
              </div>
              
              <div class="param-card">
                <div class="param-header">
                  <label for="logit_bias">Logit Bias</label>
                </div>
                <div class="param-control">
                  <input type="text" id="logit_bias" placeholder="例如: {\\"50256\\": -100}" class="text-input">
                </div>
                <div class="param-desc">控制特定token的生成概率</div>
              </div>
              
              <div class="param-card">
                <div class="param-header">
                  <label for="repetition_penalty">Repetition Penalty</label>
                  <span class="param-value" id="repetition_penalty-value">1.0</span>
                </div>
                <div class="param-control">
                  <input type="range" id="repetition_penalty" min="1" max="2" step="0.1" value="1.0" 
                         oninput="updateParameterDisplay('repetition_penalty')" class="styled-range">
                  <div class="range-track">
                    <div class="range-progress" style="width: 0%;"></div>
                  </div>
                </div>
                <div class="param-desc">惩罚重复的词语或短语</div>
              </div>
            </div>
            
            <!-- 模型能力扩展区域 -->
            <div class="capability-section">
              <h4 class="section-title">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="3"></circle>
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                </svg>
                模型能力扩展
              </h4>
              
              <!-- 深度思考/推理 -->
              <div class="capability-card" id="thinking-capability-card">
                <div class="capability-header">
                  <div class="capability-icon">🧠</div>
                  <div class="capability-title">
                    <span>深度思考/推理</span>
                    <span class="capability-status" id="thinking-status"></span>
                  </div>
                  <div class="toggle-switch">
                    <input type="checkbox" id="enable_deep_thinking" class="toggle-input" onchange="onThinkingToggleChange()">
                    <label for="enable_deep_thinking" class="toggle-label"></label>
                  </div>
                </div>
                <div class="capability-desc" id="thinking-desc">激活模型的扩展推理能力，适用于复杂问题分析</div>
                
                <!-- 思考预算配置（仅可选模型显示） -->
                <div class="capability-options" id="thinking-options">
                  <div class="option-item">
                    <div class="option-header">
                      <label for="thinking_budget">思考预算 (Thinking Budget)</label>
                      <span class="param-value" id="thinking_budget-value">8192</span>
                      <span class="option-unit">tokens</span>
                    </div>
                    <div class="param-control">
                      <input type="range" id="thinking_budget" min="1024" max="32768" step="1024" value="8192" 
                             oninput="updateParameterDisplay('thinking_budget')" class="styled-range">
                      <div class="range-track">
                        <div class="range-progress" id="thinking_budget-progress" style="width: 22%;"></div>
                      </div>
                    </div>
                    <div class="option-desc">控制模型用于推理的token数量，值越大推理越深入</div>
                  </div>
                  
                  <div class="option-item">
                    <div class="option-header">
                      <label for="include_thoughts">返回思考过程</label>
                    </div>
                    <div class="param-control">
                      <div class="toggle-switch small">
                        <input type="checkbox" id="include_thoughts" class="toggle-input">
                        <label for="include_thoughts" class="toggle-label"></label>
                      </div>
                    </div>
                    <div class="option-desc">在响应中包含模型的推理摘要</div>
                  </div>
                </div>
              </div>
              
              <!-- 联网搜索 -->
              <div class="capability-card" id="search-capability-card">
                <div class="capability-header">
                  <div class="capability-icon">🌐</div>
                  <div class="capability-title">
                    <span>联网搜索</span>
                    <span class="capability-status" id="search-status"></span>
                  </div>
                  <div class="toggle-switch">
                    <input type="checkbox" id="enable_web_search" class="toggle-input">
                    <label for="enable_web_search" class="toggle-label"></label>
                  </div>
                </div>
                <div class="capability-desc" id="search-desc">允许模型访问互联网获取实时信息</div>
              </div>
            </div>
          </div>
          
          <div class="modal-tab-content" id="prompt-tab">
            <div class="prompt-container">
              <div class="prompt-header">
                <h4>系统提示词</h4>
                <div class="prompt-actions">
                  <button class="action-button" onclick="expandSystemPrompt()">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path>
                    </svg>
                    展开
                  </button>
                  <button class="action-button" onclick="shrinkSystemPrompt()">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"></path>
                    </svg>
                    收起
                  </button>
                  <button class="action-button" onclick="resetSystemPrompt()">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M4 12h8m-4-4v8"></path>
                      <path d="M14 4h6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-6"></path>
                      <path d="M14 10h4"></path>
                    </svg>
                    重置
                  </button>
                </div>
              </div>
              <div class="prompt-editor">
                <textarea id="system_prompt" rows="8" placeholder="输入系统提示词，用于指导AI助手的行为..." class="prompt-textarea"></textarea>
                <div class="char-counter">
                  <span id="char-count">0</span> / 5000
                  <div class="char-bar">
                    <div class="char-progress" id="char-progress"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="modal-tab-content" id="presets-tab">
            <div id="preset-info" class="preset-notification"></div>
            <div class="presets-container">
              <div class="preset-card" onclick="applyPreset('general_chat')">
                <div class="preset-icon">💬</div>
                <div class="preset-info">
                  <h5>通用对话</h5>
                  <p>日常问答、数据咨询、概念解释等通用交互场景</p>
                </div>
              </div>
              
              <div class="preset-card" onclick="applyPreset('param_extraction')">
                <div class="preset-icon">🎯</div>
                <div class="preset-info">
                  <h5>参数推断</h5>
                  <p>从自然语言中提取SOP任务参数，适用于任务启动前的意图识别</p>
                </div>
              </div>
              
              <div class="preset-card" onclick="applyPreset('result_explanation')">
                <div class="preset-icon">📊</div>
                <div class="preset-info">
                  <h5>结果解释</h5>
                  <p>将分析结果转化为业务语言，突出关键发现和建议</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" onclick="resetToDefaults()">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 12h8m-4-4v8"></path>
              <path d="M14 4h6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-6"></path>
              <path d="M14 10h4"></path>
            </svg>
            恢复默认
          </button>
          <button type="button" class="btn btn-secondary" onclick="closeModelConfigModal()">取消</button>
          <button type="button" class="btn btn-primary" onclick="saveModelConfig()">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
              <polyline points="17 21 17 13 7 13 7 21"></polyline>
              <polyline points="7 3 7 8 15 8"></polyline>
            </svg>
            保存配置
            <span id="save-spinner" class="spinner" style="display: none;"></span>
          </button>
        </div>
      </div>
    </div>
  `;
  
  const modalDiv = document.createElement('div');
  modalDiv.innerHTML = modalHTML;
  const modalElement = modalDiv.firstElementChild;
  console.log('Modal element created:', modalElement);
  if (modalElement) {
    document.body.appendChild(modalElement);
  } else {
    console.error('Failed to create modal element from HTML');
  }
}

// 打开模型配置模态框
function openModelConfigModal(channelId) {
  console.log('openModelConfigModal called with channelId:', channelId);
  currentChannelId = channelId;
  
  // 确保模态框已加载
  let modal = document.getElementById('model-config-modal');
  if (!modal) {
    // 直接使用基本模态框，避免HTML文件加载问题
    createBasicModelConfigModal();
    modal = document.getElementById('model-config-modal');
  }
  
  if (modal) {
    // 显示模态框
    modal.classList.add('active');
    
    // 加载通道信息
    loadChannelInfo(channelId)
      .then(channelInfo => {
        // 设置通道信息
        document.getElementById('channel-name').textContent = channelInfo.name;
        document.getElementById('model-name').textContent = channelInfo.models;
        
        // 保存当前模型名称
        currentModelName = channelInfo.models;
        
        // 根据模型名称更新Max Tokens控件
        updateMaxTokensControl(channelInfo.models);
        
        // 根据模型能力更新UI状态
        updateCapabilityUI(channelInfo.models);
        
        // 加载模型配置
        return loadModelConfig(channelId);
      })
      .then(config => {
        currentModelConfig = config;
        // 填充表单
        fillConfigForm(config);
      })
      .catch(error => {
        console.error('打开模型配置失败:', error);
        showError('打开模型配置失败: ' + error.message);
      });
  } else {
    console.error('模态框创建失败，检查DOM:', document.getElementById('model-config-modal'));
    showError('模态框创建失败');
  }
}

// 更新模型能力UI状态
function updateCapabilityUI(modelName) {
  const capabilities = getModelCapabilities(modelName);
  
  // 更新深度思考UI
  updateThinkingUI(capabilities);
  
  // 更新联网搜索UI
  updateWebSearchUI(capabilities);
}

// 更新深度思考UI状态
function updateThinkingUI(capabilities) {
  const thinkingCard = document.getElementById('thinking-capability-card');
  const thinkingToggle = document.getElementById('enable_deep_thinking');
  const thinkingStatus = document.getElementById('thinking-status');
  const thinkingDesc = document.getElementById('thinking-desc');
  const thinkingOptions = document.getElementById('thinking-options');
  const thinkingBudget = document.getElementById('thinking_budget');
  
  if (!thinkingCard || !thinkingToggle) return;
  
  // 移除所有状态类
  thinkingCard.classList.remove('forced', 'disabled', 'optional');
  
  switch (capabilities.thinking) {
    case 'forced':
      // 强制开启：开关选中但禁用
      thinkingToggle.checked = true;
      thinkingToggle.disabled = true;
      thinkingCard.classList.add('forced');
      thinkingStatus.textContent = '(默认开启)';
      thinkingStatus.className = 'capability-status status-forced';
      thinkingDesc.textContent = '此模型默认启用深度思考功能，无法关闭';
      // 隐藏思考预算选项（强制模型通常有内置配置）
      if (thinkingOptions) thinkingOptions.style.display = 'none';
      break;
      
    case 'optional':
      // 可选：开关可操作
      thinkingToggle.disabled = false;
      thinkingCard.classList.add('optional');
      thinkingStatus.textContent = '(可选)';
      thinkingStatus.className = 'capability-status status-optional';
      thinkingDesc.textContent = '激活模型的扩展推理能力，适用于复杂问题分析';
      // 显示思考预算选项
      if (thinkingOptions) thinkingOptions.style.display = 'block';
      // 设置默认思考预算
      if (thinkingBudget && capabilities.thinking_budget_default) {
        thinkingBudget.value = capabilities.thinking_budget_default;
        updateParameterDisplay('thinking_budget');
      }
      break;
      
    case 'none':
    default:
      // 不支持：开关禁用且未选中
      thinkingToggle.checked = false;
      thinkingToggle.disabled = true;
      thinkingCard.classList.add('disabled');
      thinkingStatus.textContent = '(不支持)';
      thinkingStatus.className = 'capability-status status-disabled';
      thinkingDesc.textContent = '此模型不支持深度思考功能';
      // 隐藏思考预算选项
      if (thinkingOptions) thinkingOptions.style.display = 'none';
      break;
  }
  
  // 更新思考选项的显示状态
  onThinkingToggleChange();
}

// 更新联网搜索UI状态
function updateWebSearchUI(capabilities) {
  const searchCard = document.getElementById('search-capability-card');
  const searchToggle = document.getElementById('enable_web_search');
  const searchStatus = document.getElementById('search-status');
  const searchDesc = document.getElementById('search-desc');
  
  if (!searchCard || !searchToggle) return;
  
  // 移除所有状态类
  searchCard.classList.remove('disabled', 'optional');
  
  if (capabilities.web_search) {
    // 支持联网搜索
    searchToggle.disabled = false;
    searchCard.classList.add('optional');
    searchStatus.textContent = '(可选)';
    searchStatus.className = 'capability-status status-optional';
    searchDesc.textContent = '允许模型访问互联网获取实时信息';
  } else {
    // 不支持联网搜索
    searchToggle.checked = false;
    searchToggle.disabled = true;
    searchCard.classList.add('disabled');
    searchStatus.textContent = '(不支持)';
    searchStatus.className = 'capability-status status-disabled';
    searchDesc.textContent = '此模型不支持联网搜索功能';
  }
}

// 深度思考开关变化处理
function onThinkingToggleChange() {
  const thinkingToggle = document.getElementById('enable_deep_thinking');
  const thinkingOptions = document.getElementById('thinking-options');
  const capabilities = getModelCapabilities(currentModelName);
  
  if (!thinkingOptions) return;
  
  // 只有可选模型且开关开启时才显示选项
  if (capabilities.thinking === 'optional' && thinkingToggle && thinkingToggle.checked) {
    thinkingOptions.style.display = 'block';
    thinkingOptions.classList.add('expanded');
  } else if (capabilities.thinking === 'optional') {
    thinkingOptions.style.display = 'none';
    thinkingOptions.classList.remove('expanded');
  }
}

// 根据模型名称获取最大令牌数
function getMaxTokensForModel(modelName) {
  // 转换为小写进行匹配
  const model = modelName.toLowerCase();
  
  // GPT-4系列模型
  if (model.includes('gpt-4')) {
    if (model.includes('32k') || model.includes('32k')) {
      return 32768;  // GPT-4-32k
    } else if (model.includes('turbo')) {
      return 128000; // GPT-4 Turbo
    } else {
      return 8192;   // 标准GPT-4
    }
  }
  
  // GPT-3.5系列模型
  if (model.includes('gpt-3.5') || model.includes('gpt-35')) {
    if (model.includes('16k')) {
      return 16384;  // GPT-3.5-turbo-16k
    } else {
      return 4096;   // 标准GPT-3.5-turbo
    }
  }
  
  // Claude系列模型
  if (model.includes('claude')) {
    if (model.includes('claude-3') || model.includes('claude3')) {
      return 200000; // Claude 3系列
    } else {
      return 100000; // Claude 2系列
    }
  }
  
  // 通义千问系列模型
  if (model.includes('qwen')) {
    if (model.includes('72b') || model.includes('72b')) {
      return 30720;  // Qwen-72B
    } else if (model.includes('14b') || model.includes('14b')) {
      return 8192;   // Qwen-14B
    } else if (model.includes('7b') || model.includes('7b')) {
      return 8192;   // Qwen-7B
    } else {
      return 6144;   // 其他Qwen模型
    }
  }
  
  // Gemini系列模型
  if (model.includes('gemini')) {
    if (model.includes('2.5') || model.includes('2.0')) {
      return 8192;   // Gemini 2.x 系列
    } else if (model.includes('pro')) {
      return 32768;  // Gemini Pro
    } else if (model.includes('flash')) {
      return 8192;   // Gemini Flash
    } else {
      return 8192;   // 其他Gemini模型
    }
  }
  
  // DeepSeek系列模型
  if (model.includes('deepseek')) {
    if (model.includes('67b') || model.includes('67b')) {
      return 4096;   // DeepSeek-67B
    } else {
      return 4096;   // 其他DeepSeek模型
    }
  }
  
  // 默认值
  return 4096;
}

// 更新Max Tokens的输入控件
function updateMaxTokensControl(modelName) {
  const maxTokens = getMaxTokensForModel(modelName);
  const maxTokensInput = document.getElementById('max_tokens');
  const maxTokensValue = document.getElementById('max_tokens-value');
  
  if (maxTokensInput) {
    // 更新最大值
    maxTokensInput.max = maxTokens;
    
    // 动态调整步长，确保从 min 开始能够精确到达 max
    const minVal = parseInt(maxTokensInput.min) || 100;
    const rangeVal = maxTokens - minVal;
    
    let step = 100;
    if (rangeVal > 10000) {
      step = 256;
    } else if (rangeVal > 4000) {
      step = 128;
    }
    
    // 确保 (max - min) 能被步长整除
    if (rangeVal % step !== 0) {
      // 尝试其他常用步长
      for (const candidateStep of [128, 64, 32, 16, 8, 4, 2, 1]) {
        if (rangeVal % candidateStep === 0) {
          step = candidateStep;
          break;
        }
      }
    }
    maxTokensInput.step = step;
    
    // 如果当前值超过新的最大值，则调整当前值
    const currentValue = parseInt(maxTokensInput.value);
    if (currentValue > maxTokens) {
      maxTokensInput.value = maxTokens;
      maxTokensValue.textContent = maxTokens;
      // 更新进度条
      updateParameterDisplay('max_tokens');
    }
    
    // 更新描述文本
    const descElement = maxTokensInput.closest('.param-card').querySelector('.param-desc');
    if (descElement) {
      descElement.textContent = `控制生成内容的最大长度 (最大值: ${maxTokens})`;
    }
  }
}

// 【新增】使用后端返回的 max_tokens_limit 更新控件
function updateMaxTokensControlWithLimit(maxTokensLimit) {
  const maxTokensInput = document.getElementById('max_tokens');
  const maxTokensValue = document.getElementById('max_tokens-value');
  
  if (maxTokensInput && maxTokensLimit > 0) {
    // 更新最大值
    maxTokensInput.max = maxTokensLimit;
    
    // 动态调整步长，确保从 min 开始能够精确到达 max
    const minVal = parseInt(maxTokensInput.min) || 100;
    const rangeVal = maxTokensLimit - minVal;
    
    let step = 100;
    if (rangeVal > 10000) {
      step = 256;
    } else if (rangeVal > 4000) {
      step = 128;
    }
    
    // 确保 (max - min) 能被步长整除
    if (rangeVal % step !== 0) {
      for (const candidateStep of [128, 64, 32, 16, 8, 4, 2, 1]) {
        if (rangeVal % candidateStep === 0) {
          step = candidateStep;
          break;
        }
      }
    }
    maxTokensInput.step = step;
    
    // 如果当前值超过新的最大值，则调整当前值
    const currentValue = parseInt(maxTokensInput.value);
    if (currentValue > maxTokensLimit) {
      maxTokensInput.value = maxTokensLimit;
      if (maxTokensValue) {
        maxTokensValue.textContent = maxTokensLimit;
      }
      updateParameterDisplay('max_tokens');
    }
    
    // 更新描述文本
    const descElement = maxTokensInput.closest('.param-card').querySelector('.param-desc');
    if (descElement) {
      descElement.textContent = `控制生成内容的最大长度 (最大值: ${maxTokensLimit})`;
    }
    
    console.log(`[Model Config] 使用后端配置的 max_tokens_limit: ${maxTokensLimit}`);
  }
}

// 加载通道信息
async function loadChannelInfo(channelId) {
  try {
    const response = await fetch(`${API_BASE}/manage/channels/${channelId}`);
    const result = await response.json();
    
    if (result.code === 0) {
      return result.data;
    } else {
      throw new Error(result.message || '加载通道信息失败');
    }
  } catch (error) {
    throw new Error('网络错误: ' + error.message);
  }
}

// 加载模型配置
async function loadModelConfig(channelId) {
  try {
    const response = await fetch(`${API_BASE}/manage/channels/${channelId}/model-config`);
    
    // 如果没有配置，返回默认配置
    if (response.status === 404) {
      return {
        temperature: 0.7,
        top_p: 1.0,
        max_tokens: 2000,
        frequency_penalty: 0.0,
        presence_penalty: 0.0,
        system_prompt: '',
        enable_web_search: false,
        enable_deep_thinking: false,
        thinking_budget: null,
        include_thoughts: false
      };
    }
    
    const result = await response.json();
    
    if (result.code === 0) {
      return result.data;
    } else {
      throw new Error(result.message || '加载模型配置失败');
    }
  } catch (error) {
    throw new Error('网络错误: ' + error.message);
  }
}

// 填充配置表单
function fillConfigForm(config) {
  // 【关键修复】优先使用后端返回的 param_limits 配置参数范围
  const paramLimits = config.param_limits || null;
  const capabilities = config.capabilities || getModelCapabilities(currentModelName);
  
  // 更新所有参数控件的范围（使用后端配置）
  if (paramLimits) {
    updateParamControlWithLimits('temperature', paramLimits.temperature);
    updateParamControlWithLimits('top_p', paramLimits.top_p);
    updateParamControlWithLimits('max_tokens', paramLimits.max_tokens);
    updateParamControlWithLimits('frequency_penalty', paramLimits.frequency_penalty);
    updateParamControlWithLimits('presence_penalty', paramLimits.presence_penalty);
    updateParamControlWithLimits('thinking_budget', paramLimits.thinking_budget);
    console.log('[Model Config] 使用后端返回的 param_limits 配置参数范围');
  } else {
    // 后备方案：如果后端没有返回 param_limits，使用前端推断
    if (config.max_tokens_limit) {
      updateMaxTokensControlWithLimit(config.max_tokens_limit);
    } else {
      updateMaxTokensControl(currentModelName);
    }
  }
  
  // 填充参数值
  document.getElementById('temperature').value = config.temperature || 0.7;
  document.getElementById('top_p').value = config.top_p || 1.0;
  document.getElementById('max_tokens').value = config.max_tokens || 2000;
  document.getElementById('frequency_penalty').value = config.frequency_penalty || 0.0;
  document.getElementById('presence_penalty').value = config.presence_penalty || 0.0;
  document.getElementById('system_prompt').value = config.system_prompt || '';
  
  // 深度思考配置
  const thinkingToggle = document.getElementById('enable_deep_thinking');
  const thinkingBudget = document.getElementById('thinking_budget');
  const includeThoughts = document.getElementById('include_thoughts');
  
  if (thinkingToggle) {
    // 根据模型能力和已保存配置设置开关状态
    if (capabilities.thinking === 'forced') {
      thinkingToggle.checked = true;
    } else if (capabilities.thinking === 'optional') {
      thinkingToggle.checked = config.enable_deep_thinking || false;
    } else {
      thinkingToggle.checked = false;
    }
  }
  
  if (thinkingBudget) {
    thinkingBudget.value = config.thinking_budget || capabilities.thinking_budget_default || 8192;
  }
  
  if (includeThoughts) {
    includeThoughts.checked = config.include_thoughts || false;
  }
  
  // 联网搜索配置
  const searchToggle = document.getElementById('enable_web_search');
  if (searchToggle) {
    if (capabilities.web_search) {
      searchToggle.checked = config.enable_web_search || false;
    } else {
      searchToggle.checked = false;
    }
  }
  
  // 【新增】使用后端返回的 capabilities 更新 UI 状态
  if (config.capabilities) {
    updateThinkingUI(config.capabilities);
    updateWebSearchUI(config.capabilities);
    console.log('[Model Config] 使用后端返回的 capabilities 配置模型能力');
  }
  
  // 更新显示值
  updateAllParameterDisplays();
  updateCharCount();
  
  // 更新思考选项显示状态
  onThinkingToggleChange();
}

// 【新增】使用后端返回的参数范围配置更新控件
function updateParamControlWithLimits(paramName, limits) {
  if (!limits) return;
  
  const input = document.getElementById(paramName);
  if (!input) return;
  
  // 更新控件属性
  if (limits.min !== undefined) input.min = limits.min;
  if (limits.max !== undefined) input.max = limits.max;
  if (limits.step !== undefined) input.step = limits.step;
  
  // 如果当前值超出范围，调整到范围内
  const currentValue = parseFloat(input.value);
  if (limits.max !== undefined && currentValue > limits.max) {
    input.value = limits.max;
  }
  if (limits.min !== undefined && currentValue < limits.min) {
    input.value = limits.min;
  }
  
  // 更新描述文本（如果存在）
  const paramCard = input.closest('.param-card');
  if (paramCard) {
    const descElement = paramCard.querySelector('.param-desc');
    if (descElement && paramName === 'max_tokens') {
      descElement.textContent = `控制生成内容的最大长度 (最大值: ${limits.max})`;
    }
  }
}

// 关闭模型配置模态框
function closeModelConfigModal() {
  const modal = document.getElementById('model-config-modal');
  if (modal) {
    modal.classList.remove('active');
  }
  currentChannelId = null;
  currentModelConfig = null;
  
  // 确保主页面的标签内容不受影响
  setTimeout(() => {
    const activeMainTab = document.querySelector('.nav-item.active');
    if (activeMainTab) {
      const tabName = activeMainTab.onclick.toString().match(/switchTab\([^,]+,\s*'([^']+)'\)/);
      if (tabName && tabName[1]) {
        const mainTabContent = document.getElementById(tabName[1] + '-tab');
        if (mainTabContent && !mainTabContent.classList.contains('active')) {
          mainTabContent.classList.add('active');
        }
      }
    }
  }, 100);
}

// 应用预设
function applyPreset(presetName) {
  if (typeof applyPresetToForm === 'function') {
    const success = applyPresetToForm(presetName);
    if (success) {
      showSuccess(`已应用"${getPresetConfig(presetName).name}"预设`);
    } else {
      showError('应用预设失败');
    }
  } else {
    showError('预设功能未加载');
  }
}

// 更新参数显示
function updateParameterDisplay(paramName) {
  const paramElement = document.getElementById(paramName);
  const displayElement = document.getElementById(`${paramName}-value`);
  
  if (paramElement && displayElement) {
    displayElement.textContent = paramElement.value;
    
    // 更新滑块进度条
    if (paramElement.type === 'range') {
      const progressElement = paramElement.parentElement.querySelector('.range-progress');
      if (progressElement) {
        const min = parseFloat(paramElement.min);
        const max = parseFloat(paramElement.max);
        const value = parseFloat(paramElement.value);
        const percentage = ((value - min) / (max - min)) * 100;
        progressElement.style.width = `${percentage}%`;
      }
    }
  }
}

// 更新所有参数显示
function updateAllParameterDisplays() {
  updateParameterDisplay('temperature');
  updateParameterDisplay('top_p');
  updateParameterDisplay('max_tokens');
  updateParameterDisplay('frequency_penalty');
  updateParameterDisplay('presence_penalty');
  updateParameterDisplay('thinking_budget');
}

// 切换高级参数区域
function toggleSection(sectionId) {
  const section = document.querySelector(`#${sectionId}-params`).closest('.collapsible');
  const header = section.querySelector('h4');
  
  if (section.classList.contains('expanded')) {
    section.classList.remove('expanded');
    header.textContent = header.textContent.replace('▼', '▼');
  } else {
    section.classList.add('expanded');
    header.textContent = header.textContent.replace('▼', '▼');
  }
}

// 更新字符计数
function updateCharCount() {
  const textarea = document.getElementById('system_prompt');
  const countElement = document.getElementById('char-count');
  const progressElement = document.getElementById('char-progress');
  
  if (textarea && countElement) {
    const count = textarea.value.length;
    const maxLength = 5000;
    const percentage = (count / maxLength) * 100;
    
    countElement.textContent = count;
    
    if (progressElement) {
      progressElement.style.width = `${Math.min(percentage, 100)}%`;
      
      // 根据字数改变颜色
      if (percentage < 70) {
        progressElement.style.background = 'linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%)';
      } else if (percentage < 90) {
        progressElement.style.background = 'linear-gradient(90deg, #f59e0b 0%, #ef4444 100%)';
      } else {
        progressElement.style.background = 'linear-gradient(90deg, #ef4444 0%, #dc2626 100%)';
      }
    }
  }
}

// 切换模态框内部标签
function switchModalTab(tabName) {
  // 移除所有标签的active类，只影响模态框内的按钮
  document.querySelectorAll('#model-config-modal .tab-button').forEach(btn => {
    btn.classList.remove('active');
  });
  
  // 移除模态框内所有标签内容的active类
  document.querySelectorAll('#model-config-modal .modal-tab-content').forEach(content => {
    content.classList.remove('active');
  });
  
  // 添加active类到选中的标签
  const targetButton = document.querySelector(`#model-config-modal .tab-button:nth-child(${getTabIndex(tabName)})`);
  if (targetButton) {
    targetButton.classList.add('active');
  }
  
  const targetContent = document.getElementById(`${tabName}-tab`);
  if (targetContent) {
    targetContent.classList.add('active');
  }
}

// 获取标签索引
function getTabIndex(tabName) {
  const tabs = ['basic', 'advanced', 'prompt', 'presets'];
  return tabs.indexOf(tabName) + 1;
}

// 点击背景关闭模态框
function closeModalOnBackdrop(event) {
  if (event.target === event.currentTarget) {
    closeModelConfigModal();
  }
}

// 展开系统提示词
function expandSystemPrompt() {
  const textarea = document.getElementById('system_prompt');
  if (textarea) {
    textarea.rows = 20;
  }
}

// 收起系统提示词
function shrinkSystemPrompt() {
  const textarea = document.getElementById('system_prompt');
  if (textarea) {
    textarea.rows = 8;
  }
}

// 重置系统提示词
function resetSystemPrompt() {
  const textarea = document.getElementById('system_prompt');
  if (textarea && currentModelConfig) {
    textarea.value = currentModelConfig.system_prompt || '';
    updateCharCount();
  }
}

// 恢复默认参数
function resetToDefaults() {
  if (confirm('确定要恢复所有参数到默认值吗？')) {
    document.getElementById('temperature').value = 0.7;
    document.getElementById('top_p').value = 1.0;
    document.getElementById('max_tokens').value = 2000;
    document.getElementById('frequency_penalty').value = 0.0;
    document.getElementById('presence_penalty').value = 0.0;
    document.getElementById('system_prompt').value = '';
    
    // 重置模型能力扩展配置
    const capabilities = getModelCapabilities(currentModelName);
    
    // 深度思考
    const thinkingToggle = document.getElementById('enable_deep_thinking');
    const thinkingBudget = document.getElementById('thinking_budget');
    const includeThoughts = document.getElementById('include_thoughts');
    
    if (thinkingToggle && capabilities.thinking === 'optional') {
      thinkingToggle.checked = false;
    }
    if (thinkingBudget) {
      thinkingBudget.value = capabilities.thinking_budget_default || 8192;
    }
    if (includeThoughts) {
      includeThoughts.checked = false;
    }
    
    // 联网搜索
    const searchToggle = document.getElementById('enable_web_search');
    if (searchToggle && capabilities.web_search) {
      searchToggle.checked = false;
    }
    
    updateAllParameterDisplays();
    updateCharCount();
    onThinkingToggleChange();
    
    showSuccess('已恢复默认参数');
  }
}

// 获取当前配置
function getCurrentConfig() {
  const capabilities = getModelCapabilities(currentModelName);
  
  const config = {
    temperature: parseFloat(document.getElementById('temperature').value),
    top_p: parseFloat(document.getElementById('top_p').value),
    max_tokens: parseInt(document.getElementById('max_tokens').value),
    frequency_penalty: parseFloat(document.getElementById('frequency_penalty').value),
    presence_penalty: parseFloat(document.getElementById('presence_penalty').value),
    system_prompt: document.getElementById('system_prompt').value
  };
  
  // 添加深度思考配置
  const thinkingToggle = document.getElementById('enable_deep_thinking');
  const thinkingBudget = document.getElementById('thinking_budget');
  const includeThoughts = document.getElementById('include_thoughts');
  
  if (capabilities.thinking === 'forced') {
    // 强制开启的模型
    config.enable_deep_thinking = true;
  } else if (capabilities.thinking === 'optional' && thinkingToggle) {
    config.enable_deep_thinking = thinkingToggle.checked;
    if (thinkingToggle.checked && thinkingBudget) {
      config.thinking_budget = parseInt(thinkingBudget.value);
    }
    if (includeThoughts) {
      config.include_thoughts = includeThoughts.checked;
    }
  } else {
    config.enable_deep_thinking = false;
  }
  
  // 添加联网搜索配置
  const searchToggle = document.getElementById('enable_web_search');
  if (capabilities.web_search && searchToggle) {
    config.enable_web_search = searchToggle.checked;
  } else {
    config.enable_web_search = false;
  }
  
  return config;
}

// 保存模型配置
async function saveModelConfig() {
  if (!currentChannelId) {
    showError('没有选中的通道');
    return;
  }
  
  // 显示加载状态
  const spinner = document.getElementById('save-spinner');
  spinner.style.display = 'inline-block';
  
  try {
    const config = getCurrentConfig();
    
    const response = await fetch(`${API_BASE}/manage/channels/${currentChannelId}/model-config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(config)
    });
    
    const result = await response.json();
    
    if (result.code === 0) {
      showSuccess('模型配置保存成功！');
      currentModelConfig = config;
      
      // 如果有回调函数，调用它
      if (typeof onModelConfigSaved === 'function') {
        onModelConfigSaved(currentChannelId, config);
      }
      
      // 刷新配置列表以更新图标显示
      if (typeof window.loadChannels === 'function') {
        window.loadChannels();
      }
      
      // 延迟关闭模态框，让用户看到成功消息
      setTimeout(() => {
        closeModelConfigModal();
      }, 1000);
    } else {
      showError('保存失败: ' + (result.message || '未知错误'));
    }
  } catch (error) {
    console.error('保存模型配置异常:', error);
    showError('保存异常: ' + error.message);
  } finally {
    // 隐藏加载状态
    spinner.style.display = 'none';
  }
}

// 显示成功消息
function showSuccess(message) {
  showMessage(message, 'success');
}

// 显示错误消息
function showError(message) {
  showMessage(message, 'error');
}

// 显示信息消息
function showInfo(message) {
  showMessage(message, 'info');
}

// 显示消息
function showMessage(message, type) {
  // 创建消息元素
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${type}`;
  messageDiv.textContent = message;
  
  // 添加样式
  Object.assign(messageDiv.style, {
    position: 'fixed',
    top: '20px',
    right: '20px',
    padding: '12px 20px',
    borderRadius: '4px',
    color: 'white',
    fontWeight: 'bold',
    zIndex: '10000',
    maxWidth: '400px',
    wordWrap: 'break-word'
  });
  
  // 根据类型设置背景色
  switch (type) {
    case 'success':
      messageDiv.style.backgroundColor = '#4CAF50';
      break;
    case 'error':
      messageDiv.style.backgroundColor = '#F44336';
      break;
    case 'info':
      messageDiv.style.backgroundColor = '#2196F3';
      break;
    default:
      messageDiv.style.backgroundColor = '#9E9E9E';
  }
  
  // 添加到页面
  document.body.appendChild(messageDiv);
  
  // 自动移除
  setTimeout(() => {
    if (messageDiv.parentNode) {
      messageDiv.parentNode.removeChild(messageDiv);
    }
  }, 5000);
}

// 导出函数
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    initModelConfig,
    openModelConfigModal,
    closeModelConfigModal,
    saveModelConfig,
    applyPreset,
    resetToDefaults,
    getModelCapabilities,
    updateCapabilityUI,
    onThinkingToggleChange
  };
}

// 确保函数在全局可访问
if (typeof window !== 'undefined') {
  window.initModelConfig = initModelConfig;
  window.openModelConfigModal = openModelConfigModal;
  window.closeModelConfigModal = closeModelConfigModal;
  window.saveModelConfig = saveModelConfig;
  window.applyPreset = applyPreset;
  window.resetToDefaults = resetToDefaults;
  window.onThinkingToggleChange = onThinkingToggleChange;
  window.updateCapabilityUI = updateCapabilityUI;
  window.getModelCapabilities = getModelCapabilities;
}