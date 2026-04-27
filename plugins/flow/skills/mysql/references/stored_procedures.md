# Stored Procedures & Functions

## Overview

MySQL stored routines encapsulate reusable SQL logic on the server side. This reference covers procedures, functions, control flow, error handling, cursors, triggers, and scheduled events.

---

## CREATE PROCEDURE / CREATE FUNCTION

```sql
-- Procedure: may return multiple result sets, uses OUT/INOUT parameters.
DELIMITER $$
CREATE PROCEDURE get_customer_orders(
    IN  p_customer_id INT,
    OUT p_order_count INT
)
BEGIN
    SELECT COUNT(*) INTO p_order_count
      FROM orders
     WHERE customer_id = p_customer_id;

    -- Return a result set as well.
    SELECT id, total, created_at
      FROM orders
     WHERE customer_id = p_customer_id
     ORDER BY created_at DESC;
END$$
DELIMITER ;

-- Call the procedure.
CALL get_customer_orders(42, @cnt);
SELECT @cnt AS order_count;
```

```sql
-- Function: returns a single scalar value. Must be deterministic or
-- declared with appropriate characteristics for replication safety.
DELIMITER $$
CREATE FUNCTION calculate_tax(
    subtotal DECIMAL(12,2),
    tax_rate DECIMAL(5,4)
)
RETURNS DECIMAL(12,2)
DETERMINISTIC
NO SQL
BEGIN
    RETURN subtotal * tax_rate;
END$$
DELIMITER ;

-- Use in queries.
SELECT id, subtotal, calculate_tax(subtotal, 0.0825) AS tax FROM orders;
```

---

## Variables and Control Flow

### Variables

```sql
DELIMITER $$
CREATE PROCEDURE demo_variables()
BEGIN
    -- Local variables (must be declared before any other statements).
    DECLARE v_count INT DEFAULT 0;
    DECLARE v_name  VARCHAR(100);
    DECLARE v_done  BOOLEAN DEFAULT FALSE;

    SET v_count = 10;
    SELECT name INTO v_name FROM users WHERE id = 1;
END$$
DELIMITER ;
```

### IF / CASE

```sql
DELIMITER $$
CREATE PROCEDURE categorize_order(IN p_total DECIMAL(12,2), OUT p_tier VARCHAR(20))
BEGIN
    IF p_total >= 1000 THEN
        SET p_tier = 'premium';
    ELSEIF p_total >= 100 THEN
        SET p_tier = 'standard';
    ELSE
        SET p_tier = 'basic';
    END IF;
END$$
DELIMITER ;
```

```sql
-- CASE expression in a procedure.
DELIMITER $$
CREATE FUNCTION order_priority(status VARCHAR(20))
RETURNS INT
DETERMINISTIC
NO SQL
BEGIN
    RETURN CASE status
        WHEN 'urgent'    THEN 1
        WHEN 'high'      THEN 2
        WHEN 'normal'    THEN 3
        ELSE 4
    END;
END$$
DELIMITER ;
```

### LOOP / WHILE / REPEAT

```sql
DELIMITER $$
CREATE PROCEDURE loop_examples()
BEGIN
    DECLARE v_i INT DEFAULT 0;

    -- WHILE loop
    WHILE v_i < 10 DO
        SET v_i = v_i + 1;
    END WHILE;

    -- REPEAT loop (executes at least once, like do-while)
    SET v_i = 0;
    REPEAT
        SET v_i = v_i + 1;
    UNTIL v_i >= 10
    END REPEAT;

    -- LOOP with labeled LEAVE (break) and ITERATE (continue)
    SET v_i = 0;
    my_loop: LOOP
        SET v_i = v_i + 1;
        IF v_i = 5 THEN
            ITERATE my_loop;  -- skip to next iteration
        END IF;
        IF v_i >= 10 THEN
            LEAVE my_loop;    -- exit loop
        END IF;
    END LOOP my_loop;
END$$
DELIMITER ;
```

