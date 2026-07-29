"""Pendrive-Native Agent Operating System (PNAOS).

The agent is the OS shell; the USB stick is home; the host is borrowed hardware.
"""

__version__ = "0.1.0"

from aos.kernel import AgentKernel
from aos.manifest import Manifest, ManifestRuntime
from aos.soul import SoulStore

__all__ = ["AgentKernel", "Manifest", "ManifestRuntime", "SoulStore", "__version__"]
