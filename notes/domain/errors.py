

### COMMENTS
# ============================================
# Konwencja użycia błędów domenowych w projekcie
# ============================================
# - Repozytoria (adaptery):
#     * wykrywają duplikaty lub brak rekordów
#     * mapują błędy techniczne (np. KeyError, IntegrityError) na DomainError
#
# - Serwisy:
#     * walidują dane użytkownika i rzucają TaskValidationError
#     * jeśli get() zwraca None, a operacja wymaga istniejącego zadania — TaskNotFoundError
#
# - UI (CLI, API):
#     * łapie DomainError (lub konkretne klasy) i wyświetla przyjazny komunikat
#     * wszystko inne traktuje jako błąd techniczny (np. loguje stacktrace)


class DomainError(Exception):
    """Bazowa klasa dla błędów domenowych.
    Służy jako wspólny typ nadrzędny dla wszystkich wyjątków biznesowych w systemie.
    Umożliwia odróżnienie błędów domeny (logika aplikacji) od błędów technicznych
    (np. problemów z bazą danych, I/O, siecią).
    Nie powinna być rzucana bezpośrednio — używaj klas pochodnych.
    """

class TaskAlreadyExistsError(DomainError):
    """Rzucany, gdy próba dodania nowego zadania kończy się kolizją identyfikatora.
    Najczęściej występuje, gdy w repozytorium (np. bazie danych lub pliku) istnieje już wpis
    o tym samym `task_id`.
    Zgłaszany przez adaptery implementujące `TaskRepository.add()`.
    """
    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(self.__str__())
    def __str__(self):
        return f"Zadanie o ID {self.task_id} juz istnieje."

class TaskValidationError(DomainError):
    """Rzucany, gdy dane wejściowe nie spełniają reguł biznesowych dla zadania.
    Przykłady:
    - tytuł jest pusty,
    - termin wykonania (due_date) jest w przeszłości,
    - status ma niepoprawną wartość.
    Zgłaszany wyłącznie przez serwis (`TaskService`), przed próbą zapisu w repozytorium.
    Zawiera czytelny komunikat (`message`) oraz opcjonalnie nazwę pola (`field`),
    którego dotyczy błąd, co ułatwia prezentację w UI.
    """    
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(self.__str__())
    def __str__(self):
        return f"Błąd walidacji pola '{self.field}': {self.message}"



class TaskNotFoundError(DomainError):
    """Rzucany, gdy żądane zadanie nie istnieje w repozytorium.
    Występuje w operacjach wymagających istnienia rekordu, np. przy aktualizacji, usunięciu
    lub oznaczaniu zadania jako ukończone (`update()`, `remove()`, `mark_done()`).
    Zgłaszany przez adaptery repozytoriów lub przez serwis, jeśli `get()` zwraca `None`.
    """
    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(self.__str__())
    def __str__(self):
        return f"Zadanie o ID {self.task_id} nie istnieje."

