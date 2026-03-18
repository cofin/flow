
# Sphinx VHS Demos Workflow

## Overview

Use this skill to generate and manage automated terminal demonstrations using `vhs`. By writing declarative scripts (`.tape`), you can compile reproducible terminal interface visual streams that update on demand without reliance on brittle screen recorders.

## Execution Workflow

### 1. Create Tape Scripts (`docs/_tapes/*.tape`)

Write `.tape` declarative scripts that execute commands as users would. Setup initial configurations like themes and padding.

**Example Tape Structure (`docs/_tapes/demo.tape`):**

```text
Output docs/_static/demos/example_command.gif

Set Theme "Material"
Set FontSize 16
Set Width 1200
Set Height 600
Set Padding 20

# Slow down typing speed for clarity
Set TypingSpeed 75ms

Type "uv run dma assessment list"
Sleep 500ms
Enter

Sleep 3s
```

### 2. Local Execution

Running `vhs` requires supporting tools to render streams accurately in isolation.

-   **Core dependency**: `vhs`
-   **Supporting nodes**: `ttyd` (isolates terminal output), `ffmpeg` (compilation)

To compile local script additions:

```bash
# Verify setup
vhs --version

# Compile single tape script into your artifacts directory
vhs docs/_tapes/demo.tape
```

### 3. Embedding inside Sphinx

Standard directives pull rendered media automatically inside your guide flows structure:

```markdown
## assessment execution

Here is how list assessment works visually:

![Assessment Demo](/_static/demos/example_command.gif)
```

## Best Practices

-   **Static output locations**: Always route Outputs to `docs/_static/demos/*.gif` so standard theme modules detect and package them smoothly.
-   **Sandbox isolation**: In environments utilizing complex setups, isolate rendering via `docker` configurations if local dependency chains conflict.
-   **Bypassing Safety Checks**: If tape commands intentional execute live endpoints requiring security triggers, supply bypass flags scoped only for the visualization step without tampering codebase defenses.
-   **Framerate guidelines**: Favor standard frame rates; very fast speeds make scanning harder for new users.
