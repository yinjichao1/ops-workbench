"""Development startup script — 局域网共享模式."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",       # 局域网可访问
        port=8000,
        reload=True,
        log_level="info",
    )
