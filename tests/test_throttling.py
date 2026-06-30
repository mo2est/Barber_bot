"""Тесты ThrottlingMiddleware без поднятия aiogram Dispatcher."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from bot.middlewares.throttling import ThrottlingMiddleware


@pytest.fixture
def middleware():
    return ThrottlingMiddleware()


def _user(uid: int):
    return SimpleNamespace(id=uid)


async def _call(middleware, user_id: int, calls: list[str]):
    async def handler(event, data):
        calls.append("called")
        return "handled"

    event = SimpleNamespace()
    data = {"event_from_user": _user(user_id)}
    return await middleware(handler, event, data)


async def test_first_call_passes(middleware):
    calls: list[str] = []
    result = await _call(middleware, 1, calls)
    assert result == "handled"
    assert calls == ["called"]


async def test_rapid_second_call_dropped(middleware):
    calls: list[str] = []
    await _call(middleware, 1, calls)
    result = await _call(middleware, 1, calls)
    assert result is None
    assert calls == ["called"]  # второй вызов не достиг хендлера


async def test_different_users_not_throttled(middleware):
    calls: list[str] = []
    await _call(middleware, 1, calls)
    result = await _call(middleware, 2, calls)
    assert result == "handled"
    assert calls == ["called", "called"]


async def test_call_after_window_passes(middleware):
    calls: list[str] = []
    await _call(middleware, 1, calls)
    await asyncio.sleep(0.8)  # больше THROTTLE_WINDOW_SECONDS
    result = await _call(middleware, 1, calls)
    assert result == "handled"
    assert calls == ["called", "called"]


async def test_missing_user_not_throttled(middleware):
    """Если в data нет event_from_user (служебные события) — не троттлим."""
    calls: list[str] = []

    async def handler(event, data):
        calls.append("called")
        return "ok"

    result1 = await middleware(handler, SimpleNamespace(), {})
    result2 = await middleware(handler, SimpleNamespace(), {})
    assert result1 == result2 == "ok"
    assert calls == ["called", "called"]
