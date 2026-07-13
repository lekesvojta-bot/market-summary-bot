import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

client = Anthropic(api_key=ANTHROPIC_API_KEY)

PRAGUE = ZoneInfo("Europe/Prague")


def _fmt_news_time(unix_timestamp):
    if not unix_timestamp:
        return ""
    prague = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc).astimezone(PRAGUE)
    return prague.strftime("%H:%M")


def _format_news(news_items, with_meta=False):
    """with_meta=True přidá čas a URL - potřebné pro makro feed, kde má
    Claude čas i odkaz zkopírovat do výstupu."""
    if not news_items:
        return "  (žádné novinky za sledované období)"
    lines = []
    for item in news_items:
        if with_meta:
            time_part = _fmt_news_time(item.get("datetime"))
            lines.append(
                f"  - [{time_part}] {item['headline']} — {item['summary'][:200]}"
                f" (zdroj: {item['source']}, url: {item['url']})"
            )
        else:
            lines.append(f"  - {item['headline']} — {item['summary'][:200]}")
    return "\n".join(lines)


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
    last = stock.get("last_earnings")
    if last:
        verdict = "nad odhadem" if last["beat"] else "pod odhadem"
        extra_lines.append(
            f"Poslední výsledky ({last['date']}): EPS {last['actual']} vs odhad "
            f"{last['estimate']} ({verdict})"
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
    macro_block = _format_news(macro_news, with_meta=True)
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
   - Odstavec "💡 <b>Tip na zajímavé akcie</b>": stejné tipy jako v klíči "tips" níže, u každého jedna věta. Jasně uveď, že jde jen o nápad k vlastnímu prozkoumání, NE investiční doporučení.
   - Odstavec "📖 <b>Pojem dne</b>": vyber JEDEN odborný pojem, který jsi v této zprávě skutečně použil, a vysvětli ho jednou-dvěma větami pro úplného laika.
   - Celkově 400-600 slov. Telegram HTML parse mode: pouze tagy <b></b> a <i></i>, žádný Markdown, žádné #.

2. "stocks" (objekt): pro každý ze symbolů {tickers} klíč s objektem:
   {{"analysis": "...", "outlook": "gain|loss|neutral"}}
   - "analysis": podrobná analýza pro web, 8-12 vět prostého textu bez HTML. Piš ve stylu: co konkrétně se stalo, proč na tom trhu záleží, jak to zapadá do širšího příběhu firmy, jaká jsou rizika a na co si dát pozor v příštích dnech/týdnech. Zohledni i poslední výsledky (beat/miss) a blížící se earnings, pokud jsou v datech.
   - "outlook": tvůj odhad dopadu na akcii - "gain" (růst), "loss" (pokles), nebo "neutral". Nemusí kopírovat dnešní pohyb ceny; jde o tvůj úsudek z novinek a kontextu.

3. "macro" (pole 2-4 objektů): nejdůležitější makro témata dne jako zpravodajský feed, každé:
   {{"time": "HH:MM", "title": "novinový titulek česky", "body": "3-5 vět česky", "url": "...", "source": "..."}}
   - "time", "url" a "source" ZKOPÍRUJ z odpovídající zdrojové novinky výše (čas je v hranaté závorce). Pokud téma vychází z více novinek, použij tu nejdůležitější. Pokud URL není, dej null.
   - Seřaď od nejnovějšího. Témata se nesmí obsahově překrývat.

4. "tips" (pole 3-4 objektů): tipy na zajímavé akcie MIMO sledovaný seznam:
   {{"ticker": "...", "name": "celé jméno firmy", "tag": "kategorie 2-3 slova", "reason": "2-3 věty proč stojí za pozornost"}}
   - Vycházej z trendů v datech výše. Alespoň jeden tip dej mimo technologický sektor (diverzifikace).
   - "tag" je krátký štítek, např. "AI síťování", "výrobní kapacita", "mimo tech sektor".

5. "glossary" (objekt): stejný pojem dne jako v telegram_message, formát {{"term": "...", "explanation": "..."}}.

6. "weekly_recap" (string nebo null): {recap_instruction}

Piš vše česky. Neopakuj tyto pokyny ve výstupu.
"""


def _output_schema(symbols):
    """JSON schéma pro structured outputs - API pak garantuje validní JSON
    přesně v této struktuře, takže parsování nemůže selhat na rozbitém výstupu."""
    stock_schema = {
        "type": "object",
        "properties": {
            "analysis": {"type": "string"},
            "outlook": {"type": "string", "enum": ["gain", "loss", "neutral"]},
        },
        "required": ["analysis", "outlook"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "telegram_message": {"type": "string"},
            "stocks": {
                "type": "object",
                "properties": {symbol: stock_schema for symbol in symbols},
                "required": list(symbols),
                "additionalProperties": False,
            },
            "macro": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "time": {"type": ["string", "null"]},
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "url": {"type": ["string", "null"]},
                        "source": {"type": ["string", "null"]},
                    },
                    "required": ["time", "title", "body", "url", "source"],
                    "additionalProperties": False,
                },
            },
            "tips": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string"},
                        "name": {"type": "string"},
                        "tag": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["ticker", "name", "tag", "reason"],
                    "additionalProperties": False,
                },
            },
            "glossary": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "explanation": {"type": "string"},
                },
                "required": ["term", "explanation"],
                "additionalProperties": False,
            },
            "weekly_recap": {"type": ["string", "null"]},
        },
        "required": [
            "telegram_message", "stocks", "macro", "tips", "glossary", "weekly_recap"
        ],
        "additionalProperties": False,
    }


def generate_summary(stocks, macro_news, weekly_recap=False):
    """Vrátí slovník s klíči telegram_message, stocks, macro, tips, glossary, weekly_recap."""
    prompt = build_prompt(stocks, macro_news, weekly_recap)
    symbols = [stock["symbol"] for stock in stocks]
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=16384,
        thinking={"type": "disabled"},
        # Structured outputs: API vynutí, že odpověď je validní JSON dle schématu.
        output_config={"format": {"type": "json_schema", "schema": _output_schema(symbols)}},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in message.content:
        if block.type == "text":
            return json.loads(block.text)
    raise ValueError("Odpověď od Claude neobsahuje žádný textový blok.")
