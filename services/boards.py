import asyncio
import math
import os
import re
import secrets
import time
from datetime import datetime
from typing import Any, Dict, List

import dotenv
import emoji
from pydantic import TypeAdapter

from objects import Board, Reaction, Response, Thread
from services.db import DBService
from services.exception import (
    BackendError,
    ContentTooLong,
    ContentTooShort,
    PostResponseRateLimit,
    PostThreadRateLimit,
    VerificationRequired,
)
from services.id import generateId, tz
from services.socketio import sio
from services.trip import generateTrip

dotenv.load_dotenv()

boardTypeAdapter = TypeAdapter(List[Board])
threadTypeAdapter = TypeAdapter(List[Thread])
responseTypeAdapter = TypeAdapter(List[Response])
reactionTypeAdapter = TypeAdapter(List[Reaction])


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


async def getBoards():
    rows = [dict(row) for row in await DBService.pool.fetch("SELECT * FROM boards")]
    return boardTypeAdapter.validate_python(rows)


async def getThreadsInBoard(id: str, page: int = 0):
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
            "SELECT COUNT(*) FROM responses WHERE parent_id = $1",
            row["id"],
        )
        row["board"] = row["id"].split("_")[0]
        row["id"] = int(row["id"].split("_")[1])
        rows.append(row)

    return threadTypeAdapter.validate_python(rows)


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
    row["board"] = row["id"].split("_")[0]
    row["id"] = int(row["id"].split("_")[1])
    return Thread.model_validate(row)


async def getResponsesInThread(boardId: str, id: str):
    rows = []

    for _row in await DBService.pool.fetch(
        "SELECT * FROM responses WHERE parent_id = $1 ORDER by created_at ASC",
        f"{boardId}_{id}",
    ):
        row = dict(_row)
        rows.append(row)

    return responseTypeAdapter.validate_python(rows)


async def getVerifiedUser(command: str, cookies: Dict[str, str]) -> Dict[str, Any]:
    token = cookies.get("2ch_X")
    if not token:
        tokens = command.split("#", 1)
        if len(tokens) <= 1:
            raise VerificationRequired(os.getenv("turnstileSiteKey"))
        token = tokens[1]

    idRow = await DBService.pool.fetchrow("SELECT * FROM ids WHERE token = $1", token)
    if not idRow:
        raise VerificationRequired(os.getenv("turnstileSiteKey"))
    return dict(idRow)


def sanitize(input: str):
    # 基本的なサニタイズ
    input = (
        emoji.emojize(
            input, delimiters=("::", "::"), language="alias", variant="emoji_type"
        )
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .strip()
        .strip(" ")
        .strip("　")
        .strip("\t")
        .strip("\n")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("&#10;", "")
    )
    return input


def sanitizeRefs(text: str) -> str:
    result = []
    i = 0
    while i < len(text):
        if text[i] == "&" and i + 1 < len(text) and text[i + 1] == "#":
            j = i + 2
            base = 10
            if j < len(text) and text[j] in "xX":
                base = 16
                j += 1

            while j < len(text) and (
                text[j].isdigit() or (base == 16 and text[j] in "abcdefABCDEF")
            ):
                j += 1

            if j < len(text) and text[j] == ";":
                result.append(text[i : j + 1])
                i = j + 1
                continue
            else:
                i = j
                continue
        else:
            result.append(text[i])
            i += 1
    return "".join(result)


def sanitizeThreadName(name: str):
    name = name.replace("\r\n", "").replace("\r", "").replace("\n", "")
    name = re.sub(r"&#([Xx]0*[aA]|0*10);", "", name)
    return sanitizeRefs(name)


def sanitizeName(name: str):
    name = (
        sanitize(name)
        .replace("\n", "")
        .replace("◆", "◇")
        .replace("&#9670;", "◇")
        .replace("★", "☆")
        .replace("&#9733;", "☆")
    )
    return name


def formatName(name: str, anonName: str) -> str:
    if name != "":
        fields = name.rsplit("#", 1)
        if len(fields) <= 1:
            return sanitizeName(fields[0])
        else:
            name, tripKey = tuple(fields)

            name = sanitizeName(name)
            tripKey = generateTrip(f"#{tripKey}")
            return f"{name}{tripKey}"
    return sanitizeName(anonName)


def formatContent(content: str) -> str:
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    return content


# ここらへん直さないとだめな気がする
def emojiToHTML(text: str) -> str:
    result = []
    for char in text:
        if ord(char) > 0xFFFF:
            result.append(f"&#{ord(char)};")
        else:
            result.append(char)
    return "".join(result)


