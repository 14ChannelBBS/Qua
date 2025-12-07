from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_snake


class IdRow(BaseModel):
    token: str
    id: str
    ips: List[str]
    createdAt: datetime
    cap: Optional[str] = None
    capColor: Optional[str] = None

    model_config = ConfigDict(
        alias_generator=to_snake, populate_by_name=True, serialize_by_alias=False
    )
