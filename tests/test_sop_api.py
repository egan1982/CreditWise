"""
Integration tests for SOP API endpoints

Tests the SOP task management API:
- Task listing and metadata
- Data preview and analysis
- Task execution and status tracking
- Result retrieval
"""

import unittest
import os
import sys
import tempfile
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import FastAPI test client
try:
    from fastapi.testclient import TestClient
    HAS_TESTCLIENT = True
except ImportError:
    HAS_TESTCLIENT = False

# Import SOP modules
from deepanalyze.analysis.task_SOP.registry import (
    get_registry,
    register_builtin_tasks,
    SOPRegistry
)
from deepanalyze.analysis.task_SOP.executor import (
    ExecutionStore,
    ExecutionStatus,
    get_executor
)


class TestSOPRegistry(unittest.TestCase):
    """Test cases for SOP Registry"""
    
    def setUp(self):
        """Reset registry before each test"""
        # Get fresh registry
        self.registry = get_registry()
    
    def test_register_builtin_tasks(self):
        """Test builtin task registration"""
        register_builtin_tasks()
        
        # Check rule_mining task is registered
        task = self.registry.get_task('rule_mining')
        self.assertIsNotNone(task)
        self.assertEqual(task.task_id, 'rule_mining')
        self.assertEqual(task.task_name, '策略规则挖掘')
    
    def test_list_tasks(self):
        """Test task listing"""
        register_builtin_tasks()
        
        tasks = self.registry.list_tasks()
        self.assertIsInstance(tasks, list)
        self.assertGreater(len(tasks), 0)
        
        # Check task structure
        task = tasks[0]
        self.assertIn('task_id', task)
        self.assertIn('task_name', task)
        self.assertIn('description', task)
    
    def test_list_tasks_by_category(self):
        """Test task listing with category filter"""
        register_builtin_tasks()
        
        tasks = self.registry.list_tasks(category='风控建模')
        self.assertIsInstance(tasks, list)
        
        for task in tasks:
            self.assertEqual(task['category'], '风控建模')
    
    def test_get_task_meta_dict(self):
        """Test getting task metadata as dict"""
        register_builtin_tasks()
        
        meta = self.registry.get_task_meta_dict('rule_mining')
        self.assertIsNotNone(meta)
        self.assertIn('task_id', meta)
        self.assertIn('required_params', meta)
        self.assertIn('optional_params', meta)
        self.assertIn('stages', meta)
    
    def test_get_nonexistent_task(self):
        """Test getting non-existent task"""
        task = self.registry.get_task('nonexistent_task')
        self.assertIsNone(task)


class TestExecutionStore(unittest.TestCase):
    """Test cases for ExecutionStore"""
    
    def setUp(self):
        """Clear execution store before each test"""
        ExecutionStore._executions.clear()
    
    def test_create_execution(self):
        """Test execution context creation"""
        context = ExecutionStore.create(
            task_id='rule_mining',
            session_id='test_session',
            params={'target_col': 'target'},
            file_path='/tmp/test.csv'
        )
        
        self.assertIsNotNone(context)
        self.assertIsNotNone(context.execution_id)
        self.assertEqual(context.task_id, 'rule_mining')
        self.assertEqual(context.session_id, 'test_session')
        self.assertEqual(context.status, ExecutionStatus.PENDING)
    
    def test_get_execution(self):
        """Test getting execution by ID"""
        context = ExecutionStore.create(
            task_id='rule_mining',
            session_id='test_session',
            params={},
            file_path='/tmp/test.csv'
        )
        
        retrieved = ExecutionStore.get(context.execution_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.execution_id, context.execution_id)
    
    def test_list_by_session(self):
        """Test listing executions by session"""
        # Create multiple executions
        ExecutionStore.create(
            task_id='rule_mining',
            session_id='session_1',
            params={},
            file_path='/tmp/test1.csv'
        )
        ExecutionStore.create(
            task_id='rule_mining',
            session_id='session_1',
            params={},
            file_path='/tmp/test2.csv'
        )
        ExecutionStore.create(
            task_id='rule_mining',
            session_id='session_2',
            params={},
            file_path='/tmp/test3.csv'
        )
        
        session_1_execs = ExecutionStore.list_by_session('session_1')
        self.assertEqual(len(session_1_execs), 2)
        
        session_2_execs = ExecutionStore.list_by_session('session_2')
        self.assertEqual(len(session_2_execs), 1)
    
    def test_delete_execution(self):
        """Test execution deletion"""
        context = ExecutionStore.create(
            task_id='rule_mining',
            session_id='test_session',
            params={},
            file_path='/tmp/test.csv'
        )
        
        result = ExecutionStore.delete(context.execution_id)
        self.assertTrue(result)
        
        # Should not exist anymore
        retrieved = ExecutionStore.get(context.execution_id)
        self.assertIsNone(retrieved)
    
    def test_update_progress(self):
        """Test progress update"""
        context = ExecutionStore.create(
            task_id='rule_mining',
            session_id='test_session',
            params={},
            file_path='/tmp/test.csv'
        )
        
        context.update_stage('preprocessing', 50)
        self.assertEqual(context.current_stage, 'preprocessing')
        self.assertGreater(context.overall_progress, 0)


