# PL/pgSQL Development

## Functions

```sql
-- Basic function returning a scalar
CREATE OR REPLACE FUNCTION get_user_balance(p_user_id bigint)
RETURNS numeric
LANGUAGE plpgsql
STABLE  -- or VOLATILE, IMMUTABLE
AS $$
DECLARE
    v_balance numeric;
BEGIN
    SELECT balance INTO v_balance
    FROM accounts
    WHERE user_id = p_user_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'User % not found', p_user_id
            USING ERRCODE = 'P0002';
    END IF;

    RETURN v_balance;
END;
$$;
```

## Procedures (PG11+)

```sql
-- Procedures can manage transactions (COMMIT/ROLLBACK inside)
CREATE OR REPLACE PROCEDURE transfer_funds(
    p_from bigint,
    p_to bigint,
    p_amount numeric
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE accounts SET balance = balance - p_amount WHERE user_id = p_from;
    UPDATE accounts SET balance = balance + p_amount WHERE user_id = p_to;

    -- Can commit mid-procedure
    COMMIT;
END;
$$;

CALL transfer_funds(1, 2, 100.00);
```

## Variable Declaration

```sql
DECLARE
    v_count    integer := 0;
    v_name     text;
    v_row      users%ROWTYPE;           -- full row type from table
    v_email    users.email%TYPE;        -- column type
    v_record   record;                  -- untyped, assigned at runtime
    v_arr      integer[] := ARRAY[1,2,3];
    v_const    constant text := 'fixed';
```

## Control Flow

### IF / ELSIF / ELSE

```sql
IF v_status = 'active' THEN
    v_rate := 0.05;
ELSIF v_status = 'premium' THEN
    v_rate := 0.02;
ELSE
    v_rate := 0.10;
END IF;
```

### CASE

```sql
-- Simple CASE
CASE v_status
    WHEN 'active' THEN v_label := 'Active';
    WHEN 'inactive' THEN v_label := 'Inactive';
    ELSE v_label := 'Unknown';
END CASE;

-- Searched CASE
CASE
    WHEN v_amount > 1000 THEN v_tier := 'high';
    WHEN v_amount > 100  THEN v_tier := 'medium';
    ELSE v_tier := 'low';
END CASE;
```

### Loops

```sql
-- Basic LOOP with EXIT
LOOP
    FETCH cur INTO v_row;
    EXIT WHEN NOT FOUND;
    -- process v_row
END LOOP;

-- FOR loop over integer range
FOR i IN 1..10 LOOP
    RAISE NOTICE 'Iteration %', i;
END LOOP;

-- FOR loop over query results
FOR v_rec IN SELECT id, name FROM users WHERE active LOOP
    RAISE NOTICE 'User: % %', v_rec.id, v_rec.name;
END LOOP;

-- FOREACH over array
FOREACH v_element IN ARRAY v_arr LOOP
    RAISE NOTICE 'Element: %', v_element;
END LOOP;

-- WHILE loop
WHILE v_count < 100 LOOP
    v_count := v_count + 1;
END LOOP;
```

## Exception Handling

```sql
BEGIN
    INSERT INTO orders (id, total) VALUES (p_id, p_total);
EXCEPTION
    WHEN unique_violation THEN
        RAISE NOTICE 'Order % already exists, updating', p_id;
        UPDATE orders SET total = p_total WHERE id = p_id;
    WHEN foreign_key_violation THEN
        RAISE EXCEPTION 'Invalid reference in order %', p_id;
    WHEN OTHERS THEN
        -- Capture full error context
        DECLARE
            v_msg    text;
            v_detail text;
            v_hint   text;
        BEGIN
            GET STACKED DIAGNOSTICS
                v_msg    = MESSAGE_TEXT,
                v_detail = PG_EXCEPTION_DETAIL,
                v_hint   = PG_EXCEPTION_HINT;
            RAISE WARNING 'Unexpected error: % (detail: %, hint: %)',
                v_msg, v_detail, v_hint;
            RAISE;  -- re-raise original exception
        END;
END;
```

