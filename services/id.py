import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import dotenv

dotenv.load_dotenv()
tz = timezone(timedelta(hours=9), "Asia/Tokyo")


def generateId(ipAddress: str, boardId: str):
    timestamp = datetime.now(tz).strftime("%Y-%m-%d")
    data = f"{timestamp}-{ipAddress}-{boardId}"

    idHash = hmac.new(
        os.getenv("idEncryptKey").encode("utf-8"), data.encode("utf-8"), hashlib.sha1
    ).hexdigest()

    idBase64 = base64.b64encode(idHash.encode()).decode()

    return idBase64[:8]
