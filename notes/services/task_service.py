from notes.ports.task_repository import TaskRepository
from notes.domain.task import Task, TaskId
from notes.domain.errors import TaskValidationError, TaskNotFoundError
from uuid import uuid4
from datetime import datetime, timezone
from typing import Literal
from notes.domain.enums import TaskStatus


### COMMENTS
# ==========================================================
# Warstwa serwisowa (services/task_service.py) — przypadki użycia.
# ==========================================================
# Rola:
# - Orkiestracja logiki aplikacyjnej nad portem `TaskRepository`.
# - Walidacje danych wejściowych (np. tytuł, paginacja).
# - Tworzenie/aktualizacja obiektów domenowych (Task), bez znajomości technologii.
#
# Zasady:
# - Serwis korzysta wyłącznie z portów (repozytoriów); nie dotyka adapterów.
# - Błędy domenowe:
#     * Walidacje (np. pusty tytuł) → `TaskValidationError`.
#     * Brak wpisu przy „twardym” pobraniu/aktualizacji → `TaskNotFoundError`.
# - Paginacja: serwis liczy `offset/limit`, repo odpowiada za sort + tiebreaker + cięcie.
# - Modele domenowe są niemutowalne (`frozen=True`) — zmiana = nowa instancja i `repo.update`.



class TaskService:
    """
    Serwis przypadków użycia dla zadań (Notes/Tasks).

    :param repo: Implementacja portu TaskRepository.
    """
    def __init__(self, repo: TaskRepository) -> None:
        self.repo = repo
    
    def create_task(self, title, description=None, due_date=None) -> Task:
        """
            Tworzy nowe zadanie i zapisuje je w repozytorium.

            - Walidacja: `title` nie może być pusty ani składać się wyłącznie z białych znaków
            (`TaskValidationError("title", "...")`).
            - `task_id` generowany lokalnie (`str(uuid4())`), `created_at = datetime.utcnow()`.
            - Status startowy: "Open" (domyślna wartość w modelu).

            :param title: Tytuł zadania (wymagany).
            :param description: Opis (opcjonalnie).
            :param due_date: Pole rezerwowe (Level 1 – bez logiki).
            :return: Utworzony obiekt `Task`.
            :raises TaskValidationError: Gdy `title` jest niepoprawny.
        """

        if not title or not title.strip():
            raise TaskValidationError("title", "Tytul nie moze byc pusty")
        
        task_id = str(uuid4())
        created_at = datetime.now(timezone.utc)
        task = Task(task_id = TaskId(task_id), title=title, description=description, created_at=created_at)
        self.repo.add(task)
        
        return task
    
    def list_tasks(
        self,
        page: int = 1,
        page_size: int = 20,
        order_by: Literal["created_at", "title"] | None = None,
        ) -> tuple[list[Task], int]:
        """
        Zwraca stronę zadań oraz łączną liczbę rekordów.

        - Oblicza paginację: offset = (page - 1) * page_size, limit = page_size.
        - Wywołuje repozytorium: list_all(limit, offset, order_by).
        - Zwraca: (lista zadań, liczba wszystkich rekordów).

        :param page: Numer strony (>=1).
        :param page_size: Liczba elementów na stronę (>=1).
        :raises TaskValidationError: Gdy paginacja jest niepoprawna.
        :return: (items, total)
        """
        if page < 1 or page_size < 1:
            raise TaskValidationError("pagination", "page >= 1, page_size >= 1")

        order_by = order_by or "created_at"
        offset = (page - 1) * page_size
        limit = page_size

        total = self.repo.count_all()
        items = self.repo.list_all(limit=limit, offset=offset)

        return items, total
    
    def mark_in_progress(self, task_id: TaskId) -> Task:
        """
            Marks an existing task as completed (`status="In Progress"`).

            - Fetches the task using `repo.get(task_id)`.
            - If not found, raises `TaskNotFoundError`.
            - Creates a new `Task` with the same ID and data, but `status="In Progress"`.
            - Persists the change via `repo.update(new_task)`.

            :param task_id: Identifier of the task to mark as done.
            :raises TaskNotFoundError: If no task with the given ID exists.
            :return: The updated `Task` instance with status `"In Progress"`.
        """
        task = self.repo.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        if task.status == 'In Progress':
            return task
        closed_task = Task(task_id = task.task_id, title=task.title, description=task.description, created_at=task.created_at, status=TaskStatus.IN_PROGRESS)
        self.repo.update(closed_task)
        return closed_task

    def mark_done(self, task_id: TaskId) -> Task:
        """
            Marks an existing task as completed (`status="Closed"`).

            - Fetches the task using `repo.get(task_id)`.
            - If not found, raises `TaskNotFoundError`.
            - Creates a new `Task` with the same ID and data, but `status="Closed"`.
            - Persists the change via `repo.update(new_task)`.

            :param task_id: Identifier of the task to mark as done.
            :raises TaskNotFoundError: If no task with the given ID exists.
            :return: The updated `Task` instance with status `"Closed"`.
        """
        task = self.repo.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        if task.status == "Closed":
            return task
        closed_task = Task(task_id = task.task_id, title=task.title, description=task.description, created_at=task.created_at, status=TaskStatus.CLOSED)
        self.repo.update(closed_task)
        return closed_task
    
    def remove_task(self, task_id: TaskId) -> None:
        """
            Usuwa zadanie z repozytorium.

            - Deleguje do `repo.remove(task_id)`.
            - Repozytorium zgłasza `TaskNotFoundError`, jeśli brak rekordu.

            :param task_id: Identyfikator zadania do usunięcia.
            :raises TaskNotFoundError: Gdy nie znaleziono zadania.
            :return: None
        """
        self.repo.remove(task_id)
    
    def get_task(self, task_id: TaskId) -> Task:
        """
            Zwraca pojedyncze zadanie o wskazanym identyfikatorze.

            - Pobiera obiekt `Task` z repozytorium.
            - Jeśli nie istnieje, zgłasza `TaskNotFoundError`.

            :param task_id: Identyfikator zadania do pobrania.
            :raises TaskNotFoundError: Gdy nie znaleziono zadania.
            :return: Obiekt `Task`.
        """
        task = self.repo.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return task