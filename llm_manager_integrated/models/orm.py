from sqlalchemy import Boolean, Column, Integer, String, Text, Float, ForeignKey, DateTime
from datetime import datetime
from .database import Base

class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    type = Column(String, nullable=False) # 例如: 'openai', 'azure', 'claude'
    base_url = Column(String, nullable=False)
    encrypted_api_key = Column(String, nullable=False)
    models = Column(Text, nullable=False) # 逗号分隔的模型列表
    status = Column(Boolean, default=True)
    stream_output = Column(Boolean, default=True)  # 是否启用流式输出，默认启用

class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False, index=True)
    model_name = Column(String, nullable=False, index=True)
    system_prompt = Column(Text, nullable=True)  # 默认系统提示词
    temperature = Column(Float, default=0.3)  # 温度参数 (0-2)，风控场景建议低温度保证一致性
    top_p = Column(Float, default=0.8)  # Top P 参数 (0-1)，适度截断低概率token提升稳定性
    max_tokens = Column(Integer, default=4096)  # 最大输出 token 数，风控报告通常需要较长输出
    frequency_penalty = Column(Float, default=0.0)  # 频率惩罚 (-2-2)
    presence_penalty = Column(Float, default=0.0)  # 存在惩罚 (-2-2)
    description = Column(Text, nullable=True)  # 模型描述（用户编辑）
    # 官方模型信息（自动获取）
    model_info = Column(Text, nullable=True)  # JSON 格式的模型官方信息
    max_tokens_limit = Column(Integer, nullable=True)  # 模型官方支持的最大 token 数
    
    # 联网搜索配置
    enable_web_search = Column(Boolean, default=False)  # 是否启用联网搜索
    
    # 深度思考配置
    enable_deep_thinking = Column(Boolean, default=False)  # 是否启用深度思考
    thinking_budget = Column(Integer, nullable=True)  # 思考预算（token数）
    include_thoughts = Column(Boolean, default=False)  # 是否返回思考摘要

class APILog(Base):
    __tablename__ = "api_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)  # 请求时间
    model_name = Column(String, nullable=False, index=True)  # 使用的模型
    channel_name = Column(String, nullable=True)  # 使用的渠道
    status = Column(String, nullable=False, index=True)  # 状态: success, error
    status_code = Column(Integer, nullable=True)  # HTTP状态码
    
    # Token使用情况
    prompt_tokens = Column(Integer, nullable=True)  # 输入token数
    completion_tokens = Column(Integer, nullable=True)  # 输出token数
    total_tokens = Column(Integer, nullable=True)  # 总token数
    
    # 请求和响应信息
    request_data = Column(Text, nullable=True)  # 请求数据（JSON格式）
    response_data = Column(Text, nullable=True)  # 响应数据（JSON格式）
    error_message = Column(Text, nullable=True)  # 错误信息
    
    # 性能指标
    response_time = Column(Float, nullable=True)  # 响应时间（秒）
    
    # 成本估算（可选）
    estimated_cost = Column(Float, nullable=True)  # 估算成本（美元）
    
    # 数据来源标记
    is_test_data = Column(Boolean, default=False, index=True)  # 是否为测试数据
