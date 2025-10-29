from typing import Protocol, Optional, Literal
from notes.domain.task import Task, TaskId


### COMMENTS
# ==========================================================
# Kontrakt repozytorium zadań (ports/task_repository.py).
# ==========================================================
# Ten moduł definiuje interfejs (Protocol) dla warstwy trwałości Tasków.
# - Jest niezależny od technologii (pamięć, plik JSONL, baza SQL).
# - Adaptery mają obowiązek mapować błędy technologiczne na błędy domenowe
#  (np. UNIQUE → TaskAlreadyExistsError, brak rekordu → TaskNotFoundError).
# - Repozytorium nie zawiera logiki biznesowej (walidacje są w serwisie).
# - Listowanie gwarantuje stabilną kolejność dzięki tiebreakerowi po task_id (ASC).


class TaskRepository(Protocol):
    """Interfejs repozytorium do zapisu i odczytu obiektów `Task`.

    Adaptery (implementacje) muszą:
    - zapewnić atomowość operacji zapisu,
    - mapować błędy technologiczne na błędy domenowe,
    - stosować stabilne sortowanie (tiebreaker po `task_id` rosnąco),
    - nie wykonywać walidacji biznesowych (te należą do warstwy serwisu).
    """

    def add(self, task: Task) -> Task:
        """Dodaje nowy rekord `Task`.

        Zwraca:
            Task: Zapisany obiekt (na Level 1 identyczny jak wejściowy).

        Wyjątki domenowe:
            TaskAlreadyExistsError: Gdy istnieje wpis o tym samym `task_id`.

        Uwagi:
            Operacja powinna być atomowa (spójność po błędzie częściowym).
        """

    def get(self, task_id: TaskId) -> Optional[Task]:
        """Zwraca zadanie o podanym `task_id`.

        Zwraca:
            Optional[Task]: Obiekt `Task`, jeśli istnieje; w przeciwnym razie `None`.

        Wyjątki domenowe:
            Brak — to odczyt, repozytorium nie rzuca tutaj wyjątków domenowych.

        Uwagi:
            Metoda nie wykonuje walidacji biznesowych.
        """

    def update(self, task: Task) -> None:
        """Pełna podmiana istniejącego rekordu o danym `task_id`.

        Zwraca:
            Task: Zaktualizowany obiekt.

        Wyjątki domenowe:
            TaskNotFoundError: Gdy rekord z `task_id` nie istnieje.

        Uwagi:
            Repozytorium nie „skleja” pól — zapisuje kompletny obiekt.
        """

    def remove(self, task_id: TaskId) -> None:
        """Usuwa (hard delete) rekord o podanym `task_id`.

        Zwraca:
            None

        Wyjątki domenowe:
            TaskNotFoundError: Gdy rekord z `task_id` nie istnieje.

        Uwagi:
            Idempotencja nie jest wymagana — brak rekordu to błąd domenowy.
        """

    def list_all(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[Literal["created_at", "title"]] = None,
    ) -> list[Task]:
        """Zwraca posortowaną listę zadań z paginacją.

        Parametry:
            limit (Optional[int]): Maksymalna liczba wyników na stronie.
                                   Gdy `None`, brak ograniczenia.
            offset (Optional[int]): Przesunięcie od początku posortowanej listy.
                                    Gdy `None`, traktowane jak 0.
            order_by (Optional[Literal["created_at", "title"]]):
                Główne kryterium sortowania, rosnąco.
                Gdy `None`, domyślnie `"created_at"`.

        Sortowanie:
            - Najpierw po `order_by` (ASC),
            - Następnie tiebreaker po `task_id` (ASC), dla stabilności kolejności.

        Paginacja:
            - ZAWSZE po sortowaniu: najpierw sort → potem offset/limit.

        Zwraca:
            list[Task]: Fragment listy po zastosowaniu sortowania i paginacji.

        Wyjątki domenowe:
            Brak — metoda odczytu nie rzuca wyjątków domenowych.

        Uwagi:
            Oczekiwane, że `limit` i `offset` to liczby nieujemne.
            Walidacje wejścia zwykle realizuje serwis; repo zakłada poprawne typy.
        """

    def count_all(self) -> int:
        """Zwraca liczbę wszystkich rekordów (do paginacji).

        Zwraca:
            int: Całkowita liczba zadań w repozytorium.
        """

    def exists(self, task_id: TaskId) -> bool:
        """Szybkie sprawdzenie istnienia rekordu o `task_id`.

        Zwraca:
            bool: `True` jeśli rekord istnieje, w przeciwnym razie `False`.

        Uwagi:
            Adapter może używać najtańszego mechanizmu (np. `SELECT 1` w DB).
        """