### RAISE Levels

```sql
RAISE DEBUG 'detailed debug info: %', v_data;
RAISE LOG 'server log message';
RAISE NOTICE 'informational: %', v_info;      -- most common for dev
RAISE WARNING 'something unexpected: %', v_msg;
RAISE EXCEPTION 'fatal: %', v_msg
    USING ERRCODE = 'P0001',
          DETAIL  = 'More context here',
          HINT    = 'Try doing X instead';
```

## Set-Returning Functions

```sql
-- RETURN NEXT (row-by-row)
CREATE OR REPLACE FUNCTION active_users_with_orders()
RETURNS SETOF record
LANGUAGE plpgsql
AS $$
DECLARE
    v_rec record;
BEGIN
    FOR v_rec IN
        SELECT u.id, u.name, count(o.id) AS order_count
        FROM users u JOIN orders o ON o.user_id = u.id
        WHERE u.active
        GROUP BY u.id, u.name
    LOOP
        RETURN NEXT v_rec;
    END LOOP;
END;
$$;

-- RETURN QUERY (preferred, simpler)
CREATE OR REPLACE FUNCTION get_active_users()
RETURNS TABLE(user_id bigint, user_name text)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT id, name FROM users WHERE active ORDER BY name;
END;
$$;

-- Usage
SELECT * FROM get_active_users();
```

## Triggers

```sql
-- Trigger function (must return trigger)
CREATE OR REPLACE FUNCTION audit_changes()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, op, new_data, changed_at)
        VALUES (TG_TABLE_NAME, 'INSERT', to_jsonb(NEW), now());
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, op, old_data, new_data, changed_at)
        VALUES (TG_TABLE_NAME, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW), now());
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, op, old_data, changed_at)
        VALUES (TG_TABLE_NAME, 'DELETE', to_jsonb(OLD), now());
        RETURN OLD;
    END IF;
END;
$$;

-- Row-level trigger (fires once per affected row)
CREATE TRIGGER trg_orders_audit
    AFTER INSERT OR UPDATE OR DELETE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION audit_changes();

-- Statement-level trigger (fires once per statement)
CREATE TRIGGER trg_orders_stmt
    AFTER INSERT ON orders
    FOR EACH STATEMENT
    EXECUTE FUNCTION notify_batch_insert();

-- BEFORE trigger to modify data before insert
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_set_updated
    BEFORE INSERT OR UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- Transition tables (PG10+, statement-level only)
CREATE TRIGGER trg_orders_transition
    AFTER INSERT ON orders
    REFERENCING NEW TABLE AS new_orders
    FOR EACH STATEMENT
    EXECUTE FUNCTION process_new_orders();
-- Inside function: SELECT * FROM new_orders
```

## DO Blocks (Anonymous Code)

```sql
DO $$
DECLARE
    v_count integer;
BEGIN
    SELECT count(*) INTO v_count FROM users WHERE active;
    RAISE NOTICE 'Active users: %', v_count;

    IF v_count > 1000 THEN
        PERFORM pg_notify('admin', 'High user count: ' || v_count);
    END IF;
END;
$$;
```

## Composite Types and Domains

```sql
-- Custom composite type
CREATE TYPE address AS (
    street  text,
    city    text,
    state   text,
    zip     text
);

CREATE TABLE customers (
    id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name    text NOT NULL,
    home    address,
    work    address
);

-- Access composite fields
SELECT (home).city, (work).zip FROM customers;

-- Custom domain with constraints
CREATE DOMAIN email_address AS text
    CHECK (VALUE ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

CREATE DOMAIN positive_int AS integer
    CHECK (VALUE > 0);
```

## Security Definer vs Invoker

```sql
-- Runs with privileges of the function owner (like SUID)
CREATE FUNCTION admin_only_reset(p_user_id bigint)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public  -- always set search_path with SECURITY DEFINER
AS $$
BEGIN
    UPDATE users SET password_hash = NULL WHERE id = p_user_id;
END;
$$;

-- Default: SECURITY INVOKER (runs with caller's privileges)
```
