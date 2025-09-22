import traceback

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from services.boards import (
    getBoard,
    getResponsesInThread,
    getThreadInBoard,
    getThreadsInBoard,
    postThread,
)
from services.cf import isFromCloudflare
from services.exception import ContentTooLong, VerificationRequired

router = APIRouter()

version = "v2025.09.21"


@router.get("/api/boards/{boardId:str}")
async def board(boardId: str):
    try:
        board = await getBoard(boardId)
    except NameError:
        raise HTTPException(404)

    return board


@router.get("/api/boards/{boardId:str}/threads")
async def threads(boardId: str):
    try:
        board = await getBoard(boardId)
        threads = await getThreadsInBoard(board.id)
    except NameError:
        raise HTTPException(404)

    for thread in threads:
        del thread.ownerId

    return threads


@router.get("/api/boards/{boardId:str}/threads/{threadId:int}")
async def responses(boardId: str, threadId: int):
    try:
        board = await getBoard(boardId)
        thread = await getThreadInBoard(board.id, threadId)
        responses = await getResponsesInThread(board.id, thread.id)
    except NameError:
        raise HTTPException(404)

    for response in responses:
        del response.authorId

    return responses


class PostThreadRequest(BaseModel):
    title: str
    name: str
    command: str
    content: str


@router.put("/api/boards/{boardId:str}")
async def apiPostThread(
    request: Request, response: Response, boardId: str, model: PostThreadRequest
):
    cookies = request.cookies
    ipAddress = (
        request.headers["CF-Connecting-IP"]
        if isFromCloudflare(request.client.host)
        else request.client.host
    )

    try:
        return await postThread(
            boardId=boardId,
            title=model.title,
            name=model.name,
            command=model.command,
            content=model.content,
            cookies=cookies,
            ipAddress=ipAddress,
        )
    except VerificationRequired as e:
        response.status_code = 401
        return {
            "detail": "VERIFICATION_REQUIRED",
            "message": "認証が必要です。以下のチェックボックスをクリックして認証を行ってください。",
            "sitekey": e.turnstileSiteKey,
        }
    except NameError:
        raise HTTPException(404)
    except ContentTooLong as e:
        response.status_code = 413
        return {
            "detail": "CONTENT_TOO_LONG",
            "message": f"{e.type}が長すぎます。{e.max}文字以内に収めてください。",
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, detail=e)
