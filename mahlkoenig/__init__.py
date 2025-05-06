import asyncio
import itertools
import json
import logging
from urllib.parse import urljoin
from contextlib import suppress
from datetime import timedelta
from types import TracebackType
from typing import Any, Dict, Final, Self

import aiohttp
from pydantic.networks import AnyHttpUrl

from .exceptions import AuthenticationError, ProtocolError
from .models import (
    AutoSleepMessage,
    AutoSleepTimePreset,
    LoginRequest,
    MachineInfo,
    MachineInfoMessage,
    MessageType,
    Recipe,
    RecipeMessage,
    RequestMessage,
    ResponseMessage,
    ResponseStatusMessage,
    SetAutoSleepTimeRequest,
    SimpleRequest,
    Statistics,
    SystemStatus,
    SystemStatusMessage,
    WifiInfo,
    WifiInfoMessage,
    parse,
    parse_statistics,
)

_LOGGER: Final = logging.getLogger(__name__)


class Grinder:
    """Asynchronous WebSocket client for the Mahlkönig X54 grinder."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9998,
        password: str = "",
        *,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._ws_url: Final = str(AnyHttpUrl(f"http://{host}:{port}"))
        self._http_url: Final = str(AnyHttpUrl(f"http://{host}"))
        self._password: Final = password
        self._session_external: Final = session
        self._session: Final = session or aiohttp.ClientSession()

        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._receiver_task: asyncio.Task[None] | None = None
        self._connected = asyncio.Event()

        self._msg_id_iter: Final = itertools.count(1)
        self._session_id: int = 1
        self._pending: Dict[int, asyncio.Future[ResponseMessage]] = {}

        self._machine_info: MachineInfo | None = None
        self._wifi_info: WifiInfo | None = None
        self._system_status: SystemStatus | None = None
        self._auto_sleep_time: timedelta | None = None
        self._recipes: Dict[int, Recipe] = {}
        self._statistics: Statistics | None = None

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    # --------------------------------------------------------------------- public API

    @property
    def machine_info(self) -> MachineInfo | None:  # noqa: D401
        """Most recent `MachineInfo` payload."""
        return self._machine_info

    @property
    def wifi_info(self) -> WifiInfo | None:  # noqa: D401
        """Most recent `WifiInfo` payload."""
        return self._wifi_info

    @property
    def system_status(self) -> SystemStatus | None:  # noqa: D401
        """Most recent `SystemStatus` payload."""
        return self._system_status

    @property
    def statistics(self) -> Statistics | None:  # noqa: D401
        """Most recent `Statistics` payload."""
        return self._statistics

    @property
    def recipes(self) -> Dict[int, Recipe]:  # noqa: D401
        """Cached grinder recipes indexed by recipe number."""
        return self._recipes.copy()

    @property
    def auto_sleep_time(self) -> AutoSleepTimePreset:  # noqa: D401
        """Cached grinder recipes indexed by recipe number."""
        return self._auto_sleep_time

    @property
    def connected(self) -> bool:
        """Shows if Client is connected"""
        return self._connected.is_set()

    async def connect(self) -> None:
        """Open WebSocket connection and authenticate (idempotent)."""
        try:
            if self._ws and not self._ws.closed:
                return
            self._ws = await self._session.ws_connect(self._ws_url)
            self._receiver_task = asyncio.create_task(
                self._recv_loop(), name="x54-recv"
            )
            await self._login()
        except aiohttp.ClientConnectorError as err:
            raise ConnectionError(f"Failed to connect to grinder: {err}") from err
        except (
            asyncio.TimeoutError,
            aiohttp.SocketTimeoutError,
            aiohttp.ServerTimeoutError,
        ) as err:
            raise ConnectionError("Connection to grinder timed out") from err

    async def close(self) -> None:
        """Terminate background task and close owned resources."""
        if self._receiver_task:
            self._receiver_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._receiver_task
            self._receiver_task = None

        if self._ws and not self._ws.closed:
            await self._ws.close()
        self._ws = None
        self._connected.clear()

        if not self._session_external:
            await self._session.close()

    async def request_machine_info(self) -> MachineInfo:
        """Fetch and return the current `MachineInfo` from the grinder."""
        await self._connected.wait()
        await self._request(SimpleRequest(request_type=MessageType.MachineInfo))
        return self.machine_info

    async def request_wifi_info(self) -> WifiInfo:
        """Fetch and return the current `WifiInfo` from the grinder."""
        await self._connected.wait()
        await self._request(SimpleRequest(request_type=MessageType.WifiInfo))
        return self.wifi_info

    async def request_system_status(self) -> SystemStatus:
        """Fetch and return the current `SystemStatus` from the grinder."""
        await self._connected.wait()
        await self._request(SimpleRequest(request_type=MessageType.SystemStatus))
        return self.system_status

    async def request_recipe_list(self) -> Dict[int, Recipe]:
        """Fetch and cache the current recipe list, then return it."""
        # TODO: move wait to _request() but find way to use _request() also for login
        await self._connected.wait()
        await self._request(SimpleRequest(request_type=MessageType.RecipeList))
        return self.recipes

    async def request_auto_sleep_time(self) -> AutoSleepTimePreset:
        """Fetch and return the current auto-sleep setting."""
        await self._connected.wait()
        await self._request(SimpleRequest(request_type=MessageType.AutoSleepTime))
        return self.auto_sleep_time

    async def set_auto_sleep_time(
        self, preset: AutoSleepTimePreset
    ) -> AutoSleepTimePreset:
        """Set a new auto-sleep setting."""
        await self._connected.wait()
        await self._request(SetAutoSleepTimeRequest(auto_sleep_time=preset))
        return self.auto_sleep_time

    async def request_statistics(self) -> Statistics:
        await self._connected.wait()
        # WARNING: this http server expects the params in this order!
        async with self._session.get(
            urljoin(self._http_url, "info"),
            params={"raw_statistics": "", "id": self._session_id},
        ) as resp:
            body = await resp.text()
            stats = parse_statistics(body)

            self._statistics = stats
            return self.statistics

    # --------------------------------------------------------------------- internal helpers

    async def _login(self) -> None:
        await self._request(LoginRequest(login=self._password))
        try:
            await asyncio.wait_for(self._connected.wait(), timeout=5)
        except asyncio.TimeoutError as err:
            raise AuthenticationError("Grinder login timed out") from err

    async def _request(self, request: RequestMessage) -> ResponseMessage:
        msg_id = await self._send(request)
        fut: asyncio.Future[ResponseMessage] = (
            asyncio.get_running_loop().create_future()
        )
        self._pending[msg_id] = fut
        return await fut

    async def _send(self, request: RequestMessage) -> int:
        if not self._ws or self._ws.closed:
            raise RuntimeError("WebSocket not connected")

        msg_id = next(self._msg_id_iter)
        request.msg_id = msg_id
        request.session_id = self._session_id

        payload = request.model_dump(by_alias=True)
        await self._ws.send_json(payload)
        return msg_id

    async def _recv_loop(self) -> None:  # noqa: C901
        async for msg in self._ws:
            if msg.type is not aiohttp.WSMsgType.TEXT:
                continue
            try:
                raw: Dict[str, Any] = msg.json()
                parsed = parse(raw)
            except (json.JSONDecodeError, ProtocolError):
                _LOGGER.warning(f"Ignoring malformed frame: {msg.data}")
                continue
            except Exception:
                _LOGGER.exception("Unexpected error while parsing frame", exc_info=True)
                continue

            self._dispatch(parsed)
            await self._fulfil_pending(parsed)

    def _dispatch(self, message: ResponseMessage) -> None:
        match message:
            case ResponseStatusMessage():
                if message.response_status.source_message == MessageType.Login:
                    if message.response_status.success:
                        self._connected.set()
                        self._session_id = message.session_id
                    else:
                        raise AuthenticationError(message.response_status.reason)
            case MachineInfoMessage():
                self._machine_info = message.machine_info
            case WifiInfoMessage():
                self._wifi_info = message.wifi_info
            case SystemStatusMessage():
                self._system_status = message.system_status
            case AutoSleepMessage():
                self._auto_sleep_time = message.auto_sleep_time
            case RecipeMessage():
                self._recipes[message.recipe.recipe_no] = message.recipe
            case _:
                pass

    async def _fulfil_pending(self, message: ResponseMessage) -> None:
        if fut := self._pending.pop(message.msg_id, None):
            if not fut.done():
                fut.set_result(message)
