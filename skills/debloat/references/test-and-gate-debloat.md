# Test and gate debloat

Use this reference before deleting tests or replacing repository gates.

## Classify the contract

- **Observable behavior:** retain direct coverage or replace it with equally direct behavior coverage.
- **Public contract:** retain coverage when compatibility depends on the signature, export, schema, immutability, or protocol shape.
- **Operational property:** retain coverage when structure affects memory, hashing, compilation, reflection, serialization, or import isolation.
- **Implementation snapshot:** replace exact shape with an invariant or behavior check when the shape has no supported meaning.
- **Duplicate coverage:** remove only after another test is shown to exercise the same contract and failure mode.

Structural does not mean useless. Slots may enforce a memory target, frozen state may guarantee hashability, coroutine introspection may define a protocol, and `__all__` may be supported API.

## Replacement-first sequence

1. Run the focused baseline and capture the relevant contract or coverage result.
2. Add the replacement invariant, configured gate, or consolidated test.
3. Inject a representative violation into a temporary tree or isolated fixture.
4. Require the replacement to return non-zero with the expected diagnostic.
5. Restore the violation and require the replacement to pass.
6. Remove only the superseded assertion or test.
7. Rerun focused and aggregate verification; compare affected-file coverage when behavioral execution could be lost.

Do not require a repository-wide coverage snapshot for metadata-only assertions that execute no package code. Do compare missing lines and branches when deleting a behavioral path, fixture, error case, or object construction.

## Common replacements

- Replace large export snapshots with resolution, privacy, and required-public-name invariants unless the exact export tuple is versioned API.
- Parametrize frozen/slotted contracts only when the property applies uniformly and exceptions are explicit.
- Prefer maintained parsers, linters, type checkers, and build checks over source scanners when they express the complete rule.
- Keep subprocess tests when fresh-interpreter state, installed-package behavior, environment variables, or absent optional dependencies are the contract.

## Gate proof requirements

Exercise equivalent spellings when relevant, such as direct imports, from-imports, aliases, and relative imports. Assert both the non-zero status and the expected diagnostic. Verify the canonical command's discovery scope: some hook runners ignore untracked files while other tools scan the filesystem.

Coverage equivalence alone does not prove semantic equivalence. Preserve distinct assertions for contractual errors, state transitions, side effects, ordering, and boundary values even when they execute the same lines.
