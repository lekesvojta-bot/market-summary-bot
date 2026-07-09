from datetime import datetime

import claude_summary
import config
import finnhub_client
import telegram_sender


def collect_stock_data():
    stocks = []
    for ticker in config.TICKERS:
        symbol = ticker["symbol"]
        # finnhub_symbol umožňuje stahovat data pod jiným symbolem, než se
        # zobrazuje (např. VUAA se sleduje přes americké SPY, viz config.py).
        finnhub_symbol = ticker.get("finnhub_symbol", symbol)
        print(f"Stahuji data pro {symbol} ({finnhub_symbol})...")
        quote = finnhub_client.get_quote(finnhub_symbol)
        news = finnhub_client.get_company_news(finnhub_symbol, config.NEWS_LOOKBACK_HOURS)
        stocks.append(
            {"symbol": symbol, "quote": quote, "news": news, "note": ticker.get("note")}
        )
    return stocks


def main():
    print(f"=== Spouštím tržní shrnutí: {datetime.now().isoformat()} ===")

    stocks = collect_stock_data()

    print("Stahuji makro novinky...")
    macro_news = finnhub_client.get_general_market_news(config.NEWS_LOOKBACK_HOURS)

    print("Generuji shrnutí přes Claude API...")
    summary = claude_summary.generate_summary(stocks, macro_news)

    header = f"📊 <b>Přehled trhu — {datetime.now().strftime('%d.%m.%Y %H:%M')}</b>\n\n"
    message = header + summary

    print("Posílám na Telegram...")
    telegram_sender.send_message(message)

    print("Hotovo.")


if __name__ == "__main__":
    main()
