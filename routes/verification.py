import os
import secrets
import string
import uuid

import dotenv
import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from services.cf import isFromCloudflare
from services.db import DBService

dotenv.load_dotenv()

router = APIRouter()


class VerificationRequest(BaseModel):
    turnstileResponse: str


def randomId(n: int) -> str:
    return "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(n)
    )


@router.post("/api/verification")
async def verification(request: Request, model: VerificationRequest):
    ipAddress = (
        request.headers["CF-Connecting-IP"]
        if isFromCloudflare(request.client.host)
        else request.client.host
    )

    async with httpx.AsyncClient() as http:
        response = await http.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            json={
                "secret": os.getenv("turnstileSecretKey"),
                "response": model.turnstileResponse,
                "remoteip": ipAddress,
                "idempotency_key": str(uuid.uuid4()),
            },
        )
        response.raise_for_status()
        jsonData = response.json()

    if not jsonData["success"]:
        raise HTTPException(
            400, detail=jsonData.get("error-codes", "Verification failed")
        )

    token = secrets.token_hex(16)
    await DBService.pool.execute(
        "INSERT INTO ids (token, id, ips) VALUES ($1, $2, $3)",
        token,
        randomId(8),
        [ipAddress],
    )

    return {
        "detail": "VERIFICATION_SUCCESSFUL",
        "message": "認証が完了しました。",
        "token": token,
    }
