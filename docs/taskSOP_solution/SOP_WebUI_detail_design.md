# SOP 任务 WebUI 集成详细设计方案

> **文档目的**：详细说明 SOP 任务（以评分卡开发为例）在 WebUI 三列式布局中的集成方案，包括任务选项卡设计、交互流程、Prompt 注入机制等。

---

## 📌 文档定位与关联

| 属性 | 说明 |
|------|------|
| **本文档定位** | **前端UI/UX详细设计** - 侧重用户界面布局、交互流程、视觉设计 |
| **关联文档** | [SOP_WebUI_Integration_design.md](./SOP_WebUI_Integration_design.md) - 后端架构与开发计划 |
| **示例任务** | 评分卡开发（Scorecard Development） |

### 文档分工

| 内容领域 | 本文档 | Integration_Plan |
|----------|:------:|:----------------:|
| **三列式UI布局设计** | ✅ 主责 | 引用本文档 |
| **左侧任务选项卡设计** | ✅ 主责 | 引用本文档 |
| **参数面板内嵌设计** | ✅ 主责 | 引用本文档 |
| **交互流程时序图** | ✅ 主责 | 引用本文档 |
| **Prompt注入机制** | ✅ 主责 | 引用本文档 |
| **前端组件代码示例** | ✅ 主责 | 补充 |
| **系统架构设计** | 引用 | ✅ 主责 |
| **SOP Registry设计** | 引用 | ✅ 主责 |
| **API端点设计** | 引用 | ✅ 主责 |
| **任务执行引擎** | 引用 | ✅ 主责 |
| **开发任务分解** | 引用 | ✅ 主责 |
| **文件结构规划** | 引用 | ✅ 主责 |
| **验收标准** | 引用 | ✅ 主责 |

---

## 一、设计方案演进

### 1.1 原始构想评估

**用户原始设想**：将左侧列一分为二，左上是原有的文件管理，左下设计一个任务类型选项卡。

| 维度 | 评价 |
|------|------|
| **空间利用** | ✅ 充分利用已有空间，不增加UI复杂度 |
| **操作直觉** | ✅ 点击选项卡触发任务，符合用户心智模型 |
| **关注点分离** | ✅ 文件管理与任务选择独立，职责清晰 |
| **可扩展性** | ✅ 新增任务只需添加选项卡，无需改动布局 |

**潜在局限**：
- 左侧空间有限，任务类型较多时（>6个）可能拥挤
- 参数配置弹出面板可能遮挡工作区
- 任务执行状态可见性需要明确

### 1.2 优化融合方案

基于原始构想，融合以下优化点：

| 优化点 | 说明 |
|--------|------|
| **参数面板内嵌** | 配置面板出现在中间列顶部，而非弹出遮挡 |
| **任务分组折叠** | 支持更多任务类型，分类清晰（可选） |
| **进度状态可视化** | 任务执行进度在对话区上方持续显示 |
| **状态联动** | 左侧任务选项卡显示当前激活状态 |

---

## 二、最终 WebUI 布局设计

### 2.1 融合后的三列式布局

```
┌─────────────────┐  ┌─────────────────────────────┐  ┌─────────────────────┐
│   📁 文件管理   │  │  ┌─────────────────────────┐│  │                     │
│   (可折叠)      │  │  │ 📊 评分卡开发任务       ││  │   代码/结果展示     │
│   workspace/    │  │  │ 目标列: [下拉选择]      ││  │                     │
│   ├── data.csv  │  │  │ 基准分: [600]           ││  │   <Analyze>         │
│                 │  │  │ [开始执行] [重置]       ││  │   <Code>            │
├─────────────────┤  │  └─────────────────────────┘│  │   <Output>          │
│   🎯 任务选择   │  │  ─────────────────────────  │  │                     │
│   ┌───────────┐ │  │  进度: ████░░ 60%          │  │   📈 可视化         │
│   │ 评分卡 ● │◀│  │                             │  │                     │
│   │ 规则挖掘  │ │  │  AI: 正在进行WOE分箱...    │  │                     │
│   │ 特征分析  │ │  │                             │  │                     │
│   └───────────┘ │  │  [输入框] [发送]            │  │                     │
└─────────────────┘  └─────────────────────────────┘  └─────────────────────┘
```

### 2.2 核心设计特点

| 特点 | 说明 |
|------|------|
| **左侧保持简洁** | 文件管理+任务选项卡，符合原始设想 |
| **参数面板内嵌** | 点击任务后，配置面板出现在中间列顶部，不遮挡 |
| **进度条可见** | 任务执行进度在对话区上方持续显示 |
| **状态联动** | 左侧任务选项卡显示当前激活状态（●标记） |

### 2.3 左侧列详细设计

