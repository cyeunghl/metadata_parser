"""Streamlit app for converting example metadata CSV to Pl1_metadata format."""

import io
from pathlib import Path

import pandas as pd
import streamlit as st

from antibody_config import ANTIBODY_OPTIONS, CLONE_ANTIBODY_OPTIONS, get_channel
from converter import ConversionConfig, convert
from parser import (
    is_bead_sample,
    parse_metadata,
    rows_to_dataframe,
    unique_prefixes,
    unique_suffixes,
)

EXAMPLE_FILE = Path(__file__).parent / "exampleMetadata - Sheet1.csv"


def _init_session_state(parsed_rows) -> None:
    prefixes = unique_prefixes(parsed_rows)
    suffixes = unique_suffixes(parsed_rows)

    if "prefix_sample_map" not in st.session_state:
        st.session_state.prefix_sample_map = {p: "" for p in prefixes}
    else:
        for p in prefixes:
            st.session_state.prefix_sample_map.setdefault(p, "")

    if "suffix_antibody_map" not in st.session_state:
        st.session_state.suffix_antibody_map = {s: "" for s in suffixes}
    else:
        for s in suffixes:
            st.session_state.suffix_antibody_map.setdefault(s, "")

    if "suffix_notes_map" not in st.session_state:
        st.session_state.suffix_notes_map = {s: "" for s in suffixes}
    else:
        for s in suffixes:
            st.session_state.suffix_notes_map.setdefault(s, "")

    if "bead_prefix_antibody_map" not in st.session_state:
        st.session_state.bead_prefix_antibody_map = {}
    if "bead_base" not in st.session_state:
        st.session_state.bead_base = ""


def main() -> None:
    st.set_page_config(page_title="Metadata Converter", layout="wide")
    st.title("Metadata Converter")
    st.caption("Convert example metadata CSV into Pl1_metadata format.")

    uploaded = st.file_uploader("Upload source metadata CSV", type=["csv"])
    use_example = st.checkbox("Use bundled example file", value=uploaded is None)

    if uploaded is not None:
        source = uploaded
    elif use_example and EXAMPLE_FILE.exists():
        source = EXAMPLE_FILE
    else:
        st.info("Upload a CSV or enable the bundled example file to begin.")
        return

    parsed_rows = parse_metadata(source)
    if not parsed_rows:
        st.error("No valid .fcs filenames found in the uploaded file.")
        return

    _init_session_state(parsed_rows)

    st.subheader("Parse Preview")
    preview_df = rows_to_dataframe(parsed_rows)
    st.dataframe(preview_df, use_container_width=True)
    st.write(
        f"**{len(parsed_rows)}** FCS files · "
        f"**{len(unique_prefixes(parsed_rows))}** unique prefixes · "
        f"**{len(unique_suffixes(parsed_rows))}** unique suffixes"
    )

    st.subheader("Prefix → Sample/CellLine")
    prefixes = unique_prefixes(parsed_rows)
    for prefix in prefixes:
        cols = st.columns([2, 3, 1])
        with cols[0]:
            st.text(prefix)
        with cols[1]:
            value = st.text_input(
                "Sample/CellLine",
                value=st.session_state.prefix_sample_map.get(prefix, ""),
                key=f"prefix_sample_{prefix}",
                label_visibility="collapsed",
            )
            st.session_state.prefix_sample_map[prefix] = value
        with cols[2]:
            if is_bead_sample(value):
                st.markdown("**bead**")

    bead_prefixes = [
        p for p, sample in st.session_state.prefix_sample_map.items() if is_bead_sample(sample)
    ]
    clone_prefixes = [p for p in prefixes if p not in bead_prefixes]

    suffixes = unique_suffixes(parsed_rows)
    clone_suffixes = sorted(
        {row.suffix for row in parsed_rows if row.prefix in clone_prefixes},
        key=int,
    )

    if clone_suffixes:
        st.subheader("Suffix → Antibody (clone rows)")
        for suffix in clone_suffixes:
            cols = st.columns([1, 2, 2])
            with cols[0]:
                st.text(suffix)
            with cols[1]:
                antibody = st.selectbox(
                    "Antibody",
                    options=[""] + CLONE_ANTIBODY_OPTIONS,
                    index=(
                        CLONE_ANTIBODY_OPTIONS.index(st.session_state.suffix_antibody_map[suffix]) + 1
                        if st.session_state.suffix_antibody_map.get(suffix) in CLONE_ANTIBODY_OPTIONS
                        else 0
                    ),
                    key=f"suffix_antibody_{suffix}",
                    label_visibility="collapsed",
                )
                st.session_state.suffix_antibody_map[suffix] = antibody
            with cols[2]:
                channel = get_channel(antibody) if antibody else ""
                st.text(channel or "—")

        with st.expander("Notes per suffix (optional)"):
            for suffix in clone_suffixes:
                notes = st.text_input(
                    f"Notes for suffix {suffix}",
                    value=st.session_state.suffix_notes_map.get(suffix, ""),
                    key=f"suffix_notes_{suffix}",
                )
                st.session_state.suffix_notes_map[suffix] = notes

    if bead_prefixes:
        st.subheader("Bead Settings")
        st.session_state.bead_base = st.text_input(
            "Bead base ID",
            value=st.session_state.bead_base,
            placeholder="e.g. 17847",
            help="Sample/CellLine will be generated as base/0, base/1, … per bead prefix group.",
        )

        st.markdown("**Bead prefix → Antibody**")
        for prefix in sorted(bead_prefixes):
            cols = st.columns([2, 2, 2])
            with cols[0]:
                st.text(prefix)
            with cols[1]:
                current = st.session_state.bead_prefix_antibody_map.get(prefix, "")
                antibody = st.selectbox(
                    "Antibody",
                    options=[""] + ANTIBODY_OPTIONS,
                    index=ANTIBODY_OPTIONS.index(current) + 1 if current in ANTIBODY_OPTIONS else 0,
                    key=f"bead_antibody_{prefix}",
                    label_visibility="collapsed",
                )
                st.session_state.bead_prefix_antibody_map[prefix] = antibody
            with cols[2]:
                channel = get_channel(antibody) if antibody else ""
                st.text(channel or "—")

    st.subheader("Preview & Export")
    config = ConversionConfig(
        prefix_sample_map=st.session_state.prefix_sample_map,
        suffix_antibody_map=st.session_state.suffix_antibody_map,
        bead_prefix_antibody_map=st.session_state.bead_prefix_antibody_map,
        bead_base=st.session_state.bead_base,
        suffix_notes_map=st.session_state.suffix_notes_map,
    )

    try:
        output_df, warnings = convert(parsed_rows, config)
        for warning in warnings:
            st.warning(warning)
        st.dataframe(output_df, use_container_width=True)

        csv_buffer = io.StringIO()
        output_df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Download Pl1_metadata.csv",
            data=csv_buffer.getvalue(),
            file_name="Pl1_metadata.csv",
            mime="text/csv",
        )
    except ValueError as exc:
        st.error("Complete all required mappings before export:")
        for line in str(exc).split("\n"):
            st.write(f"- {line}")


if __name__ == "__main__":
    main()
