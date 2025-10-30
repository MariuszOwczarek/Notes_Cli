from notes.ports.task_repository import TaskRepository
from notes.domain.task import Task, TaskId
from notes.domain.errors import TaskAlreadyExistsError, TaskNotFoundError, TaskValidationError, DomainError
from pathlib import Path
from typing import Iterable
from dataclasses import asdict
import os, json
from notes.domain.enums import TaskStatus
from datetime import datetime, timezone

ALLOWED = {"Open", "In Progress", "Closed"}

def _encode_task(task: Task) -> dict:
    return {
        "task_id": str(task.task_id),
        "title": task.title,
        "description": task.description,
        "created_at": task.created_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": task.status.value if isinstance(task.status, TaskStatus) else str(task.status),  # enum -> str
    }

def _decode_task(row: dict) -> Task:
    raw = row.get("status", "Open")
    try:
        status = raw if isinstance(raw, TaskStatus) else TaskStatus(raw)  # str -> enum
    except ValueError:
        status = TaskStatus.OPEN  # defensywny fallback

    return Task(
        task_id=TaskId(row["task_id"]),
        title=row["title"],
        description=row.get("description"),
        created_at=_parse_utc_z(row["created_at"]),  # jak masz z L2
        status=status,
    )

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
        tasks: dict[str, Task] = {}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as e:
                        raise TaskValidationError(f"{self.path.name}:{lineno}: invalid JSON: {e}")

                    try:
                        task = _decode_task(record)
                    except (KeyError, ValueError) as e:
                        raise TaskValidationError("record", f"{self.path.name}:{lineno}: {e}")

                    key = str(task.task_id)  # klucz zawsze jako string
                    if key in tasks:
                        raise TaskValidationError("record", f"{self.path.name}:{lineno}: duplicate task_id '{key}'")
                    tasks[key] = task
        except FileNotFoundError:
            return {}
        except OSError as e:
            raise DomainError(str(e))
        return tasks



    def _atomic_dump(self, tasks: Iterable[Task]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".swap")
        try:
            with tmp.open("w", encoding="utf-8", newline="\n") as f:
                for t in tasks:
                    rec = _encode_task(t)  # enum -> str, TaskId -> str, datetime -> Z
                    f.write(json.dumps(rec, ensure_ascii=False))
                    f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        except OSError as e:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
            raise DomainError(str(e))

    def add(self, task: Task) -> None:
        """Dodaje nowy Task do repozytorium.
        Rzuca TaskAlreadyExistsError, jeśli task_id już istnieje.
        Zapisuje dane w sposób atomowy."""

        tasks = self._load_tasks()
        key = str(task.task_id)
        if key in tasks:
            raise TaskAlreadyExistsError(task.task_id)
        tasks[key] = task
        self._atomic_dump(tasks.values())


    def get(self, task_id: TaskId) -> Task:
        """Zwraca Task o podanym ID.
        Rzuca TaskNotFoundError, jeśli nie istnieje."""

        task = self._load_tasks().get(str(task_id))
        if task is None:
            raise TaskNotFoundError(task_id)
        return task


    def update(self, task: Task) -> None:
        """Aktualizuje istniejący Task w repozytorium."""

        tasks = self._load_tasks()
        key = str(task.task_id)
        if key not in tasks:
            raise TaskNotFoundError(task.task_id)
        tasks[key] = task
        self._atomic_dump(tasks.values())


    def remove(self, task_id: TaskId) -> None:
        """Usuwa Task o podanym ID.
        Rzuca TaskNotFoundError, jeśli nie istnieje.
        Zapis wykonywany atomowo."""

        tasks = self._load_tasks()
        key = str(task_id)
        if key not in tasks:
            raise TaskNotFoundError(task_id)
        del tasks[key]
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
        return str(task_id) in self._load_tasks()