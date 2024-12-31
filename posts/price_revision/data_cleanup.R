# %%
suppressPackageStartupMessages(library(tidyverse))
library(knitr)
library(patchwork)
library(this.path)
setwd(here())
# %%
# We remove periods of COVID which may have caused market movement that are not representative of normal conditions
min_data_date <- as.Date("2021-01-01")
listings <- read_csv("listings.csv", show_col_types = F) %>%
    filter(listing_date >= min_data_date)
revisions <- read_csv("revisions.csv", show_col_types = F) %>%
    filter(revision_date >= min_data_date)


# %%
