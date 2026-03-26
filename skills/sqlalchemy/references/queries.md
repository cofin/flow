# SQLAlchemy 2.0 — Querying (select() Style)

## Basic select()

```python
from sqlalchemy import select, and_, or_, not_, func, text, literal_column
from sqlalchemy.orm import Session

stmt = select(User)
stmt = select(User.id, User.name)  # select specific columns

with Session(engine) as session:
    result = session.execute(stmt)
    users = result.scalars().all()          # list of User objects
    rows = result.all()                      # list of Row tuples (when selecting columns)
```

## where() Clause Operators

```python
# Equality / inequality
select(User).where(User.name == "alice")
select(User).where(User.age != 30)

# Comparison
select(User).where(User.age > 18)
select(User).where(User.age >= 21)

# IN
select(User).where(User.id.in_([1, 2, 3]))
select(User).where(~User.id.in_([1, 2, 3]))  # NOT IN

# LIKE / ILIKE
select(User).where(User.name.like("al%"))
select(User).where(User.name.ilike("%alice%"))  # case-insensitive

# BETWEEN
select(User).where(User.age.between(18, 65))

# IS NULL / IS NOT NULL
select(User).where(User.email.is_(None))
select(User).where(User.email.is_not(None))

# AND / OR / NOT
select(User).where(and_(User.active == True, User.age > 18))
select(User).where(or_(User.role == "admin", User.role == "superadmin"))
select(User).where(not_(User.banned))

# Multiple .where() calls are AND-ed
select(User).where(User.active == True).where(User.age > 18)

# String contains / startswith / endswith
select(User).where(User.name.contains("ali"))
select(User).where(User.name.startswith("al"))
select(User).where(User.name.endswith("ce"))
```

## Joins

```python
# Implicit join (relationship-based)
stmt = select(User).join(User.posts).where(Post.published == True)

# Explicit join condition
stmt = select(User).join(Post, User.id == Post.author_id)

# Outer join
stmt = select(User).outerjoin(User.posts)

# Multiple joins
stmt = (
    select(User)
    .join(User.posts)
    .join(Post.comments)
    .where(Comment.approved == True)
)

# select_from for complex cases
stmt = (
    select(User.name, func.count(Post.id))
    .select_from(User)
    .outerjoin(Post, User.id == Post.author_id)
    .group_by(User.name)
)
```

## Aggregations

```python
from sqlalchemy import func

# Count
stmt = select(func.count()).select_from(User)
stmt = select(func.count(User.id)).where(User.active == True)

# Sum, Avg, Min, Max
stmt = select(func.sum(Order.total))
stmt = select(func.avg(Order.total))
stmt = select(func.min(Order.created_at), func.max(Order.created_at))

# Group By + Having
stmt = (
    select(Post.author_id, func.count(Post.id).label("post_count"))
    .group_by(Post.author_id)
    .having(func.count(Post.id) > 5)
)
```

## Subqueries

```python
# Subquery in WHERE
subq = (
    select(Post.author_id)
    .where(Post.published == True)
    .group_by(Post.author_id)
    .having(func.count(Post.id) > 10)
    .subquery()
)
stmt = select(User).where(User.id.in_(select(subq.c.author_id)))

# Scalar subquery
post_count = (
    select(func.count(Post.id))
    .where(Post.author_id == User.id)
    .scalar_subquery()
)
stmt = select(User.name, post_count.label("post_count"))

# Correlated subquery with exists()
stmt = select(User).where(
    select(Post).where(Post.author_id == User.id).exists()
)

# NOT EXISTS
stmt = select(User).where(
    ~select(Post).where(Post.author_id == User.id).exists()
)
```

## Common Table Expressions (CTEs)

```python
# CTE for recursive queries (e.g., tree traversal)
cte = (
    select(Category.id, Category.name, Category.parent_id)
    .where(Category.parent_id.is_(None))
    .cte(name="category_tree", recursive=True)
)

cte_alias = cte.alias("ct")
category_alias = Category.__table__.alias("c")

recursive_part = (
    select(category_alias.c.id, category_alias.c.name, category_alias.c.parent_id)
    .join(cte_alias, category_alias.c.parent_id == cte_alias.c.id)
)

cte = cte.union_all(recursive_part)
stmt = select(cte)
```

## Order By, Limit, Offset, Distinct

```python
# Order by
stmt = select(User).order_by(User.name)
stmt = select(User).order_by(User.created_at.desc())
stmt = select(User).order_by(User.last_name, User.first_name)

# Nulls first / last
stmt = select(User).order_by(User.score.desc().nulls_last())

# Limit and offset
stmt = select(User).order_by(User.id).limit(20).offset(40)

# Distinct
stmt = select(User.name).distinct()
```

## Set Operations

```python
from sqlalchemy import union, union_all, intersect, except_

stmt1 = select(User.id, User.name).where(User.role == "admin")
stmt2 = select(User.id, User.name).where(User.active == True)

# Union (deduped)
stmt = union(stmt1, stmt2)

# Union All
stmt = union_all(stmt1, stmt2)

# Intersect
stmt = intersect(stmt1, stmt2)

# Except
stmt = except_(stmt1, stmt2)
```

## Bulk Operations

```python
from sqlalchemy import insert, update, delete

# Bulk insert
stmt = insert(User).values([
    {"name": "alice", "email": "alice@example.com"},
    {"name": "bob", "email": "bob@example.com"},
])
session.execute(stmt)

# Bulk update
stmt = (
    update(User)
    .where(User.last_login < datetime(2024, 1, 1))
    .values(active=False)
)
session.execute(stmt)

# Bulk delete
stmt = delete(User).where(User.active == False)
session.execute(stmt)

# Returning clause (PostgreSQL, SQLite 3.35+, MariaDB 10.5+)
stmt = insert(User).values(name="alice").returning(User.id, User.created_at)
result = session.execute(stmt)
new_id, created = result.one()

# Update with returning
stmt = (
    update(User)
    .where(User.id == 1)
    .values(name="Alice Updated")
    .returning(User.id, User.name)
)
```

## Executing & Result Handling

```python
with Session(engine) as session:
    stmt = select(User).where(User.active == True)

    # All results
    users = session.execute(stmt).scalars().all()         # list[User]

    # Unique results (needed with joinedload)
    users = session.execute(stmt).unique().scalars().all()

    # First result or None
    user = session.execute(stmt).scalars().first()

    # Exactly one result (raises if 0 or 2+)
    user = session.execute(stmt).scalars().one()

    # One or None (raises if 2+)
    user = session.execute(stmt).scalars().one_or_none()

    # Iterate without loading all into memory
    for user in session.execute(stmt).scalars():
        process(user)

    # Raw rows (when selecting columns, not entities)
    stmt = select(User.id, User.name)
    for row in session.execute(stmt):
        print(row.id, row.name)     # named tuple access
        print(row[0], row[1])       # index access

    # Partitioned results for batched processing
    for partition in session.execute(stmt).scalars().partitions(500):
        process_batch(partition)
```
