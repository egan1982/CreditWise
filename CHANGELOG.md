# DeepAnalyze 功能开发清单

> 本文档记录了相较于原始项目的所有新增、优化和调整功能，以及下一阶段待完成的优化事项。

---

## 〇、最新更新

### 2025-12-19 系统提示词优化与文档重构

#### 背景
LLM SOP 模式废弃后，LLM 在新架构中的角色从"执行引擎"转变为"智能入口"，原有系统提示词需要适配新的 LLM+Pipeline 架构。

#### 更新内容

**文档重命名与重构**
| 原文件 | 新文件 | 说明 |
|--------|--------|------|
| `docs/系统提示词说明及使用指南.md` | `docs/system_prompt_guide.md` | 英文重命名 + 内容重构 |

**系统提示词优化** (`deepanalyze/analysis/task_SOP/llm_param_extractor.py`)
| 优化项 | 说明 |
|--------|------|
| 角色定位明确 | 强调"智能入口"而非"执行引擎" |
| 约束条件强化 | 明确不生成代码、不干预执行流程 |
| 任务类型无关 | 一个提示词适用于所有 SOP 任务 |
| 置信度标准化 | 添加置信度评估标准表格 |

**预设配置卡更新** (`llm_manager_integrated/frontend/shared/js/model_task_presets.js`)
| 原预设 | 新预设 | 说明 |
|--------|--------|------|
| 数据分析 | 通用对话 | 日常问答、数据咨询、概念解释 |
| 特征工程 | 参数推断 | 从自然语言提取 SOP 任务参数 |
| 模型开发 | 结果解释 | 将分析结果转为业务语言 |
| 策略评估 | - | 已删除 |
| 报表报告 | - | 已删除 |

**UI 文件同步更新**
- `llm_manager_integrated/frontend/shared/html/model-config-modal.html`
- `llm_manager_integrated/frontend/shared/js/model-config.js`

**引用更新**
- `CHANGELOG.md` 中文档引用已更新

---

### 2025-12-18 LLM SOP 模型配置传递修复

#### 问题描述
LLM SOP 模式执行任务时，未使用前端 ModelSelector 选择的模型配置，始终使用默认的 `deepseek-chat` 模型。

#### 修复内容

**API 层修改** (`API/sop_api.py`)
| 修改 | 说明 |
|------|------|
| `TaskExecuteRequest` 新增字段 | `model`: LLM模型名称<br>`api_base`: LLM API基础URL |

**执行器修改** (`deepanalyze/analysis/task_SOP/executor.py`)
| 修改 | 说明 |
|------|------|
| `ExecutionContext` 新增字段 | `model`, `api_base` |
| `ExecutionStore.create()` | 接受 LLM 配置参数 |
| `execute_async()` | 传递 LLM 配置到执行上下文 |
| `_get_llm_executor()` | 根据配置动态创建/复用执行器 |
| `_run_llm_sop_task()` | 使用 context 中的 LLM 配置 |

**错误信息增强** (`llm_manager_integrated/api/routes/proxy/proxy.py`)
| 修改 | 说明 |
|------|------|
| `httpx.RequestError` 处理 | 增强错误信息，显示错误类型和目标URL |
| 请求日志 | 添加转发请求的详细日志 |

#### 前端适配
前端调用 `/sop/execute` 时需传递 ModelSelector 选择的配置：
```javascript
{
  // ...其他参数
  model: 'gemini-2.5-flash',  // 来自 ModelSelector
  api_base: 'http://localhost:8200/llm-manager/api/proxy'
}
```

---

### 2025-12-15 Task SOP 统一实施路线图第三阶段完成

#### 完成内容概览
完成了 `unified_implementation_roadmap.md` 中规划的第三阶段所有非延后内容：

| 模块 | 阶段 | 状态 |
|------|------|------|
| Pipeline UI | Phase 2-3（伪代码+预览） | ✅ 已完成 |
| Rule Mining | Phase 1-4（质量验证+稳定性+说明+解读） | ✅ 已完成 |

#### Rule Mining Enhancement 详细更新

**Phase 1: 规则质量验证模块**
| 新增类/方法 | 文件 | 说明 |
|------------|------|------|
| `RuleValidator` | `rule_mining.py` | 规则质量验证器 |
| `_check_coverage()` | - | 覆盖率检测 |
| `_check_conflicts()` | - | 冲突检测 |
| `_check_overlap()` | - | 重叠度检测（Jaccard） |
| `_check_redundancy()` | - | 冗余检测 |
| `_calculate_quality_score()` | - | 综合质量评分(0-100) |

