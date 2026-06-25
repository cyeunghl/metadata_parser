"""Streamlit app for converting example metadata CSV to Pl1_metadata format."""

import io
from pathlib import Path

import pandas as pd
import streamlit as st

from antibody_config import ANTIBODY_OPTIONS, CLONE_ANTIBODY_OPTIONS, get_channel
from cell_lines import load_tracker_csv, suggest_tracker_id, tracker_label
from converter import ConversionConfig, convert
from parser import (
    is_bead_sample,
    parse_metadata,
    rows_to_dataframe,
    unique_prefixes,
    unique_suffixes,
)

DEFAULT_TRACKER_FILE = Path(__file__).parent / "20260625_Tracker - Sheet1.csv"
OTHER_OPTION = "__other__"
BEAD_OPTIONS = ["bead", "beads"]

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
    if "cell_line_tracker" not in st.session_state:
        st.session_state.cell_line_tracker = None
    if "last_tracker_name" not in st.session_state:
        st.session_state.last_tracker_name = None


def _apply_tracker_suggestions(prefixes: list[str], tracker_df: pd.DataFrame) -> None:
    for prefix in prefixes:
        if not st.session_state.prefix_sample_map.get(prefix, "").strip():
            suggested = suggest_tracker_id(prefix, tracker_df)
            if suggested:
                st.session_state.prefix_sample_map[prefix] = suggested


def _load_tracker(source, name: str, prefixes: list[str]) -> pd.DataFrame | None:
    try:
        tracker_df = load_tracker_csv(source)
    except ValueError as exc:
        st.error(str(exc))
        return st.session_state.cell_line_tracker

    st.session_state.cell_line_tracker = tracker_df
    st.session_state.last_tracker_name = name
    _apply_tracker_suggestions(prefixes, tracker_df)
    return tracker_df


def _ensure_default_tracker(prefixes: list[str]) -> pd.DataFrame | None:
    if st.session_state.cell_line_tracker is not None:
        return st.session_state.cell_line_tracker

    if DEFAULT_TRACKER_FILE.exists():
        return _load_tracker(DEFAULT_TRACKER_FILE, DEFAULT_TRACKER_FILE.name, prefixes)

    return None


def _render_cell_line_import(prefixes: list[str]) -> pd.DataFrame | None:
    st.subheader("Import Cell Lines")
    st.caption(
        "Tracker CSV with `TrackerCellLine` and `TrackerID` columns. "
        f"Defaults to `{DEFAULT_TRACKER_FILE.name}` when present."
    )

    _ensure_default_tracker(prefixes)

    tracker_file = st.file_uploader(
        "Upload a different cell line tracker CSV",
        type=["csv"],
        key="tracker_upload",
    )

    if tracker_file is not None and tracker_file.name != st.session_state.last_tracker_name:
        _load_tracker(tracker_file, tracker_file.name, prefixes)

    tracker_df = st.session_state.cell_line_tracker
    if tracker_df is not None:
        st.dataframe(tracker_df, use_container_width=True, hide_index=True)
        source = st.session_state.last_tracker_name or "tracker"
        st.write(f"**{len(tracker_df)}** cell lines loaded from `{source}`")
    else:
        st.info("No cell line tracker available. Prefix assignment will use freeform text only.")

    return tracker_df


def _tracker_select_label(option: str, tracker_df: pd.DataFrame, tracker_ids: set[str]) -> str:
    if option == "":
        return "—"
    if option == OTHER_OPTION:
        return "Other (freeform)"
    if option in tracker_ids:
        return tracker_label(option, tracker_df)
    return option


def _render_prefix_assignment(prefixes: list[str], tracker_df: pd.DataFrame | None) -> None:
    st.subheader("Prefix → Sample/CellLine")

    tracker_available = tracker_df is not None and not tracker_df.empty
    assignment_modes = ["Freeform text for all"]
    if tracker_available:
        assignment_modes.insert(0, "Tracker select")

    assignment_mode = st.radio(
        "Assignment mode",
        options=assignment_modes,
        horizontal=True,
        help="Tracker select: choose a TrackerID per prefix, or Other (freeform) for custom values. "
        "Freeform text for all: text input on every line.",
    )

    tracker_ids_list = tracker_df["TrackerID"].tolist() if tracker_available else []
    tracker_ids = set(tracker_ids_list)

    for prefix in prefixes:
        cols = st.columns([2, 3, 1])
        current = st.session_state.prefix_sample_map.get(prefix, "")

        with cols[0]:
            st.text(prefix)
        with cols[1]:
            if assignment_mode == "Tracker select" and tracker_available:
                select_options = [""] + tracker_ids_list + BEAD_OPTIONS + [OTHER_OPTION]

                if current in tracker_ids or current in BEAD_OPTIONS:
                    select_index = select_options.index(current)
                elif current:
                    select_index = select_options.index(OTHER_OPTION)
                else:
                    select_index = 0

                selected = st.selectbox(
                    "Sample/CellLine",
                    options=select_options,
                    index=select_index,
                    format_func=lambda option: _tracker_select_label(option, tracker_df, tracker_ids),
                    key=f"prefix_tracker_{prefix}",
                    label_visibility="collapsed",
                )

                if selected == OTHER_OPTION:
                    value = st.text_input(
                        "Other value",
                        value=current if current not in select_options else "",
                        key=f"prefix_other_{prefix}",
                        label_visibility="collapsed",
                        placeholder="Custom Sample/CellLine",
                    )
                else:
                    value = selected
            else:
                value = st.text_input(
                    "Sample/CellLine",
                    value=current,
                    key=f"prefix_sample_{prefix}",
                    label_visibility="collapsed",
                    placeholder="TrackerID, sample name, or bead/beads",
                )

            st.session_state.prefix_sample_map[prefix] = value
        with cols[2]:
            if is_bead_sample(value):
                st.markdown("**bead**")
            elif tracker_available and value in tracker_ids:
                st.markdown("**tracker**")


def main() -> None:
    st.set_page_config(page_title="Metadata Converter", layout="wide")
    st.title("Metadata Converter")
    st.caption("Convert example metadata CSV into Pl1_metadata format.")

    uploaded = st.file_uploader("Upload source metadata CSV", type=["csv"])
    if uploaded is None:
        st.info("Upload a source metadata CSV to begin.")
        return

    parsed_rows = parse_metadata(uploaded)
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

    prefixes = unique_prefixes(parsed_rows)
    tracker_df = _render_cell_line_import(prefixes)
    _render_prefix_assignment(prefixes, tracker_df)

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

    output_df, warnings = convert(parsed_rows, config)
    if warnings:
        st.warning("Some mappings are incomplete:")
        for warning in warnings:
            st.write(f"- {warning}")
    st.dataframe(output_df, use_container_width=True)

    csv_buffer = io.StringIO()
    output_df.to_csv(csv_buffer, index=False)
    st.download_button(
        label="Download Pl1_metadata.csv",
        data=csv_buffer.getvalue(),
        file_name="Pl1_metadata.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