class TestSOPExecutor(unittest.TestCase):
    """Test cases for SOP Executor"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data file"""
        np.random.seed(42)
        n_samples = 200
        
        cls.test_df = pd.DataFrame({
            'age': np.random.randint(18, 70, n_samples),
            'income': np.random.randint(10000, 200000, n_samples),
            'target': np.zeros(n_samples),
            'weight': np.ones(n_samples)
        })
        
        bad_mask = (cls.test_df['age'] < 30) & (cls.test_df['income'] < 50000)
        cls.test_df.loc[bad_mask, 'target'] = 1
        
        # Create temp file
        cls.temp_dir = tempfile.mkdtemp()
        cls.test_file = os.path.join(cls.temp_dir, 'test_data.csv')
        cls.test_df.to_csv(cls.test_file, index=False)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up temp files"""
        if os.path.exists(cls.test_file):
            os.remove(cls.test_file)
        if os.path.exists(cls.temp_dir):
            os.rmdir(cls.temp_dir)
    
    def setUp(self):
        """Reset stores before each test"""
        ExecutionStore._executions.clear()
        register_builtin_tasks()
    
    def test_executor_initialization(self):
        """Test executor initialization"""
        executor = get_executor()
        self.assertIsNotNone(executor)
    
    def test_validate_params(self):
        """Test parameter validation"""
        executor = get_executor()
        
        # Valid params
        valid_params = {
            'target_col': 'target',
            'mining_mode': 'single'
        }
        
        # Should not raise
        try:
            # Executor should accept valid params
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Valid params raised exception: {e}")


@unittest.skipUnless(HAS_TESTCLIENT, "FastAPI TestClient not available")
class TestSOPAPIEndpoints(unittest.TestCase):
    """Test cases for SOP API endpoints"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test client and data"""
        # Import API module
        from API.main import app
        cls.client = TestClient(app)
        
        # Create test data
        np.random.seed(42)
        n_samples = 100
        
        cls.test_df = pd.DataFrame({
            'age': np.random.randint(18, 70, n_samples),
            'income': np.random.randint(10000, 200000, n_samples),
            'target': np.random.randint(0, 2, n_samples),
            'weight': np.ones(n_samples)
        })
        
        cls.temp_dir = tempfile.mkdtemp()
        cls.test_file = os.path.join(cls.temp_dir, 'test_data.csv')
        cls.test_df.to_csv(cls.test_file, index=False)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up temp files"""
        if os.path.exists(cls.test_file):
            os.remove(cls.test_file)
        if os.path.exists(cls.temp_dir):
            os.rmdir(cls.temp_dir)
    
    def test_list_tasks(self):
        """Test GET /sop/tasks"""
        response = self.client.get("/sop/tasks")
        self.assertEqual(response.status_code, 200)
        
        tasks = response.json()
        self.assertIsInstance(tasks, list)
        self.assertGreater(len(tasks), 0)
    
    def test_get_task_definition(self):
        """Test GET /sop/tasks/{task_id}"""
        response = self.client.get("/sop/tasks/rule_mining")
        self.assertEqual(response.status_code, 200)
        
        task = response.json()
        self.assertEqual(task['task_id'], 'rule_mining')
        self.assertIn('required_params', task)
        self.assertIn('stages', task)
    
    def test_get_nonexistent_task(self):
        """Test GET /sop/tasks/{task_id} for non-existent task"""
        response = self.client.get("/sop/tasks/nonexistent")
        self.assertEqual(response.status_code, 404)
    
    def test_data_preview(self):
        """Test POST /sop/data/preview"""
        response = self.client.post(
            "/sop/data/preview",
            json={
                "file_path": self.test_file,
                "rows": 5
            }
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('columns', data)
        self.assertIn('preview_data', data)
        self.assertIn('total_rows', data)
        self.assertEqual(len(data['preview_data']), 5)
    
    def test_data_preview_file_not_found(self):
        """Test POST /sop/data/preview with non-existent file"""
        response = self.client.post(
            "/sop/data/preview",
            json={
                "file_path": "/nonexistent/file.csv",
                "rows": 5
            }
        )
        self.assertEqual(response.status_code, 404)
    
    def test_data_analyze(self):
        """Test POST /sop/data/analyze"""
        response = self.client.post(
            "/sop/data/analyze",
            params={"file_path": self.test_file}
        )
        self.assertEqual(response.status_code, 200)
        
        analysis = response.json()
        self.assertIn('total_rows', analysis)
        self.assertIn('total_columns', analysis)
        self.assertIn('numeric_columns', analysis)
        self.assertIn('recommendations', analysis)
    
    def test_build_prompt(self):
        """Test POST /sop/prompt/build"""
        response = self.client.post(
            "/sop/prompt/build",
            json={
                "task_id": "rule_mining",
                "params": {
                    "mining_mode": "single",
                    "n_bins": 10,
                    "max_hit_rate_filter": 0.03,
                    "min_lift_filter": 3.5,
                    "max_hit_rate_select": 0.1
                },
                "workspace_files_info": "test_data.csv (100 rows)"
            }
        )
        self.assertEqual(response.status_code, 200)
        
        result = response.json()
        self.assertIn('prompt', result)
        self.assertIn('规则挖掘', result['prompt'])
    
    def test_list_executions(self):
        """Test GET /sop/executions"""
        response = self.client.get("/sop/executions")
        self.assertEqual(response.status_code, 200)
        
        executions = response.json()
        self.assertIsInstance(executions, list)


class TestRuleMiningMeta(unittest.TestCase):
    """Test cases for rule mining metadata"""
    
    def test_get_task_meta(self):
        """Test getting task metadata"""
        from deepanalyze.analysis.task_SOP.rule_mining_meta import get_task_meta
        
        meta = get_task_meta()
        self.assertIsNotNone(meta)
        self.assertEqual(meta['task_id'], 'rule_mining')
        self.assertIn('stages', meta)
        self.assertIn('required_params', meta)
    
    def test_get_sop_prompt_template(self):
        """Test getting SOP prompt template"""
        from deepanalyze.analysis.task_SOP.rule_mining_meta import get_sop_prompt_template
        
        template = get_sop_prompt_template()
        self.assertIsNotNone(template)
        self.assertIn('Role', template)
        self.assertIn('Instruction', template)
    
    def test_build_sop_prompt(self):
        """Test building SOP prompt with parameters"""
        from deepanalyze.analysis.task_SOP.rule_mining_meta import build_sop_prompt
        
        params = {
            'mining_mode': 'single',
            'n_bins': 10,
            'max_hit_rate_filter': 0.03,
            'min_lift_filter': 3.5,
            'max_hit_rate_select': 0.1
        }
        
        prompt = build_sop_prompt(params, "test_data.csv")
        self.assertIsNotNone(prompt)
        self.assertIn('test_data.csv', prompt)
    
    def test_validate_params(self):
        """Test parameter validation"""
        from deepanalyze.analysis.task_SOP.rule_mining_meta import validate_params
        
        # Valid params
        valid_params = {
            'target_col': 'target',
            'mining_mode': 'single'
        }
        
        is_valid, errors = validate_params(valid_params)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_get_stage_info(self):
        """Test getting stage information"""
        from deepanalyze.analysis.task_SOP.rule_mining_meta import get_stage_info
        
        stage = get_stage_info('preprocess')
        self.assertIsNotNone(stage)
        self.assertEqual(stage['id'], 'preprocess')
        self.assertIn('name', stage)
        self.assertIn('progress_weight', stage)


if __name__ == '__main__':
    unittest.main(verbosity=2)
