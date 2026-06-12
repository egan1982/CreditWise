# Pipeline模式任务流程展示方案优化

## 1. 背景与目标

### 1.1 问题描述

当前Pipeline模式的UI展示形式与原项目（LLM对话模式）存在显著差异：

| 对比维度 | 原项目（LLM模式） | Pipeline模式（当前） |
|---------|------------------|---------------------|
| **中间列展示** | `<Analyze>/<Code>/<Execute>`可折叠卡片 | `TaskProgress`紧凑进度条 |
| **右侧Code列** | Monaco Editor可编辑+Run按钮 | 空置（显示提示文字） |
| **执行过程可见性** | 高（每步骤有详细卡片） | 低（仅进度条） |
| **视觉风格** | 结构化、信息丰富 | 简洁、信息有限 |

### 1.2 优化目标

1. **视觉风格统一**：Pipeline模式的UI与原项目保持基本一致
2. **执行过程可见**：用户可以看到Pipeline的执行过程和详细日志
3. **信息利用率提升**：右侧Code列不再空置，展示有价值的信息
4. **保持核心特性**：Pipeline模式仍为全自动化流程，不支持人工干预

### 1.3 约束条件

- Pipeline模式是全自动化流程，**不支持人工干预**
- 右侧Code列应为**只读模式**，不显示Run按钮
- 不改变Pipeline的执行逻辑，仅改变展示形式

### 1.4 通用性设计

本方案设计为**任务类型无关**，可同时支持：
- ✅ 评分卡开发任务（scorecard_development）
- ✅ 规则挖掘任务（rule_mining）
- ✅ 后续新增任务类型（通过扩展 `getStageConfigs()` 函数）

各任务类型的阶段配置定义在对应的 `*_meta.py` 文件中，前端通过 `taskId` 动态获取。

---

## 2. 方案设计

### 2.1 整体架构

```
┌─────────────────┐  ┌─────────────────────────────┐  ┌─────────────────────┐
│   左侧列        │  │      中间列                  │  │   右侧列            │
│   文件管理      │  │                             │  │                     │
│   任务选择      │  │  ┌─────────────────────┐    │  │  ┌───────────────┐  │
│                 │  │  │ 🔍 数据加载         │    │  │  │ Execution Log │  │
│                 │  │  │ ████████░░ 80%     │    │  │  │               │  │
│                 │  │  │ 检测异常值...       │    │  │  │ [2024-01-15]  │  │
│                 │  │  └─────────────────────┘    │  │  │ 开始数据加载  │  │
│                 │  │  ┌─────────────────────┐    │  │  │ 检查数据质量  │  │
│                 │  │  │ 📊 WOE分箱          │    │  │  │ 检测异常值    │  │
│                 │  │  │ ░░░░░░░░░░ 0%      │    │  │  │ ...           │  │
│                 │  │  │ 等待中              │    │  │  │               │  │
│                 │  │  └─────────────────────┘    │  │  └───────────────┘  │
│                 │  │  ...更多阶段卡片...         │  │                     │
└─────────────────┘  └─────────────────────────────┘  └─────────────────────┘
```

### 2.2 中间列改造：阶段卡片组件

#### 2.2.1 组件设计

创建`SopStageController`组件（原名PipelineStageCards），复用原项目`sectionConfigs`的视觉样式：

