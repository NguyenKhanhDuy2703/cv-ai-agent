import asyncio
import uvicorn
from .config import settings
from .jobs.database import configure_event_loop


def main():
    logger_msg = f"[cv-ai-agent] Starting FastAPI server on port {settings.ai_port}..."
    print(logger_msg)
    # Own the loop so psycopg uses SelectorEventLoop on Windows. Calling
    # uvicorn.run directly can select ProactorEventLoop on recent Uvicorn.
    async def serve():
        server = uvicorn.Server(uvicorn.Config(
            "src.api.server:app", host="0.0.0.0", port=settings.ai_port,
        ))
        await server.serve()

    configure_event_loop()
    asyncio.run(serve())


if __name__ == "__main__":
    main()
