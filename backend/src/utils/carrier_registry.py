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


# Reverse: name (normalized lower) -> carrier id. Prefer numeric IDs (1-8) over legacy (carrier-a etc.).
def _name_to_id_map() -> dict[str, str]:
    out: dict[str, str] = {}
    for cid, name in CARRIER_NAMES.items():
        if name:
            out[name.strip().lower()] = cid
    for cid, name in _LEGACY_NAMES.items():
        if name:
            key = name.strip().lower()
            if key not in out:
                out[key] = cid
    return out


_NAME_TO_ID = _name_to_id_map()


def get_carrier_id_by_name(name: str) -> str | None:
    """Resolve a carrier name or id to carrier id. Prefer numeric id (1-8) over legacy (carrier-a)."""
    if not name or not isinstance(name, str):
        return None
    s = name.strip()
    if not s:
        return None
    if s in CARRIER_NAMES:
        return s
    if s in _LEGACY_NAMES:
        canonical = _NAME_TO_ID.get(_LEGACY_NAMES[s].strip().lower())
        return canonical if canonical else s
    return _NAME_TO_ID.get(s.lower())


def resolve_carrier_names_to_ids(values: list[str]) -> list[str]:
    """
    Resolve a list of carrier identifiers (ids or names, comma-separated allowed) to carrier IDs.
    E.g. ['1', 'Principal', 'ABC Life, Principal'] -> ['1', '3'] (deduped, order preserved).
    Unknown names are skipped; if a segment contains a known name (e.g. 'Principal' in 'XYZ, Principal'),
    that carrier is included. Also matches known names inside the whole raw string so
    'ABC Life Insurance Company, XYZ Annuity Corp, Principal' resolves to ['3'].
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
        # First try exact/match per segment (split by comma)
        for part in (p.strip() for p in raw_clean.split(",") if p.strip()):
            cid = get_carrier_id_by_name(part)
            if cid:
                add_if_known(cid)
            else:
                # Try to find any known carrier name inside this segment (e.g. "Principal" in "Principal Financial")
                for known_name_lower, known_id in _NAME_TO_ID.items():
                    if known_name_lower in part.lower():
                        add_if_known(known_id)
                        break
        # If the whole raw string was one segment and we didn't match, try containment on the full string
        # (e.g. "ABC Life Insurance Company, XYZ Annuity Corp, Principal" contains "principal")
        if not result and raw_clean:
            raw_lower = raw_clean.lower()
            for known_name_lower, known_id in _NAME_TO_ID.items():
                if known_name_lower in raw_lower:
                    add_if_known(known_id)
    return result


_LEGACY_DEFAULT_TEMPLATE: dict[str, str] = {"carrier-a": "flat", "carrier-b": "nested"}


def get_default_template(carrier_id: str) -> str:
    """Return the default template (flat or nested) for a carrier when no custom YAML is used."""
    return (
        DEFAULT_TEMPLATE_BY_CARRIER.get(carrier_id)
        or _LEGACY_DEFAULT_TEMPLATE.get(carrier_id, STANDARD_TEMPLATE)
    )


def list_carriers() -> list[dict[str, str]]:
    return [{"id": cid, "name": name} for cid, name in CARRIER_NAMES.items()]
