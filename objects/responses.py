from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_snake

from .reactions import Reaction


class Response(BaseModel):
    id: str
    parentId: str
    createdAt: datetime
    authorId: str
    shownId: str
    name: str
    content: str
    reactions: List[Reaction]
    attributes: Dict[str, Any]

    model_config = ConfigDict(
        alias_generator=to_snake, populate_by_name=True, serialize_by_alias=False
    )
