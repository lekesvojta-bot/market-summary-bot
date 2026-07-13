import json

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

client = Anthropic(api_key=ANTHROPIC_API_KEY)


def _format_news(news_items):
    if not news_items:
        return "  (žádné novinky za sledované období)"
    return "\n".join(
        f"  - {item['headline']} — {item['summary'][:200]}" for item in news_items
    )


def _build_stock_section(stock):
    quote = stock["quote"]
    if quote:
        price_line = (
            f"Cena: {quote['price']} USD, změna oproti včerejšku: {quote['change_pct']:+.2f} %, "
            f"denní rozpětí: {quote['day_low']}–{quote['day_high']} USD (otevřeno na {quote['day_open']} USD)"
        )
    else:
        price_line = "Cena: nedostupná"

    extra_lines = []
    if stock.get("week_change_pct") is not None:
        extra_lines.append(f"Změna za ~7 dní: {stock['week_change_pct']:+.2f} %")
    if stock.get("earnings_date"):
        extra_lines.append(
            f"POZOR: kvartální výsledky (earnings) už {stock['earnings_date']}"
        )
    if stock.get("note"):
        extra_lines.append(f"Poznámka: {stock['note']}")

    extra_block = "\n".join(extra_lines)
    if extra_block:
        extra_block += "\n"
    return f"### {stock['symbol']}\n{price_line}\n{extra_block}Novinky:\n{_format_news(stock['news'])}"


def build_prompt(stocks, macro_news, weekly_recap):
    """`stocks` je seznam slovníků - viz main.py. `weekly_recap`: True v pátek večer."""
    stocks_block = "\n\n".join(_build_stock_section(stock) for stock in stocks)
    macro_block = _format_news(macro_news)
    tickers = ", ".join(stock["symbol"] for stock in stocks)

    if weekly_recap:
        recap_instruction = (
            'Je pátek večer - do klíče "weekly_recap" napiš týdenní rekapitulaci (8-12 vět): '
            "co tento týden hýbalo trhem, kterým sledovaným akciím se dařilo/nedařilo a proč, "
            "s využitím týdenních změn v datech. Piš srozumitelně pro neprofesionála."
        )
    else:
        recap_instruction = 'Do klíče "weekly_recap" dej null.'

    return f"""Jsi finanční analytik píšící pro laika, který chce rozumět dění na trhu. Na základě dat níže vytvoř výstup PŘESNĚ ve formátu JSON popsaném na konci.

DATA PRO JEDNOTLIVÉ AKCIE:
{stocks_block}

OBECNÉ MAKRO NOVINKY:
{macro_block}

POŽADOVANÝ VÝSTUP - vrať POUZE validní JSON objekt (žádný text před ním ani za ním, žádné ```značky) s těmito klíči:

1. "telegram_message" (string): Zpráva pro Telegram v češtině, formát:
   - Pro každou akcii odstavec: symbol tučně, cena, % změna a denní rozpětí, emoji odhad dopadu (📈 růst / 📉 pokles / ⏸️ neutrálně) a 2-4 věty proč (na základě novinek, jinak pohybu ceny). Pokud známe změnu za ~7 dní, zmiň ji. Pokud se blíží earnings, upozorni na ně (⚠️ + datum + že kolem výsledků bývá zvýšená volatilita).
   - Pokud je u akcie "Poznámka", stručně ji zmiň, nezabíhej do detailu.
   - Odstavec "🌍 <b>Makro</b>": dopad obecných zpráv na trh, 3-5 vět.
   - Odstavec "💡 <b>Tip na zajímavé akcie</b>": 2-3 tickery (mohou být mimo sledovaný seznam) podle trendů z dat, s větou zdůvodnění. Jasně uveď, že jde jen o nápad k vlastnímu prozkoumání, NE investiční doporučení.
   - Odstavec "📖 <b>Pojem dne</b>": vyber JEDEN odborný pojem, který jsi v této zprávě skutečně použil, a vysvětli ho jednou-dvěma větami pro úplného laika.
   - Celkově 400-600 slov. Telegram HTML parse mode: pouze tagy <b></b> a <i></i>, žádný Markdown, žádné #.
2. "stocks" (objekt): pro každý ze symbolů {tickers} klíč se stringem - podrobnější analýza pro web, 4-8 vět: co se děje, proč, souvislosti, na co si dát pozor. Prostý text bez HTML.
3. "macro" (string): podrobnější makro analýza pro web, 5-8 vět, prostý text.
4. "tips" (pole objektů): stejné tipy jako v telegram_message, formát [{{"ticker": "...", "reason": "..."}}].
5. "glossary" (objekt): stejný pojem dne, formát {{"term": "...", "explanation": "..."}}.
6. "weekly_recap" (string nebo null): {recap_instruction}

Piš vše česky. Neopakuj tyto pokyny ve výstupu.
"""


def generate_summary(stocks, macro_news, weekly_recap=False):
    """Vrátí slovník s klíči telegram_message, stocks, macro, tips, glossary, weekly_recap."""
    prompt = build_prompt(stocks, macro_news, weekly_recap)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=8192,
        thinking={"type": "disabled"},
        messages=[{"role": "user", "content": prompt}],
    )
    # Odpověď může kromě textu obsahovat i "thinking" blok (interní úvahu
    # modelu), takže hledáme konkrétně blok typu "text", ne jen content[0].
    text = None
    for block in message.content:
        if block.type == "text":
            text = block.text
            break
    if text is None:
        raise ValueError("Odpověď od Claude neobsahuje žádný textový blok.")

    # Model má vrátit čistý JSON, ale pro jistotu ostříháme případné ```obaly.
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]

    output = json.loads(text)
    for required_key in ("telegram_message", "stocks", "macro"):
        if required_key not in output:
            raise ValueError(f"V odpovědi od Claude chybí klíč '{required_key}'.")
    return output
