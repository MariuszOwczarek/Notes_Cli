# 📝 Notes / Tasks CLI (Python + Typer + Rich)

Mały projekt do nauki **OOP** i **architektury hexagonalnej** na przykładzie menedżera zadań.

## 🚀 Uruchomienie
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m api.cli --help


💡 Funkcje
add – dodaje nowe zadanie
list – listuje zadania (z paginacją i sortowaniem)
done – oznacza jako zakończone
rm – usuwa
show – pokazuje szczegóły

🧱 Architektura
notes/
├─ domain/      # modele i błędy domenowe
├─ ports/       # interfejsy (TaskRepository)
├─ adapters/    # implementacje (InMemory)
├─ services/    # logika aplikacyjna (TaskService)
└─ api/         # CLI (Typer + Rich)



