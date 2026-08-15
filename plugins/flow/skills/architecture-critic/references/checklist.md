# Architecture Review Checklist

Work through each item. Flag anything that raises a concern. For clean items, a brief note is sufficient. For concerns, explain the structural problem and its long-term consequence.

1. **Boundaries** — Does each component have one clear responsibility? Can you describe what a component does without mentioning how other components work?

2. **Interfaces** — Are interfaces between components well-defined? Could you swap the implementation without changing consumers?

3. **Coupling** — What would break if you changed this component? Is the blast radius proportional to the change?

4. **Cohesion** — Do things that change together live together? Are there cases where a single feature change requires touching many unrelated files?

5. **Abstraction level** — Are abstractions justified by actual use cases (2+ consumers) or speculative? Are there missing abstractions where code is duplicated across boundaries?

6. **Data flow** — Is it clear how data moves through the system? Are there hidden side channels or global state?

7. **Scaling characteristics** — What happens at 10x load? Are there obvious bottlenecks (single database, synchronous calls in hot paths)?

8. **Testability** — Can components be tested in isolation? Are test boundaries aligned with component boundaries?

9. **Simplicity** — Could this design be simpler and still meet requirements? Is complexity earning its keep?
