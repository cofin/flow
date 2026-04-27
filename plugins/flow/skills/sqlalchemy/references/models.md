# SQLAlchemy 2.0 — Declarative Mapped Classes

## DeclarativeBase

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, BigInteger, text
from datetime import datetime

class Base(DeclarativeBase):
    pass
```

## MappedAsDataclass

```python
from sqlalchemy.orm import MappedAsDataclass, Mapped, mapped_column

class Base(MappedAsDataclass, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(default=True)
```

## Mapped[] Type Annotations

```python
from sqlalchemy import String, Text, DateTime, func
from typing import Optional

class User(Base):
    __tablename__ = "users"

    # Required column — Mapped[type] (non-optional = NOT NULL)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

    # Nullable column — use Optional
    bio: Mapped[Optional[str]] = mapped_column(Text)

    # Server default
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

## mapped_column() Options

```python
from sqlalchemy import String, BigInteger, Index, UniqueConstraint, text
from uuid import UUID, uuid4

class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data: Mapped[Optional[str]] = mapped_column(deferred=True)  # lazy-load heavy column
    sort_order: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    external_id: Mapped[UUID] = mapped_column(default=uuid4)
```

## Table Args

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        UniqueConstraint("tenant_id", "external_ref", name="uq_tenant_ref"),
        {"schema": "audit", "comment": "Audit trail for all entities"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int]
    external_ref: Mapped[Optional[str]] = mapped_column(String(100))
```

## Column Types

```python
from sqlalchemy import (
    String, Integer, BigInteger, SmallInteger,
    Boolean, DateTime, Date, Time, Interval,
    Float, Numeric, JSON, LargeBinary, Text, Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
import enum

class Status(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class Example(Base):
    __tablename__ = "examples"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    count: Mapped[int] = mapped_column(SmallInteger)
    active: Mapped[bool] = mapped_column(Boolean)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    metadata_: Mapped[dict] = mapped_column("metadata", JSON)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String))  # PostgreSQL only
    avatar: Mapped[Optional[bytes]] = mapped_column(LargeBinary)
    status: Mapped[Status] = mapped_column(default=Status.ACTIVE)
    uid: Mapped[UUID] = mapped_column(Uuid, default=uuid4)
```

## Custom TypeDecorator

```python
from sqlalchemy import TypeDecorator, String
import json

class JSONEncodedList(TypeDecorator):
    """Store a Python list as a JSON-encoded string."""
    impl = String(2000)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None

class Widget(Base):
    __tablename__ = "widgets"
    id: Mapped[int] = mapped_column(primary_key=True)
    labels: Mapped[Optional[list]] = mapped_column(JSONEncodedList)
```

## Mixins

```python
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, declared_attr

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

class SoftDeleteMixin:
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

class TableNameMixin:
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + "s"

class User(TimestampMixin, SoftDeleteMixin, TableNameMixin, Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
```

## Inheritance

### Single-Table Inheritance

```python
class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(50))

    __mapper_args__ = {"polymorphic_on": "type", "polymorphic_identity": "employee"}

class Manager(Employee):
    department: Mapped[Optional[str]] = mapped_column(String(100))
    __mapper_args__ = {"polymorphic_identity": "manager"}
```

### Joined-Table Inheritance

```python
class Person(Base):
    __tablename__ = "persons"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(50))
    __mapper_args__ = {"polymorphic_on": "type", "polymorphic_identity": "person"}

class Engineer(Person):
    __tablename__ = "engineers"
    id: Mapped[int] = mapped_column(ForeignKey("persons.id"), primary_key=True)
    specialty: Mapped[str] = mapped_column(String(100))
    __mapper_args__ = {"polymorphic_identity": "engineer"}
```

## Hybrid Properties

```python
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy import case

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    quantity: Mapped[int]
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2))
    discount_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)

    @hybrid_property
    def total(self) -> float:
        return self.quantity * self.unit_price * (1 - self.discount_pct / 100)

    @total.inplace.expression
    @classmethod
    def _total_expression(cls):
        return cls.quantity * cls.unit_price * (1 - cls.discount_pct / 100)

    @hybrid_method
    def is_high_value(self, threshold: float) -> bool:
        return self.total > threshold

    @is_high_value.inplace.expression
    @classmethod
    def _is_high_value_expression(cls, threshold: float):
        return cls._total_expression() > threshold
```

Usage in queries:

```python
# hybrid_property works in SQL WHERE clauses
stmt = select(Order).where(Order.total > 1000)
stmt = select(Order).where(Order.is_high_value(500))
```
