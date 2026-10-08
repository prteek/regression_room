---
name: project-docs
description: Set up or update a minimal set of docs for an analysis folder (README.md, summary.md, decisions.md, todolist.txt). Use when starting a new analysis or post, when asked to "set up project docs", to work through items in todolist.txt, or after finishing a piece of work to record status and decisions.
---

# Project docs

Four short files in the analysis folder, so the work can be picked up cold.

| File | Answers |
|---|---|
| `README.md` | What is this and where is everything? |
| `summary.md` | Where are we now? |
| `decisions.md` | What did we choose, and why? |
| `todolist.txt` | What's left to do? |

## Rules

- Dates are absolute (`YYYY-MM-DD`). `summary.md` and `decisions.md` start with front matter `title:` and `updated:`; bump `updated` on every edit.
- **README.md** — one-paragraph purpose, then one line per file or folder saying what it is.
- **summary.md** — current state as short bullets. Rewrite stale bullets; don't append history.
- **decisions.md** — bullets: **short name** — the rule, why, and the number that supports it. Record checked facts, not intentions. Rewrite a decision in place when it changes.
- **todolist.txt** — Todo+ format: sections end in `:`, items `☐` pending, `✔` done, `✘` cancelled. Finished items move to `Archive:` (last section, newest first) as `✔ <task> (<result>) @done(YY-MM-DD HH:MM)`. Never invent a time; use `@done(YY-MM-DD)` if unknown.

## Working

- **Starting:** create the four files with what is known; leave `TBD` where unknown.
- **After each piece of work:** move the todo to `Archive:` with its result, update the matching `summary.md` bullet, add any choice or caveat to `decisions.md`, and add new files to `README.md`.
- **Todo list as work queue:** "do item N" means the Nth pending `☐` in the named section. Don't reorder or reword the user's items. Prerequisites go above the item they block; out-of-scope findings become new items rather than silent fixes.
- **Keep it short:** one line per item, one or two sentences per decision or bullet, the result plus the one number that proves it. Link rather than repeat.
- **Human edits win:** re-read a file before editing and build on the user's version.
