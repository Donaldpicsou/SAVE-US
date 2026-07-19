"""Read-only access to the CEMAC country and subdivision reference data."""

from __future__ import annotations

import json
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "cemac_regions.json"


def load_cemac_data() -> dict[str, dict]:
    """Return the complete CEMAC country reference data."""
    with DATA_PATH.open(encoding="utf-8") as dataset:
        return json.load(dataset)


def country_options() -> list[dict[str, str]]:
    """Return countries in a UI-friendly form, sorted by display name."""
    data = load_cemac_data()
    return sorted(
        [{"code": code, "name": country["name"]} for code, country in data.items()],
        key=lambda country: country["name"],
    )


def subdivisions_for(country_code: str) -> list[dict[str, str]]:
    """Return the subdivisions for one supported CEMAC country."""
    country = load_cemac_data().get(country_code)
    return [] if country is None else country["subdivisions"]
