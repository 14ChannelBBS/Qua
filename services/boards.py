from typing import List

from pydantic import TypeAdapter

from objects import Board, Response, Thread
from services.db import DBService


async def createBoard(board: Board):
    await DBService.pool.execute(
        "INSERT INTO boards (id, name, description, anon_name) VALUES ($1, $2, $3, $4)",
        board.id,
        board.name,
        board.description,
        board.anonName,
    )
    return board


async def getBoard(id: str):
    row = await DBService.pool.fetchrow("SELECT * FROM boards WHERE id = $1", id)
    if not row:
        raise NameError(f"Board {id} not found")
    return Board.model_validate(dict(row))


async def getThreadsInBoard(id: str, page: int = 0):
    typeAdapter = TypeAdapter(List[Thread])

    rows = []

    PAGE_SIZE = 20

    for _row in await DBService.pool.fetch(
        """
            SELECT *
            FROM threads
            WHERE id LIKE $1
            ORDER BY sort_key DESC
            OFFSET $2 LIMIT $3
        """,
        f"{id}_%",
        page * PAGE_SIZE,
        PAGE_SIZE,
    ):
        row = dict(_row)
        row["count"] = await DBService.pool.fetchval(
            "SELECT COUNT(*) FROM threads WHERE id = $1",
            row["id"],
        )
        row["id"] = int(row["id"].split("_")[1])
        rows.append(row)

    return typeAdapter.validate_python(rows)


async def getThreadInBoard(boardId: str, id: int):
    row = await DBService.pool.fetchrow(
        "SELECT * FROM threads WHERE id = $1", f"{boardId}_{id}"
    )
    if not row:
        raise NameError(f"thread {id} not found")

    row = dict(row)
    row["count"] = await DBService.pool.fetchval(
        "SELECT COUNT(*) FROM responses WHERE parent_id = $1", row["id"]
    )
    row["id"] = int(row["id"].split("_")[1])
    return Thread.model_validate(row)


async def getResponsesInThread(boardId: str, id: str):
    typeAdapter = TypeAdapter(List[Response])

    rows = []

    for _row in await DBService.pool.fetch(
        "SELECT * FROM responses WHERE parent_id = $1 ORDER by created_at ASC",
        f"{boardId}_{id}",
    ):
        row = dict(_row)
        rows.append(row)

    return typeAdapter.validate_python(rows)
