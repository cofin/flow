# Biome Linter Overrides

Specific configurations to apply overrides for generated code, UI components, and routing structures.

## 1. Generated Code
Directories: `src/lib/api/**/*`, `src/lib/generated/**/*`

- **Status**: **DISABLED**
- **Reason**: Generated code should not be linted or formatted to avoid conflicts and speed up checks.

---

## 2. UI Components (ShadCN)
Directory: `src/components/ui/**/*`

Overrides to accommodate standard ShadCN/ui component code styles.

| Group | Rule | Status | Rationale |
|-------|------|--------|-----------|
| `performance` | `noNamespaceImport` | `off` | Standard in some components |
| `style` | `noNestedTernary` | `off` | Common in render logic |
| `suspicious` | `noArrayIndexKey` | `off` | Edge cases in lists |
| `nursery` | `noShadow` | `off` | Component scope variables |

---

## 3. Routes (TanStack Router)
Directory: `src/routes/**/*`

| Group | Rule | Status | Rationale |
|-------|------|--------|-----------|
| `style` | `useFilenamingConvention` | `off` | File-based routing requires specific naming structures (e.g., `+page.tsx` or uppercase titles). |

---

## 4. Barrel Files
Files: `src/lib/auth/index.ts`, `src/stores/index.ts`

| Group | Rule | Status | Rationale |
|-------|------|--------|-----------|
| `performance` | `noBarrelFile` | `off` | Necessary for clean public API grouping. |
