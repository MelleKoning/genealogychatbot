import asyncio
import logging
import os

from gramps.gen.config import CONFIGMAN

from AsyncChatService import AsyncChatService
from chatbot import YieldType

logger = logging.getLogger("chatbot")


class ChatBotConsole:
    """
    This class contains the actual logic for processing the chat messages.
    It implements the IChatLogic interface.
    """
    def __init__(self, database_name):
        logger.debug("Initializing ChatBotConsole")
        # Encapsulate the threading logic
        self.chat_service = AsyncChatService(database_name)

    def chat_loop(self):
        # We don't need to start/stop the worker here; the service handles it
        try:
            while True:
                # SYNCHRONOUS input on the main thread (as requested)
                query = input("\n\nEnter your question: ")
                if not query:
                    break

                # Run the asynchronous processing for this single query
                try:
                    asyncio.run(self.process_query_async(query))
                except Exception as e:
                    print(f"An error occurred: {e}")
                    break
        finally:
            # Crucial: Stop the persistent worker when the app exits
            self.chat_service.stop_worker()

    async def process_query_async(self, query):
        """
        Asynchronously processes a single query and prints the replies as they come in.
        """
        # The ChatThreading service handles all the threading and queues.
        # We just iterate over the async generator it returns.
        async for reply in self.chat_service.get_reply_stream(query):
            reply_type, content = reply

            if reply_type == YieldType.PARTIAL:
                print(content, end="", flush=True)
            elif reply_type == YieldType.TOOL_CALL:
                print(" - toolcall: ", content, flush=True)
            elif reply_type == YieldType.FINAL:
                print("\n>>>", content)

    def get_gramps_database_names(self) -> list[str]:
        """
        Returns a list of available Gramps database names.
        """
        db_path = CONFIGMAN.get("database.path")
        if not os.path.isdir(db_path):
            raise Exception(f"Database path does not exist: {db_path}")
        db_names = [
            name
            for name in os.listdir(db_path)
            if os.path.isdir(os.path.join(db_path, name))
        ]
        return db_names


# overwrite the default database path in case the env variable is set
GRAMPS_DB_LOCATION = os.environ.get("GRAMPS_DB_LOCATION")

if __name__ == "__main__":
    # Get the database name from the environment variable
    database_name = os.getenv("GRAMPS_DB_NAME")
    logger.debug(f"Attempting to initialize Chatbot with database: {database_name}")
    # Use env variable if set, otherwise default to ./grampsdb below script
    if GRAMPS_DB_LOCATION:
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        # If the env var is a relative path, resolve it relative to script
        if not os.path.isabs(GRAMPS_DB_LOCATION):
            GRAMPS_DB_FOLDER = os.path.join(SCRIPT_DIR, GRAMPS_DB_LOCATION)
        else:
            GRAMPS_DB_FOLDER = GRAMPS_DB_LOCATION
        logger.debug(f"Using database folder: {GRAMPS_DB_FOLDER}")
        if not os.path.isdir(GRAMPS_DB_FOLDER):
            raise Exception(
                f"GRAMPS_DB_FOLDER path does not exist: {GRAMPS_DB_FOLDER}\n"
                f"GRAMPS_DB_LOCATION env: {GRAMPS_DB_LOCATION}"
            )
        CONFIGMAN.set("database.path", GRAMPS_DB_FOLDER)
    chatbotConsole = ChatBotConsole(database_name)
    print(chatbotConsole.get_gramps_database_names())
    chatbotConsole.chat_loop()
