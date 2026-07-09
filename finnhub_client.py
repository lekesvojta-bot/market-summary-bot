import time
from datetime import datetime, timedelta

import requests

from config import FINNHUB_API_KEY

BASE_URL = "https://finnhub.io/api/v1"


def _get(endpoint, params):
    params = {**params, "token": FINNHUB_API_KEY}
    response = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def get_quote(symbol):
    """Vrátí aktuální cenu, % změnu a denní rozpětí (high/low/open)."""
    try:
        data = _get("/quote", {"symbol": symbol})
        price = data["c"]
        previous_close = data["pc"]
        change_pct = 0.0
        if previous_close:
            change_pct = (price - previous_close) / previous_close * 100
        return {
            "symbol": symbol,
            "price": price,
            "change_pct": change_pct,
            "day_high": data.get("h"),
            "day_low": data.get("l"),
            "day_open": data.get("o"),
        }
    except Exception as error:
        print(f"[finnhub] Nepodařilo se stáhnout cenu pro {symbol}: {error}")
        return None


def _filter_recent(news_items, cutoff_timestamp):
    recent = [item for item in news_items if item.get("datetime", 0) >= cutoff_timestamp]
    recent.sort(key=lambda item: item["datetime"], reverse=True)
    return [
        {
            "headline": item.get("headline", ""),
            "summary": item.get("summary", ""),
            "source": item.get("source", ""),
        }
        for item in recent[:8]
    ]


def get_company_news(symbol, hours):
    """Vrátí novinky pro danou akcii za posledních `hours` hodin."""
    cutoff_timestamp = time.time() - hours * 3600
    # from/to bere Finnhub jen jako datum (ne čas), takže bereme o den víc
    # dozadu, aby se do výběru vešly i novinky těsně po půlnoci.
    date_from = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d")
    date_to = datetime.utcnow().strftime("%Y-%m-%d")
    try:
        news = _get("/company-news", {"symbol": symbol, "from": date_from, "to": date_to})
        return _filter_recent(news, cutoff_timestamp)
    except Exception as error:
        print(f"[finnhub] Nepodařilo se stáhnout novinky pro {symbol}: {error}")
        return []


def get_general_market_news(hours):
    """Vrátí obecné makro/tržní novinky za posledních `hours` hodin."""
    cutoff_timestamp = time.time() - hours * 3600
    try:
        news = _get("/news", {"category": "general"})
        return _filter_recent(news, cutoff_timestamp)
    except Exception as error:
        print(f"[finnhub] Nepodařilo se stáhnout makro novinky: {error}")
        return []
