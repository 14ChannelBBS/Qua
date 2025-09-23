import traceback

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from services.boards import (
    getBoard,
    getResponsesInThread,
    getThreadInBoard,
    getThreadsInBoard,
    postResponse,
    postThread,
)
from services.cf import isFromCloudflare
from services.db import DBService
from services.exception import (
    ContentTooLong,
    ContentTooShort,
    PostResponseRateLimit,
    PostThreadRateLimit,
    VerificationRequired,
)

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
        response.status_code = 201
        thread = await postThread(
            boardId=boardId,
            title=model.title,
            name=model.name,
            command=model.command,
            content=model.content,
            cookies=cookies,
            ipAddress=ipAddress,
        )

        response.set_cookie(
            "2ch_X",
            await DBService.pool.fetchval(
                "SELECT token FROM ids WHERE id = $1", thread.ownerId
            ),
            max_age=60 * 60 * 60 * 24 * 365 * 10,
        )

        if model.name != "":
            response.set_cookie(
                "NAME", model.name, max_age=60 * 60 * 60 * 24 * 365 * 10
            )
        if model.command != "":
            response.set_cookie(
                "MAIL", model.command, max_age=60 * 60 * 60 * 24 * 365 * 10
            )

        return thread
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
    except ContentTooShort as e:
        response.status_code = 400
        return {
            "detail": "CONTENT_TOO_SHORT",
            "message": f"{e.type}が短すぎます。{e.min}文字以上にしてください。",
        }
    except PostThreadRateLimit as e:
        response.status_code = 429
        return {
            "detail": "OTITUITE",
            "message": f"落ち着いて投稿してください。投稿可能になるまで残り{e.remain}秒です。",
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, detail=str(e))


class PostResponseRequest(BaseModel):
    name: str
    command: str
    content: str


@router.put("/api/boards/{boardId:str}/threads/{threadId:int}")
async def apiPostResponse(
    request: Request,
    response: Response,
    boardId: str,
    threadId: int,
    model: PostResponseRequest,
):
    cookies = request.cookies
    ipAddress = (
        request.headers["CF-Connecting-IP"]
        if isFromCloudflare(request.client.host)
        else request.client.host
    )

    try:
        response.status_code = 201
        responseObject = await postResponse(
            boardId=boardId,
            threadId=threadId,
            name=model.name,
            command=model.command,
            content=model.content,
            cookies=cookies,
            ipAddress=ipAddress,
        )

        response.set_cookie(
            "2ch_X",
            await DBService.pool.fetchval(
                "SELECT token FROM ids WHERE id = $1", responseObject.authorId
            ),
            max_age=60 * 60 * 60 * 24 * 365 * 10,
        )
        if model.name != "":
            response.set_cookie(
                "NAME", model.name, max_age=60 * 60 * 60 * 24 * 365 * 10
            )
        if model.command != "":
            response.set_cookie(
                "MAIL", model.command, max_age=60 * 60 * 60 * 24 * 365 * 10
            )

        return responseObject
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
    except ContentTooShort as e:
        response.status_code = 400
        return {
            "detail": "CONTENT_TOO_SHORT",
            "message": f"{e.type}が短すぎます。{e.min}文字以上にしてください。",
        }
    except PostResponseRateLimit as e:
        response.status_code = 429
        return {
            "detail": "OTITUITE",
            "message": f"落ち着いて投稿してください。投稿可能になるまで残り{e.remain}秒です。",
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, detail=str(e))
