import enum
from dataclasses import dataclass, field
from typing import Dict, Optional

from .boards import Board
from .id import IdRow
from .responses import Response
from .threads import Thread


class Device(enum.Enum):
    OfficialClient = 0
    Monazilla = 1


@dataclass
class BaseEvent:
    __errorMessage__: Optional[str] = field(None, init=False)
    __isCriticalError__: bool = field(False, init=False)

    def setErrorMessage(self, message: str):
        self.__errorMessage__ = message

    def setCriticalError(self, isCriticalError: bool):
        self.__isCriticalError__ = isCriticalError


@dataclass
class ThreadPostEvent(BaseEvent):
    board: Board
    title: str
    name: str
    command: str
    content: str
    attributes: Dict[str, str]
    idRow: IdRow
    shownId: str


@dataclass
class ResponsePostEvent(BaseEvent):
    thread: Thread
    name: str
    command: str
    content: str
    attributes: Dict[str, str]
    idRow: IdRow
    shownId: str


@dataclass
class RenderingResponseEvent(BaseEvent):
    thread: Thread
    response: Optional[Response]
    device: Device


class QuaPlugin:
    def __init__(self):
        self.id = None
        self.name = None
        self.description = None
        self.projectUrl = None
        self.version = None

    async def onThreadPost(self, event: ThreadPostEvent):
        raise NotImplementedError()

    async def onResponsePost(self, event: ResponsePostEvent):
        raise NotImplementedError()

    def onRenderingResponse(self, event: RenderingResponseEvent):
        raise NotImplementedError()
