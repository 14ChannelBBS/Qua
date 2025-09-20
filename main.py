import glob
import importlib

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(
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
