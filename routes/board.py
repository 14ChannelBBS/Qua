from fastapi import APIRouter, HTTPException

from services.boards import (
    getBoard,
    getResponsesInThread,
    getThreadInBoard,
    getThreadsInBoard,
)

router = APIRouter()

version = "v2025.09.21"


@router.get("/api/boards/{boardId:str}", include_in_schema=True)
async def board(boardId: str):
    try:
        board = await getBoard(boardId)
    except NameError:
        raise HTTPException(404)

    return board


@router.get("/api/boards/{boardId:str}/threads", include_in_schema=True)
async def threads(boardId: str):
    try:
        board = await getBoard(boardId)
        threads = await getThreadsInBoard(board.id)
    except NameError:
        raise HTTPException(404)

    for thread in threads:
        del thread.ownerId

    return threads


@router.get("/api/boards/{boardId:str}/threads/{threadId:int}", include_in_schema=True)
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
