#!/usr/bin/env python3
"""Build static English and Spanish card catalogs from cards.js."""

from __future__ import annotations

import html
import json
import pathlib
import time
import urllib.parse
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cards.js"
TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
TRANSLATABLE_FIELDS = [
    "Core Theme", "Brief Description", "Keywords Upright", "Keywords Reversed",
    "Numerology", "Astrology", "Affirmation", "Emotional Meaning",
    "Career Meaning", "Spiritual Layer", "Psychological Shadow",
    "Symbolism Notes", "Personal Meaning", "Color Palette",
]

MAJOR_NAMES = {
    "The Fool": "El Loco", "The Magician": "El Mago",
    "The High Priestess": "La Sacerdotisa", "The Empress": "La Emperatriz",
    "The Emperor": "El Emperador", "The Hierophant": "El Hierofante",
    "The Lovers": "Los Enamorados", "The Chariot": "El Carro",
    "Strength": "La Fuerza", "The Hermit": "El Ermitaño",
    "Wheel of Fortune": "La Rueda de la Fortuna", "Justice": "La Justicia",
    "The Hanged Man": "El Colgado", "Death": "La Muerte",
    "Temperance": "La Templanza", "The Devil": "El Diablo",
    "The Tower": "La Torre", "The Star": "La Estrella", "The Moon": "La Luna",
    "The Sun": "El Sol", "Judgement": "El Juicio", "The World": "El Mundo",
    "The Rising Sun": "El Sol Naciente", "The Setting Sun": "El Sol Poniente",
    "New Moon": "Luna Nueva", "First Quarter Moon": "Cuarto Creciente",
    "Full Moon": "Luna Llena", "Last Quarter Moon": "Cuarto Menguante",
    "Solar Eclipse": "Eclipse Solar", "Lunar Eclipse": "Eclipse Lunar",
}
RANKS = {
    "Ace": "As", "Two": "Dos", "Three": "Tres", "Four": "Cuatro",
    "Five": "Cinco", "Six": "Seis", "Seven": "Siete", "Eight": "Ocho",
    "Nine": "Nueve", "Ten": "Diez", "Page": "Sota",
    "Knight": "Caballero", "Queen": "Reina", "King": "Rey",
}
TERMS = {
    "Major Arcana": "Arcano Mayor", "Minor Arcana": "Arcano Menor",
    "Special Card": "Carta Especial", "Major": "Mayor", "Special": "Especial",
    "Wands": "Bastos", "Cups": "Copas", "Swords": "Espadas",
    "Pentacles": "Oros", "Fire": "Fuego", "Water": "Agua", "Air": "Aire",
    "Earth": "Tierra", "Spirit": "Espíritu", "Light": "Luz",
    "Shadow": "Sombra", "Divine": "Divino", "Solar": "Solar", "Lunar": "Lunar",
    "Multiple": "Múltiple", "Yes": "Sí", "No": "No", "Neutral": "Neutral",
}


def read_cards() -> list[dict]:
    source = SOURCE.read_text(encoding="utf-8").strip()
    prefix = "window.SOLAR_KINGDOM_CARDS="
    if not source.startswith(prefix):
        raise RuntimeError("Unexpected cards.js format")
    return json.loads(source[len(prefix):].rstrip(";"))


def card_name_es(name: str) -> str:
    if name in MAJOR_NAMES:
        return MAJOR_NAMES[name]
    for rank, rank_es in RANKS.items():
        for suit in ("Wands", "Cups", "Swords", "Pentacles"):
            if name == f"{rank} of {suit}":
                return f"{rank_es} de {TERMS[suit]}"
    return name


def translate(text: str, retries: int = 3) -> str:
    if not text:
        return ""
    payload = urllib.parse.urlencode({
        "client": "gtx", "sl": "en", "tl": "es", "dt": "t", "q": text,
    }).encode()
    for attempt in range(retries):
        try:
            request = urllib.request.Request(TRANSLATE_URL, data=payload)
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.load(response)
            return html.unescape("".join(part[0] for part in result[0] if part[0])).strip()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("Translation failed")


def translate_card(card: dict, index: int, total: int) -> dict:
    result = dict(card)
    result["Card Name"] = card_name_es(card.get("Card Name", ""))
    for field in ("Arcana", "Suit", "Element", "Yes / No"):
        result[field] = TERMS.get(card.get(field, ""), card.get(field, ""))
    result["Energy Type"] = [TERMS.get(value, value) for value in card.get("Energy Type", [])]

    values = [str(card.get(field, "")) for field in TRANSLATABLE_FIELDS]
    delimiter = "\n__SKT_CARD_FIELD__\n"
    translated = translate(delimiter.join(values))
    parts = translated.split("__SKT_CARD_FIELD__")
    parts = [part.strip(" \n") for part in parts]
    if len(parts) != len(values):
        parts = [translate(value) for value in values]
    for field, value in zip(TRANSLATABLE_FIELDS, parts):
        result[field] = value
    print(f"[{index:02d}/{total}] {card['Card Name']} → {result['Card Name']}", flush=True)
    time.sleep(0.12)
    return result


def write_json(path: pathlib.Path, cards: list[dict]) -> None:
    path.write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    cards_en = read_cards()
    cards_es = [translate_card(card, index, len(cards_en)) for index, card in enumerate(cards_en, 1)]
    write_json(ROOT / "cards.en.json", cards_en)
    write_json(ROOT / "cards.es.json", cards_es)
    (ROOT / "cards.es.js").write_text(
        "window.SOLAR_KINGDOM_CARDS_ES=" + json.dumps(cards_es, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print("Built cards.en.json, cards.es.json and cards.es.js", flush=True)


if __name__ == "__main__":
    main()
