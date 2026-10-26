import uvicorn
from .config import settings
from .api.server import app


def main():
    logger_msg = f"[cv-ai-agent] Starting FastAPI server on port {settings.ai_port}..."
    print(logger_msg)
    uvicorn.run(
        "src.api.server:app",
        host="0.0.0.0",
        port=settings.ai_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
