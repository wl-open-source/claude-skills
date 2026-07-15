# Repository guide for Claude Code

This repo is a collection of Claude Code skills. Each top-level folder is one skill.

## Structure

- One skill = one folder with a `SKILL.md` (required) plus optional `references/`, `scripts/`, and `assets/`.
- `SKILL.md` frontmatter has `name` and `description`; the description is what triggers the skill.
- Skill content is written in **German** by design — keep it that way when editing.

## Skills

- `meeting-summary` — `SKILL.md` only (no scripts).
- `para-dateiorganisation` — Python scripts (`scripts/`), a test suite (`tests/`), and an eval harness (`eval/`).
- `hetzner-server-runbook` — `SKILL.md` + reference runbooks (`references/`).
- `projekt-bootstrap` — `SKILL.md` + templates (`references/templates/`) + `scripts/github_metrics.py`.

## Tests

`para-dateiorganisation` has a self-contained test suite (standard library only, synthetic data):

```bash
python3 para-dateiorganisation/tests/run_all.py       # all tests
python3 para-dateiorganisation/tests/run_all.py -v    # verbose
```

`projekt-bootstrap` script tests:

```bash
python3 -m unittest projekt-bootstrap/scripts/test_github_metrics.py
```

## Installation

`./setup.sh` symlinks (or `--copy`) each skill into `~/.claude/skills/`.
