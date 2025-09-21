from datetime import datetime
from typing import Union

from pydantic import BaseModel, ConfigDict, Json
from pydantic.alias_generators import to_snake


class Thread(BaseModel):
    id: Union[str, int]
    title: str
    createdAt: datetime
    sortKey: int
    ownerId: str
    ownerShownId: str
    count: int
    attributes: Json

    model_config = ConfigDict(alias_generator=to_snake)
