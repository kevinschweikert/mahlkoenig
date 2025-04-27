from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

import mahlkoenig
from mahlkoenig import (
    AutoSleepTimePreset,
    Grinder,
    MessageType,
    SetAutoSleepTimeRequest,
    SimpleRequest,
)


@pytest.fixture
async def mock_grinder():
    grinder = Grinder(
        host="localhost", port=9998, password="password", session=AsyncMock()
    )
    # pretend we are already connected
    grinder._connected.set()
    return grinder


@pytest.mark.asyncio
async def test_request_machine_info(mock_grinder):
    mock_grinder._request = AsyncMock()
    expected = SimpleRequest(request_type=MessageType.MachineInfo)
    await mock_grinder.request_machine_info()
    mock_grinder._request.assert_awaited_once_with(expected)


@pytest.mark.asyncio
async def test_request_wifi_info(mock_grinder):
    mock_grinder._request = AsyncMock()
    expected = SimpleRequest(request_type=MessageType.WifiInfo)
    await mock_grinder.request_wifi_info()
    mock_grinder._request.assert_awaited_once_with(expected)


@pytest.mark.asyncio
async def test_request_system_status(mock_grinder):
    mock_grinder._request = AsyncMock()
    expected = SimpleRequest(request_type=MessageType.SystemStatus)
    await mock_grinder.request_system_status()
    mock_grinder._request.assert_awaited_once_with(expected)


@pytest.mark.asyncio
async def test_request_recipe_list(mock_grinder):
    mock_grinder._request = AsyncMock()
    expected = SimpleRequest(request_type=MessageType.RecipeList)
    await mock_grinder.request_recipe_list()
    mock_grinder._request.assert_awaited_once_with(expected)


@pytest.mark.asyncio
async def test_request_auto_sleep_time(mock_grinder):
    mock_grinder._request = AsyncMock()
    expected = SimpleRequest(request_type=MessageType.AutoSleepTime)
    await mock_grinder.request_auto_sleep_time()
    mock_grinder._request.assert_awaited_once_with(expected)


@pytest.mark.asyncio
async def test_set_auto_sleep_time(mock_grinder):
    mock_grinder._request = AsyncMock()
    preset = AutoSleepTimePreset.MIN_10
    expected = SetAutoSleepTimeRequest(auto_sleep_time=preset)
    await mock_grinder.set_auto_sleep_time(preset)
    mock_grinder._request.assert_awaited_once_with(expected)


@pytest.mark.asyncio
async def test_request_statistics(mock_grinder, monkeypatch):
    sentinel = object()
    monkeypatch.setattr(mahlkoenig, "parse_statistics", lambda body: sentinel)

    mock_resp = AsyncMock()
    mock_resp.text = AsyncMock(return_value="raw-body")

    @asynccontextmanager
    async def fake_get(*args, **kwargs):
        yield mock_resp

    mock_grinder._session.get = fake_get

    result = await mock_grinder.request_statistics()

    assert result is sentinel
    assert mock_grinder.statistics is sentinel
