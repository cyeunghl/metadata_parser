"""Hardwired antibody to channel mapping."""

ANTIBODY_CHANNEL_MAP: dict[str, str] = {
    "HER2": "APC",
    "TROP2": "PE",
    "ABCB1": "PE",
    "ABCG2": "PE",
    "HB-44976": "APC, PE",
}

CLONE_ANTIBODY_CHANNEL_MAP: dict[str, str] = {
    **ANTIBODY_CHANNEL_MAP,
    "cMET": "FITC",
}

ANTIBODY_OPTIONS: list[str] = list(ANTIBODY_CHANNEL_MAP.keys())
CLONE_ANTIBODY_OPTIONS: list[str] = list(CLONE_ANTIBODY_CHANNEL_MAP.keys())


def get_channel(antibody: str) -> str:
    """Return the channel for a given antibody."""
    return CLONE_ANTIBODY_CHANNEL_MAP[antibody]
