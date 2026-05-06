# Arsenal.dk Discord Scraper

Cloud scraper for Arsenal.dk. It checks both "Nyheder fra fanklubben" and "Nyheder fra Arsenal F.C." every five minutes with GitHub Actions and sends new posts to a Discord webhook.

## How It Works

- GitHub Actions runs `.github/workflows/scrape.yml` on `*/5 * * * *`.
- The Python scraper reads `data/seen_posts.json`.
- New Arsenal.dk post URLs are sent to Discord.
- The workflow commits the updated state file back to the repo.
- If the state file is empty, the scraper primes it without sending old posts.

## Setup

1. Create a new GitHub repository and push this folder.
2. In GitHub, go to `Settings` -> `Secrets and variables` -> `Actions`.
3. Add a repository secret named `DISCORD_WEBHOOK_URL`.
4. Enable GitHub Actions if GitHub asks.
5. Optional: run the workflow manually once with `prime_only=true`.
6. To verify Discord immediately, run the workflow manually with `send_test=true`.

The scheduled workflow runs on UTC time. GitHub's shortest supported schedule interval is five minutes, but runs can be delayed during GitHub Actions load spikes.

## Local Test

```powershell
python -m unittest discover -s tests -v
```

## Manual Local Prime

```powershell
$env:PRIME_ONLY = "1"
python -m arsenal_scraper.scraper
```
