import glob
import importlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from services.db import DBService


@asynccontextmanager
async def lifespan(app: FastAPI):
    await DBService.run()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Qua",
    summary="くあちゃん今日もかわいいね🥰",
    description="A document of qua (14channel backend system)",
)
app.mount("/static", StaticFiles(directory="static"), "static")


moduleList = glob.glob("routes/*.py")
for module in moduleList:
    app.include_router(
        importlib.import_module(module.replace(".py", "").replace("\\", ".")).router
    )
