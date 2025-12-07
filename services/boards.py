import asyncio
import copy
import html
import math
import os
import re
import secrets
import time
from datetime import datetime
from typing import Dict, List

import dotenv
import emoji
from pydantic import TypeAdapter

from objects import (
    Board,
    Device,
    Emoji,
    IdRow,
    Reaction,
    RenderingResponseEvent,
    Response,
    ResponsePostEvent,
    Thread,
    ThreadPostEvent,
)
from services import emojiData
from services.db import DBService
from services.exception import (
    BackendError,
    ContentTooLong,
    ContentTooShort,
    PostRateLimit,
    VerificationRequired,
)
from services.id import generateId, tz
from services.plugin import PluginService
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
            WHERE id LIKE $1 AND deleted = false
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
        "SELECT * FROM threads WHERE id = $1 AND deleted = false", f"{boardId}_{id}"
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
        "SELECT * FROM responses WHERE parent_id = $1 AND deleted = false ORDER by created_at ASC",
        f"{boardId}_{id}",
    ):
        row = dict(_row)
        rows.append(row)

    return responseTypeAdapter.validate_python(rows)


async def updateThread(thread: Thread):
    await DBService.pool.execute(
        """
            UPDATE ONLY responses
            SET title = $2,
            WHERE id = $1
        """,
        thread.id,
        thread.title,
    )


async def updateResponse(response: Response):
    response = copy.deepcopy(response)
    for reaction in response.reactions:
        del reaction.count

    await DBService.pool.execute(
        """
            UPDATE ONLY responses
            SET name = $2,
            content = $3,
            reactions = $4,
            attributes = $5
            WHERE id = $1
        """,
        response.id,
        response.name,
        response.content,
        reactionTypeAdapter.dump_python(response.reactions, mode="json"),
        response.attributes,
    )


async def getVerifiedUser(command: str, cookies: Dict[str, str]) -> IdRow:
    token = cookies.get("2ch_X")
    if not token:
        tokens = command.split("#", 1)
        if len(tokens) <= 1:
            raise VerificationRequired(os.getenv("turnstileSiteKey"))
        token = tokens[1]

    row = await DBService.pool.fetchrow("SELECT * FROM ids WHERE token = $1", token)
    if not row:
        raise VerificationRequired(os.getenv("turnstileSiteKey"))
    return IdRow.model_validate(dict(row))


async def deleteThread(thread: Thread, hard: bool = False):
    if hard:
        await DBService.pool.execute("DELETE from threads WHERE id = $1", thread.id)
    else:
        await DBService.pool.execute(
            "UPDATE only threads SET deleted = true WHERE id = $1", thread.id
        )


async def deleteResponse(response: Response, hard: bool = False):
    if hard:
        await DBService.pool.execute("DELETE from responses WHERE id = $1", response.id)
    else:
        await DBService.pool.execute(
            "UPDATE only responses SET deleted = true WHERE id = $1", response.id
        )


