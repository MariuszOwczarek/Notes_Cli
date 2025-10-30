from typing import Protocol
from datetime import datetime

class Clock(Protocol):
    """Abstrakcja źródła czasu. Zwraca czas w strefie UTC (aware)."""
    def now(self) -> datetime:
        pass