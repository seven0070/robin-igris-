from robin_igris.agent import Agent
from robin_igris.app import create_app
from robin_igris.cli import run_cli
from robin_igris.hermes_client import chat as hermes_chat
from robin_igris.hermes_client import health as hermes_health
from robin_igris.omniroute import chat_text as omniroute_chat
from robin_igris.omniroute import health as omniroute_health

__version__ = "0.3.0"
__all__ = [
    "Agent",
    "create_app",
    "run_cli",
    "hermes_chat",
    "hermes_health",
    "omniroute_chat",
    "omniroute_health",
    "__version__",
]
