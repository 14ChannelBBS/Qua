import asyncio

from objects import Board
from services.boards import createBoard
from services.db import DBService


async def main():
    await DBService.run()

    await createBoard(
        Board(
            id=input("板のID: "),
            name=input("板の名前: "),
            description=input("板の説明: "),
            anon_name=input("名無し名: "),
        )
    )

    await DBService.shutdown()


asyncio.run(main())
