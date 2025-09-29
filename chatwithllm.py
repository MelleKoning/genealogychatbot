import abc
import time
from enum import Enum, auto
from typing import Iterator, Tuple

from gramps.gen.const import GRAMPS_LOCALE as glocale

# ==============================================================================
# Support GRAMPS API translations
# ==============================================================================
# from gramps.gen.plug import Gramplet

_ = glocale.get_addon_translator(__file__).gettext


class YieldType(Enum):
    PARTIAL = auto()
    TOOL_CALL = auto()
    FINAL = auto()


# ==============================================================================
# Interface and Logic Classes
# ==============================================================================
class IChatLogic(abc.ABC):
    """
    Abstract base class (interface) for chat logic.
    Any class that processes a message and returns a reply must implement this.
    """

    @abc.abstractmethod
    def get_reply(self, message: str) -> Iterator[Tuple[YieldType, str]]:
        """
        Processes a user message and returns a reply string.
        """
        pass

    @abc.abstractmethod
    def open_database(self) -> None:
        """
        Opens the Gramps database.
        """
        pass


class ChatWithLLM(IChatLogic):
    """
    This class contains the actual logic for processing the chat messages.
    It implements the IChatLogic interface.
    """

    def __init__(self):
        """
        Constructor for the chat logic class.
        In the future, this is where you would initialize the LLM or other
        resources needed to generate a reply.
        """
        # For now, it's just a simple text reversal.
        pass

    def open_database(self) -> None:
        """
        Opens the Gramps database.
        """
        pass

    def get_reply(self, message: str) -> Iterator[Tuple[YieldType, str]]:
        """
        Processes the message and yields parts of the reply.

        This example simulates a slow, iterative process by yielding
        one character at a time. In a real-world scenario, you would
        yield text as it's streamed from the LLM or as tool calls complete.
        """
        if message == "exit":
            quit()

        reversed_message = _("Tree: '{}'").format(message[::-1])

        for char in reversed_message:
            yield (YieldType.PARTIAL, char)
            time.sleep(0.05)  # Simulate a slight delay, like a real-time stream
        yield (YieldType.FINAL, reversed_message)  # final response
