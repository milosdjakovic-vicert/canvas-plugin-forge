# Plugin Forge — Project Instructions

Canvas plugin development workspace. All plugins are tracked in this repo. Individual plugins can be pushed to their own remotes via `git subtree`.

## Structure

- `plugins/` — Active plugin projects (tracked in this repo)
- `misc/` — Fixtures, POCs, example documents (tracked)
- `.cpa-workflow-artifacts/` — CPA session costs, user inputs, workflow reports (tracked)

## Environment (direnv)

Two-level `.envrc` setup for CPA:

- **Workspace** `.envrc` — sets `CPA_RUNNING=1` and `CPA_WORKSPACE_DIR`
- **Plugin** `.envrc` — inherits via `source_up`, adds `CPA_PLUGIN_DIR`

Launch Claude from the workspace for new plugin creation, or from a plugin directory for all other CPA commands.

## Git Subtree (per-plugin remotes)

To push a plugin to its own remote:

```bash
git remote add {plugin-name} git@github.com:org/{plugin-name}.git
git subtree push --prefix=plugins/{plugin-name} {plugin-name} main
```
