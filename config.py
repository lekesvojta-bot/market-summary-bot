import os

from dotenv import load_dotenv

# Lokálně načte proměnné z .env souboru do prostředí.
# Na GitHub Actions .env neexistuje - tam se stejné proměnné nastaví
# přes "secrets", takže tento řádek tam jen tiše nic neudělá.
load_dotenv()

FINNHUB_API_KEY = os.environ["FINNHUB_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# Akcie/ETF, které bot sleduje. "finnhub_symbol" a "note" jsou volitelné -
# použijí se, když se zobrazovaný symbol liší od symbolu ve Finnhubu
# (typicky proto, že Finnhub free tier neumí evropské burzy).
TICKERS = [
    {"symbol": "NVDA", "name": "NVIDIA Corp."},
    {"symbol": "AMD", "name": "Advanced Micro Devices"},
    {"symbol": "GOOGL", "name": "Alphabet Inc."},
    {"symbol": "META", "name": "Meta Platforms"},
    {"symbol": "AAPL", "name": "Apple Inc."},
    {"symbol": "MSFT", "name": "Microsoft Corp."},
    {
        "symbol": "VUAA",
        "name": "S&P 500 (přes SPY)",
        "finnhub_symbol": "SPY",
        "note": (
            "VUAA je evropský ETF na S&P 500 (LSE/Xetra), Finnhub free tier "
            "ale evropské burzy nepodporuje. Cena a novinky jsou proto z "
            "amerického ETF SPY, který sleduje stejný index 1:1."
        ),
    },
]

# Kolik hodin zpátky brát novinky. Bot běží zhruba každých 5-7 hodin,
# 8 hodin je bezpečná rezerva, aby nevznikla mezera bez pokrytí.
NEWS_LOOKBACK_HOURS = 8

CLAUDE_MODEL = "claude-sonnet-5"
