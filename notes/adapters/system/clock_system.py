from notes.ports.clock import Clock
from datetime import datetime, UTC, timezone

class SystemClock(Clock):
    """Adapter systemowy korzystający z bieżącego czasu UTC."""
    
    def now(self) -> datetime:
        """Zwraca aktualny czas w strefie UTC (aware)."""
        return datetime.now(timezone.utc)