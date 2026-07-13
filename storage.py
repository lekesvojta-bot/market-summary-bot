"""Ukládání dat z každého běhu do docs/data/ - odtud je čte webový dashboard.

Soubory:
- history.json          malý záznam cen z každého běhu (pro grafy a týdenní trendy)
- latest.json           kompletní data posledního běhu
- archive/<ts>.json     kopie latest.json pro každý běh (max ARCHIVE_LIMIT kusů)
- archive/index.json    seznam dostupných archivních souborů (aby je web našel)
"""

import json
import os
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "data")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
ARCHIVE_LIMIT = 90


def _read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def load_history():
    return _read_json(HISTORY_FILE, [])


def append_history(stocks, timestamp):
    """Přidá do historie jeden záznam: čas + cena a % změna každé akcie."""
    history = load_history()
    prices = {}
    for stock in stocks:
        quote = stock["quote"]
        if quote:
            prices[stock["symbol"]] = {
                "price": quote["price"],
                "change_pct": round(quote["change_pct"], 2),
            }
    history.append({"timestamp": timestamp, "prices": prices})
    _write_json(HISTORY_FILE, history)
    return history


def get_week_change(history, symbol, current_price):
    """% změna ceny oproti záznamu starému ~7 dní (nejstaršímu v okně 6-8 dní,
    případně nejstaršímu dostupnému, pokud historie zatím tak dlouhá není).
    Vrátí None, dokud není s čím srovnávat."""
    if not history or not current_price:
        return None
    now = datetime.now(timezone.utc)
    best = None
    for record in history:
        entry = record["prices"].get(symbol)
        if not entry:
            continue
        recorded_at = datetime.fromisoformat(record["timestamp"])
        age_days = (now - recorded_at).total_seconds() / 86400
        if age_days > 8:
            continue
        if best is None or age_days > best[0]:
            best = (age_days, entry["price"])
    # Srovnání má smysl až od ~2 dnů historie, jinak je to jen denní změna.
    if best is None or best[0] < 2:
        return None
    old_price = best[1]
    return (current_price - old_price) / old_price * 100


def save_run(stocks, macro_news, ai_output, timestamp):
    """Uloží kompletní data běhu pro web: latest.json + kopii do archivu."""
    run_data = {
        "timestamp": timestamp,
        "stocks": [
            {
                "symbol": stock["symbol"],
                "quote": stock["quote"],
                "news": stock["news"],
                "note": stock.get("note"),
                "earnings_date": stock.get("earnings_date"),
                "week_change_pct": stock.get("week_change_pct"),
                "analysis": ai_output["stocks"].get(stock["symbol"], ""),
            }
            for stock in stocks
        ],
        "macro_news": macro_news,
        "macro_analysis": ai_output.get("macro", ""),
        "tips": ai_output.get("tips", []),
        "glossary": ai_output.get("glossary"),
        "weekly_recap": ai_output.get("weekly_recap"),
    }

    _write_json(os.path.join(DATA_DIR, "latest.json"), run_data)

    # Archiv: soubor pojmenovaný podle času běhu + aktualizace indexu.
    archive_name = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d-%H%M") + ".json"
    _write_json(os.path.join(ARCHIVE_DIR, archive_name), run_data)

    index_path = os.path.join(ARCHIVE_DIR, "index.json")
    index = _read_json(index_path, [])
    if archive_name not in index:
        index.append(archive_name)
    index.sort(reverse=True)

    # Přeteklé archivy smažeme, ať repozitář neroste donekonečna.
    for old_name in index[ARCHIVE_LIMIT:]:
        old_path = os.path.join(ARCHIVE_DIR, old_name)
        if os.path.exists(old_path):
            os.remove(old_path)
    index = index[:ARCHIVE_LIMIT]

    _write_json(index_path, index)
