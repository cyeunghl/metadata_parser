"""Parse source metadata CSV and extract FCS filename components."""

import re
from dataclasses import dataclass

import pandas as pd

FCS_PATTERN = re.compile(
    r"^(?P<prefix>.+?)(?P<date>\d{4}-\d{2}-\d{2})\.(?P<suffix>\d+)\.fcs$"
)

BEAD_SAMPLE_PATTERN = re.compile(r"^beads?$", re.IGNORECASE)


@dataclass
class ParsedRow:
    fcs_file: str
    prefix: str
    date: str
    suffix: str

    @property
    def suffix_int(self) -> int:
        return int(self.suffix)


def is_bead_sample(value: str) -> bool:
    """Return True if the Sample/CellLine value indicates a bead row."""
    return bool(BEAD_SAMPLE_PATTERN.match(value.strip()))


def parse_fcs_filename(filename: str) -> ParsedRow | None:
    """Parse a single FCS filename into prefix, date, and suffix."""
    match = FCS_PATTERN.match(filename.strip())
    if not match:
        return None
    return ParsedRow(
        fcs_file=filename.strip(),
        prefix=match.group("prefix"),
        date=match.group("date"),
        suffix=match.group("suffix"),
    )


def load_source_csv(file) -> pd.DataFrame:
    """Load the source metadata CSV from a file-like object or path."""
    return pd.read_csv(file, header=0)


def extract_fcs_filenames(df: pd.DataFrame) -> list[str]:
    """Extract FCS filenames from the first column of the source CSV."""
    col = df.columns[0]
    filenames: list[str] = []
    for value in df[col]:
        text = str(value).strip()
        if text.endswith(".fcs"):
            filenames.append(text)
    return filenames


def parse_metadata(file) -> list[ParsedRow]:
    """Load and parse all valid FCS rows from a source metadata CSV."""
    df = load_source_csv(file)
    rows: list[ParsedRow] = []
    for filename in extract_fcs_filenames(df):
        parsed = parse_fcs_filename(filename)
        if parsed is not None:
            rows.append(parsed)
    return rows


def unique_prefixes(rows: list[ParsedRow]) -> list[str]:
    """Return sorted unique prefixes."""
    return sorted({row.prefix for row in rows})


def unique_suffixes(rows: list[ParsedRow]) -> list[str]:
    """Return unique suffixes sorted numerically."""
    return sorted({row.suffix for row in rows}, key=int)


def rows_to_dataframe(rows: list[ParsedRow]) -> pd.DataFrame:
    """Convert parsed rows to a preview dataframe."""
    return pd.DataFrame(
        [
            {
                "FCSFile": row.fcs_file,
                "prefix": row.prefix,
                "date": row.date,
                "suffix": row.suffix,
            }
            for row in rows
        ]
    )
