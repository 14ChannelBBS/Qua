from datetime import datetime
from typing import Dict, Union

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_snake


class Thread(BaseModel):
    id: Union[str, int]
    board: str
    title: str
    createdAt: datetime
    sortKey: int
    ownerId: str
    ownerShownId: str
    count: int
    attributes: Dict[str, str]

    model_config = ConfigDict(alias_generator=to_snake)
