#!/usr/bin/env bash
set -euo pipefail

# Installs the skills in this repo into ~/.claude/skills/ by symlink (default)
# or by copy (--copy). Existing installs are detected and skipped, never
# overwritten.

MODE="symlink"
if [[ "${1:-}" == "--copy" ]]; then
  MODE="copy"
elif [[ -n "${1:-}" ]]; then
  echo "Unknown option: ${1}. Use --copy or no argument." >&2
  exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="${HOME}/.claude/skills"
SKILLS=(meeting-summary para-dateiorganisation hetzner-server-runbook projekt-bootstrap)

mkdir -p "${SKILLS_DIR}"

for skill in "${SKILLS[@]}"; do
  src="${REPO_DIR}/${skill}"
  dest="${SKILLS_DIR}/${skill}"
  if [[ -e "${dest}" || -L "${dest}" ]]; then
    echo "skip    ${skill} — already exists at ${dest}"
    continue
  fi
  if [[ "${MODE}" == "copy" ]]; then
    cp -R "${src}" "${dest}"
    echo "copied  ${skill} -> ${dest}"
  else
    ln -s "${src}" "${dest}"
    echo "linked  ${skill} -> ${dest}"
  fi
done

echo "Done. ${#SKILLS[@]} skill(s) processed (mode: ${MODE})."
