from typing import Dict

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_snake


class Board(BaseModel):
    id: str
    name: str
    description: str
    anonName: str
    attributes: Dict[str, str]

    model_config = ConfigDict(alias_generator=to_snake)
