"""Carrier id <-> display name registry. Used for API responses and internal mapping."""
from __future__ import annotations

# Template names (payload shape): "flat" = carrierId + advisor + statesRequested; "nested" = meta + agent + appointment.
STANDARD_TEMPLATE = "flat"

# Carrier ID (numeric string) -> display name shown in UI
CARRIER_NAMES: dict[str, str] = {
    "1": "MassMutual",
    "2": "Nationwide",
    "3": "Principal",
    "4": "Lincoln Financial",
    "5": "Pacific Life",
    "6": "Guardian Life",
    "7": "Ameritas",
    "8": "Transamerica",
}

# Carrier ID -> default built-in template when no custom YAML is uploaded
DEFAULT_TEMPLATE_BY_CARRIER: dict[str, str] = {
    "1": "flat",
    "2": "nested",
    # 3-8 use standard (flat)
}


# Legacy IDs (for old submissions)
_LEGACY_NAMES: dict[str, str] = {
    "carrier-a": "MassMutual",
    "carrier-b": "Nationwide",
    "carrier-c": "Principal",
    "carrier-d": "Lincoln Financial",
    "carrier-e": "Pacific Life",
    "carrier-f": "Guardian Life",
    "carrier-g": "Ameritas",
    "carrier-h": "Transamerica",
}


def get_carrier_name(carrier_id: str) -> str:
    return CARRIER_NAMES.get(carrier_id) or _LEGACY_NAMES.get(carrier_id, carrier_id)


_LEGACY_DEFAULT_TEMPLATE: dict[str, str] = {"carrier-a": "flat", "carrier-b": "nested"}


def get_default_template(carrier_id: str) -> str:
    """Return the default template (flat or nested) for a carrier when no custom YAML is used."""
    return (
        DEFAULT_TEMPLATE_BY_CARRIER.get(carrier_id)
        or _LEGACY_DEFAULT_TEMPLATE.get(carrier_id, STANDARD_TEMPLATE)
    )


def list_carriers() -> list[dict[str, str]]:
    return [{"id": cid, "name": name} for cid, name in CARRIER_NAMES.items()]
