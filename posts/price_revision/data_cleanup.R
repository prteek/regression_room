# %%
suppressPackageStartupMessages(library(tidyverse))
library(knitr)
library(patchwork)
library(this.path)
setwd(here())
options(width = 200)

# %%

min_data_date <- as.Date("2021-01-01")
listings <- read_csv("listings.csv", show_col_types = F) %>%
    # remove periods of COVID which may have caused market movement that are not representative of normal conditions, max date < Mini budget
    filter(listing_date >= min_data_date) %>%
    mutate(location = if_else(location == "Newcastle upon Tyne", "Newcastle Upon Tyne", location)) %>%
    # remove bathroom_count from analysis as it has quite a lot of missing values and does not seem very valuable piece of info
    select(-bathroom_count) %>%
    # remove 0 and 1 bed houses (likely errors), flats with > 2 beds (very few 3 beds exist) and restrict to 5 beds overall since those may be asset classes of interest
    filter((property_type == "flat" & between(bedroom_count, 0, 2)) | (property_type == "house" & between(bedroom_count, 2, 5))) %>%
    # sensible max price
    filter((bedroom_count == 0 & asking_price < 300000) | (asking_price <= 1000000 & between(bedroom_count, 1, 4)) | (asking_price <= 1500000 & bedroom_count == 5))

# This is a smaller subset of listings
revisions <- read_csv("revisions.csv", show_col_types = F)

summary(listings)

# %%
# Check distribution of prices
for (bed in unique(sort(listings$bedroom_count))) {
    p <- ggplot(listings %>% filter(bedroom_count == bed)) +
        geom_histogram(aes(x = asking_price, y = after_stat(count / max(count)), fill = property_type), alpha = 0.8, position = "dodge") +
        ggtitle(paste("Beds: ", bed))
    print(p)
}

# %%
# Check for duplicates
listings %>%
    group_by(listing_id) %>%
    summarise(counts = n()) %>%
    arrange(desc(counts))

# %%
# Filter revisions using sensible listings

listings_with_revisions <- inner_join(listings, revisions, by = "listing_id") %>%
    # Logically remove revisions occuring before listing date. Could be related to previous sale
    filter(revision_date >= listing_date) %>%
    # sensible max price
    filter(revised_asking_price >= 100000) %>%
    filter((bedroom_count == 0 & revised_asking_price < 300000) | (revised_asking_price <= 1000000 & between(bedroom_count, 1, 4)) | (revised_asking_price <= 1500000 & bedroom_count == 5)) %>%
    # remove instances where listings may be inactive for long promting at a possible recycling of existing listing
    filter((revision_date - listing_date) <= 270)

# Check distribution of revised prices
for (bed in unique(sort(listings_with_revisions$bedroom_count))) {
    p <- ggplot(listings_with_revisions %>% filter(bedroom_count == bed)) +
        geom_histogram(aes(x = revised_asking_price, y = after_stat(count / max(count)), fill = property_type), alpha = 0.7, position = "dodge") +
        ggtitle(paste("Beds: ", bed))
    print(p)
}

# %%
frequently_revised <- listings_with_revisions %>%
    arrange(listing_id, revision_date) %>%
    group_by(listing_id) %>%
    mutate(price_change = revised_asking_price != lag(revised_asking_price, default = first(revised_asking_price))) %>%
    summarise(
        all_revisions = n(), price_levels = n_distinct(revised_asking_price),
        price_revisions = sum(price_change, na.rm = TRUE)
    ) %>%
    filter(price_revisions <= price_levels)

suspect_id = 15578098
suspected_revisions <- listings_with_revisions %>% filter(listing_id == suspect_id)
# print(suspected_revisions)
ggplot(suspected_revisions) +
    geom_line(aes(x = revision_date, y = revised_asking_price))

# %%
filtered_listings_with_revisions <- listings_with_revisions %>%
    filter(listing_id %in% frequently_revised$listing_id)

# Check if siginificant rows have been dropped from revisions
nrow(revisions)
nrow(listings_with_revisions)
nrow(filtered_listings_with_revisions)

# Check if significant number of listitngs were affected
length(revisions %>% pull(listing_id) %>% unique())
length(listings_with_revisions %>% pull(listing_id) %>% unique())
length(filtered_listings_with_revisions %>% pull(listing_id) %>% unique())

# Since there aren't significant number of listings affected the results of filtering are acceptable

# %%
start_and_end_revisions <- filtered_listings_with_revisions %>%
    arrange(listing_id, revision_date, desc(revised_asking_price)) %>%
    group_by(listing_id) %>%
    summarise(
        first_price = first(asking_price),
        last_price = last(revised_asking_price),
        max_revision_date = last(revision_date),
        listing_date = first(revision_date),
    ) %>%
    mutate(active_days = max_revision_date - listing_date) %>%
    # Keep sensible changes. Large changes may be due to reasons that make properties not interesting for our application (e.g. damage/long onward-chain)
    filter(between(last_price / first_price, 0.7, 1.3))

terminal_revisions <- inner_join(filtered_listings_with_revisions, start_and_end_revisions %>% select(-listing_date), by = c("listing_id" = "listing_id", "revision_date" = "max_revision_date", "revised_asking_price" = "last_price")) %>%
    select(names(filtered_listings_with_revisions)) %>%
    # Add binary indicator for >= 5% reduction
    mutate(is_5percent_reduced = if_else(revised_asking_price / asking_price <= 0.95, "yes", "no"))

# %%
write.csv(terminal_revisions %>% select(-revised_asking_price),
    "terminal_revisions.csv",
    row.names = F
)

# %%

plot(terminal_revisions$asking_price, terminal_revisions$revised_asking_price)
abline(0, 1.3, lty = 1)
abline(0, 1, lty = 1)
abline(0, 0.95, lty = 2)
abline(0, 0.7, lty = 1)

plot(ecdf(terminal_revisions$revised_asking_price / terminal_revisions$asking_price), main = "% price change ECDF", xlab = "% price change")

# %%
