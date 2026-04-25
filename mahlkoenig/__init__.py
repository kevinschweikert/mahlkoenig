import asyncio
import itertools
import json
import logging
from urllib.parse import urljoin
from contextlib import suppress
from datetime import timedelta
from types import TracebackType
from typing import Any, Final, Self

import aiohttp
from pydantic.networks import AnyHttpUrl

from .exceptions import (
    MahlkoenigAuthenticationError,
    MahlkoenigProtocolError,
    MahlkoenigConnectionError,
    MahlkoenigTimeoutError,
)
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

_DEFAULT_REQUEST_TIMEOUT: Final = timedelta(seconds=10)
_DEFAULT_LOGIN_TIMEOUT: Final = timedelta(seconds=5)


class Grinder:
    """Asynchronous WebSocket client for the Mahlkönig X54 grinder."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9998,
        password: str = "",
        *,
        session: aiohttp.ClientSession | None = None,
        request_timeout: timedelta = _DEFAULT_REQUEST_TIMEOUT,
    ) -> None:
        # mDNS / zeroconf often returns hostnames with a trailing dot;
        # strip it so the pydantic URL validator below accepts the host.
        host = host.rstrip(".")
        # Validate host & port via pydantic. Raises ValidationError on
        # malformed input (bad chars, port out of range, etc.).
        AnyHttpUrl(f"http://{host}:{port}")
        self._ws_url: Final = f"ws://{host}:{port}"
        self._http_url: Final = f"http://{host}"
        self._password: Final = password
        self._session_external: Final = session
        self._session: aiohttp.ClientSession | None = session
        self._request_timeout: Final = request_timeout

        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._receiver_task: asyncio.Task[None] | None = None
        self._connected = asyncio.Event()

        self._msg_id_iter: Final = itertools.count(1)
        self._session_id: int = 1
        self._pending: dict[int, asyncio.Future[ResponseMessage]] = {}

        self._machine_info: MachineInfo | None = None
        self._wifi_info: WifiInfo | None = None
        self._system_status: SystemStatus | None = None
        self._auto_sleep_time: AutoSleepTimePreset | None = None
        self._recipes: dict[int, Recipe] = {}
        self._statistics: Statistics | None = None

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        await self.close()

    # --------------------------------------------------------------------- public API

    @property
    def machine_info(self) -> MachineInfo | None:
        """Most recent `MachineInfo` payload."""
        return self._machine_info

    @property
    def wifi_info(self) -> WifiInfo | None:
        """Most recent `WifiInfo` payload."""
        return self._wifi_info

    @property
    def system_status(self) -> SystemStatus | None:
        """Most recent `SystemStatus` payload."""
        return self._system_status

    @property
    def statistics(self) -> Statistics | None:
        """Most recent `Statistics` payload."""
        return self._statistics

    @property
    def recipes(self) -> dict[int, Recipe]:
        """Cached grinder recipes indexed by recipe number."""
        return self._recipes.copy()

    @property
    def auto_sleep_time(self) -> AutoSleepTimePreset | None:
        """Most recent auto-sleep preset."""
        return self._auto_sleep_time

    @property
    def connected(self) -> bool:
        """Whether the client is connected and authenticated."""
        return self._connected.is_set()

    async def connect(self) -> None:
        """Open WebSocket connection and authenticate (idempotent)."""
        if self._ws and not self._ws.closed:
            return

        if self._session is None:
            self._session = aiohttp.ClientSession()

        try:
            self._ws = await self._session.ws_connect(self._ws_url)
        except aiohttp.ClientConnectorError as err:
            raise MahlkoenigConnectionError(
                f"Failed to connect to grinder: {err}"
            ) from err
        except (
            asyncio.TimeoutError,
            aiohttp.SocketTimeoutError,
            aiohttp.ServerTimeoutError,
        ) as err:
            raise MahlkoenigConnectionError("Connection to grinder timed out") from err

        self._receiver_task = asyncio.create_task(self._recv_loop(), name="x54-recv")
        try:
            await self._login()
        except BaseException:
            await self.close()
            raise

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

        self._fail_pending(MahlkoenigConnectionError("Connection closed"))

        if self._session is not None and self._session_external is None:
            await self._session.close()
            self._session = None

    async def request_machine_info(self) -> MachineInfo | None:
        """Fetch and return the current `MachineInfo` from the grinder."""
        await self._request(SimpleRequest(request_type=MessageType.MachineInfo))
        return self.machine_info

    async def request_wifi_info(self) -> WifiInfo | None:
        """Fetch and return the current `WifiInfo` from the grinder."""
        await self._request(SimpleRequest(request_type=MessageType.WifiInfo))
        return self.wifi_info

    async def request_system_status(self) -> SystemStatus | None:
        """Fetch and return the current `SystemStatus` from the grinder."""
        await self._request(SimpleRequest(request_type=MessageType.SystemStatus))
        return self.system_status

    async def request_recipe_list(self) -> dict[int, Recipe]:
        """Fetch and cache the current recipe list, then return it."""
        self._recipes.clear()
        await self._request(SimpleRequest(request_type=MessageType.RecipeList))
        return self.recipes

    async def request_auto_sleep_time(self) -> AutoSleepTimePreset | None:
        """Fetch and return the current auto-sleep setting."""
        await self._request(SimpleRequest(request_type=MessageType.AutoSleepTime))
        return self.auto_sleep_time

    async def set_auto_sleep_time(
        self, preset: AutoSleepTimePreset
    ) -> AutoSleepTimePreset | None:
        """Set a new auto-sleep setting."""
        await self._request(SetAutoSleepTimeRequest(auto_sleep_time=preset))
        return self.auto_sleep_time

    async def request_statistics(self) -> Statistics:
        """Fetch and return raw statistics over HTTP."""
        if self._session is None:
            raise MahlkoenigConnectionError("Session not initialised")
        # WARNING: this http server expects the params in this order!
        async with self._session.get(
            urljoin(self._http_url, "info"),
            params={"raw_statistics": "", "id": self._session_id},
        ) as resp:
            if resp.status >= 400:
                raise MahlkoenigConnectionError(
                    f"Statistics request failed with HTTP {resp.status}"
                )
            body = await resp.text()
        stats = parse_statistics(body)
        self._statistics = stats
        return stats

    # --------------------------------------------------------------------- internal helpers

    async def _login(self) -> None:
        try:
            await self._request(
                LoginRequest(login=self._password),
                timeout=_DEFAULT_LOGIN_TIMEOUT,
            )
        except MahlkoenigTimeoutError as err:
            raise MahlkoenigAuthenticationError("Grinder login timed out") from err

    async def _request(
        self,
        request: RequestMessage,
        *,
        timeout: timedelta | None = None,
    ) -> ResponseMessage:
        msg_id = await self._send(request)
        fut: asyncio.Future[ResponseMessage] = (
            asyncio.get_running_loop().create_future()
        )
        self._pending[msg_id] = fut
        effective_timeout = timeout if timeout is not None else self._request_timeout
        try:
            return await asyncio.wait_for(
                fut, timeout=effective_timeout.total_seconds()
            )
        except asyncio.TimeoutError as err:
            raise MahlkoenigTimeoutError(
                f"Request {type(request).__name__} timed out"
            ) from err
        finally:
            self._pending.pop(msg_id, None)

    async def _send(self, request: RequestMessage) -> int:
        if not self._ws or self._ws.closed:
            raise MahlkoenigConnectionError("WebSocket not connected")

        msg_id = next(self._msg_id_iter)
        outgoing = request.model_copy(
            update={"msg_id": msg_id, "session_id": self._session_id}
        )
        payload = outgoing.model_dump(by_alias=True)
        await self._ws.send_json(payload)
        return msg_id

    async def _recv_loop(self) -> None:
        try:
            assert self._ws is not None
            async for msg in self._ws:
                if msg.type is not aiohttp.WSMsgType.TEXT:
                    continue
                try:
                    raw: dict[str, Any] = msg.json()
                    parsed = parse(raw)
                except json.JSONDecodeError:
                    _LOGGER.warning("Invalid JSON received: %s", msg.data)
                    continue
                except MahlkoenigProtocolError:
                    _LOGGER.error("Malformed frame: %s", msg.data)
                    continue
                except Exception:
                    _LOGGER.exception("Unexpected error while parsing frame")
                    continue

                self._update_cache(parsed)
                self._resolve_pending(parsed)
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Receive loop terminated unexpectedly")
        finally:
            self._connected.clear()
            self._fail_pending(MahlkoenigConnectionError("Connection lost"))

    def _update_cache(self, message: ResponseMessage) -> None:
        match message:
            case ResponseStatusMessage():
                if (
                    message.response_status.source_message == MessageType.Login
                    and message.response_status.success
                ):
                    self._connected.set()
                    self._session_id = message.session_id
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

    def _resolve_pending(self, message: ResponseMessage) -> None:
        fut = self._pending.pop(message.msg_id, None)
        if fut is None or fut.done():
            return
        if (
            isinstance(message, ResponseStatusMessage)
            and not message.response_status.success
        ):
            if message.response_status.source_message == MessageType.Login:
                fut.set_exception(
                    MahlkoenigAuthenticationError(message.response_status.reason)
                )
            else:
                fut.set_exception(
                    MahlkoenigProtocolError(
                        f"Request failed: {message.response_status.reason}",
                        data=message.model_dump(),
                    )
                )
        else:
            fut.set_result(message)

    def _fail_pending(self, exc: BaseException) -> None:
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(exc)
        self._pending.clear()
