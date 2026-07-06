import time

from knowledge_ingestor.core import throttle


async def test_wait_for_host_is_noop_when_disabled():
    start = time.monotonic()

    await throttle.wait_for_host("https://example.com/a", 0.0, 0.0)
    await throttle.wait_for_host("https://example.com/b", 0.0, 0.0)

    assert time.monotonic() - start < 0.05


async def test_wait_for_host_spaces_out_same_host_calls():
    start = time.monotonic()

    await throttle.wait_for_host("https://example.com/a", 0.05, 0.05)
    await throttle.wait_for_host("https://example.com/b", 0.05, 0.05)
    await throttle.wait_for_host("https://example.com/c", 0.05, 0.05)

    elapsed = time.monotonic() - start
    assert elapsed >= 0.09


async def test_wait_for_host_does_not_block_different_hosts():
    start = time.monotonic()

    await throttle.wait_for_host("https://example.com/a", 0.1, 0.1)
    await throttle.wait_for_host("https://other.com/a", 0.1, 0.1)

    elapsed = time.monotonic() - start
    assert elapsed < 0.15
