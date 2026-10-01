"""Hard budget caps for agent runs (CI/batch first-class controls).

A Budget is a wall-clock and/or token ceiling shared by everything that
receives it: one per run, or one across a whole batch. When it is exhausted
the generation loop stops cleanly — the final joint evaluation still runs, so
every started target still yields a mutation score for whatever was accepted.

Zero/absent caps mean unlimited (the experiment default).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Budget:
    sec: float = 0.0        # wall-clock ceiling; 0 = unlimited
    tokens: int = 0         # LLM token ceiling (in+out); 0 = unlimited
    _t0: float = field(default_factory=time.perf_counter, repr=False)

    def elapsed(self) -> float:
        return time.perf_counter() - self._t0

    def exhausted(self, tokens_used: int = 0) -> bool:
        if self.sec and self.elapsed() >= self.sec:
            return True
        if self.tokens and tokens_used >= self.tokens:
            return True
        return False
