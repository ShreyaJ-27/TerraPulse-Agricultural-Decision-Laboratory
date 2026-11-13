"""Start the TerraPulse API with a psycopg-compatible local event loop."""

import asyncio

import uvicorn

from app.core.config import get_settings
from app.core.event_loop import new_event_loop


def main() -> None:
    settings = get_settings()
    server = uvicorn.Server(uvicorn.Config("app.main:app", host=settings.api_host, port=settings.api_port))
    with asyncio.Runner(loop_factory=new_event_loop) as runner:
        runner.run(server.serve())


if __name__ == "__main__":
    main()
