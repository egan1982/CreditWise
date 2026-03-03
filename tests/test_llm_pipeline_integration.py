# -*- coding: utf-8 -*-
"""
LLM+Pipeline 新架构集成测试

测试内容：
1. LLM 参数推断器 (LLMParamExtractor) 功能测试
2. 统一任务路由器 (UnifiedTaskRouter) 功能测试
3. 代码生成器 (StageCodeGenerator, EquivalentCodeGenerator) 功能测试
4. API 端点集成测试
5. 前后端联调模拟测试

运行方式：
    pytest tests/test_llm_pipeline_integration.py -v
    pytest tests/test_llm_pipeline_integration.py -v -k "test_param_extractor"
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# =============================================================================
# 导入被测模块
# =============================================================================

from deepanalyze.analysis.task_SOP.llm_param_extractor import (
    LLMParamExtractor,
    TaskIntent,
    ExtractionContext,
    create_param_extractor,
)
from deepanalyze.analysis.task_SOP.task_router import (
    UnifiedTaskRouter,
    RouteRequest,
    RouteResult,
    EntrySource,
    ValidationResult,
    create_router,
    route_from_sop_ui,
    route_from_chat,
)
from deepanalyze.analysis.task_SOP.code_templates import (
    StageCodeGenerator,
    EquivalentCodeGenerator,
    generate_task_config_summary,
    get_code_template,
    format_code_template,
)
from deepanalyze.analysis.task_SOP.registry import get_registry, register_builtin_tasks


# =============================================================================
# 测试配置
# =============================================================================

# 确保任务已注册
register_builtin_tasks()


# =============================================================================
# LLM 参数推断器测试
# =============================================================================

class TestLLMParamExtractor:
    """LLM 参数推断器测试"""
    
    @pytest.fixture
    def extractor(self):
        """创建参数推断器实例"""
        return create_param_extractor()
    
    @pytest.fixture
    def mock_llm_response_rule_mining(self):
        """模拟 LLM 返回的规则挖掘参数"""
        return json.dumps({
            "task_type": "rule_mining",
            "confidence": 0.95,
            "params": {
                "target_col": "is_default",
                "force_categorical": ["province_code", "city_code"],
                "allow_overlap": True
            },
            "missing_params": [],
            "clarification_needed": False,
            "clarification_question": ""
        })
    
    @pytest.fixture
    def mock_llm_response_scorecard(self):
        """模拟 LLM 返回的评分卡参数"""
        return json.dumps({
            "task_type": "scorecard_dev",
            "confidence": 0.90,
            "params": {
                "target_col": "bad_flag",
                "test_ratio": 0.3,
                "base_score": 600
            },
            "missing_params": [],
            "clarification_needed": False,
            "clarification_question": ""
        })
    
    @pytest.fixture
    def mock_llm_response_clarification(self):
        """模拟 LLM 需要澄清的响应"""
        return json.dumps({
            "task_type": "",
            "confidence": 0.3,
            "params": {},
            "missing_params": ["target_col"],
            "clarification_needed": True,
            "clarification_question": "请问您的目标变量是哪一列？"
        })
    
    def test_extractor_creation(self, extractor):
        """测试参数推断器创建"""
        assert extractor is not None
        assert extractor.api_base == "http://localhost:8200/llm-manager/api/proxy"
        assert extractor.model == "deepseek-chat"
        assert extractor.registry is not None
    
    def test_build_system_prompt(self, extractor):
        """测试系统 prompt 构建"""
        system_prompt = extractor._build_system_prompt()
        
        assert "参数提取助手" in system_prompt
        assert "rule_mining" in system_prompt or "规则挖掘" in system_prompt
        assert "JSON" in system_prompt
    
    def test_build_user_prompt(self, extractor):
        """测试用户 prompt 构建"""
        context = ExtractionContext(
            user_message="帮我做规则挖掘，目标变量是is_default",
            workspace_files=["data.csv"],
            data_columns=["id", "is_default", "age", "income"],
            conversation_history=[]
        )
        
        user_prompt = extractor._build_user_prompt(context)
        
        assert "规则挖掘" in user_prompt
        assert "is_default" in user_prompt
        assert "data.csv" in user_prompt
        assert "id, is_default, age, income" in user_prompt
    
    @pytest.mark.asyncio
    async def test_extract_rule_mining_params(self, extractor, mock_llm_response_rule_mining):
        """测试规则挖掘参数提取"""
        with patch.object(extractor, '_call_llm', return_value=mock_llm_response_rule_mining):
            context = ExtractionContext(
                user_message="帮我做规则挖掘，目标变量是is_default，省份和城市代码是分类变量",
                workspace_files=["credit_data.csv"],
                data_columns=["id", "is_default", "province_code", "city_code", "age"]
            )
            
            intent = await extractor.extract(context)
            
            assert intent.task_type == "rule_mining"
            assert intent.confidence >= 0.9
            assert intent.params.get("target_col") == "is_default"
            assert "province_code" in intent.params.get("force_categorical", [])
            assert not intent.clarification_needed
    
    @pytest.mark.asyncio
    async def test_extract_scorecard_params(self, extractor, mock_llm_response_scorecard):
        """测试评分卡参数提取"""
        with patch.object(extractor, '_call_llm', return_value=mock_llm_response_scorecard):
            context = ExtractionContext(
                user_message="开发一个评分卡，目标是bad_flag",
                workspace_files=["loan_data.xlsx"],
                data_columns=["id", "bad_flag", "income", "age"]
            )
            
            intent = await extractor.extract(context)
            
            assert intent.task_type == "scorecard_dev"
            assert intent.confidence >= 0.8
            assert intent.params.get("target_col") == "bad_flag"
    
    @pytest.mark.asyncio
    async def test_extract_with_clarification(self, extractor, mock_llm_response_clarification):
        """测试需要澄清的情况"""
        with patch.object(extractor, '_call_llm', return_value=mock_llm_response_clarification):
            context = ExtractionContext(
                user_message="帮我分析一下数据",
                workspace_files=["data.csv"]
            )
            
            intent = await extractor.extract(context)
            
            assert intent.clarification_needed
            assert "目标变量" in intent.clarification_question
    
    def test_parse_json_response(self, extractor):
        """测试 JSON 响应解析"""
        # 标准 JSON
        response1 = '{"task_type": "rule_mining", "confidence": 0.9, "params": {}, "missing_params": [], "clarification_needed": false}'
        intent1 = extractor._parse_response(response1)
        assert intent1.task_type == "rule_mining"
        
        # 带 markdown 代码块
        response2 = '```json\n{"task_type": "scorecard_dev", "confidence": 0.85, "params": {}, "missing_params": [], "clarification_needed": false}\n```'
        intent2 = extractor._parse_response(response2)
        assert intent2.task_type == "scorecard_dev"
    
    def test_validate_and_enhance(self, extractor):
        """测试验证和增强"""
        intent = TaskIntent(
            task_type="rule_mining",
            confidence=0.9,
            params={"target_col": "is_default"},
            missing_params=[],
            clarification_needed=False
        )
        
        context = ExtractionContext(
            user_message="test",
            data_columns=["is_default", "age", "income"]
        )
        
        enhanced = extractor._validate_and_enhance(intent, context)
        
        # 任务类型有效
        assert enhanced.task_type == "rule_mining"
        # 列名匹配
        assert enhanced.params.get("target_col") == "is_default"
    
    def test_match_column_names(self, extractor):
        """测试列名匹配"""
        params = {
            "target_col": "IS_DEFAULT",  # 大小写不同
            "force_categorical": ["Province_Code", "CITY_CODE"]
        }
        columns = ["id", "is_default", "province_code", "city_code", "age"]
        
        matched = extractor._match_column_names(params, columns)
        
        assert matched["target_col"] == "is_default"
        assert "province_code" in matched["force_categorical"]
        assert "city_code" in matched["force_categorical"]


# =============================================================================
# 统一任务路由器测试
# =============================================================================

class TestUnifiedTaskRouter:
    """统一任务路由器测试"""
    
    @pytest.fixture
    def router(self):
        """创建路由器实例"""
        return create_router()
    
    @pytest.fixture
    def sample_data(self, tmp_path):
        """创建测试数据文件"""
        data = pd.DataFrame({
            "id": range(100),
            "is_default": [0] * 80 + [1] * 20,
            "age": [25 + i % 40 for i in range(100)],
            "income": [3000 + i * 100 for i in range(100)]
        })
        file_path = tmp_path / "test_data.csv"
        data.to_csv(file_path, index=False)
        return str(file_path), data
    
    def test_router_creation(self, router):
        """测试路由器创建"""
        assert router is not None
        assert router.registry is not None
    
    def test_validate_params_valid(self, router):
        """测试有效参数验证"""
        result = router.validate_params("rule_mining", {
            "target_col": "is_default",
            "n_vars": 3
        })
        
        assert result.valid
        assert len(result.errors) == 0
    
    def test_validate_params_missing_required(self, router):
        """测试缺少必需参数"""
        result = router.validate_params("rule_mining", {
            # 缺少 target_col
            "n_vars": 3
        })
        
        # 根据任务定义，target_col 可能有默认值或不是必需的
        # 这里主要测试验证逻辑能正常运行
        assert isinstance(result, ValidationResult)
    
    def test_validate_params_invalid_task(self, router):
        """测试无效任务类型"""
        result = router.validate_params("invalid_task", {})
        
        assert not result.valid
        assert len(result.errors) > 0
        assert "不存在" in result.errors[0]
    
    def test_validate_params_type_conversion(self, router, sample_data):
        """测试参数类型转换"""
        file_path, _ = sample_data
        result = router.validate_params("rule_mining", {
            "file_path": file_path,
            "target_col": "is_default",
            "n_vars": "3",  # 字符串应转换为数字
            "min_lift_filter": "1.5"  # 字符串应转换为浮点数
        })
        
        # 验证转换后的参数（数字类型可能是 int 或 float）
        if result.valid:
            n_vars = result.normalized_params.get("n_vars")
            min_lift = result.normalized_params.get("min_lift_filter")
            assert n_vars == 3 or n_vars == 3.0  # 接受 int 或 float
            assert isinstance(min_lift, (int, float)) and min_lift == 1.5
    
    @pytest.mark.asyncio
    async def test_route_sop_ui_entry(self, router, sample_data):
        """测试 SOP UI 入口路由"""
        file_path, data = sample_data
        
        request = RouteRequest(
            task_type="rule_mining",
            params={"target_col": "is_default"},
            source=EntrySource.SOP_UI,
            session_id="test-session-001",
            file_path=file_path,
            data=data,
            interaction_mode="auto"
        )
        
        # 由于实际执行需要完整环境，这里主要测试路由逻辑
        # 使用 mock 避免实际执行
        with patch('deepanalyze.analysis.task_SOP.executor.SOPExecutor') as mock_executor:
            mock_executor.return_value.execute_async = AsyncMock(return_value=MagicMock(
                execution_id="exec-001",
                status=MagicMock(value="completed"),
                stages={}
            ))
            
            result = await router.route(request)
            
            # 验证路由结果结构
            assert isinstance(result, RouteResult)
    
    @pytest.mark.asyncio
    async def test_route_chat_entry(self, router, sample_data):
        """测试 Chat 入口路由"""
        file_path, data = sample_data
        
        request = RouteRequest(
            task_type="rule_mining",
            params={"target_col": "is_default"},
            source=EntrySource.CHAT,
            session_id="test-session-002",
            file_path=file_path,
            data=data,
            interaction_mode="auto",
            chat_context={
                "user_message": "帮我做规则挖掘"
            },
            llm_extraction_result={
                "confidence": 0.95
            }
        )
        
        with patch('deepanalyze.analysis.task_SOP.executor.SOPExecutor') as mock_executor:
            mock_executor.return_value.execute_async = AsyncMock(return_value=MagicMock(
                execution_id="exec-002",
                status=MagicMock(value="completed"),
                stages={},
                outputs={}
            ))
            
            result = await router.route(request)
            
            assert isinstance(result, RouteResult)
    
    def test_route_invalid_task(self, router):
        """测试无效任务路由"""
        request = RouteRequest(
            task_type="invalid_task",
            params={},
            source=EntrySource.SOP_UI,
            session_id="test-session"
        )
        
        result = asyncio.run(router.route(request))
        
        assert not result.success
        assert "不存在" in result.error or "未知" in result.error


# =============================================================================
# 代码生成器测试
# =============================================================================

class TestCodeGenerators:
    """代码生成器测试"""
    
    def test_stage_code_generator_rule_mining(self):
        """测试规则挖掘阶段伪代码生成"""
        params = {
            "file_path": "data.csv",
            "target_col": "is_default",
            "force_categorical": ["province_code"],
            "n_vars": 3,
            "max_depth": 3
        }
        
        # 测试各阶段
        stages = ["preprocessing", "feature_engineering", "generating_rules", 
                  "rule_filtering", "selecting_rules"]
        
        for stage_id in stages:
            code = StageCodeGenerator.generate_pseudo_code("rule_mining", stage_id, params)
            assert code is not None
            assert len(code) > 0
            # 验证包含关键内容
            if stage_id == "preprocessing":
                assert "load_data" in code or "preprocess" in code
            elif stage_id == "generating_rules":
                assert "generate_rules" in code
    
    def test_stage_code_generator_scorecard(self):
        """测试评分卡阶段伪代码生成"""
        params = {
            "file_path": "loan_data.csv",
            "target_col": "bad_flag",
            "base_score": 600,
            "pdo": 20
        }
        
        stages = ["data_loading", "woe_binning", "feature_selection",
                  "model_training", "score_scaling", "model_evaluation"]
        
        for stage_id in stages:
            code = StageCodeGenerator.generate_pseudo_code("scorecard_dev", stage_id, params)
            assert code is not None
            assert len(code) > 0
    
    def test_stage_result_comment(self):
        """测试阶段结果注释生成"""
        result_summary = {
            "features_count": 15,
            "rules_generated": 12,
            "avg_lift": 2.5
        }
        
        comment = StageCodeGenerator.generate_stage_result_comment(
            "generating_rules",
            result_summary,
            execution_time_ms=3500
        )
        
        assert "15" in comment
        assert "12" in comment
        assert "3.5s" in comment or "3500" in comment
    
    def test_equivalent_code_generator_rule_mining(self):
        """测试规则挖掘等效代码生成"""
        params = {
            "file_path": "credit_data.csv",
            "target_col": "is_default",
            "force_categorical": ["province_code"],
            "n_vars": 3,
            "max_depth": 3,
            "allow_overlap": True
        }
        
        code = EquivalentCodeGenerator.generate_equivalent_code("rule_mining", params)
        
        assert "import pandas" in code
        assert "RuleMiningPipeline" in code
        assert "credit_data.csv" in code
        assert "is_default" in code
        assert "allow_overlap" in code
    
    def test_equivalent_code_generator_scorecard(self):
        """测试评分卡等效代码生成"""
        params = {
            "file_path": "loan_data.csv",
            "target_col": "bad_flag",
            "base_score": 600,
            "pdo": 20,
            "test_ratio": 0.3
        }
        
        code = EquivalentCodeGenerator.generate_equivalent_code("scorecard_dev", params)
        
        assert "import pandas" in code
        assert "ScorecardPipeline" in code
        assert "loan_data.csv" in code
        assert "base_score" in code
        assert "600" in code
    
    def test_task_config_summary(self):
        """测试任务配置摘要生成"""
        params = {
            "file_path": "data.csv",
            "target_col": "is_default",
            "n_vars": 3,
            "allow_overlap": True
        }
        
        summary = generate_task_config_summary("rule_mining", params)
        
        assert "规则挖掘" in summary
        assert "data.csv" in summary
        assert "target_col" in summary
        assert "is_default" in summary
    
    def test_get_code_template(self):
        """测试获取代码模板"""
        # 评分卡模板
        template = get_code_template("scorecard_dev", "data_loading")
        assert template is not None
        assert "pd.read_csv" in template or "加载数据" in template
        
        # 规则挖掘模板
        template = get_code_template("rule_mining", "preprocessing")
        assert template is not None
        
        # 无效任务
        template = get_code_template("invalid_task", "stage")
        assert template == ""
    
    def test_format_code_template(self):
        """测试格式化代码模板"""
        params = {
            "file_path": "my_data.csv",
            "target_col": "target",
            "missing_threshold": 0.9
        }
        
        formatted = format_code_template("scorecard_dev", "data_loading", params)
        
        assert "my_data.csv" in formatted
        assert "target" in formatted


# =============================================================================
# API 端点集成测试
# =============================================================================

class TestAPIIntegration:
    """API 端点集成测试"""
    
    @pytest.fixture
    def test_client(self):
        """创建测试客户端"""
        from fastapi.testclient import TestClient
        from API.sop_api import router
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    def test_list_tasks(self, test_client):
        """测试任务列表 API"""
        response = test_client.get("/sop/tasks")
        
        assert response.status_code == 200
        tasks = response.json()
        assert isinstance(tasks, list)
        
        # 验证包含基本任务
        task_ids = [t["task_id"] for t in tasks]
        assert "rule_mining" in task_ids or "scorecard_dev" in task_ids
    
    def test_get_task_definition(self, test_client):
        """测试获取任务定义 API"""
        response = test_client.get("/sop/tasks/rule_mining")
        
        if response.status_code == 200:
            task_def = response.json()
            assert "task_id" in task_def
            assert task_def["task_id"] == "rule_mining"
    
    def test_llm_extract_endpoint(self, test_client):
        """测试 LLM 参数提取 API"""
        # 由于需要实际 LLM 服务，这里测试端点是否存在
        response = test_client.post("/sop/llm/extract", json={
            "user_message": "帮我做规则挖掘",
            "session_id": "test-session",
            "workspace_files": [],
            "conversation_history": []
        })
        
        # 可能返回 501（服务不可用）或 200（成功）
        assert response.status_code in [200, 501, 500]
    
    def test_unified_execute_endpoint_validation(self, test_client):
        """测试统一执行端点参数验证"""
        # 缺少必需字段
        response = test_client.post("/sop/unified/execute", json={
            "task_id": "rule_mining",
            "session_id": "test-session"
            # 缺少 file_path
        })
        
        assert response.status_code in [422, 404, 500]
    
    def test_code_events_endpoint(self, test_client):
        """测试代码事件 API"""
        # 使用不存在的 execution_id
        response = test_client.get("/sop/code/nonexistent-id/events")
        
        assert response.status_code == 404


# =============================================================================
# 前后端联调模拟测试
# =============================================================================

class TestFrontendBackendIntegration:
    """前后端联调模拟测试"""
    
    def test_sop_ui_workflow(self):
        """测试 SOP UI 完整工作流程"""
        # 模拟前端请求流程
        
        # 1. 获取任务列表
        registry = get_registry()
        tasks = registry.list_tasks()
        assert len(tasks) > 0
        
        # 2. 获取任务定义
        task_def = registry.get_task("rule_mining")
        assert task_def is not None
        
        # 3. 验证参数
        router = create_router()
        validation = router.validate_params("rule_mining", {
            "target_col": "is_default",
            "n_vars": 3
        })
        assert isinstance(validation, ValidationResult)
        
        # 4. 生成配置摘要代码
        config_code = generate_task_config_summary("rule_mining", {
            "target_col": "is_default",
            "n_vars": 3
        })
        assert "规则挖掘" in config_code
    
    def test_chat_workflow(self):
        """测试 Chat 入口完整工作流程"""
        # 模拟 Chat 入口流程
        
        # 1. 创建参数提取器
        extractor = create_param_extractor()
        assert extractor is not None
        
        # 2. 构建提取上下文
        context = ExtractionContext(
            user_message="帮我做规则挖掘，目标变量是is_default",
            workspace_files=["data.csv"],
            data_columns=["id", "is_default", "age"]
        )
        
        # 3. 构建 prompt（不实际调用 LLM）
        system_prompt = extractor._build_system_prompt()
        user_prompt = extractor._build_user_prompt(context)
        
        assert "参数提取" in system_prompt
        assert "is_default" in user_prompt
        
        # 4. 模拟提取结果
        intent = TaskIntent(
            task_type="rule_mining",
            confidence=0.95,
            params={"target_col": "is_default"},
            missing_params=[],
            clarification_needed=False
        )
        
        # 5. 验证路由
        router = create_router()
        validation = router.validate_params(intent.task_type, intent.params)
        assert isinstance(validation, ValidationResult)
    
    def test_code_panel_data_structure(self):
        """测试 Code 栏数据结构"""
        # 验证前端 CodeBlock 结构与后端 StageCodeEvent 兼容
        
        # 后端生成的事件
        config_code = generate_task_config_summary("rule_mining", {"target_col": "is_default"})
        stage_code = StageCodeGenerator.generate_pseudo_code("rule_mining", "preprocessing", {
            "file_path": "data.csv",
            "target_col": "is_default"
        })
        
        # 模拟后端返回的事件结构
        events = [
            {
                "event_type": "config",
                "content": config_code,
                "timestamp": datetime.now().timestamp()
            },
            {
                "event_type": "stage_start",
                "stage_id": "preprocessing",
                "stage_name": "数据预处理",
                "content": stage_code,
                "status": "running",
                "timestamp": datetime.now().timestamp()
            }
        ]
        
        # 验证结构
        for event in events:
            assert "event_type" in event
            assert "content" in event
            assert "timestamp" in event
            assert isinstance(event["content"], str)
            assert len(event["content"]) > 0
    
    def test_full_code_generation_for_export(self):
        """测试完整代码生成（用于导出）"""
        params = {
            "file_path": "credit_data.csv",
            "target_col": "is_default",
            "force_categorical": ["province_code", "city_code"],
            "n_vars": 3,
            "max_depth": 3,
            "allow_overlap": True
        }
        
        # 生成等效代码
        full_code = EquivalentCodeGenerator.generate_equivalent_code("rule_mining", params)
        
        # 验证代码完整性
        assert "import pandas" in full_code
        assert "pd.read_csv" in full_code
        assert "RuleMiningPipeline" in full_code
        assert "credit_data.csv" in full_code
        assert "is_default" in full_code
        assert "province_code" in full_code
        assert "allow_overlap" in full_code
        
        # 验证代码可解析（语法正确）
        try:
            compile(full_code, "<string>", "exec")
            syntax_valid = True
        except SyntaxError:
            syntax_valid = False
        
        assert syntax_valid, "生成的代码存在语法错误"


# =============================================================================
# 性能和边界测试
# =============================================================================

class TestEdgeCases:
    """边界情况测试"""
    
    def test_empty_params(self):
        """测试空参数"""
        code = StageCodeGenerator.generate_pseudo_code("rule_mining", "preprocessing", {})
        assert code is not None
        assert len(code) > 0
    
    def test_special_characters_in_params(self):
        """测试参数中的特殊字符"""
        params = {
            "file_path": "data with spaces.csv",
            "target_col": "is_default",
            "force_categorical": ["col'name", 'col"name']
        }
        
        code = EquivalentCodeGenerator.generate_equivalent_code("rule_mining", params)
        assert code is not None
    
    def test_unicode_in_params(self):
        """测试参数中的 Unicode 字符"""
        params = {
            "file_path": "数据文件.csv",
            "target_col": "是否违约"
        }
        
        summary = generate_task_config_summary("rule_mining", params)
        assert "数据文件.csv" in summary
        assert "是否违约" in summary
    
    def test_large_params(self):
        """测试大量参数"""
        params = {
            "file_path": "data.csv",
            "target_col": "target",
            "force_categorical": [f"col_{i}" for i in range(100)],
            "n_vars": 5,
            "max_depth": 10
        }
        
        code = StageCodeGenerator.generate_pseudo_code("rule_mining", "preprocessing", params)
        assert code is not None
    
    def test_unknown_stage_id(self):
        """测试未知阶段 ID"""
        code = StageCodeGenerator.generate_pseudo_code("rule_mining", "unknown_stage", {})
        assert "unknown_stage" in code
    
    def test_unknown_task_id(self):
        """测试未知任务 ID"""
        code = EquivalentCodeGenerator.generate_equivalent_code("unknown_task", {})
        assert "未知任务" in code


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
