#!/usr/bin/env python3
"""Attach project-local artwork paths to every generated card catalog."""

import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
IMAGES = {
    "The Fool": "images/cards/the-fool.webp",
    "The Moon": "images/cards/the-moon.webp",
    "The Sun": "images/cards/the-sun.webp",
}
SPANISH_TO_ENGLISH = {
    "El Loco": "The Fool",
    "La Luna": "The Moon",
    "El Sol": "The Sun",
}


def read_js(path: pathlib.Path, prefix: str) -> list[dict]:
    source = path.read_text(encoding="utf-8").strip()
    return json.loads(source.removeprefix(prefix).rstrip(";"))


def write_js(path: pathlib.Path, prefix: str, cards: list[dict]) -> None:
    path.write_text(prefix + json.dumps(cards, ensure_ascii=False) + ";\n", encoding="utf-8")


def attach(cards: list[dict], spanish: bool = False) -> list[dict]:
    for card in cards:
        name = card.get("Card Name", "")
        english_name = SPANISH_TO_ENGLISH.get(name, name) if spanish else name
        if english_name in IMAGES:
            card["Image"] = IMAGES[english_name]
    return cards


def main() -> None:
    english = attach(read_js(ROOT / "cards.js", "window.SOLAR_KINGDOM_CARDS="))
    spanish = attach(read_js(ROOT / "cards.es.js", "window.SOLAR_KINGDOM_CARDS_ES="), spanish=True)
    write_js(ROOT / "cards.js", "window.SOLAR_KINGDOM_CARDS=", english)
    write_js(ROOT / "cards.es.js", "window.SOLAR_KINGDOM_CARDS_ES=", spanish)
    (ROOT / "cards.en.json").write_text(json.dumps(english, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "cards.es.json").write_text(json.dumps(spanish, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
