"""Load and query cell line tracker imports."""

import pandas as pd

REQUIRED_COLUMNS = {"TrackerCellLine", "TrackerID"}


def load_tracker_csv(file) -> pd.DataFrame:
    """Load a cell line tracker CSV with TrackerCellLine and TrackerID columns."""
    df = pd.read_csv(file)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Tracker CSV must include columns: {', '.join(sorted(REQUIRED_COLUMNS))}. "
            f"Missing: {', '.join(sorted(missing))}"
        )

    df = df[list(REQUIRED_COLUMNS)].copy()
    df["TrackerCellLine"] = df["TrackerCellLine"].astype(str).str.strip()
    df["TrackerID"] = df["TrackerID"].astype(str).str.strip()
    return df.dropna(subset=["TrackerID"]).loc[lambda d: d["TrackerID"] != ""]


def tracker_label(tracker_id: str, tracker_df: pd.DataFrame) -> str:
    """Format a tracker row for display in select widgets."""
    if not tracker_id:
        return "—"
    match = tracker_df.loc[tracker_df["TrackerID"] == tracker_id]
    if match.empty:
        return tracker_id
    cell_line = match.iloc[0]["TrackerCellLine"]
    return f"{cell_line} ({tracker_id})"


def suggest_tracker_id(prefix: str, tracker_df: pd.DataFrame) -> str:
    """Suggest a TrackerID when the parsed prefix matches TrackerCellLine."""
    match = tracker_df.loc[tracker_df["TrackerCellLine"].str.lower() == prefix.lower()]
    if len(match) == 1:
        return match.iloc[0]["TrackerID"]
    return ""
