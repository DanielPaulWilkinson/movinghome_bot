# movinghome_bot

A small Telegram bot that tells you about houses for sale that match your criteria.
It searches Rightmove for each area you list, filters by price, beds and bathrooms,
flags anything your deposit won't cover, and sends each listing **once**. It also
sends it again if the price drops.

## ⚠️ Read this first: Rightmove's terms

Rightmove's terms of use prohibit automated access and scraping. Because of that,
fetching is **switched off by default** (`RIGHTMOVE_SCRAPE_ENABLED=false`). When it's
off, the bot runs but `/find` won't fetch anything.

If you choose to switch it on, you take on that risk. The bot keeps its footprint
small: it checks `robots.txt`, identifies itself in the User-Agent, fetches one page
per area by default (results are sorted newest first), waits between requests,
and checks every 60 minutes by default.

**Simpler alternative:** a saved search on Rightmove with *instant* email or app
alerts covers "tell me when something new is listed" for free and within the terms.
This bot only adds value on top of that: one Telegram feed for two people, price-drop
alerts and the deposit check.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in TELEGRAM_BOT_TOKEN and ALLOWED_CHAT_IDS
python movinghome_bot.py
```

1. Create a bot with [@BotFather](https://t.me/BotFather) and put the token in `.env`.
   `.env` is git-ignored, so **never commit tokens**.
2. Send `/start` to the bot. The log shows `/start from chat <id>`. Put that id
   (plus anyone else's, comma-separated) in `ALLOWED_CHAT_IDS` so strangers can't use it.
3. Edit `data/criteria.json` (see below).

### Settings (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | (required) | From @BotFather |
| `ALLOWED_CHAT_IDS` | empty (anyone) | Comma-separated chat ids allowed to use the bot |
| `ALERT_INTERVAL_MINUTES` | `60` | How often `/start_alerts` checks |
| `RIGHTMOVE_SCRAPE_ENABLED` | `false` | See the terms warning above |
| `REQUEST_DELAY_SECONDS` | `10` | Pause between requests |
| `MAX_PAGES` | `1` | Result pages per area (24 listings each) |
| `CRITERIA_FILE` / `SEEN_FILE` | `data/criteria.json` / `data/seen.json` | File locations |
| `LOG_LEVEL` / `LOG_FILE` | `INFO` / none | Logging |

### Search criteria (`data/criteria.json`)

```json
{
  "locations": [{ "name": "Selby", "code": "", "search_url": "", "active": true }],
  "min_beds": 3, "max_beds": 4, "min_bathrooms": 1,
  "min_price": 100000, "max_price": 200000,
  "property_types": ["bungalow", "detached", "semi-detached", "terraced"],
  "must_have": ["garden"],
  "dont_show": ["newHome", "retirement", "sharedOwnership"],
  "include_sstc": false,
  "deposit": 9000, "min_deposit_pct": 5
}
```

For each area, give **either**:
- `search_url`: set up the search on rightmove.co.uk in your browser and paste the
  results URL here. This is the easiest option, and Rightmove's own filters apply as-is. **or**
- `code`: Rightmove's `locationIdentifier` (e.g. `REGION^1234`, visible in the
  results URL). The bot then builds the URL from the other criteria.

An area with neither is skipped, with a warning in the log.

`deposit` + `min_deposit_pct` work out the most a deposit covers (for example,
£9,000 at 5% covers up to £180,000). Listings above that are still shown, but with a
warning. Lenders' affordability (income multiples) is a separate check that this bot
doesn't do.

## Commands

- `/find`: search now and show anything new
- `/start_alerts` / `/stop_alerts`: regular checks (quiet unless something new turns up)
- `/criteria`: show the current search
- `/help`

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests cover parsing, filtering, de-duplication, price-drop detection, URL
building and message formatting. They use canned HTML and never touch Rightmove.

## Layout

```
movinghome_bot.py          entry point and command wiring
config.py                  env settings + criteria loading
commands/handlers.py       Telegram handlers (thin)
services/search_service.py one search run: fetch -> filter -> de-dupe
services/rightmove_service.py  URL building, page parsing, polite fetching
services/filtering.py      criteria and affordability checks
services/seen_store.py     remembers alerted listings (data/seen.json)
services/parsing.py        price/number/id parsing helpers
```

## Deploying

`Procfile` declares a `worker` process (the bot uses long polling, so it doesn't need
a web port). Any always-on box works. A Raspberry Pi or a small VPS is plenty.
Keep `data/seen.json` on persistent storage, or every restart re-sends every listing.
