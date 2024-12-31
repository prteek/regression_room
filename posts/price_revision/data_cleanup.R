# %%
suppressPackageStartupMessages(library(tidyverse))
library(knitr)
library(patchwork)
library(this.path)
setwd(here())
# %%
listings <- read_csv("listings.csv", show_col_types = F)
revisions <- read_csv("revisions.csv", show_col_types = F)

analysis_start_date <- as.Date("2021-01-01")
analysis_end_date <- as.Date("2022-06-01")
listings <- listings %>% filter(between(listing_date, analysis_start_date, analysis_end_date))
revisions <- revisions %>% filter(between(price_revision_date, analysis_start_date, analysis_end_date))

# %%