```
┌─────────────────────────────────────┐
│         左侧列 (宽度: 280px)         │
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────────────────────┐   │
│  │ 📁 工作区文件               │   │  ← 左上：文件管理区
│  │ ─────────────────────────── │   │     (高度: 40%，可折叠)
│  │                             │   │
│  │  📄 credit_data.csv  (2.3MB)│   │
│  │  📄 config.json      (1KB) │   │
│  │  📁 output/                 │   │
│  │     └─ scorecard.xlsx       │   │
│  │                             │   │
│  │  ┌───────────────────────┐ │   │
│  │  │ 拖拽或点击上传文件    │ │   │
│  │  │ 支持 CSV, Excel       │ │   │
│  │  └───────────────────────┘ │   │
│  │                             │   │
│  └─────────────────────────────┘   │
│                                     │
│  ═══════════════════════════════   │  ← 分隔线（可拖拽调整比例）
│                                     │
│  ┌─────────────────────────────┐   │
│  │ 🎯 任务类型                 │   │  ← 左下：任务选项卡区
│  │ ─────────────────────────── │   │     (高度: 60%)
│  │                             │   │
│  │  ┌─────────────────────┐   │   │
│  │  │ 📊 评分卡开发       │◀──│───│── 当前选中（高亮+●标记）
│  │  │    信用评分卡标准流程│   │   │
│  │  └─────────────────────┘   │   │
│  │                             │   │
│  │  ┌─────────────────────┐   │   │
│  │  │ 🎯 策略规则挖掘     │   │   │
│  │  │    决策树规则生成   │   │   │
│  │  └─────────────────────┘   │   │
│  │                             │   │
│  │  ┌─────────────────────┐   │   │
│  │  │ 🔧 特征工程         │   │   │
│  │  │    WOE/IV/相关性    │   │   │
│  │  └─────────────────────┘   │   │
│  │                             │   │
│  │  ┌─────────────────────┐   │   │
│  │  │ 📈 模型评估         │   │   │
│  │  │    KS/AUC/PSI分析   │   │   │
│  │  └─────────────────────┘   │   │
│  │                             │   │
│  │  ──────────────────────    │   │
│  │  [+ 自定义任务]            │   │
│  │                             │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

### 2.4 中间列详细设计（参数面板内嵌）

```
┌─────────────────────────────────────────────────────┐
│                  中间列 - AI对话区                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐   │  ← 参数配置面板
│  │ 📊 评分卡开发任务                     [收起]│   │    （点击任务后展开）
│  │ ───────────────────────────────────────────│   │
│  │                                             │   │
│  │  数据文件: [credit_data.csv ▼]             │   │
│  │                                             │   │
│  │  目标变量: [is_bad ▼]   基准分: [600]      │   │
│  │  PDO: [20]              基准Odds: [20:1]   │   │
│  │                                             │   │
│  │  ▼ 高级参数（按阶段分组展示）              │   │
│  │  ┌─────────────────────────────────────┐   │   │
│  │  │ ▶ WOE分箱 (3)                       │   │   │
│  │  │ ▶ 特征筛选 (4)                      │   │   │
│  │  │ ▶ 模型训练 (5)                      │   │   │
│  │  │ ▶ 评分转换 (2)                      │   │   │
│  │  └─────────────────────────────────────┘   │   │
│  │                                             │   │
│  │  [重置参数]                [🚀 开始执行]   │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │  ← 进度显示区
│  │ 📊 评分卡开发 - 阶段 2/7: WOE分箱           │   │    （执行时显示）
│  │ ████████████░░░░░░░░ 40%                    │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │  ← 对话历史区
│  │ 🤖 AI: 好的，我将按照评分卡开发标准流程...  │   │
│  │                                             │   │
│  │ 正在执行阶段2: 对 age, income 等变量进行    │   │
│  │ WOE分箱处理...                              │   │
│  │                                             │   │
│  │ 👤 用户: 帮我开发一个评分卡                 │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │  ← 输入区
│  │ 输入消息...                        [发送]   │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 三、交互流程设计

### 3.1 完整交互流程

```
1. 用户上传 data.csv 
   → 左上文件区显示文件

2. 用户点击左下[评分卡开发] 
   → 中间列顶部展开参数配置面板
   → 左侧任务选项卡高亮显示（●标记）

3. 系统自动识别data.csv列名 
   → 填充下拉选项（目标变量、特征变量）

4. 用户配置参数 → 点击[开始执行]
   → 配置面板收起（或最小化）
   → 显示进度条
   → AI开始按SOP流程执行

5. 执行过程中
   → 进度条实时更新
   → 对话区显示当前阶段说明
   → 右侧展示代码和中间输出

6. 执行完成 
   → 右侧展示最终结果（评分卡表、KS/AUC、图表）
   → 左侧任务状态更新为"已完成"
   → 提供下载/导出选项
```

