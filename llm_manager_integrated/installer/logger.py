"""
简单的日志记录器
"""
import sys
from datetime import datetime
from pathlib import Path


class SimpleLogger:
    """简单的日志记录器"""

    def __init__(self, log_file=None):
        """初始化日志记录器"""
        self.log_file = log_file
        self.logs = []

    def info(self, message):
        """记录信息"""
        self._log('INFO', message)

    def warning(self, message):
        """记录警告"""
        self._log('WARNING', message)

    def error(self, message):
        """记录错误"""
        self._log('ERROR', message)

    def success(self, message):
        """记录成功"""
        self._log('SUCCESS', message)

    def _log(self, level, message):
        """内部日志记录"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f'[{timestamp}] [{level}] {message}'
        self.logs.append(log_message)
        print(log_message)

        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(log_message + '\n')
            except Exception as e:
                print(f'Failed to write log: {e}')

    def save_to_file(self, file_path):
        """保存日志到文件"""
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.logs))
            return True
        except Exception as e:
            self.error(f'Failed to save log: {e}')
            return False
