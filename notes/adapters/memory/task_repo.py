from notes.domain.task import Task, TaskId
from notes.domain.errors import TaskAlreadyExistsError, TaskNotFoundError, TaskValidationError
from typing import Iterable, Optional, Literal

### COMMENTS
# ==========================================================
# Adapter pamięciowy dla repozytorium zadań (adapters/memory/task_repo.py).
# ==========================================================
# Ten moduł zawiera implementację portu `TaskRepository` w pamięci.
#
# - Służy do testów, prototypowania i poziomu Level 1 (bez trwałego zapisu).
# - Dane przechowywane są w słowniku `_data: dict[TaskId, Task]`.
# - Wszystkie operacje działają w czasie życia obiektu (brak trwałości między uruchomieniami).
# - Zasady zgodne z kontraktem portu:
#     * `add`  → zgłasza `TaskAlreadyExistsError`, jeśli ID istnieje,
#     * `update` → zgłasza `TaskNotFoundError`, jeśli ID nie istnieje,
#     * `remove` → usuwa lub zgłasza `TaskNotFoundError`,
#     * `list_all` → sortuje ASC + tiebreaker po `task_id`, potem paginacja,
#     * `count_all`, `exists` → pomocnicze do walidacji i listowania.
# - Repozytorium nie zawiera logiki biznesowej — tylko trwałość danych.
# - Wyjątki techniczne są mapowane na błędy domenowe.



class InMemoryTaskRepository:
    """
        Inicjalizuje repozytorium z opcjonalną kolekcją startowych zadań.
        :param initial: Iterable z obiektami Task do wstępnego załadowania.
        W przypadku duplikatów task_id ma obowiązywać zasada:
        ostatni wygrywa podczas ładowania (to tylko seed, nie API).
    """
    def __init__(self, initial: Iterable[Task] | None = None) -> None:
        """Initialize repository with optional tasks."""
        #self._data = {t.task_id: t for t in (initial or [])} - comprehension list, below is for loop - better for beginers
        self._data = {}
        for t in (initial or []):
            self._data[t.task_id] = t  # load each Task by ID
    
    def add(self, task:Task):
        """
            Dodaje nowe zadanie do repozytorium.

            - Kolizja rozpoznawana jest po `task.task_id` (kluczu w mapie `_data`).
            - Jeśli identyfikator już istnieje, metoda nie nadpisuje wpisu,
            tylko zgłasza błąd domenowy `TaskAlreadyExistsError`.
            - Repozytorium nie wykonuje żadnej walidacji biznesowej – za to
            odpowiada warstwa serwisu.

            :param task: Obiekt domenowy Task do zapisania.
            :raises TaskAlreadyExistsError: Jeśli zadanie o tym samym `task_id`
            już istnieje w repozytorium.
            :return: None
        """
        if task.task_id not in self._data:
            self._data[task.task_id] = task
            return
        raise TaskAlreadyExistsError(task.task_id)
    
    def get(self, task_id:TaskId) -> Optional[Task]:
        """
            Zwraca zadanie o podanym identyfikatorze `task_id`.

            - Jeśli zadanie istnieje w repozytorium, zwraca obiekt `Task`.
            - Jeśli nie istnieje, zwraca `None` (bez zgłaszania błędu).
            - Repozytorium nie interpretuje braku zadania jako błąd – to
            decyzja warstwy serwisu.

            :param task_id: Identyfikator zadania do pobrania.
            :return: Obiekt `Task`, jeśli istnieje, w przeciwnym razie `None`.
        """
        if task_id in self._data:
            return self._data[task_id]
        return None

    def update(self, task: Task) -> None:
        """
            Pełna podmiana istniejącego rekordu o danym `task_id`.

            - Jeśli rekord o tym identyfikatorze nie istnieje, zgłasza
            `TaskNotFoundError`.
            - Aktualizacja polega na całkowitej wymianie obiektu — repozytorium
            nie „skleja” pól, tylko zastępuje stary wpis nowym.

            :param task: Nowy obiekt `Task` (z tym samym `task_id` co istniejący).
            :raises TaskNotFoundError: Gdy rekord z `task_id` nie istnieje.
            :return: None
        """

        if task.task_id in self._data:
            self._data[task.task_id] = task
            return None
        raise TaskNotFoundError(task.task_id)
    
    def remove(self, task_id: TaskId) -> None:
        """
            Usuwa zadanie o wskazanym identyfikatorze z repozytorium.

            - Jeśli zadanie o podanym `task_id` nie istnieje, metoda zgłasza
            `TaskNotFoundError`.
            - Usunięcie jest trwałe w kontekście życia obiektu repozytorium.

            :param task_id: Identyfikator zadania do usunięcia.
            :raises TaskNotFoundError: Jeśli nie istnieje wpis o podanym `task_id`.
            :return: None
        """

        if task_id in self._data:
            del self._data[task_id]
            return None
        raise TaskNotFoundError(task_id)
    
    def list_all(
        self,
        *,  # * „Od tego miejsca wszystkie parametry muszą być przekazane nazwami.”  - repo.list_all(limit=10, offset=5, order_by="title")
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[Literal["created_at", "title"]] = None,
    ) -> list[Task]:
        """
        Zwraca posortowaną i paginowaną listę zadań.

        - Sortowanie rosnące (ASC) po `order_by` (domyślnie "created_at").
        - Stabilność: tiebreaker po `task_id` ASC.
        - Paginacja: po sortowaniu (offset, limit).
        - Waliduje parametry wejściowe (order_by, offset, limit).

        :param limit: Maksymalna liczba wyników (None = bez limitu).
        :param offset: Liczba elementów do pominięcia po sortowaniu.
        :param order_by: Pole sortowania ("created_at" lub "title").
        :raises TaskValidationError: Przy błędnych parametrach.
        :return: Lista obiektów `Task` po sortowaniu i paginacji.
        """
        # domyślne wartości
        order_by = order_by or "created_at"
        offset = offset or 0

        if order_by not in {"created_at", "title"}:
            raise TaskValidationError("order_by", f"Nieobsługiwane pole: {order_by}")

        if offset < 0 or (limit is not None and limit <= 0):
            raise TaskValidationError("pagination", "Offset >= 0, limit > 0")

        # lista zadań
        tasks = list(self._data.values())

        # sortowanie z tiebreakerem
        tasks.sort(key=lambda t: (getattr(t, order_by), t.task_id))

        # paginacja po sortowaniu
        if limit is not None:
            tasks = tasks[offset : offset + limit]
        else:
            tasks = tasks[offset:]

        return tasks

    def count_all(self) -> int:
        """
            Zwraca całkowitą liczbę zadań przechowywanych w repozytorium.

            - Liczenie odbywa się na podstawie liczby wpisów w `_data`.
            - Metoda nie filtruje wyników ani nie stosuje paginacji.

            :return: Liczba obiektów `Task` w repozytorium.
        """
        return len(self._data)


    def exists(self, task_id: TaskId) -> bool:
        """
            Sprawdza, czy w repozytorium istnieje zadanie o podanym identyfikatorze.

            - Weryfikuje obecność klucza `task_id` w strukturze `_data`.
            - Nie zgłasza wyjątków — zwraca jedynie wartość logiczną.

            :param task_id: Identyfikator zadania do sprawdzenia.
            :return: True, jeśli zadanie istnieje; False w przeciwnym razie.
        """
        #return task_id in self._data  - mozna to zapisac krocej

        if task_id in self._data:
            return True
        return False