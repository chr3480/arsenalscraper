# Arsenal Discord Scraper Design

## Goal

Build a cloud-run scraper that checks Arsenal.dk every five minutes and sends a Discord webhook when Arsenal.dk publishes a new post in either "Nyheder fra fanklubben" or "Nyheder fra Arsenal F.C."

## Architecture

The scraper is a small Python command line program run by GitHub Actions on a `*/5 * * * *` schedule. It uses only the Python standard library, fetches Arsenal.dk category/archive pages, parses post cards into structured records, compares them with `data/seen_posts.json`, sends Discord messages for unseen posts, then writes the updated state back to the repository. The GitHub Actions workflow commits the state file after successful runs.

## Components

- `arsenal_scraper/scraper.py`: Fetch, parse, deduplicate, and notify.
- `data/seen_posts.json`: Repository-backed state with seen post URLs.
- `.github/workflows/scrape.yml`: Scheduled cloud runner and manual dispatch entry point.
- `tests/`: Unit tests for HTML parsing, state updates, and dry-run behavior.

## Data Flow

1. GitHub Actions starts every five minutes on the default branch.
2. The workflow installs Python dependencies and runs the scraper.
3. The scraper loads `data/seen_posts.json`.
4. It fetches the fanklub and Arsenal F.C. archive URLs.
5. It extracts posts with title, URL, date, and category.
6. It sends Discord webhook embeds for posts not already seen.
7. It saves the updated state.
8. The workflow commits `data/seen_posts.json` only when it changed.

## Configuration

`DISCORD_WEBHOOK_URL` is stored as a GitHub Actions secret. `PRIME_ONLY=1` can be used to mark existing posts as seen without notifying Discord. If the state file is empty, the scraper automatically primes state without notifying, which prevents old posts from being sent on the first scheduled run.

## Error Handling

Network and parse failures exit non-zero so GitHub Actions records a failed run. Discord webhook failures also fail the run after logging which post failed. Duplicate URLs are ignored within a single run and across runs.

## Testing

Tests use Python `unittest`, local HTML fixtures, and fake webhook senders. They do not call Arsenal.dk or Discord. The GitHub workflow runs the test suite before scraping.
