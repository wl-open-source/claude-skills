"""Tests für github_metrics.py — offline, alle HTTP-Aufrufe gemockt."""
import json
import unittest
from unittest import mock

import github_metrics


REPO_RESPONSE = {
    "stargazers_count": 2000,
    "pushed_at": "2026-06-01T12:00:00Z",
    "archived": False,
    "open_issues_count": 50,
}
RELEASES_RESPONSE = [
    {"published_at": "2026-05-01T00:00:00Z"},
    {"published_at": "2024-01-01T00:00:00Z"},
]


def fake_get(url):
    if url.endswith("/repos/acme/tool"):
        return REPO_RESPONSE, {}
    if "/releases?" in url:
        return RELEASES_RESPONSE, {}
    if "/contributors?" in url:
        link = '<https://api.github.com/x?page=42>; rel="last"'
        return [], {"Link": link}
    raise AssertionError(f"unerwartete URL: {url}")


class CollectTest(unittest.TestCase):
    def test_collect_berechnet_alle_felder(self):
        with mock.patch.object(github_metrics, "_get", side_effect=fake_get):
            result = github_metrics.collect("acme/tool")
        self.assertEqual(result["stars"], 2000)
        self.assertEqual(result["last_commit"], "2026-06-01T12:00:00Z")
        self.assertFalse(result["archived"])
        self.assertEqual(result["open_issues"], 50)
        self.assertEqual(result["issues_per_1k_stars"], 25.0)
        self.assertEqual(result["releases_last_year"], 1)
        self.assertEqual(result["last_release"], "2026-05-01T00:00:00Z")
        self.assertEqual(result["contributors_approx"], 42)

    def test_collect_ohne_releases_und_stars(self):
        def fake(url):
            if "/releases?" in url:
                return [], {}
            if "/contributors?" in url:
                return [], {}
            return {"stargazers_count": 0, "pushed_at": None,
                    "archived": True, "open_issues_count": 3}, {}
        with mock.patch.object(github_metrics, "_get", side_effect=fake):
            result = github_metrics.collect("acme/leer")
        self.assertIsNone(result["issues_per_1k_stars"])
        self.assertEqual(result["releases_last_year"], 0)
        self.assertIsNone(result["last_release"])
        self.assertTrue(result["archived"])
        self.assertEqual(result["contributors_approx"], 1)


class MainTest(unittest.TestCase):
    def test_main_ohne_gueltige_slugs_gibt_1(self):
        self.assertEqual(github_metrics.main(["prog"]), 1)
        self.assertEqual(github_metrics.main(["prog", "kein-slash"]), 1)

    def test_main_rate_limit_gibt_2(self):
        with mock.patch.object(
            github_metrics, "collect",
            side_effect=github_metrics.RateLimitError("Limit erreicht"),
        ), mock.patch("builtins.print") as fake_print:
            code = github_metrics.main(["prog", "acme/tool"])
        self.assertEqual(code, 2)
        payload = json.loads(fake_print.call_args_list[0].args[0])
        self.assertIn("error", payload["acme/tool"])


if __name__ == "__main__":
    unittest.main()
