"""FastAPI 应用入口 - 用于 uvicorn 启动"""

from .app import create_standalone_app

# 创建应用实例
app = create_standalone_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
