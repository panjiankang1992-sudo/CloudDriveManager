<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan at:
specs/001-cloud-drive-manager/plan.md
<!-- SPECKIT END -->

## Project State

Greenfield project — no application code yet. `main.py` is a PyCharm default placeholder. No dependency management (`requirements.txt` / `pyproject.toml`), no tests, no CI configured.

## Tech Stack

- **Language**: Python 3.10
- **IDE**: PyCharm
- **Shell**: PowerShell (Windows)
- **Git remote**: `origin` → `https://github.com/panjiankang1992-sudo/CloudDriveManager.git`
- **Branch numbering**: Sequential (via SpecKit git extension)

## SpecKit Workflow

This repo uses **SpecKit v0.7.4.dev0** integrated with OpenCode. The workflow is:
`specify → clarify → plan → tasks → implement`

- Git extension handles auto-branching and auto-commits at each stage
- Feature branches follow `NNN-feature-name` sequential numbering
- Constitution, spec, plan, and task templates are in `.specify/templates/`
- Do **not** manually edit `.specify/` generated files; use SpecKit commands instead

## Key Paths

| Path | Purpose |
|---|---|
| `main.py` | Entry point (currently placeholder) |
| `.specify/` | SpecKit config, templates, extensions |
| `.opencode/` | OpenCode plugin config (SpecKit commands) |
| `.idea/` | PyCharm project config (Python 3.10 SDK) |

## Before Adding Code

When starting real development, set up:
1. Dependency management (`pyproject.toml` or `requirements.txt`)
2. A `.gitignore` for Python (bytecode, venv, `.env`, etc.)
3. Test framework (pytest recommended)
4. Replace the placeholder `main.py`
