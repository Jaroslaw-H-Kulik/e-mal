# Java Migration Plan

## Goal

Rewrite the Python backend (`server.py` + `new_data_model.py` + supporting
services) as a Java backend, built alongside the existing Python one — not
replacing it in place. The Python backend keeps running and keeps being the
source of truth until the Java backend is proven equivalent. Only then do we
switch the running backend to Java.

"Proven" means: the existing `tests/golden/*.json` fixtures pass against the
Java implementation, and a live dual-run comparison against the Python
server shows identical responses (see "Cutover gate" below). The frontend
(`web/`) does not change — it talks to whichever backend is running over the
same REST contract.

## Stack decisions

- **Framework:** Spring Boot
- **Build tool:** Maven
- **Java version:** 21 (LTS — virtual threads, pattern matching/switch,
  sequenced collections; also just a better footing for a new project than
  17)
- **JSON:** Jackson (Spring Boot default), with a custom
  `JsonSerializer`/`JsonDeserializer` for `FlexibleDate`
- **Data model:** Java records mirroring the dataclasses in
  `new_data_model.py` (`Person`, `Event`, `EventParticipation`,
  `FamilyRelationship`, `Place`)
- **Persistence (initial):** keep the single JSON file
  (`data/genealogy_new_model.json`) as the datastore, read/written via
  Jackson — same shape as today. Do **not** combine this rewrite with a move
  to a real database; that's a separate, later decision once Java parity is
  proven.
- **Frontend:** unchanged. Spring serves `web/` as external static content
  (`spring.web.resources.static-locations=file:../web/`) rather than
  copying it into `src/main/resources/static/`, so the actively-edited
  frontend isn't duplicated during the transition.

## Folder structure

```
e-mal/
├── web/                          # unchanged frontend
├── data/                         # unchanged datastore (genealogy_new_model.json)
├── tests/                        # existing Python golden tests — kept as the oracle
│                                  # until parity is proven, then retired
│
├── java/                         # new Spring Boot project, alongside the Python one
│   ├── pom.xml
│   └── src/
│       ├── main/
│       │   ├── java/com/emal/genealogy/
│       │   │   ├── GenealogyApplication.java     # @SpringBootApplication, main()
│       │   │   │
│       │   │   ├── config/
│       │   │   │   └── DataProperties.java        # @ConfigurationProperties("data") — path to
│       │   │   │                                  # genealogy_new_model.json
│       │   │   │
│       │   │   ├── model/                         # records mirroring new_data_model.py
│       │   │   │   ├── Person.java
│       │   │   │   ├── Event.java
│       │   │   │   ├── EventParticipation.java
│       │   │   │   ├── FamilyRelationship.java
│       │   │   │   ├── Place.java
│       │   │   │   └── FlexibleDate.java          # + model.serialization.* Jackson (de)serializers
│       │   │   │
│       │   │   ├── repository/
│       │   │   │   └── GenealogyRepository.java   # @Component, loads JSON on @PostConstruct,
│       │   │   │                                  # holds in-memory store, saves on write
│       │   │   │
│       │   │   ├── service/                       # business logic — Spring-free plain classes,
│       │   │   │   │                               # this is the layer golden tests exercise directly
│       │   │   │   ├── PersonService.java          # add/update/delete-person
│       │   │   │   ├── EventService.java           # add/update/delete-event
│       │   │   │   ├── RelationshipService.java    # add-relationship
│       │   │   │   ├── SyncService.java            # sync-event-dates, sync-ages, dedupe-witnesses
│       │   │   │   └── GedcomService.java          # gedcom-lookup, gedcom-person
│       │   │   │
│       │   │   ├── web/                            # @RestController layer — thin, parses request,
│       │   │   │   ├── PersonController.java       # delegates to service, returns JSON
│       │   │   │   ├── EventController.java
│       │   │   │   ├── RelationshipController.java
│       │   │   │   └── GedcomController.java
│       │   │   │
│       │   │   ├── dto/                            # request/response bodies where they diverge
│       │   │   │                                   # from the domain model
│       │   │   │
│       │   │   ├── exception/
│       │   │   │   └── GlobalExceptionHandler.java # @ControllerAdvice — centralizes error→JSON
│       │   │   │                                   # mapping (server.py does this ad hoc per-handler)
│       │   │   │
│       │   │   └── gedcom/                         # port of convert_gedcom_to_model.py /
│       │   │       └── GedcomParser.java           # enrich_from_gedcom.py — deprioritized, do last
│       │   │
│       │   └── resources/
│       │       └── application.yml                 # server.port=8000, data.file=../data/genealogy_new_model.json,
│       │                                            # spring.web.resources.static-locations=file:../web/
│       │
│       └── test/
│           └── java/com/emal/genealogy/
│               ├── service/                        # plain JUnit5, NO @SpringBootTest — instantiate
│               │   ├── PersonServiceTest.java       # services directly against a repository pointed
│               │   ├── EventServiceTest.java        # at ../../tests/golden fixtures. Mirrors
│               │   └── RelationshipServiceTest.java # tests/test_add_event.py etc. one-to-one.
│               ├── web/                             # @WebMvcTest/MockMvc controller smoke tests —
│               │   └── ...                          # add later, low priority (service tests carry
│               │                                    # the golden-parity burden)
│               └── golden/
│                   └── GoldenFileTestSupport.java    # loads a golden JSON from ../../../tests/golden,
│                                                     # runs the service call, asserts equality
```

