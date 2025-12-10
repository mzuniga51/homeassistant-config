# Start of code to paste
import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Dict, Optional

import aiohttp

_LOGGER = logging.getLogger(__name__ )

class HomeAssistantClient:
    def __init__(self, websocket_url: str, token: str):
        self.websocket_url = websocket_url
        self.token = token
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.msg_id = 1
        self.msg_callbacks: Dict[int, asyncio.Future] = {}

    async def __aenter__(self ):
        self.session = aiohttp.ClientSession( )
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        if self.session:
            await self.session.close()

    async def connect(self):
        _LOGGER.debug("Connecting to %s", self.websocket_url)
        self.ws = await self.session.ws_connect(self.websocket_url)
        
        # Authenticate
        auth_msg = await self.ws.receive_json()
        if auth_msg.get("type") != "auth_required":
            raise ConnectionError(f"Expected auth_required, got: {auth_msg}")

        await self.ws.send_json({"type": "auth", "access_token": self.token})
        
        auth_ok_msg = await self.ws.receive_json()
        if auth_ok_msg.get("type") != "auth_ok":
            raise ConnectionError(f"Authentication failed: {auth_ok_msg}")
        
        _LOGGER.debug("Authentication successful")
        asyncio.create_task(self._reader())

    async def disconnect(self):
        if self.ws:
            await self.ws.close()
        _LOGGER.debug("Disconnected")

    async def send_command(self, command_type: str, params: Dict[str, Any] = None) -> Any:
        if not self.ws:
            raise ConnectionError("Not connected")

        command_id = self.msg_id
        self.msg_id += 1
        
        future = asyncio.get_running_loop().create_future()
        self.msg_callbacks[command_id] = future
        
        message = {"id": command_id, "type": command_type}
        if params:
            message.update(params)
        
        await self.ws.send_json(message)
        
        return await future

    async def _reader(self):
        while self.ws and not self.ws.closed:
            try:
                msg = await self.ws.receive_json()
                msg_id = msg.get("id")
                if msg_id in self.msg_callbacks:
                    future = self.msg_callbacks.pop(msg_id)
                    if msg.get("success"):
                        future.set_result(msg.get("result"))
                    else:
                        future.set_exception(RuntimeError(msg.get("error")))
            except aiohttp.ClientError as e:
                _LOGGER.debug("Connection error in reader: %s", e )
                break
            except Exception as e:
                _LOGGER.error("Unexpected error in reader: %s", e)
                break
# End of code to paste
