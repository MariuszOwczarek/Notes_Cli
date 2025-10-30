from notes.adapters.memory.task_repo import InMemoryTaskRepository
from notes.services.task_service import TaskService
from notes.domain.task import Task
from notes.domain.errors import TaskNotFoundError
import pytest
from datetime import datetime, timezone, timedelta

from datetime import datetime, timezone

class FakeIdProvider:
    def __init__(self):
        self.counter = 0
    def new_id(self) -> str:
        self.counter += 1
        return f"id-{self.counter}"

class FakeClock:
    def __init__(self, fixed: datetime | None = None):
        # jeśli nie podamy fixed, zwróci zawsze ten sam „teraz”
        self.fixed = fixed or datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    def now(self) -> datetime:
        return self.fixed
    


def format_task(task) -> str:
    return f"✅ {task.title} | {task.task_id} | done={task.status} | created={task.created_at}"

def test_create_task():
    # Arrange
    repo = InMemoryTaskRepository()
    service = TaskService(repo, FakeIdProvider(), FakeClock())

    # Act
    task = service.create_task("Kup mleko")

    # Assert
    items, total = service.list_tasks()
    assert total == 1
    assert len(items) == 1
    assert "Kup mleko" in format_task(items[0])
    assert task.task_id in format_task(items[0])


def test_list_empty_returns_no_items():
    # Arrange
    repo = InMemoryTaskRepository()
    service = TaskService(repo, FakeIdProvider(), FakeClock())
    
    # Act
    task = service.create_task("Kup mleko")
    service.remove_task(task.task_id)

    items, total = service.list_tasks()

    # Assert
    assert items == []
    assert total == 0

def test_list_sorted_by_created_at_with_tiebreaker():
    # Arrange
    repo = InMemoryTaskRepository()
    service = TaskService(repo, FakeIdProvider(), FakeClock())
    
    # Act
    t1 = service.create_task("A")
    t2 = service.create_task("B")
    
    items, total = service.list_tasks()

    # Assert
    # kolejność po created_at (rosnąco)
    assert items[0].created_at <= items[1].created_at

    # gdy czasy równe — tie-breaker po id
    if items[0].created_at == items[1].created_at:
        assert items[0].task_id < items[1].task_id

def test_get_returns_existing_task():
    #Arrange
    repo = InMemoryTaskRepository()
    service = TaskService(repo, FakeIdProvider(), FakeClock())

    # Act
    t1 = service.create_task("A")
    got = service.get_task(t1.task_id)

    # Assert
    assert got.task_id == t1.task_id
    assert got.title == "A"
    assert got.status == "Open"
    assert got.created_at is not None

def test_get_raises_on_missing():
    #Arrange
    repo = InMemoryTaskRepository()
    service = TaskService(repo, FakeIdProvider(), FakeClock())

    # Assert
    with pytest.raises(TaskNotFoundError):
        service.get_task("non-existent-id")

def test_done_marks_as_completed():
    #Arrange
    repo = InMemoryTaskRepository()
    service = TaskService(repo, FakeIdProvider(), FakeClock())

    #Act
    t1 = service.create_task("A")
    t1 = service.mark_done(t1.task_id)
    items, total = service.list_tasks()

    #Assert
    assert t1.status == "Closed"
    assert total == 1
    assert items[0].status == "Closed"

def test_done_is_idempotent():
    repo = InMemoryTaskRepository()
    service = TaskService(repo, FakeIdProvider(), FakeClock())
    t = service.create_task("A")

    t1 = service.mark_done(t.task_id)
    t2 = service.mark_done(t.task_id)

    assert t1.status == "Closed"
    assert t2.status == "Closed"
    assert t1 == t2 


from notes.adapters.system.id_provider_uuid import UuidIdProvider
from datetime import datetime, timezone

def test_create_sets_valid_uuid_v4_and_is_unique():
    repo = InMemoryTaskRepository()
    # do testu UUID korzystamy z prawdziwego providera:
    service = TaskService(repo, UuidIdProvider(), FakeClock(datetime.now(timezone.utc)))

    t1 = service.create_task("A")
    t2 = service.create_task("B")

    import uuid
    u1 = uuid.UUID(str(t1.task_id))
    u2 = uuid.UUID(str(t2.task_id))
    assert u1.version == 4
    assert u2.version == 4
    assert t1.task_id != t2.task_id


from datetime import datetime, timezone, timedelta

def test_created_at_is_utc_aware_and_not_in_future():
    repo = InMemoryTaskRepository()
    fixed = datetime.now(timezone.utc)  # to „teraz” dla zegara
    service = TaskService(repo, FakeIdProvider(), FakeClock(fixed))

    before = fixed  # albo datetime.now(timezone.utc) tuż przed create
    t = service.create_task("A")
    after = fixed   # albo datetime.now(timezone.utc) tuż po create

    assert t.created_at.tzinfo is not None
    assert t.created_at.tzinfo.utcoffset(t.created_at) == timedelta(0)
    assert before <= t.created_at <= after

def test_created_at_is_preserved_when_status_changes():
    repo = InMemoryTaskRepository()
    service = TaskService(repo, FakeIdProvider(), FakeClock())

    t = service.create_task("A")
    created = t.created_at

    t1 = service.mark_in_progress(t.task_id)
    t2 = service.mark_done(t.task_id)

    assert t1.created_at == created
    assert t2.created_at == created

def test_list_sorted_by_created_at_then_task_id():
    repo = InMemoryTaskRepository()
    service = TaskService(repo, FakeIdProvider(), FakeClock())

    a = service.create_task("A")
    b = service.create_task("B")
    # ewentualnie sztucznie wyrównaj czasy w repo pamięciowym, jeśli masz taką możliwość testową

    items, _ = service.list_tasks(order_by="created_at")
    # oczekiwana kolejność: created_at ASC, a przy remisie task_id ASC
    assert items == sorted(items, key=lambda t: (t.created_at, str(t.task_id)))


def test_create_uses_clock_time():
    repo = InMemoryTaskRepository()
    clock = FakeClock(datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    idp = FakeIdProvider()
    svc = TaskService(repo, idp, clock)

    t = svc.create_task("A")
    assert t.created_at == clock.fixed