def sanitize(input: str):
    # 基本的なサニタイズ
    input = (
        emoji.emojize(
            input, delimiters=("::", "::"), language="alias", variant="emoji_type"
        )
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .strip()
        .strip(" ")
        .strip("　")
        .strip("\t")
        .strip("\n")
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
    name = sanitize(name).replace('"', "&quot;")
    name = re.sub(r"&#([Xx]0*[aA]|0*10);", "", name)
    return sanitizeRefs(name)


def sanitizeName(name: str):
    name = (
        sanitize(name)
        .replace('"', "&quot;")
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
    content = content.replace('"', "&quot;")
    return content


def emojiToHTML(text: str) -> str:
    result = []
    for char in text:
        if char.encode("shift-jis", "ignore").decode("shift-jis", "ignore") != char:
            result.append(f"&#{ord(char)};")
        else:
            result.append(char)
    return "".join(result)


async def updateIdIp(idRow: IdRow, ipAddress: str):
    idRow.ips.append(ipAddress)
    await DBService.pool.execute(
        "UPDATE ONLY ids SET ips = $1 WHERE token = $2",
        list(set(idRow.ips)),
        idRow.token,
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
    if idRow.cap:
        attributes["cap"] = idRow.cap
        attributes["nameColor"] = idRow.capColor

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

    shownId = generateId(ipAddress, board.id)

    ratelimit = await DBService.redis.get(f"PostThreadRateLimits_{idRow.id}")
    if ratelimit and float(ratelimit) > time.time():
        raise PostRateLimit(float(ratelimit) - time.time())
    await DBService.redis.set(
        f"PostThreadRateLimits_{idRow.id}", time.time() + 600, ex=60 * 60 * 24
    )

    # Run event
    event = ThreadPostEvent(
        board, title, name, command, content, attributes, idRow, shownId
    )
    for plugin in PluginService.plugins:
        try:
            await plugin.onThreadPost(event)
        except NotImplementedError:
            pass

    title = event.title
    name = event.name
    content = event.content
    attributes = event.attributes
    shownId = event.shownId

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
            (id, created_at, title, sort_key, owner_id, owner_shown_id, host)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """,
        f"{board.id}_{key}",
        datetime.now(tz),
        title,
        key,
        idRow.id,
        shownId,
        ipAddress,
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
            (id, created_at, parent_id, author_id, shown_id, host, name, content, attributes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        secrets.token_hex(6),
        datetime.now(tz),
        f"{board.id}_{key}",
        idRow.id,
        shownId,
        ipAddress,
        name,
        content,
        attributes,
    )

    async def notification():
        await sio.emit(
            "updateThreads",
            threadTypeAdapter.dump_python(
                await getThreadsInBoard(board.id), mode="json"
            ),
            thread.board,
        )

    asyncio.create_task(updateIdIp(idRow, ipAddress))
    asyncio.create_task(notification())

    return thread, idRow


async def checkReactions(content: str, userId: str, parentId: str) -> List[Response]:
    responses = []

    lines = content.splitlines()
    for line in lines:
        fields = line.split(" ", 2)
        if len(fields) < 2:
            continue
        anker, emoji = fields

        if not anker.startswith("&gt;&gt;") or not anker[8:].isdigit():
            continue
        if not emoji.startswith("+"):
            continue

        resNum = int(anker[8:])
        emoji = html.unescape(emoji[1:])

        responses.append(await addReaction(emoji, userId, parentId, resNum))
        lines.remove(line)

    return responses, "\n".join(lines)


async def addReaction(emojiChar: str, userId: str, parentId: str, resNum: int):
    _emoji = emojiData.checkEmoji(emojiChar)
    if isinstance(_emoji, bool):
        if not _emoji:
            raise BackendError("REACTION_EMOJI_NOT_FOUND", "絵文字が存在しません")
    else:
        emojiChar = _emoji

    board, thread = parentId.rsplit("_", 1)

    try:
        response = (await getResponsesInThread(board, thread))[resNum - 1]
    except IndexError:
        raise BackendError("REACTION_RESPONSE_NOT_FOUND", "レスが存在しません")

    if len(response.reactions) >= 20:
        raise BackendError(
            "REACTION_LIMIT_EXCEEDED",
            "1つのレスにつけられるリアクションの数は20個までです",
        )

    found = False
    for reaction in response.reactions:
        if userId in reaction.userIds:
            if reaction.emoji.name == emojiToHTML(emojiChar):
                reaction.userIds.remove(userId)
                found = True
        else:
            if reaction.emoji.name == emojiToHTML(emojiChar):
                reaction.userIds.append(userId)
                found = True

        if len(reaction.userIds) <= 0:
            response.reactions.remove(reaction)

    if not found:
        response.reactions.append(
            Reaction(
                emoji=Emoji(id=None, name=emojiToHTML(emojiChar)), user_ids=[userId]
            )
        )

    await updateResponse(response)

    for reaction in response.reactions:
        reaction.count = len(reaction.userIds)
        del reaction.userIds

    return response


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

    content = sanitize(formatContent(content))
    name = emojiToHTML(formatName(name, board.anonName))

    attributes = {}
    # キャップ
    if idRow.cap:
        attributes["cap"] = idRow.cap
        attributes["nameColor"] = idRow.capColor

    if len(content) <= 0:
        raise ContentTooShort("本文", 1)
    if len(name) > 128:
        raise ContentTooLong("名前", 128)
    if formatContent(content).count("\n") > 16:
        raise ContentTooLong("本文の改行", 16)
    if len(content) > 9192:
        raise ContentTooLong("本文", 9192)

    if await DBService.pool.fetchval(
        "SELECT COUNT(*) FROM responses WHERE parent_id = $1",
        f"{thread.board}_{thread.id}",
    ) >= thread.attributes.get("maxResponses", 1000):
        raise BackendError(
            "MAX_RESPONSE_EXDEEDED",
            "スレッドが最大レス数に到達しました。次スレを建てるなら今です！！",
        )

    shownId = generateId(ipAddress, board.id)

    ratelimit = await DBService.redis.get(f"PostResponseRateLimits_{idRow.id}")
    if ratelimit and float(ratelimit) > time.time():
        raise PostRateLimit(float(ratelimit) - time.time())
    await DBService.redis.set(
        f"PostResponseRateLimits_{idRow.id}", time.time() + 5, ex=60 * 60 * 24
    )

    # リアクション
    responses, content = await checkReactions(
        content, idRow.id, f"{thread.board}_{thread.id}"
    )

    # Run event
    event = ResponsePostEvent(
        thread, name, command, content, attributes, idRow, shownId
    )
    for plugin in PluginService.plugins:
        try:
            await plugin.onResponsePost(event)
        except NotImplementedError:
            pass

    name = event.name
    content = event.content
    attributes = event.attributes
    shownId = event.shownId

    if content.strip() != "":
        row = await DBService.pool.fetchrow(
            """
                INSERT INTO responses
                (id, created_at, parent_id, author_id, shown_id, host, name, content, attributes)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING *
            """,
            secrets.token_hex(6),
            datetime.now(tz),
            f"{thread.board}_{thread.id}",
            idRow.id,
            shownId,
            ipAddress,
            name,
            emojiToHTML(content),
            attributes,
        )
        response = Response.model_validate(dict(row))

        await DBService.pool.execute(
            "UPDATE ONLY threads SET sort_key = $1 WHERE id = $2",
            time.time(),
            f"{thread.board}_{thread.id}",
        )
    else:
        response = None

    async def notification():
        nonlocal response

        if response:
            # Run event
            event = RenderingResponseEvent(thread, response, Device.OfficialClient)
            for plugin in PluginService.plugins:
                try:
                    plugin.onRenderingResponse(event)
                except NotImplementedError:
                    pass

            response = event.response

        await sio.emit(
            "newResponse",
            {
                "response": response.model_dump(mode="json") if response else None,
                "updatedResponses": responseTypeAdapter.dump_python(
                    responses, mode="json"
                ),
            },
            f"{thread.board}_{thread.id}",
        )

        await sio.emit(
            "updateThreads",
            threadTypeAdapter.dump_python(
                await getThreadsInBoard(board.id), mode="json"
            ),
            thread.board,
        )

    asyncio.create_task(updateIdIp(idRow, ipAddress))
    asyncio.create_task(notification())

    return response, idRow
