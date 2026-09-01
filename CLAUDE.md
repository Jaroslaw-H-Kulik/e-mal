# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A web application for exploring Polish genealogical records from the parish of Grzybowa Góra (1826–1914). It parses historical records into a structured JSON database and provides an interactive web UI backed by a Java/Spring Boot REST API.

## Ways of work

IMPORTANT: When you are asked to do something, you must analyze task first. Check exisitng code, think about possible open questions/improvements/suggestions. Always think about bigger picture and how to make this app better and more functional. Ask questions before you start actual coding.

Always apply this rule even if you are not explicitly asked to do so in command passed to CLI.

## Running the Server

```bash
./mvnw spring-boot:run
# Windows: mvnw.cmd spring-boot:run
# Open: http://localhost:8000
```

The server is a Spring Boot app (`src/main/java/com/emal/genealogy/`) that serves the `web/` frontend and exposes a REST API. It loads `data/genealogy_new_model.json` into memory on startup and reads/writes it as the primary data store. Run tests with `./mvnw test`.

There is no data-regeneration pipeline anymore — `base.md`/`base.ged` are kept as raw source records only; nothing in the codebase parses them at runtime. `data/genealogy_new_model.json` is edited exclusively through the running app.

## Architecture

### Data Model (`src/main/java/com/emal/genealogy/model/`)

Plain Java records, each with a Jackson catch-all (`@JsonAnySetter`/`@JsonAnyGetter`) so unrecognized fields still round-trip losslessly:
- **Person** (`Person.java`) — `id` (P0001...), `first_name`, `last_name`, `maiden_name`, `gender` (M/F/U), `occupation`, `tags`, `notes`
- **Event** (`Event.java`) — life event (`birth`, `marriage`, `death`, `generic`) with `id` (E0001...), `type`, `date` (`FlexibleDate`), `place_id`, `content`, `description`, `title`, `source`, `notes`, `tags`, `links`
- **EventParticipation** (`EventParticipation.java`) — links persons to events via `role` (child/father/mother/deceased/bride/groom/witness/godparent/participant)
- **Place** (`Place.java`) — location with optional `house_number` and `parish_name`
- **Document**/**DocumentPage** (`Document.java`/`DocumentPage.java`) — scanned-record management, stored separately in `data/documents.json` + `data/documents/`
- **FamilyRelationship** (`FamilyRelationship.java`) — modeled but unused; relationships are derived from event participations, not stored as their own collection (see its javadoc)

All genealogy data lives in `data/genealogy_new_model.json`. Person IDs are `P####`, event IDs are `E####`, place IDs are `PL####`, event-participation IDs are `EP####`, document IDs are `D##`.

### Server API (`src/main/java/com/emal/genealogy/web/`)

Thin `@RestController`s delegate to a `service/` layer (business logic, one class per entity family — `PersonService`, `EventService`, `RelationshipService`, `DocumentService`, `DataService`, `GenetekaService`). GET routes serve static files from `web/` and `data/` (`config/StaticResourceConfig.java`) plus SPA routes for `/events`, `/person/**`, `/document/**` (`web/SpaRoutingController.java`), plus:
- `/api/geneteka-import` — external lookup proxy

POST endpoints (all accept/return JSON):
- `/api/save-data`, `/api/update-person`, `/api/add-person`, `/api/delete-person`
- `/api/add-event`, `/api/update-event`, `/api/delete-event`
- `/api/add-relationship`
- `/api/add-document`, `/api/update-document`, `/api/delete-document`, `/api/delete-document-page`

### Frontend (`web/`)

- `index.html` + `style.css` — shell and styling
- `app.js` — main application, person card, network graph (vis.js), search/filter
- `editor.js` — person edit and merge modals
- `event-editor.js` — event creation/editing modals for birth/marriage/death/generic events

The frontend is unchanged by the Java migration — it talks to the same REST contract regardless of backend language.

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

The "new model" (`data/genealogy_new_model.json`, defined by the canonical field lists in `JAVA_MIGRATION.md`'s "Data schema normalization" section) replaced an older flat model. The old model files (`data/persons.json`, `data/events.json`, `data/relationships.json`, `data/genealogy_complete.json`, `data/genealogy_enriched.json`, `data/genealogy_fixed.json`, `data/gender_review.json`, `data/disambiguation_report.json`, `data/statistics.json`) are legacy artifacts — nothing in the codebase reads or writes them anymore.


