"""Build Pl1_metadata output from parsed rows and user mappings."""

from dataclasses import dataclass

import pandas as pd

from antibody_config import get_channel
from parser import ParsedRow, is_bead_sample


OUTPUT_COLUMNS = ["FCSFile", "Sample/CellLine", "Antibody", "Channel", "Notes", "WellID"]
MAX_WELLS = 96


@dataclass
class ConversionConfig:
    prefix_sample_map: dict[str, str]
    suffix_antibody_map: dict[str, str]
    bead_prefix_antibody_map: dict[str, str]
    bead_base: str
    suffix_notes_map: dict[str, str]


def generate_well_ids(count: int) -> list[str]:
    """Generate sequential 96-well IDs in row-major order (A1..A12, B1..B12, ...)."""
    wells: list[str] = []
    for row_letter in "ABCDEFGH":
        for col in range(1, 13):
            wells.append(f"{row_letter}{col}")
            if len(wells) >= count:
                return wells
    return wells


def _sort_clone_rows(rows: list[ParsedRow]) -> list[ParsedRow]:
    return sorted(rows, key=lambda r: (r.prefix, r.suffix_int))


def _sort_bead_rows(rows: list[ParsedRow]) -> list[ParsedRow]:
    return sorted(rows, key=lambda r: (r.prefix, r.suffix_int))


def _bead_index_within_prefix(rows: list[ParsedRow]) -> dict[str, int]:
    """Map fcs_file to 0-based index within its prefix group (by ascending suffix)."""
    indices: dict[str, int] = {}
    by_prefix: dict[str, list[ParsedRow]] = {}
    for row in rows:
        by_prefix.setdefault(row.prefix, []).append(row)
    for prefix_rows in by_prefix.values():
        for index, row in enumerate(sorted(prefix_rows, key=lambda r: r.suffix_int)):
            indices[row.fcs_file] = index
    return indices


def validate_config(rows: list[ParsedRow], config: ConversionConfig) -> list[str]:
    """Return a list of validation error messages."""
    errors: list[str] = []
    prefixes = {row.prefix for row in rows}

    for prefix in prefixes:
        if prefix not in config.prefix_sample_map or not config.prefix_sample_map[prefix].strip():
            errors.append(f"Missing Sample/CellLine mapping for prefix: {prefix}")

    bead_prefixes = {
        p for p, sample in config.prefix_sample_map.items() if is_bead_sample(sample)
    }
    clone_prefixes = prefixes - bead_prefixes

    if clone_prefixes:
        suffixes = {row.suffix for row in rows if row.prefix in clone_prefixes}
        for suffix in suffixes:
            if suffix not in config.suffix_antibody_map or not config.suffix_antibody_map[suffix]:
                errors.append(f"Missing Antibody mapping for suffix: {suffix}")

    for prefix in bead_prefixes:
        if prefix not in config.bead_prefix_antibody_map or not config.bead_prefix_antibody_map[prefix]:
            errors.append(f"Missing Antibody mapping for bead prefix: {prefix}")

    if bead_prefixes and not config.bead_base.strip():
        errors.append("Bead base ID is required when bead prefixes are present.")

    return errors


def convert(rows: list[ParsedRow], config: ConversionConfig) -> tuple[pd.DataFrame, list[str]]:
    """Convert parsed rows to Pl1_metadata format. Returns (dataframe, warnings)."""
    warnings: list[str] = []
    errors = validate_config(rows, config)
    if errors:
        raise ValueError("\n".join(errors))

    bead_prefixes = {
        p for p, sample in config.prefix_sample_map.items() if is_bead_sample(sample)
    }

    clone_rows = [r for r in rows if r.prefix not in bead_prefixes]
    bead_rows = [r for r in rows if r.prefix in bead_prefixes]

    clone_rows = _sort_clone_rows(clone_rows)
    bead_rows = _sort_bead_rows(bead_rows)
    ordered_rows = clone_rows + bead_rows

    bead_indices = _bead_index_within_prefix(bead_rows)
    output_rows: list[dict[str, str]] = []

    for row in ordered_rows:
        if row.prefix in bead_prefixes:
            index = bead_indices[row.fcs_file]
            sample = f"{config.bead_base.strip()}/{index}"
            antibody = config.bead_prefix_antibody_map[row.prefix]
            notes = ""
        else:
            sample = config.prefix_sample_map[row.prefix].strip()
            antibody = config.suffix_antibody_map[row.suffix]
            notes = config.suffix_notes_map.get(row.suffix, "").strip()

        output_rows.append(
            {
                "FCSFile": row.fcs_file,
                "Sample/CellLine": sample,
                "Antibody": antibody,
                "Channel": get_channel(antibody),
                "Notes": notes,
                "WellID": "",
            }
        )

    if len(output_rows) > MAX_WELLS:
        warnings.append(
            f"Output has {len(output_rows)} rows but only {MAX_WELLS} wells are available."
        )

    well_ids = generate_well_ids(len(output_rows))
    for i, well_id in enumerate(well_ids):
        output_rows[i]["WellID"] = well_id

    return pd.DataFrame(output_rows, columns=OUTPUT_COLUMNS), warnings
