import html
import traceback
from typing import Dict
from urllib.parse import parse_qs, quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

from routes.front import version
from services.boards import (
    getBoard,
    getBoards,
    getResponsesInThread,
    getThreadInBoard,
    getThreadsInBoard,
    postResponse,
    postThread,
)
from services.cf import isFromCloudflare
from services.db import DBService
from services.exception import (
    BackendError,
    ContentTooLong,
    ContentTooShort,
    PostRateLimit,
    VerificationRequired,
)

router = APIRouter()
env = Environment(
    loader=FileSystemLoader("pages", encoding="shift_jis"),
    autoescape=select_autoescape(["html", "xml"]),
)


def renderSJISPage(name: str, context: Dict[str, str]) -> bytes:
    template = env.get_template(name)
    htmlText = template.render(**context)
    htmlBytes = htmlText.encode("shift_jis", errors="replace")
    return htmlBytes


@router.get("/bbsmenu.html")
async def index(request: Request):
    return Response(
        content=renderSJISPage(
            "bbsmenu.html",
            {"request": request, "version": version, "boards": await getBoards()},
        ),
        media_type="text/html; charset=shift_jis",
    )


@router.get("/{boardId:str}/SETTING.TXT", response_class=PlainTextResponse)
async def board(boardId: str):
    try:
        board = await getBoard(boardId)
    except NameError:
        raise HTTPException(404)

    setting = {
        "BBS_TITLE": board.name,
        "BBS_TITLE_ORIG": board.name,
        "BBS_LINE_NUMBER": 16,
        "BBS_NONAME_NAME": board.anonName,
        "BBS_SUBJECT_COUNT": 192,
        "BBS_NAME_COUNT": 128,
        "BBS_MAIL_COUNT": 9192,
        "BBS_MESSAGE_COUNT": 9192,
    }

    return PlainTextResponse(
        ("\n".join([f"{key}={value}" for key, value in setting.items()])).encode(
            "shift_jis"
        ),
        media_type="text/plain; charset=shift_jis",
    )


@router.get("/{boardId:str}/head.txt", response_class=PlainTextResponse)
async def head(boardId: str):
    try:
        board = await getBoard(boardId)
    except NameError:
        raise HTTPException(404)

    return PlainTextResponse(
        board.description.encode("shift_jis"),
        media_type="text/plain; charset=shift_jis",
    )


@router.get("/{boardId:str}/subject.txt", response_class=PlainTextResponse)
async def threads(boardId: str):
    try:
        board = await getBoard(boardId)
        threads = (
            (await getThreadsInBoard(board.id, 0))
            + (await getThreadsInBoard(board.id, 1))
            + (await getThreadsInBoard(board.id, 2))
            + (await getThreadsInBoard(board.id, 3))
        )
    except NameError:
        raise HTTPException(404)

    for thread in threads:
        del thread.ownerId

    return PlainTextResponse(
        (
            "\n".join(
                [
                    f"{thread.id}.dat<>{thread.title} ({thread.count})"
                    for thread in threads
                ]
            )
            + "\n"
        ).encode("shift-jis"),
        media_type="text/plain; charset=shift_jis",
    )


@router.get(
    "/test/read.cgi/{boardId:str}/{threadId:int}/{options:str}",
    response_class=RedirectResponse,
    include_in_schema=False,
)
def redirect(boardId: str, threadId: int, options: str):
    return RedirectResponse(f"/{boardId}/{threadId}")


