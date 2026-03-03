"""
Configuration module for DeepAnalyze API Server
Contains all configuration constants and environment setup
"""

import os

# Environment setup
os.environ.setdefault("MPLBACKEND", "Agg")

# API Configuration - Using Chat API (migrated from proxy)
API_BASE = os.environ.get("LLM_API_BASE", "http://localhost:8200/v1")
MODEL_PATH = os.environ.get("LLM_MODEL", "deepseek-chat")

# API Key configuration
import os
API_KEY = os.environ.get("OPENAI_API_KEY", os.environ.get("DEEPSEEK_API_KEY"))
WORKSPACE_BASE_DIR = "workspace"
HTTP_SERVER_PORT = 8100
HTTP_SERVER_BASE = f"http://localhost:{HTTP_SERVER_PORT}"

# API Server Configuration
API_HOST = "0.0.0.0"
API_PORT = 8200
API_TITLE = "DeepAnalyze OpenAI-Compatible API"
API_VERSION = "1.0.0"

# Thread cleanup configuration
CLEANUP_TIMEOUT_HOURS = 12
CLEANUP_INTERVAL_MINUTES = 30

# Code execution configuration
CODE_EXECUTION_TIMEOUT = 120

# File handling configuration
FILE_STORAGE_DIR = os.path.join(WORKSPACE_BASE_DIR, "_files")
VALID_FILE_PURPOSES = ["fine-tune", "answers", "file-extract", "assistants"]

# API请求默认值（仅用于请求参数缺省时）
# 注意：实际模型参数应从LLM Manager渠道配置获取，这些只是API层的后备默认值
DEFAULT_TEMPERATURE = 0.4  # API请求默认温度（会被渠道配置覆盖）
DEFAULT_MODEL = "deepseek-chat"  # 默认模型名（旧版兼容）

# Supported tools
SUPPORTED_TOOLS = ["code_interpreter"]