---

## Cursors

```sql
-- Cursors iterate row-by-row over a result set.
-- Always declare the NOT FOUND handler to detect end-of-cursor.
DELIMITER $$
CREATE PROCEDURE process_inactive_users()
BEGIN
    DECLARE v_user_id INT;
    DECLARE v_email   VARCHAR(255);
    DECLARE v_done    BOOLEAN DEFAULT FALSE;

    DECLARE cur CURSOR FOR
        SELECT id, email FROM users
         WHERE last_login < NOW() - INTERVAL 1 YEAR;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = TRUE;

    OPEN cur;

    read_loop: LOOP
        FETCH cur INTO v_user_id, v_email;
        IF v_done THEN
            LEAVE read_loop;
        END IF;

        -- Process each row.
        INSERT INTO inactive_user_log (user_id, email, logged_at)
        VALUES (v_user_id, v_email, NOW());
    END LOOP;

    CLOSE cur;
END$$
DELIMITER ;
```

---

## Error Handling

### DECLARE HANDLER

```sql
DELIMITER $$
CREATE PROCEDURE safe_insert(IN p_name VARCHAR(100))
BEGIN
    -- Handler for duplicate key violation (SQLSTATE '23000', errno 1062).
    DECLARE EXIT HANDLER FOR 1062
    BEGIN
        SELECT CONCAT('Duplicate entry for: ', p_name) AS error_message;
    END;

    -- Handler for any SQL exception.
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        GET DIAGNOSTICS CONDITION 1
            @err_no = MYSQL_ERRNO,
            @err_msg = MESSAGE_TEXT;
        SELECT @err_no AS errno, @err_msg AS message;
        ROLLBACK;
    END;

    START TRANSACTION;
    INSERT INTO categories (name) VALUES (p_name);
    COMMIT;
END$$
DELIMITER ;
```

### SIGNAL / RESIGNAL

```sql
DELIMITER $$
CREATE PROCEDURE validate_age(IN p_age INT)
BEGIN
    IF p_age < 0 OR p_age > 150 THEN
        -- Raise a custom error. SQLSTATE '45000' = user-defined condition.
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Age must be between 0 and 150',
                MYSQL_ERRNO = 50001;
    END IF;
END$$
DELIMITER ;
```

```sql
-- RESIGNAL re-raises the current exception, optionally modifying it.
DELIMITER $$
CREATE PROCEDURE wrapped_insert()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        RESIGNAL SET MESSAGE_TEXT = 'wrapped_insert failed';
    END;

    INSERT INTO audit_log (event) VALUES ('test');
END$$
DELIMITER ;
```

### Common SQLSTATE Codes

| SQLSTATE | Meaning                     | MySQL Errno |
|----------|-----------------------------|-------------|
| `02000`  | No data / NOT FOUND         | 1329        |
| `23000`  | Integrity constraint violation | 1062, 1452 |
| `40001`  | Deadlock / serialization failure | 1213    |
| `42000`  | Syntax error / access denied | 1064, 1044 |
| `45000`  | User-defined condition      | (custom)    |
| `HY000`  | General error               | (varies)    |

---

## Prepared Statements in Stored Procedures

```sql
-- Use PREPARE/EXECUTE for dynamic SQL inside procedures.
-- Always deallocate to avoid memory leaks.
DELIMITER $$
CREATE PROCEDURE dynamic_count(IN p_table VARCHAR(64), OUT p_count BIGINT)
BEGIN
    -- Validate identifier to prevent SQL injection.
    IF p_table NOT REGEXP '^[a-zA-Z_][a-zA-Z0-9_]*$' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid table name';
    END IF;

    SET @sql = CONCAT('SELECT COUNT(*) INTO @cnt FROM `', p_table, '`');
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
    SET p_count = @cnt;
END$$
DELIMITER ;
```

---

## Triggers

