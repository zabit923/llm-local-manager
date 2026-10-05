import asyncio

import pytest

from src.application.agent.conversation.sessions import InMemorySessionStore


@pytest.mark.asyncio
async def test_concurrent_turns_enter_serially():
    store = InMemorySessionStore()
    first_inside = asyncio.Event()
    release = asyncio.Event()
    sequence = []

    async def first():
        async with store.lease("call") as state:
            sequence.append("first")
            state.branch = "Ермошкина"
            first_inside.set()
            await release.wait()
            store.remove("call")

    async def second():
        await first_inside.wait()
        async with store.lease("call") as state:
            sequence.append("second")
            assert state.branch is None
            state.branch = "Центральная"

    tasks = [asyncio.create_task(first()), asyncio.create_task(second())]
    await first_inside.wait()
    await asyncio.sleep(0)
    assert sequence == ["first"]
    release.set()
    await asyncio.gather(*tasks)
    assert sequence == ["first", "second"]
    assert store.get("call").branch == "Центральная"


@pytest.mark.asyncio
async def test_exception_releases_session_lease():
    store = InMemorySessionStore()
    with pytest.raises(ValueError):
        async with store.lease("call"):
            raise ValueError("test")
    async with store.lease("call") as state:
        assert state.lines == []
