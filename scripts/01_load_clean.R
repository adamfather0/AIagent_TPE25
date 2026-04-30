# scripts/01_load_clean.R
# Load and clean 2025 TPE tomato biochar pot experiment data.
# Reads data/2025TPE_raw.xlsx (sheet "summary"), normalizes column names,
# coerces numerics, sets factor levels, and writes data/tpe25.rds.

suppressPackageStartupMessages({
  library(readxl)
  library(dplyr)
  library(tibble)
  library(stringr)
})

set.seed(2025)

raw_path <- "data/2025TPE_raw.xlsx"
out_path <- "data/tpe25.rds"

# Row 1 = column names, row 2 = units, data starts row 3.
# Read names from row 1; read data starting from row 3 with those names.
header <- as.character(unlist(read_excel(raw_path, sheet = "summary",
                                         n_max = 1, col_names = FALSE)))
units_row <- as.character(unlist(read_excel(raw_path, sheet = "summary",
                                            skip = 1, n_max = 1,
                                            col_names = FALSE)))
df <- read_excel(raw_path, sheet = "summary", skip = 2, col_names = FALSE,
                 na = c("", "NA", "#VALUE!", "#DIV/0!", "#N/A"))

# Normalize header: trim spaces, replace problematic chars, drop trailing "*".
clean_name <- function(x) {
  x <- str_trim(x)
  x <- str_replace_all(x, "\\*$", "")
  x <- str_replace_all(x, "/", "_")
  x <- str_replace_all(x, "\\s+", "_")
  x
}
names(df) <- clean_name(header)

# Sanity check: expected 42 columns.
stopifnot(ncol(df) == length(header))

# Coerce numerics for all measurement columns.
id_cols <- c("Treatment", "Rep", "Soil", "Biochar", "Fertilizer")
num_cols <- setdiff(names(df), id_cols)
df <- df %>%
  mutate(across(all_of(num_cols), ~ suppressWarnings(as.numeric(.x))))

# Factor levels per CLAUDE.md.
df <- df %>%
  mutate(
    Treatment  = factor(str_trim(Treatment),
                        levels = paste0("T", 1:8)),
    Rep        = factor(as.integer(Rep), levels = 1:4),
    Soil       = factor(Soil,       levels = c("Red_soil", "Alluvial_soil")),
    Biochar    = factor(Biochar,    levels = c("NO", "Rice_husk", "Leucaena")),
    Fertilizer = factor(Fertilizer, levels = c("NO", "YES"))
  )

# Quick integrity report.
cat("Rows:", nrow(df), " Cols:", ncol(df), "\n")
cat("Treatment x Rep counts (should be 4 reps for each of 8 treatments):\n")
print(addmargins(table(df$Treatment, df$Rep)))
cat("\nNA counts (top 15 columns by missingness):\n")
na_summary <- sort(colSums(is.na(df)), decreasing = TRUE)
print(head(na_summary, 15))

# Persist a units lookup alongside the cleaned data.
units <- tibble(column = names(df), unit = units_row) %>%
  mutate(unit = if_else(column %in% id_cols, NA_character_, unit))

saveRDS(list(data = df, units = units), out_path)
cat("\nWrote", out_path, "\n")