```sql
-- BEFORE INSERT: validate or transform data before it hits the table.
DELIMITER $$
CREATE TRIGGER trg_orders_before_insert
BEFORE INSERT ON orders
FOR EACH ROW
BEGIN
    IF NEW.total < 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Order total cannot be negative';
    END IF;
    SET NEW.created_at = COALESCE(NEW.created_at, NOW());
END$$
DELIMITER ;

-- AFTER UPDATE: audit trail.
DELIMITER $$
CREATE TRIGGER trg_orders_after_update
AFTER UPDATE ON orders
FOR EACH ROW
BEGIN
    IF OLD.status <> NEW.status THEN
        INSERT INTO order_audit (order_id, old_status, new_status, changed_at)
        VALUES (NEW.id, OLD.status, NEW.status, NOW());
    END IF;
END$$
DELIMITER ;

-- AFTER DELETE: cascade cleanup.
DELIMITER $$
CREATE TRIGGER trg_users_after_delete
AFTER DELETE ON users
FOR EACH ROW
BEGIN
    DELETE FROM user_preferences WHERE user_id = OLD.id;
END$$
DELIMITER ;
```

**Trigger limitations:** MySQL triggers cannot call stored procedures that return result sets, cannot use PREPARE/EXECUTE, and only one trigger per timing/event combination per table (before 5.7.2, extended in 8.0).

---

## Events (Scheduled Tasks)

```sql
-- Enable the event scheduler (must be ON at the server level).
SET GLOBAL event_scheduler = ON;

-- Create a recurring event to purge old logs every day at midnight.
CREATE EVENT evt_purge_old_logs
ON SCHEDULE EVERY 1 DAY
STARTS '2026-03-27 00:00:00'
DO
    DELETE FROM application_logs WHERE created_at < NOW() - INTERVAL 90 DAY;

-- One-time event.
CREATE EVENT evt_one_time_cleanup
ON SCHEDULE AT '2026-04-01 03:00:00'
DO
    CALL archive_old_orders();

-- Alter or disable an event.
ALTER EVENT evt_purge_old_logs DISABLE;

-- Drop an event.
DROP EVENT IF EXISTS evt_one_time_cleanup;
```

---

## Best Practices and Anti-Patterns

### Best Practices

- Keep procedures focused: one procedure, one responsibility.
- Use transactions explicitly (`START TRANSACTION` / `COMMIT` / `ROLLBACK`).
- Always declare error handlers to prevent silent failures.
- Use `DETERMINISTIC` / `NO SQL` / `READS SQL DATA` characteristics accurately for replication and optimizer.
- Validate dynamic identifiers with regex before string concatenation.
- Prefer set-based operations over cursors; cursors process row-by-row and are significantly slower.

### Anti-Patterns

- **Cursors for batch processing.** Use `INSERT ... SELECT`, `UPDATE ... JOIN`, or `DELETE ... JOIN` instead.
- **Nested cursors.** Refactor into JOINs or temporary tables.
- **Missing DEALLOCATE PREPARE.** Leaks memory from the prepared statement cache.
- **Business logic in triggers.** Triggers are invisible to application developers and make debugging harder. Prefer application-layer logic or stored procedures called explicitly.
- **SELECT * in stored procedures.** Fragile if table schema changes; always list columns explicitly.
- **Ignoring sql_mode.** Procedures written under lax sql_mode may break under `STRICT_TRANS_TABLES`. Always develop with strict mode enabled.

---

## Official References

- CREATE PROCEDURE: <https://dev.mysql.com/doc/refman/8.0/en/create-procedure.html>
- CREATE TRIGGER: <https://dev.mysql.com/doc/refman/8.0/en/create-trigger.html>
- CREATE EVENT: <https://dev.mysql.com/doc/refman/8.0/en/create-event.html>
- Error Handling: <https://dev.mysql.com/doc/refman/8.0/en/declare-handler.html>
- SIGNAL/RESIGNAL: <https://dev.mysql.com/doc/refman/8.0/en/signal.html>
