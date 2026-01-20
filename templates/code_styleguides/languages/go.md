# Go Style Guide

Idiomatic Go with simplicity and clarity.

## Core Rules

### Formatting

- **Always use `gofmt`** - This is non-negotiable
- Use tabs for indentation (gofmt handles this)
- No strict line length limit - let gofmt wrap

### Naming

| Concept | Convention | Example |
|---------|------------|---------|
| Exported | `PascalCase` | `UserService`, `GetUser` |
| Unexported | `camelCase` | `userCache`, `getConfig` |
| Packages | lowercase, single word | `users`, `config` |
| Interfaces | Method + `-er` suffix | `Reader`, `Writer`, `Closer` |
| Getters | No `Get` prefix | `Owner()` not `GetOwner()` |

```go
// Good: Exported vs unexported
type UserService struct {
    cache map[string]User  // unexported field
}

func (s *UserService) GetUser(id string) User {  // exported method
    return s.cache[id]
}

// Good: Interface naming
type Reader interface {
    Read(p []byte) (n int, err error)
}
```

## Control Structures

```go
// If with initialization
if err := doSomething(); err != nil {
    return err
}

// Switch without expression (cleaner if-else)
switch {
case n < 0:
    return "negative"
case n == 0:
    return "zero"
default:
    return "positive"
}

// For-range for iteration
for i, item := range items {
    process(i, item)
}

// For-range with blank identifier
for _, item := range items {
    process(item)
}
```

## Functions

```go
// Multiple returns for result and error
func GetUser(id string) (User, error) {
    user, err := db.Find(id)
    if err != nil {
        return User{}, fmt.Errorf("get user %s: %w", id, err)
    }
    return user, nil
}

// Named return parameters (use sparingly, for documentation)
func Split(path string) (dir, file string) {
    // ...
}

// Defer for cleanup
func ReadFile(path string) ([]byte, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, err
    }
    defer f.Close()

    return io.ReadAll(f)
}
```

## Error Handling

```go
// Always check errors explicitly
result, err := doSomething()
if err != nil {
    return fmt.Errorf("doing something: %w", err)
}

// Wrap errors with context
if err := processFile(path); err != nil {
    return fmt.Errorf("process file %s: %w", path, err)
}

// Custom error types
type NotFoundError struct {
    Resource string
    ID       string
}

func (e *NotFoundError) Error() string {
    return fmt.Sprintf("%s not found: %s", e.Resource, e.ID)
}

// Never ignore errors
// Bad:
result, _ := doSomething()

// Good:
result, err := doSomething()
if err != nil {
    log.Printf("warning: %v", err)
}
```

## Data Structures

```go
// new vs make
// new(T) - allocates zeroed memory, returns *T
ptr := new(User)

// make(T, ...) - creates and initializes slices, maps, channels
slice := make([]int, 0, 100)  // len=0, cap=100
m := make(map[string]int)
ch := make(chan int, 10)

// Slice operations
items = append(items, newItem)
copy(dest, source)

// Map with "comma ok"
value, ok := m[key]
if !ok {
    // key not found
}
```

## Interfaces

```go
// Implicit implementation - no "implements" keyword
type Reader interface {
    Read(p []byte) (n int, err error)
}

type File struct { /* ... */ }

func (f *File) Read(p []byte) (n int, err error) {
    // Implementation
}

// File now implements Reader automatically

// Prefer small interfaces
type Closer interface {
    Close() error
}

type ReadCloser interface {
    Reader
    Closer
}
```

## Concurrency

```go
// Goroutine
go processItem(item)

// Channel
ch := make(chan Result, 10)

go func() {
    result := compute()
    ch <- result
}()

result := <-ch

// Select for multiple channels
select {
case result := <-resultCh:
    process(result)
case err := <-errCh:
    handleError(err)
case <-ctx.Done():
    return ctx.Err()
}

// Share by communicating, don't communicate by sharing
// Bad: Shared memory with mutex
// Good: Send data through channels
```

## Best Practices

- Accept interfaces, return structs
- Keep packages focused and small
- Use context for cancellation and timeouts
- Don't panic in library code
- Write table-driven tests
- Use `go vet` and `staticcheck`

## Anti-Patterns

```go
// Bad: Unnecessary getter prefix
func (u *User) GetName() string { ... }

// Good: Just the field name
func (u *User) Name() string { ... }

// Bad: Ignoring error
result, _ := riskyOperation()

// Bad: Naked returns in long functions
func complexOperation() (result int, err error) {
    // 50 lines of code...
    return  // What's being returned?
}

// Bad: Init functions with side effects
func init() {
    db = connectToDatabase()  // Side effect!
}

// Good: Explicit initialization
func NewService() (*Service, error) {
    db, err := connectToDatabase()
    // ...
}
```

## Tooling

- **Formatter**: `gofmt` or `goimports`
- **Linter**: `golangci-lint`
- **Build**: `go build`
- **Test**: `go test`
