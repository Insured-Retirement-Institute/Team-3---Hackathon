"""Carrier id <-> display name registry. Used for API responses and internal mapping."""
from __future__ import annotations

# Template names (payload shape): "flat" = carrierId + advisor + statesRequested; "nested" = meta + agent + appointment.
STANDARD_TEMPLATE = "flat"

# Carrier ID (numeric 1-8) -> display name shown in UI
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

# Name (lower) -> carrier id, for resolving "Principal" -> "3"
_NAME_TO_ID: dict[str, str] = {
    (name or "").strip().lower(): cid
    for cid, name in CARRIER_NAMES.items()
    if name
}


def get_carrier_name(carrier_id: str) -> str:
    return CARRIER_NAMES.get(carrier_id, carrier_id)


def get_carrier_id_by_name(name: str) -> str | None:
    """Resolve a carrier name or id to carrier id (numeric 1-8)."""
    if not name or not isinstance(name, str):
        return None
    s = name.strip()
    if not s:
        return None
    if s in CARRIER_NAMES:
        return s
    return _NAME_TO_ID.get(s.lower())


def resolve_carrier_names_to_ids(values: list[str]) -> list[str]:
    """
    Resolve a list of carrier identifiers (ids or names, comma-separated allowed) to numeric carrier IDs (1-8).
    E.g. ['1', 'Principal', 'ABC Life, Principal'] -> ['1', '3'] (deduped, order preserved).
    """
    seen: set[str] = set()
    result: list[str] = []

    def add_if_known(cid: str) -> None:
        if cid and cid not in seen:
            seen.add(cid)
            result.append(cid)

    for raw in values:
        if not raw or not isinstance(raw, str):
            continue
        raw_clean = raw.strip()
        if not raw_clean:
            continue
        for part in (p.strip() for p in raw_clean.split(",") if p.strip()):
            cid = get_carrier_id_by_name(part)
            if cid:
                add_if_known(cid)
            else:
                for known_name_lower, known_id in _NAME_TO_ID.items():
                    if known_name_lower in part.lower():
                        add_if_known(known_id)
                        break
        if not result and raw_clean:
            raw_lower = raw_clean.lower()
            for known_name_lower, known_id in _NAME_TO_ID.items():
                if known_name_lower in raw_lower:
                    add_if_known(known_id)
    return result


def get_default_template(carrier_id: str) -> str:
    """Return the default template (flat or nested) for a carrier when no custom YAML is used."""
    return DEFAULT_TEMPLATE_BY_CARRIER.get(carrier_id, STANDARD_TEMPLATE)


def list_carriers() -> list[dict[str, str]]:
    return [{"id": cid, "name": name} for cid, name in CARRIER_NAMES.items()]
