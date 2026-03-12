# CLAUDE.md

## Project Overview

Research paper: **"Congestion Charging and Political Backlash: Low Emission Zones in Spain"**

This project studies how Spain's 2021 Climate Change Law (Ley 7/2021) mandate
requiring municipalities with >50,000 inhabitants to establish Low Emission Zones
(Zonas de Bajas Emisiones, ZBE) affected:
1. Vehicle fleet composition (shift toward cleaner vehicles)
2. Electoral support for the populist right (Vox) and PP

The population threshold at 50k creates a regression discontinuity. The staggered
and politically heterogeneous rollout creates additional variation for diff-in-diff.

Key reference: Colantone et al. (2024, APSR) on Milan's Area B and Lega voting.

## Data Sources

### 1. DGT — Vehicle Fleet (Parque de Vehículos)
- **What**: Stock of vehicles by municipality, type, fuel, environmental label
- **Portal**: https://www.dgt.es/menusecundario/dgt-en-cifras/
- **Key variable**: Distribution across DGT environmental labels (Zero, Eco, C, B, no-label)
- **Granularity**: Municipality-year (annual snapshots)
- **Format**: Excel files from "DGT en cifras" or PC-Axis tables from the old statistical portal
- **Interactive dashboard**: Panel de datos del parque de vehículos (national to municipal)

### 2. DGT — New Registrations (Matriculaciones)
- **What**: Monthly/daily microdata of newly registered vehicles
- **Portal**: Same as above, under "Microdatos" category
- **Key fields**: Registration date, province code, vehicle type, fuel, CO2 emissions, electric category
- **Note**: Microdata files use the MATRABA format. Province is coded; confirm whether municipality code is included.
- **Format**: Fixed-width text files (design doc at sedeapl.dgt.gob.es)

### 3. INE — Municipal Population (Padrón Municipal)
- **What**: Official population figures for every Spanish municipality, as of 1 January each year
- **Portal**: https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736177011&menu=resultados&idp=1254734710990
- **Also**: INE API (JSON-stat) at https://servicios.ine.es/wstempus/js/
- **Key use**: Running variable for the RD at 50k threshold; identify treated municipalities
- **Identifiers**: INE 5-digit municipal code (2-digit province + 3-digit municipality)
- **Series**: Available from 1996 onward

### 4. Ministry of Interior — Election Results
- **What**: Municipal election results (2015, 2019, 2023), general election results
- **Portal**: https://infoelectoral.interior.gob.es/en/elecciones-celebradas/resultados-electorales/
- **R package**: `infoelectoral` (ropenspain/infoelectoral on GitHub)
- **Also**: SEA database (Spanish Electoral Archive), published in Scientific Data (2021)
- **Key variables**: Vox vote share, PP vote share, turnout, by municipality
- **Granularity**: Down to ballot-box (mesa) level; municipality level is sufficient

### 5. Ministerio de Hacienda — Municipal Fiscal Data (Liquidaciones)
- **What**: Annual budget settlements (liquidaciones presupuestarias) for all municipalities
- **Portal**: CONPREL at https://serviciostelematicosext.hacienda.gob.es/SGFAL/CONPREL
- **Format**: ZIP files containing Access databases (.accdb for 2022+, .mdb for earlier years)
- **Key tables**: tb_economica (revenue/expenditure by budget chapter), tb_inventario (entity registry)
- **Key variables**: own revenue (ch.1-3), transfers from Estado/CCAA/EU (ch.4+7 sub-chapters), debt service (ch.3 expense), capital spending (ch.6 expense)
- **Matching**: Entity code starts with INE 5-digit municipal code; filter to Ayuntamiento entities (suffix AA000)
- **Years available**: 2002-2024 (we use 2019-2023)
- **Scripts**: `03b_download_hacienda_fiscal.py` → `05c_clean_hacienda_fiscal.py` → `07b_merge_fiscal.py` → `12b_fiscal_zbe_adoption.py`

### 6. BDNS — Next Generation EU ZBE Fund Allocations
- **What**: Municipality-level NGEU fund allocations for ZBE implementation and sustainable urban transport
- **Portal**: BDNS (Base de Datos Nacional de Subvenciones) API at https://www.pap.hacienda.gob.es/bdnstrans/api/
- **Program**: "Ayudas a municipios para la implantación de ZBE y la transformación digital y sostenible del transporte urbano"
- **Convocatorias**: 2021 (BDNS 576282, EUR 1.16bn, 169 grants) + 2022 (BDNS 640563, EUR 485m, 109 grants)
- **Key variables**: total_eu_funds, eu_funds_2021, eu_funds_2022, eu_funds_pc (per capita)
- **Matching**: Beneficiary CIF Pddmmmcc → INE code dd+mmm (5-digit zero-padded)
- **Coverage**: 187 unique municipalities, 73/148 (49%) of >50k municipalities
- **Scripts**: `03c_download_mitma_zbe_funds.py` → `05d_clean_mitma_zbe_funds.py` → `07c_merge_eu_funds.py` → `12b_fiscal_zbe_adoption.py`

### 7. MITECO — ZBE Implementation Status
- **What**: Interactive map classifying obligated municipalities as vigente/en trámite/pendiente
- **Portal**: https://www.miteco.gob.es/en/calidad-y-evaluacion-ambiental/temas/movilidad/zonas_de_bajas_emisiones_en_espana.html
- **Note**: No time-series archive. May need to hand-code implementation dates from
  municipal ordinances (BOE/BOP), Wayback Machine snapshots, and news sources.
- **Status as of Jan 2026**: 58 vigentes, 91 en trámite, ~20 pendientes

## Languages & Tools

- **Python** (primary): pandas, requests, openpyxl, statsmodels, rdrobust, matplotlib, seaborn
- **R** (for election data): infoelectoral package, rdrobust
- **LaTeX**: Paper drafting (Overleaf sync via Git)

## Coding Conventions

- All raw downloads go in `data/raw/` and are NEVER modified in place
- Cleaned intermediates go in `data/interim/`
- Analysis-ready panels go in `data/processed/`
- Municipal identifiers always use INE 5-digit codes (CPRO 2-digit + CMUN 3-digit)
- Panel structure: municipality-year for fleet; municipality-election for voting
- UTF-8 throughout; Spanish accents in variable labels/values are fine
- Scripts are numbered: `01_download_ine.py`, `02_download_dgt.py`, etc.
- Each script in `src/download/` should be runnable independently
- Use `if __name__ == "__main__":` blocks
- Prefer explicit column names over positional indexing
- Log progress to stdout when downloading

## Key Identifiers

- **INE municipal code**: 5-digit string, zero-padded (e.g., "28079" = Madrid)
- **Province code**: First 2 digits of the municipal code
- **DGT environmental labels**: CERO (Zero), ECO, C, B, SIN DISTINTIVO (no label / A)

## Research Design Notes

- **RD**: Population threshold at 50,000 (Padrón Municipal, as of 1 Jan of relevant year)
- **Treatment**: Obligation to implement ZBE (above 50k) — fuzzy RD since compliance varies
- **Staggered DiD**: Exploit variation in actual implementation dates across municipalities
- **Key outcomes**: (1) Share of no-label vehicles in municipal fleet; (2) Vox vote share
- **Key elections**: Municipal 2019 (pre-mandate), Municipal 2023 (post-mandate)
- **Potential confounders**: Other policy discontinuities at 50k threshold (check)
- **Bandwidth**: Test sensitivity around 30k–70k range
