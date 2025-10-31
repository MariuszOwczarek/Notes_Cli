from __future__ import annotations
from typing import Iterable
import sqlalchemy as db, select
from sqlalchemy.engine import Row
from sqlalchemy.exc import IntegrityError
from pathlib import Path
from notes.ports.task_repository import TaskRepository
from notes.domain.task import Task, TaskId
from notes.domain.enums import TaskStatus
from datetime import datetime, timezone
from notes.domain.errors import TaskAlreadyExistsError, TaskNotFoundError, DomainError

class SqlTaskRepository(TaskRepository):
    def __init__(self, url: str | Path) -> None:
        """
        url: np. 'sqlite:///data/tasks.db' lub Path do pliku (zostanie zrobiony URL)
        """
        if isinstance(url, Path):
            # absolutna ścieżka -> sqlite:////abs/path.db
            db_url = f"sqlite:///{url}"
        else:
            db_url = url

        self.engine = db.create_engine('sqlite:///data/users.db', future=True)
        self.meta = db.MetaData()
        
        # database name
        self.tasks = db.Table(
            "tasks",
            self.meta,
            db.Column("task_id", db.String, primary_key=True),
            db.Column("title", db.String, nullable=False),
            db.Column("description", db.String, nullable=True),
            db.Column("created_at", db.String, nullable=False),  # ISO8601 '...Z'
            db.Column("status", db.String, nullable=False),      # 'Open'/'In Progress'/'Closed'
        )

        # utwórz tabelę jeśli nie istnieje
        self.meta.create_all(self.engine)
    
    def _encode_dt(self,dt: datetime) -> str:
        # ISO 8601 w UTC z sufiksem 'Z'
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def _decode_dt(self,s: str) -> datetime:
        # '...Z' -> aware UTC
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    
    def _to_row(self, task: Task) -> dict:
        return {
            'task_id':str(task.task_id),
            'title':task.title,
            'description':task.description,
            'created_at':self._encode_dt(task.created_at),
            'status':task.status.value if isinstance(task.status, TaskStatus) else str(task.status),
        }
    
    def _from_row(self, row: db.Row | dict) -> Task:
        raw_status = row["status"]
        try:
            status = raw_status if isinstance(raw_status, TaskStatus) else TaskStatus(raw_status)
        except ValueError:
            status = TaskStatus.OPEN

        return Task(
            task_id=TaskId(row["task_id"]),
            title=row["title"],
            description=row["description"],
            created_at=self._decode_dt(row["created_at"]),
            status=status,
        )
    
    def add(self, task: Task) -> None:
        rec = self._to_row(task)
        stmt = db.insert(self.tasks).values(**rec)
        try:
            with self.engine.begin() as conn:
                conn.execute(stmt)
        except IntegrityError:
            # konflikt PK
            raise TaskAlreadyExistsError(task.task_id)
    
    def get(self, task_id: TaskId) -> Task:
        stmt = db.select(self.tasks).where(self.tasks.c.task_id == str(task_id))
        try:
            with self.engine.connect() as conn:
                row = conn.execute(stmt).mappings().first()
                if row is None:
                    raise TaskNotFoundError(task_id)
                return self._from_row(row)
        except OSError as e:
            raise DomainError(str(e))

    def update(self, task: Task) -> None:
        rec = self._to_row(task)
        stmt = (
            db.update(self.tasks)
            .where(self.tasks.c.task_id == str(task.task_id))
            .values(**rec)
        )
        try:
            with self.engine.begin() as conn:
                result = conn.execute(stmt)
                if result.rowcount == 0:
                    raise TaskNotFoundError(task.task_id)
        except OSError as e:
            raise DomainError(str(e))

    def remove(self, task_id: TaskId) -> None:
        stmt = db.delete(self.tasks).where(self.tasks.c.task_id == str(task_id))
        try:
            with self.engine.begin() as conn:
                result = conn.execute(stmt)
                if result.rowcount == 0:
                    raise TaskNotFoundError(task_id)
        except OSError as e:
            raise DomainError(str(e))

    def exists(self, task_id: TaskId) -> bool:
        stmt = (
            db.select(db.literal(1))
            .select_from(self.tasks)
            .where(self.tasks.c.task_id == str(task_id))
            .limit(1)
        )
        try:
            with self.engine.connect() as conn:
                return conn.execute(stmt).first() is not None
        except OSError as e:
            raise DomainError(str(e))

    def count_all(self) -> int:
        stmt = db.select(db.func.count()).select_from(self.tasks)
        try:
            with self.engine.connect() as conn:
                return int(conn.execute(stmt).scalar_one())
        except OSError as e:
            raise DomainError(str(e))

    def list_all(
        self,
        limit: int | None = None,
        offset: int = 0,
        order_by: str | None = None,
    ) -> Iterable[Task]:
        # sortowanie stabilne: ASC + tie-breaker po task_id
        order = (order_by or "created_at").lower()
        if order == "title":
            ordering = (self.tasks.c.title.asc(), self.tasks.c.task_id.asc())
        else:
            ordering = (self.tasks.c.created_at.asc(), self.tasks.c.task_id.asc())

        stmt = db.select(self.tasks).order_by(*ordering)
        if offset and offset > 0:
            stmt = stmt.offset(int(offset))
        if limit is not None:
            if limit <= 0:
                return []
            stmt = stmt.limit(int(limit))

        try:
            with self.engine.connect() as conn:
                rows = conn.execute(stmt).mappings().all()
                return [self._from_row(r) for r in rows]
        except OSError as e:
            raise DomainError(str(e))