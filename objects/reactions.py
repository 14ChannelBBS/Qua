from typing import List, Optional

from pydantic import BaseModel


class Emoji(BaseModel):
    id: Optional[str]
    name: str


class Reaction(BaseModel):
    emoji: Emoji
    userIds: List[str]
