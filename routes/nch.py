from urllib.parse import parse_qs, quote, unquote_plus

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from routes.front import templates, version
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
    ContentTooLong,
    ContentTooShort,
    PostResponseRateLimit,
    PostThreadRateLimit,
    VerificationRequired,
)

router = APIRouter()


@router.get("/bbsmenu.html")
async def index(request: Request):
    return templates.TemplateResponse(
        request,
        "bbsmenu.html",
        {"request": request, "version": version, "boards": await getBoards()},
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
        (
            f"{board.id}@Qua\n"
            + "\n".join([f"{key}={value}" for key, value in setting.items()])
        ).encode("shift_jis"),
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
        ).encode("shift-jis"),
        media_type="text/plain; charset=shift_jis",
    )


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

    name = response.name
    if response.attributes.get("cap"):
        name += "@" + response.attributes.get("cap") + " ★"

        if response.attributes.get("cap_color"):
            name = f'<font color="{response.attributes.get("cap_color")}">{name}</font>'

    return PlainTextResponse(
        (
            "\n".join(
                [
                    f"{name}<>{response.attributes.get('email', '')}<>{response.createdAt.strftime('%Y/%m/%d %H:%M:%S.%f')} ID:{response.shownId}<> {response.content.replace('\n', ' <br> ')} <>"
                    for response in responses
                ]
            )
        ).encode("shift-jis"),
        media_type="text/plain; charset=shift_jis",
    )


@router.get("/test/bbs.cgi")
@router.post("/test/bbs.cgi")
async def bbscgi(request: Request):
    data = await request.body()
    postDataDict = {
        k: unquote_plus(v[0], "cp932") for k, v in parse_qs(data.decode()).items()
    }

    bbs = postDataDict.get("bbs", "").encode("utf-8").decode("utf-8")
    key = int(postDataDict.get("key", 0))
    subject = postDataDict.get("subject", "").encode("utf-8").decode("utf-8")
    FROM = postDataDict.get("FROM", "").encode("utf-8").decode("utf-8")
    mail = postDataDict.get("mail", "").encode("utf-8").decode("utf-8")
    MESSAGE = postDataDict.get("MESSAGE", "").encode("utf-8").decode("utf-8")
    submit = postDataDict.get("submit", "").encode("utf-8").decode("utf-8")

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
        return templates.TemplateResponse(
            request=request,
            name="bbscgi_error.html",
            context={
                "message": "フォーム情報が正しく読めないです。",
                "ipaddr": ipAddress,
                "bbs": bbs,
                "key": key,
                "FROM": FROM,
                "mail": mail,
                "MESSAGE": MESSAGE,
            },
            headers={"content-type": "text/html; charset=shift_jis"},
        )

    try:
        if key:
            response = await postResponse(
                boardId=bbs,
                threadId=key,
                name=FROM,
                command=mail,
                content=MESSAGE,
                cookies=cookies,
                ipAddress=ipAddress,
            )
            fields = response.parentId.rsplit("_", 1)
            board = fields[0]
            threadId = fields[1]
            internalId = response.authorId
        else:
            thread = await postThread(
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
            internalId = thread.ownerId

        templateResponse = templates.TemplateResponse(
            request=request,
            name="bbscgi_success.html",
            context={
                "bbs": board,
                "key": threadId,
            },
            headers={"content-type": "text/html; charset=shift_jis"},
        )

        templateResponse.set_cookie(
            "2ch_X",
            await DBService.pool.fetchval(
                "SELECT token FROM ids WHERE id = $1", internalId
            ),
            max_age=60 * 60 * 60 * 24 * 365 * 10,
        )
        if FROM != "":
            templateResponse.set_cookie(
                "NAME", quote(FROM), max_age=60 * 60 * 60 * 24 * 365 * 10
            )
        else:
            response.delete_cookie("NAME")
        if mail != "":
            templateResponse.set_cookie(
                "MAIL", quote(mail), max_age=60 * 60 * 60 * 24 * 365 * 10
            )
        else:
            response.delete_cookie("MAIL")

        return templateResponse
    except VerificationRequired:
        return templates.TemplateResponse(
            request=request,
            name="bbscgi_error.html",
            context={
                "message": f'あなたは認証していません。 <a href="{request.url.scheme}://{request.url.hostname}{f":{request.url.port}" if request.url.port is not None else ""}/auth">{request.url.scheme}://{request.url.hostname}{f":{request.url.port}" if request.url.port is not None else ""}/auth</a> から認証してください。',
                "ipaddr": ipAddress,
                "bbs": bbs,
                "key": key,
                "FROM": FROM,
                "mail": mail,
                "MESSAGE": MESSAGE,
                "version": version,
            },
            headers={"content-type": "text/html; charset=shift_jis"},
        )
    except NameError:
        return templates.TemplateResponse(
            request=request,
            name="bbscgi_error.html",
            context={
                "message": "板情報またはスレッド情報が壊れています！",
                "ipaddr": ipAddress,
                "bbs": bbs,
                "key": key,
                "FROM": FROM,
                "mail": mail,
                "MESSAGE": MESSAGE,
                "version": version,
            },
            headers={"content-type": "text/html; charset=shift_jis"},
        )
    except ContentTooLong as e:
        return templates.TemplateResponse(
            request=request,
            name="bbscgi_error.html",
            context={
                "message": f"{e.type}が長すぎます。{e.max}文字以内に収めてください。",
                "ipaddr": ipAddress,
                "bbs": bbs,
                "key": key,
                "FROM": FROM,
                "mail": mail,
                "MESSAGE": MESSAGE,
                "version": version,
            },
            headers={"content-type": "text/html; charset=shift_jis"},
        )
    except ContentTooShort as e:
        return templates.TemplateResponse(
            request=request,
            name="bbscgi_error.html",
            context={
                "message": f"{e.type}が短すぎます。{e.min}文字以上にしてください。",
                "ipaddr": ipAddress,
                "bbs": bbs,
                "key": key,
                "FROM": FROM,
                "mail": mail,
                "MESSAGE": MESSAGE,
                "version": version,
            },
            headers={"content-type": "text/html; charset=shift_jis"},
        )
    except PostThreadRateLimit as e:
        return templates.TemplateResponse(
            request=request,
            name="bbscgi_error.html",
            context={
                "message": f"落ち着いて投稿してください。投稿可能になるまで残り{e.remain}秒です。",
                "ipaddr": ipAddress,
                "bbs": bbs,
                "key": key,
                "FROM": FROM,
                "mail": mail,
                "MESSAGE": MESSAGE,
                "version": version,
            },
            headers={"content-type": "text/html; charset=shift_jis"},
        )
    except PostResponseRateLimit as e:
        return templates.TemplateResponse(
            request=request,
            name="bbscgi_error.html",
            context={
                "message": f"落ち着いて投稿してください。投稿可能になるまで残り{e.remain}秒です。",
                "ipaddr": ipAddress,
                "bbs": bbs,
                "key": key,
                "FROM": FROM,
                "mail": mail,
                "MESSAGE": MESSAGE,
                "version": version,
            },
            headers={"content-type": "text/html; charset=shift_jis"},
        )
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="bbscgi_error.html",
            context={
                "message": f"内部エラーです: {e}",
                "ipaddr": ipAddress,
                "bbs": bbs,
                "key": key,
                "FROM": FROM,
                "mail": mail,
                "MESSAGE": MESSAGE,
                "version": version,
            },
            headers={"content-type": "text/html; charset=shift_jis"},
        )
