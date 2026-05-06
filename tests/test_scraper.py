import json
import shutil
import unittest
from pathlib import Path

from arsenal_scraper.scraper import (
    Post,
    build_discord_payload,
    find_new_posts,
    load_state,
    parse_posts,
    run,
    save_state,
)


FIXTURE = Path(__file__).parent / "fixtures" / "arsenal_archive.html"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ScraperTests(unittest.TestCase):
    def tearDown(self):
        tmp_root = PROJECT_ROOT / ".test-tmp"
        if tmp_root.exists():
            shutil.rmtree(tmp_root)

    def test_parse_posts_extracts_supported_news_items(self):
        posts = parse_posts(FIXTURE.read_text(encoding="utf-8"))

        self.assertEqual(
            posts,
            [
                Post(
                    title="Nye varer på lager",
                    url="https://arsenal.dk/nye-varer-paa-lager-2/",
                    category="Nyheder fra fanklubben",
                    date="14. august 2025",
                ),
                Post(
                    title="En sæson i tredje gear",
                    url="https://arsenal.dk/en-saeson-i-tredje-gear/",
                    category="Nyheder fra Arsenal F.C.",
                    date="12. juni 2025",
                ),
            ],
        )

    def test_state_loads_missing_file_as_empty(self):
        with self.subTest("missing state file"):
            state = load_state(Path(self._tmpdir()) / "missing.json")

        self.assertEqual(state, {"seen_urls": []})

    def test_state_saves_seen_urls_sorted(self):
        state_path = Path(self._tmpdir()) / "seen_posts.json"

        save_state(state_path, {"seen_urls": ["https://b.example", "https://a.example"]})

        self.assertEqual(
            json.loads(state_path.read_text(encoding="utf-8")),
            {"seen_urls": ["https://a.example", "https://b.example"]},
        )

    def test_find_new_posts_skips_seen_and_deduplicates_current_run(self):
        posts = [
            Post("Seen", "https://arsenal.dk/seen/", "Nyheder fra fanklubben", "1. maj 2026"),
            Post("New", "https://arsenal.dk/new/", "Nyheder fra Arsenal F.C.", "2. maj 2026"),
            Post("New duplicate", "https://arsenal.dk/new/", "Nyheder fra Arsenal F.C.", "2. maj 2026"),
        ]

        self.assertEqual(
            find_new_posts(posts, {"seen_urls": ["https://arsenal.dk/seen/"]}),
            [Post("New", "https://arsenal.dk/new/", "Nyheder fra Arsenal F.C.", "2. maj 2026")],
        )

    def test_build_discord_payload_uses_embed(self):
        payload = build_discord_payload(
            Post("Nyt opslag", "https://arsenal.dk/nyt/", "Nyheder fra fanklubben", "6. maj 2026")
        )

        self.assertEqual(payload["embeds"][0]["title"], "Nyt opslag")
        self.assertEqual(payload["embeds"][0]["url"], "https://arsenal.dk/nyt/")
        self.assertEqual(
            payload["embeds"][0]["fields"],
            [
                {"name": "Kategori", "value": "Nyheder fra fanklubben", "inline": True},
                {"name": "Dato", "value": "6. maj 2026", "inline": True},
            ],
        )

    def test_run_sends_only_new_posts_and_updates_state(self):
        state_path = Path(self._tmpdir()) / "seen_posts.json"
        save_state(state_path, {"seen_urls": ["https://arsenal.dk/nye-varer-paa-lager-2/"]})
        sent_payloads = []

        result = run(
            archive_urls=["https://example.test/archive"],
            state_path=state_path,
            webhook_url="https://discord.test/webhook",
            fetch_html=lambda url: FIXTURE.read_text(encoding="utf-8"),
            send_webhook=lambda url, payload: sent_payloads.append((url, payload)),
        )

        self.assertEqual(result.new_count, 1)
        self.assertEqual(sent_payloads[0][1]["embeds"][0]["title"], "En sæson i tredje gear")
        self.assertEqual(
            json.loads(state_path.read_text(encoding="utf-8"))["seen_urls"],
            [
                "https://arsenal.dk/en-saeson-i-tredje-gear/",
                "https://arsenal.dk/nye-varer-paa-lager-2/",
            ],
        )

    def test_run_prime_only_updates_state_without_sending(self):
        state_path = Path(self._tmpdir()) / "seen_posts.json"
        sent_payloads = []

        result = run(
            archive_urls=["https://example.test/archive"],
            state_path=state_path,
            webhook_url=None,
            fetch_html=lambda url: FIXTURE.read_text(encoding="utf-8"),
            send_webhook=lambda url, payload: sent_payloads.append((url, payload)),
            prime_only=True,
        )

        self.assertEqual(result.new_count, 2)
        self.assertEqual(sent_payloads, [])
        self.assertEqual(
            json.loads(state_path.read_text(encoding="utf-8"))["seen_urls"],
            [
                "https://arsenal.dk/en-saeson-i-tredje-gear/",
                "https://arsenal.dk/nye-varer-paa-lager-2/",
            ],
        )

    def test_run_auto_primes_empty_state_without_sending_old_posts(self):
        state_path = Path(self._tmpdir()) / "seen_posts.json"
        sent_payloads = []

        result = run(
            archive_urls=["https://example.test/archive"],
            state_path=state_path,
            webhook_url="https://discord.test/webhook",
            fetch_html=lambda url: FIXTURE.read_text(encoding="utf-8"),
            send_webhook=lambda url, payload: sent_payloads.append((url, payload)),
        )

        self.assertEqual(result.new_count, 2)
        self.assertEqual(result.notified_count, 0)
        self.assertEqual(sent_payloads, [])

    def _tmpdir(self):
        tmp_root = PROJECT_ROOT / ".test-tmp"
        tmp_root.mkdir(exist_ok=True)
        path = tmp_root / self._testMethodName
        path.mkdir(exist_ok=True)
        return path


if __name__ == "__main__":
    unittest.main()
