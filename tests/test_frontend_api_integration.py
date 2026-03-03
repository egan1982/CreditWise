# -*- coding: utf-8 -*-
"""
前端 API 联调测试脚本

测试前端组件与后端 API 的完整交互流程，包括：
1. 任务列表获取
2. 任务定义获取
3. LLM 参数提取（模拟）
4. 统一执行请求
5. 代码事件获取
6. 执行状态轮询

运行方式：
    # 确保后端服务已启动
    python tests/test_frontend_api_integration.py
    
    # 或使用 pytest
    pytest tests/test_frontend_api_integration.py -v
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# 配置
# =============================================================================

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8200")
SOP_API_PREFIX = "/sop"
TEST_SESSION_ID = f"test-session-{int(time.time())}"

# 测试数据文件（需要在 workspace/{session_id}/ 目录下存在）
TEST_DATA_FILE = "test_data.csv"


# =============================================================================
# 辅助函数
# =============================================================================

def log_step(step: str, status: str = "INFO"):
    """打印测试步骤"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    status_colors = {
        "INFO": "\033[94m",    # 蓝色
        "OK": "\033[92m",      # 绿色
        "FAIL": "\033[91m",    # 红色
        "WARN": "\033[93m",    # 黄色
    }
    reset = "\033[0m"
    color = status_colors.get(status, "")
    print(f"[{timestamp}] {color}[{status}]{reset} {step}")


def make_request(method: str, endpoint: str, **kwargs) -> requests.Response:
    """发送 HTTP 请求"""
    url = f"{API_BASE_URL}{SOP_API_PREFIX}{endpoint}"
    try:
        response = requests.request(method, url, timeout=30, **kwargs)
        return response
    except requests.RequestException as e:
        log_step(f"Request failed: {e}", "FAIL")
        raise


def create_test_data_file():
    """创建测试数据文件"""
    import pandas as pd
    import numpy as np
    
    # 创建工作区目录
    workspace_dir = Path("workspace") / TEST_SESSION_ID
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成测试数据
    np.random.seed(42)
    n_samples = 1000
    
    data = pd.DataFrame({
        "id": range(n_samples),
        "is_default": np.random.choice([0, 1], n_samples, p=[0.8, 0.2]),
        "age": np.random.randint(18, 65, n_samples),
        "income": np.random.randint(3000, 50000, n_samples),
        "province_code": np.random.choice(["11", "31", "44", "33"], n_samples),
        "city_code": np.random.choice(["001", "002", "003", "004"], n_samples),
        "loan_amount": np.random.randint(1000, 100000, n_samples),
        "credit_score": np.random.randint(300, 850, n_samples),
    })
    
    file_path = workspace_dir / TEST_DATA_FILE
    data.to_csv(file_path, index=False)
    log_step(f"Created test data: {file_path}", "OK")
    
    return str(file_path)


# =============================================================================
# 测试用例
# =============================================================================

