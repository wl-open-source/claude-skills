#!/usr/bin/env python3
"""GitHub-Metriken für Tech-Stack-Kandidaten (projekt-bootstrap Skill).

Aufruf:   python3 github_metrics.py owner/repo [owner/repo ...]
Ausgabe:  JSON auf stdout, ein Eintrag pro Repo.
Auth:     GITHUB_TOKEN wird genutzt, falls gesetzt (höheres Rate-Limit).
Exit:     0 = ok (einzelne Repo-Fehler stehen im JSON),
          1 = Usage-Fehler, 2 = Rate-Limit-Abbruch.

Nur Python-Standardbibliothek, plattformunabhängig.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.github.com"
RELEASES_SAMPLE = 30
TIMEOUT_SECONDS = 15


class RateLimitError(Exception):
    """GitHub-Rate-Limit erschöpft — Lauf abbrechen statt still raten."""


def _request(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "projekt-bootstrap-skill",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8")), dict(resp.headers)


def _get(url):
    try:
        return _request(url)
    except urllib.error.HTTPError as err:
        if err.code in (403, 429) and err.headers.get("X-RateLimit-Remaining") == "0":
            raise RateLimitError(
                "GitHub-Rate-Limit erreicht. GITHUB_TOKEN setzen "
                "oder später erneut versuchen."
            ) from err
        raise


def _parse_iso(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _contributors_approx(slug):
    _, headers = _get(f"{API}/repos/{slug}/contributors?per_page=1&anon=true")
    match = re.search(r'[?&]page=(\d+)>; rel="last"', headers.get("Link", ""))
    return int(match.group(1)) if match else 1


def collect(slug):
    repo, _ = _get(f"{API}/repos/{slug}")
    releases, _ = _get(f"{API}/repos/{slug}/releases?per_page={RELEASES_SAMPLE}")
    year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    recent = [
        r for r in releases
        if r.get("published_at") and _parse_iso(r["published_at"]) > year_ago
    ]
    stars = repo.get("stargazers_count", 0)
    open_issues = repo.get("open_issues_count", 0)
    return {
        "stars": stars,
        "last_commit": repo.get("pushed_at"),
        "archived": repo.get("archived", False),
        "open_issues": open_issues,
        "issues_per_1k_stars": (
            round(open_issues / stars * 1000, 1) if stars else None
        ),
        "releases_last_year": len(recent),
        "last_release": (
            releases[0]["published_at"] if releases
            and releases[0].get("published_at") else None
        ),
        "contributors_approx": _contributors_approx(slug),
    }


def main(argv):
    slugs = [arg for arg in argv[1:] if "/" in arg]
    if not slugs:
        print(
            "Aufruf: github_metrics.py owner/repo [owner/repo ...]",
            file=sys.stderr,
        )
        return 1
    results = {}
    for slug in slugs:
        try:
            results[slug] = collect(slug)
        except RateLimitError as err:
            results[slug] = {"error": str(err)}
            print(json.dumps(results, indent=2, ensure_ascii=False))
            return 2
        except urllib.error.HTTPError as err:
            results[slug] = {"error": f"HTTP {err.code} für {slug}"}
        except urllib.error.URLError as err:
            results[slug] = {"error": f"Netzwerkfehler: {err.reason}"}
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
