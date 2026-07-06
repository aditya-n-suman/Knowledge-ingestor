import pytest_asyncio

from knowledge_ingestor.core import session, throttle


@pytest_asyncio.fixture(autouse=True)
async def _reset_client():
    yield
    await session.close_client()
    throttle.reset()
