import glob
import importlib
from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from services.db import DBService
from services.socketio import sio


@asynccontextmanager
async def lifespan(app: FastAPI):
    await DBService.run()
    yield


fastAPI = FastAPI(
    lifespan=lifespan,
    title="Qua",
    summary="くあちゃん今日もかわいいね🥰",
    description="A document of qua (14channel backend system)",
)
fastAPI.mount("/static", StaticFiles(directory="static"), "static")
fastAPI.add_middleware(GZipMiddleware, minimum_size=1000)


moduleList = glob.glob("routes/*.py")
for module in moduleList:
    fastAPI.include_router(
        importlib.import_module(module.replace(".py", "").replace("\\", ".")).router
    )

app = socketio.ASGIApp(sio, fastAPI)
