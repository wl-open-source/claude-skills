# Contributing

Issues and pull requests are welcome.

- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- **Skill format:** Keep the `SKILL.md` frontmatter (`name`, `description`) intact — the description is the skill's trigger, so be deliberate when changing it.
- **Language:** Skill content is German by design; keep new content consistent unless a skill is explicitly meant to be multilingual.
- **Tests:** If you touch `para-dateiorganisation`, keep the suite green (`python3 para-dateiorganisation/tests/run_all.py`) and add tests for new behavior.
- **No secrets / no PII:** These skills are meant to be shareable — no real names, emails, tokens, or absolute user paths. Use placeholders and environment variables.
