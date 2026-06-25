# SOP: Metadata Parser (Streamlit)

## Purpose

Convert a source metadata CSV (FCS filenames from the cytometer export) into `Pl1_metadata.csv` with columns: `FCSFile`, `Sample/CellLine`, `Antibody`, `Channel`, `Notes`, `WellID`.

---

## Before You Start

**Input file requirements**

- CSV with `.fcs` filenames in the first column
- Filenames follow the pattern: `{prefix}{YYYY-MM-DD}.{number}.fcs`  
  Example: `Clone12026-06-02.0001.fcs`

**What you need ready**

- Sample/CellLine names for each clone prefix (e.g. `Clone1` → `KPL4_e38_e1_e1_b1_P2`)
- Antibody assignments for each suffix used by clone rows (e.g. `0001` → HER2)
- Bead base ID if bead samples are present (e.g. `17847`)
- Antibody per bead prefix (e.g. `HER2 Beads` → HER2)

---

## Step 1: Launch the App

```bash
cd /path/to/metadataParser
pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser.

---

## Step 2: Load Your Source File

1. Click **Upload source metadata CSV** and select your file, **or**
2. Leave **Use bundled example file** checked to load the example.

**Check the Parse Preview table.** You should see each FCS file split into:

- `prefix` — text before the date (e.g. `Clone1`, `HER2 Beads`)
- `date` — delimiter (e.g. `2026-06-02`)
- `suffix` — number after the date (e.g. `0001`)

If no rows appear, confirm filenames match the expected pattern.

---

## Step 3: Map Prefixes → Sample/CellLine

For every unique **prefix**, enter a Sample/CellLine value.

### Cell line / clone samples

Enter the full sample name:

- `Clone1` → `KPL4_e38_e1_e1_b1_P2`
- `Clone2` → `KPL4_e38_e1_e2_b1_P2`

### Bead samples

Type **`bead`** or **`beads`** (any case). A **bead** badge appears next to that prefix.

Examples:

- `HER2 Beads` → `beads`
- `B1` → `bead`
- `TROP2 Beads` → `beads`

**Note:** `bead`/`beads` is a classification label only. The final output uses `{base}/0`, `{base}/1`, etc. (see Step 5).

---

## Step 4: Map Suffixes → Antibody (Clone Rows Only)

For clone prefixes, assign an antibody to each **suffix** (e.g. `0001`, `0002`, …).

| Suffix | Typical antibody | Channel (auto) |
|--------|------------------|----------------|
| 0001   | HER2             | APC            |
| 0002   | TROP2            | PE             |
| 0003   | ABCB1            | PE             |
| 0004   | ABCG2            | PE             |
| 0005   | HB-44976         | APC, PE        |

Clone rows also support **cMET** → FITC.

Channel fills in automatically. Optionally add **Notes** per suffix (e.g. `unstained control` for suffix `0005`).

---

## Step 5: Configure Bead Settings (If Applicable)

If any prefix is marked as bead, a **Bead Settings** section appears.

1. **Bead base ID** — enter the base identifier (e.g. `17847`).
2. **Bead prefix → Antibody** — assign one antibody per bead prefix:

| Bead prefix   | Example antibody |
|---------------|------------------|
| HER2 Beads    | HER2             |
| TROP2 Beads   | TROP2            |
| B1            | ABCB1            |
| G2            | ABCG2            |

**How bead Sample/CellLine is generated**

- Within each bead prefix group, rows are sorted by suffix (`.0001`, `.0002`, …).
- Output becomes: `17847/0`, `17847/1`, `17847/2`, …

---

## Step 6: Preview and Export

1. Scroll to **Preview & Export**.
2. Review the output table.
3. Fix any red error messages (missing mappings).
4. Click **Download Pl1_metadata.csv**.

**Output behavior**

- Clone rows appear first, then bead rows.
- **WellID** is assigned sequentially: `A1`, `A2`, `A3`, … through the 96-well plate.
- A warning appears if there are more than 96 rows.

---

## Quick Reference: Clone vs Bead Logic

| | Clone / cell line | Bead |
|---|---|---|
| **How identified** | Any prefix value except `bead`/`beads` | Prefix mapped to `bead` or `beads` |
| **Sample/CellLine** | Your entered text | `{bead_base}/{index}` |
| **Antibody** | By suffix (shared across clones) | By bead prefix |
| **Channel** | Auto from antibody | Auto from antibody |
| **Notes** | Optional per suffix | Blank |

---

## Troubleshooting

| Issue | Action |
|-------|--------|
| "No valid .fcs filenames found" | Check that filenames end in `.fcs` and include a date like `2026-06-02` |
| "Missing Sample/CellLine mapping for prefix" | Fill in every prefix in Step 3 |
| "Missing Antibody mapping for suffix" | Complete all suffix dropdowns for clone rows |
| "Missing Antibody mapping for bead prefix" | Assign antibody for each bead prefix |
| "Bead base ID is required" | Enter a bead base when bead prefixes exist |
| Wrong antibody on bead rows | Beads use per-prefix antibody, not suffix mapping |

---

## Example Workflow (Pl1 dataset)

1. Upload `exampleMetadata - Sheet1.csv`
2. Map `Clone1`–`Clone12` to their `KPL4_…` sample names
3. Map `B1`, `G2`, `HER2 Beads`, `TROP2 Beads` → `beads`
4. Map suffixes `0001`–`0005` to HER2, TROP2, ABCB1, ABCG2, HB-44976
5. Set bead base to `17847`
6. Map bead antibodies: HER2 Beads→HER2, TROP2 Beads→TROP2, B1→ABCB1, G2→ABCG2
7. Add note `unstained control` for suffix `0005` (optional)
8. Download `Pl1_metadata.csv`