### 3.2 点击任务选项卡后的详细流程

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          任务选项卡点击后的交互流程                                   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  用户点击 [📊 评分卡开发]                                                           │
│           │                                                                         │
│           ▼                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │ Step 1: 加载任务配置                                                        │   │
│  │                                                                             │   │
│  │  前端调用: GET /sop/tasks/scorecard_development                            │   │
│  │  返回: 任务元数据（参数Schema、阶段定义、SOP Prompt模板）                   │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│           │                                                                         │
│           ▼                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │ Step 2: 展开参数配置面板（内嵌在中间列顶部）                                │   │
│  │                                                                             │   │
│  │  - 根据参数Schema动态生成表单                                               │   │
│  │  - 自动检测工作区文件，填充数据文件下拉选项                                 │   │
│  │  - 如果已选择数据文件，自动解析列名填充目标变量/特征变量选项               │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│           │                                                                         │
│           ▼ (用户配置参数并点击 [开始执行])                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │ Step 3: 构建并注入 SOP Prompt                                               │   │
│  │                                                                             │   │
│  │  - 收集表单参数                                                             │   │
│  │  - 调用 POST /sop/execute                                                   │   │
│  │  - API层构建完整SOP Prompt（注入参数+数据上下文）                           │   │
│  │  - 将SOP Prompt作为system消息发送给LLM                                      │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│           │                                                                         │
│           ▼                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │ Step 4: LLM 按 SOP 流程执行                                                 │   │
│  │                                                                             │   │
│  │  - 配置面板收起/最小化                                                      │   │
│  │  - 显示进度条（阶段 X/6）                                                   │   │
│  │  - 对话区显示AI执行说明                                                     │   │
│  │  - 右侧展示生成的代码和执行输出                                             │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│           │                                                                         │
│           ▼ (任务完成)                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │ Step 5: 展示最终结果                                                        │   │
│  │                                                                             │   │
│  │  - 对话区显示任务完成摘要（KS、AUC、入模变量数）                            │   │
│  │  - 右侧展示：评分卡表格、ROC/KS曲线、分数分布图                             │   │
│  │  - 提供下载按钮：[下载评分卡] [导出报告]                                    │   │
│  │  - 左侧任务状态更新                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 四、SOP Prompt 注入机制

### 4.1 Prompt 注入位置

SOP Prompt 模板在 **API 层** 的 `prepare_vllm_messages` 函数中注入：

```python
# API/utils.py - 修改后的消息处理流程

def prepare_vllm_messages(
    messages: List[Dict],
    workspace_files: List[Dict] = None,
    sop_context: Optional[Dict] = None  # 新增：SOP任务上下文
) -> List[Dict]:
    """
    准备发送给LLM的消息，注入SOP Prompt和上下文
    
    Args:
        messages: 原始对话消息
        workspace_files: 工作区文件信息
        sop_context: SOP任务上下文
            {
                "task_id": "scorecard_development",
                "sop_prompt": "...",  # 完整的SOP Prompt
                "params": {...}
            }
    """
    
    # 如果有SOP任务，使用SOP Prompt作为系统提示词
    if sop_context and sop_context.get("sop_prompt"):
        system_content = sop_context["sop_prompt"]
        
        # 附加数据上下文
        if workspace_files:
            data_context = format_workspace_files(workspace_files)
            system_content += f"\n\n# Data Context\n{data_context}"
    else:
        # 默认的通用Prompt
        system_content = "# Instruction\n"
        if messages:
            system_content += messages[-1].get("content", "")
        
        if workspace_files:
            system_content += f"\n\n# Data\n{format_workspace_files(workspace_files)}"
    
    # 构建最终消息列表
    result_messages = [{"role": "system", "content": system_content}]
    
    # 添加历史对话
    for msg in messages[:-1]:
        result_messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })
    
    return result_messages
```

### 4.2 SOP Prompt 模板结构（评分卡开发示例）

```python
# API/prompts/scorecard_prompt.py

SCORECARD_SOP_PROMPT = """
# Role
你是一名资深的银行风控建模专家，精通信用评分卡开发。

# Task
{task_description}

# Instruction
请使用数据集 `{data_file}` 构建一张标准的信用评分卡。
目标变量: {target_col}
{feature_cols_instruction}

必须严格遵守以下标准工作流进行处理，不要跳过任何步骤：

## 阶段1：数据清洗与预处理
- 检查缺失值，对缺失率 > {missing_threshold}% 的变量进行剔除
- 检查异常值，使用IQR方法识别
- 将数据分割为训练集和测试集（比例 {test_ratio}）

## 阶段2：特征工程（核心步骤）
- 必须使用 **Weight of Evidence (WOE)** 方法对所有连续变量和分类变量进行转换
- 使用 {binning_method} 分箱方法进行处理
- 必须计算每个变量的 **Information Value (IV)**
- 生成WOE分箱可视化图

## 阶段3：特征筛选
- 仅保留 IV 值在 [{iv_lower}, {iv_upper}] 之间的变量
- 检查变量间的多重共线性（VIF），剔除 VIF > {vif_threshold} 的变量
- 检查变量间相关性，剔除相关系数 > {corr_threshold} 的冗余变量

## 阶段4：模型训练
- 使用 **逻辑回归 (Logistic Regression)** 算法
- 禁止使用XGBoost、RandomForest等黑盒模型（监管合规要求）
{stepwise_instruction}
- 检验所有系数的显著性（p < {significance_level}）
- 验证系数方向与业务逻辑一致

## 阶段5：评分刻度转换（Scaling）
- 设定 Base Score = {base_score} points at odds {base_odds}:1
- 设定 PDO (Points to Double the Odds) = {pdo}
- 输出最终的评分卡刻度表

## 阶段6：模型评估
- 绘制 ROC 曲线，计算 AUC 值
- 计算 KS 值 (Kolmogorov-Smirnov)，绘制 KS 曲线
- 分析分数分布，按分数段统计bad_rate

# Constraints
- 所有步骤必须按顺序执行，不可跳过
- 必须使用逻辑回归，禁止使用其他算法
- 所有入模变量必须通过显著性检验
- 输出结果需包含完整的评分卡表格

# Data Context
{data_context}

# Output Requirements
1. 每个阶段完成后，输出阶段结果摘要
2. 最终输出完整的评分卡表格
3. 输出模型评估指标（KS、AUC）
4. 生成可视化图表（ROC、KS曲线）
"""
```

