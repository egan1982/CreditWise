"""
CRUD 操作模块
提供数据库的增删改查操作
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from ..models import orm, schemas
from ..utils import security


def _decrypt_channel(db_channel):
    """将数据库模型转换为 Pydantic 模型，并解密 API Key"""
    if not db_channel:
        return None
    decrypted_key = security.decrypt_data(db_channel.encrypted_api_key)
    
    return schemas.Channel(
        id=db_channel.id,
        name=db_channel.name,
        type=db_channel.type,
        base_url=db_channel.base_url,
        models=db_channel.models,
        api_key=decrypted_key,
        status=db_channel.status,
        stream_output=db_channel.stream_output  # 包含流式输出配置
    )


# 渠道 CRUD 操作
def get_channel(db: Session, channel_id: int):
    db_channel = db.query(orm.Channel).filter(orm.Channel.id == channel_id).first()
    return _decrypt_channel(db_channel)


def get_channels(db: Session, skip: int = 0, limit: int = 100):
    db_channels = db.query(orm.Channel).offset(skip).limit(limit).all()
    return [_decrypt_channel(ch) for ch in db_channels]


def get_active_channels(db: Session, skip: int = 0, limit: int = 100):
    """获取所有激活的渠道"""
    db_channels = db.query(orm.Channel).filter(orm.Channel.status == True).offset(skip).limit(limit).all()
    return [_decrypt_channel(ch) for ch in db_channels]


def create_channel(db: Session, channel: schemas.ChannelCreate):
    encrypted_key = security.encrypt_data(channel.api_key)
    # 使用请求中的status值，如果未提供则默认为False
    status = channel.status if hasattr(channel, 'status') and channel.status is not None else False
    # 使用请求中的stream_output值，如果未提供则默认为True
    stream_output = channel.stream_output if hasattr(channel, 'stream_output') and channel.stream_output is not None else True
    
    db_channel = orm.Channel(
        name=channel.name,
        type=channel.type,
        base_url=channel.base_url,
        encrypted_api_key=encrypted_key,
        models=channel.models,
        status=status,
        stream_output=stream_output
    )
    db.add(db_channel)
    db.commit()
    db.refresh(db_channel)
    return _decrypt_channel(db_channel)


def update_channel(db: Session, channel_id: int, channel_update: schemas.ChannelUpdate):
    db_channel = db.query(orm.Channel).filter(orm.Channel.id == channel_id).first()
    if not db_channel:
        return None

    update_data = channel_update.dict(exclude_unset=True)
    
    # 如果更新了 api_key，需要加密
    if "api_key" in update_data and update_data["api_key"]:
        encrypted_key = security.encrypt_data(update_data["api_key"])
        db_channel.encrypted_api_key = encrypted_key
        del update_data["api_key"]  # 从更新字典中移除，避免直接赋值

    for key, value in update_data.items():
        setattr(db_channel, key, value)

    db.commit()
    db.refresh(db_channel)
    return _decrypt_channel(db_channel)


def delete_channel(db: Session, channel_id: int):
    db_channel = db.query(orm.Channel).filter(orm.Channel.id == channel_id).first()
    if not db_channel:
        return None
    db.delete(db_channel)
    db.commit()
    return _decrypt_channel(db_channel)


# API日志 CRUD 操作
def create_api_log(db: Session, log: schemas.APILogCreate):
    """创建API调用日志"""
    db_log = orm.APILog(**log.dict())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def get_api_logs(db: Session, skip: int = 0, limit: int = 100, model_name: str = None, status: str = None, exclude_test_data: bool = False):
    """获取API调用日志列表，支持过滤"""
    query = db.query(orm.APILog)
    
    if model_name:
        query = query.filter(orm.APILog.model_name == model_name)
    if status:
        query = query.filter(orm.APILog.status == status)
    if exclude_test_data:
        query = query.filter(orm.APILog.is_test_data == False)
    
    return query.order_by(orm.APILog.timestamp.desc()).offset(skip).limit(limit).all()


def get_api_log_stats(db: Session, exclude_test_data: bool = False):
    """获取API调用统计信息"""
    from sqlalchemy import func
    
    # 基础查询
    base_query = db.query(orm.APILog)
    if exclude_test_data:
        base_query = base_query.filter(orm.APILog.is_test_data == False)
    
    # 总调用次数
    total_calls = base_query.with_entities(func.count(orm.APILog.id)).scalar()
    
    # 成功/失败次数
    success_calls = base_query.filter(orm.APILog.status == 'success').with_entities(func.count(orm.APILog.id)).scalar()
    error_calls = base_query.filter(orm.APILog.status == 'error').with_entities(func.count(orm.APILog.id)).scalar()
    
    # 总token使用量
    total_tokens = base_query.with_entities(func.sum(orm.APILog.total_tokens)).scalar() or 0
    
    # 总成本
    total_cost = base_query.with_entities(func.sum(orm.APILog.estimated_cost)).scalar() or 0.0
    
    # 按模型统计
    model_stats_query = base_query.with_entities(
        orm.APILog.model_name,
        func.count(orm.APILog.id).label('count'),
        func.sum(orm.APILog.total_tokens).label('tokens'),
        func.sum(orm.APILog.estimated_cost).label('cost')
    ).group_by(orm.APILog.model_name)
    
    model_stats = model_stats_query.all()
    
    return {
        'total_calls': total_calls,
        'success_calls': success_calls,
        'error_calls': error_calls,
        'total_tokens': int(total_tokens),
        'total_cost': float(total_cost),
        'model_stats': [
            {
                'model_name': stat[0],
                'count': stat[1],
                'tokens': int(stat[2] or 0),
                'cost': float(stat[3] or 0.0)
            }
            for stat in model_stats
        ]
    }


def delete_api_logs(db: Session, days: int = 30):
    """删除指定天数之前的日志"""
    from datetime import datetime, timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    deleted_count = db.query(orm.APILog).filter(orm.APILog.timestamp < cutoff_date).delete()
    db.commit()
    return deleted_count


def delete_test_data(db: Session):
    """删除所有测试数据"""
    deleted_count = db.query(orm.APILog).filter(orm.APILog.is_test_data == True).delete()
    db.commit()
    return deleted_count


def has_test_data(db: Session) -> bool:
    """检查是否存在测试数据"""
    count = db.query(orm.APILog).filter(orm.APILog.is_test_data == True).count()
    return count > 0


def has_real_data(db: Session) -> bool:
    """检查是否存在真实数据"""
    count = db.query(orm.APILog).filter(orm.APILog.is_test_data == False).count()
    return count > 0


def get_data_summary(db: Session):
    """获取数据概况"""
    from sqlalchemy import func
    test_count = db.query(func.count(orm.APILog.id)).filter(orm.APILog.is_test_data == True).scalar()
    real_count = db.query(func.count(orm.APILog.id)).filter(orm.APILog.is_test_data == False).scalar()
    return {
        'test_data_count': test_count,
        'real_data_count': real_count,
        'total_count': test_count + real_count,
        'has_test_data': test_count > 0,
        'has_real_data': real_count > 0
    }


# 模型配置 CRUD 操作
def get_model_config_by_channel(db: Session, channel_id: int):
    """根据渠道ID获取模型配置"""
    return db.query(orm.ModelConfig).filter(orm.ModelConfig.channel_id == channel_id).first()


def create_model_config(db: Session, config: schemas.ModelConfigCreate):
    """创建模型配置"""
    db_config = orm.ModelConfig(**config.dict())
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config


def update_model_config(db: Session, channel_id: int, config_update: schemas.ModelConfigUpdate):
    """更新模型配置"""
    db_config = db.query(orm.ModelConfig).filter(orm.ModelConfig.channel_id == channel_id).first()
    if not db_config:
        return None
    
    update_data = config_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_config, key, value)
    
    db.commit()
    db.refresh(db_config)
    return db_config


def delete_model_config(db: Session, channel_id: int):
    """删除模型配置"""
    db_config = db.query(orm.ModelConfig).filter(orm.ModelConfig.channel_id == channel_id).first()
    if not db_config:
        return None
    
    db.delete(db_config)
    db.commit()
    return db_config


def get_all_model_configs(db: Session, skip: int = 0, limit: int = 100):
    """获取所有模型配置"""
    return db.query(orm.ModelConfig).offset(skip).limit(limit).all()
