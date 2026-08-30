# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A web application for exploring Polish genealogical records from the parish of Grzybowa Góra (1826–1914). It parses historical records into a structured JSON database and provides an interactive web UI and Python query API.

## Ways of work

IMPORTANT: When you are asked to do something, you must analyze task first. Check exisitng code, think about possible open questions/improvements/suggestions. Always think about bigger picture and how to make this app better and more functional. Ask questions before you start actual coding.

Always apply this rule even if you are not explicitly asked to do so in command passed to CLI.

## Running the Server

```bash
python3 server.py
# Open: http://localhost:8000
```

The server (`server.py`) serves the `web/` frontend and exposes a REST API. It reads/writes `data/genealogy_new_model.json` as the primary data store.

## Regenerating Data from Source

```bash
python3 process_genealogy.py   # Parse base.md → data/ JSON files
python3 query_genealogy.py     # Run example queries
```

## Architecture

### Data Model (`new_data_model.py`)

The current (new) model uses these entities:
- **Person** — individual with `id` (P0001...), `first_name`, `last_name`, `maiden_name`, `gender` (M/F/U), `birth_date`/`death_date` as `FlexibleDate`
- **Event** — life event (`birth`, `marriage`, `death`, `generic`) with `id` (E0001...), `type`, `date`, `place_id`, `content`
- **EventParticipation** — links persons to events via `role` (child/father/mother/deceased/bride/groom/witness/godparent/participant)
- **FamilyRelationship** — derived relationship between two persons (parent/child/spouse/sibling), optionally sourced from an event
- **Place** — location with optional `house_number` and `parish_name`

All data lives in `data/genealogy_new_model.json`. Person IDs are `P####`, event IDs are `E####`, relationship IDs are `R####`.

### Server API (`server.py`)

`GenealogyServerHandler` extends `SimpleHTTPRequestHandler`. GET routes serve static files from `web/` and `data/`, plus:
- `/api/geneteka-import` — external lookup proxy

POST endpoints (all accept/return JSON):
- `/api/save-data`, `/api/update-person`, `/api/add-person`, `/api/delete-person`
- `/api/add-event`, `/api/update-event`, `/api/delete-event`
- `/api/add-relationship`

### Frontend (`web/`)

- `index.html` + `style.css` — shell and styling
- `app.js` — main application, person card, network graph (vis.js), search/filter
- `editor.js` — person edit and merge modals
- `event-editor.js` — event creation/editing modals for birth/marriage/death/generic events

### Supporting Scripts

| Script | Purpose |
|--------|---------|
| `process_genealogy.py` | Parse `base.md` → JSON (legacy model) |
| `process_genealogy_v2.py` | Newer parser variant |
| `query_genealogy.py` | `GenealogyQuery` class for programmatic queries |
| `migrate_to_new_model.py` / `migrate_to_event_relationships.py` | One-time migrations |

### External Data Sources

- **Geneteka** (`geneteka.genealodzy.pl`) — external parish records lookup; used for birth/marriage/death lookups from person card buttons

## Key Data Files

- `data/genealogy_new_model.json` — **primary data file** (read/written by server at runtime)
- `data/genealogy_new_model.backup.json` — backup
- `base.md` — original Polish source records (do not modify)
- `base.ged` — GEDCOM export (raw source only; no code reads it — GEDCOM lookup/import was removed)
- `improvements.txt` — running list of feature requests/bug fixes (steps 1–59)

## Ongoing Development

`improvements.txt` tracks incremental feature steps. When implementing a step, read the full step description carefully — many steps have interdependencies (e.g., steps 29–31 around birth event parent handling, steps 32–34 around "family witness" events).

The "new model" (in `new_data_model.py` and `data/genealogy_new_model.json`) replaced an older flat model. The old model files (`data/persons.json`, `data/events.json`, `data/relationships.json`) are legacy artifacts.


