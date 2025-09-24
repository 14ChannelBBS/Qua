from datetime import datetime
from typing import Dict, List

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
    attributes: Dict[str, str]

    model_config = ConfigDict(alias_generator=to_snake)
