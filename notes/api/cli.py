from notes.domain.errors import TaskNotFoundError, TaskValidationError, DomainError
from notes.domain.task import Task, TaskId
from notes.services.task_service import TaskService
from notes.adapters.memory.task_repo import InMemoryTaskRepository
from notes.adapters.jsonl.task_repo import JsonlTaskRepository
from typer import Option, Typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Literal
from math import ceil
from pathlib import Path
from typing import Optional
from notes.domain.enums import TaskStatus
from notes.api.colors import TaskColor


### COMMENTS
# ==========================================================
# CLI (Typer + Rich) — interfejs użytkownika dla Notes/Tasks.
# ==========================================================
# Rola:
# - Mapuje komendy na metody TaskService (add/list/done/rm/show).
# - Wyświetla wyniki w czytelnej formie (tabele, panele, kolory).
# - Łapie DomainError i drukuje przyjazne komunikaty.
#
# Zasady:
# - Zero logiki biznesowej — deleguj do TaskService.
# - Jednorazowy bootstrap zależności (repo + service) na starcie modułu.
# - Stabilne listowanie gwarantuje repo (sort ASC + tiebreaker + paginacja).


app = Typer(help="Notes/Tasks CLI")
console = Console()

service: TaskService | None = None  # ustawimy w callbacku

def build_service(file: Optional[Path]) -> TaskService:
    """Tworzy serwis na bazie wybranego adaptera.
    - Brak pliku -> InMemory
    - Podany plik -> Jsonl (trwałość)
    """
    if file:
        repo = JsonlTaskRepository(file)
    else:
        repo = InMemoryTaskRepository()
    return TaskService(repo)

@app.callback()
def main(
    file: Optional[Path] = Option(
        None,
        "--file",
        "-f",
        help="Ścieżka do pliku JSONL (włącza tryb trwały)",
    )
) -> None:
    """Bootstrap zależności na starcie procesu CLI."""
    global service
    service = build_service(file)



def short_id(task_id: str, n: int = 8) -> str:
    """Zwraca skróconą wersję UUID do wyświetlenia (np. pierwsze 8 znaków)."""
    return task_id[:n]
    

def color_status(status: TaskStatus) -> str:
    """Zwraca status w Rich-markup z kolorem."""
    match status:
        case TaskStatus.OPEN:
            return f"{TaskColor.RED}Open{TaskColor.RESET}"
        case TaskStatus.IN_PROGRESS:
            return f"{TaskColor.BLUE}In Progress{TaskColor.RESET}"
        case TaskStatus.CLOSED:
            return f"{TaskColor.GREEN}Closed{TaskColor.RESET}"
        case _:
            return str(status)


def render_list(items: list[Task], total: int, page: int, page_size: int) -> None:
    """Renderuje tabelę Rich z kolumnami: ID, Title, Created, Status + stopką paginacji."""

    table = Table(show_lines=True, header_style="bold")
    table.add_column("ID", no_wrap=True, style="Cyan")
    table.add_column("Title")
    table.add_column("Created At", no_wrap=True, style="Dim")
    table.add_column("Status", no_wrap=True)

    for t in items:
        created = t.created_at.strftime("%Y-%m-%d %H:%M")
        table.add_row(
            short_id(t.task_id),
            t.title,
            created,
            color_status(t.status),
        )
    
    pages = max(1, ceil(total/ page_size)) if page_size > 0 else 1

    console.print(table)
    console.print(
        f"[dim]Strona {page}/{pages} • Razem: {total} • Page size: {page_size}[/dim]"
    )

@app.command("add")
def add(title: str, desc: str | None = Option(None, "--desc", "-d")) -> None:
    """
    Dodaje nowe zadanie.

    Flow:
    - Wywołaj: service.create_task(title, description=desc)
    - Sukces: Panel „✅ Dodano zadanie”, pokaż skrócone ID.
    - Błąd walidacji: TaskValidationError → czerwony Panel z podpowiedzią.
    """
    try:
        task = service.create_task(title=title, description=desc)
        console.print(Panel.fit(
            f"✅ Dodano zadanie\n"
            f"[cyan]ID:[/cyan] {short_id(task.task_id)}\n"
            f"[dim]Title:[/dim] {task.title}"
            + (f"\n[dim]Description:[/dim] {task.description}" if task.description else ""),
            title="Sukces",
            border_style="green",
        ))



    except TaskValidationError as e:
        console.print(Panel.fit(
        f"❌ {e}\n[dim]Podpowiedź: użyj np.:[/] notes add 'Tytuł' -d 'Opis'",
        title="Błąd walidacji",
        border_style="red",
        ))
    except DomainError as e:
        console.print(Panel.fit(
            f"❌ {e}",
            title="Błąd domenowy",
            border_style="red",
        ))
    return 


