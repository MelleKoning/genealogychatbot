import asyncio
import logging
import queue
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncIterator, Iterator, Optional, Tuple

from chatbot import ChatBot
from chatwithllm import YieldType

logger = logging.getLogger("AsyncChatService")

# Alias for the yielded items from the ChatBot generator
ReplyItem = Tuple[YieldType, str]


class AsyncChatService:
    """
    Manages a single-worker ThreadPoolExecutor for thread-local database access.
    """

    def __init__(self, database_name: str) -> None:
        self.chat_logic = ChatBot(database_name)

        # Create a dedicated executor pool with ONLY ONE worker thread
        self.executor: ThreadPoolExecutor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="DBWorker"
        )

        # Submit the open_database call as the first task to the single thread.
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Runs the blocking open_database() call on the worker thread."""

        def init_task() -> None:
            logger.debug("Running open_database on the dedicated worker thread.")
            self.chat_logic.open_database()

        # Blocking wait for the database to open on the worker thread.
        future = self.executor.submit(init_task)
        future.result()

    def stop_worker(self) -> None:
        """Shuts down the executor pool."""
        # Optional: Submit close_database to ensure it runs on the worker thread,
        # but needs careful handling as shutdown might be concurrent.

        # We rely on the executor's shutdown mechanism for cleanup.
        self.executor.shutdown(wait=True)

    async def get_reply_stream(self, query: str) -> AsyncIterator[ReplyItem]:
        """
        Asynchronously submits a query to the single-worker executor and yields results
        as they come back from the thread.
        """
        loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

        # Create a synchronous queue for this reply stream
        result_queue: queue.Queue[Optional[ReplyItem]] = queue.Queue()

        # Define the synchronous wrapper function that will run on the executor thread
        def generate_replies_on_worker() -> None:
            # This runs on the *single* dedicated worker thread.

            # The type hint for the generator: Iterator[ReplyItem]
            reply_iterator: Iterator[ReplyItem] = self.chat_logic.get_reply(query)

            for reply in reply_iterator:
                result_queue.put(reply)
            result_queue.put(None)  # Sentinel

        # Submit the wrapper function to the dedicated executor
        self.executor.submit(generate_replies_on_worker)

        # 4. Asynchronously read from the queue back on the main async thread
        while True:
            # We use run_in_executor to block ASYNCHRONOUSLY on the queue.
            # We hint the expected return type is Optional[ReplyItem],
            # meaning it can be ReplyItem or None.
            reply: Optional[ReplyItem] = await (
                loop.run_in_executor(None, result_queue.get)
            )
            if reply is None:  # Sentinel received
                break  # to end the async generator

            # Since reply is guaranteed not to be None here, it is a ReplyItem
            yield reply
