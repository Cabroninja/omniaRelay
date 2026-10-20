import asyncio
import socket
import unittest
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from omnia_codespaces_relay import PrivateRoomRelay, MAX_PACKET


class CodespacesRelayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.relay = PrivateRoomRelay(max_rooms=2)
        self.server = await serve(self.relay.handle, "127.0.0.1", 0,
                                  max_size=MAX_PACKET, compression=None)
        port = self.server.sockets[0].getsockname()[1]
        self.url = f"ws://127.0.0.1:{port}/omnia"

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()

    async def test_create_join_bidirectional_and_cleanup(self):
        async with connect(self.url) as host:
            await host.send("CREATE abcdef123456")
            self.assertEqual(await host.recv(), "READY")
            async with connect(self.url) as guest:
                await guest.send("JOIN abcdef123456")
                self.assertEqual(await guest.recv(), "JOINED")
                self.assertEqual(await host.recv(), "PEER")
                await guest.send('{"protocol":7,"type":"hello"}\n')
                self.assertEqual(await host.recv(), '{"protocol":7,"type":"hello"}\n')
                await host.send('{"protocol":7,"type":"welcome"}\n')
                self.assertEqual(await guest.recv(), '{"protocol":7,"type":"welcome"}\n')
                await guest.send('{"type":"deckoffer","deckJson":"PRIVATE"}\n')
                self.assertIn('PRIVATE', await host.recv())
            await asyncio.wait_for(host.wait_closed(), 3)
        self.assertFalse(self.relay.rooms)

    async def test_unknown_room_and_bad_code(self):
        async with connect(self.url) as client:
            await client.send("JOIN aaaaaaaaaaaa")
            self.assertEqual(await client.recv(), "ERROR ROOM_UNAVAILABLE")
        async with connect(self.url) as client:
            await client.send("JOIN bad")
            self.assertEqual(await client.recv(), "ERROR BAD_REQUEST")

    async def test_room_collision_and_second_guest(self):
        async with connect(self.url) as host:
            await host.send("CREATE abcdef123456")
            self.assertEqual(await host.recv(), "READY")
            async with connect(self.url) as copy:
                await copy.send("CREATE abcdef123456")
                self.assertEqual(await copy.recv(), "ERROR ROOM_EXISTS")
            async with connect(self.url) as guest:
                await guest.send("JOIN abcdef123456")
                self.assertEqual(await guest.recv(), "JOINED")
                self.assertEqual(await host.recv(), "PEER")
                async with connect(self.url) as another:
                    await another.send("JOIN abcdef123456")
                    self.assertEqual(await another.recv(), "ERROR ROOM_UNAVAILABLE")

    async def test_reject_binary_and_oversized(self):
        async with connect(self.url) as host:
            await host.send("CREATE abcdef123456")
            self.assertEqual(await host.recv(), "READY")
            async with connect(self.url) as guest:
                await guest.send("JOIN abcdef123456")
                self.assertEqual(await guest.recv(), "JOINED")
                self.assertEqual(await host.recv(), "PEER")
                await guest.send(b"not text")
                await asyncio.wait_for(host.wait_closed(), 3)

    async def test_host_disconnect_removes_unpaired_room(self):
        async with connect(self.url) as host:
            await host.send("CREATE abcdef123456")
            self.assertEqual(await host.recv(), "READY")
        await asyncio.sleep(0.05)
        self.assertFalse(self.relay.rooms)

    async def test_health_endpoint_is_not_game_channel(self):
        async with connect(f"{self.url}oops") as ws:
            await ws.wait_closed()
            self.assertEqual(ws.close_code, 1008)


if __name__ == "__main__":
    unittest.main()
