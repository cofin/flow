# MongoDB Scripting Guide (2026 Edition)

Standards for automating MongoDB tasks using `mongosh` (the modern shell) or drivers.

## 1. Tool Selection

*   **Use `mongosh`**: The legacy `mongo` shell is deprecated. `mongosh` is Node.js-based and supports modern JS syntax.
*   **Prefer Drivers**: For complex logic, writing a small Python/Node.js script with the official driver is often safer and more testable than a complex shell script.

## 2. Secure Connections

*   **URI Connection Strings**: Use standard URI format for clarity.
    ```bash
    MONGODB_URI="mongodb+srv://${USER}:${PASS}@cluster.example.com/db?retryWrites=true&w=majority"
    mongosh "$MONGODB_URI" --file script.js
    ```
*   **Auth Source**: Explicitly state `--authenticationDatabase` if not `admin`.

## 3. JavaScript Scripting (`mongosh`)

Scripts run in a JS environment. Use it!

### 3.1. Error Handling (Strict Mode)
Wrap operations in `try-catch` blocks. `mongosh` scripts don't always exit non-zero on DB error by default unless you throw.

```javascript
// script.js
'use strict';

try {
  const db = db.getSiblingDB('my_database');
  
  // Use Sessions for Transactions (if replica set/sharded)
  const session = db.getMongo().startSession();
  session.startTransaction();
  
  try {
    const coll = session.getDatabase('my_database').getCollection('users');
    const result = coll.updateOne({ id: 1 }, { $set: { active: true } });
    
    if (result.matchedCount === 0) {
      throw new Error("User not found!");
    }
    
    session.commitTransaction();
  } catch (err) {
    session.abortTransaction();
    throw err;
  } finally {
    session.endSession();
  }
  
} catch (error) {
  print('Error occurred: ' + error);
  quit(1); // Explicit non-zero exit
}
```

### 3.2. Output Formatting
Use `JSON.stringify()` for machine-readable output.

```javascript
const docs = db.users.find().toArray();
print(JSON.stringify(docs));
```

## 4. Best Practices

*   **Idempotency**: Use `update` with `upsert: true` or `updateOne` over `insert` for repeatable scripts.
*   **Read Preference**: Specify read preference (`secondaryPreferred`) in connection string for reporting scripts to reduce load on primary.
