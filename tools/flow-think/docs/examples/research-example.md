# Research Example: Hypothesis Testing

This example demonstrates using `flow_think` to conduct structured research with hypothesis formation and verification.

## Scenario

Investigating why a new library might be better than the current solution for data validation. The research process forms hypotheses and tests them systematically.

---

## Step 1: Define Research Question

```json
{
  "step_number": 1,
  "estimated_total": 5,
  "purpose": "research",
  "context": "Team considering switching from Joi to Zod for data validation. Need to understand tradeoffs before committing.",
  "thought": "Research should cover: TypeScript integration, bundle size, runtime performance, ecosystem support, migration effort. Will form hypothesis about which areas Zod excels.",
  "outcome": "Research scope defined: Compare Joi vs Zod across 5 dimensions with quantifiable metrics where possible",
  "next_action": {
    "tool": "WebSearch",
    "action": "Search for Zod vs Joi comparison benchmarks",
    "parameters": { "query": "zod vs joi typescript validation benchmark 2024" },
    "expectedOutput": "Performance comparisons and community discussions"
  },
  "rationale": "Start with existing comparisons to avoid duplicating research",
  "hypothesis": "Zod provides better TypeScript integration but may have performance tradeoffs",
  "verification_status": "pending"
}
```

### Expected Response

```json
{
  "status": "flow_think_in_progress",
  "step_number": 1,
  "estimated_total": 5,
  "completed": false,
  "total_steps_recorded": 1,
  "next_action": {
    "tool": "WebSearch",
    "action": "Search for Zod vs Joi comparison benchmarks",
    "parameters": { "query": "zod vs joi typescript validation benchmark 2024" },
    "expectedOutput": "Performance comparisons and community discussions"
  },
  "hypothesis": {
    "text": "Zod provides better TypeScript integration but may have performance tradeoffs",
    "status": "pending"
  }
}
```

---

## Step 2: Analyze TypeScript Integration

```json
{
  "step_number": 2,
  "estimated_total": 5,
  "purpose": "research",
  "context": "Found several benchmark articles. Zod is TS-native, Joi requires @types/joi. Key finding: Zod schemas can be used as type definitions directly.",
  "thought": "TypeScript integration is a major differentiator. Zod's .infer utility eliminates duplicate type definitions. Joi requires manual type synchronization which causes drift.",
  "outcome": "TypeScript integration analysis:\n- Zod: Schema IS the type (z.infer<typeof schema>)\n- Joi: Schema + separate interface required\n- Zod eliminates 100% of type drift bugs\n- Developer experience significantly better with Zod",
  "next_action": "Measure bundle size impact",
  "rationale": "Bundle size affects load time - critical for frontend validation",
  "hypothesis": "Zod provides better TypeScript integration but may have performance tradeoffs",
  "verification_status": "pending",
  "confidence": 0.85,
  "tools_used": ["WebSearch"]
}
```

---

## Step 3: Evaluate Bundle Size

```json
{
  "step_number": 3,
  "estimated_total": 5,
  "purpose": "research",
  "context": "TypeScript analysis confirms Zod advantage. Now checking bundle size using bundlephobia.",
  "thought": "Bundle size comparison:\n- Zod: ~52KB minified, ~13KB gzipped\n- Joi: ~149KB minified, ~35KB gzipped\nZod is ~65% smaller. However, Joi has more validators built-in.",
  "outcome": "Bundle size analysis:\n- Zod: 13KB gzipped (core only)\n- Joi: 35KB gzipped (batteries included)\n- Zod + common plugins: ~18KB gzipped\n- Net savings: 17KB gzipped (~48% smaller)",
  "next_action": "Test runtime validation performance",
  "rationale": "Performance matters for high-volume API validation",
  "hypothesis": "Zod provides better TypeScript integration but may have performance tradeoffs",
  "verification_status": "pending",
  "confidence": 0.8,
  "external_context": {
    "zod_size_gzip": "13KB",
    "joi_size_gzip": "35KB",
    "size_reduction": "48%"
  }
}
```

---

## Step 4: Performance Testing

```json
{
  "step_number": 4,
  "estimated_total": 5,
  "purpose": "validation",
  "context": "Bundle size favors Zod. Running local benchmark with realistic payload (user registration object with nested address).",
  "thought": "Benchmark results (1M iterations):\n- Joi: 2,847ms average\n- Zod: 3,124ms average\nZod is ~10% slower in raw validation. However, when including TypeScript compilation benefits and type checking, Zod provides net positive.",
  "outcome": "Performance analysis:\n- Raw validation: Joi ~10% faster\n- With TS type generation: Zod eliminates separate type maintenance\n- Real-world impact: Negligible (<1ms per request)\n- TypeScript errors caught at compile time: Significant win",
  "next_action": "Assess migration effort and ecosystem",
  "rationale": "Migration effort determines short-term cost vs long-term benefit",
  "hypothesis": "Zod provides better TypeScript integration but may have performance tradeoffs",
  "verification_status": "confirmed",
  "confidence": 0.9,
  "tools_used": ["Bash"],
  "patterns_discovered": [
    "Raw performance benchmarks don't capture full developer productivity impact",
    "Type safety benefits compound over time as codebase grows"
  ]
}
```

