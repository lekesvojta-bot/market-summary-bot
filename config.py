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

# Akcie, které bot sleduje.
TICKERS = ["NVDA", "AMD", "GOOGL", "META", "AAPL"]

# Kolik hodin zpátky brát novinky. Bot běží zhruba každých 5-7 hodin,
# 8 hodin je bezpečná rezerva, aby nevznikla mezera bez pokrytí.
NEWS_LOOKBACK_HOURS = 8

CLAUDE_MODEL = "claude-sonnet-5"