```typescript
// 评分卡开发任务阶段配置
const scorecardStageConfigs = {
  data_loading: {
    icon: "📥",
    color: "bg-blue-50 border-blue-200 dark:bg-blue-950/30 dark:border-blue-800",
    label: "数据加载"
  },
  woe_binning: {
    icon: "📊",
    color: "bg-cyan-50 border-cyan-200 dark:bg-cyan-950/30 dark:border-cyan-800",
    label: "WOE分箱"
  },
  feature_selection: {
    icon: "🔍",
    color: "bg-purple-50 border-purple-200 dark:bg-purple-950/30 dark:border-purple-800",
    label: "特征筛选"
  },
  model_training: {
    icon: "🧠",
    color: "bg-orange-50 border-orange-200 dark:bg-orange-950/30 dark:border-orange-800",
    label: "模型训练"
  },
  score_scaling: {
    icon: "📐",
    color: "bg-green-50 border-green-200 dark:bg-green-950/30 dark:border-green-800",
    label: "评分转换"
  },
  model_evaluation: {
    icon: "📈",
    color: "bg-yellow-50 border-yellow-200 dark:bg-yellow-950/30 dark:border-yellow-800",
    label: "模型评估"
  },
  report_generation: {
    icon: "📋",
    color: "bg-gray-50 border-gray-200 dark:bg-gray-950/30 dark:border-gray-700",
    label: "报告生成"
  }
};

// 规则挖掘任务阶段配置（对应 rule_mining_meta.py 中的 stages）
const ruleMiningStageConfigs = {
  preprocessing: {
    icon: "🔧",
    color: "bg-slate-50 border-slate-200 dark:bg-slate-950/30 dark:border-slate-800",
    label: "数据预处理"
  },
  feature_engineering: {
    icon: "⚙️",
    color: "bg-indigo-50 border-indigo-200 dark:bg-indigo-950/30 dark:border-indigo-800",
    label: "特征工程（可选）"
  },
  generating_rules: {
    icon: "🌲",
    color: "bg-emerald-50 border-emerald-200 dark:bg-emerald-950/30 dark:border-emerald-800",
    label: "规则生成"
  },
  rule_filtering: {
    icon: "🔍",
    color: "bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800",
    label: "规则过滤"
  },
  selecting_rules: {
    icon: "✅",
    color: "bg-green-50 border-green-200 dark:bg-green-950/30 dark:border-green-800",
    label: "最优选择"
  },
  report_generation: {
    icon: "📋",
    color: "bg-gray-50 border-gray-200 dark:bg-gray-950/30 dark:border-gray-700",
    label: "报告生成"
  }
};

// 根据任务类型获取阶段配置
function getStageConfigs(taskId: string): Record<string, StageConfig> {
  switch (taskId) {
    case "scorecard_development":
      return scorecardStageConfigs;
    case "rule_mining":
      return ruleMiningStageConfigs;
    default:
      return {};  // 后续新增任务类型在此扩展
  }
}
```

#### 2.2.2 卡片结构

```tsx
interface StageCardProps {
  stageId: string;
  stageName: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  message: string;
  logs?: string[];
  isCollapsed: boolean;
  onToggle: () => void;
  onClick?: () => void;  // 点击时更新右侧面板
  taskId: string;        // 任务类型ID，用于获取对应的阶段配置
}

function StageCard({ stageId, stageName, status, progress, message, logs, isCollapsed, onToggle, onClick, taskId }: StageCardProps) {
  const stageConfigs = getStageConfigs(taskId);
  const config = stageConfigs[stageId] || { icon: "⚙️", color: "bg-gray-50", label: stageName };
  
  return (
    <div 
      className={cn("border rounded-lg p-3 cursor-pointer", config.color)}
      onClick={onClick}
    >
      {/* 头部：图标、名称、状态 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span>{config.icon}</span>
          <span className="font-medium">{config.label}</span>
          <StatusBadge status={status} />
        </div>
        <button onClick={(e) => { e.stopPropagation(); onToggle(); }}>
          {isCollapsed ? <ChevronDown /> : <ChevronUp />}
        </button>
      </div>
      
      {/* 进度条 */}
      {status === "running" && (
        <div className="mt-2">
          <Progress value={progress} />
          <span className="text-xs text-gray-500">{message}</span>
        </div>
      )}
      
      {/* 可折叠日志区域 */}
      {!isCollapsed && logs && logs.length > 0 && (
        <div className="mt-2 text-xs text-gray-600 space-y-1 max-h-32 overflow-auto">
          {logs.map((log, i) => (
            <div key={i}>{log}</div>
          ))}
        </div>
      )}
    </div>
  );
}
```

### 2.3 右侧Code列改造：只读日志面板

#### 2.3.1 展示模式切换

```tsx
// Pipeline执行时自动切换到日志模式
const [rightPanelMode, setRightPanelMode] = useState<"code" | "log">("code");

// 当Pipeline开始执行时
useEffect(() => {
  if (isSOPExecuting) {
    setRightPanelMode("log");
  }
}, [isSOPExecuting]);
```

#### 2.3.2 日志面板组件

