# claude-skills

Four production-tested Claude Code skills. A [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills) is a folder with a `SKILL.md` file that teaches Claude a repeatable workflow — Claude loads it automatically when the task matches.

| Skill | What it does |
|---|---|
| [`meeting-summary`](meeting-summary/) | Turns a meeting transcript or rough notes into one fixed, consistent summary structure (topics, decisions, action items with owner/deadline, open questions, next steps) — always output in German. |
| [`para-dateiorganisation`](para-dateiorganisation/) | Analyzes files in a folder (e.g. Downloads), proposes renames per German naming conventions (DIN 5008, ISO dates), finds duplicates and deletion candidates, and organizes everything into a PARA (Projects/Areas/Resources/Archives) second-brain structure. Proposes only — never acts without confirmation. |
| [`hetzner-server-runbook`](hetzner-server-runbook/) | Provisions Hetzner Cloud servers via the `hcloud` CLI, hardens them (SSH-key-only, ufw, fail2ban, auto-updates), and deploys Docker Compose apps behind Caddy — plus runbooks for backups and troubleshooting. |
| [`projekt-bootstrap`](projekt-bootstrap/) | Runs a live-researched tech-stack proposal for a new greenfield project (GitHub metrics, community size, doc quality) and, after explicit confirmation, generates `CLAUDE.md`, `AGENTS.md`, and `context/` documentation. |

## Language

These skills are content-first in **German** — the `SKILL.md` instructions, output formats, and generated artifacts (e.g. file names, summaries) are written in German and optimized for German-speaking use. `para-dateiorganisation`, for example, renames files per **DIN 5008** and ISO 8601 dates. Nothing here is translated or paraphrased; that's intentional, not an oversight.

## Installation

Run the bootstrap installer, which symlinks each skill folder into `~/.claude/skills/`:

```bash
./setup.sh          # symlink (default) — edits in this repo take effect immediately
./setup.sh --copy   # copy instead of symlink
```

Symlinking is recommended if you plan to `git pull` updates. Copying is useful if you want to modify a skill locally without touching this repo.

Claude Code picks up skills placed under `~/.claude/skills/<name>/SKILL.md` automatically — no restart required for new sessions.

## Requirements

- **Claude Code** — required for all four skills.
- **Python 3** — required to run the automation scripts in `para-dateiorganisation` (dedupe scan, metadata extraction, triage) and `projekt-bootstrap` (`github_metrics.py`). Standard library only, no `pip install` needed.
- **`hcloud` CLI** and an SSH key — only needed if you actually run the `hetzner-server-runbook` workflows against a real Hetzner Cloud account.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