async def updateIdIp(idRow: Dict[str, Any], ipAddress: str):
    idRow["ips"].append(ipAddress)
    await DBService.pool.execute(
        "UPDATE ONLY ids SET ips = $1 WHERE token = $2",
        list(set(idRow["ips"])),
        idRow["token"],
    )


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

    idRow = await getVerifiedUser(command, cookies)

    title = emojiToHTML(sanitizeThreadName(title))
    content = emojiToHTML(sanitize(formatContent(content)))
    name = emojiToHTML(formatName(name, board.anonName))

    attributes = {}
    # キャップ
    if idRow["cap"]:
        attributes["cap"] = idRow["cap"]
        attributes["cap_color"] = idRow["cap_color"]

    if len(title) <= 0:
        raise ContentTooShort("タイトル", 1)
    if len(content) <= 0:
        raise ContentTooShort("本文", 1)
    if len(title) > 192:
        raise ContentTooLong("タイトル", 192)
    if len(name) > 128:
        raise ContentTooLong("名前", 128)
    if formatContent(content).count("\n") > 16:
        raise ContentTooLong("本文の改行", 16)
    if len(content) > 9192:
        raise ContentTooLong("本文", 9192)

    shownId = generateId(ipAddress)

    ratelimit = await DBService.redis.get(f"postThreadRateLimits_{idRow['id']}")
    if ratelimit and float(ratelimit) > time.time():
        raise PostThreadRateLimit(float(ratelimit) - time.time())
    await DBService.redis.set(
        f"postThreadRateLimits_{idRow['id']}", time.time() + 600, ex=60 * 60 * 24
    )

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
            (id, created_at, title, sort_key, owner_id, owner_shown_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """,
        f"{board.id}_{key}",
        datetime.now(tz),
        title,
        key,
        idRow["id"],
        shownId,
    )

    row = dict(row)
    row["count"] = await DBService.pool.fetchval(
        "SELECT COUNT(*) FROM responses WHERE parent_id = $1", row["id"]
    )
    row["board"] = row["id"].split("_")[0]
    row["id"] = int(row["id"].split("_")[1])
    thread = Thread.model_validate(row)

    await DBService.pool.execute(
        """
            INSERT INTO responses
            (id, created_at, parent_id, author_id, shown_id, name, content, attributes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
        secrets.token_hex(6),
        datetime.now(tz),
        f"{board.id}_{key}",
        idRow["id"],
        shownId,
        name,
        content,
        attributes,
    )

    async def notification():
        await sio.emit(
            "updateThreads",
            threadTypeAdapter.dump_python(
                await getThreadsInBoard(board.id), mode="json", by_alias=True
            ),
            thread.board,
        )

    asyncio.create_task(updateIdIp(idRow, ipAddress))
    asyncio.create_task(notification())

    return thread, idRow


def addReaction(*, emojiChar: str, resNum: int):
    if emojiChar not in emoji.EMOJI_DATA:
        raise BackendError("EMOJI_NOT_FOUND", "絵文字が存在しません")


async def postResponse(
    *,
    boardId: str,
    threadId: str,
    name: str,
    command: str,
    content: str,
    cookies: Dict[str, str],
    ipAddress: str,
):
    board = await getBoard(boardId)
    thread = await getThreadInBoard(board.id, threadId)

    idRow = await getVerifiedUser(command, cookies)

    content = emojiToHTML(sanitize(formatContent(content)))
    name = emojiToHTML(formatName(name, board.anonName))

    attributes = {}
    # キャップ
    if idRow["cap"]:
        attributes["cap"] = idRow["cap"]
        attributes["cap_color"] = idRow["cap_color"]

    if len(content) <= 0:
        raise ContentTooShort("本文", 1)
    if len(name) > 128:
        raise ContentTooLong("名前", 128)
    if formatContent(content).count("\n") > 16:
        raise ContentTooLong("本文の改行", 16)
    if len(content) > 9192:
        raise ContentTooLong("本文", 9192)

    shownId = generateId(ipAddress)

    ratelimit = await DBService.redis.get(f"postResponseRateLimits_{idRow['id']}")
    if ratelimit and float(ratelimit) > time.time():
        raise PostResponseRateLimit(float(ratelimit) - time.time())
    await DBService.redis.set(
        f"postResponseRateLimits_{idRow['id']}", time.time() + 5, ex=60 * 60 * 24
    )

    # キー被り対策
    while True:
        key = math.floor(time.time())
        if not await DBService.pool.fetchrow(
            "SELECT * FROM threads WHERE id = $1", f"{thread.board}_{key}"
        ):
            break
        await asyncio.sleep(1)

    row = await DBService.pool.fetchrow(
        """
            INSERT INTO responses
            (id, created_at, parent_id, author_id, shown_id, name, content, attributes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """,
        secrets.token_hex(6),
        datetime.now(tz),
        f"{thread.board}_{thread.id}",
        idRow["id"],
        shownId,
        name,
        content,
        attributes,
    )
    response = Response.model_validate(dict(row))

    await DBService.pool.execute(
        "UPDATE ONLY threads SET sort_key = $1 WHERE id = $2",
        time.time(),
        f"{thread.board}_{thread.id}",
    )

    async def notification():
        await sio.emit(
            "newResponse",
            response.model_dump(mode="json", by_alias=True),
            f"{thread.board}_{thread.id}",
        )

        await sio.emit(
            "updateThreads",
            threadTypeAdapter.dump_python(
                await getThreadsInBoard(board.id), mode="json", by_alias=True
            ),
            thread.board,
        )

    asyncio.create_task(updateIdIp(idRow, ipAddress))
    asyncio.create_task(notification())

    return response, idRow