```tsx
interface ExecutionLogPanelProps {
  executionId: string;
  stages: Record<string, StageProgress>;
  currentStage: string;
}

function ExecutionLogPanel({ executionId, stages, currentStage }: ExecutionLogPanelProps) {
  const allLogs = useMemo(() => {
    const logs: Array<{ time: string; stage: string; message: string }> = [];
    Object.values(stages).forEach(stage => {
      stage.logs?.forEach(log => {
        logs.push({
          time: new Date().toLocaleTimeString(),
          stage: stage.stage_name,
          message: log
        });
      });
    });
    return logs;
  }, [stages]);

  return (
    <div className="flex flex-col h-full">
      {/* 头部 */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h2 className="text-sm font-medium">Execution Log</h2>
        <Badge>{currentStage}</Badge>
      </div>
      
      {/* 日志内容（只读） */}
      <div className="flex-1 overflow-auto p-4 font-mono text-sm bg-gray-900 text-gray-200">
        {allLogs.map((log, i) => (
          <div key={i} className="flex gap-2">
            <span className="text-gray-500">[{log.time}]</span>
            <span className="text-blue-400">[{log.stage}]</span>
            <span>{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 2.4 后端改造：日志字段扩展

#### 2.4.1 StageProgress扩展

```python
# executor.py

@dataclass
class StageProgress:
    """阶段进度"""
    stage_id: str
    stage_name: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    progress: float = 0.0  # 0-100
    message: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    # 新增字段
    logs: list[str] = field(default_factory=list)  # 阶段日志列表
```

#### 2.4.2 日志追加方法

```python
# executor.py

def _update_progress(self, stage_id: str, progress: float, message: str):
    """更新阶段进度并追加日志"""
    if stage_id in self.context.stages:
        stage = self.context.stages[stage_id]
        stage.progress = progress
        stage.message = message
        # 追加日志
        timestamp = datetime.now().strftime("%H:%M:%S")
        stage.logs.append(f"[{timestamp}] {message}")
        
        # 状态更新
        if progress == 0:
            stage.status = ExecutionStatus.RUNNING
            stage.started_at = datetime.now()
        elif progress >= 100:
            stage.status = ExecutionStatus.COMPLETED
            stage.completed_at = datetime.now()
    
    self.context.current_stage = stage_id
    self.context.message = message
```

#### 2.4.3 API返回格式更新

```python
# API/sop_api.py

def _format_stage_progress(stage: StageProgress) -> dict:
    """格式化阶段进度"""
    return {
        "stage_id": stage.stage_id,
        "stage_name": stage.stage_name,
        "status": stage.status.value,
        "progress": stage.progress,
        "message": stage.message,
        "started_at": stage.started_at.isoformat() if stage.started_at else None,
        "completed_at": stage.completed_at.isoformat() if stage.completed_at else None,
        "logs": stage.logs  # 新增
    }
```

---

## 3. 可选增强（后续迭代）

### 3.1 伪代码生成

#### 3.1.1 目标

每个阶段显示对应的Python代码片段，让用户了解Pipeline内部执行的逻辑。

#### 3.1.2 实现方案

```python
# 在StageProgress中添加code字段
@dataclass
class StageProgress:
    # ... 现有字段 ...
    code: str = ""  # 阶段对应的Python代码

# 在Pipeline执行时生成伪代码
def _update_progress(self, stage_id: str, progress: float, message: str, code: str = ""):
    if stage_id in self.context.stages:
        stage = self.context.stages[stage_id]
        if code:
            stage.code = code
```

#### 3.1.3 各阶段伪代码示例

```python
STAGE_CODE_TEMPLATES = {
    "data_loading": '''
# 数据加载与验证
df = pd.read_csv(file_path)
train_df, test_df, oot_df = preprocessor.split_data(
    df, target_col="{target_col}",
    sample_type_col="{sample_type_col}"
)
outlier_info = preprocessor.detect_outliers(
    df, method='iqr', threshold=1.5
)
''',
    "woe_binning": '''
# WOE分箱
df_woe, bins, iv_table = woe_transformer.fit_transform(
    train_df, target_col="{target_col}",
    bin_method="{bin_method}",
    max_bins={max_bins}
)
''',
    "feature_selection": '''
# 特征筛选（v4.3调整：不含逐步回归）
selected_features, selection_detail = feature_selector.select_features(
    df_woe, iv_table, woe_cols,
    iv_lower={iv_lower}, iv_upper={iv_upper},
    corr_threshold={corr_threshold},
    vif_threshold={vif_threshold}
    # 注：use_stepwise 已迁移至 model_training 阶段
)
''',
    # ... 更多阶段 ...
}
```

#### 3.1.4 前端展示

```tsx
// 点击阶段卡片时，在右侧显示对应代码
function handleStageClick(stageId: string) {
  const stage = stages[stageId];
  if (stage?.code) {
    setRightPanelMode("code");
    setCodeEditorContent(stage.code);
    setCodeEditorReadOnly(true);  // 只读模式
  }
}
```

### 3.2 阶段输出预览

#### 3.2.1 目标

点击阶段卡片时，在右侧显示该阶段的中间结果预览。

#### 3.2.2 实现方案

```python
# 在StageProgress中添加output_preview字段
@dataclass
class StageProgress:
    # ... 现有字段 ...
    output_preview: dict | None = None  # 阶段输出预览

