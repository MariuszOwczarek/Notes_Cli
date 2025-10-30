from enum import Enum

class TaskColor(Enum):
    RED = "[red]"
    BLUE = "[blue]"
    GREEN = "[green]"
    RESET = "[/]"

    def __str__(self):
        return self.value