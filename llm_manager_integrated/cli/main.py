#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM API Manager - CLI 启动模块

提供命令行接口启动 LLM API Manager 服务

使用方式:
    llm-manager serve              # 启动后端服务
    llm-manager serve --port 8001  # 指定端口
    llm-manager serve --help       # 显示帮助
"""

import sys
import argparse
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    """配置日志"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='[%(levelname)s] %(message)s'
    )


def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    log_level: str = "info"
) -> int:
    """
    启动 FastAPI 服务
    
    Args:
        host: 绑定的主机地址
        port: 服务端口
        reload: 是否启用自动重载
        log_level: 日志级别
    
    Returns:
        exit code
    """
    try:
        import uvicorn
        from llm_manager_integrated.api.main import app
        
        logger.info("=" * 60)
        logger.info("LLM API Manager - Starting Service")
        logger.info("=" * 60)
        logger.info(f"Backend URL: http://{host}:{port}")
        logger.info(f"API Docs: http://{host}:{port}/docs")
        logger.info(f"Frontend: http://{host}:{port}/")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level=log_level
        )
        return 0
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        return 1


def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        prog="llm-manager",
        description="LLM API Manager - 大模型 API 管理和代理系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  llm-manager serve              # Start service on default port (8000)
  llm-manager serve --port 8001  # Start service on custom port
  llm-manager serve --reload     # Start with auto-reload for development
  llm-manager serve --help       # Show this help message

Features:
  - FastAPI backend with integrated React frontend
  - Channel management and API proxying
  - Built-in logging and monitoring
  - Database management
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # 'serve' 子命令
    serve_parser = subparsers.add_parser(
        "serve",
        help="Start the LLM API Manager service"
    )
    serve_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    serve_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    serve_parser.add_argument(
        "--log-level",
        type=str,
        choices=["critical", "error", "warning", "info", "debug"],
        default="info",
        help="Log level (default: info)"
    )
    
    # 解析参数
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(args.log_level if hasattr(args, "log_level") else "INFO")
    
    # 如果没有指定命令，显示帮助并启动 serve
    if not args.command or args.command == "serve":
        return serve(
            host=getattr(args, "host", "127.0.0.1"),
            port=getattr(args, "port", 8000),
            reload=getattr(args, "reload", False),
            log_level=getattr(args, "log_level", "info")
        )
    
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
