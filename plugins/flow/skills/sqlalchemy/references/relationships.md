# SQLAlchemy 2.0 — Relationships & Loading

## Basic Relationship with Mapped[] Typing

```python
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

    # One-to-Many: user.posts returns list
    posts: Mapped[list["Post"]] = relationship(back_populates="author")

class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Many-to-One: post.author returns single object
    author: Mapped["User"] = relationship(back_populates="posts")
```

## back_populates vs backref

Always prefer `back_populates` — it is explicit and type-checker-friendly.

```python
# GOOD — explicit on both sides
class Parent(Base):
    __tablename__ = "parents"
    id: Mapped[int] = mapped_column(primary_key=True)
    children: Mapped[list["Child"]] = relationship(back_populates="parent")

class Child(Base):
    __tablename__ = "children"
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"))
    parent: Mapped["Parent"] = relationship(back_populates="children")
```

## One-to-One

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    profile: Mapped[Optional["Profile"]] = relationship(
        back_populates="user", uselist=False
    )

class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    user: Mapped["User"] = relationship(back_populates="profile")
```

## Many-to-Many with Association Table

```python
from sqlalchemy import Table, Column, ForeignKey

# Plain association table (no extra columns)
post_tags = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", ForeignKey("posts.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)

class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    tags: Mapped[list["Tag"]] = relationship(
        secondary=post_tags, back_populates="posts"
    )

class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    posts: Mapped[list["Post"]] = relationship(
        secondary=post_tags, back_populates="tags"
    )
```

## Association Object (extra columns on the join)

```python
from datetime import datetime
from sqlalchemy import DateTime, func

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="user_roles")
    role: Mapped["Role"] = relationship(back_populates="user_roles")

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_roles: Mapped[list["UserRole"]] = relationship(back_populates="user")

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    user_roles: Mapped[list["UserRole"]] = relationship(back_populates="role")
```

## Association Proxy

```python
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_roles: Mapped[list["UserRole"]] = relationship(back_populates="user")

    # Access role names directly: user.role_names
    role_names: AssociationProxy[list[str]] = association_proxy(
        "user_roles", "role_name"
    )

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    user: Mapped["User"] = relationship(back_populates="user_roles")
    role: Mapped["Role"] = relationship()

    @property
    def role_name(self) -> str:
        return self.role.name
```

## Loading Strategies

### Lazy Loading Options (relationship-level)

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)

    # Default: loads on access via SELECT
    posts: Mapped[list["Post"]] = relationship(lazy="select")

    # Eager load via SELECT IN
    comments: Mapped[list["Comment"]] = relationship(lazy="selectin")

    # Eager load via JOIN
    profile: Mapped[Optional["Profile"]] = relationship(lazy="joined")

    # Eager load via subquery
    orders: Mapped[list["Order"]] = relationship(lazy="subquery")

    # Raise error if accessed without explicit load — great for async
    audit_logs: Mapped[list["AuditLog"]] = relationship(lazy="raise")

    # Never load
    legacy_data: Mapped[list["LegacyData"]] = relationship(lazy="noload")
```

### Explicit Loading (query-level)

```python
from sqlalchemy.orm import selectinload, joinedload, lazyload, raiseload, subqueryload

# Override lazy strategy per-query
stmt = (
    select(User)
    .options(
        selectinload(User.posts),             # eager via IN
        joinedload(User.profile),             # eager via JOIN
        subqueryload(User.orders),            # eager via subquery
        lazyload(User.comments),              # force lazy
        raiseload(User.audit_logs),           # raise on access
    )
    .where(User.id == user_id)
)

# Nested eager loading
stmt = (
    select(User)
    .options(
        selectinload(User.posts).selectinload(Post.comments),
        joinedload(User.profile),
    )
)

# Wildcard raiseload — catch all unloaded relationships
stmt = select(User).options(
    selectinload(User.posts),
    raiseload("*"),  # any other relationship access raises
)
```

## Cascades

```python
class Parent(Base):
    __tablename__ = "parents"
    id: Mapped[int] = mapped_column(primary_key=True)

    # delete children when parent is deleted; remove orphans
    children: Mapped[list["Child"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        passive_deletes=True,  # let DB handle ON DELETE CASCADE
    )

class Child(Base):
    __tablename__ = "children"
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(
        ForeignKey("parents.id", ondelete="CASCADE")
    )
    parent: Mapped["Parent"] = relationship(back_populates="children")
```

Cascade options:

- `save-update` — add related objects to session (default)
- `merge` — cascade `session.merge()` (default)
- `delete` — delete children when parent is deleted
- `delete-orphan` — delete children removed from collection
- `all` — shorthand for `save-update, merge, refresh-expire, expunge, delete`

## Composite Foreign Keys

```python
class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["order_id", "order_version"],
            ["orders.id", "orders.version"],
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int]
    order_version: Mapped[int]

    order: Mapped["Order"] = relationship(
        foreign_keys=[order_id, order_version]
    )
```

## Custom Join Conditions

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int]

    # Only load addresses matching the same tenant
    addresses: Mapped[list["Address"]] = relationship(
        primaryjoin=lambda: and_(
            User.id == Address.user_id,
            User.tenant_id == Address.tenant_id,
        ),
        foreign_keys=lambda: [Address.user_id, Address.tenant_id],
    )
```

## Self-Referential Relationships

### Adjacency List (Tree)

```python
class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"))

    parent: Mapped[Optional["Category"]] = relationship(
        back_populates="children",
        remote_side="Category.id",
    )
    children: Mapped[list["Category"]] = relationship(back_populates="parent")
```

### Manager / Reports

```python
class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    manager_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"))

    manager: Mapped[Optional["Employee"]] = relationship(
        back_populates="reports", remote_side="Employee.id"
    )
    reports: Mapped[list["Employee"]] = relationship(back_populates="manager")
```