---

## 五、前端组件设计

### 5.1 任务选项卡组件

```javascript
// frontend/components/sop/TaskSelector.js

/**
 * 任务选项卡组件
 * 显示在左侧列下半部分
 */
class TaskSelector {
    constructor(container) {
        this.container = container;
        this.tasks = [];
        this.selectedTask = null;
        this.onTaskSelect = null;  // 回调函数
    }
    
    /**
     * 加载可用任务列表
     */
    async loadTasks() {
        const response = await fetch('/sop/tasks');
        this.tasks = await response.json();
        this.render();
    }
    
    /**
     * 渲染任务列表
     */
    render() {
        const html = `
            <div class="task-selector">
                <div class="task-selector-header">
                    <span class="icon">🎯</span>
                    <span class="title">任务类型</span>
                </div>
                <div class="task-list">
                    ${this.tasks.map(task => this.renderTaskItem(task)).join('')}
                </div>
                <div class="task-selector-footer">
                    <button class="btn-add-task">+ 自定义任务</button>
                </div>
            </div>
        `;
        this.container.innerHTML = html;
        this.bindEvents();
    }
    
    /**
     * 渲染单个任务项
     */
    renderTaskItem(task) {
        const isSelected = this.selectedTask?.task_id === task.task_id;
        return `
            <div class="task-item ${isSelected ? 'selected' : ''}" 
                 data-task-id="${task.task_id}">
                <div class="task-icon">${task.icon}</div>
                <div class="task-info">
                    <div class="task-name">${task.name}</div>
                    <div class="task-desc">${task.description}</div>
                </div>
                ${isSelected ? '<div class="task-indicator">●</div>' : ''}
            </div>
        `;
    }
    
    /**
     * 选择任务
     */
    async selectTask(taskId) {
        const response = await fetch(`/sop/tasks/${taskId}`);
        this.selectedTask = await response.json();
        this.render();
        
        if (this.onTaskSelect) {
            this.onTaskSelect(this.selectedTask);
        }
    }
}
```

### 5.2 参数配置面板组件（内嵌式）

