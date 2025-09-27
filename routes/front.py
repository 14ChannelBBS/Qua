from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from services.boards import getBoard, getThreadInBoard

router = APIRouter()
templates = Jinja2Templates("pages")

version = "v2025.09.27"


@router.get("/", include_in_schema=False)
def index(request: Request):
    return templates.TemplateResponse(
        request, "index.html", {"request": request, "version": version}
    )


@router.get("/auth", include_in_schema=False)
def authPage(request: Request):
    return templates.TemplateResponse(
        request, "auth.html", {"request": request, "version": version}
    )


@router.get("/{boardId:str}/", include_in_schema=False)
async def boardPage(request: Request, boardId: str):
    try:
        board = await getBoard(boardId)
    except NameError:
        raise HTTPException(404)

    return templates.TemplateResponse(
        request,
        "board.html",
        {
            "request": request,
            "version": version,
            "board": board,
        },
    )


@router.get("/{boardId:str}/{threadId:int}", include_in_schema=False)
async def threadPage(request: Request, boardId: str, threadId: int):
    try:
        board = await getBoard(boardId)
        thread = await getThreadInBoard(board.id, threadId)
    except NameError:
        raise HTTPException(404)

    return templates.TemplateResponse(
        request,
        "thread.html",
        {
            "request": request,
            "version": version,
            "board": board,
            "thread": thread,
        },
    )
