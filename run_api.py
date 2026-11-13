import asyncio
import selectors
import sys
import uvicorn

if sys.platform == "win32":
    loop_factory = lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())
else:
    loop_factory = "auto"

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, loop=loop_factory, reload=False, app_dir="apps/api")
