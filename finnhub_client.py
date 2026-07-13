import time
from datetime import datetime, timedelta

import requests

from config import FINNHUB_API_KEY

BASE_URL = "https://finnhub.io/api/v1"


def _get(endpoint, params):
    params = {**params, "token": FINNHUB_API_KEY}
    # Finnhub občas neodpoví včas (timeout) - zkusíme až 3x, mezi pokusy
    # krátká pauza. Až když selžou všechny pokusy, pustíme chybu dál.
    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as error:
            last_error = error
            print(f"[finnhub] Pokus {attempt + 1}/3 pro {endpoint} selhal: {error}")
            time.sleep(3)
    raise last_error


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
            "url": item.get("url", ""),
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


def get_next_earnings(symbol):
    """Vrátí datum (YYYY-MM-DD) nejbližších kvartálních výsledků do 21 dnů, jinak None."""
    date_from = datetime.utcnow().strftime("%Y-%m-%d")
    date_to = (datetime.utcnow() + timedelta(days=21)).strftime("%Y-%m-%d")
    try:
        data = _get(
            "/calendar/earnings", {"symbol": symbol, "from": date_from, "to": date_to}
        )
        events = data.get("earningsCalendar", [])
        if not events:
            return None
        return min(event["date"] for event in events)
    except Exception as error:
        print(f"[finnhub] Nepodařilo se stáhnout earnings pro {symbol}: {error}")
        return None


def get_general_market_news(hours):
    """Vrátí obecné makro/tržní novinky za posledních `hours` hodin."""
    cutoff_timestamp = time.time() - hours * 3600
    try:
        news = _get("/news", {"category": "general"})
        return _filter_recent(news, cutoff_timestamp)
    except Exception as error:
        print(f"[finnhub] Nepodařilo se stáhnout makro novinky: {error}")
        return []
