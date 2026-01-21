# Flow Context

If a user mentions a "plan" or asks about the plan, and they have used the Flow extension in the current session, they are likely referring to the `.agent/specs/prds.md` file or one of the PRD plans (`.agent/specs/<prd_id>/plan.md`).

## Configuration

The root directory for Flow artifacts defaults to `.agent/specs/`. This can be customized during `/flow:setup`.

To find the configured root directory:

1. Search for `setup-state.json` in these locations (in order):
   - `.agent/specs/setup-state.json`
   - `conductor/setup_state.json` (legacy)
2. Read the `root_directory` value from the found file
3. If no file found, use `.agent/specs/` as default

## Universal File Resolution Protocol

**PROTOCOL: How to locate files.**
To find a file (e.g., "**Product Definition**") within a specific context (Project Root or a specific PRD):

1. **Identify Index:** Determine the relevant index file:
    - **Project Context:** `.agent/specs/index.md`
    - **PRD Context:**
        a. Resolve and read the **PRD Registry** (via Project Context).
        b. Find the entry for the specific `<prd_id>`.
        c. Follow the link provided in the registry to locate the PRD's folder. The index file is `<prd_folder>/index.md`.
        d. **Fallback:** If the PRD is not yet registered (e.g., during creation) or the link is broken:
            1. Resolve the **PRD Directory** (via Project Context).
            2. The index file is `<PRD Directory>/<prd_id>/index.md`.

2. **Check Index:** Read the index file and look for a link with a matching or semantically similar label.

3. **Resolve Path:** If a link is found, resolve its path **relative to the directory containing the `index.md` file**.
    - *Example:* If `.agent/specs/index.md` links to `./workflow.md`, the full path is `.agent/specs/workflow.md`.

4. **Fallback:** If the index file is missing or the link is absent, use the **Default Path** keys below.

5. **Verify:** You MUST verify the resolved file actually exists on the disk.

**Standard Default Paths (Project):**

- **Product Definition**: `.agent/specs/product.md`
- **Tech Stack**: `.agent/specs/tech-stack.md`
- **Workflow**: `.agent/specs/workflow.md`
- **Product Guidelines**: `.agent/specs/product-guidelines.md`
- **PRD Registry**: `.agent/specs/prds.md`
- **PRD Directory**: `.agent/specs/`
- **Archive Directory**: `.agent/archive/`
- **Template Directory**: `.agent/template/`
- **Code Styleguides Directory**: `.agent/code-styleguides/`

**Standard Default Paths (PRD):**

- **Specification**: `.agent/specs/<prd_id>/spec.md`
- **Implementation Plan**: `.agent/specs/<prd_id>/plan.md`
- **Metadata**: `.agent/specs/<prd_id>/metadata.json`

## PRD ID Naming Convention

- **Active PRDs:** Simple slug format (e.g., `user-auth`, `dark-mode-toggle`)
  - Derived from description: lowercase, hyphens for spaces, no special characters
  - Example: "Add User Authentication" -> `user-auth`
- **Archived PRDs:** Timestamped format `prd_YYYYMMDD_<slug>` (e.g., `prd_20260121_user-auth`)
  - Timestamp added when archiving, preserves history
