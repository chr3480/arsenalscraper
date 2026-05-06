# Arsenal Discord Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a GitHub Actions scraper that checks Arsenal.dk every five minutes and notifies Discord about new fanklub and Arsenal F.C. posts.

**Architecture:** A Python package owns parsing, state management, and webhook notification. GitHub Actions provides scheduling and repository-backed state persistence by committing `data/seen_posts.json` after each successful scrape.

**Tech Stack:** Python 3.12 standard library, `unittest`, GitHub Actions cron, Discord webhook API.

---

### Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `README.md`
- Create: `.gitignore`
- Create: `arsenal_scraper/__init__.py`
- Create: `data/seen_posts.json`

- [ ] Keep runtime and test dependencies empty because the scraper uses Python standard library only.
- [ ] Document GitHub secret setup and first-run prime mode.
- [ ] Ignore Python caches and local environment files.

### Task 2: Parser and State

**Files:**
- Create: `tests/fixtures/arsenal_archive.html`
- Create: `tests/test_scraper.py`
- Create: `arsenal_scraper/scraper.py`

- [ ] Write failing tests for extracting title, URL, date, and category from archive HTML.
- [ ] Write failing tests for loading missing state as empty and saving seen URLs.
- [ ] Implement `Post`, `parse_posts`, `load_state`, and `save_state`.
- [ ] Run `python -m unittest discover -s tests -v`.

### Task 3: Notification Flow

**Files:**
- Modify: `tests/test_scraper.py`
- Modify: `arsenal_scraper/scraper.py`

- [ ] Write failing tests that unseen posts are sent and seen posts are skipped.
- [ ] Write failing test that `prime_only=True` updates state but sends nothing.
- [ ] Implement `find_new_posts`, `build_discord_payload`, `send_discord_webhook`, and `run`.
- [ ] Run `python -m unittest discover -s tests -v`.

### Task 4: GitHub Actions

**Files:**
- Create: `.github/workflows/scrape.yml`

- [ ] Run tests in the workflow.
- [ ] Run scraper every five minutes and via manual dispatch.
- [ ] Pass `DISCORD_WEBHOOK_URL` from GitHub Secrets.
- [ ] Commit `data/seen_posts.json` when changed.

### Task 5: Verification

**Files:**
- Modify as needed based on failures.

- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Run scraper with `PRIME_ONLY=1` and no webhook to verify state write behavior does not require Discord.
- [ ] Inspect generated files for secrets and accidental local-only paths.
