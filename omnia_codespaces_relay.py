#!/usr/bin/env python3
"""OMNIA ONLINE O1-CS: WebSocket relay for private 2-player rooms.

Designed for a forwarded *public* GitHub Codespaces HTTP port. HTTPS/WSS
terminates at GitHub; this local process listens on plain HTTP/WebSocket only.
It DOES NOT execute rules, read cards or store game contents.
Do not deploy as public production matchmaking infrastructure.
"""
import argparse
import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

LOG = logging.getLogger("omnia.codespaces")
ROOM_CODE = re.compile(r"^[0-9a-f]{12}$")
MAX_PACKET = 32768
ROOM_WAIT_SECONDS = 900


@dataclass
class Room:
    code: str
    host: object
    guest: Optional[object] = None
    created: float = field(default_factory=time.monotonic)
    started: asyncio.Event = field(default_factory=asyncio.Event)
    finished: asyncio.Event = field(default_factory=asyncio.Event)


class PrivateRoomRelay:
    def __init__(self, max_rooms=16):
        self.max_rooms = max_rooms
        self.rooms: dict[str, Room] = {}
        self.lock = asyncio.Lock()

    async def forward(self, source, destination):
        async for frame in source:
            if not isinstance(frame, str) or len(frame.encode("utf8")) > MAX_PACKET:
                await source.close(code=1009, reason="Invalid frame")
                return
            await destination.send(frame)

    async def transmit(self, room):
        first = asyncio.create_task(self.forward(room.host, room.guest))
        second = asyncio.create_task(self.forward(room.guest, room.host))
        try:
            completed, pending = await asyncio.wait(
                {first, second}, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            await asyncio.gather(first, second, return_exceptions=True)
        finally:
            room.finished.set()

    async def handle(self, ws):
        room = None
        owner = False
        try:
            if ws.request.path != "/omnia":
                await ws.close(code=1008, reason="Invalid endpoint")
                return
            opening = await asyncio.wait_for(ws.recv(), timeout=10)
            if not isinstance(opening, str) or len(opening) > 80:
                await ws.send("ERROR BAD_REQUEST")
                return
            match = re.fullmatch(r"(CREATE|JOIN) ([0-9a-f]{12})", opening)
            if match is None:
                await ws.send("ERROR BAD_REQUEST")
                return
            verb, code = match.groups()
            owner = verb == "CREATE"
            async with self.lock:
                if owner:
                    if code in self.rooms:
                        await ws.send("ERROR ROOM_EXISTS")
                        return
                    if len(self.rooms) >= self.max_rooms:
                        await ws.send("ERROR RELAY_FULL")
                        return
                    room = Room(code, ws)
                    self.rooms[code] = room
                else:
                    candidate = self.rooms.get(code)
                    if candidate is None or candidate.guest is not None or \
                            time.monotonic() - candidate.created > ROOM_WAIT_SECONDS:
                        await ws.send("ERROR ROOM_UNAVAILABLE")
                        return
                    candidate.guest = ws
                    room = candidate
            if owner:
                await ws.send("READY")
                joined = asyncio.create_task(room.started.wait())
                disconnected = asyncio.create_task(ws.wait_closed())
                completed, pending = await asyncio.wait(
                    {joined, disconnected}, timeout=ROOM_WAIT_SECONDS,
                    return_when=asyncio.FIRST_COMPLETED)
                for task in pending:
                    task.cancel()
                await asyncio.gather(joined, disconnected, return_exceptions=True)
                if joined not in completed:
                    return
                await self.transmit(room)
            else:
                # Control messages precede forwarded JSON so the client can
                # send its authenticated HELLO after JOINED.
                await ws.send("JOINED")
                await room.host.send("PEER")
                room.started.set()
                await room.finished.wait()
        except asyncio.TimeoutError:
            try:
                await ws.send("ERROR ROOM_TIMEOUT")
            except ConnectionClosed:
                pass
        except (ConnectionClosed, OSError) as exc:
            LOG.debug("Disconnect: %s", type(exc).__name__)
        finally:
            if owner and room is not None:
                async with self.lock:
                    if self.rooms.get(room.code) is room:
                        del self.rooms[room.code]
                room.finished.set()
                if room.guest is not None:
                    await room.guest.close()


async def main_async(host, port, max_rooms):
    relay = PrivateRoomRelay(max_rooms=max_rooms)
    async with serve(relay.handle, host, port, max_size=MAX_PACKET,
                     max_queue=16, ping_interval=20, ping_timeout=20,
                     compression=None) as server:
        LOG.info("OMNIA Codespaces WSS relay running on http://%s:%s/omnia", host, port)
        LOG.info("Share the Codespaces forwarded public HTTPS URL, not localhost")
        await server.serve_forever()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=27862, type=int)
    parser.add_argument("--max-rooms", default=16, type=int)
    args = parser.parse_args()
    if args.max_rooms < 1 or args.max_rooms > 128:
        parser.error("max-rooms must be between 1 and 128")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(main_async(args.host, args.port, args.max_rooms))


if __name__ == "__main__":
    main()