---

## Step 5: Final Recommendation

```json
{
  "step_number": 5,
  "estimated_total": 5,
  "purpose": "decision",
  "context": "All research dimensions evaluated. Ready to synthesize findings into recommendation.",
  "thought": "Summary of findings:\n1. TypeScript: Zod significantly better (type inference)\n2. Bundle: Zod 48% smaller\n3. Performance: Joi 10% faster (negligible in practice)\n4. Ecosystem: Both mature, Zod growing faster\n5. Migration: 2-3 days for our codebase (~50 schemas)\n\nThe hypothesis was confirmed - Zod's TypeScript integration outweighs the minor performance tradeoff.",
  "outcome": "RECOMMENDATION: Migrate to Zod\n- Short-term cost: ~3 developer days\n- Long-term benefits: Eliminated type drift, smaller bundle, better DX\n- Risk: Low (gradual migration possible)",
  "next_action": {
    "tool": "Write",
    "action": "Create migration plan document",
    "parameters": { "path": "docs/adr/003-zod-migration.md" },
    "expectedOutput": "Architecture decision record with migration steps"
  },
  "rationale": "Document decision for future reference and team alignment",
  "hypothesis": "Zod provides better TypeScript integration but may have performance tradeoffs",
  "verification_status": "confirmed",
  "is_final_step": true,
  "confidence": 0.95,
  "patterns_discovered": [
    "Schema-as-type pattern eliminates entire category of bugs",
    "Bundle size savings compound across multiple entry points",
    "Migration can be incremental - coexistence is possible"
  ]
}
```

### Expected Response

```json
{
  "status": "flow_think_complete",
  "step_number": 5,
  "estimated_total": 5,
  "completed": true,
  "total_steps_recorded": 5,
  "next_action": {
    "tool": "Write",
    "action": "Create migration plan document",
    "parameters": { "path": "docs/adr/003-zod-migration.md" },
    "expectedOutput": "Architecture decision record with migration steps"
  },
  "confidence": 0.95,
  "hypothesis": {
    "text": "Zod provides better TypeScript integration but may have performance tradeoffs",
    "status": "confirmed"
  }
}
```

---

## Tips for Research with flow_think

1. **Form explicit hypotheses** - State what you expect to find before investigating
2. **Use verification_status** - Track hypothesis progression: pending -> confirmed/refuted
3. **Capture external context** - Store specific metrics in `external_context` for reference
4. **Build confidence incrementally** - Start lower, increase as evidence accumulates
5. **Record tools used** - Track which tools provided each piece of evidence
6. **End with actionable decision** - Research should culminate in clear recommendation

## Research Patterns

### Refuting a Hypothesis

```json
{
  "step_number": 3,
  "purpose": "validation",
  "thought": "Initial hypothesis was wrong. Evidence shows the opposite pattern.",
  "hypothesis": "GraphQL reduces API calls compared to REST",
  "verification_status": "refuted",
  "revision_reason": "Benchmark showed N+1 query pattern in our use case",
  "confidence": 0.85
}
```

### Pivoting Research Direction

```json
{
  "step_number": 4,
  "purpose": "exploration",
  "thought": "Original question was wrong. Real issue is not library choice but architecture.",
  "outcome": "Pivoting research from 'which library' to 'do we need this at all'",
  "estimated_total": 7,
  "confidence": 0.6,
  "uncertainty_notes": "May need additional steps to explore alternative approaches"
}
```

### Using Branching for Alternatives

```json
{
  "step_number": 4,
  "purpose": "exploration",
  "branch_from": 2,
  "branch_id": "alternative-approach",
  "branch_name": "Evaluate build-time validation instead",
  "thought": "Worth exploring if we can move validation to build time entirely",
  "confidence": 0.5
}
```

### Capturing Quantitative Evidence

```json
{
  "purpose": "research",
  "external_context": {
    "benchmark_results": {
      "option_a": { "latency_p99": "45ms", "memory_mb": 128 },
      "option_b": { "latency_p99": "32ms", "memory_mb": 256 }
    },
    "sample_size": 10000,
    "confidence_interval": "95%"
  },
  "confidence": 0.9
}
```
