from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

client = Anthropic(api_key=ANTHROPIC_API_KEY)


def _format_news(news_items):
    if not news_items:
        return "  (žádné novinky za sledované období)"
    return "\n".join(
        f"  - {item['headline']} — {item['summary'][:200]}" for item in news_items
    )


def build_prompt(stocks, macro_news):
    """`stocks` je seznam slovníků {"symbol", "quote", "news"} - viz main.py."""
    sections = []
    for stock in stocks:
        quote = stock["quote"]
        if quote:
            price_line = f"Cena: {quote['price']} USD, změna oproti včerejšku: {quote['change_pct']:+.2f} %"
        else:
            price_line = "Cena: nedostupná"
        sections.append(
            f"### {stock['symbol']}\n{price_line}\nNovinky:\n{_format_news(stock['news'])}"
        )

    stocks_block = "\n\n".join(sections)
    macro_block = _format_news(macro_news)

    return f"""Jsi finanční analytik. Na základě dat níže napiš KRÁTKÉ shrnutí trhu v ČEŠTINĚ, určené k odeslání na Telegram.

DATA PRO JEDNOTLIVÉ AKCIE:
{stocks_block}

OBECNÉ MAKRO NOVINKY:
{macro_block}

POKYNY PRO VÝSTUP:
- Piš v češtině, stručně a věcně.
- Pro každou akcii jeden krátký odstavec: symbol tučně, cena a % změna, emoji odhad dopadu (📈 růst / 📉 pokles / ⏸️ neutrálně) a jednu až dvě věty proč (na základě novinek, pokud nějaké jsou, jinak na základě pohybu ceny).
- Pokud pro akcii nejsou žádné relevantní novinky, napiš to a odhad založ jen na pohybu ceny.
- Na konec přidej krátký odstavec "Makro" shrnující dopad obecných zpráv na trh jako celek.
- Buď stručný, celkově maximálně 200-250 slov.
- Formátuj pro Telegram HTML parse mode: smíš použít pouze tagy <b></b> a <i></i>, žádný Markdown (žádné **hvězdičky**), žádné nadpisy typu #.
- Neopakuj tyto pokyny ve výstupu, vrať jen finální text zprávy.
"""


def generate_summary(stocks, macro_news):
    prompt = build_prompt(stocks, macro_news)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
