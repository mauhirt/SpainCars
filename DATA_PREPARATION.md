# Data Preparation Instructions

Extracted from the `spain-zbe.zip` archive for the research paper:
**"Congestion Charging and Political Backlash: Low Emission Zones in Spain"**

---

## Overview

This project requires three main datasets to be downloaded, cleaned, and merged into analysis-ready panels for a regression discontinuity / difference-in-differences design around Spain's 50,000-population threshold for Low Emission Zones (ZBE).

The pipeline follows four stages: **Download** -> **Clean** -> **Merge** -> **Analysis**

All scripts are in `spain-zbe/src/` and are numbered to indicate execution order.

---

## Stage 1: Download Raw Data

### 1.1 INE Municipal Population (Script: `01_download_ine_population.py`)

**Purpose**: Official population figures from the Padrón Municipal. This is the **running variable** for the regression discontinuity at the 50,000 inhabitant threshold.

**Source**: INE — Cifras oficiales de población de los municipios españoles
- Portal: https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736177011
- API: https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/2852
- Table 2852: "Población por municipios y sexo"

**Years**: 2017–2025 (covers pre- and post-mandate periods)

**How to run**:
```bash
python spain-zbe/src/download/01_download_ine_population.py
```

**What the script does**:
1. Attempts to download Table 2852 from the INE JSON-stat API (`nult=10` for last 10 periods)
2. Saves raw JSON to `data/raw/ine_population/table_2852_raw.json`
3. Parses records extracting: INE 5-digit municipal code, municipality name, year, population
4. Builds a municipality-year panel with derived variables:
   - `cod_provincia`: first 2 digits of INE code
   - `above_50k`: boolean flag for the RD threshold
   - `pop_distance_50k`: population minus 50,000 (running variable)
5. Saves panel to `data/interim/ine_population_panel.csv`

**Manual fallback** (if API fails):
1. Go to https://www.ine.es/dynt3/inebase/index.htm?padre=517
2. Navigate to the desired year -> "Población por municipios y sexo"
3. Select all municipalities, "Total" for sex
4. Download as CSV/Excel
5. Save as `data/raw/ine_population/padron_{year}.csv`
6. Re-run the script with `--parse-only`

**Alternative**: PC-Axis files at `https://www.ine.es/jaxi/Tabla.htm?path=/t20/e260/a{year}/l0/&file=mun00.px`

---

### 1.2 DGT Vehicle Fleet (Script: `02_download_dgt_fleet.py`)

**Purpose**: Vehicle fleet data by environmental label (Zero, Eco, C, B, no-label) at the municipal level. This is the **primary outcome variable** — share of vehicles in each DGT environmental category.

**Source**: DGT (Dirección General de Tráfico) — "DGT en cifras"
- Portal: https://www.dgt.es/menusecundario/dgt-en-cifras/
- Interactive dashboard: "Panel de datos del parque de vehículos"
- Old PC-Axis portal: sedeapl.dgt.gob.es

**Years**: 2019–2024

**How to run**:
```bash
python spain-zbe/src/download/02_download_dgt_fleet.py
```

**What the script does**:
1. Scrapes DGT "cifras detalle" pages for Excel download links for each year (2019–2024)
2. Downloads annual statistical Excel workbooks to `data/raw/dgt_fleet/parque_vehiculos_{year}.xlsx`
3. Inspects sheet names and structure of each workbook
4. Attempts PC-Axis table download from the old portal as a fallback

**Data acquisition strategy** (from script documentation):

| Source | Level | Label Data? | Status |
|--------|-------|-------------|--------|
| Annual Excel workbooks | Province | Yes (2020+) | Useful but insufficient for municipal RD |
| Interactive dashboard | Municipal | Yes | Best source; may require manual export |
| PC-Axis tables | Municipal | No (type/fuel only) | Proxy via fuel type |
| Custom DGT request | Municipal | Yes | Most reliable; submit via datos.gob.es |
| MATRABA microdata | Province | Derivable from CO2/fuel | Flow (registrations) not stock |

**Recommended approach**:
1. Download annual Excel tables for province-level label data
2. Check interactive dashboard for municipal-level CSV/Excel export
3. File a custom data request to DGT for the municipal x label panel
4. Use MATRABA microdata for registration flow analysis
5. Use PC-Axis municipal x fuel data as a proxy if the custom request is slow

---

### 1.3 Election Results (Scripts: `03_download_elections.R` / `03_download_elections_py.py`)

**Purpose**: Municipal election results for measuring political backlash — specifically Vox and PP vote shares.

**Source**: Ministry of Interior (Ministerio del Interior)
- Portal: https://infoelectoral.interior.gob.es/
- R package: `infoelectoral` (ropenspain/infoelectoral on GitHub)
- SEA database: https://dataverse.harvard.edu/dataverse/SEA