**Phase 2: 规则稳定性检测（PSI）**
| 新增方法 | 文件 | 说明 |
|---------|------|------|
| `calculate_rule_psi()` | `RuleEvaluator` | 计算规则PSI |
| `calculate_rule_psi_by_time()` | `RuleEvaluator` | 按时间分段计算PSI |

PSI阈值标准：
- `<0.1`: 稳定
- `0.1-0.25`: 轻微变化
- `≥0.25`: 显著变化

**Phase 3: 前端分箱方法说明**
| 文件 | 更新内容 |
|------|---------|
| `DynamicParamRenderer.tsx` | 分箱方法选择器添加Tooltip浮动说明（替代已删除的RuleMiningConfigPanel） |

**Phase 4: 规则业务解读增强**
| 新增类/方法 | 文件 | 说明 |
|------------|------|------|
| `RuleInterpreter` | `rule_mining.py` | 规则业务解读器 |
| `interpret()` | - | 规则转业务文本 |
| `interpret_rules_batch()` | - | 批量规则解读 |

**前端展示更新**
| 新增组件 | 文件 | 说明 |
|---------|------|------|
| `ValidationReportPanel` | `RuleMiningResults.tsx` | 质量验证报告面板 |
| `PSIReportPanel` | `RuleMiningResults.tsx` | PSI稳定性报告面板 |

#### Pipeline集成
在 `RuleMiningPipeline.run()` 报告生成阶段自动执行：
- `RuleValidator.validate()` → `validation_report`
- `RuleEvaluator.calculate_rule_psi()` → `psi_report`

#### BUG修复
| 问题 | 文件 | 修复 |
|------|------|------|
| 前后端API路径不一致 | `sopService.ts` | `/sop/build-prompt` → `/sop/prompt/build` |

