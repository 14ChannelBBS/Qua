import asyncio

from services.db import DBService


async def main():
    await DBService.run()

    token = input("トークン: ")

    if not await DBService.pool.fetchrow("SELECT * FROM ids WHERE token = $1", token):
        raise Exception("IDが存在しないけど")

    cap = input("キャップ名: ")
    capColor = input("キャップ色 (何も入力しないとスキップ): ")
    if capColor == "":
        capColor = None

    await DBService.pool.execute(
        "UPDATE ONLY ids SET cap = $1, cap_color = $2 WHERE token = $3",
        cap,
        capColor,
        token,
    )

    await DBService.shutdown()


asyncio.run(main())