@router.get("/{boardId:str}/dat/{threadId:int}.dat", response_class=PlainTextResponse)
async def responses(boardId: str, threadId: int):
    try:
        board = await getBoard(boardId)
        thread = await getThreadInBoard(board.id, threadId)
        responses = await getResponsesInThread(board.id, thread.id)
    except NameError:
        raise HTTPException(404)

    for response in responses:
        del response.authorId

        if len(response.reactions) > 0:
            reactions = "\n"
            for reaction in response.reactions:
                reactions += f"{reaction.emoji.name} {len(reaction.userIds)} | "
            reactions = reactions.removesuffix("| ")

            response.content += reactions

    name = response.name
    if response.attributes.get("cap"):
        name += "@" + response.attributes.get("cap") + " ★"

        if response.attributes.get("cap_color"):
            name = f'<font color="{response.attributes.get("cap_color")}">{name}</font>'

    return PlainTextResponse(
        (
            "\n".join(
                [
                    f"{name}<>{response.attributes.get('email', '')}<>{response.createdAt.strftime('%Y/%m/%d %H:%M:%S.%f')} ID:{response.shownId}<> {response.content.replace('\n', ' <br> ')} <>{thread.title if i == 0 else ''}"
                    for i, response in enumerate(responses)
                ]
            )
            + "\n"
        ).encode("shift-jis", "ignore"),
        media_type="text/plain; charset=shift_jis",
    )


