import socketio

sio = socketio.AsyncServer(async_mode="asgi")


@sio.event
async def joinRoom(sid: str, room: str):
    await sio.enter_room(sid, room)
