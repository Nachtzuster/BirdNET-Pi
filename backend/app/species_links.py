"""Helpers for constructing external species reference links."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import quote


BACKEND_DIR = Path(__file__).resolve().parent
BASE_DIR = BACKEND_DIR.parent.parent
EBIRD_CODES_PATH = BACKEND_DIR / "data" / "ebird_codes.json"
LABELS_EN_PATH = BASE_DIR / "model" / "l18n" / "labels_en.json"


@lru_cache(maxsize=1)
def load_ebird_codes() -> dict[str, str]:
    """Load scientific-name to eBird species code mappings."""
    with EBIRD_CODES_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_english_labels() -> dict[str, str]:
    """Load scientific-name to English common-name mappings."""
    with LABELS_EN_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def allaboutbirds_slug(name: str) -> str:
    """Convert a common name to All About Birds guide slug format."""
    return name.replace("'", "").replace(" ", "_")


def build_species_links(
    sci_name: str,
    com_name: Optional[str] = None,
    language: str = "en",
) -> dict:
    """Construct eBird + All About Birds links for a species."""
    sci_name = sci_name.strip()
    ebird_raw_code = load_ebird_codes().get(sci_name)
    ebird_code = None if not ebird_raw_code or ebird_raw_code.lower() == "null" else ebird_raw_code

    english_name = load_english_labels().get(sci_name) or com_name or sci_name
    aab_slug = allaboutbirds_slug(english_name)

    return {
        "sci_name": sci_name,
        "com_name": com_name,
        "english_name": english_name,
        "ebird": {
            "available": bool(ebird_code),
            "code": ebird_code,
            "url": (
                f"https://ebird.org/species/{ebird_code}?siteLanguage={quote(language)}"
                if ebird_code
                else None
            ),
        },
        "allaboutbirds": {
            "available": bool(aab_slug),
            "slug": aab_slug,
            "url": f"https://allaboutbirds.org/guide/{quote(aab_slug)}" if aab_slug else None,
        },
    }

