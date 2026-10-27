"""All settings in one place. Secrets come from environment variables (or a
local, git-ignored .env file); search preferences come from data/criteria.json."""
import json
import os
from dataclasses import dataclass, field
from typing import List

from objects.criteria import Criteria, Location

try:  # optional: lets you keep settings in a local .env file
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def _bool(value: str) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    token: str
    allowed_chat_ids: List[int] = field(default_factory=list)
    alert_interval_minutes: int = 60
    criteria_file: str = "data/criteria.json"
    seen_file: str = "data/seen.json"
    scrape_enabled: bool = False
    request_delay_seconds: float = 10.0
    max_pages: int = 1


def load_settings(env=os.environ) -> Settings:
    token = env.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and add the "
            "token from @BotFather."
        )
    ids = [int(x) for x in env.get("ALLOWED_CHAT_IDS", "").replace(" ", "").split(",") if x]
    return Settings(
        token=token,
        allowed_chat_ids=ids,
        alert_interval_minutes=int(env.get("ALERT_INTERVAL_MINUTES", 60)),
        criteria_file=env.get("CRITERIA_FILE", "data/criteria.json"),
        seen_file=env.get("SEEN_FILE", "data/seen.json"),
        scrape_enabled=_bool(env.get("RIGHTMOVE_SCRAPE_ENABLED", "false")),
        request_delay_seconds=float(env.get("REQUEST_DELAY_SECONDS", 10)),
        max_pages=max(1, int(env.get("MAX_PAGES", 1))),
    )


def _opt_int(value):
    return None if value in (None, "") else int(value)


def criteria_from_dict(d: dict) -> Criteria:
    locations = [
        Location(
            name=loc["name"],
            code=loc.get("code", ""),
            search_url=loc.get("search_url", ""),
            active=bool(loc.get("active", True)),
        )
        for loc in d.get("locations", [])
    ]
    return Criteria(
        locations=locations,
        min_beds=_opt_int(d.get("min_beds")),
        max_beds=_opt_int(d.get("max_beds")),
        min_bathrooms=_opt_int(d.get("min_bathrooms")),
        min_price=_opt_int(d.get("min_price")),
        max_price=_opt_int(d.get("max_price")),
        property_types=list(d.get("property_types", [])),
        must_have=list(d.get("must_have", [])),
        dont_show=list(d.get("dont_show", [])),
        include_sstc=bool(d.get("include_sstc", False)),
        deposit=_opt_int(d.get("deposit")),
        min_deposit_pct=float(d.get("min_deposit_pct", 5)),
    )


def load_criteria(path: str) -> Criteria:
    with open(path, "r", encoding="utf-8") as f:
        return criteria_from_dict(json.load(f))
