# SQLAlchemy 2.0 — Events & Extensions

## ORM Events

### before_insert / after_insert

```python
from sqlalchemy import event
from sqlalchemy.orm import Session

@event.listens_for(User, "before_insert")
def receive_before_insert(mapper, connection, target):
    """Set defaults before inserting a User."""
    if not target.slug:
        target.slug = target.name.lower().replace(" ", "-")

@event.listens_for(User, "after_insert")
def receive_after_insert(mapper, connection, target):
    """Run side effects after insert (e.g., audit log)."""
    connection.execute(
        audit_log_table.insert().values(
            entity_type="user",
            entity_id=target.id,
            action="created",
        )
    )
```

### before_update / after_update

```python
@event.listens_for(User, "before_update")
def receive_before_update(mapper, connection, target):
    """Track changes before update."""
    state = inspect(target)
    for attr in state.attrs:
        hist = attr.history
        if hist.has_changes():
            print(f"{attr.key}: {hist.deleted} -> {hist.added}")
```

### load (after loading from DB)

```python
@event.listens_for(User, "load")
def receive_load(target, context):
    """Called when a User is loaded from the database."""
    target._loaded_at = datetime.now()
```

### init (after __init__)

```python
@event.listens_for(User, "init")
def receive_init(target, args, kwargs):
    """Called after User.__init__()."""
    target._is_new = True
```

## Session Events

```python
@event.listens_for(Session, "before_flush")
def receive_before_flush(session, flush_context, instances):
    """Inspect pending changes before they're flushed to DB."""
    for obj in session.new:
        if isinstance(obj, AuditedMixin):
            obj.created_by = get_current_user_id()
    for obj in session.dirty:
        if isinstance(obj, AuditedMixin):
            obj.updated_by = get_current_user_id()
    for obj in session.deleted:
        print(f"Deleting: {obj}")

@event.listens_for(Session, "after_flush")
def receive_after_flush(session, flush_context):
    """Access generated PKs and server defaults after flush."""
    pass

@event.listens_for(Session, "before_commit")
def receive_before_commit(session):
    """Last chance to modify before commit."""
    pass

@event.listens_for(Session, "after_commit")
def receive_after_commit(session):
    """Run side effects after successful commit (e.g., send notifications)."""
    pass

@event.listens_for(Session, "after_rollback")
def receive_after_rollback(session):
    """Clean up after rollback."""
    pass
```

## Mapper Events

```python
from sqlalchemy.orm import Mapper

@event.listens_for(Mapper, "mapper_configured")
def receive_mapper_configured(mapper, class_):
    """Called when a mapper is fully configured."""
    print(f"Mapper configured for {class_.__name__}")

@event.listens_for(Mapper, "after_configured")
def receive_after_configured():
    """Called after ALL mappers are configured (once per MetaData)."""
    pass
```

## Attribute Events

```python
@event.listens_for(User.email, "set")
def receive_email_set(target, value, oldvalue, initiator):
    """Normalize email on assignment."""
    if value is not None:
        target.email = value.lower().strip()

@event.listens_for(User.posts, "append")
def receive_posts_append(target, value, initiator):
    """Called when a post is added to user.posts."""
    print(f"Post '{value.title}' added to user {target.name}")

@event.listens_for(User.posts, "remove")
def receive_posts_remove(target, value, initiator):
    """Called when a post is removed from user.posts."""
    pass
```

## Hybrid Properties (Computed Columns)

```python
from sqlalchemy.ext.hybrid import hybrid_property

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))

    @hybrid_property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @full_name.inplace.expression
    @classmethod
    def _full_name_expression(cls):
        return cls.first_name + " " + cls.last_name

# Works in Python and SQL
user.full_name  # "John Doe"
select(User).where(User.full_name == "John Doe")
select(User).order_by(User.full_name)
```

## Column Property (SQL-Level Computed)

```python
from sqlalchemy.orm import column_property
from sqlalchemy import select, func

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))

    # Evaluated as SQL on every load
    full_name: Mapped[str] = column_property(
        first_name + " " + last_name
    )

class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    published: Mapped[bool] = mapped_column(default=False)

# Correlated subquery as column_property
User.post_count = column_property(
    select(func.count(Post.id))
    .where(Post.author_id == User.id)
    .correlate_except(Post)
    .scalar_subquery()
)
```

## Custom Comparators

```python
from sqlalchemy.ext.hybrid import hybrid_property, Comparator

class CaseInsensitiveComparator(Comparator):
    def __eq__(self, other):
        return func.lower(self.__clause_element__()) == func.lower(other)

    def contains(self, other):
        return func.lower(self.__clause_element__()).contains(func.lower(other))

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    _name: Mapped[str] = mapped_column("name", String(100))

    @hybrid_property
    def name(self) -> str:
        return self._name

    @name.inplace.comparator
    @classmethod
    def _name_comparator(cls):
        return CaseInsensitiveComparator(cls._name)

# Case-insensitive queries
select(User).where(User.name == "ALICE")  # compares lower(name) = lower('ALICE')
```

## Version ID Column (Optimistic Locking)

```python
class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)

    # Auto-incremented version column
    version_id: Mapped[int] = mapped_column(default=1)

    __mapper_args__ = {"version_id_col": version_id}

# SQLAlchemy automatically adds WHERE version_id = <expected>
# on UPDATE. Raises StaleDataError if the row was modified
# by another transaction.

with SessionFactory() as session:
    doc = session.get(Document, 1)
    doc.title = "Updated Title"
    try:
        session.commit()
    except StaleDataError:
        session.rollback()
        # Another transaction modified this document; reload and retry
```

## Event-Based Audit Trail Pattern

```python
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int]
    action: Mapped[str] = mapped_column(String(20))  # created, updated, deleted
    changes: Mapped[Optional[dict]] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

@event.listens_for(Session, "before_flush")
def audit_before_flush(session, flush_context, instances):
    for obj in session.new:
        if hasattr(obj, "__audit__") and obj.__audit__:
            session.add(AuditLog(
                entity_type=obj.__class__.__name__,
                entity_id=obj.id,
                action="created",
            ))

    for obj in session.dirty:
        if hasattr(obj, "__audit__") and obj.__audit__:
            state = inspect(obj)
            changes = {}
            for attr in state.attrs:
                hist = attr.history
                if hist.has_changes():
                    changes[attr.key] = {
                        "old": hist.deleted[0] if hist.deleted else None,
                        "new": hist.added[0] if hist.added else None,
                    }
            if changes:
                session.add(AuditLog(
                    entity_type=obj.__class__.__name__,
                    entity_id=obj.id,
                    action="updated",
                    changes=changes,
                ))

    for obj in session.deleted:
        if hasattr(obj, "__audit__") and obj.__audit__:
            session.add(AuditLog(
                entity_type=obj.__class__.__name__,
                entity_id=obj.id,
                action="deleted",
            ))

# Usage: add __audit__ = True to any model
class User(Base):
    __tablename__ = "users"
    __audit__ = True
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
```
