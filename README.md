# movinghome_bot

A daily house-hunting report for Selby. It reads saved **Rightmove alert
emails** and writes:

- `report.html`: one self-contained page with a filterable, sortable table and
  a map. Filters cover price, beds, type, tenure, church tier and distance,
  garden, parking, EPC, flood, condition, and new vs reduced.
- `brief.md` / `brief.json`: a short summary of what is new or reduced today,
  with things to check.

It does not scrape any property portal and never logs in to email. Whoever runs
it (you, a script or an assistant) saves the alert emails into a folder first.

## Usage

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# 1. Save today's Rightmove alert emails into inbox/ as .eml, .json or .html
# 2. Run:
python daily.py --input inbox/ --out reports/
```

Outputs go in `reports/<YYYY-MM-DD>/report.html`, `brief.md` and `brief.json`.

| Option | Default | Notes |
| --- | --- | --- |
| `--input` | `inbox` | Folder (or one file) of saved alert emails |
| `--out` | `reports` | Output root; files go in `<out>/<date>/` |
| `--criteria` | `data/criteria.json` | Beds, prices, deposit, church, tiers, mortgage settings |
| `--seen` | `data/seen.json` | Remembers listings, so repeats show as "earlier" and price cuts as "reduced" |
| `--cache` | `data/cache` | Cached lookups, plus the monthly school and sold-price files |
| `--date` | today | Report date |
| `--offline` | off | Skip every network lookup; area facts are left blank |

Accepted input formats:

- `.eml`: a raw email (the HTML part is used).
- `.json`: `{"subject": "...", "html": "..."}` or `{"text": "..."}`, or a list of those.
- `.html`: the email body.

To call it from Python, use `daily.run(alert_bodies, criteria, store, out_dir, net)`.
It takes any iterable of email HTML.

Optional environment variables (see `.env.example`):

- `NOMINATIM_CONTACT`: an email address sent to OpenStreetMap's geocoder, as
  their usage policy asks.
- `LOG_LEVEL`.

No API keys or secrets are needed.

## Where the data comes from

All sources are free and need no key. Every lookup is best effort: if one
fails, its field is left blank.

| What | Source |
| --- | --- |
| Listings | Rightmove alert emails you have saved |
| Location | postcodes.io, then OpenStreetMap Nominatim (at most 1 request a second), then the village or town centre |
| Church tier and distance | `data/criteria.json` (St James the Apostle, Selby) |
| Crime | data.police.uk: street-level crime within 1 mile, latest month |
| Flood | Environment Agency flood alert areas within 1 km and live warnings, plus a link to the long-term flood risk check |
| Schools | DfE "Get Information about Schools": nearest open primary schools, with Ofsted links. Downloaded monthly |
| Sold prices | HM Land Registry price-paid data for the postcode districts in `criteria.json`. Downloaded monthly |
| Costs | Stamp duty (standard and first-time buyer, England rates from April 2025), 5% and 10% deposits, and an illustrative monthly repayment |
| Council tax | A link to the GOV.UK band checker (there is no API) |
| Condition | **An estimate** from the listing wording and EPC rating. Not a survey |

Garden and parking are also read from the listing text: "unknown" means the
alert did not say.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

The tests run offline, using a synthetic alert email in `tests/fixtures/`.

## History

This started in 2023 as a Telegram bot that scraped Rightmove with Selenium.
That bot was removed. If you ever ran it, revoke its old token in @BotFather:
a token is still in this repository's git history.
