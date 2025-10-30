
````markdown
# 📝 Notes / Tasks CLI

Mały projekt edukacyjny do nauki **OOP**, **architektury hexagonalnej** i **czystego Pythona** — na przykładzie prostego menedżera zadań działającego w terminalu.

---

## 🚀 Uruchomienie

```bash
# 1️⃣ Utwórz i aktywuj wirtualne środowisko
python -m venv .venv
source .venv/bin/activate    # macOS / Linux
# lub .venv\Scripts\activate  # Windows

# 2️⃣ Zainstaluj zależności
pip install -r requirements.txt

# 3️⃣ Uruchom CLI
python -m notes.api.cli --help
````

---

## 💡 Funkcje

| Komenda      | Opis                                                |
| ------------ | --------------------------------------------------- |
| `add`        | Dodaje nowe zadanie                                 |
| `list`       | Listuje zadania (z paginacją i sortowaniem)         |
| `done`       | Oznacza zadanie jako zakończone                     |
| `inprogress` | Ustawia status „In Progress”                        |
| `rm`         | Usuwa zadanie                                       |
| `show`       | Pokazuje szczegóły zadania                          |
| `demo`       | Przykładowy przebieg działania w pamięci (InMemory) |

Przykłady:

```bash
python -m notes.api.cli add "Kup mleko" -d "2% bez laktozy"
python -m notes.api.cli list
python -m notes.api.cli done <task_id>
python -m notes.api.cli rm <task_id>
```

---

## 🧱 Architektura (Hexagonal / Ports & Adapters)

```
notes/
├─ domain/        # modele i błędy domenowe (Task, TaskStatus, TaskId)
├─ ports/         # interfejsy (TaskRepository, Clock, IdProvider)
├─ adapters/      # implementacje (InMemory, Jsonl, SystemClock, UUID)
├─ services/      # logika aplikacyjna (TaskService)
└─ api/           # CLI (Typer + Rich)
```

Zasady:

* **Brak logiki biznesowej w CLI** — wszystko w `TaskService`.
* **Repozytoria jako porty** — adapter JSONL/InMemory to implementacje.
* **IdProvider** i **Clock** to osobne porty, łatwe do mockowania w testach.

---

## 🧪 Testy

Testy uruchamiane przez `pytest`:

```bash
pytest -v
```

---

## 🧰 Technologie

* Python 3.12+
* [Typer](https://typer.tiangolo.com/) — CLI
* [Rich](https://rich.readthedocs.io/) — kolorowy terminal
* [pytest](https://docs.pytest.org/) — testy jednostkowe
* Architektura **Ports & Adapters (Hexagonal Architecture)**

---

## 🧩 Przykładowy widok CLI

```bash
$ python -m notes.api.cli list

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ID        │ Title        │ Created At     │ Status   ┃
┃ fd583ef4  │ Kup mleko    │ 2025-10-30 ... │ [red]Open[/]  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
Strona 1/1 • Razem: 1 • Page size: 20
```

---

## 📚 Cele edukacyjne

* Nauka **projektowania domeny** (DDD-lite)
* Praktyka **czystego kodu** i **typowania**
* Izolacja logiki od infrastruktury
* Pisanie **testowalnego** kodu

---

## 🧑‍💻 Autor

Projekt edukacyjny — rozwijany w ramach nauki Pythona i architektury aplikacji.