@router.get("/test/bbs.cgi")
@router.post("/test/bbs.cgi")
async def bbscgi(request: Request):
    data = await request.body()
    postDataDict = {
        k: v[0] for k, v in parse_qs(data.decode(), encoding="shift-jis").items()
    }

    bbs = html.unescape(postDataDict.get("bbs", ""))
    key = int(postDataDict.get("key", 0))
    time = int(postDataDict.get("time", 0))
    subject = html.unescape(postDataDict.get("subject", ""))
    FROM = html.unescape(postDataDict.get("FROM", ""))
    mail = html.unescape(postDataDict.get("mail", ""))
    MESSAGE = html.unescape(postDataDict.get("MESSAGE", ""))
    submit = html.unescape(postDataDict.get("submit", ""))

    cookies = request.cookies
    ipAddress = (
        request.headers["CF-Connecting-IP"]
        if isFromCloudflare(request.client.host)
        else request.client.host
    )

    if not (
        (request.method.lower() != "post")
        or ("書き込む" in submit)
        or ((not subject) and (not key))
        or ((subject is not None) and (key is not None))
    ):
        return Response(
            content=renderSJISPage(
                "bbscgi_error.html",
                {
                    "message": "フォーム情報が正しく読めないです。",
                    "ipaddr": ipAddress,
                    "bbs": bbs,
                    "key": key,
                    "FROM": FROM,
                    "mail": mail,
                    "MESSAGE": MESSAGE,
                },
            ),
            media_type="text/html; charset=shift_jis",
        )

    try:
        if key:
            response, idRow = await postResponse(
                boardId=bbs,
                threadId=key,
                name=FROM,
                command=mail,
                content=MESSAGE,
                cookies=cookies,
                ipAddress=ipAddress,
            )
            if response:
                fields = response.parentId.rsplit("_", 1)
                board = fields[0]
                threadId = fields[1]
                resNum = await DBService.pool.fetchval(
                    "SELECT COUNT(*) FROM responses WHERE parent_id = $1",
                    response.parentId,
                )
            else:
                board = bbs
                threadId = key
                resNum = None
        else:
            thread, idRow = await postThread(
                boardId=bbs,
                title=subject,
                name=FROM,
                command=mail,
                content=MESSAGE,
                cookies=cookies,
                ipAddress=ipAddress,
            )
            board = thread.board
            threadId = thread.id
            resNum = thread.count

        templateResponse = Response(
            content=renderSJISPage(
                "bbscgi_success.html",
                {
                    "bbs": board,
                    "key": threadId,
                },
            ),
            media_type="text/html; charset=shift_jis",
        )

        templateResponse.set_cookie(
            "2ch_X",
            idRow["token"],
            max_age=60 * 60 * 60 * 24 * 365 * 10,
        )
        if FROM != "":
            templateResponse.set_cookie(
                "NAME", quote(FROM), max_age=60 * 60 * 60 * 24 * 365 * 10
            )
        else:
            templateResponse.delete_cookie("NAME")
        if mail != "":
            templateResponse.set_cookie(
                "MAIL", quote(mail), max_age=60 * 60 * 60 * 24 * 365 * 10
            )
        else:
            templateResponse.delete_cookie("MAIL")

        if resNum:
            templateResponse.headers.update({"X-ResNum": str(resNum)})

        return templateResponse
    except VerificationRequired:
        return Response(
            content=renderSJISPage(
                "bbscgi_error.html",
                {
                    "message": f'あなたは認証していません。 <a href="{request.url.scheme}://{request.url.hostname}{f":{request.url.port}" if request.url.port is not None else ""}/auth">{request.url.scheme}://{request.url.hostname}{f":{request.url.port}" if request.url.port is not None else ""}/auth</a> から認証してください。',
                    "ipaddr": ipAddress,
                    "bbs": bbs,
                    "key": key,
                    "time": time,
                    "subject": subject,
                    "FROM": FROM,
                    "mail": mail,
                    "MESSAGE": MESSAGE,
                    "version": version,
                },
            ),
            media_type="text/html; charset=shift_jis",
        )
    except NameError:
        return Response(
            content=renderSJISPage(
                "bbscgi_error.html",
                {
                    "message": "板情報またはスレッド情報が壊れています！",
                    "ipaddr": ipAddress,
                    "bbs": bbs,
                    "key": key,
                    "time": time,
                    "subject": subject,
                    "FROM": FROM,
                    "mail": mail,
                    "MESSAGE": MESSAGE,
                    "version": version,
                },
            ),
            media_type="text/html; charset=shift_jis",
        )
    except ContentTooLong as e:
        return Response(
            content=renderSJISPage(
                "bbscgi_error.html",
                {
                    "message": f"{e.type}が長すぎます。{e.max}文字以内に収めてください。",
                    "ipaddr": ipAddress,
                    "bbs": bbs,
                    "key": key,
                    "time": time,
                    "subject": subject,
                    "FROM": FROM,
                    "mail": mail,
                    "MESSAGE": MESSAGE,
                    "version": version,
                },
            ),
            media_type="text/html; charset=shift_jis",
        )
    except ContentTooShort as e:
        return Response(
            content=renderSJISPage(
                "bbscgi_error.html",
                {
                    "message": f"{e.type}が短すぎます。{e.min}文字以上にしてください。",
                    "ipaddr": ipAddress,
                    "bbs": bbs,
                    "key": key,
                    "time": time,
                    "subject": subject,
                    "FROM": FROM,
                    "mail": mail,
                    "MESSAGE": MESSAGE,
                    "version": version,
                },
            ),
            media_type="text/html; charset=shift_jis",
        )
    except PostRateLimit as e:
        return Response(
            content=renderSJISPage(
                "bbscgi_error.html",
                {
                    "message": f"落ち着いて投稿してください。投稿可能になるまで残り{e.remain}秒です。",
                    "ipaddr": ipAddress,
                    "bbs": bbs,
                    "key": key,
                    "time": time,
                    "subject": subject,
                    "FROM": FROM,
                    "mail": mail,
                    "MESSAGE": MESSAGE,
                    "version": version,
                },
            ),
            media_type="text/html; charset=shift_jis",
        )
    except BackendError as e:
        return Response(
            content=renderSJISPage(
                "bbscgi_error.html",
                {
                    "message": e.message or e.detail,
                    "ipaddr": ipAddress,
                    "bbs": bbs,
                    "key": key,
                    "time": time,
                    "subject": subject,
                    "FROM": FROM,
                    "mail": mail,
                    "MESSAGE": MESSAGE,
                    "version": version,
                },
            ),
            media_type="text/html; charset=shift_jis",
        )
    except Exception as e:
        traceback.print_exc()
        return Response(
            content=renderSJISPage(
                "bbscgi_error.html",
                {
                    "message": f"内部エラーです！ {e}",
                    "ipaddr": ipAddress,
                    "bbs": bbs,
                    "key": key,
                    "time": time,
                    "subject": subject,
                    "FROM": FROM,
                    "mail": mail,
                    "MESSAGE": MESSAGE,
                    "version": version,
                },
            ),
            media_type="text/html; charset=shift_jis",
        )
