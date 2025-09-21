from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Json
from pydantic.alias_generators import to_snake


class Response(BaseModel):
    id: str
    parentId: str
    createdAt: datetime
    authorId: str
    shownId: str
    name: str
    content: str
    reactions: List[str]
    attributes: Json

    model_config = ConfigDict(alias_generator=to_snake)