**Elections of interest**:
- Municipal 2015 (baseline, pre-Vox)
- Municipal 2019 (Vox's breakthrough)
- Municipal 2023 (post-ZBE mandate — key test)
- General July 2023 (robustness check)

#### Option A: R (Preferred)

```bash
Rscript spain-zbe/src/download/03_download_elections.R
```

Requires: `install.packages("infoelectoral")`

**What the R script does**:
1. Uses `municipios()` from `infoelectoral` to download municipality-level results for municipal 2015, 2019, 2023
2. Downloads general election July 2023 municipality-level results
3. Saves raw CSVs to `data/raw/elections/municipal_{year}_municipios.csv`
4. Combines into a panel at `data/interim/elections_municipal_panel.csv`
5. Key columns: `codigo_provincia`, `codigo_municipio`, `nombre_municipio`, `siglas` (party abbreviation), `votos`

#### Option B: Python (Direct download)

```bash
python spain-zbe/src/download/03_download_elections_py.py
```

**What the Python script does**:
1. Downloads ZIP files from the Ministry of Interior's download area
2. URL pattern: `https://infoelectoral.interior.gob.es/estaticos/docxl/apliext/{TTMMYYYY}.zip`
   - TT: election type (`04` = municipal, `02` = Congress)
   - MM: month, YYYY: year
3. Saves to `data/raw/elections/{election_key}.zip`

**ZIP file contents** (fixed-width ASCII):
- `01{TTMMYYYY}.DAT` — Control file
- `02{TTMMYYYY}.DAT` — Candidacies (party code -> party name mapping)
- `03{TTMMYYYY}.DAT` — Candidates
- `04{TTMMYYYY}.DAT` — **Results by municipality and candidacy** (key file)
- `05{TTMMYYYY}.DAT` — Results by municipality (summary)
- `06{TTMMYYYY}.DAT` — Results by polling station

**Key fields in file 04** (fixed-width):
- Cols 1-2: Election type
- Cols 3-6: Year
- Cols 7-8: Month
- Cols 9-10: Province code
- Cols 11-13: Municipality code

**Alternative**: SEA database on Harvard Dataverse provides pre-parsed Excel workbooks.

---

### 1.4 Hacienda Municipal Fiscal Data (Script: `03b_download_hacienda_fiscal.py`)

**Purpose**: Municipal budget settlement data (liquidaciones presupuestarias) for testing whether fiscal structure predicts ZBE compliance.

**Source**: CONPREL — Ministerio de Hacienda
- Portal: https://serviciostelematicosext.hacienda.gob.es/SGFAL/CONPREL

**Years**: 2019–2023

**How to run**:
```bash
python spain-zbe/src/download/03b_download_hacienda_fiscal.py
```

**What the script does**:
1. Downloads annual ZIP files from CONPREL (each ~50 MB)
2. URL pattern: `DescargaFichero?CCAA=&TipoDato=Liquidaciones&Ejercicio={year}&TipoPublicacion=Access`
3. Saves to `data/raw/hacienda_fiscal/Liquidaciones{year}.zip`

**ZIP contents**: Access database (.accdb for 2022+, .mdb for 2019-2021) with tables:
- `tb_inventario`: entity registry (maps internal IDs to INE 5-digit municipal codes via `codente` field)
- `tb_economica`: revenue and expenditure by budget classification (`tipreig`=I for income, G for expenditure; `cdcta` = budget chapter code)
- `tb_remanente`: treasury remainder data

**Cleaning** (`05c_clean_hacienda_fiscal.py`): Extracts chapter-level aggregates for Ayuntamiento entities (suffix AA000), computes fiscal ratios.

**Merging** (`07b_merge_fiscal.py`): Averages 2019-2020 (pre-mandate baseline) and merges onto election panel by cod_ine.

---

## Stage 2: Clean Data

Scripts go in `spain-zbe/src/clean/` (currently empty — to be implemented).

**Key cleaning tasks**:
- Parse INE JSON into a consistent municipality-year panel
- Standardize INE 5-digit municipal codes across all datasets (2-digit province + 3-digit municipality, zero-padded)
- Compute DGT environmental label shares per municipality
- Compute Vox and PP vote shares per municipality (note: Vox did not run in 2015 municipal elections)
- Handle encoding (UTF-8 throughout; Spanish accents preserved)

---

## Stage 3: Merge Panel

Scripts go in `spain-zbe/src/merge/` (currently empty — to be implemented).

**Target panel structures**:
1. **Municipality-year panel** (for fleet outcomes): municipality code, year, population, above_50k flag, environmental label shares
2. **Municipality-election panel** (for voting outcomes): municipality code, election year, population, above_50k flag, Vox vote share, PP vote share, turnout

**Merge key**: INE 5-digit municipal code

---

## Stage 4: Analysis

Scripts go in `spain-zbe/src/analysis/` (currently empty — to be implemented).

**Research design**:
- **Regression Discontinuity**: Population threshold at 50,000 (fuzzy RD since compliance with ZBE varies)
- **Staggered Diff-in-Diff**: Exploits variation in actual ZBE implementation dates
- **Bandwidth**: Test sensitivity around 30k–70k range
- **Key outcomes**: (1) Share of no-label vehicles, (2) Vox vote share

---

## Coding Conventions

- Raw downloads in `data/raw/` — **never modified in place**
- Cleaned intermediates in `data/interim/`
- Analysis-ready panels in `data/processed/`
- Municipal identifiers: always INE 5-digit codes, zero-padded (e.g., "28079" = Madrid)
- Scripts numbered: `01_`, `02_`, etc.
- Each script runnable independently with `if __name__ == "__main__":` blocks
- Prefer explicit column names over positional indexing
- Log progress to stdout

## Dependencies

```
pip install -r spain-zbe/requirements.txt
```

Contents of `requirements.txt`:
- pandas
- requests
- openpyxl
- beautifulsoup4
- lxml
- statsmodels
- matplotlib
- seaborn

For R: `install.packages("infoelectoral")`
