import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.import_router import router as import_router
from utils.logger import get_logger

logger = get_logger("main")

app = FastAPI(
    title="Import Service",
    description="Parses bank CSV exports and dispatches transactions to a RabbitMQ queue for import.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(import_router)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
