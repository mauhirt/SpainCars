# Spain ZBE — Low Emission Zones and Political Backlash

Research project on the political economy of Spain's Low Emission Zone (ZBE) mandate.

## Quick Start with Claude Code

```bash
# 1. Clone / enter the project directory
cd spain-zbe

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Start Claude Code
claude

# 4. Ask Claude Code to run the download scripts:
#    "Run the INE population download script"
#    "Download the DGT fleet data"
#    "Set up the election data pipeline"
```

Claude Code reads `CLAUDE.md` automatically for project context.

## Project Structure

```
spain-zbe/
├── CLAUDE.md              # Project context for Claude Code
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── data/
│   ├── raw/               # Downloaded source files (never modify)
│   │   ├── ine_population/
│   │   ├── dgt_fleet/
│   │   └── elections/
│   ├── interim/           # Cleaned intermediates
│   └── processed/         # Analysis-ready panels
├── src/
│   ├── download/          # Data acquisition scripts
│   │   ├── 01_download_ine_population.py
│   │   ├── 02_download_dgt_fleet.py
│   │   ├── 03_download_elections.R
│   │   └── 03_download_elections_py.py
│   ├── clean/             # Parsing and harmonising
│   ├── merge/             # Building the municipal panel
│   └── analysis/          # RD, DiD, descriptives
├── output/
│   ├── figures/
│   └── tables/
└── paper/                 # LaTeX source
```

## Data Sources

| Source | Variable | Granularity | Format |
|--------|----------|-------------|--------|
| INE Padrón | Municipal population | Municipality × year | JSON API / Excel |
| DGT Parque | Vehicle fleet by env. label | Municipality × year | Excel / Dashboard |
| DGT MATRABA | New registrations | Province × month | Fixed-width text |
| Interior Ministry | Election results | Municipality × election | Fixed-width / R package |
| MITECO | ZBE implementation status | Municipality | Interactive map |

## Key Design

- **Regression Discontinuity** at the 50,000 population threshold
- **Staggered Diff-in-Diff** exploiting variation in ZBE implementation timing
- **Outcomes**: (1) vehicle fleet composition, (2) Vox/PP vote share
- **Reference**: Colantone et al. (2024, APSR) on Milan Area B and Lega voting
