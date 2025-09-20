from datetime import datetime
from typing import Any, Dict, Union

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_snake


class Response(BaseModel):
    id: str
    parentId: str
    createdAt: datetime
    authorId: str
    shownId: str
    name: str
    content: str
    attributes: Dict[str, Union[str, int, Dict[Any, Any]]]

    model_config = ConfigDict(alias_generator=to_snake)
