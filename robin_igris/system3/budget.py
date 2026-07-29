"""Budget-based metabolism (OpenLife): persistence is earned, not given."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Metabolism:
    """Track an energy/budget ledger. Exhaustion = operational death."""

    daily_allowance_usd: float = 1.0
    balance_usd: float = 5.0
    path: Path = field(default_factory=lambda: Path("data/system3/metabolism.json"))
    _day: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.load()
        self._roll_day()

    def _today(self) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime())

    def _roll_day(self) -> None:
        today = self._today()
        if self._day != today:
            self.balance_usd += self.daily_allowance_usd
            self._day = today
            self.save()

    @property
    def alive(self) -> bool:
        self._roll_day()
        return self.balance_usd > 0

    def debit(self, amount_usd: float, reason: str = "") -> bool:
        """Spend budget. Returns False if this would cause death (and does not spend)."""
        self._roll_day()
        if amount_usd <= 0:
            return True
        if self.balance_usd < amount_usd:
            return False
        self.balance_usd = round(self.balance_usd - amount_usd, 6)
        self._append_ledger(-amount_usd, reason)
        self.save()
        return True

    def credit(self, amount_usd: float, reason: str = "") -> None:
        self._roll_day()
        self.balance_usd = round(self.balance_usd + amount_usd, 6)
        self._append_ledger(amount_usd, reason)
        self.save()

    def _append_ledger(self, delta: float, reason: str) -> None:
        ledger = self.path.with_name("ledger.jsonl")
        with ledger.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "ts": time.time(),
                        "delta": delta,
                        "balance": self.balance_usd,
                        "reason": reason,
                    }
                )
                + "\n"
            )

    def load(self) -> None:
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.balance_usd = float(data.get("balance_usd", self.balance_usd))
        self.daily_allowance_usd = float(
            data.get("daily_allowance_usd", self.daily_allowance_usd)
        )
        self._day = str(data.get("day", ""))

    def save(self) -> None:
        self.path.write_text(
            json.dumps(
                {
                    "balance_usd": self.balance_usd,
                    "daily_allowance_usd": self.daily_allowance_usd,
                    "day": self._day or self._today(),
                    "alive": self.alive,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def status(self) -> dict:
        self._roll_day()
        return {
            "alive": self.alive,
            "balance_usd": self.balance_usd,
            "daily_allowance_usd": self.daily_allowance_usd,
            "day": self._day,
        }