```javascript
// frontend/components/sop/ParamConfigPanel.js

/**
 * 参数配置面板（内嵌在中间列顶部）
 */
class ParamConfigPanel {
    constructor(container) {
        this.container = container;
        this.task = null;
        this.dataColumns = [];
        this.isExpanded = false;
    }
    
    /**
     * 展开配置面板
     */
    async expand(task, dataFile) {
        this.task = task;
        this.isExpanded = true;
        
        // 获取数据列信息
        if (dataFile) {
            const preview = await this.previewData(dataFile);
            this.dataColumns = preview.columns;
        }
        
        this.render();
    }
    
    /**
     * 收起配置面板
     */
    collapse() {
        this.isExpanded = false;
        this.render();
    }
    
    /**
     * 渲染面板
     */
    render() {
        if (!this.isExpanded || !this.task) {
            this.container.innerHTML = '';
            return;
        }
        
        this.container.innerHTML = `
            <div class="param-config-panel">
                <div class="panel-header">
                    <span class="panel-icon">${this.task.icon}</span>
                    <span class="panel-title">${this.task.name}</span>
                    <button class="panel-collapse" onclick="paramPanel.collapse()">收起 ▲</button>
                </div>
                
                <div class="panel-body">
                    <div class="param-row">
                        <div class="param-field">
                            <label>数据文件</label>
                            <select id="param-data-file">${this.renderFileOptions()}</select>
                        </div>
                    </div>
                    
                    <div class="param-row">
                        <div class="param-field">
                            <label>目标变量</label>
                            <select id="param-target-col">${this.renderColumnOptions()}</select>
                        </div>
                        <div class="param-field">
                            <label>基准分</label>
                            <input type="number" id="param-base-score" value="600">
                        </div>
                        <div class="param-field">
                            <label>PDO</label>
                            <input type="number" id="param-pdo" value="20">
                        </div>
                    </div>
                    
                    <!-- 高级参数（按阶段分组展示） -->
                    <div class="advanced-params-container">
                        <h4>高级参数</h4>
                        
                        <!-- 按阶段分组，每个阶段可独立折叠 -->
                        <details class="stage-param-group">
                            <summary>▶ WOE分箱 (3)</summary>
                            <div class="param-row">
                                <div class="param-field">
                                    <label>分箱方法</label>
                                    <select id="param-bin-method">
                                        <option value="tree" selected>决策树</option>
                                        <option value="chimerge">卡方</option>
                                    </select>
                                </div>
                                <div class="param-field">
                                    <label>最大分箱数</label>
                                    <input type="number" id="param-max-bins" value="5">
                                </div>
                            </div>
                        </details>
                        
                        <details class="stage-param-group">
                            <summary>▶ 特征筛选 (4)</summary>
                            <div class="param-row">
                                <div class="param-field">
                                    <label>IV下限</label>
                                    <input type="number" id="param-iv-lower" value="0.02" step="0.01">
                                </div>
                                <div class="param-field">
                                    <label>IV上限</label>
                                    <input type="number" id="param-iv-upper" value="0.5" step="0.1">
                                </div>
                                <div class="param-field">
                                    <label>VIF阈值</label>
                                    <input type="number" id="param-vif" value="5">
                                </div>
                                <div class="param-field">
                                    <label>相关系数阈值</label>
                                    <input type="number" id="param-corr" value="0.7" step="0.1">
                                </div>
                            </div>
                        </details>
                        
                        <details class="stage-param-group">
                            <summary>▶ 模型训练 (5)</summary>
                            <div class="param-row">
                                <div class="param-field">
                                    <label>显著性检验模式</label>
                                    <select id="param-significance-mode">
                                        <option value="remove" selected>remove (自动剔除)</option>
                                        <option value="warn">warn (警告并继续)</option>
                                        <option value="skip">skip (跳过检验)</option>
                                    </select>
                                </div>
                                <div class="param-field">
                                    <label>系数方向验证模式</label>
                                    <select id="param-coef-direction-mode">
                                        <option value="warn" selected>warn (警告并继续)</option>
                                        <option value="remove">remove (自动剔除)</option>
                                        <option value="skip">skip (跳过检验)</option>
                                    </select>
                                </div>
                                <div class="param-field">
                                    <label>最大迭代次数</label>
                                    <input type="number" id="param-max-iterations" value="10" min="1" max="20">
                                </div>
                            </div>
                        </details>
                        
                        <details class="stage-param-group">
                            <summary>▶ 评分转换 (2)</summary>
                            <div class="param-row">
                                <div class="param-field">
                                    <label>基准分</label>
                                    <input type="number" id="param-base-score-adv" value="600">
                                </div>
                                <div class="param-field">
                                    <label>PDO</label>
                                    <input type="number" id="param-pdo-adv" value="20">
                                </div>
                            </div>
                        </details>
                    </div>
                </div>
                
                <div class="panel-footer">
                    <button class="btn btn-secondary" onclick="paramPanel.reset()">重置参数</button>
                    <button class="btn btn-primary" onclick="paramPanel.execute()">🚀 开始执行</button>
                </div>
            </div>
        `;
    }
    
    /**
     * 执行任务
     */
    async execute() {
        const params = this.collectParams();
        
        // 最小化面板（不完全收起，保留进度显示）
        this.minimize();
        
        // 构建SOP请求
        const sopRequest = {
            task_id: this.task.task_id,
            params: params
        };
        
        // 触发任务执行
        await chatSystem.sendSOPTask(sopRequest);
    }
}
```

#### 5.2.1 高级参数按阶段分组展示设计

> **v2.1 新增**（2025-02-04）

为了帮助用户更好地理解高级参数的用途，参数配置面板中的高级参数按所属阶段进行分组展示。

**设计要点**：

1. **分组逻辑**：
   - 高级参数按 `stage` 字段分组，保持 `taskMeta.stages` 定义的阶段顺序
   - 每个阶段显示名称和参数数量，如 `▶ WOE分箱 (3)`
   - 无 `stage` 字段的参数归类到"通用参数"组

2. **交互设计**：
   - 每个阶段组可独立折叠/展开
   - 默认折叠状态，节省显示空间
   - 阶段内部仍按 `group` 字段进行二次分组（并排显示）

3. **实现组件**：
   - `TaskConfigPanel.tsx`：左侧任务栏的参数配置面板
   - `TaskParamCard.tsx`：LLM拉起任务时的参数配置卡片
   - 两个入口体验保持一致

4. **数据结构**：
   ```typescript
   interface TaskParam {
     name: string;
     label: string;
     type: ParamType;
     default?: any;
     group?: string;    // 二级分组（如 'binning'、'filtering'）
     stage?: string;    // 阶段ID，用于按阶段分组展示
     // ...
   }
   ```

5. **示例展示**：
   ```
   ▼ 高级参数
   ┌─────────────────────────────────────────────┐
   │ ▼ WOE分箱 (3)                               │
   │   ┌─────────────────────────────────────┐   │
   │   │ 分箱方法: [决策树 ▼]  最大分箱数: [5]│   │
   │   │ 单调约束: [是 ▼]                    │   │
   │   └─────────────────────────────────────┘   │
   │ ▶ 特征筛选 (4)                              │
   │ ▶ 模型训练 (5)                              │
   │ ▶ 评分转换 (2)                              │
   └─────────────────────────────────────────────┘
   ```

