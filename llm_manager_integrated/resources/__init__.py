"""
LLM API Manager 资源包

包含集成文档、示例代码和其他资源文件

使用方式：
    # 获取资源路径
    >>> from llm_manager_integrated import get_docs_path, get_examples_path
    >>> docs = get_docs_path()
    >>> examples = get_examples_path()

    # 直接读取内容
    >>> from llm_manager_integrated.resources.utils import read_doc, read_example
    >>> guide = read_doc('INTEGRATION_GUIDE.md')
    >>> fastapi_example = read_example('fastapi_integration.py')

    # 列出可用的资源
    >>> from llm_manager_integrated.resources.utils import list_docs, list_examples
    >>> all_docs = list_docs()
    >>> all_examples = list_examples()
"""

from .utils import (
    get_resource_path,
    get_docs_path,
    get_examples_path,
    list_docs,
    list_examples,
    read_doc,
    read_example,
)

__all__ = [
    'get_resource_path',
    'get_docs_path',
    'get_examples_path',
    'list_docs',
    'list_examples',
    'read_doc',
    'read_example',
]