@app.command("list")
def list_cmd(
    page: int = Option(1, "--page", "-p", min=1),
    page_size: int = Option(20, "--page-size", "-s", min=1),
    order_by: Literal["created_at", "title"] | None = Option(None, "--order-by", "-o"),
) -> None:
    """
    Listuje zadania z paginacją.

    Flow:
    - items, total = service.list_tasks(page=page, page_size=page_size, order_by=order_by)
    - render_list(items, total, page, page_size)
    - Błąd paginacji: TaskValidationError → czerwony Panel.
    """
    try:
        items, total = service.list_tasks(page=page, page_size=page_size, order_by=order_by)
        render_list(items, total, page, page_size)
        console.print(f"[dim]Strona {page}, razem {total} zadań[/]")
    except TaskValidationError as e:
        console.print(Panel.fit(
        f"❌ {e}\n[dim]Zla Paginacja",
        title="Błąd walidacji",
        border_style="red",
        ))
    except DomainError as e:
        console.print(Panel.fit(
            f"❌ {e}",
            title="Błąd domenowy",
            border_style="red",
        ))

@app.command("inprogress")
def in_progress(task_id: str) -> None:
    """
    Oznacza zadanie jako zakończone (status="In Progress").

    Flow:
    - service.mark_in+progress(TaskId(task_id))
    - Sukces: Panel „✅ W toku”, pokaż ID i tytuł.
    - Błąd: TaskNotFoundError → „❌ Nie znaleziono… Użyj 'notes list'”.
    """
    try:
        task = service.mark_in_progress(TaskId(task_id))
        console.print(Panel.fit(
            f"✅ Sukces! ID: {short_id(task.task_id)}\n[dim]Title:[/dim] {task.title}\nStatus: {color_status(task.status)}",
            title="Sukces",
            border_style="green",
        ))
    except TaskNotFoundError as e:
        console.print(Panel.fit(
            f"❌ {e}\n[dim]Nie znaleziono zadania o ID: {task_id}[/]\n, [dim]Użyj 'notes list', żeby znaleźć poprawne ID[/]",
            title="Nie znaleziono",
            border_style="red",
        ))
    except DomainError as e:
        console.print(Panel.fit(
            f"❌ {e}",
            title="Błąd domenowy",
            border_style="red",
        ))

@app.command("done")
def done(task_id: str) -> None:
    """
    Oznacza zadanie jako zakończone (status="Closed").

    Flow:
    - service.mark_done(TaskId(task_id))
    - Sukces: Panel „✅ Zamknięto”, pokaż ID i tytuł.
    - Błąd: TaskNotFoundError → „❌ Nie znaleziono… Użyj 'notes list'”.
    """
    try:
        task = service.mark_done(TaskId(task_id))
        console.print(Panel.fit(
            f"✅ Sukces! ID: {short_id(task.task_id)}\n[dim]Title:[/dim] {task.title}\nStatus: {color_status(task.status)}",
            title="Sukces",
            border_style="green",
        ))
    except TaskNotFoundError as e:
        console.print(Panel.fit(
            f"❌ {e}\n[dim]Nie znaleziono zadania o ID: {task_id}[/]\n, [dim]Użyj 'notes list', żeby znaleźć poprawne ID[/]",
            title="Nie znaleziono",
            border_style="red",
        ))
    except DomainError as e:
        console.print(Panel.fit(
            f"❌ {e}",
            title="Błąd domenowy",
            border_style="red",
        ))

