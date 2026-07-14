# Tržní notifikační bot

Python bot, který jednou denně večer stáhne ceny a novinky pro NVDA, AMD, GOOGL,
META, AAPL, MSFT a VUAA (přes SPY) z Finnhub API, nechá Claude API vygenerovat
české shrnutí s odhadem dopadu a pošle ho na Telegram. Běží automaticky přes
GitHub Actions.

Součástí je i **webový dashboard** (GitHub Pages) s podrobnějšími analýzami,
grafy vývoje cen, novinkami s odkazy a archivem starších běhů:
**https://lekesvojta-bot.github.io/market-summary-bot/**

Jak web funguje: každý běh bota uloží data do `docs/data/` a workflow je
commitne do repa. GitHub Pages servíruje statickou stránku `docs/index.html`,
která tato JSON data načítá JavaScriptem. Žádný server není potřeba.

Když jakýkoliv běh selže, bot pošle na Telegram upozornění s odkazem na log
(krok "Upozornit na selhání" ve workflow).

## 1. Založení Anthropic (Claude) API klíče

1. Jdi na https://console.anthropic.com a zaregistruj se / přihlas se.
2. V levém menu klikni na **API Keys**.
3. Klikni na **Create Key**, pojmenuj ji (např. `market-bot`) a klíč zkopíruj.
   Klíč se zobrazí jen jednou, tak si ho hned ulož (např. do `.env`, viz níže).
4. Do účtu bude potřeba nahrát malý kredit (Billing sekce v Console) — bez kreditu
   API volání selžou.

## 2. Lokální nastavení a test

1. Zkopíruj `.env.example` do nového souboru `.env` (ve stejné složce).
2. Do `.env` vyplň všechny 4 hodnoty (Finnhub, Anthropic, Telegram token, chat_id).
3. Nainstaluj závislosti:
   ```
   pip install -r requirements.txt
   ```
4. Spusť bota:
   ```
   python main.py
   ```
   Pokud vše proběhne bez chyby, dorazí ti zpráva na Telegram a v terminálu uvidíš
   průběžné výpisy (`Stahuji data pro NVDA...` apod.).

## 3. Nastavení GitHub Secrets (pro automatický běh)

1. V repozitáři na GitHubu jdi do **Settings → Secrets and variables → Actions**.
2. Klikni **New repository secret** a přidej postupně tyto 4 secrets (přesně
   pod těmito názvy, hodnoty stejné jako v tvém `.env`):
   - `FINNHUB_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. Nahraj (push) kód do repozitáře, pokud jsi to ještě neudělal.

## 4. Ruční test workflow na GitHubu

1. Jdi do záložky **Actions** v repozitáři.
2. Vlevo vyber workflow **Market Summary**.
3. Klikni **Run workflow** (tlačítko vpravo) a potvrď.
4. Sleduj log běhu — pokud je vše v pořádku, přijde ti zpráva na Telegram stejně
   jako při lokálním testu.

## 5. Automatický běh

Jakmile ruční test projde, není potřeba nic dalšího dělat — workflow poběží
sám jednou denně večer podle rozvrhu v `.github/workflows/market-summary.yml`
(cca 20:05 českého letního času; v zimě o hodinu později, viz komentář v souboru).

## Struktura projektu

- `config.py` — načtení API klíčů a nastavení (sledované akcie, časové okno novinek)
- `finnhub_client.py` — stahování cen a novinek z Finnhub
- `claude_summary.py` — sestavení promptu a volání Claude API
- `telegram_sender.py` — odeslání zprávy přes Telegram Bot API
- `main.py` — propojení všeho dohromady
- `.github/workflows/market-summary.yml` — plánované spouštění přes GitHub Actions
