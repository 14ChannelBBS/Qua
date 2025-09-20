from datetime import datetime
from typing import Any, Dict, Union

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_snake


class Thread(BaseModel):
    id: str
    title: str
    createdAt: datetime
    ownerId: str
    ownerShownId: str
    attributes: Dict[str, Union[str, int, Dict[Any, Any]]]

    model_config = ConfigDict(alias_generator=to_snake)
