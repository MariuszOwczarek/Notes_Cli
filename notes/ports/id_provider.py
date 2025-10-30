from typing import Protocol

class IdProvider(Protocol):
    """Port odpowiedzialny za generowanie unikalnych identyfikatorów."""
    def new_id(self) -> str:
        pass