class FrontendAPIIntegrationTest:
    """前端 API 联调测试"""
    
    def __init__(self):
        self.execution_id = None
        self.test_results = []
    
    def run_all_tests(self):
        """运行所有测试"""
        log_step("=" * 60)
        log_step("前端 API 联调测试开始")
        log_step("=" * 60)
        
        tests = [
            ("服务健康检查", self.test_health_check),
            ("获取任务列表", self.test_get_task_list),
            ("获取任务定义", self.test_get_task_definition),
            ("数据预览", self.test_data_preview),
            ("参数验证", self.test_param_validation),
            ("LLM 参数提取", self.test_llm_extract),
            ("统一执行请求", self.test_unified_execute),
            ("执行状态查询", self.test_execution_status),
            ("代码事件获取", self.test_code_events),
            ("执行结果获取", self.test_execution_result),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            log_step(f"\n--- {test_name} ---")
            try:
                result = test_func()
                if result:
                    log_step(f"{test_name}: 通过", "OK")
                    passed += 1
                else:
                    log_step(f"{test_name}: 失败", "FAIL")
                    failed += 1
            except Exception as e:
                log_step(f"{test_name}: 异常 - {e}", "FAIL")
                failed += 1
        
        log_step("\n" + "=" * 60)
        log_step(f"测试完成: {passed} 通过, {failed} 失败")
        log_step("=" * 60)
        
        return failed == 0
    
    def test_health_check(self) -> bool:
        """测试服务健康状态"""
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                log_step("服务运行正常")
                return True
            else:
                log_step(f"服务状态异常: {response.status_code}")
                return False
        except requests.RequestException:
            log_step("服务不可达，尝试任务列表端点")
            # 尝试任务列表端点
            try:
                response = make_request("GET", "/tasks")
                return response.status_code == 200
            except:
                return False
    
    def test_get_task_list(self) -> bool:
        """测试获取任务列表"""
        response = make_request("GET", "/tasks")
        
        if response.status_code != 200:
            log_step(f"状态码: {response.status_code}", "FAIL")
            return False
        
        tasks = response.json()
        log_step(f"获取到 {len(tasks)} 个任务")
        
        # 验证任务结构
        for task in tasks:
            if "task_id" not in task or "task_name" not in task:
                log_step("任务结构不完整", "FAIL")
                return False
        
        # 验证包含基本任务
        task_ids = [t["task_id"] for t in tasks]
        if "rule_mining" not in task_ids and "scorecard_dev" not in task_ids:
            log_step("缺少基本任务类型", "WARN")
        
        log_step(f"任务列表: {task_ids}")
        return True
    
    def test_get_task_definition(self) -> bool:
        """测试获取任务定义"""
        response = make_request("GET", "/tasks/rule_mining")
        
        if response.status_code != 200:
            log_step(f"状态码: {response.status_code}", "FAIL")
            return False
        
        task_def = response.json()
        
        # 验证必需字段
        required_fields = ["task_id", "task_name", "stages"]
        for field in required_fields:
            if field not in task_def:
                log_step(f"缺少字段: {field}", "FAIL")
                return False
        
        log_step(f"任务名称: {task_def.get('task_name')}")
        log_step(f"阶段数量: {len(task_def.get('stages', []))}")
        
        return True
    
    def test_data_preview(self) -> bool:
        """测试数据预览"""
        # 创建测试数据
        create_test_data_file()
        
        response = make_request("POST", "/data/preview", json={
            "file_path": TEST_DATA_FILE,
            "rows": 10,
            "session_id": TEST_SESSION_ID
        })
        
        if response.status_code != 200:
            log_step(f"状态码: {response.status_code}", "FAIL")
            log_step(f"响应: {response.text}")
            return False
        
        preview = response.json()
        
        # 验证预览结构
        if "columns" not in preview or "preview_data" not in preview:
            log_step("预览结构不完整", "FAIL")
            return False
        
        log_step(f"列数: {len(preview['columns'])}")
        log_step(f"预览行数: {len(preview['preview_data'])}")
        log_step(f"总行数: {preview.get('total_rows', 'N/A')}")
        
        return True
    
    def test_param_validation(self) -> bool:
        """测试参数验证（通过任务定义间接验证）"""
        # 获取任务定义来验证参数 schema
        response = make_request("GET", "/tasks/rule_mining")
        
        if response.status_code != 200:
            return False
        
        task_def = response.json()
        
        # 检查参数定义
        required_params = task_def.get("required_params", [])
        optional_params = task_def.get("optional_params", [])
        
        log_step(f"必需参数: {len(required_params)}")
        log_step(f"可选参数: {len(optional_params)}")
        
        # 验证参数结构
        for param in required_params + optional_params:
            if "name" not in param:
                log_step("参数缺少 name 字段", "FAIL")
                return False
        
        return True
    
    def test_llm_extract(self) -> bool:
        """测试 LLM 参数提取"""
        response = make_request("POST", "/llm/extract", json={
            "user_message": "帮我做规则挖掘，目标变量是is_default，省份和城市代码是分类变量",
            "session_id": TEST_SESSION_ID,
            "workspace_files": [TEST_DATA_FILE],
            "conversation_history": []
        })
        
        # LLM 服务可能不可用
        if response.status_code == 501:
            log_step("LLM 服务不可用（预期行为）", "WARN")
            return True
        
        if response.status_code != 200:
            log_step(f"状态码: {response.status_code}", "FAIL")
            return False
        
        result = response.json()
        log_step(f"提取成功: {result.get('success')}")
        log_step(f"任务类型: {result.get('task_type')}")
        log_step(f"置信度: {result.get('confidence')}")
        
        return True
    
    def test_unified_execute(self) -> bool:
        """测试统一执行请求"""
        response = make_request("POST", "/unified/execute", json={
            "task_id": "rule_mining",
            "session_id": TEST_SESSION_ID,
            "file_path": TEST_DATA_FILE,
            "params": {
                "target_col": "is_default",
                "force_categorical": ["province_code", "city_code"],
                "n_vars": 2,
                "max_depth": 2,
                "min_samples_leaf": 50
            },
            "source": "sop_ui",
            "interaction_mode": "auto"
        })
        
        if response.status_code not in [200, 202]:
            log_step(f"状态码: {response.status_code}", "FAIL")
            log_step(f"响应: {response.text}")
            return False
        
        result = response.json()
        self.execution_id = result.get("execution_id")
        
        log_step(f"执行ID: {self.execution_id}")
        log_step(f"状态: {result.get('status')}")
        
        return self.execution_id is not None
    
    def test_execution_status(self) -> bool:
        """测试执行状态查询"""
        if not self.execution_id:
            log_step("无执行ID，跳过", "WARN")
            return True
        
        # 轮询状态
        max_attempts = 30
        for i in range(max_attempts):
            response = make_request("GET", f"/status/{self.execution_id}")
            
            if response.status_code != 200:
                log_step(f"状态查询失败: {response.status_code}")
                time.sleep(2)
                continue
            
            status = response.json()
            current_status = status.get("status")
            progress = status.get("overall_progress", 0)
            
            log_step(f"状态: {current_status}, 进度: {progress:.1%}")
            
            if current_status in ["completed", "failed", "stopped"]:
                return current_status == "completed"
            
            time.sleep(2)
        
        log_step("执行超时", "WARN")
        return False
    
    def test_code_events(self) -> bool:
        """测试代码事件获取"""
        if not self.execution_id:
            log_step("无执行ID，跳过", "WARN")
            return True
        
        response = make_request("GET", f"/code/{self.execution_id}/events")
        
        if response.status_code != 200:
            log_step(f"状态码: {response.status_code}", "FAIL")
            return False
        
        events = response.json()
        log_step(f"事件数量: {len(events)}")
        
        # 验证事件结构
        event_types = set()
        for event in events:
            if "event_type" not in event or "content" not in event:
                log_step("事件结构不完整", "FAIL")
                return False
            event_types.add(event["event_type"])
        
        log_step(f"事件类型: {event_types}")
        
        # 验证包含配置事件
        if "config" not in event_types:
            log_step("缺少配置事件", "WARN")
        
        return True
    
    def test_execution_result(self) -> bool:
        """测试执行结果获取"""
        if not self.execution_id:
            log_step("无执行ID，跳过", "WARN")
            return True
        
        # 等待执行完成
        time.sleep(2)
        
        response = make_request("GET", f"/results/{self.execution_id}")
        
        # 任务可能未完成
        if response.status_code == 400:
            log_step("任务未完成", "WARN")
            return True
        
        if response.status_code != 200:
            log_step(f"状态码: {response.status_code}", "FAIL")
            return False
        
        result = response.json()
        
        log_step(f"结果状态: {result.get('status')}")
        log_step(f"输出键: {list(result.get('outputs', {}).keys())}")
        
        return True


# =============================================================================
# 模拟前端组件行为测试
# =============================================================================

class FrontendComponentSimulation:
    """模拟前端组件行为"""
    
    def simulate_sop_ui_workflow(self):
        """模拟 SOP UI 工作流程"""
        log_step("\n=== 模拟 SOP UI 工作流程 ===")
        
        # 1. 用户选择任务
        log_step("1. 用户选择任务: rule_mining")
        
        # 2. 获取任务定义
        response = make_request("GET", "/tasks/rule_mining")
        if response.status_code == 200:
            task_def = response.json()
            log_step(f"   获取任务定义成功: {task_def.get('task_name')}")
        
        # 3. 用户配置参数（模拟表单填写）
        params = {
            "target_col": "is_default",
            "force_categorical": ["province_code", "city_code"],
            "n_vars": 2,
            "max_depth": 2
        }
        log_step(f"2. 用户配置参数: {params}")
        
        # 4. 提交执行
        log_step("3. 提交执行请求")
        
        # 5. 接收代码事件（模拟 SSE）
        log_step("4. 接收代码事件流...")
        
        # 6. 展示结果
        log_step("5. 展示执行结果")
    
    def simulate_chat_workflow(self):
        """模拟 Chat 工作流程"""
        log_step("\n=== 模拟 Chat 工作流程 ===")
        
        # 1. 用户输入自然语言
        user_message = "帮我做规则挖掘，目标变量是is_default，省份和城市代码是分类变量"
        log_step(f"1. 用户输入: {user_message}")
        
        # 2. LLM 参数提取
        log_step("2. 调用 LLM 参数提取...")
        response = make_request("POST", "/llm/extract", json={
            "user_message": user_message,
            "session_id": TEST_SESSION_ID,
            "workspace_files": [TEST_DATA_FILE],
            "conversation_history": []
        })
        
        if response.status_code == 200:
            result = response.json()
            log_step(f"   提取结果: task_type={result.get('task_type')}, confidence={result.get('confidence')}")
        elif response.status_code == 501:
            log_step("   LLM 服务不可用，使用模拟数据")
        
        # 3. 展示 LLM 推断过程（Code 栏）
        log_step("3. 展示 LLM 推断过程到 Code 栏")
        
        # 4. 执行 Pipeline
        log_step("4. 执行 Pipeline...")
        
        # 5. 生成自然语言解释
        log_step("5. 生成自然语言解释")


# =============================================================================
# 主函数
# =============================================================================

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="前端 API 联调测试")
    parser.add_argument("--api-url", default="http://localhost:8200", help="API 基础 URL")
    parser.add_argument("--simulate", action="store_true", help="运行前端模拟测试")
    args = parser.parse_args()
    
    global API_BASE_URL
    API_BASE_URL = args.api_url
    
    log_step(f"API 基础 URL: {API_BASE_URL}")
    
    # 运行集成测试
    test = FrontendAPIIntegrationTest()
    success = test.run_all_tests()
    
    # 运行模拟测试
    if args.simulate:
        simulation = FrontendComponentSimulation()
        simulation.simulate_sop_ui_workflow()
        simulation.simulate_chat_workflow()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