### 5.3 进度显示组件

```javascript
// frontend/components/sop/ProgressBar.js

/**
 * 任务进度显示组件
 * 
 * 注意：评分卡任务为7个阶段，规则挖掘任务为6个阶段（v2.0合并优化）
 */
class TaskProgressBar {
    constructor(container) {
        this.container = container;
        this.currentStage = 0;
        this.totalStages = 7;  // 评分卡7阶段，规则挖掘6阶段
        this.stageName = '';
    }
    
    /**
     * 更新进度
     */
    update(stage, stageName, totalStages = 7) {
        this.currentStage = stage;
        this.stageName = stageName;
        this.totalStages = totalStages;
        this.render();
    }
    
    /**
     * 渲染进度条
     */
    render() {
        const percent = Math.round((this.currentStage / this.totalStages) * 100);
        const filledBlocks = Math.round(percent / 5);
        const emptyBlocks = 20 - filledBlocks;
        
        this.container.innerHTML = `
            <div class="task-progress">
                <div class="progress-header">
                    <span class="progress-task">📊 评分卡开发</span>
                    <span class="progress-stage">阶段 ${this.currentStage}/${this.totalStages}: ${this.stageName}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${percent}%"></div>
                </div>
                <div class="progress-text">${'█'.repeat(filledBlocks)}${'░'.repeat(emptyBlocks)} ${percent}%</div>
            </div>
        `;
    }
    
    /**
     * 隐藏进度条
     */
    hide() {
        this.container.innerHTML = '';
    }
}
```

---

## 六、后端 API 扩展

### 6.1 SOP 任务 API

```python
# API/sop_api.py

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/sop", tags=["SOP Tasks"])

# ==================== 数据模型 ====================

class TaskExecuteRequest(BaseModel):
    """SOP任务执行请求"""
    task_id: str
    session_id: str
    params: Dict[str, Any]

class TaskListItem(BaseModel):
    """任务列表项"""
    task_id: str
    name: str
    description: str
    icon: str
    category: str

class TaskDefinition(BaseModel):
    """任务完整定义"""
    task_id: str
    name: str
    description: str
    icon: str
    category: str
    params: List[Dict]
    stages: List[Dict]
    prompt_template: str

# ==================== API端点 ====================

@router.get("/tasks", response_model=List[TaskListItem])
async def list_tasks():
    """获取所有可用的SOP任务"""
    from deepanalyze.analysis.task_SOP.registry import get_all_tasks
    
    tasks = get_all_tasks()
    return [
        TaskListItem(
            task_id=t.task_id,
            name=t.name,
            description=t.description,
            icon=t.icon,
            category=t.category
        )
        for t in tasks
    ]

@router.get("/tasks/{task_id}", response_model=TaskDefinition)
async def get_task_definition(task_id: str):
    """获取任务详细定义"""
    from deepanalyze.analysis.task_SOP.registry import get_task_by_id
    from API.prompts import load_prompt_template
    
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    prompt_template = load_prompt_template(task_id)
    
    return TaskDefinition(
        task_id=task.task_id,
        name=task.name,
        description=task.description,
        icon=task.icon,
        category=task.category,
        params=[p.__dict__ for p in task.params],
        stages=[s.__dict__ for s in task.stages],
        prompt_template=prompt_template
    )

@router.post("/execute")
async def execute_sop_task(request: TaskExecuteRequest):
    """
    执行SOP任务
    
    1. 加载任务定义和Prompt模板
    2. 根据参数构建完整的SOP Prompt
    3. 返回构建好的Prompt供对话系统使用
    """
    from deepanalyze.analysis.task_SOP.registry import get_task_by_id
    from API.prompts import build_sop_prompt
    
    task = get_task_by_id(request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {request.task_id} not found")
    
    # 构建SOP Prompt
    sop_prompt = build_sop_prompt(
        task_id=request.task_id,
        params=request.params
    )
    
    return {
        "task_id": request.task_id,
        "sop_prompt": sop_prompt,
        "stages": [s.__dict__ for s in task.stages],
        "status": "ready"
    }
```

### 6.2 注册到主应用

```python
# API/main.py - 添加SOP路由

from API.sop_api import router as sop_router

app.include_router(sop_router)
```

---

