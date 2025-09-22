import asyncio
import html
import math
import os
import time
from typing import Dict, List

import dotenv
from pydantic import TypeAdapter

from objects import Board, Response, Thread
from services.db import DBService
from services.exception import ContentTooLong, VerificationRequired
from services.id import generateId
from services.trip import generateTrip

dotenv.load_dotenv()


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


async def postThread(
    *,
    boardId: str,
    title: str,
    name: str,
    command: str,
    content: str,
    cookies: Dict[str, str],
    ipAddress: str,
):
    board = await getBoard(boardId)

    token = cookies.get("2ch_X")
    if not token:
        raise VerificationRequired(os.getenv("turnstileSiteKey"))

    idRow = await DBService.pool.fetchrow("SELECT * FROM ids WHERE token = $1", token)
    if not idRow:
        raise VerificationRequired(os.getenv("turnstileSiteKey"))
    idRow = dict(idRow)

    if len(title) > 100:
        raise ContentTooLong("タイトル", 100)
    if len(name) > 32:
        raise ContentTooLong("名前", 32)
    if len(content) > 500:
        raise ContentTooLong("本文", 500)

    title = html.escape(title)
    name = html.escape(generateTrip(name))
    content = html.escape(content)

    # 1日限りのIDを生成
    shownId = generateId(ipAddress)

    # キー被り対策
    while True:
        key = math.floor(time.time())
        if not await DBService.pool.fetchrow(
            "SELECT * FROM threads WHERE id = $1", f"{board.id}_{key}"
        ):
            break
        await asyncio.sleep(1)

    row = await DBService.pool.fetchrow(
        """
            INSERT INTO threads
            (id, title, sort_key, owner_id, owner_shown_id)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """,
        f"{board.id}_{key}",
        title,
        key,
        idRow["id"],
        shownId,
    )

    row = dict(row)
    row["count"] = await DBService.pool.fetchval(
        "SELECT COUNT(*) FROM responses WHERE parent_id = $1", row["id"]
    )
    row["id"] = int(row["id"].split("_")[1])

    async def updateIdIp():
        idRow["ips"].append(ipAddress)
        await DBService.pool.execute(
            "UPDATE ONLY ids SET ips = $1 WHERE token = $2",
            list(set(idRow["ips"])),
            idRow["token"],
        )

    asyncio.create_task(updateIdIp())

    return Thread.model_validate(row)
