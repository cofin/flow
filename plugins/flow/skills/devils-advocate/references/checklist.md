# Devil's Advocate Review Checklist

Work through these questions for the code, design, or proposal under review. For each item that raises a concern, explain what the concern is and what should be done about it.

1. **Does this change make assumptions that aren't verified?**
   Look for implicit "we assume X is always true" or "we assume the upstream always does Y." If the assumption is wrong, what breaks?

2. **What happens when this fails? Is the failure mode acceptable?**
   Consider: the external call times out, the database is unavailable, the input is malformed, a dependency returns an unexpected value. Are failures caught? Are they surfaced clearly? Do they fail safe?

3. **Will this be harder to change later than it is to get right now?**
   Look for decisions that will become load-bearing: data model choices, API contracts, coupling to third-party behavior. The cost of changing these grows over time — is the current design worth that future cost?

4. **Are there edge cases that aren't tested?**
   Look for: empty inputs, large inputs, concurrent access, boundary values, the user who does something unexpected. Are the interesting edge cases covered, or only the happy path?

5. **Does this introduce coupling that will spread?**
   Look for direct dependencies on implementation details, shared mutable state, or implicit ordering requirements. Will this coupling make future changes harder? Will it make testing harder?

6. **Is there a simpler approach that was not considered?**
   Could this be done with less code, fewer abstractions, or a more direct solution? Complexity should earn its keep — if a simpler approach exists that meets requirements, it's worth naming.

7. **What would a new team member find confusing about this?**
   Look for: surprising behavior, non-obvious invariants, names that don't match what things do, logic that requires context to understand. These are maintenance risks that compound over time.

8. **Does this match what the spec/requirements actually asked for?**
   Compare what was built against what was asked. Are there features added that weren't requested (scope creep)? Are there requirements not addressed? Does the implementation match the stated intent?