## 七、完整交互时序图

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  用户    │     │  前端    │     │  API     │     │  LLM     │     │ 代码执行 │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │                │
     │ 1. 上传数据文件 │                │                │                │
     │───────────────>│                │                │                │
     │                │ POST /files    │                │                │
     │                │───────────────>│                │                │
     │                │    file_id     │                │                │
     │                │<───────────────│                │                │
     │                │                │                │                │
     │ 2. 点击[评分卡开发]             │                │                │
     │───────────────>│                │                │                │
     │                │ GET /sop/tasks/scorecard        │                │
     │                │───────────────>│                │                │
     │                │  任务定义+参数Schema            │                │
     │                │<───────────────│                │                │
     │                │                │                │                │
     │                │ 3. 展开参数配置面板（内嵌）     │                │
     │<───────────────│                │                │                │
     │                │                │                │                │
     │ 4. 配置参数并点击[执行]         │                │                │
     │───────────────>│                │                │                │
     │                │ POST /sop/execute               │                │
     │                │ {task_id, params}               │                │
     │                │───────────────>│                │                │
     │                │                │ 5. 构建SOP Prompt               │
     │                │  sop_prompt    │                │                │
     │                │<───────────────│                │                │
     │                │                │                │                │
     │                │ 6. POST /v1/chat/completions    │                │
     │                │ (带SOP Prompt) │                │                │
     │                │───────────────>│                │                │
     │                │                │ 7. 转发给LLM   │                │
     │                │                │───────────────>│                │
     │                │                │                │                │
     │                │                │  8. LLM按SOP生成代码            │
     │                │                │<───────────────│                │
     │                │                │                │                │
     │                │                │ 9. 执行代码    │                │
     │                │                │───────────────────────────────>│
     │                │                │                │   执行结果     │
     │                │                │<───────────────────────────────│
     │                │                │                │                │
     │                │  10. SSE流式返回                │                │
     │                │  (进度+代码+结果)               │                │
     │<───────────────│<───────────────│                │                │
     │                │                │                │                │
     │ 11. 显示最终结果                │                │                │
     │ (评分卡表+KS/AUC+图表)          │                │                │
     │<───────────────│                │                │                │
