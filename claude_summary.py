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
    """`stocks` je seznam slovníků {"symbol", "quote", "news", "note"} - viz main.py."""
    sections = []
    for stock in stocks:
        quote = stock["quote"]
        if quote:
            price_line = (
                f"Cena: {quote['price']} USD, změna oproti včerejšku: {quote['change_pct']:+.2f} %, "
                f"denní rozpětí: {quote['day_low']}–{quote['day_high']} USD (otevřeno na {quote['day_open']} USD)"
            )
        else:
            price_line = "Cena: nedostupná"
        note_line = f"Poznámka: {stock['note']}\n" if stock.get("note") else ""
        sections.append(
            f"### {stock['symbol']}\n{note_line}{price_line}\nNovinky:\n{_format_news(stock['news'])}"
        )

    stocks_block = "\n\n".join(sections)
    macro_block = _format_news(macro_news)

    return f"""Jsi finanční analytik. Na základě dat níže napiš PODROBNÉ shrnutí trhu v ČEŠTINĚ, určené k odeslání na Telegram.

DATA PRO JEDNOTLIVÉ AKCIE:
{stocks_block}

OBECNÉ MAKRO NOVINKY:
{macro_block}

POKYNY PRO VÝSTUP:
- Piš v češtině, věcně, ale podrobněji než jen jednou větou - u každé akcie rozveď kontext (co konkrétně se stalo, proč na tom trhu záleží, jak to zapadá do denního rozpětí ceny).
- Pro každou akcii odstavec: symbol tučně, cena, % změna a denní rozpětí, emoji odhad dopadu (📈 růst / 📉 pokles / ⏸️ neutrálně) a 2-4 věty proč (na základě novinek, pokud nějaké jsou, jinak na základě pohybu ceny a rozpětí).
- Pokud je u akcie "Poznámka", stručně ji zmiň (např. že jde o proxy přes jiný symbol), ale nezabíhej do detailu.
- Pokud pro akcii nejsou žádné relevantní novinky, napiš to a odhad založ jen na pohybu ceny.
- Přidej odstavec "🌍 <b>Makro</b>" shrnující dopad obecných zpráv na trh jako celek, klidně 3-5 vět.
- Na úplný konec přidej odstavec "💡 <b>Tip na zajímavé akcie</b>": 2-3 tickery (mohou být i mimo sledovaný seznam), které by podle aktuálních novinek/trendů z dat výše mohly stát za pozornost, s jednou větou zdůvodnění u každého. Jasně uveď, že jde jen o nápad k vlastnímu prozkoumání založený na obecných trendech, NE o investiční doporučení, protože pro tyto tickery nemáme aktuální cenu ani novinky.
- Celkově piš spíš 400-600 slov, ale nenaťahuj to prázdnými frázemi.
- Formátuj pro Telegram HTML parse mode: smíš použít pouze tagy <b></b> a <i></i>, žádný Markdown (žádné **hvězdičky**), žádné nadpisy typu #.
- Neopakuj tyto pokyny ve výstupu, vrať jen finální text zprávy.
"""


def generate_summary(stocks, macro_news):
    prompt = build_prompt(stocks, macro_news)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        thinking={"type": "disabled"},
        messages=[{"role": "user", "content": prompt}],
    )
    # Odpověď může kromě textu obsahovat i "thinking" blok (interní úvahu
    # modelu), takže hledáme konkrétně blok typu "text", ne jen content[0].
    for block in message.content:
        if block.type == "text":
            return block.text
    raise ValueError("Odpověď od Claude neobsahuje žádný textový blok.")
