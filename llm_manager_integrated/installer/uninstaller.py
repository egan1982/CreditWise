"""
简单的卸载程序
"""
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


class SimpleUninstaller:
    """简单的卸载程序"""

    def __init__(self, target_path, logger):
        """初始化卸载程序"""
        self.target_path = Path(target_path)
        self.logger = logger
        self.backup_path = None

    def uninstall(self, remove_package=True, backup=True):
        """执行卸载"""
        try:
            self.logger.info('开始卸载 LLM API Manager...')

            # 创建备份
            if backup:
                if not self._backup_files():
                    self.logger.warning('备份失败，继续卸载')

            # 卸载 pip 包
            if remove_package:
                if not self._uninstall_package():
                    self.logger.warning('卸载 pip 包失败，继续清理文件')

            # 删除文件
            if not self._remove_files():
                self.logger.warning('删除文件失败')
                return False

            self.logger.success('卸载完成！')
            return True

        except Exception as e:
            self.logger.error(f'卸载失败: {e}')
            return False

    def _backup_files(self):
        """备份文件"""
        try:
            self.logger.info('正在备份文件...')

            # 创建备份目录
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = self.target_path.parent / f'llm_api_manager_backup_{timestamp}'
            backup_dir.mkdir(parents=True, exist_ok=True)

            # 备份 llm_api_manager 目录
            llm_dir = self.target_path / 'llm_api_manager'
            if llm_dir.exists():
                shutil.copytree(llm_dir, backup_dir / 'llm_api_manager')

            # 备份配置文件
            config_file = self.target_path / 'llm_manager_config.json'
            if config_file.exists():
                shutil.copy2(config_file, backup_dir / 'llm_manager_config.json')

            self.backup_path = backup_dir
            self.logger.success(f'备份完成: {backup_dir}')
            return True

        except Exception as e:
            self.logger.error(f'备份失败: {e}')
            return False

    def _uninstall_package(self):
        """卸载 pip 包"""
        try:
            self.logger.info('正在卸载 pip 包...')

            result = subprocess.run(
                ['pip', 'uninstall', '-y', 'llm-api-manager'],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                self.logger.success('pip 包卸载成功')
                return True
            else:
                self.logger.warning(f'pip 包卸载失败: {result.stderr}')
                return False

        except Exception as e:
            self.logger.error(f'卸载 pip 包失败: {e}')
            return False

    def _remove_files(self):
        """删除文件"""
        try:
            self.logger.info('正在删除文件...')

            # 删除 llm_api_manager 目录
            llm_dir = self.target_path / 'llm_api_manager'
            if llm_dir.exists():
                shutil.rmtree(llm_dir)
                self.logger.info('已删除 llm_api_manager 目录')

            # 删除配置文件
            config_file = self.target_path / 'llm_manager_config.json'
            if config_file.exists():
                config_file.unlink()
                self.logger.info('已删除配置文件')

            # 删除数据库文件
            db_file = self.target_path / 'llm_manager.db'
            if db_file.exists():
                db_file.unlink()
                self.logger.info('已删除数据库文件')

            self.logger.success('文件删除完成')
            return True

        except Exception as e:
            self.logger.error(f'删除文件失败: {e}')
            return False
