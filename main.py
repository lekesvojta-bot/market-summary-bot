from datetime import datetime, timezone

import claude_summary
import config
import finnhub_client
import storage
import telegram_sender

WEB_URL = "https://lekesvojta-bot.github.io/market-summary-bot/"


def collect_stock_data(history):
    stocks = []
    for ticker in config.TICKERS:
        symbol = ticker["symbol"]
        # finnhub_symbol umožňuje stahovat data pod jiným symbolem, než se
        # zobrazuje (např. VUAA se sleduje přes americké SPY, viz config.py).
        finnhub_symbol = ticker.get("finnhub_symbol", symbol)
        print(f"Stahuji data pro {symbol} ({finnhub_symbol})...")
        quote = finnhub_client.get_quote(finnhub_symbol)
        news = finnhub_client.get_company_news(finnhub_symbol, config.NEWS_LOOKBACK_HOURS)
        next_earnings = finnhub_client.get_next_earnings(finnhub_symbol)
        last_earnings = finnhub_client.get_last_earnings(finnhub_symbol)
        week_change = storage.get_week_change(
            history, symbol, quote["price"] if quote else None
        )
        stocks.append(
            {
                "symbol": symbol,
                "name": ticker.get("name"),
                "quote": quote,
                "news": news,
                "note": ticker.get("note"),
                # earnings_date (jen datum) čte prompt, next_earnings (i s časem) web.
                "earnings_date": next_earnings["date"] if next_earnings else None,
                "next_earnings": next_earnings,
                "last_earnings": last_earnings,
                "week_change_pct": week_change,
            }
        )
    return stocks


def is_weekly_recap_time(now):
    """Páteční večerní běh (po 15:00 UTC) přidává týdenní rekapitulaci."""
    return now.weekday() == 4 and now.hour >= 15


def main():
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    print(f"=== Spouštím tržní shrnutí: {timestamp} ===")

    history = storage.load_history()
    stocks = collect_stock_data(history)

    print("Stahuji makro novinky...")
    macro_news = finnhub_client.get_general_market_news(config.NEWS_LOOKBACK_HOURS)

    weekly_recap = is_weekly_recap_time(now)
    print(f"Generuji shrnutí přes Claude API... (týdenní recap: {weekly_recap})")
    ai_output = claude_summary.generate_summary(stocks, macro_news, weekly_recap)

    local_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    header = f"📊 <b>Přehled trhu — {local_time}</b>\n\n"
    footer = f'\n\n📎 <a href="{WEB_URL}">Podrobnosti a grafy na webu</a>'
    message = header + ai_output["telegram_message"] + footer
    if ai_output.get("weekly_recap"):
        message += "\n\n🗓 <b>Týdenní rekapitulace</b>\n" + ai_output["weekly_recap"]

    print("Posílám na Telegram...")
    telegram_sender.send_message(message)

    print("Ukládám data pro web...")
    storage.save_run(stocks, macro_news, ai_output, timestamp)
    storage.append_history(stocks, timestamp)

    print("Hotovo.")


if __name__ == "__main__":
    main()
