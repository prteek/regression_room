# F1 Laptime Modelling - Analysis Plan

## Introduction

This analysis develops a predictive model for F1 race dynamics, specifically focusing on how multiple factors influence individual lap times and ultimately determine finishing position in a race. The key questions this analysis will answer are:

- How do pit stops, fuel quantity, tyre type and age affect lap times during a race?
- How do team and track-specific effects influence performance variability?
- Can we predict the final race position based on these mechanical and operational factors?

The analysis builds on existing work in F1 analytics and provides a framework for understanding race dynamics beyond raw driver skill.

## Data

**Sources:**
- fastf1 Python library - provides comprehensive race telemetry data (saved at @posts/f1_laptimes/data/season_race.csv)
- 2025 F1 season races (dry conditions only)

**Variables:**
- Lap times (raw race lap data)
- Pit stop duration and timing
- Track status information (safety cars, weather conditions)
- Tyre type and estimated tyre age
- Fuel load estimates (derived from lap number as proxy)
- Driver and team identifiers

**Data Characteristics:**
- Time series structure: multiple laps per driver per race
- Nested structure: laps within races, drivers within teams
- Multiple races across the 2025 season providing cross-race validation

## Key Assumptions

1. **Driver Consistency:** Driver performance remains relatively consistent throughout the 2025 season (no major form changes)
2. **Team Car Parity:** Variability between cars of the same team is negligible
3. **Laptime Determinants:** Laptime is primarily a function of:
   - Fuel quantity (approximated by lap number)
   - Tyre type (hard/medium/soft compound)
   - Tyre age (estimated laps since tyre change)
4. **Track Effects:** Performance varies meaningfully between tracks
5. **Dry Conditions:** Analysis focuses on dry weather races only

## Scope

**Included:**
- Race laps only (not qualifying)
- 2025 season races in dry conditions
- Team-level performance variability
- Track-specific variability
- Predictive modeling for end-of-race position

**Excluded:**
- Wet weather races
- Qualifying sessions
- Detailed driver-to-driver comparisons
- Track position/overtaking dynamics (focus on mechanical factors)
- Individual driver performance differences beyond team effects

**Output:**
A predictive model capable of estimating final race position based on race dynamics observed up to a given point or based on expected pit strategy and tyre management.

---

## Instructions for Implementation

This analysis should be carried out in the `index.qmd` file using Quarto markdown format. The following workflow is recommended:

1. **Data Acquisition & Exploration**
   - Load race data from fastf1 for 2025 season dry races
   - Explore lap time distributions, pit stop patterns, and tyre strategies
   - Visualize relationships between fuel load, tyre age, and lap times

2. **Feature Engineering**
   - Create tyre age variable (laps since change)
   - Generate fuel load proxy from lap number
   - Extract pit stop information and timing
   - Identify track status events and their impact

3. **Exploratory Analysis**
   - Examine lap time trends within races
   - Compare performance across teams and tracks
   - Assess variability of key predictors

4. **Model Development**
   - Fit mixed-effects models accounting for nested structure (laps within races, drivers within teams)
   - Include fixed effects for tyre type, tyre age, fuel quantity, and track
   - Include random effects for drivers and teams
   - Evaluate model fit and assumptions

5. **Prediction & Validation**
   - Demonstrate predictive capability for race position
   - Cross-validate across races
   - Interpret model coefficients in context of F1 dynamics

6. **Visualizations & Summary**
   - Create plots showing laptime vs. tyre age, fuel quantity, tyre type
   - Visualize team and track effects
   - Summary table of model results and key findings

Reference: https://vu-business-analytics.github.io/internship-office/papers/paper-sulsters.pdf
