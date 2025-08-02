import abc

# ==============================================================================
# Support GRAMPS API translations
# ==============================================================================
from gramps.gen.plug import Gramplet
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.get_addon_translator(__file__).gettext

# ==============================================================================
# Interface and Logic Classes
# ==============================================================================
class IChatLogic(abc.ABC):
    """
    Abstract base class (interface) for chat logic.
    Any class that processes a message and returns a reply must implement this.
    """
    @abc.abstractmethod
    def get_reply(message: str) -> str:
        """
        Processes a user message and returns a reply string.
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

    def get_reply(message: str) -> str:
        """
        Processes the message and returns a reply.
        In this initial version, it simply reverses the input text.
        """
        return _("Tree: '{}'").format(message[::-1])
