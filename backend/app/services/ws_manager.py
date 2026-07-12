import asyncio
from collections import defaultdict


class _WSManager:
    def __init__(self):
        self._queues: dict[int, list] = defaultdict(list)

    def subscribe(self, book_id: int) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues[book_id].append(q)
        return q

    def unsubscribe(self, book_id: int, q: asyncio.Queue):
        try:
            self._queues[book_id].remove(q)
        except ValueError:
            pass

    def publish(self, book_id: int, data: dict, loop: asyncio.AbstractEventLoop):
        """Called from the sync generator thread to push events to async WS clients."""
        for q in list(self._queues.get(book_id, [])):
            loop.call_soon_threadsafe(q.put_nowait, data)


manager = _WSManager()
