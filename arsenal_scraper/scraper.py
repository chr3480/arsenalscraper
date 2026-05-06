from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Iterable
from urllib import request
from urllib.error import HTTPError, URLError


ARCHIVE_URLS = [
    "https://arsenal.dk/nyheder-fra-fanklubben/",
    "https://arsenal.dk/nyheder-fra-arsenal-f-c/",
]
SUPPORTED_CATEGORIES = ("Nyheder fra fanklubben", "Nyheder fra Arsenal F.C.")
DEFAULT_STATE_PATH = Path("data/seen_posts.json")
USER_AGENT = "arsenal-discord-scraper/1.0 (+https://github.com/)"


@dataclass(frozen=True)
class Post:
    title: str
    url: str
    category: str
    date: str


@dataclass(frozen=True)
class RunResult:
    scanned_count: int
    new_count: int
    notified_count: int


class ArsenalArchiveParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.posts: list[Post] = []
        self._in_article = False
        self._article_depth = 0
        self._current_link: str | None = None
        self._current_title_parts: list[str] = []
        self._current_text_parts: list[str] = []
        self._capturing_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        classes = set((attrs_dict.get("class") or "").split())

        if tag == "article":
            self._in_article = True
            self._article_depth = 1
            self._current_link = None
            self._current_title_parts = []
            self._current_text_parts = []
            self._capturing_title = False
            return

        if self._in_article:
            self._article_depth += 1
            if tag in {"h1", "h2", "h3"} or "entry-title" in classes:
                self._capturing_title = True
            if tag == "a" and self._capturing_title and not self._current_link:
                href = attrs_dict.get("href")
                if href:
                    self._current_link = href

    def handle_endtag(self, tag: str) -> None:
        if not self._in_article:
            return

        if tag in {"h1", "h2", "h3"} and self._capturing_title:
            self._capturing_title = False

        self._article_depth -= 1
        if tag == "article" or self._article_depth <= 0:
            post = self._build_post()
            if post:
                self.posts.append(post)
            self._in_article = False
            self._article_depth = 0
            self._capturing_title = False

    def handle_data(self, data: str) -> None:
        if not self._in_article:
            return

        text = html.unescape(data).strip()
        if not text:
            return

        self._current_text_parts.append(text)
        if self._capturing_title:
            self._current_title_parts.append(text)

    def _build_post(self) -> Post | None:
        title = clean_text(" ".join(self._current_title_parts))
        url = self._current_link
        article_text = clean_text(" ".join(self._current_text_parts))
        category = extract_category(article_text)
        date = extract_date(article_text)

        if not title or not url or not category:
            return None

        return Post(title=title, url=url, category=category, date=date)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_category(text: str) -> str:
    found = [category for category in SUPPORTED_CATEGORIES if category in text]
    return ", ".join(found)


def extract_date(text: str) -> str:
    match = re.search(r"\b\d{1,2}\.\s+[A-Za-zÆØÅæøå]+\s+\d{4}\b", text)
    return match.group(0) if match else ""


def parse_posts(html_text: str) -> list[Post]:
    parser = ArsenalArchiveParser()
    parser.feed(html_text)
    return parser.posts


def load_state(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {"seen_urls": []}

    with path.open("r", encoding="utf-8") as state_file:
        data = json.load(state_file)

    seen_urls = data.get("seen_urls", [])
    if not isinstance(seen_urls, list):
        raise ValueError(f"Invalid state file: {path}")
    return {"seen_urls": [str(url) for url in seen_urls]}


def save_state(path: Path, state: dict[str, list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = {"seen_urls": sorted(set(state.get("seen_urls", [])))}
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_new_posts(posts: Iterable[Post], state: dict[str, list[str]]) -> list[Post]:
    seen = set(state.get("seen_urls", []))
    yielded: set[str] = set()
    new_posts: list[Post] = []

    for post in posts:
        if post.url in seen or post.url in yielded:
            continue
        yielded.add(post.url)
        new_posts.append(post)

    return new_posts


def build_discord_payload(post: Post) -> dict[str, object]:
    fields = [{"name": "Kategori", "value": post.category, "inline": True}]
    if post.date:
        fields.append({"name": "Dato", "value": post.date, "inline": True})

    return {
        "username": "Arsenal.dk",
        "embeds": [
            {
                "title": post.title,
                "url": post.url,
                "description": "Nyt opslag på Arsenal.dk",
                "color": 0xDB0007,
                "fields": fields,
            }
        ],
    }


def fetch_url(url: str) -> str:
    req = request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with request.urlopen(req, timeout=20) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not fetch {url}: {exc}") from exc


def send_discord_webhook(webhook_url: str, payload: dict[str, object]) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=20) as response:
            if response.status >= 400:
                raise RuntimeError(f"Discord returned HTTP {response.status}")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not send Discord webhook: {exc}") from exc


def run(
    archive_urls: Iterable[str],
    state_path: Path,
    webhook_url: str | None,
    fetch_html: Callable[[str], str] = fetch_url,
    send_webhook: Callable[[str, dict[str, object]], None] = send_discord_webhook,
    prime_only: bool = False,
) -> RunResult:
    state = load_state(state_path)
    posts: list[Post] = []

    for archive_url in archive_urls:
        posts.extend(parse_posts(fetch_html(archive_url)))

    new_posts = find_new_posts(posts, state)
    auto_prime = not state.get("seen_urls")

    notified_count = 0
    if new_posts and not prime_only and not auto_prime:
        if not webhook_url:
            raise RuntimeError("DISCORD_WEBHOOK_URL is required unless PRIME_ONLY=1")
        for post in new_posts:
            send_webhook(webhook_url, build_discord_payload(post))
            notified_count += 1

    seen_urls = set(state.get("seen_urls", []))
    for post in new_posts:
        seen_urls.add(post.url)
    save_state(state_path, {"seen_urls": list(seen_urls)})

    return RunResult(scanned_count=len(posts), new_count=len(new_posts), notified_count=notified_count)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scrape Arsenal.dk and notify Discord about new posts.")
    parser.add_argument("--state", default=str(DEFAULT_STATE_PATH), help="Path to seen posts state JSON.")
    parser.add_argument("--prime-only", action="store_true", help="Mark current posts as seen without notifying.")
    args = parser.parse_args(argv)

    prime_only = args.prime_only or os.getenv("PRIME_ONLY") == "1"
    result = run(
        archive_urls=ARCHIVE_URLS,
        state_path=Path(args.state),
        webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
        prime_only=prime_only,
    )
    print(
        f"Scanned {result.scanned_count} posts, found {result.new_count} new, "
        f"sent {result.notified_count} Discord notifications."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
