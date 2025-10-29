from notes.ports.task_repository import TaskRepository
from notes.domain.task import Task, TaskId
from notes.domain.errors import TaskAlreadyExistsError, TaskNotFoundError, TaskValidationError, DomainError
from pathlib import Path
from typing import Iterable
from dataclasses import asdict
from datetime import datetime, timezone
import os, json

from datetime import datetime, timezone

ALLOWED = {"Open", "In Progress", "Closed"}

def _parse_utc_z(s: str) -> datetime:
    """Parsuje datę w formacie ISO8601 zakończoną literą 'Z' (UTC)."""
    if not isinstance(s, str) or not s.endswith("Z"):
        raise ValueError("created_at must be ISO8601 UTC with 'Z'")
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    

class JsonlTaskRepository(TaskRepository):
    def __init__(self, path: Path) -> None:
        """Inicjalizuje repozytorium JSONL.
        Tworzy katalog nadrzędny dla pliku, jeśli nie istnieje."""
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)


    def _load_tasks(self) -> dict[str, Task]:
        """Wczytuje wszystkie Taski z pliku JSONL.
        Zwraca słownik {task_id: Task}.
        Ignoruje puste linie.
        Rzuca TaskValidationError przy błędnym rekordzie
        i DomainError przy problemach I/O (poza FileNotFoundError)."""

        tasks: dict[str, Task] = {}

        try:
            with self.path.open("r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue  # pomiń puste linie

                    try:
                        record = json.loads(line)  # zamienia tekst JSON → dict
                    except json.JSONDecodeError as e:
                        raise TaskValidationError(
                            f"{self.path.name}:{lineno}: invalid JSON: {e}"
                        )
                    try:
                        task_id = record["task_id"]
                        title = record["title"]
                        description = record.get("description")
                        created_at = _parse_utc_z(record["created_at"])
                        status = record["status"]
                        if status not in ALLOWED:
                            raise ValueError(f"status '{status}' is not allowed")
                    except KeyError as e:
                        raise TaskValidationError("record", f"{self.path.name}:{lineno}: missing field {e!s}")
                    except ValueError as e:
                        raise TaskValidationError("record", f"{self.path.name}:{lineno}: {e}")

                    if task_id in tasks:
                        raise TaskValidationError("record", f"{self.path.name}:{lineno}: duplicate task_id '{task_id}'")

                    task = Task(
                        task_id=task_id,
                        title=title,
                        description=description,
                        created_at=created_at,
                        status=status,
                    )
                    tasks[task_id] = task

        except FileNotFoundError:
            # brak pliku = pusta baza
            return {}

        except OSError as e:
            # inne błędy systemowe
            raise DomainError(str(e))

        return tasks


    def _atomic_dump(self, tasks: Iterable[Task]) -> None:
        """Zapisuje cały zbiór Tasków do pliku JSONL w sposób atomowy.

        Strategia: zapisz do pliku tymczasowego obok (*.swap), fsync, a potem os.replace()
        na docelowy plik. Dzięki temu po awarii mamy *albo* starą, *albo* nową wersję.
        """
        tmp = self.path.with_suffix(self.path.suffix + ".swap")
        try:
            with tmp.open("w", encoding="utf-8", newline="\n") as f:
                for t in tasks:
                    rec = self._task_to_record(t)
                    f.write(json.dumps(rec, ensure_ascii=False))
                    f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)  # atomowa podmiana
        except OSError as e:
            # sprzątanie po nieudanym zapisie (nie maskuje błędu)
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
            raise DomainError(str(e))

    @staticmethod
    def _format_dt(dt: datetime) -> str:
        # ISO 8601 w UTC z sufiksem 'Z'
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _task_to_record(self, t: Task) -> dict:
        d = asdict(t)              # bo Task to dataclass (frozen) z Level 1
        d["created_at"] = self._format_dt(t.created_at)
        return d

    def add(self, task: Task) -> None:
        """Dodaje nowy Task do repozytorium.
        Rzuca TaskAlreadyExistsError, jeśli task_id już istnieje.
        Zapisuje dane w sposób atomowy."""

        tasks = self._load_tasks()
        if task.task_id in tasks:
            raise TaskAlreadyExistsError(task.task_id)
        tasks[task.task_id] = task
        self._atomic_dump(tasks.values())


    def get(self, task_id: TaskId) -> Task:
        """Zwraca Task o podanym ID.
        Rzuca TaskNotFoundError, jeśli nie istnieje."""

        task = self._load_tasks().get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return task

    def update(self, task: Task) -> None:
        """Aktualizuje istniejący Task w repozytorium."""

        tasks = self._load_tasks()
        if task.task_id not in tasks:
            raise TaskNotFoundError(task.task_id)
        tasks[task.task_id] = task
        self._atomic_dump(tasks.values())

    def remove(self, task_id: TaskId) -> None:
        """Usuwa Task o podanym ID.
        Rzuca TaskNotFoundError, jeśli nie istnieje.
        Zapis wykonywany atomowo."""

        tasks = self._load_tasks()
        if task_id not in tasks:
            raise TaskNotFoundError(task_id)
        del tasks[task_id]
        self._atomic_dump(tasks.values())

    def list_all(self, offset: int = 0, limit: int | None = None) -> Iterable[Task]:
        """Zwraca listę Tasków posortowaną rosnąco po created_at,
        z tiebreakerem po task_id. Następnie stosuje paginację offset/limit."""
        tasks = list(self._load_tasks().values())

        # sort → (created_at ASC, task_id ASC)
        tasks.sort(key=lambda t: (t.created_at, t.task_id))

        # normalizacja parametrów
        start = max(0, int(offset))
        if limit is None:
            return tasks[start:]
        if limit <= 0:
            return []

        end = start + int(limit)
        return tasks[start:end]


    def count_all(self) -> int:
        """Zwraca liczbę wszystkich Tasków w repozytorium."""
        tasks = self._load_tasks()
        return len(tasks)

    def exists(self, task_id: TaskId) -> bool:
        """Zwraca True, jeśli istnieje zadanie o podanym ID."""
        tasks = self._load_tasks()
        return task_id in tasks