#### 文档更新
| 文档 | 更新内容 |
|------|---------|
| `rule_mining_task_design.md` | 更新至v1.3，添加第三阶段完成内容 |
| `scorecard_development_task_design.md` | 更新至v1.2，标记所有任务为已完成 |
| `routing_architecture.md` | 新增SOP API路由（/sop/*） |

---

### 2025-12-10 规则挖掘二值型特征方向优化

#### 功能增强
针对数据预处理后生成的二值型特征（0/1值），优化规则方向支持：

| 特征类型 | 识别方式 | 方向 | 示例 |
|----------|----------|------|------|
| One-Hot编码特征 | 列名含 `_is_` | `==` | `gender_is_male == 1` |
| 文本关键词特征 | 列名含 `_txt_has_` | `==` | `desc_txt_has_fraud == 1` |
| 标志位特征 | 列名含 `_flag_`、`_binary_` | `==` | `is_vip_flag == 1` |
| 数据推断二值 | 仅含0/1值 | `==` | `has_phone == 1` |

#### 修改文件
| 文件 | 操作 | 说明 |
|------|------|------|
| `deepanalyze/analysis/task_SOP/rule_mining.py` | **更新** | 新增 `is_binary_feature()`、`detect_binary_features()` 方法 |
| `deepanalyze/analysis/task_SOP/rule_mining.py` | **更新** | `generate_rules()` 对二值特征使用 `==` 方向 |
| `deepanalyze/analysis/task_SOP/rule_mining.py` | **更新** | `get_split_direction()` 跳过二值特征推断 |
| `deepanalyze/analysis/task_SOP/rule_mining.py` | **更新** | `filter_by_direction()` 支持 `==` 方向过滤 |
| `deepanalyze/analysis/task_SOP/SOP_docs/rule_mining_workflow.md` | **更新** | 添加二值特征方向说明 |
| `deepanalyze/analysis/task_SOP/rule_mining_meta.py` | **更新** | SOP提示词模板增加二值特征处理说明 |
| `tests/test_rule_mining.py` | **新增** | 二值特征检测与规则生成测试用例 |

#### 新增常量与方法
```python
# 二值特征识别指示符
DEFAULT_BINARY_INDICATORS = ['_is_', '_txt_has_', '_flag_', '_binary_']

# 新增方法
def is_binary_feature(col_name: str, series: pd.Series) -> bool: ...
def detect_binary_features(df: pd.DataFrame, feature_cols: list[str]) -> set[str]: ...
```

#### 方向类型扩展
| 方向 | 适用场景 | 规则示例 |
|------|----------|----------|
| `<=` | 数值特征（越小风险越高） | `age <= 25` |
| `>` | 数值特征（越大风险越高） | `debt_ratio > 0.8` |
| `==` | **二值特征（等于1表示命中）** | `is_blacklist == 1` |

---

### 2025-12-09 业务场景SOP模块与特征分析依赖增强

#### 新增SOP任务模块
| 文件 | 说明 |
|------|------|
| `deepanalyze/analysis/task_SOP/__init__.py` | SOP模块导出 |
| `deepanalyze/analysis/task_SOP/rule_mining.py` | 策略规则挖掘核心实现 |
| `deepanalyze/analysis/task_SOP/SOP_docs/rule_mining_workflow.md` | 规则挖掘工作流说明文档 |
| `docs/SOP_WebUI_Integration_design.md` | SOP WebUI集成功能优化设计文档 |

#### 规则挖掘模块核心类
- `RuleMiner` - 基于决策树的规则生成与过滤
- `RuleEvaluator` - 规则效果评估（recall/bad_rate/lift/hit_rate）
- `RuleSelector` - 贪心算法最优规则集选择
- `RuleMiningPipeline` - 完整流程编排

#### 新增特征相关性分析依赖
| 库 | 版本 | 用途 |
|---|---|---|
| `statsmodels` | 0.14.6 | 偏相关、多变量回归、深度统计分析 |
| `plotly` | 6.5.0 | 交互式可视化 |
| `pingouin` | 0.5.5 | 多种相关性检验、效应量计算 |

#### requirements.txt 更新
```diff
+ # Feature Correlation Analysis & Advanced Statistics
+ statsmodels              # 偏相关、多变量回归、深度统计分析
+ plotly                   # 交互式可视化
+ pingouin                 # 多种相关性检验、效应量计算
```

---

## 一、项目架构优化

### 1.1 前后端分离架构
| 组件 | 端口 | 技术栈 | 说明 |
|------|------|--------|------|
| 三列式前端 | 3000 | Next.js | 主应用界面，数据科学任务交互 |
| LLM Manager前端 | 3001 | Vite | API管理界面，渠道配置管理 |
| 后端API | 8200 | FastAPI | 统一API服务，包含主应用和LLM Manager |

### 1.2 路由系统重构
- **主应用路由**：`/workspace/*`、`/execute/*`、`/export/*`
- **LLM Manager子应用**：`/llm-manager/*`
- **代理服务**：`/llm-manager/api/proxy/*`
- **管理API**：`/llm-manager/api/manage/*`

### 1.3 开发/生产模式切换
- **开发模式**：`/llm-manager` 重定向到 `localhost:3001`
- **生产模式**：FastAPI直接提供静态页面
- **Vite代理配置**：自动代理 `/llm-manager` 到后端

---

## 二、LLM Manager系统集成

### 2.1 渠道管理功能
| 功能 | API端点 | 说明 |
|------|---------|------|
| 获取渠道列表 | `GET /llm-manager/api/manage/channels` | 支持分页和过滤 |
| 创建渠道 | `POST /llm-manager/api/manage/channels` | 支持多种供应商类型 |
| 更新渠道 | `PUT /llm-manager/api/manage/channels/{id}` | 更新配置和参数 |
| 删除渠道 | `DELETE /llm-manager/api/manage/channels/{id}` | 软删除支持 |
| 渠道测试 | `POST /llm-manager/api/manage/channels/{id}/test-via-proxy` | 通过代理测试连接 |

### 2.2 支持的供应商类型
- OpenAI (GPT系列)
- GoogleAI (Gemini系列)
- DeepSeek (DeepSeek系列)
- Claude (Anthropic系列)
- 通义千问 (阿里云)
- 自定义 (OpenAI兼容格式)

### 2.3 API代理功能
**实现位置**：`llm_manager_integrated/api/routes/proxy/proxy.py`

| 功能 | 说明 |
|------|------|
| 请求转发 | 转发到激活渠道的外部API |
| 负载均衡 | 多渠道智能负载分发 |
| 失败重试 | 自动重试机制 |
| 日志记录 | 完整的请求/响应日志 |
| 指标更新 | 实时更新渠道指标 |

### 2.4 API日志系统
**实现位置**：`llm_manager_integrated/api/routes/logs.py`

- 请求/响应详情记录
- Token使用统计
- 响应时间记录
- 错误日志追踪

---

## 三、模型管理功能改造

### 3.1 Channel模型扩展
**实现位置**：`llm_manager_integrated/models/schemas.py`

```python
class Channel(BaseModel):
    id: int
    name: str
    type: str           # 供应商类型
    models: str         # 模型名称
    api_base: str       # API端点
    api_key: str        # API密钥
    status: bool        # 激活状态（支持多个同时激活）
    max_qps: int        # 最大QPS
    timeout: int        # 超时时间
    weight: int         # 权重配置
```

### 3.2 ModelConfig模型
**实现位置**：`llm_manager_integrated/models/schemas.py`

| 字段 | 类型 | 说明 |
|------|------|------|
| `temperature` | float | 温度参数 (0-2) |
| `top_p` | float | 核采样参数 (0-1) |
| `max_tokens` | int | 最大生成token数 |
| `frequency_penalty` | float | 频率惩罚 |
| `presence_penalty` | float | 存在惩罚 |
| `system_prompt` | str | 系统提示词 |
| `enable_web_search` | bool | 联网搜索开关 |
| `enable_deep_thinking` | bool | 深度思考开关 |
| `thinking_budget` | int | 思考预算 |
| `include_thoughts` | bool | 是否包含思考过程 |

### 3.3 任务类型映射API
**实现位置**：`llm_manager_integrated/api/routes/channels.py`

| API端点 | 说明 |
|---------|------|
| `GET /channels/active-configs` | 获取所有激活渠道的配置 |
| `GET /channels/{id}/model-config` | 获取指定渠道的模型配置 |
| `POST /channels/{id}/model-config` | 保存模型配置 |
| `DELETE /channels/{id}/model-config` | 删除模型配置 |

### 3.4 前端配置弹窗
**实现位置**：`llm_manager_integrated/frontend/shared/js/model-config.js`

功能特性：
- ✅ 基础参数配置（temperature、top_p、max_tokens）
- ✅ 高级参数配置（frequency_penalty、presence_penalty）
- ✅ 系统提示词编辑
- ✅ 联网搜索和深度思考开关
- ✅ 预设配置快速应用
- ✅ 参数实时预览

### 3.5 任务预设配置
**实现位置**：`llm_manager_integrated/frontend/shared/js/model_task_presets.js`

| 预设名称 | 适用场景 | 关键参数 |
|----------|----------|----------|
| 数据分析 | 数据处理、统计分析 | temperature=0.4, top_p=0.9 |
| 代码生成 | 编程、脚本开发 | temperature=0.2, top_p=0.8 |
| 创意写作 | 文案、内容创作 | temperature=1.2, top_p=0.95 |
| 对话聊天 | 通用对话 | temperature=0.7, top_p=1.0 |
| 研究报告 | 深度分析、报告生成 | temperature=0.5, top_p=0.85 |

---

## 四、/models端点优化

### 4.1 新增OpenAI兼容端点
**实现位置**：`llm_manager_integrated/api/routes/proxy/models_proxy.py`

```
GET /llm-manager/api/models
```

**响应格式**：
```json
{
  "object": "list",
  "data": [
    {
      "id": "deepseek-chat",
      "object": "model",
      "created": 1764878386,
      "owned_by": "deepseek"
    }
  ]
}
```

### 4.2 过滤功能
| 参数 | 说明 |
|------|------|
| `proxy_type` | 按供应商类型过滤 |
| `include_unavailable` | 是否包含不可用模型 |
| `refresh_cache` | 刷新缓存 |

### 4.3 渠道测试功能
- 通过代理测试渠道连接
- 验证API密钥有效性
- 检查模型可用性

---

## 五、API LLM业务优化

### 5.1 API_BASE改用LLM Manager代理
**实现位置**：`API/config.py`

```python
# 已改为使用LLM Manager代理
API_BASE = os.environ.get("LLM_API_BASE", "http://localhost:8200/llm-manager/api/proxy")
```

**优势**：
- 统一的API管理入口
- 自动负载均衡
- 完整的日志记录
- 故障自动切换

### 5.2 代理功能完整实现
**实现位置**：`llm_manager_integrated/api/routes/proxy/proxy.py`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/chat/completions` | POST | OpenAI兼容的聊天完成接口 |
| `/channels/status` | GET | 渠道状态查询 |
| `/load-balancer/strategy` | POST | 负载均衡策略配置 |
| `/load-balancer/metrics` | GET | 负载均衡器指标 |

---

## 六、三列式前端组件开发

### 6.1 ModelSelector组件
**实现位置**：`demo/chat/components/ModelSelector.tsx`

功能：
- ✅ 从 `/llm-manager/api/models/active-configs` 获取配置列表
- ✅ 显示配置参数（temperature、top_p、max_tokens）
- ✅ 显示联网搜索和深度思考状态
- ✅ 支持打开模型配置模态框

### 6.2 ModelConfigModal组件
**实现位置**：`demo/chat/components/ModelConfigModal.tsx`

功能：
- ✅ 模型参数编辑界面
- ✅ 系统提示词编辑
- ✅ 预设配置选择
- ✅ 参数保存和重置

---

## 七、下一阶段待完成优化事项

### 7.1 三列式前端模型选择集成 ✅ 已完成
**当前状态**：ModelSelector组件已开发并集成到主界面

**已完成工作**：
- [x] 在 `three-panel-interface.tsx` 中导入 ModelSelector 组件
- [x] 添加 `selectedConfig` 状态变量
- [x] 修改 `handleSendMessage` 函数使用选择的模型配置
- [x] 将模型选择框集成到消息输入区域

**实现位置**：`demo/chat/components/three-panel-interface.tsx`

**集成代码**：
```typescript
// 导入 (第70行)
import ModelSelector from "./ModelSelector";

// 状态 (第350行)
const [selectedConfig, setSelectedConfig] = useState<ModelConfig | null>(null);

// 使用配置 (第2208-2229行)
model: selectedConfig?.models?.split(",")[0]?.trim() || "deepseek-chat",
temperature: selectedConfig.temperature,
max_tokens: selectedConfig.max_tokens,
system_prompt: selectedConfig.system_prompt || undefined,
```

### 7.2 系统提示词集成 ✅ 已完成
**当前状态**：已整合到 `chat_api.py`

**完成内容**：
- ✅ 修改 `API/utils.py` 的 `prepare_vllm_messages` 函数添加 `system_prompt` 参数
- ✅ 在 `chat_api.py` 中支持 `system_prompt` 参数
- ✅ 系统提示词可从 LLM Manager 配置传递
- ✅ 保持向后兼容（无配置时保持现有行为）

**使用方式**：
```python
# API调用时传递system_prompt
response = requests.post("/v1/chat/completions", json={
    "model": "deepseek-chat",
    "messages": [...],
    "system_prompt": "你是一个数据分析专家...",  # 可选
    "enable_code_execution": True  # 可选，默认True
})
```

### 7.3 /models端点缓存机制 ✅ 已完成
**当前状态**：已实现完整的内存缓存机制

**已完成工作**：
- [x] 实现内存缓存机制（ModelsCache类）
- [x] 添加缓存过期时间配置（默认TTL: 5分钟）
- [x] 实现缓存刷新逻辑（refresh_cache参数）
- [x] 添加缓存命中率监控（/models/cache/stats端点）
- [x] 渠道变更时自动失效缓存

**新增API端点**：
| 端点 | 方法 | 说明 |
|------|------|------|
| `/llm-manager/api/models` | GET | 模型列表（支持缓存） |
| `/llm-manager/api/models/cache/stats` | GET | 缓存统计信息 |
| `/llm-manager/api/models/cache/invalidate` | POST | 手动使缓存失效 |
| `/llm-manager/api/models/cache/reset-stats` | POST | 重置统计信息 |

**缓存特性**：
- TTL过期机制（可配置）
- 线程安全
- 按查询参数分离缓存
- 缓存命中率监控
- 渠道CRUD操作自动触发缓存失效

**目标指标**：
- 响应时间 < 100ms ✅
- 缓存命中率 > 80% ✅

### 7.4 监控日志增强 ⚠️ 低优先级
**待完成工作**：
- [ ] 添加详细的请求日志记录
- [ ] 实现端点性能监控
- [ ] 添加错误率统计
- [ ] 实现成本分析功能

### 7.5 安全性增强 ⚠️ 低优先级
**待完成工作**：
- [ ] 添加访问控制
- [ ] 实现API密钥验证
- [ ] 添加请求频率限制

---

## 八、文档整合说明

本文档整合了以下任务文档的内容：

| 原文档 | 整合内容 |
|--------|----------|
| `routing_architecture.md` | 第一节：项目架构优化 |
| `模型管理功能改造计划.md` | 第三节：模型管理功能改造 |
| `docs/system_prompt_guide.md` | 第七节：系统提示词集成待办 |
| `models端点改造后续优化计划.md` | 第四节：/models端点优化 |
| `API LLM业务应用优化任务.md` | 第五节：API LLM业务优化 |
| `todo.md` | 第七节：三列式前端集成待办 |

---

## 九、版本信息

- **创建时间**：2025-12-08
- **最后更新**：2025-12-08
- **项目版本**：基于原始DeepAnalyze项目的增强版本
- **备份文件**：`DeepAnalyze_Backup_20251208_125546.zip`

---

## 十、更新日志

### 2025-12-08 Chat API整合

#### 整合内容
将 `simple_chat_api.py` 的功能整合到 `chat_api.py`，统一聊天API入口。

#### 修改文件
| 文件 | 操作 | 说明 |
|------|------|------|
| `API/chat_api.py` | **重写** | 整合版，支持system_prompt、enable_code_execution开关、LLMClientManager |
| `API/utils.py` | **更新** | `prepare_vllm_messages`添加`system_prompt`参数 |
| `API/main.py` | **更新** | import从`simple_chat_api`改为`chat_api` |
| `API/simple_chat_api.py` | **移动** | → `deprecated_files/` |
| `API/simple_utils.py` | **移动** | → `deprecated_files/` |

#### 新增API参数
```python
@router.post("/v1/chat/completions")
async def chat_completions(
    model: str,
    messages: List[Dict],
    file_ids: Optional[List[str]] = None,      # 文件附件
    temperature: float = 0.4,
    stream: bool = False,
    system_prompt: Optional[str] = None,        # NEW: 系统提示词
    enable_code_execution: bool = True,         # NEW: 代码执行开关
)
```

#### 工作模式
| 模式 | `enable_code_execution` | 功能 |
|------|------------------------|------|
| **简单对话** | `False` | 直接转发LLM响应，无代码执行 |
| **DeepAnalyze Agent** | `True` (默认) | 解析`<Code>`标签、执行Python、追踪文件、生成报告 |

---

## 十一、快速参考

### 启动命令
```powershell
# 完整服务启动
.\start_all_api.ps1

# 仅后端
.\start_api_only.ps1

# 开发模式
.\start_dev.ps1
```

### 关键端点
| 功能 | 端点 |
|------|------|
| **聊天完成（整合版）** | `POST /v1/chat/completions` |
| 代理聊天 | `POST /llm-manager/api/proxy/chat/completions` |
| 模型列表 | `GET /llm-manager/api/models` |
| 模型缓存统计 | `GET /llm-manager/api/models/cache/stats` |
| 渠道管理 | `GET/POST /llm-manager/api/manage/channels` |
| 模型配置 | `GET/POST /channels/{id}/model-config` |
| API日志 | `GET /llm-manager/api/logs/list` |

### 管理界面
- **主应用**：http://localhost:3000
- **LLM Manager**：http://localhost:3001
- **API文档**：http://localhost:8200/docs

---

## 十二、详细更新日志

### 2025-12-08 /models端点缓存机制实现

#### 实现内容
为 `/llm-manager/api/models` 端点添加完整的内存缓存机制，提升响应性能。

#### 修改文件
| 文件 | 操作 | 说明 |
|------|------|------|
| `llm_manager_integrated/api/routes/proxy/models_proxy.py` | **重写** | 添加ModelsCache类、缓存统计、管理端点 |
| `llm_manager_integrated/api/routes/channels.py` | **更新** | 渠道CRUD操作时自动使缓存失效 |
| `CHANGELOG.md` | **更新** | 记录缓存机制实现 |

#### 缓存机制设计
```python
class ModelsCache:
    """
    特性：
    - TTL过期机制（默认5分钟）
    - 线程安全（RLock）
    - 按查询参数分离缓存
    - LRU淘汰策略
    - 缓存统计监控
    """
```

#### 新增API端点
```
GET  /llm-manager/api/models/cache/stats      # 缓存统计
POST /llm-manager/api/models/cache/invalidate # 手动失效
POST /llm-manager/api/models/cache/reset-stats # 重置统计
```

#### 自动缓存失效触发点
- `POST /channels` - 创建渠道
- `PUT /channels/{id}` - 更新渠道
- `DELETE /channels/{id}` - 删除渠道
