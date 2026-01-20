# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Quarto-based data science blog hosted at https://prteek.github.io/regression_room/. Posts are written in `.qmd` files combining R/Python code with narrative, rendered to static HTML in `docs/` for GitHub Pages hosting.

## Commands

**Render entire site:**
```bash
quarto render
```

**Render single post:**
```bash
quarto render posts/<post-name>/index.qmd
```

**Preview with live reload:**
```bash
quarto preview
```

## Architecture

- `_quarto.yml` - Site configuration (output to `docs/`, Cosmo theme)
- `posts/_metadata.yml` - Default post settings (`freeze: true` caches execution)
- `posts/<name>/index.qmd` - Individual blog posts with YAML frontmatter
- `docs/` - Generated HTML output (do not edit directly)
- `_freeze/` - Cached code execution results

## Post Structure

Each post in `posts/` contains:
- `index.qmd` - Main document with YAML frontmatter (title, date, categories, bibliography)
- `references.bib` - Citations (optional)
- `data/` - Supporting data files (optional)

Posts support both R and Python code chunks. Use `echo: false` in YAML to hide code from output.

## Dependencies

- **Python:** `pip install -r requirements.txt` (pandas, plotnine, statsmodels, scipy, fastf1, etc.)
- **R:** Managed via `renv` - run `renv::restore()` (tidyverse, lme4, sf, leaflet)

## Execution Model

Posts use `freeze: true` by default - code only re-runs when source changes. To force re-execution, delete the corresponding `_freeze/posts/<name>/` directory before rendering.
