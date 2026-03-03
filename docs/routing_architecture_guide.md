# DeepAnalyze 项目前后端路由关系图

## 1. 整体架构概述

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                 DeepAnalyze 系统                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  前端应用 (3000, 3001)                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────┐     │
│  │  三列式前端 (Next.js - 端口 3000)                                          │     │
│  │  ├── 主页 (/) - 主界面                                                      │     │
│  │  ├── 聊天组件 - 调用聊天API                                                 │     │
│  │  ├── 工作区管理 - 文件操作                                                   │     │
│  │  └── 代码执行 - 代码运行                                                     │     │
│  └─────────────────────────────────────────────────────────────────────────────┘     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐     │
│  │  LLM Manager 前端 (Vite - 端口 3001)                                       │     │
│  │  ├── 主页 (/) - LLM管理界面                                                  │     │
│  │  ├── 渠道管理 - 管理LLM渠道                                                 │     │
│  │  ├── 监控面板 - 系统监控                                                     │     │
│  │  └── 日志查看 - API日志                                                      │     │
│  └─────────────────────────────────────────────────────────────────────────────┘     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  后端API服务 (FastAPI - 端口 8200)                                                │
│  ┌─────────────────────────────────────────────────────────────────────────────┐     │
│  │  主应用路由 (/)                                                             │     │
│  │  ├── 根路径 (/) - 健康检查与服务信息                                         │     │
│  │  ├── /health - 健康检查                                                      │     │
│  │  ├── /docs - API文档                                                         │     │
│  │  ├── /workspace/* - 工作区管理                                               │     │
│  │  ├── /execute/* - 代码执行                                                   │     │
│  │  ├── /export/* - 导出功能                                                     │     │
│  │  ├── /sop/* - SOP任务管理（规则挖掘/评分卡开发）                              │     │
│  └─────────────────────────────────────────────────────────────────────────────┘     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐     │
│  │  LLM Manager 子应用 (/llm-manager)                                           │     │
│  │  ├── 根路径 (/llm-manager) - 开发模式重定向到3001，生产模式提供静态页面       │     │
│  │  ├── /llm-manager/api - LLM管理API                                          │     │
│  │  └── /llm-manager/docs - LLM Manager文档                                    │     │
│  │      ├── /llm-manager/api/proxy - 代理服务                                   │     │
│  │      ├── /llm-manager/api/models - 模型列表                                   │     │
│  │      ├── /llm-manager/api/manage - 渠道管理                                  │     │
│  │      ├── /llm-manager/api/logs - 日志管理                                    │     │
│  │      └── /llm-manager/api/monitoring - 系统监控                              │     │
│  └─────────────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 2. 详细路由说明

### 2.1 前端应用

#### 2.1.1 三列式前端 (Next.js - 端口 3000)
| 功能 | 路由 | API调用 | 描述 |
|------|------|---------|------|
| 主页 | / | - | 主应用界面 |
| 聊天功能 | - | /v1/chat/completions | 聊天请求（支持代码执行模式） |
| 聊天流式 | - | /v1/chat/completions?stream=true | 流式聊天 |
| 工作区管理 | - | /workspace/* | 文件操作 |
| 代码执行 | - | /execute/code | 代码执行 |
| 导出功能 | - | /export/report | 报告导出 |
| /sop/tasks | GET | SOP任务列表 |
| /sop/execute | POST | 执行SOP任务 |

#### 2.1.2 LLM Manager 前端 (Vite - 端口 3001)
| 功能 | 路由 | API调用 | 描述 |
|------|------|---------|------|
| 主页 | / | - | LLM管理界面 |
| 渠道管理 | - | /llm-manager/api/manage/* | 管理LLM渠道 |
| 监控面板 | - | /llm-manager/api/monitoring/* | 获取监控数据 |
| 日志查看 | - | /llm-manager/api/logs/* | 查询API日志 |

### 2.2 后端API服务

#### 2.2.1 主应用路由 (端口 8200)
| 路由 | 方法 | 描述 |
|------|------|------|
| / | GET | 提供健康检查和服务信息 |
| /health | GET | 健康检查 |
| /docs | GET | API文档 |
| /v1/chat/completions | POST | **整合版聊天API**（支持代码执行开关） |
| /workspace/list | GET | 获取工作区列表 |
| /workspace/upload | POST | 上传文件到工作区 |
| /workspace/delete | DELETE | 删除工作区 |
| /workspace/file | DELETE | 删除工作区文件 |
| /workspace/files | GET | 获取工作区文件列表 |
| /workspace/tree | GET | 获取工作区文件树结构 |
| /workspace/clear | DELETE | 清空工作区 |
| /execute/code | POST | 代码执行 |
| /export/report | POST | 导出报告 |

#### 2.2.2 SOP任务管理API (/sop)

**任务定义与数据预览**
| 路由 | 方法 | 描述 |
|------|------|------|
| /sop/tasks | GET | 获取所有可用SOP任务类型 |
| /sop/tasks/{task_id} | GET | 获取指定任务的详细定义 |
| /sop/data/preview | POST | 预览数据文件 |
| /sop/data/analyze | POST | 分析数据特征 |
| /sop/prompt/build | POST | 构建SOP Prompt |
| /sop/docs/{doc_name} | GET | 获取任务操作指引文档 |

**任务执行与状态**
| 路由 | 方法 | 描述 |
|------|------|------|
| /sop/execute | POST | 执行SOP任务 |
| /sop/status/{execution_id} | GET | 获取任务执行状态 |
| /sop/results/{execution_id} | GET | 获取任务执行结果 |
| /sop/executions | GET | 列出执行记录 |
| /sop/executions/{execution_id} | DELETE | 取消/删除执行记录 |

**任务控制（暂停/停止/恢复）**
| 路由 | 方法 | 描述 |
|------|------|------|
| /sop/executions/{execution_id}/pause | POST | 暂停任务 |
| /sop/executions/{execution_id}/stop | POST | 停止任务 |
| /sop/executions/{execution_id}/resume | POST | 恢复任务 |

**任务历史记录**
| 路由 | 方法 | 描述 |
|------|------|------|
| /sop/history | GET | 查询任务历史记录 |
| /sop/history/{record_id} | GET | 获取历史记录详情 |
| /sop/history/{record_id}/result | GET | 获取历史任务完整结果 |
| /sop/history/{record_id} | DELETE | 删除历史记录 |
| /sop/statistics | GET | 获取任务统计信息 |
| /sop/report/export | POST | 导出任务执行报告 |

**专家模式API**
| 路由 | 方法 | 描述 |
|------|------|------|
| /sop/expert/create | POST | 创建专家模式执行上下文 |
| /sop/expert/{execution_id} | GET | 获取专家模式执行上下文 |
| /sop/expert/{execution_id}/stages/{stage_id}/execute | POST | 执行单个阶段 |
| /sop/expert/{execution_id}/stages/{stage_id}/skip | POST | 跳过阶段 |
| /sop/expert/{execution_id}/stages/{stage_id}/reset | POST | 重置阶段 |
| /sop/expert/{execution_id}/stages/{stage_id}/params | PUT | 更新阶段参数 |
| /sop/expert/{execution_id}/stages/{stage_id}/code | PUT | 更新阶段代码 |
| /sop/expert/{execution_id}/stages/{stage_id}/result | GET | 获取阶段结果 |


#### 2.2.3 LLM Manager 子应用 (/llm-manager)
| 路由 | 方法 | 描述 |
|------|------|------|
| /llm-manager | GET | 开发模式重定向到3001，生产模式提供静态页面 |
| /llm-manager/api/config | GET | 获取配置信息 |
| /llm-manager/health | GET | LLM Manager健康检查 |
| /llm-manager/docs | GET | LLM Manager API文档 |

#### 2.2.4 LLM Manager API 详细路由
| 路由 | 方法 | 描述 |
|------|------|------|
| /llm-manager/api/models | GET | OpenAI兼容的模型列表 |
| /llm-manager/api/proxy/chat/completions | POST | OpenAI兼容的聊天接口 |
| /llm-manager/api/proxy/channels/status | GET | 渠道状态查询 |
| /llm-manager/api/proxy/load-balancer/strategy | POST | 负载均衡策略 |
| /llm-manager/api/proxy/load-balancer/metrics | GET | 负载均衡器指标 |
| /llm-manager/api/proxy/channels/{id}/health-check | POST | 渠道健康检查 |
| /llm-manager/api/manage/channels | GET | 获取渠道列表 |
| /llm-manager/api/manage/channels | POST | 创建渠道 |
| /llm-manager/api/manage/channels/{id} | GET | 获取单个渠道 |
| /llm-manager/api/manage/channels/{id} | PUT | 更新渠道 |
| /llm-manager/api/manage/channels/{id} | DELETE | 删除渠道 |
| /llm-manager/api/manage/channels/{id}/test-via-proxy | POST | 通过代理测试渠道连接 |
| /llm-manager/api/manage/channels/{id}/model-config | GET | 获取渠道模型配置（含param_limits/capabilities） |
| /llm-manager/api/manage/channels/{id}/model-config | POST | 创建/更新渠道模型配置 |
| /llm-manager/api/manage/channels/{id}/model-config | DELETE | 删除渠道模型配置 |
| /llm-manager/api/manage/model-capabilities | GET | 获取所有模型能力配置 |
| /llm-manager/api/manage/model-capabilities/{model_name} | GET | 获取指定模型能力配置 |
| /llm-manager/api/manage/param-limits | GET | 获取默认参数范围配置 |
| /llm-manager/api/logs/list | GET | 获取日志列表 |
| /llm-manager/api/logs/stats | GET | 获取日志统计 |
| /llm-manager/api/monitoring/system | GET | 系统监控信息 |

## 3. 特殊路由关系

### 3.1 重定向关系
```
开发模式:
http://127.0.0.1:8200/llm-manager → http://localhost:3001

生产模式:
http://127.0.0.1:8200/llm-manager → 静态HTML页面
```

### 3.2 Vite代理配置
```
Vite服务器(3001)配置代理:
/llm-manager → http://localhost:8200

前端调用:
前端可以直接调用 /llm-manager/api/*，Vite会自动代理到后端
```

## 4. 数据流向图

### 4.1 聊天流程
```
前端(3000/3001) → /v1/chat/completions → 后端API(8200) → LLMClientManager → 外部LLM服务
                                       ↓ (enable_code_execution=true时)
                                       代码执行 → 文件追踪 → 报告生成
                ← 响应（含generated_files）  ← 响应
```

### 4.2 工作区文件操作
```
前端(3000) → /workspace/upload → 后端API(8200) → 文件系统
          ← 响应           ← 响应
```

### 4.3 模型列表
```
前端(3000/3001) → /llm-manager/api/models → LLM Manager(8200) → 数据库
              ← 响应                              ← 响应
```

### 4.4 渠道管理
```
前端(3001) → /llm-manager/api/manage/channels → 后端API(8200) → 数据库
          ← 响应                              ← 响应
```

### 4.5 渠道连接测试
```
前端(3001) → /llm-manager/api/manage/channels/{id}/test-via-proxy → LLM Manager(8200) → /llm-manager/api/models
          ← 响应                                                              ← 响应
```

### 4.6 SOP任务执行流程
```
前端(3000) → /sop/execute → 后端API(8200) → SOPExecutor → Pipeline执行引擎
          ← SSE/轮询状态                   ← 执行结果
          
专家模式:
前端(3000) → /sop/expert/create → 创建执行上下文
          → /sop/expert/{id}/stages/{stage}/execute → 逐阶段执行
          → /sop/expert/{id}/stages/{stage}/params → 修改参数
          ← 阶段结果

LLM智能入口（参数推断）:
用户自然语言描述 → LLMParamExtractor → 参数推断 → Pipeline执行
```

## 5. 部署模式

### 5.1 开发模式
- 前端1: Next.js 开发服务器 (端口 3000)
- 前端2: Vite 开发服务器 (端口 3001)
- 后端: FastAPI 开发服务器 (端口 8200)
- 重定向: 8200/llm-manager → 3001

### 5.2 生产模式
- 前端: 构建后的静态文件由FastAPI提供服务 (端口 8200)
- 后端: FastAPI 生产服务器 (端口 8200)
- 无需重定向

---

**文档版本**: v1.3  
**更新日期**: 2025-12-24  
**更新内容**: 
- v1.3: 新增模型能力配置API（model-capabilities、param-limits），用于前端动态获取参数范围
- v1.2: 更新SOP执行流程，LLM SOP执行模式已废弃，统一使用Pipeline执行引擎，LLM重新定位为智能入口（参数推断器）
- v1.1: 新增 SOP 任务管理 API 路由（/sop/*）
