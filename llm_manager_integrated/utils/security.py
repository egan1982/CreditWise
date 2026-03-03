"""数据加密解密工具

使用 Fernet 对称加密算法保护敏感数据（如 API 密钥）。
"""

import os
from typing import Optional
from cryptography.fernet import Fernet


class SecurityManager:
    """安全管理器
    
    负责数据的加密和解密操作。
    
    Attributes:
        encryption_key: Fernet 加密密钥
        
    Example:
        >>> manager = SecurityManager(encryption_key="your-key-here")
        >>> encrypted = manager.encrypt("sensitive-data")
        >>> decrypted = manager.decrypt(encrypted)
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """初始化安全管理器
        
        Args:
            encryption_key: Fernet 加密密钥。如果为 None，则从配置中获取。
            
        Raises:
            ValueError: 如果未提供加密密钥
        """
        if not encryption_key:
            # 首先尝试从环境变量获取
            encryption_key = os.getenv('LLM_MANAGER_ENCRYPTION_KEY')
            
        if not encryption_key:
            # 然后尝试从配置获取
            from ..core.config import settings
            encryption_key = settings.encryption_key
            
        if not encryption_key:
            raise ValueError(
                "未提供加密密钥。请通过以下方式之一设置：\n"
                "1. 传递 encryption_key 参数\n"
                "2. 设置环境变量 LLM_MANAGER_ENCRYPTION_KEY\n"
                "3. 在 .env 文件中设置 ENCRYPTION_KEY\n"
                "\n生成密钥的方法：\n"
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        
        self.fernet = Fernet(encryption_key.encode())
    
    def encrypt(self, data: str) -> str:
        """加密数据
        
        Args:
            data: 要加密的明文字符串
            
        Returns:
            加密后的字符串
        """
        if not data:
            return ""
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """解密数据
        
        Args:
            encrypted_data: 要解密的密文字符串
            
        Returns:
            解密后的明文字符串
        """
        if not encrypted_data:
            return ""
        return self.fernet.decrypt(encrypted_data.encode()).decode()


# 全局安全管理器实例（延迟初始化）
_security_manager: Optional[SecurityManager] = None


def get_security_manager(encryption_key: Optional[str] = None) -> SecurityManager:
    """获取全局安全管理器实例
    
    Args:
        encryption_key: 可选的加密密钥。如果提供，将创建新实例。
        
    Returns:
        安全管理器实例
    """
    global _security_manager
    
    if encryption_key:
        return SecurityManager(encryption_key)
    
    if _security_manager is None:
        _security_manager = SecurityManager()
    
    return _security_manager


# 便捷函数（向后兼容）
def encrypt_data(data: str, encryption_key: Optional[str] = None) -> str:
    """加密数据（便捷函数）
    
    Args:
        data: 要加密的数据
        encryption_key: 可选的加密密钥
        
    Returns:
        加密后的数据
    """
    manager = get_security_manager(encryption_key)
    return manager.encrypt(data)


def decrypt_data(encrypted_data: str, encryption_key: Optional[str] = None) -> str:
    """解密数据（便捷函数）
    
    Args:
        encrypted_data: 要解密的数据
        encryption_key: 可选的加密密钥
        
    Returns:
        解密后的数据
    """
    manager = get_security_manager(encryption_key)
    return manager.decrypt(encrypted_data)


def generate_encryption_key() -> str:
    """生成新的加密密钥
    
    Returns:
        Fernet 格式的加密密钥
        
    Example:
        >>> key = generate_encryption_key()
        >>> print(f"ENCRYPTION_KEY={key}")
    """
    return Fernet.generate_key().decode()
