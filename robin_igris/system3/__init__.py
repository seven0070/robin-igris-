"""System 3 — OpenLife / Sophia-inspired persistence layer for Robin Igris.

Papers:
  - OpenLife  arXiv:2606.31046
  - Sophia    arXiv:2512.18202
  - OpenSkill arXiv:2606.06741
"""

from robin_igris.system3.budget import Metabolism
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
]