Note on the golden fixtures: Java tests reference `tests/golden/` **directly**
(no copy into `src/test/resources`). Single source of truth, zero drift risk.
The tradeoff is a relative-path coupling from the `java/` module out to the
repo-root `tests/` folder — acceptable since both live in the same repo for
the duration of the migration.

## Migration order

Simplest-first, to stand up the model/repository/test-harness scaffolding
before tackling harder logic:

1. `model/` + `repository/` (data model, JSON load/save) — no business logic yet
2. `add-person` (simplest endpoint, smallest golden fixture set)
3. `add-event` (birth/death/marriage/generic — larger surface, exercises
   parent/child sync logic from `improvements.txt` steps 29–34)
4. `update-person`, `update-event`
5. `add-relationship`
6. `delete-person`, `delete-event`
7. Sync endpoints: `generate-parent-marriages`, `sync-event-dates-to-persons`,
   `sync-all-ages-to-birth-years`, `deduplicate-witnesses-godparents`
8. GEDCOM endpoints: `gedcom-lookup`, `gedcom-person`, `geneteka-import`
9. `gedcom/` parser port (`convert_gedcom_to_model.py`,
   `enrich_from_gedcom.py`) — last, since these are offline batch tools, not
   in the server request path

Each step is done when: the Java service produces byte-for-byte-equivalent
JSON (structurally) against every relevant fixture in `tests/golden/`.

## Cutover gate

Per-endpoint golden-file unit tests prove the service layer is correct in
isolation. Before actually switching the running backend to Java, add a
**dual-run parity harness**: run both servers (Python on its current port,
Java on a second port) side by side, send identical requests to both for
every endpoint, and diff the raw HTTP JSON responses. This catches anything
the unit-level golden tests can't see — HTTP-layer serialization
differences, header/status-code mismatches, routing edge cases.

Cutover only happens once:
- [ ] All golden-file tests pass against the Java service layer
- [ ] The dual-run harness shows no diffs across all endpoints, run against
      the real `data/genealogy_new_model.json`
- [ ] Frontend manually exercised against the Java backend (golden path +
      edge cases per CLAUDE.md's UI testing guidance)

## Explicitly out of scope for this migration

- Moving off the single-JSON-file datastore (stays as-is; a DB migration is
  a separate future decision)
- Rewriting `process_genealogy.py`, `query_genealogy.py`,
  `migrate_to_new_model.py`, `migrate_to_event_relationships.py`,
  `generate_enrichment_queue.py` — these are one-off/orphaned scripts, not
  part of the running server
- Any change to `web/` (frontend stays vanilla JS, talks to REST regardless
  of backend language)

## Open items / TBD

- Maven `groupId`/`artifactId` for `pom.xml` — currently assumed
  `com.emal.genealogy`, not yet confirmed
- Whether `java/` becomes the permanent home once Python is retired, or gets
  flattened to repo root at that point
- Whether to eventually copy `web/` into `src/main/resources/static/` for a
  single self-contained fat jar (deferred until Java is the sole backend)
