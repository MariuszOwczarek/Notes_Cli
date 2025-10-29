from typing import NewType, Literal
import datetime
from dataclasses import dataclass

TaskId = NewType("TaskId", str)

@dataclass(frozen=True)
class Task():
    """
    Model domenowy pojedynczego zadania; niemutowalny; status z zamkniętego zestawu wartości; 
    czas w UTC dostarczany przez serwis
    """
    task_id: TaskId
    title: str
    created_at: datetime
    description: str | None = None
    status: Literal["Open","In Progress","Closed"] = "Open"



### COMMENTS
#Ten plik definiuje model domenowy `Task` — czyli czysty, niezmienny obiekt opisujący pojedyncze zadanie.
#Nie zawiera logiki biznesowej ani technicznej — tylko dane i ich strukturalne znaczenie.
# ======================================
# 1️⃣ Dekorator @dataclass
# ======================================
# Dataclass to skrótowy sposób na tworzenie klas danych w Pythonie.
# Normalnie musielibyśmy pisać __init__, __repr__, __eq__ itd.
# @dataclass robi to za nas automatycznie:
# - generuje __init__ z argumentami odpowiadającymi polom klasy
# - generuje __repr__ (czytelny opis obiektu np. Task(task_id='...', title='...'))
# - umożliwia porównywanie obiektów (__eq__)
#
# Dzięki temu mamy klasę, która zachowuje się jak "rekord danych", a nie jak klasa z logiką.
#
# Przykład myślowy:
#   @dataclass
#   class Point:
#       x: int
#       y: int
#   => automatycznie generuje Point.__init__(self, x: int, y: int)

# ======================================
# 2️⃣ Parametr frozen=True
# ======================================
# frozen=True sprawia, że obiekt po utworzeniu jest niemutowalny.
# Oznacza to, że nie możesz zmienić żadnego pola po konstrukcji:
#   task.title = "Nowy tytuł"  ❌  -> błąd: cannot assign to field 'title'
#
# W praktyce to wymusza tzw. "immutability" — podejście, w którym dane są niezmienne,
# a każda "zmiana" to stworzenie nowego obiektu (np. kopii z nowym statusem).
# To daje ogromną przewidywalność, szczególnie w logice domenowej i testach.

# ======================================
# 3️⃣ Literal
# ======================================
# Literal pozwala zdefiniować "zamknięty zestaw" dozwolonych wartości dla zmiennej.
# W naszym przypadku: Status = Literal["Open", "In Progress", "Closed"]
#
# Dzięki temu IDE i mypy wiedzą, że status może mieć TYLKO te wartości.
# - pomaga to uniknąć literówek i błędów typu: task.status = "Done" (którego nie ma w Literal)
# - to proste zastępstwo dla Enum w małych projektach (później możemy zamienić Literal na Enum)

# ======================================
# 4️⃣ NewType
# ======================================
# NewType tworzy "nowy typ logiczny" (dla systemu typów), który w runtime nadal jest tym samym typem.
# Przykład:
#   TaskId = NewType("TaskId", str)
#
# - Dla Pythona w czasie działania to nadal zwykły string
# - Dla narzędzi typujących (mypy, Pyright, IDE) to osobny typ
#
# Dzięki temu możesz odróżnić np. `TaskId` od `UserId` mimo że oba są stringami.
# To minimalny koszt, a duża przejrzystość — zwłaszcza przy większej liczbie encji.

# ======================================
# 5️⃣ Kolejność pól w dataclass
# ======================================
# Python wymaga, żeby pola z wartościami domyślnymi były na końcu.
# Dlaczego?
# - Bo generowany __init__ działa jak każda funkcja: najpierw argumenty wymagane,
#   potem opcjonalne z domyślnymi.
#
# Jeśli zrobisz odwrotnie (czyli pole z domyślną przed wymaganym),
# dostaniesz błąd typu: "non-default argument follows default argument".
#
# Dlatego:
#  ✅ najpierw pola obowiązkowe: task_id, title, created_at
#  ✅ potem opcjonalne lub z domyślną: description, status

# ======================================
# 6️⃣ Dlaczego nie piszemy __init__
# ======================================
# W dataclass __init__ generuje się automatycznie z pól klasy.
# Nie potrzebujemy pisać ręcznie konstruktora.
# 
# Nasza klasa to tzw. "model danych" — czyli "czysty obiekt" (POJO w Javie, DTO w C#),
# który nie ma logiki tworzenia ani walidacji (tym zajmuje się serwis).
#
# Możesz myśleć o tym jak o "schemacie" danych — tak samo jak Protocol określa "jak coś wygląda",
# ale nie mówi "jak to działa".
#
# Różnica z Protocol:
# - Protocol określa zestaw metod i ich sygnatury (interfejs zachowania)
# - dataclass określa zestaw pól i ich typy (interfejs danych)
#
# Oba są "modelowaniem", ale na różnych poziomach:
#   Protocol = zachowanie
#   dataclass = struktura danych

# ======================================
# 7️⃣ created_at i zarządzanie czasem
# ======================================
# Wartość pola `created_at` nie powinna być ustawiana domyślnie w klasie
# (bo wtedy byłaby obliczona przy imporcie, a nie przy tworzeniu obiektu).
# 
# Czas powinien być przekazany z zewnątrz — np. przez serwis przy tworzeniu Taska.
# Na Level 2 nauczymy się wstrzykiwać go przez osobny port Clock.
#
# Na razie zakładamy, że serwis przekazuje `datetime.datetime.utcnow()`.