@app.command("rm")
def rm(task_id: str) -> None:
    """
    Usuwa zadanie.

    Flow:
    - service.remove_task(TaskId(task_id))
    - Sukces: Panel „🟡 Usunięto”.
    - Błąd: TaskNotFoundError → czerwony Panel z podpowiedzią.
    """
    try:
        service.remove_task(TaskId(task_id))
        console.print(Panel.fit(
            f"🟡 Zadanie usunięte\nID: {short_id(task_id)}\n[dim] skasowany[/]",
            title="Usunięto",
            border_style="yellow",
        ))
    except TaskNotFoundError as e:
        console.print(Panel.fit(
            f"❌ {e}\n"
            f"[dim]Nie znaleziono zadania o ID: {task_id}[/]\n"
            f"[dim]Użyj 'notes list', żeby znaleźć poprawne ID[/]",
            title="Nie znaleziono",
            border_style="red",
        ))
    except DomainError as e:
        console.print(Panel.fit(
            f"❌ {e}",
            title="Błąd domenowy",
            border_style="red",
        ))


@app.command("show")
def show(task_id: str) -> None:
    """
    Pokazuje szczegóły pojedynczego zadania.

    Flow:
    - task = service.get_task(TaskId(task_id))
    - Panel z polami: ID, Title, Description (jeśli jest), Created (UTC), Status (kolor)
    - Błąd: TaskNotFoundError → czerwony Panel.
    """
    try:
        task = service.get_task(TaskId(task_id))

        id_line = f"ID: {short_id(task.task_id)}"
        title_line = f"Title: {task.title}"
        desc_text = task.description or "[dim]brak[/]"
        desc_line = f"Description: {desc_text}"
        created_line = f"Created: {task.created_at.isoformat()}"
        status_line = f"Status: {color_status(task.status)}"

        console.print(Panel.fit(
            "\n".join([id_line, title_line, desc_line, created_line, status_line]),
            title="Szczegóły zadania",
            border_style="cyan",
        ))
    except TaskNotFoundError as e:
        console.print(Panel.fit(
            f"❌ {e}\n"
            f"[dim]Nie znaleziono zadania o ID: {task_id}[/]\n"
            f"[dim]Użyj 'notes list', żeby znaleźć poprawne ID[/]",
            title="Nie znaleziono",
            border_style="red",
        ))
    except DomainError as e:
        console.print(Panel.fit(
            f"❌ {e}",
            title="Błąd domenowy",
            border_style="red",
        ))

@app.command("demo")
def demo() -> None:
    """
    Pokazowy przebieg działania aplikacji w jednym procesie (InMemory).

    - Tworzy 3 zadania.
    - Pokazuje listę.
    - Oznacza jedno jako zakończone.
    - Usuwa inne.
    - Pokazuje listę po zmianach.
    """

    console.print(Panel.fit("🚀 Start demonstracji", border_style="cyan"))

    # 1️⃣ Tworzymy 3 zadania
    t1 = service.create_task("Buy milk", description="2% lactose-free")
    t2 = service.create_task("Call mom", description="Sunday afternoon")
    t3 = service.create_task("Read a book", description="DDD chapter 3")
    t4 = service.create_task("Watch Movie", description="Furioza 2")
    
    items, total = service.list_tasks()
    console.print(Panel.fit(f"✅ Utworzono {total} zadania", border_style="green"))

    # 2️⃣ Pokazujemy listę po dodaniu
    #items, total = service.list_tasks()
    console.print("\n📋 Lista po utworzeniu:")
    render_list(items, total, page=1, page_size=20)

    # 3️⃣ Oznaczamy jedno jako zakończone
    service.mark_done(t2.task_id)
    console.print(Panel.fit(f"✔️ Zamknięto zadanie: {short_id(t2.task_id)} ({t2.title})", border_style="yellow"))

    # 3️⃣ Oznaczamy jedno jako in progress
    service.mark_in_progress(t4.task_id)
    console.print(Panel.fit(f"✔️ Zmieniono status: {short_id(t4.task_id)} ({t4.title})", border_style="blue"))

    # 4️⃣ Usuwamy jedno zadanie
    service.remove_task(t3.task_id)
    console.print(Panel.fit(f"🗑️ Usunięto zadanie: {short_id(t3.task_id)} ({t3.title})", border_style="red"))

    # 5️⃣ Pokazujemy listę po zmianach
    items, total = service.list_tasks()
    console.print("\n📋 Lista po zmianach:")
    render_list(items, total, page=1, page_size=20)

    console.print(Panel.fit("🏁 Demo zakończone", border_style="cyan"))


if __name__ == "__main__":
    app()
    