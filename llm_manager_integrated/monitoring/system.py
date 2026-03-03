"""
统一监控系统 - 支持个人和企业部署模式
提供系统监控、性能指标、健康检查、告警等功能
"""

import asyncio
import json
import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DeploymentMode(str, Enum):
    """部署模式"""
    PERSONAL = "personal"  # 个人模式：轻量级，本地SQLite，基础监控
    ENTERPRISE = "enterprise"  # 企业模式：PostgreSQL，Redis，高级监控


class AlertSeverity(str, Enum):
    """告警严重级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthStatus(str, Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class SystemMetric:
    """系统指标"""
    name: str
    value: float
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """告警信息"""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class MonitorRule:
    """监控规则基类"""
    
    def __init__(self, name: str, check_interval: int = 60):
        self.name = name
        self.check_interval = check_interval
        self.last_check = 0
        self.enabled = True
    
    async def check(self) -> List[Alert]:
        """执行监控检查"""
        if not self.enabled:
            return []
        
        current_time = time.time()
        if current_time - self.last_check < self.check_interval:
            return []
        
        self.last_check = current_time
        return await self._check()
    
    async def _check(self) -> List[Alert]:
        """子类实现具体检查逻辑"""
        raise NotImplementedError


class CPUMonitorRule(MonitorRule):
    """CPU监控规则"""
    
    def __init__(self, warning_threshold: float = 70.0, critical_threshold: float = 90.0, **kwargs):
        super().__init__(name="cpu_monitor", **kwargs)
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    async def _check(self) -> List[Alert]:
        alerts = []
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if cpu_percent >= self.critical_threshold:
                alerts.append(Alert(
                    id=f"cpu-critical-{int(time.time())}",
                    title="CPU使用率过高",
                    description=f"当前CPU使用率: {cpu_percent:.1f}%, 超过临界阈值 {self.critical_threshold}%",
                    severity=AlertSeverity.CRITICAL,
                    tags={"metric": "cpu", "value": str(cpu_percent)}
                ))
            elif cpu_percent >= self.warning_threshold:
                alerts.append(Alert(
                    id=f"cpu-warning-{int(time.time())}",
                    title="CPU使用率较高",
                    description=f"当前CPU使用率: {cpu_percent:.1f}%, 超过警告阈值 {self.warning_threshold}%",
                    severity=AlertSeverity.WARNING,
                    tags={"metric": "cpu", "value": str(cpu_percent)}
                ))
        except Exception as e:
            logger.error(f"CPU监控检查失败: {e}")
        
        return alerts


class MemoryMonitorRule(MonitorRule):
    """内存监控规则"""
    
    def __init__(self, warning_threshold: float = 80.0, critical_threshold: float = 95.0, **kwargs):
        super().__init__(name="memory_monitor", **kwargs)
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    async def _check(self) -> List[Alert]:
        alerts = []
        
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            if memory_percent >= self.critical_threshold:
                alerts.append(Alert(
                    id=f"memory-critical-{int(time.time())}",
                    title="内存使用率过高",
                    description=f"当前内存使用率: {memory_percent:.1f}%, 超过临界阈值 {self.critical_threshold}%",
                    severity=AlertSeverity.CRITICAL,
                    tags={"metric": "memory", "value": str(memory_percent)}
                ))
            elif memory_percent >= self.warning_threshold:
                alerts.append(Alert(
                    id=f"memory-warning-{int(time.time())}",
                    title="内存使用率较高",
                    description=f"当前内存使用率: {memory_percent:.1f}%, 超过警告阈值 {self.warning_threshold}%",
                    severity=AlertSeverity.WARNING,
                    tags={"metric": "memory", "value": str(memory_percent)}
                ))
        except Exception as e:
            logger.error(f"内存监控检查失败: {e}")
        
        return alerts


class DiskMonitorRule(MonitorRule):
    """磁盘监控规则"""
    
    def __init__(self, warning_threshold: float = 85.0, critical_threshold: float = 95.0, **kwargs):
        super().__init__(name="disk_monitor", **kwargs)
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    async def _check(self) -> List[Alert]:
        alerts = []
        
        try:
            disks = psutil.disk_partitions()
            
            for disk in disks:
                try:
                    usage = psutil.disk_usage(disk.mountpoint)
                    usage_percent = (usage.used / usage.total) * 100
                    
                    if usage_percent >= self.critical_threshold:
                        alerts.append(Alert(
                            id=f"disk-critical-{disk.mountpoint.replace('/', '-')}-{int(time.time())}",
                            title=f"磁盘空间不足: {disk.mountpoint}",
                            description=f"磁盘 {disk.mountpoint} 使用率: {usage_percent:.1f}%, 超过临界阈值 {self.critical_threshold}%",
                            severity=AlertSeverity.CRITICAL,
                            tags={
                                "metric": "disk",
                                "mountpoint": disk.mountpoint,
                                "value": str(usage_percent)
                            }
                        ))
                    elif usage_percent >= self.warning_threshold:
                        alerts.append(Alert(
                            id=f"disk-warning-{disk.mountpoint.replace('/', '-')}-{int(time.time())}",
                            title=f"磁盘空间较低: {disk.mountpoint}",
                            description=f"磁盘 {disk.mountpoint} 使用率: {usage_percent:.1f}%, 超过警告阈值 {self.warning_threshold}%",
                            severity=AlertSeverity.WARNING,
                            tags={
                                "metric": "disk",
                                "mountpoint": disk.mountpoint,
                                "value": str(usage_percent)
                            }
                        ))
                except Exception as e:
                    logger.error(f"检查磁盘 {disk.mountpoint} 使用情况失败: {e}")
        except Exception as e:
            logger.error(f"磁盘监控检查失败: {e}")
        
        return alerts


class ServiceHealthRule(MonitorRule):
    """服务健康监控规则"""
    
    def __init__(self, services: List[str], **kwargs):
        super().__init__(name="service_health", **kwargs)
        self.services = services
    
    async def _check(self) -> List[Alert]:
        alerts = []
        
        for service in self.services:
            # 这里简化实现，实际应该检查各服务的健康状态
            # 可以通过调用健康检查API或其他方式
            
            # 示例：检查数据库连接
            if service == "database":
                # 这里应该有实际的数据库健康检查
                # 简化示例：假设数据库健康
                pass
            
            # 示例：检查Redis连接（企业模式）
            if service == "redis":
                # 这里应该有实际的Redis健康检查
                # 简化示例：假设Redis健康
                pass
        
        return alerts


class MonitorSystem:
    """监控系统"""
    
    def __init__(self, deployment_mode: DeploymentMode = DeploymentMode.PERSONAL):
        self.deployment_mode = deployment_mode
        self.rules: List[MonitorRule] = []
        self.alerts: List[Alert] = []
        self.metrics: List[SystemMetric] = []
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._alert_handlers: List[Callable[[Alert], None]] = []
        
        # 初始化监控规则
        self._init_rules()
    
    def _init_rules(self):
        """初始化监控规则"""
        # 基础监控规则（所有模式）
        self.rules.append(CPUMonitorRule())
        self.rules.append(MemoryMonitorRule())
        self.rules.append(DiskMonitorRule())
        
        # 企业模式额外规则
        if self.deployment_mode == DeploymentMode.ENTERPRISE:
            # 企业模式可以添加更多监控规则
            # 如：服务健康、数据库连接池、Redis等
            enterprise_services = ["database", "redis", "api_service"]
            self.rules.append(ServiceHealthRule(enterprise_services))
        
        logger.info(f"初始化监控系统，模式: {self.deployment_mode.value}")
    
    def add_rule(self, rule: MonitorRule):
        """添加监控规则"""
        self.rules.append(rule)
    
    def remove_rule(self, rule_name: str):
        """移除监控规则"""
        self.rules = [rule for rule in self.rules if rule.name != rule_name]
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """添加告警处理器"""
        self._alert_handlers.append(handler)
    
    async def start(self):
        """启动监控系统"""
        if self._running:
            logger.warning("监控系统已在运行")
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("监控系统已启动")
    
    async def stop(self):
        """停止监控系统"""
        if not self._running:
            logger.warning("监控系统未运行")
            return
        
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("监控系统已停止")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                # 检查所有规则
                new_alerts = []
                for rule in self.rules:
                    alerts = await rule.check()
                    new_alerts.extend(alerts)
                
                # 处理新告警
                for alert in new_alerts:
                    self.alerts.append(alert)
                    
                    # 调用告警处理器
                    for handler in self._alert_handlers:
                        try:
                            handler(alert)
                        except Exception as e:
                            logger.error(f"告警处理器执行失败: {e}")
                
                # 收集系统指标
                await self._collect_metrics()
                
                # 清理旧告警（保留最近的100条）
                self.alerts = self.alerts[-100:]
                
                # 清理旧指标（保留最近的1000条）
                self.metrics = self.metrics[-1000:]
                
                # 等待下次检查
                await asyncio.sleep(30)  # 30秒检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                await asyncio.sleep(60)  # 异常后等待1分钟再重试
    
    async def _collect_metrics(self):
        """收集系统指标"""
        try:
            # CPU指标
            cpu_percent = psutil.cpu_percent(interval=None)
            self.metrics.append(SystemMetric(
                name="cpu_usage",
                value=cpu_percent,
                unit="percent",
                tags={"type": "system"}
            ))
            
            # 内存指标
            memory = psutil.virtual_memory()
            self.metrics.append(SystemMetric(
                name="memory_usage",
                value=memory.percent,
                unit="percent",
                tags={"type": "system"}
            ))
            self.metrics.append(SystemMetric(
                name="memory_available",
                value=memory.available / (1024**3),  # GB
                unit="GB",
                tags={"type": "system"}
            ))
            
            # 磁盘指标
            for disk in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(disk.mountpoint)
                    self.metrics.append(SystemMetric(
                        name="disk_usage",
                        value=(usage.used / usage.total) * 100,
                        unit="percent",
                        tags={"type": "system", "mountpoint": disk.mountpoint}
                    ))
                    self.metrics.append(SystemMetric(
                        name="disk_free",
                        value=usage.free / (1024**3),  # GB
                        unit="GB",
                        tags={"type": "system", "mountpoint": disk.mountpoint}
                    ))
                except Exception as e:
                    logger.error(f"收集磁盘 {disk.mountpoint} 指标失败: {e}")
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            # 计算健康状态
            health_status = self._calculate_health_status()
            
            # 获取最近的系统指标
            recent_metrics = self._get_recent_metrics()
            
            # 获取活跃告警
            active_alerts = [alert for alert in self.alerts if not alert.resolved]
            
            return {
                "status": health_status,
                "deployment_mode": self.deployment_mode.value,
                "monitoring_active": self._running,
                "active_rules": [rule.name for rule in self.rules if rule.enabled],
                "active_alerts_count": len(active_alerts),
                "total_alerts_count": len(self.alerts),
                "metrics": recent_metrics,
                "alerts": [
                    {
                        "id": alert.id,
                        "title": alert.title,
                        "description": alert.description,
                        "severity": alert.severity.value,
                        "timestamp": alert.timestamp.isoformat(),
                        "tags": alert.tags,
                        "acknowledged": alert.acknowledged,
                        "acknowledged_by": alert.acknowledged_by,
                        "resolved": alert.resolved,
                        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
                    }
                    for alert in active_alerts[-10:]  # 返回最近的10条活跃告警
                ]
            }
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "error": str(e)
            }
    
    def _calculate_health_status(self) -> HealthStatus:
        """计算系统健康状态"""
        # 获取最近的活跃告警
        active_alerts = [alert for alert in self.alerts if not alert.resolved]
        
        # 检查是否有严重告警
        critical_alerts = [alert for alert in active_alerts if alert.severity == AlertSeverity.CRITICAL]
        if critical_alerts:
            return HealthStatus.UNHEALTHY
        
        # 检查是否有错误告警
        error_alerts = [alert for alert in active_alerts if alert.severity == AlertSeverity.ERROR]
        if error_alerts:
            return HealthStatus.DEGRADED
        
        # 检查是否有多个警告告警
        warning_alerts = [alert for alert in active_alerts if alert.severity == AlertSeverity.WARNING]
        if len(warning_alerts) >= 3:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def _get_recent_metrics(self) -> List[Dict[str, Any]]:
        """获取最近的系统指标"""
        # 按指标名称分组，获取每个指标的最新值
        latest_metrics = {}
        
        for metric in self.metrics:
            key = f"{metric.name}:{json.dumps(metric.tags, sort_keys=True)}"
            if key not in latest_metrics or metric.timestamp > latest_metrics[key]["timestamp"]:
                latest_metrics[key] = {
                    "name": metric.name,
                    "value": metric.value,
                    "unit": metric.unit,
                    "timestamp": metric.timestamp.isoformat(),
                    "tags": metric.tags
                }
        
        # 返回最近30分钟的指标
        return list(latest_metrics.values())


# 全局监控系统实例
_monitor_system: Optional[MonitorSystem] = None


def get_monitor_system(deployment_mode: DeploymentMode = DeploymentMode.PERSONAL) -> MonitorSystem:
    """获取全局监控系统实例"""
    global _monitor_system
    if _monitor_system is None:
        _monitor_system = MonitorSystem(deployment_mode=deployment_mode)
    return _monitor_system


def init_monitor_system(deployment_mode: DeploymentMode = DeploymentMode.PERSONAL) -> MonitorSystem:
    """初始化全局监控系统"""
    global _monitor_system
    _monitor_system = MonitorSystem(deployment_mode=deployment_mode)
    return _monitor_system


# 辅助函数
def get_deployment_mode_from_config() -> DeploymentMode:
    """从配置获取部署模式"""
    try:
        from ..core.config import settings
        
        # 检查是否配置了企业模式
        enterprise_features = getattr(settings, 'enterprise_features', False)
        redis_url = getattr(settings, 'redis_url', None)
        
        if enterprise_features or redis_url:
            return DeploymentMode.ENTERPRISE
        else:
            return DeploymentMode.PERSONAL
    except Exception:
        # 默认使用个人模式
        return DeploymentMode.PERSONAL


# 简单的日志告警处理器
def log_alert_handler(alert: Alert):
    """将告警记录到日志"""
    log_level = {
        AlertSeverity.INFO: logger.info,
        AlertSeverity.WARNING: logger.warning,
        AlertSeverity.ERROR: logger.error,
        AlertSeverity.CRITICAL: logger.critical
    }.get(alert.severity, logger.info)
    
    log_level(
        f"告警 [{alert.severity.value.upper()}] {alert.title}: {alert.description} "
        f"(ID: {alert.id}, 时间: {alert.timestamp.isoformat()})"
    )