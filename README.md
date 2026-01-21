# Flow Extension for Gemini CLI

**Measure twice, code once.**

Flow is a Gemini CLI extension that enables **Context-Driven Development**. It turns the Gemini CLI into a proactive project manager that follows a strict protocol to specify, plan, and implement software features and bug fixes.

Instead of just writing code, Flow ensures a consistent, high-quality lifecycle for every task: **Context -> Spec & Plan -> Implement**.

The philosophy behind Flow is simple: control your code. By treating context as a managed artifact alongside your code, you transform your repository into a single source of truth that drives every agent interaction with deep, persistent project awareness.

## Features

- **Plan before you build**: Create specs and plans that guide the agent for new and existing codebases.
- **Maintain context**: Ensure AI follows style guides, tech stack choices, and product goals.
- **Iterate safely**: Review plans before code is written, keeping you firmly in the loop.
- **Work as a team**: Set project-level context for your product, tech stack, and workflow preferences that become a shared foundation for your team.
- **Build on existing projects**: Intelligent initialization for both new (Greenfield) and existing (Brownfield) projects.
- **Smart revert**: A git-aware revert command that understands logical units of work (PRDs, phases, tasks) rather than just commit hashes.
- **Configurable directory**: Choose where Flow stores specification files (defaults to `.agent/specs/`).

## Installation

Install the Flow extension by running the following command from your terminal:

```bash
gemini extensions install https://github.com/cofin/flow --auto-update
```

The `--auto-update` is optional: if specified, it will update to new versions as they are released.

## Usage

Flow is designed to manage the entire lifecycle of your development tasks.

**Note on Token Consumption:** Flow's context-driven approach involves reading and analyzing your project's context, specifications, and plans. This can lead to increased token consumption, especially in larger projects or during extensive planning and implementation phases. You can check the token consumption in the current session by running `/stats model`.

### 1. Set Up the Project (Run Once)

When you run `/flow:setup`, Flow helps you define the core components of your project context. This context is then used for building new components or features by you or anyone on your team.

- **Product**: Define project context (e.g. users, product goals, high-level features).
- **Product guidelines**: Define standards (e.g. prose style, brand messaging, visual identity).
- **Tech stack**: Configure technical preferences (e.g. language, database, frameworks).
- **Workflow**: Set team preferences (e.g. TDD, commit strategy). Uses [workflow.md](templates/workflow.md) as a customizable template.
- **Directory configuration**: Choose where to store specification files (default: `.agent/specs/`).

**Generated Artifacts:**

- `.agent/specs/product.md`
- `.agent/specs/product-guidelines.md`
- `.agent/specs/tech-stack.md`
- `.agent/specs/workflow.md`
- `.agent/code-styleguides/`
- `.agent/specs/prds.md`

```bash
/flow:setup
```

### 2. Start a New PRD (Feature or Bug)

When you're ready to take on a new feature or bug fix, run `/flow:prd`. This initializes a **PRD** (Product Requirements Document) — a high-level unit of work. Flow helps you generate two critical artifacts:

- **Specs**: The detailed requirements for the specific job. What are we building and why?
- **Plan**: An actionable to-do list containing phases, tasks, and sub-tasks.

**Generated Artifacts:**

- `.agent/specs/<prd_id>/spec.md` (e.g., `.agent/specs/dark-mode/spec.md`)
- `.agent/specs/<prd_id>/plan.md`
- `.agent/specs/<prd_id>/metadata.json`

**Note:** PRD IDs use simple slugs (e.g., `dark-mode`, `user-auth`). When archived, they are renamed with timestamps (e.g., `prd_20260121_dark-mode`).

```bash
/flow:prd
# OR with a description
/flow:prd "Add a dark mode toggle to the settings page"
```

### 3. Implement the PRD

Once you approve the plan, run `/flow:implement`. Your coding agent then works through the `plan.md` file, checking off tasks as it completes them.

**Updated Artifacts:**

- `.agent/specs/prds.md` (Status updates)
- `.agent/specs/<prd_id>/plan.md` (Status updates)
- Project context files (Synchronized on completion)

```bash
/flow:implement
```

Flow will:

1. Select the next pending task.
2. Follow the defined workflow (e.g., TDD: Write Test -> Fail -> Implement -> Pass).
3. Update the status in the plan as it progresses.
4. **Verify Progress**: Guide you through a manual verification step at the end of each phase to ensure everything works as expected.

During implementation, you can also:

- **Check status**: Get a high-level overview of your project's progress.

  ```bash
  /flow:status
  ```

- **Revert work**: Undo a feature or a specific task if needed.

  ```bash
  /flow:revert
  ```

## Commands Reference

| Command | Description | Artifacts |
| :--- | :--- | :--- |
| `/flow:setup` | Scaffolds the project and sets up the Flow environment. Run this once per project. | `.agent/specs/product.md`<br>`.agent/specs/product-guidelines.md`<br>`.agent/specs/tech-stack.md`<br>`.agent/specs/workflow.md`<br>`.agent/specs/prds.md` |
| `/flow:prd` | Starts a new feature or bug PRD. Generates `spec.md` and `plan.md`. | `.agent/specs/<id>/spec.md`<br>`.agent/specs/<id>/plan.md`<br>`.agent/specs/prds.md` |
| `/flow:implement` | Executes the tasks defined in the current PRD's plan. | `.agent/specs/prds.md`<br>`.agent/specs/<id>/plan.md` |
| `/flow:status` | Displays the current progress of the PRD registry and active PRDs. | Reads `.agent/specs/prds.md` |
| `/flow:revert` | Reverts a PRD, phase, or task by analyzing git history. | Reverts git history |

## Directory Structure

By default, Flow creates the following structure:

```
.agent/
├── specs/                    # Specification files
│   ├── index.md              # Project context index
│   ├── product.md            # Product definition
│   ├── product-guidelines.md # Brand and style guidelines
│   ├── tech-stack.md         # Technology choices
│   ├── workflow.md           # Development workflow
│   ├── prds.md               # PRD registry
│   ├── setup-state.json      # Setup state and configuration
│   └── <prd_slug>/           # PRD folders (e.g., user-auth/)
│       ├── index.md
│       ├── spec.md
│       ├── plan.md
│       ├── metadata.json
│       └── knowledge.md
├── archive/                  # Archived PRDs (timestamped)
│   └── prd_YYYYMMDD_<slug>/
├── template/                 # Template files
└── code-styleguides/         # Code style guides
```

**PRD Naming Convention:**
- Active PRDs use simple slugs: `user-auth`, `dark-mode`
- Archived PRDs include timestamps: `prd_20260121_user-auth`

You can customize the specs location during `/flow:setup`.

## Migration from Conductor

If you have an existing project using the legacy `conductor/` directory structure, Flow will automatically detect it during setup and offer to migrate your files to the new `.agent/specs/` structure.

## Resources

- [Gemini CLI extensions](https://geminicli.com/docs/extensions/): Documentation about using extensions in Gemini CLI
- [GitHub issues](https://github.com/gemini-cli-extensions/conductor/issues): Report bugs or request features

## Legal

- License: [Apache License 2.0](LICENSE)
