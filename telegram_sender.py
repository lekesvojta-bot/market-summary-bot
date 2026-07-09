import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

TELEGRAM_MESSAGE_LIMIT = 4096


def _chunk_text(text, limit):
    """Rozdělí text na kusy do `limit` znaků, pokud možno na hranici řádku."""
    chunks = []
    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:]
    chunks.append(text)
    return chunks


def send_message(text):
    """Pošle text na Telegram. Pokud je delší než limit, rozdělí ho na víc zpráv."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chunk in _chunk_text(text, TELEGRAM_MESSAGE_LIMIT):
        chunk = chunk.strip()
        if not chunk:
            continue
        response = requests.post(
            url,
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        response.raise_for_status()
