"""Execute a single Flow chapter pipeline with isolated task turns and dual review."""

task_schema = {
    "type": "object",
    "properties": {
        "task_path": {"type": "string"},
        "commit": {"type": "string"},
        "status": {"type": "string"},
    },
    "required": ["task_path", "commit", "status"],
}

review_schema = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["PASS", "NEEDS_WORK"]},
        "summary": {"type": "string"},
    },
    "required": ["verdict", "summary"],
}

flow_id = str(args.get("flow_id", ""))
chapter_id = str(args.get("chapter_id", ""))
task_paths = list(args.get("tasks", []))
base_commit = str(args.get("base_commit", "HEAD~1"))

phase(f"Execute Chapter {chapter_id}")
log(f"Running {len(task_paths)} vertical-slice task(s) for {flow_id}/{chapter_id}")

task_results = await pipeline(
    task_paths,
    lambda task_path: agent(
        f"Execute approved Flow task worksheet `{task_path}` for `{flow_id}` chapter `{chapter_id}` "
        "using Public-Seam TDD, bounded reads, and one atomic local commit.",
        schema=task_schema,
        role=f"Execute {task_path.rsplit('/', 1)[-1]}",
        type_name="executor",
        workspace="inherit",
        model="inherit",
    ),
)

phase("Zero-Context Chapter Review")
git_range = f"{base_commit}..HEAD"
chapter_spec = f".agents/bundles/specs/{flow_id}/chapters/{chapter_id}/spec.md"

reviews = await parallel(
    [
        ("code-reviewer", "Chapter Correctness Review"),
        ("quality-reviewer", "Chapter Quality Review"),
    ],
    lambda item: agent(
        f"Review chapter `{flow_id}/{chapter_id}` across Git range `{git_range}` against `{chapter_spec}`.",
        schema=review_schema,
        role=item[1],
        type_name=item[0],
        workspace="inherit",
        model="inherit",
    ),
)

summary = {
    "flow_id": flow_id,
    "chapter_id": chapter_id,
    "tasks": task_results,
    "reviews": reviews,
}
log(f"Completed chapter {chapter_id} pipeline with verdicts: {[r['verdict'] for r in reviews]}")
print(summary)
