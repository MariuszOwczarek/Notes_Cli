import pytest
from datetime import datetime, timezone
from pathlib import Path
from notes.adapters.sql.task_repo import SqlTaskRepository
from notes.domain.task import Task, TaskId
from notes.domain.enums import TaskStatus
from notes.domain.errors import TaskNotFoundError, TaskAlreadyExistsError


@pytest.fixture
def tmp_repo(tmp_path):
    """Repozytorium na świeżej tymczasowej bazie."""
    db_path = tmp_path / "tasks.db"
    repo = SqlTaskRepository(db_path)
    return repo


def make_task(task_id: str, title: str = "Test") -> Task:
    return Task(
        task_id=TaskId(task_id),
        title=title,
        description="desc",
        created_at=datetime.now(timezone.utc),
        status=TaskStatus.OPEN,
    )


def test_add_and_get(tmp_repo):
    task = make_task("id-1")
    tmp_repo.add(task)

    fetched = tmp_repo.get(TaskId("id-1"))
    assert fetched.task_id == task.task_id
    assert fetched.title == task.title
    assert fetched.status == TaskStatus.OPEN


def test_add_duplicate_raises(tmp_repo):
    task = make_task("dup-1")
    tmp_repo.add(task)
    with pytest.raises(TaskAlreadyExistsError):
        tmp_repo.add(task)


def test_remove_deletes(tmp_repo):
    task = make_task("rm-1")
    tmp_repo.add(task)
    tmp_repo.remove(TaskId("rm-1"))
    with pytest.raises(TaskNotFoundError):
        tmp_repo.get(TaskId("rm-1"))


def test_update_changes_status(tmp_repo):
    task = make_task("up-1")
    tmp_repo.add(task)

    updated = Task(
        task_id=task.task_id,
        title=task.title,
        description=task.description,
        created_at=task.created_at,
        status=TaskStatus.CLOSED,
    )
    tmp_repo.update(updated)

    result = tmp_repo.get(task.task_id)
    assert result.status == TaskStatus.CLOSED


def test_list_and_count(tmp_repo):
    t1 = make_task("t1", "A")
    t2 = make_task("t2", "B")
    tmp_repo.add(t1)
    tmp_repo.add(t2)

    all_tasks = list(tmp_repo.list_all())
    assert len(all_tasks) == 5
    assert tmp_repo.count_all() == 5 ##because we add from other tests


def test_exists(tmp_repo):
    task = make_task("ex-1")
    tmp_repo.add(task)
    assert tmp_repo.exists(TaskId("ex-1"))
    assert not tmp_repo.exists(TaskId("nope"))
