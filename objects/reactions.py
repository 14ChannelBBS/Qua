from typing import List, Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_snake


class Emoji(BaseModel):
    id: Optional[str]
    name: str

    model_config = ConfigDict(alias_generator=to_snake)


class Reaction(BaseModel):
    emoji: Emoji
    userIds: List[str]
    count: Optional[int] = None

    model_config = ConfigDict(
        alias_generator=to_snake, populate_by_name=True, serialize_by_alias=False
    )
