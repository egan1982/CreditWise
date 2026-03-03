#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML 处理模块 - 处理 HTML 文件中的资源路径，支持子应用集成
"""

import re
from pathlib import Path
from typing import Optional


def process_html_for_subapp(
    html_content: str,
    prefix: str = ""
) -> str:
    """
    处理 HTML 内容中的资源路径，为子应用集成做准备
    
    当库作为子应用挂载到主应用时（例如挂载在 /llm），HTML 中的资源路径需要被调整。
    例如：<script src="/static/js/main.js"> 应该变成 <script src="/llm/static/js/main.js">
    
    Args:
        html_content: HTML 文件内容
        prefix: 子应用的挂载路径前缀（例如 "/llm"）
    
    Returns:
        处理后的 HTML 内容
    
    Examples:
        >>> html = '<script src="/static/js/main.js"></script>'
        >>> process_html_for_subapp(html, '/llm')
        '<script src="/llm/static/js/main.js"></script>'
    """
    
    if not prefix or prefix == "/":
        return html_content
    
    # 移除末尾的斜杠
    prefix = prefix.rstrip("/")
    
    # 处理所有以 / 开头的路径（src、href 属性）
    # 但要避免重复处理已经有前缀的路径
    def replace_path(match):
        attr_name = match.group(1)  # src 或 href
        path = match.group(2)       # 路径
        
        # 如果路径已经以前缀开头，不要重复处理
        if path.startswith(prefix):
            return match.group(0)
        
        # 特殊处理：不处理外部 URL（包含 :// 的）
        if "://" in path:
            return match.group(0)
        
        return f'{attr_name}="{prefix}{path}"'
    
    # 使用正则表达式替换所有的 src 和 href 属性
    result = re.sub(
        r'(src|href)="(/[^"]*)"',
        replace_path,
        html_content
    )
    
    return result


def load_and_process_html(
    html_path: Path,
    prefix: str = ""
) -> str:
    """
    加载 HTML 文件并处理资源路径
    
    Args:
        html_path: HTML 文件路径
        prefix: 子应用挂载路径前缀
    
    Returns:
        处理后的 HTML 内容
    
    Raises:
        FileNotFoundError: HTML 文件不存在
        IOError: 读取文件失败
    """
    
    if not html_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    return process_html_for_subapp(html_content, prefix)


class HTMLProcessor:
    """
    HTML 处理类 - 用于在请求时动态处理 HTML
    """
    
    def __init__(self, html_path: Path, prefix: str = ""):
        """
        初始化处理器
        
        Args:
            html_path: HTML 文件路径
            prefix: 子应用挂载路径前缀
        """
        self.html_path = html_path
        self.prefix = prefix
        self._cached_html: Optional[str] = None
        self._load_html()
    
    def _load_html(self) -> None:
        """加载并缓存 HTML"""
        if self.html_path.exists():
            with open(self.html_path, "r", encoding="utf-8") as f:
                self._cached_html = f.read()
    
    def get_html(self) -> str:
        """
        获取处理后的 HTML
        
        Returns:
            处理后的 HTML 内容
        """
        if self._cached_html is None:
            return ""
        
        return process_html_for_subapp(self._cached_html, self.prefix)
    
    def reload(self) -> None:
        """重新加载 HTML 文件（用于开发时热更新）"""
        self._load_html()


# 使用示例
if __name__ == "__main__":
    # 测试 process_html_for_subapp
    test_html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <link href="/static/css/main.css">
        <script src="/static/js/main.js"></script>
        <link rel="icon" href="/favicon.ico">
        <link rel="manifest" href="/manifest.json">
    </head>
    <body>
        <img src="/logo.png" />
    </body>
    </html>
    '''
    
    processed = process_html_for_subapp(test_html, "/llm")
    
    print("Original HTML:")
    print(test_html)
    print("\n" + "="*60 + "\n")
    print("Processed HTML:")
    print(processed)
    
    # 验证路径替换
    assert '/llm/static/css/main.css' in processed
    assert '/llm/static/js/main.js' in processed
    assert '/llm/favicon.ico' in processed
    assert '/llm/logo.png' in processed
    print("\n✓ All path replacements verified!")
