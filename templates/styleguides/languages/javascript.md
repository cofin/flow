# JavaScript Style Guide

Modern JavaScript with ES modules and functional patterns.

## Core Rules

### Variable Declarations
```javascript
// Always use const by default
const items = [];

// Use let only when reassignment is needed
let count = 0;

// Never use var - it's forbidden
```

### Modules
```javascript
// Use ES modules exclusively
import { fetchUsers, createUser } from './api.js';
import { formatDate } from '../utils/date.js';

// Named exports only - no default exports
export { UserService };
export { validateEmail, validatePhone };

// The .js extension is mandatory in import paths
import { helper } from './helper.js';  // Good
import { helper } from './helper';     // Bad
```

### Functions
```javascript
// Prefer function declarations for named functions
function calculateTotal(items) {
  return items.reduce((sum, item) => sum + item.price, 0);
}

// Use arrow functions for callbacks
const doubled = items.map((item) => item.value * 2);

// Use arrow functions in nested contexts to preserve this
class Counter {
  constructor() {
    this.count = 0;
  }

  start() {
    setInterval(() => {
      this.count++;  // 'this' is correctly bound
    }, 1000);
  }
}
```

## Naming Conventions

| Concept | Convention | Example |
|---------|------------|---------|
| Classes | `PascalCase` | `UserService` |
| Functions | `camelCase` | `getUserById` |
| Variables | `camelCase` | `currentUser` |
| Constants | `SCREAMING_SNAKE_CASE` | `MAX_RETRIES` |
| Files | `kebab-case` or `snake_case` | `user-service.js` |

## Formatting

```javascript
// Braces required for all control structures
if (condition) {
  doSomething();
}

// K&R style braces
function example() {
  if (condition) {
    return true;
  } else {
    return false;
  }
}

// Always use semicolons - no ASI reliance
const value = getValue();
doSomething();

// Single quotes for strings
const name = 'John';

// Template literals for interpolation
const message = `Hello, ${name}!`;
```

## Objects and Arrays

```javascript
// Use literal syntax, not constructors
const items = [];           // Good
const items = new Array();  // Bad

const obj = {};             // Good
const obj = new Object();   // Bad

// Use shorthand properties
const name = 'John';
const user = { name, email };  // { name: name, email: email }

// Use trailing commas
const config = {
  host: 'localhost',
  port: 3000,
};
```

## Control Flow

```javascript
// Always use strict equality
if (value === null) { ... }
if (count !== 0) { ... }

// Never use == or !=
if (value == null) { ... }  // Bad

// Prefer for-of for iteration
for (const item of items) {
  process(item);
}

// Use for-in only for dict-style objects
for (const key in config) {
  if (Object.hasOwn(config, key)) {
    console.log(key, config[key]);
  }
}
```

## Async Patterns

```javascript
// Prefer async/await
async function fetchUser(id) {
  const response = await fetch(`/api/users/${id}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

// Handle errors appropriately
async function loadData() {
  try {
    const data = await fetchData();
    return processData(data);
  } catch (error) {
    console.error('Failed to load data:', error);
    throw error;  // Re-throw for caller to handle
  }
}

// Use Promise.all for parallel operations
const [users, posts] = await Promise.all([
  fetchUsers(),
  fetchPosts(),
]);
```

## Error Handling

```javascript
// Create specific error types
class NotFoundError extends Error {
  constructor(resource, id) {
    super(`${resource} not found: ${id}`);
    this.name = 'NotFoundError';
    this.resource = resource;
    this.id = id;
  }
}

// Don't swallow errors
try {
  await riskyOperation();
} catch (error) {
  // Bad: Silent failure
  // catch (error) {}

  // Good: Log and rethrow or handle
  console.error('Operation failed:', error);
  throw error;
}
```

## Classes

```javascript
class UserService {
  #cache;  // Private field

  constructor(apiClient) {
    this.apiClient = apiClient;
    this.#cache = new Map();
  }

  async getUser(id) {
    if (this.#cache.has(id)) {
      return this.#cache.get(id);
    }

    const user = await this.apiClient.get(`/users/${id}`);
    this.#cache.set(id, user);
    return user;
  }
}

// Don't use getter/setter properties
// Use normal methods instead
class Bad {
  get name() { return this._name; }
  set name(value) { this._name = value; }
}

class Good {
  getName() { return this._name; }
  setName(value) { this._name = value; }
}
```

## JSDoc

```javascript
/**
 * Calculate the total price including tax.
 * @param {Array<{price: number}>} items - Items to calculate
 * @param {number} taxRate - Tax rate as decimal (e.g., 0.08)
 * @returns {number} Total price with tax
 */
function calculateTotal(items, taxRate) {
  const subtotal = items.reduce((sum, item) => sum + item.price, 0);
  return subtotal * (1 + taxRate);
}
```

## Disallowed Features

- `with` statement - forbidden
- Dynamic code execution/evaluation - forbidden for security
- Modifying builtin prototypes (`Array.prototype.custom = ...`)
- Relying on automatic semicolon insertion

## Tooling

- **Formatter**: `prettier`
- **Linter**: `eslint`
- **Runtime**: Node.js, Bun, or browser
- **Test runner**: `vitest`, `jest`

## Anti-Patterns

```javascript
// Bad: Using var
var name = 'John';

// Bad: Weak equality
if (value == null) { ... }

// Bad: Relying on ASI
const a = 1
const b = 2

// Bad: Default exports
export default function myFunction() { ... }

// Bad: Modifying builtins
Array.prototype.first = function() { return this[0]; };

// Bad: Using this outside appropriate contexts
const handler = {
  onClick: function() {
    this.doSomething();  // 'this' may be wrong
  }
};

// Good: Arrow function or bind
const handler = {
  onClick: () => {
    handler.doSomething();
  }
};
```
