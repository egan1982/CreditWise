# setup.py
# 用于向后兼容，实际配置在 pyproject.toml

from setuptools import setup, find_packages

setup(
    name="deepanalyze",
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    packages=find_packages(),
)
