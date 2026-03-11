#!/usr/bin/env Rscript
#
# 03_download_elections.R
#
# Download Spanish municipal election results using the infoelectoral
# R package (ropenspain/infoelectoral).
#
# Elections of interest:
#   - Municipal 2015 (baseline, pre-Vox)
#   - Municipal 2019 (Vox's breakthrough election)
#   - Municipal 2023 (post-ZBE mandate, key test)
#   - General July 2023 (for robustness)
#
# Source: Ministry of Interior (Ministerio del Interior)
#         https://infoelectoral.interior.gob.es/
#
# Usage:
#   Rscript src/download/03_download_elections.R
#
# Requires:
#   install.packages("infoelectoral")
#   # or: devtools::install_github("ropenspain/infoelectoral")

library(infoelectoral)

# Output directories
raw_dir <- file.path("data", "raw", "elections")
interim_dir <- file.path("data", "interim")
dir.create(raw_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(interim_dir, recursive = TRUE, showWarnings = FALSE)

cat("=======================================================\n")
cat("Spanish Election Results — Download via infoelectoral\n")
cat("=======================================================\n\n")

# ------------------------------------------------------------------
# 1. Municipal elections at the municipality level
# ------------------------------------------------------------------

municipal_years <- c("2015", "2019", "2023")

for (yr in municipal_years) {
  cat(sprintf("Downloading municipal election %s...\n", yr))

  tryCatch({
    # municipios() downloads municipality-level results
    # tipo = "municipales" for municipal elections
    df <- municipios(
      tipo_eleccion = "municipales",
      anno = yr
    )

    # Save raw
    output_path <- file.path(raw_dir, sprintf("municipal_%s_municipios.csv", yr))
    write.csv(df, output_path, row.names = FALSE, fileEncoding = "UTF-8")
    cat(sprintf("  Saved %d rows to %s\n", nrow(df), output_path))

    # Quick summary
    cat(sprintf("  Columns: %s\n", paste(names(df), collapse = ", ")))
    cat(sprintf("  Unique municipalities: %d\n", length(unique(df$codigo_municipio))))

  }, error = function(e) {
    cat(sprintf("  ERROR: %s\n", conditionMessage(e)))
    cat("  Try downloading manually from infoelectoral.interior.gob.es\n")
  })

  cat("\n")
  Sys.sleep(2)  # be polite
}

# ------------------------------------------------------------------
# 2. General election July 2023 at municipality level (robustness)
# ------------------------------------------------------------------

cat("Downloading general election July 2023...\n")

tryCatch({
  df_general <- municipios(
    tipo_eleccion = "congreso",
    anno = "2023"
  )

  output_path <- file.path(raw_dir, "general_2023_municipios.csv")
  write.csv(df_general, output_path, row.names = FALSE, fileEncoding = "UTF-8")
  cat(sprintf("  Saved %d rows to %s\n", nrow(df_general), output_path))

}, error = function(e) {
  cat(sprintf("  ERROR: %s\n", conditionMessage(e)))
})

# ------------------------------------------------------------------
# 3. Build a simple panel of Vox and PP vote shares
# ------------------------------------------------------------------

cat("\n--- Building Vox/PP vote share panel ---\n\n")

all_elections <- data.frame()

for (yr in municipal_years) {
  fpath <- file.path(raw_dir, sprintf("municipal_%s_municipios.csv", yr))

  if (!file.exists(fpath)) {
    cat(sprintf("  Skipping %s (file not found)\n", yr))
    next
  }

  df <- read.csv(fpath, fileEncoding = "UTF-8", stringsAsFactors = FALSE)

  # The infoelectoral package returns columns like:
  #   codigo_provincia, codigo_municipio, nombre_municipio,
  #   siglas (party abbreviation), votos, ...
  #
  # Column names may vary; inspect and adapt
  cat(sprintf("  %s columns: %s\n", yr, paste(head(names(df), 10), collapse = ", ")))

  df$election_year <- as.integer(yr)
  all_elections <- rbind(all_elections, df)
}

if (nrow(all_elections) > 0) {
  output_path <- file.path(interim_dir, "elections_municipal_panel.csv")
  write.csv(all_elections, output_path, row.names = FALSE, fileEncoding = "UTF-8")
  cat(sprintf("\n  Combined panel: %d rows saved to %s\n", nrow(all_elections), output_path))
}

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------

cat("\n=======================================================\n")
cat("Summary:\n")
cat(sprintf("  Files in %s:\n", raw_dir))
for (f in list.files(raw_dir)) {
  cat(sprintf("    %s\n", f))
}
cat("\nNext steps:\n")
cat("  1. Inspect column names and party codes (siglas)\n")
cat("  2. Compute Vox and PP vote shares by municipality\n")
cat("  3. Note: Vox did not run in 2015 municipal elections\n")
cat("     (founded 2013, first breakthrough in April 2019)\n")
cat("  4. Merge with INE population panel on municipal codes\n")
cat("=======================================================\n")