# 在阶段完成时保存预览
def _update_progress(self, stage_id: str, progress: float, message: str, output_preview: dict = None):
    if stage_id in self.context.stages:
        stage = self.context.stages[stage_id]
        if output_preview:
            stage.output_preview = output_preview
```

#### 3.2.3 各阶段输出预览内容

| 阶段 | 预览内容 |
|------|---------|
| data_loading | 数据概览（行数、列数、缺失值统计、异常值统计） |
| woe_binning | IV表格Top10、单调性报告 |
| feature_selection | 筛选结果汇总、特征数量变化 |
| model_training | 模型系数（含标准误、P值、95%置信区间）、显著性检验结果、**系数方向验证结果**、**迭代验证日志**（v4.3新增）、**统计指标增强**（v4.4新增） |
| score_scaling | 评分参数（基准分、Odds、PDO）、**理论/实际评分范围**、**评分分布统计**、**变量得分详情（可展开）**（v4.5新增） |
| model_evaluation | AUC/KS/Gini指标、过拟合警告 |
| report_generation | 图表缩略图 |

> **📋 v4.3 架构调整说明**：
> 
> 自 v4.3 版本起，逐步回归、显著性检验、系数方向验证从特征筛选阶段（Stage 3）迁移到模型训练阶段（Stage 4），并引入迭代验证机制。因此 `model_training` 阶段的输出预览需要展示更丰富的验证信息：
> 
> | 预览字段 | 说明 |
> |---------|------|
> | `model_coef` | 逻辑回归模型系数 |
> | `significance_test` | 显著性检验结果（p-value） |
> | `coef_direction_check` | 系数方向验证结果（expected vs actual） |
> | `post_validation` | 迭代验证日志（移除的变量及原因） |
> | `final_features` | 验证后最终入模变量列表 |

> **📋 v4.4 统计指标增强说明**：
> 
> 自 v4.4 版本起，模型训练阶段的系数表格新增以下统计指标，增强模型可解释性和诊断能力：
> 
> | 指标字段 | 说明 | 用途 |
> |---------|------|------|
> | `std_err` | 标准误差 | 评估系数估计精度，std_err过大可能存在多重共线性 |
> | `p_value` | P值（含5级显著性标记） | P<0.001 极显著 \| P<0.01 高度显著 \| P<0.05 显著 \| P<0.1 边缘显著 \| P≥0.1 不显著 |
> | `ci_lower` | 95%置信区间下界 | 系数可信范围，CI包含0表示系数可能不显著 |
> | `ci_upper` | 95%置信区间上界 | 同上 |
> 
> **AI分析诊断场景**（自动识别并给出建议）：
> 
> | 问题场景 | 判断标准 | 调整建议 |
> |---------|---------|---------|
> | 标准误偏大 | 系数/标准误 < 2 | 检查VIF值、考虑逐步回归、使用L1正则化 |
> | 置信区间包含0 | ci_lower < 0 且 ci_upper > 0 | 检查变量IV值、考虑移除或重新分箱 |
> | 置信区间过宽 | (ci_upper - ci_lower) / \|coef\| > 2 | 增加样本量、简化模型复杂度 |

> **📋 v4.5 评分转换增强说明**：
> 
> 自 v4.5 版本起，评分转换阶段的输出预览进行全面增强，提供更丰富的评分卡信息：
> 
> | 预览字段 | 说明 |
> |---------|------|
> | `theoretical_score_range` | 理论评分范围（基于各变量得分最小/最大值之和） |
> | `actual_score_stats` | 实际评分分布统计（min/max/mean/std/median/q25/q75） |
> | `scorecard_preview` | 变量得分详情（包含分箱数、得分范围、最大贡献度） |
> | `bin_details` | 可展开的分箱得分明细 |
> 
> **AI分析诊断场景**（自动识别并给出建议）：
> 
> | 问题场景 | 判断标准 | 调整建议 |
> |---------|---------|---------|
> | 基准分偏离常规 | base_score < 500 或 > 750 | 确认业务需求，行业惯例600-660 |
> | PDO设置异常 | pdo < 15 或 > 60 | 调整评分敏感度，常规范围20-50 |
> | 评分区分度不足 | std < 30 | 增大PDO参数，增强区分能力 |
> | 变量贡献度差异过大 | max/min > 5倍 | 检查变量权重，可能存在主导变量 |

> **📋 v4.6 评分转换UI优化说明**：
> 
> 自 v4.6 版本起，评分转换阶段的UI进行以下优化：
> 
> **1. 配置参数区域重构**
> 
> 将输入配置参数（基准分、基准Odds、PDO）从"评分参数"移至独立的"转换配置"区域：
> 
> ```
> ┌─────────────────────────────────────────────────┐
> │ ⚙️ 转换配置（输入参数）                          │
> │ ┌──────────┬──────────┬──────────┐              │
> │ │ 基准分   │ 基准Odds │   PDO    │              │
> │ │   600    │   50:1   │    20    │              │
> │ └──────────┴──────────┴──────────┘              │
> ├─────────────────────────────────────────────────┤
> │ 📊 理论评分范围（计算结果）                      │
> │ ┌──────────┬──────────┬──────────┐              │
> │ │ 理论最低 │ 理论最高 │ 实际分布 │              │
> │ │   450    │   750    │ 480~720  │              │
> │ └──────────┴──────────┴──────────┘              │
> └─────────────────────────────────────────────────┘
> ```
> 
> **2. 完整评分卡CSV下载**
> 
> 新增"下载完整评分卡"按钮，支持导出行业标准格式的CSV文件：
> 
> | CSV列名 | 说明 |
> |---------|------|
> | variable | 变量名 |
> | total_iv | 变量IV值（仅变量首行显示） |
> | cof | 模型系数（仅变量首行显示） |
> | index | 分箱索引 |
> | bin | 分箱区间 |
> | count | 样本数 |
> | count_distr | 样本占比 |
> | good | 好样本数 |
> | bad | 坏样本数 |
> | badprob | 坏样本率 |
> | woe | WOE值 |
> | score | 该分箱对应得分 |
> 
> **后端数据结构新增**：
> 
> ```python
> score_scaling_preview = {
>     # ... 原有字段 ...
>     "full_scorecard_csv": [
>         {"variable": "常数项", "total_iv": -0.02, "cof": "", "index": 0, ...},
>         {"variable": "最近3个月逾期次数", "total_iv": 0.30, "cof": 0.65, ...},
>         ...
>     ]
> }
> ```

#### 3.2.4 前端展示

```tsx
function StageOutputPreview({ stageId, outputPreview }: { stageId: string; outputPreview: any }) {
  if (!outputPreview) return null;
  
  switch (stageId) {
    case "data_loading":
      return <DataLoadingPreview data={outputPreview} />;
    case "woe_binning":
      return <WoeBinningPreview data={outputPreview} />;
    case "feature_selection":
      return <FeatureSelectionPreview data={outputPreview} />;
    // ... 更多阶段 ...
    default:
      return <pre>{JSON.stringify(outputPreview, null, 2)}</pre>;
  }
}
```

### 3.3 阶段详情面板

#### 3.3.1 目标

显示阶段的详细信息，包括参数、执行时间等。

#### 3.3.2 实现方案

> ✅ **已实现**（2024-12-16）

```python
# 在StageProgress中添加详情字段
@dataclass
class StageProgress:
    # ... 现有字段 ...
    params_used: dict = field(default_factory=dict)  # ✅ 使用的参数
    
    @property
    def execution_time_ms(self) -> int | None:  # ✅ 执行时间（毫秒）
        """计算阶段执行时间（毫秒）"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None
    
    # ❌ memory_usage_mb - 已废弃，不实现
```

#### 3.3.3 前端展示

> ✅ **已实现**：执行时间在 `StageOutputPreview.tsx` 头部区域显示

```tsx
// StageOutputPreview.tsx - 执行时间显示
{executionTimeMs != null && status === "completed" && (
  <span className="text-xs text-gray-400 ml-1">
    ({formatExecutionTime(executionTimeMs)})
  </span>
)}
```

#### 3.3.4 实现状态

| 字段 | 状态 | 说明 |
|------|------|------|
| `params_used` | ✅ 已实现 | 阶段开始时从 context.params 复制 |
| `execution_time_ms` | ✅ 已实现 | 通过 started_at/completed_at 计算 |
| `memory_usage_mb` | ❌ 废弃 | 实现复杂度高，收益有限，不实现 |

---

## 4. 实施计划

### 4.1 阶段划分

| 阶段 | 内容 | 工作量 | 优先级 | 状态 |
|------|------|--------|--------|------|
| **Phase 1** | 基础改造（中间列卡片+右侧日志） | 5-7天 | P0 | ✅ 已完成 |
| **Phase 2** | 伪代码生成 | 2-3天 | P1 | ✅ 已完成 |
| **Phase 3** | 阶段输出预览 | 3-4天 | P2 | ✅ 已完成 |
| **Phase 4** | 阶段详情面板 | 2-3天 | P2 | ✅ 部分完成 |

> **Phase 4 状态说明**（2024-12-16更新）：
> - ✅ `params_used`：已实现，阶段开始时从 context.params 复制
> - ✅ `execution_time_ms`：已实现，通过 property 计算
> - ❌ `memory_usage_mb`：已废弃，不实现

### 4.2 Phase 1 详细计划（基础改造）

#### 4.2.1 后端改造（1天）

| 任务 | 文件 | 描述 |
|------|------|------|
| 1.1 | `executor.py` | 在`StageProgress`中添加`logs: list[str]`字段 |
| 1.2 | `executor.py` | 修改`_update_progress`方法追加日志 |
| 1.3 | `API/sop_api.py` | 修改状态API返回格式包含logs |

#### 4.2.2 前端中间列改造（2-3天）

| 任务 | 文件 | 描述 |
|------|------|------|
| 2.1 | `sop/SopStageController.tsx` | 创建阶段卡片组件（原PipelineStageCards） |
| 2.2 | `sop/SopStageController.tsx` | 实现可折叠功能 |
| 2.3 | `sop/SopStageController.tsx` | 复用sectionConfigs视觉样式 |
| 2.4 | `three-panel-interface.tsx` | 集成SopStageController组件 |
| 2.5 | `lib/sopService.ts` | 更新类型定义包含logs |

#### 4.2.3 前端右侧列改造（1-2天）

| 任务 | 文件 | 描述 |
|------|------|------|
| 3.1 | `sop/ExecutionLogPanel.tsx` | 创建只读日志面板组件 |
| 3.2 | `three-panel-interface.tsx` | 添加右侧面板模式切换逻辑 |
| 3.3 | `three-panel-interface.tsx` | Pipeline执行时自动显示日志面板 |

#### 4.2.4 测试调试（1-2天）

| 任务 | 描述 |
|------|------|
| 4.1 | 验证阶段卡片展示正确 |
| 4.2 | 验证日志实时更新 |
| 4.3 | 验证与原项目视觉风格一致 |
| 4.4 | 验证右侧面板只读（无Run按钮） |

### 4.3 Phase 2 详细计划（伪代码生成）

| 任务 | 文件 | 描述 | 工作量 |
|------|------|------|--------|
| 5.1 | `executor.py` | 在`StageProgress`中添加`code: str`字段 | 0.5天 |
| 5.2 | `scorecard_development.py` | 定义各阶段代码模板 | 1天 |
| 5.3 | `scorecard_development.py` | 在`_update_progress`时填充代码 | 0.5天 |
| 5.4 | `three-panel-interface.tsx` | 点击阶段卡片时显示代码（只读） | 1天 |

### 4.4 Phase 3 详细计划（阶段输出预览）

| 任务 | 文件 | 描述 | 工作量 |
|------|------|------|--------|
| 6.1 | `executor.py` | 在`StageProgress`中添加`output_preview`字段 | 0.5天 |
| 6.2 | `scorecard_development.py` | 各阶段完成时保存预览数据 | 1.5天 |
| 6.3 | `sop/StageOutputPreview.tsx` | 创建预览组件 | 1.5天 |
| 6.4 | `three-panel-interface.tsx` | 集成预览组件 | 0.5天 |

### 4.5 Phase 4 详细计划（阶段详情面板）【部分完成】

> ✅ **实现状态**（2024-12-16更新）：核心字段已实现，`memory_usage_mb` 已废弃。

| 任务 | 文件 | 描述 | 状态 |
|------|------|------|------|
| 7.1 | `executor.py` | 添加`params_used`、`execution_time_ms`字段 | ✅ 已完成 |
| 7.2 | `expert_executor.py` | 添加`execution_time_ms`属性和序列化 | ✅ 已完成 |
| 7.3 | `sopService.ts` | 前端类型定义添加新字段 | ✅ 已完成 |
| 7.4 | `StageOutputPreview.tsx` | 显示执行时间 | ✅ 已完成 |
| ~~7.5~~ | ~~memory_usage_mb~~ | ~~内存占用监控~~ | ❌ 废弃 |

---

## 5. 文件清单

### 5.1 新增文件

| 文件路径 | 描述 |
|---------|------|
| `demo/chat/components/sop/SopStageController.tsx` | 阶段卡片列表+控制组件（原PipelineStageCards） |
| `demo/chat/components/sop/ExecutionLogPanel.tsx` | 只读日志面板组件 |
| `demo/chat/components/sop/StageOutputPreview.tsx` | 阶段输出预览组件（Phase 3） |
| `demo/chat/components/sop/StageDetailPanel.tsx` | 阶段详情面板组件（Phase 4） |

### 5.2 修改文件

| 文件路径 | 修改内容 |
|---------|---------|
| `deepanalyze/analysis/task_SOP/executor.py` | StageProgress扩展、日志追加逻辑 |
| `API/sop_api.py` | API返回格式更新 |
| `demo/chat/components/three-panel-interface.tsx` | 集成新组件、右侧面板模式切换 |
| `demo/chat/components/sop/index.ts` | 导出新组件 |
| `demo/chat/lib/sopService.ts` | 类型定义更新 |
| `deepanalyze/analysis/task_SOP/scorecard_development.py` | 伪代码生成、预览数据保存（Phase 2-4） |

---

## 6. 验收标准

### 6.1 Phase 1 验收标准

- [ ] 中间列显示阶段卡片列表，而非紧凑进度条
- [ ] 阶段卡片使用与原项目一致的视觉样式（图标、颜色）
- [ ] 阶段卡片可折叠，展开时显示日志
- [ ] 右侧Code列在Pipeline执行时显示实时日志
- [ ] 右侧Code列为只读模式，无Run按钮
- [ ] 日志实时更新，无明显延迟

### 6.2 Phase 2 验收标准

- [ ] 点击阶段卡片时，右侧显示对应的Python代码
- [ ] 代码为只读模式，不可编辑
- [ ] 代码内容反映Pipeline实际执行的逻辑

### 6.3 Phase 3 验收标准

- [ ] 阶段完成后，点击卡片可查看输出预览
- [ ] 预览内容针对不同阶段有不同的展示形式
- [ ] 预览数据准确反映阶段输出

### 6.4 Phase 4 验收标准【延后】

- [ ] 阶段详情面板显示使用的参数
- [ ] 阶段详情面板显示执行时间
- [ ] 阶段详情面板显示内存占用（可选）

---

## 7. 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| 日志数据量过大导致性能问题 | 中 | 限制日志条数（如最近100条），使用虚拟滚动 |
| 轮询频率过高导致后端压力 | 低 | 保持现有2秒轮询间隔，必要时使用WebSocket |
| 伪代码与实际执行不一致 | 低 | 代码模板与实际代码保持同步更新 |
| 预览数据序列化失败 | 低 | 添加异常处理，失败时显示错误提示 |

---

## 8. 附录

### 8.1 与原项目的差异对照表

| 功能 | 原项目（LLM模式） | Pipeline模式（改造后） | 说明 |
|------|------------------|----------------------|------|
| 代码编辑 | ✓ 可编辑 | ✗ 只读 | 全自动化，不支持人工干预 |
| Run按钮 | ✓ 显示 | ✗ 隐藏 | 不支持人工干预 |
| 显示内容 | LLM生成的代码 | 执行日志/伪代码 | Pipeline不生成代码 |
| 阶段标签 | `<Analyze>/<Code>/<Execute>` | 阶段名称（数据加载/WOE分箱等） | 简化标签 |
| 折叠功能 | ✓ 支持 | ✓ 支持 | 一致 |
| 视觉样式 | 图标+颜色 | 图标+颜色 | 一致 |

### 8.2 相关文档

- `task_sop_expert_mode_design.md` - 专家模式设计文档
- `pipeline_llm_hybrid_design.md` - Pipeline与LLM混合方案
- `SOP_WebUI_Detail_Design.md` - WebUI详细设计
- `scorecard_development_task_design.md` - 评分卡开发任务核心设计文档

---

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.0 | 2024-12-15 | 初始版本 |
| v1.1 | 2024-12-16 | 完善Phase 4实现状态说明 |
| v1.2 | 2025-02-04 | 同步v4.3架构调整：model_training阶段输出预览增加系数方向验证和迭代验证日志 |
| v1.3 | 2025-02-04 | 同步v4.4统计指标增强：model_training阶段新增标准误、95%置信区间、P值5级显著性标记及AI诊断场景说明 |
| v1.4 | 2025-02-04 | 同步v4.5评分转换增强：score_scaling阶段新增理论/实际评分范围、评分分布统计、变量得分详情（可展开）及AI诊断场景 |
| v1.5 | 2025-02-04 | v4.6评分转换UI优化：(1)配置参数（基准分/Odds/PDO）移至"转换配置"区域；(2)新增完整评分卡CSV下载功能（行业标准格式） |
| v1.6 | 2025-02-04 | v4.7模型评估PSI稳定性指标：(1)新增PSI计算（Train vs OOT优先，无OOT时Train vs Test）；(2)前端4列展示（AUC/KS/Gini/PSI）；(3)PSI阈值说明 |

---

## v4.7 模型评估PSI稳定性指标

### 需求背景
模型评估阶段缺少PSI（Population Stability Index）稳定性指标，这是行业标准中的必要评估项。

### PSI计算策略

| 场景 | 比较方式 | 说明 |
|------|----------|------|
| 有OOT数据 | Train vs OOT | ⭐ 最佳实践：检测模型在未来时间段的稳定性 |
| 无OOT数据 | Train vs Test | 退化方案：检测数据划分的一致性 |

### PSI阈值解读

| PSI值 | 稳定性等级 | 颜色 | 建议 |
|-------|-----------|------|------|
| < 0.1 | 稳定 | 绿色 | 模型可部署 |
| 0.1 ~ 0.25 | 轻微变化 | 黄色 | 需关注，可能需要重新校准 |
| > 0.25 | 显著变化 | 红色 | 模型可能需要重建 |

### 后端实现

```python
# scorecard_development.py - model_evaluation阶段

# PSI计算
psi_result = None
try:
    train_scores = sc.scorecard_ply(train_df, scorecard_, only_total_score=True)['score'].values
    
    if oot_df is not None:
        # Train vs OOT（最佳实践）
        oot_scores = sc.scorecard_ply(oot_df, scorecard_, only_total_score=True)['score'].values
        psi_value = self._calculate_psi(train_scores, oot_scores)
        psi_comparison = "训练集 vs OOT"
    else:
        # Train vs Test（退化方案）
        test_scores = sc.scorecard_ply(test_df, scorecard_, only_total_score=True)['score'].values
        psi_value = self._calculate_psi(train_scores, test_scores)
        psi_comparison = "训练集 vs 测试集"
    
    psi_result = {
        "value": round(psi_value, 4),
        "comparison": psi_comparison,
        "stability": "稳定" if psi_value < 0.1 else "轻微变化" if psi_value < 0.25 else "显著变化",
        "level": "good" if psi_value < 0.1 else "warning" if psi_value < 0.25 else "bad"
    }
except Exception as e:
    logger.warning(f"PSI calculation failed: {e}")
```

### 前端展示

```
┌─────────────────────────────────────────────────────────────────────┐
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐                   │
│  │  AUC   │  │   KS   │  │  Gini  │  │  PSI   │  ← 4列布局        │
│  │ 0.7097 │  │ 0.3148 │  │ 0.4194 │  │ 0.0523 │                   │
│  │训练:    │  │训练:    │  │训练:    │  │ 稳定 ✓ │                   │
│  │ 0.7178 │  │ 0.3069 │  │ 0.4355 │  │        │                   │
│  └────────┘  └────────┘  └────────┘  └────────┘                   │
│                                                                    │
│  • PSI比较：训练集 vs OOT | <0.1 稳定 | 0.1~0.25 轻微变化 | >0.25 显著变化 │
│                                                                    │
│  ⚠️ 注意: 训练集KS显著高于测试集KS，可能存在过拟合（如有警告）      │
└─────────────────────────────────────────────────────────────────────┘
```

### PSI计算公式

```
PSI = Σ (Actual% - Expected%) × ln(Actual% / Expected%)

其中：
- Expected%：基准分布（训练集）各分箱的样本占比
- Actual%：比较分布（OOT/测试集）各分箱的样本占比
- 使用10个等宽分箱
```
