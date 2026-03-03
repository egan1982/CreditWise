"""
资源访问工具模块

提供便利的方式来访问包内的文档、示例等资源。
"""

import sys
from pathlib import Path
from typing import Optional

try:
    # Python 3.9+
    from importlib.resources import files
except ImportError:
    # Python 3.8 fallback
    from importlib_resources import files  # type: ignore


def get_resource_path(resource_name: str) -> Optional[Path]:
    """
    获取包内资源的路径

    Args:
        resource_name: 资源名称（相对于 resources 目录）
                      示例：'docs/INTEGRATION_GUIDE.md'

    Returns:
        资源的 Path 对象，如果不存在则返回 None

    Examples:
        >>> from llm_api_manager import get_resource_path
        >>> path = get_resource_path('docs/INTEGRATION_GUIDE.md')
        >>> if path and path.exists():
        ...     content = path.read_text()
    """
    try:
        # 获取 resources 包的路径
        ref = files('llm_api_manager').joinpath('resources', resource_name)

        # 尝试获取实际文件路径
        # 对于已安装的包，这通常有效
        if hasattr(ref, '__fspath__'):
            return Path(ref)

        # 对于 zipped/namespaced 包，提取到临时位置
        if sys.version_info >= (3, 9):
            from importlib.resources import as_file
            with as_file(ref) as path:
                return path if path.exists() else None
        else:
            # Python 3.8
            with files('llm_api_manager').joinpath('resources').as_file(resource_name) as path:
                return path if path.exists() else None
    except (ImportError, AttributeError, FileNotFoundError):
        # 如果找不到资源，尝试从项目根目录查找（开发模式）
        try:
            project_root = Path(__file__).parent.parent
            dev_path = project_root / resource_name
            if dev_path.exists():
                return dev_path
        except Exception:
            pass

        return None


def get_docs_path() -> Optional[Path]:
    """
    获取集成文档目录的路径

    Returns:
        docs 目录的 Path 对象，如果不存在则返回 None

    Examples:
        >>> from llm_api_manager import get_docs_path
        >>> docs_dir = get_docs_path()
        >>> if docs_dir:
        ...     integration_guide = docs_dir / 'INTEGRATION_GUIDE.md'
        ...     print(integration_guide.read_text())
    """
    return get_resource_path('docs')


def get_examples_path() -> Optional[Path]:
    """
    获取示例代码目录的路径

    Returns:
        examples 目录的 Path 对象，如果不存在则返回 None

    Examples:
        >>> from llm_api_manager import get_examples_path
        >>> examples_dir = get_examples_path()
        >>> if examples_dir:
        ...     fastapi_example = examples_dir / 'fastapi_integration.py'
        ...     print(fastapi_example.read_text())
    """
    return get_resource_path('examples')


def list_docs() -> list[str]:
    """
    列出所有可用的文档文件

    Returns:
        文档文件名的列表

    Examples:
        >>> from llm_api_manager.resources.utils import list_docs
        >>> docs = list_docs()
        >>> for doc in docs:
        ...     print(f"- {doc}")
    """
    docs_path = get_docs_path()
    if docs_path and docs_path.exists():
        return [f.name for f in docs_path.glob('*.md')]
    return []


def list_examples() -> list[str]:
    """
    列出所有可用的示例文件

    Returns:
        示例文件名的列表

    Examples:
        >>> from llm_api_manager.resources.utils import list_examples
        >>> examples = list_examples()
        >>> for example in examples:
        ...     print(f"- {example}")
    """
    examples_path = get_examples_path()
    if examples_path and examples_path.exists():
        return [f.name for f in examples_path.glob('*.py')]
    return []


def read_doc(filename: str) -> Optional[str]:
    """
    读取文档文件内容

    Args:
        filename: 文档文件名（不需要完整路径）

    Returns:
        文档内容，如果文件不存在则返回 None

    Examples:
        >>> from llm_api_manager.resources.utils import read_doc
        >>> guide = read_doc('INTEGRATION_GUIDE.md')
        >>> if guide:
        ...     print(guide[:100])  # 打印前 100 个字符
    """
    docs_path = get_docs_path()
    if docs_path:
        doc_file = docs_path / filename
        if doc_file.exists():
            return doc_file.read_text(encoding='utf-8')
    return None


def read_example(filename: str) -> Optional[str]:
    """
    读取示例文件内容

    Args:
        filename: 示例文件名（不需要完整路径）

    Returns:
        示例代码内容，如果文件不存在则返回 None

    Examples:
        >>> from llm_api_manager.resources.utils import read_example
        >>> example = read_example('fastapi_integration.py')
        >>> if example:
        ...     print(example[:100])  # 打印前 100 个字符
    """
    examples_path = get_examples_path()
    if examples_path:
        example_file = examples_path / filename
        if example_file.exists():
            return example_file.read_text(encoding='utf-8')
    return None
