import os
import secrets
import string
import uuid
from datetime import datetime

import dotenv
import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from services.cf import isFromCloudflare
from services.db import DBService
from services.id import tz

dotenv.load_dotenv()

router = APIRouter()


class VerificationRequest(BaseModel):
    turnstileResponse: str


def randomId(n: int) -> str:
    return "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(n)
    )


@router.post("/api/verification")
async def verification(
    request: Request, response: Response, model: VerificationRequest
):
    ipAddress = (
        request.headers["CF-Connecting-IP"]
        if isFromCloudflare(request.client.host)
        else request.client.host
    )

    async with httpx.AsyncClient() as http:
        httpResponse = await http.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            json={
                "secret": os.getenv("turnstileSecretKey"),
                "response": model.turnstileResponse,
                "remoteip": ipAddress,
                "idempotency_key": str(uuid.uuid4()),
            },
        )
        httpResponse.raise_for_status()
        jsonData = httpResponse.json()

    if not jsonData["success"]:
        raise HTTPException(
            400, detail=jsonData.get("error-codes", "Verification failed")
        )

    token = secrets.token_hex(16)
    await DBService.pool.execute(
        "INSERT INTO ids (token, id, ips, created_at) VALUES ($1, $2, $3, $4)",
        token,
        randomId(8),
        [ipAddress],
        datetime.now(tz),
    )

    response.set_cookie("2ch_X", token, max_age=31536000)
    return {
        "detail": "VERIFICATION_SUCCESSFUL",
        "message": "認証が完了しました。",
        "token": token,
    }
