"""System 3 — OpenLife / Sophia / OpenSkill / CADVP persistence layer.

Papers:
  - OpenLife   arXiv:2606.31046
  - Sophia     arXiv:2512.18202
  - OpenSkill  arXiv:2606.06741
  - Channel Fracture / CADVP  arXiv:2606.04896
"""

from robin_igris.system3.budget import Metabolism
from robin_igris.system3.cadvp import Channel, DeliveryBus, DeliveryReceipt
from robin_igris.system3.heartbeat import Heartbeat, IntrinsicDrive
from robin_igris.system3.journal import GrowthJournal
from robin_igris.system3.monitor import ExecutiveMonitor
from robin_igris.system3.skills import SkillBootstrap

__all__ = [
    "Metabolism",
    "Heartbeat",
    "IntrinsicDrive",
    "GrowthJournal",
    "ExecutiveMonitor",
    "SkillBootstrap",
    "Channel",
    "DeliveryBus",
    "DeliveryReceipt",
]