```

---

## 八、扩展：任务分组折叠式设计（可选）

当任务类型超过6个时，可采用分组折叠式设计：

```
┌─────────────────────────────────────┐
│   🎯 任务类型                       │
│   ─────────────────────────────── │
│                                     │
│   ▼ 风控建模                        │  ← 展开状态
│     ┌─────────────────────────┐   │
│     │ 📊 评分卡开发           │●  │
│     └─────────────────────────┘   │
│     ┌─────────────────────────┐   │
│     │ 🎯 策略规则挖掘         │   │
│     └─────────────────────────┘   │
│                                     │
│   ▶ 数据分析                        │  ← 折叠状态
│                                     │
│   ▶ 特征工程                        │  ← 折叠状态
│                                     │
│   ▶ 模型评估                        │  ← 折叠状态
│                                     │
│   ──────────────────────────────   │
│   [+ 自定义任务]                    │
│                                     │
└─────────────────────────────────────┘
```

---

## 九、总结

### 9.1 方案核心要点

| 要素 | 设计方案 |
|------|----------|
| **任务入口** | 左侧列下半部分的任务选项卡（符合原始设想） |
| **参数配置** | 内嵌在中间列顶部，不遮挡工作区（优化点） |
| **Prompt注入** | API层 `prepare_vllm_messages` 函数中注入SOP Prompt |
| **执行流程** | 配置参数 → 构建Prompt → 发送LLM → 执行代码 → 报告生成 → 展示结果 |
| **进度反馈** | 中间对话列显示阶段进度条（评分卡7阶段/规则挖掘6阶段，含报告生成） |
| **状态联动** | 左侧任务选项卡显示当前激活状态（优化点） |
| **报告生成** | 每个任务Pipeline必须包含report_generation阶段 |

### 9.2 与原始设想的对应

| 原始设想 | 方案实现 |
|----------|----------|
| 左侧一分为二 | ✅ 左上文件管理 + 左下任务选项卡 |
| 点击选项卡调取SOP Prompt | ✅ 通过 `/sop/tasks/{id}` 获取Prompt模板 |
| 自动调取配套函数/参数 | ✅ 任务元数据包含参数Schema，动态生成表单 |
| 预设选项卡（评分卡/规则挖掘） | ✅ 从Registry加载任务列表 |

### 9.3 优化增强点

| 优化点 | 效果 |
|--------|------|
| 参数面板内嵌 | 不遮挡工作区，可同时查看文件 |
| 进度条可视化 | 长时间任务有明确反馈（评分卡7阶段/规则挖掘6阶段进度） |
| 状态联动 | 当前任务状态一目了然 |
| 分组折叠（可选） | 支持更多任务类型扩展 |
| 报告生成阶段 | 统一的图表数据生成，供前端渲染 |

### 9.4 已实现模块

| 模块 | 状态 | 说明 |
|------|------|------|
| `rule_mining.py` | ✅ 已实现 | 包含6阶段（v2.0合并优化，含report_generation） |
| `rule_mining_meta.py` | ✅ 已实现 | progress_weight总和=100 |
| `rule_mining_viz.py` | ✅ 已实现 | get_chart_data_for_frontend() |
| `scorecard_development.py` | ✅ 已实现 | 包含7阶段（含report_generation） |
| `scorecard_meta.py` | ✅ 已实现 | progress_weight总和=100 |
| `scorecard_viz.py` | ✅ 已实现 | get_chart_data_for_frontend() |

### 9.5 下一步行动

1. **前端开发**：实现 TaskSelector、ParamConfigPanel、ProgressBar 组件
2. **后端API**：实现 `/sop/*` 系列端点
3. **Prompt模板**：完善评分卡开发的SOP Prompt
4. **样式设计**：设计组件CSS样式
5. **集成测试**：端到端验证完整流程

---

## 十、Chat 任务入口交互优化方案（待实施）

> **优先级**: P2 | **预计工作量**: ~1-2天 | **状态**: 待实施 | **创建日期**: 2026-04-15

### 10.1 现状问题

- `TaskParamCard.tsx`（1372行）与 `TaskConfigPanel.tsx`（661行）功能高度重复，两者最终都调用 `POST /sop/execute`
- TaskParamCard 自建了 `renderParamInput`、`StageParamGroupCard` 等渲染逻辑（~800行），未复用 `DynamicParamRenderer`
- 关键词触发 extraction 模式存在误触发问题（用户聊概念也会触发参数提取）

### 10.2 优化方案（先确认再拉起）

LLM 检测到关键词匹配 SOP 任务后，不直接进入参数提取/拉起配置面板，而是先在对话中展示**轻量任务简介卡片**，由用户确认是否进入 SOP 流程：

```
用户: "帮我做个评分卡"
  → LLM 识别到匹配 SOP 任务
  → 对话中展示任务简介确认卡片：
    ┌─────────────────────────────────────┐
    │ 📊 检测到可能匹配的 SOP 任务        │
    │                                     │
    │ 【评分卡开发】                       │
    │ 基于逻辑回归的标准评分卡开发流程，   │
    │ 包含 WOE分箱、特征筛选、模型训练、   │
    │ 评分刻度转换、模型评估等 7 个阶段。   │
    │                                     │
    │ 输出结果：评分卡表、KS/AUC/PSI 指标、│
    │ Decile 排序性分析、评分分布图表等。   │
    │                                     │
    │ [使用此任务]    [继续对话]            │
    └─────────────────────────────────────┘

  用户点击 [使用此任务] → 拉起 ConfigPanel + 预填 LLM 提取的参数
  用户点击 [继续对话]   → 当作 chat mode 继续自然语言对话
```

### 10.3 核心优势 — 解决意图模糊问题

| 用户输入 | 真实意图 | 当前行为（误触发） | 新方案 |
|---------|---------|-------------------|--------|
| "帮我做个评分卡" | 执行任务 | 生成完整参数卡片 | 展示简介 → 用户确认 → 拉起 ConfigPanel |
| "评分卡的 IV 阈值一般取多少？" | 咨询问题 | 误触发参数提取 | 展示简介 → 用户点"继续对话" → 正常聊天 |
| "评分卡和机器学习模型哪个好？" | 讨论比较 | 误触发参数提取 | 同上 |
| "上次的评分卡结果在哪看？" | 查看历史 | 误触发参数提取 | 同上 |

### 10.4 TaskParamCard 独有能力替代方案

| 能力 | 当前实现 | 新方案替代 | 结论 |
|------|---------|-----------|:----:|
| 参数预填 | LLM 提取参数填入卡片表单 | 用户确认后注入 ConfigPanel 的 formValues | 可替代 |
| 追问缺失参数 | 黄色追问卡片 | ConfigPanel 表单验证 + 下拉选择（比对话打字更高效） | 可替代 |
| JSON 容错 | tryRepairTruncatedJson 在卡片组件内 | 下沉到 `isTaskParamJson()` 解析层（~70行独立函数） | 可替代 |
| 已确认状态 | 绿色"已确认执行"卡片 | 现有系统消息"✅ 任务已启动"已覆盖 | 可替代 |
| 无法识别任务 | 灰色提示卡片 | chat mode 自然语言回复已覆盖 | 可替代 |

### 10.5 实施要点

1. 新建轻量确认卡片组件（~100-150行）：展示任务名称 + 描述 + 阶段列表 + 输出结果简介 + [使用此任务]/[继续对话] 按钮；数据来自 `GET /sop/tasks/{task_id}`
2. 用户点击"使用此任务" → 调用 `setSelectedTaskId` + `setShowConfigPanel(true)` + 注入 LLM 提取的 params 到 ConfigPanel formValues
3. 用户点击"继续对话" → 切回 chat mode，LLM 以自然语言回答
4. 保留 `isTaskParamJson()` 解析函数（~70行），删除 TaskParamCard 完整参数表单组件（~1300行）
5. 统一模型传参方式（当前 TaskParamCard 传 `config_id`，ConfigPanel 传模型名+apiBase，需统一）

### 10.6 防重复确认机制

避免同一话题反复弹出确认卡片：

- **会话级记忆**：用户点击"继续对话"后，将该 task_type 记入 `dismissedTaskTypes` 集合（前端 state），同一会话内不再对同类关键词弹确认
- **复位条件**：仅当消息同时包含**执行意图动词**（"帮我做/执行/开始/跑一个/启动"等）+ 任务关键词时，才对已拒绝的 task_type 重新弹出确认（用户可能改主意了）
- **执行中跳过**：该 task_type 在当前会话已有执行中/已完成的任务 → 不弹确认，直接走 chat mode
- 判定流程：`关键词匹配 → 检查 dismissedTaskTypes → 检查执行意图词 → 检查是否有执行中任务 → 决定弹确认或走 chat`
