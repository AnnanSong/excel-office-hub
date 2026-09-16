from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    router_aggregate,
    router_compare,
    router_create_sheets,
    router_merge,
    router_split,
    router_validate,
)
from app.core.config import settings
from app.core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path("./data").mkdir(parents=True, exist_ok=True)
    init_db()
    yield


app = FastAPI(
    title="Excel Office Hub API",
    description="Excel 办公处理网站后端 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_split.router, prefix="/api/split", tags=["拆分"])
app.include_router(router_aggregate.router, prefix="/api/aggregate", tags=["汇总"])
app.include_router(router_create_sheets.router, prefix="/api/create-sheets", tags=["建表"])
app.include_router(router_merge.router, prefix="/api/merge", tags=["合并汇总"])
app.include_router(router_compare.router, prefix="/api/compare", tags=["数据比对"])
app.include_router(router_validate.router, prefix="/api/validate", tags=["数据校验"])


@app.get("/health", tags=["健康检查"])
def health_check():
    return {"status": "ok"}


@app.exception_handler(Exception)
def global_exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"detail": str(exc)})
