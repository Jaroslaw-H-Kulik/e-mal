# Java Migration Plan

## Cutover complete (2026-09-01)

The Python backend has been removed. Every endpoint CLAUDE.md documents as
live had already been ported to Java (confirmed by diffing `server.py`'s
`do_GET`/`do_POST` route table against the Java controllers — a 1:1 match,
including the four sync endpoints CLAUDE.md lists, which turned out not to
exist in either Python implementation, live or historical — see "Open items
/ TBD" below). Both suites were green at removal time (42/42 Python,
52/52 Java) and were treated as sufficient proof of parity — **the "Cutover
gate" dual-run parity harness described below was never built**; this was a
deliberate, explicit choice to skip it rather than an oversight, made when
removing Python.

What changed in this pass, beyond deleting `server.py`/`app/`/`tests/`/
`.venv`/`pyproject.toml`/`uv.lock`:
- The `java/` Spring Boot module was **flattened to the repo root**
  (`pom.xml`, `mvnw`/`mvnw.cmd`/`.mvn/`, `src/` all moved up one level) —
  resolving the "Open items / TBD" question below in favor of "flatten now."
  `application.yml`'s `../web`/`../data` relative paths became `web`/`data`.
- The `tests/golden/*.json` fixtures the Java golden-file tests read
  (`GoldenFileTestSupport`/`DocumentGoldenFileTestSupport`) moved to
  `src/test/resources/golden/` and are now self-contained inside the Java
  module — the "Golden fixtures" open question below is resolved the same
  way. `GoldenFileTestSupport`/`DocumentGoldenFileTestSupport`/
  `GenealogyRepositoryRoundTripTest`'s path constants were updated to match
  (module root == repo root now, so `../data/...` became `data/...`).
- Full test suite reconfirmed green after both moves (52/52,
  `./mvnw test` from repo root), plus a live `spring-boot:run` boot check on
  a scratch port confirming `/`, `/web/**`, `/data/**`, `/events`,
  `/person/**`, `/document/**`, and bare `/person` (404) all still resolve
  correctly against the new on-disk layout.

The rest of this document is kept as the historical record of how the
migration got here — paths inside older entries below (e.g. `java/pom.xml`,
`../../../tests/golden`) describe the pre-flatten layout at the time they
were written, not the current one.

## Status

- **Done:** Phase 0 data-schema normalization (see below) — `data/genealogy_new_model.json`
  now has a consistent field set per entity type. All 36 `tests/golden/*.json`-backed
  tests pass (`python -m uv run pytest`).
- **Done (Python side, ahead of the Java port):** `server.py`'s business logic
  was extracted into `app/genealogy_repository.py`'s `GenealogyRepository`
  class — a plain Python class with no HTTP awareness, one method per
  endpoint (`add_person`, `update_person`, `delete_person`, `add_event`,
  `update_event`, `delete_event`, `add_relationship`, plus the
  `sync_parents_to_birth_events`/`sync_ages_to_birth_years` helpers).
  `server.py` now just dispatches to a module-level instance of it. The
  Geneteka proxy and document management stay in `server.py`.
  **This is the reference to port method-by-method for the Java `service/`
  layer** (migration order below) — read it instead of the old monolithic
  `server.py` history.
- **Done:** step 1 (`model/` + `repository/` scaffolding). The `java/`
  Spring Boot project boots (Maven Wrapper, Spring Boot 4.1.1 / Jackson 3,
  Java 21 release target on the installed JDK 26 - see "Toolchain
  decisions"), loads `data/genealogy_new_model.json` on startup via
  `GenealogyRepository`, and a no-op load-then-save round trip is
  byte-identical to the source file
  (`GenealogyRepositoryRoundTripTest`). Getting there required extending
  Phase 0 further than originally scoped - see "Data schema normalization"
  below for the key-order and date-shape follow-up passes this uncovered.
- **Done:** step 2 (`add-person`). `service/PersonService.java` +
  `web/PersonController.java` port `add_person`
  (`app/genealogy_repository.py`) byte-for-byte against
  `tests/golden/add_person_*.json` (`PersonServiceTest`, via the new
  reusable `test/.../golden/GoldenFileTestSupport.java` harness), plus a
  live HTTP smoke test against a sandboxed data copy confirming the
  snake_case JSON contract. Required two Phase 0 follow-up fixes in the
  Python reference first - see the `resolve_place` and `add_person` event
  literal addenda below.
- **Done:** step 3 (`add-event`). `service/EventService.java` +
  `web/EventController.java` port `add_event`
  (`app/genealogy_repository.py`), including the
  `sync_parents_to_birth_events`/`sync_ages_to_birth_years` helpers it
  calls unconditionally and the `create_parent_marriage_if_needed` call
  for birth events - byte-for-byte against all 12
  `tests/golden/add_event_*.json` fixtures (`EventServiceTest`, same
  `GoldenFileTestSupport` harness as step 2), plus a live HTTP smoke test
  (new child + inline new parents, exercising auto-birth-event and
  auto-marriage creation) against a sandboxed data copy. Required six
  more Phase 0 follow-up fixes in the Python reference first - see the
  three step-3 addenda below (`add_event`'s own event literals and date
  shape, `resolve_place`'s other branch, three downstream helpers'
  literals, and `add_event`'s new-person literals).
  New shared `service/` components introduced for reuse by later steps:
  `RequestValues` (raw-request-map reading helpers, also backfilled into
  `PersonService`), `EventLookup` (birth/death/marriage event lookups),
  `ParentMarriageService`.
- **Done:** step 4 (`update-person`, `update-event`). `PersonService.updatePerson`
  and `EventService.updateEvent` port their Python equivalents
  (`app/genealogy_repository.py`) byte-for-byte against all 8
  `tests/golden/update_person_*.json`/`update_event_*.json` fixtures
  (additions to `PersonServiceTest`/`EventServiceTest`, same
  `GoldenFileTestSupport` harness - extended with an `extraDiffs` overload
  of `assertMatchesGolden`, mirroring `golden_utils.assert_matches_golden`'s
  `extra_new_id_diffs`, for `update_event_swap_and_new_child_combined`'s
  add-event setup call), plus live HTTP smoke tests (basic field update,
  auto-create birth/death events, new-child-with-new-parents on an existing
  birth event, nonexistent-event failure) against a sandboxed data copy.
  Required five more Phase 0 follow-up fixes in the Python reference first
  - see the step 4 addendum below. `update_event`'s participant-handling
  logic (new-person/parent creation, auto-birth/marriage-event creation) was
  near-duplicated between `add_event`/`update_event` in Python; the Java
  port instead extracts it into two methods shared by both
  `EventService.addEvent` and `EventService.updateEvent`
  (`processParticipant`/`createParticipantPersonWithParents`) rather than
  carrying the duplication into Java too - a mechanical extraction of
  `addEvent`'s existing inline block, not a behavior change (`addEvent`'s
  own tests stayed green throughout). `PersonService` gained an
  `EventLookup` dependency it didn't need before (`updatePerson` looks up
  existing birth/death events the same way `add-event`'s auto-birth-event
  logic does).
- **Done:** step 5 (`add-relationship`). `service/RelationshipService.java`
  + `web/RelationshipController.java` port `add_relationship`
  (`app/genealogy_repository.py`, "Step 10") byte-for-byte against all 4
  `tests/golden/add_relationship_*.json` fixtures (`RelationshipServiceTest`,
  same `GoldenFileTestSupport` harness), plus the two error-path scenarios
  (`missing role key`, `unknown relationship type`) asserted directly
  against the result record, plus a live HTTP smoke test (parent/spouse
  relationship creation, missing-key and unknown-type failures, nonexistent
  person failure) against a sandboxed data copy. Required one more Phase 0
  follow-up fix in the Python reference first - see the step 5 addendum
  below. Despite its name, `add_relationship` never touches a
  `family_relationships` collection - every relationship type is expressed
  by creating/reusing a birth or marriage event, reusing
  `EventLookup`/`ParentMarriageService`/`IdGenerator` unchanged from steps
  3-4; `FamilyRelationship.java` (scaffolded in step 1) stays unused, per
  its own javadoc. New shared helper: `RequestValues.requireString`, which
  mirrors Python's `dict[key]` (throws with a `"'key'"`-shaped message on a
  missing key, matching `str(KeyError(key))`) rather than the
  presence/truthiness-aware helpers every other service uses - needed
  because `add_relationship` is the first endpoint whose Python reference
  actually depends on an uncaught `KeyError` propagating out as the
  response's error text (see `test_missing_role_key_fails_cleanly`).
- **Done:** step 6 (`delete-person`, `delete-event`). `PersonService.deletePerson`
  and `EventService.deleteEvent` port their Python equivalents
  (`app/genealogy_repository.py`) byte-for-byte against both
  `tests/golden/delete_person_cascade_and_preserve.json`/
  `delete_event_removes_participations.json` fixtures (additions to
  `PersonServiceTest`/`EventServiceTest`), plus the two nonexistent-id
  failure paths asserted directly, plus a live HTTP smoke test (cascading
  person delete, plain event delete, both not-found cases) against a
  sandboxed data copy. No Phase 0 follow-up needed - unlike every prior
  step, delete-person/delete-event never construct a new
  Person/Event/Place literal, so there was no canonical-field-shape gap to
  find. `deletePerson`'s `deletedRelationships` is hardcoded to `0`:
  `family_relationships` isn't a top-level collection in the live JSON (see
  `FamilyRelationship`'s javadoc), so `GenealogyRepository` has no such map
  to cascade into - this mirrors dead code in the Python original, not a
  gap in the port. `deletePerson` also has no guard against deleting a
  cardinality-required participant role (e.g. a marriage's only groom) -
  intentionally ported as-is, matching a real, documented, currently-
  unhandled data-integrity gap in the Python reference (see
  `test_delete_person.py`'s docstring) rather than silently fixing it
  during a migration step.
- **Done (ad hoc, outside the numbered migration steps):** SPA routing for
  `/events` and `/person/**`. `web/SpaRoutingController.java` (+
  `config/FrontendProperties.java`, `web.root: ../web` in
  `application.yml`) mirrors `server.py`'s `do_GET` special-case (`self.
  path.startswith('/person/') or self.path == '/events'` → serve
  `index.html` so the frontend's own JS router can take over) - needed for
  the browser UI to work at all against the Java backend on entity URLs,
  not just `/`. `/document/*` is deliberately NOT mirrored (out of scope -
  document management isn't ported, see "Open items / TBD"). One real
  divergence found and closed while verifying this live: Spring's default
  `PathPatternParser` matches bare `/person` (no trailing id) against the
  `/person/**` mapping, unlike Python's literal `startswith('/person/')`
  check - closed by explicitly checking the raw request URI in the handler
  and returning 404 for that exact case, confirmed via live smoke test
  (`/events`, `/person/P0001`, `/person/P0001/nested` → 200 text/html;
  bare `/person`, `/document/foo` → 404; a real static file and `/` →
  unaffected).
- **Done (ad hoc, outside the numbered migration steps):** `/data/**`
  static file serving. `config/DataStaticResourceConfig.java` (a
  `WebMvcConfigurer` registering a dedicated resource handler for the
  `/data/**` pattern, separate from `spring.web.resources.static-locations`'s
  `/**` → `web/` mapping) mirrors `server.py`'s `do_GET`, which serves
  `/data/` as static files for free via `SimpleHTTPRequestHandler` - this
  is `web/app.js`'s entire read path for the genealogy model (it never
  calls an `/api/*` endpoint to *read* data, only to write it:
  `loadData()` fetches `/data/genealogy_new_model.json` or
  `/data/documents.json` on every page load
  and every model switch) and `document-manager.js`'s scanned-page
  thumbnails (`/data/documents/<filename>` as plain `<img src>`). Derives
  the served directory from the existing `DataProperties.file()` property
  (the same one `GenealogyRepository` already reads) rather than a new
  config key, so it automatically stays sandboxed to whatever
  `--data.file` override a smoke test or future dual-run harness uses,
  with no risk of drifting out of sync with the repository's own data
  source. First automated (not just manual-smoke-test) coverage for the
  web layer: `web/StaticAndSpaRoutingTest.java`, a `@SpringBootTest(webEnvironment
  = RANDOM_PORT)` using `TestRestTemplate` against a sandboxed temp-dir
  data file - covers `/data/**` serving (found + 404) and, since the same
  harness could cover it for free, folds in automated regression coverage
  for the `/events`/`/person/**` SPA routing added just before this (previously
  manual-smoke-test-only). Needed one new test dependency
  (`spring-boot-restclient`, for `RestTemplateBuilder` -
  `spring-boot-resttestclient`'s `TestRestTemplate` autoconfiguration needs
  it reflectively at context-startup but `spring-boot-starter-webmvc-test`
  doesn't pull it in transitively) and `@AutoConfigureTestRestTemplate` on
  the test class - unlike older Spring Boot, `TestRestTemplate` is no
  longer auto-registered just from `webEnvironment = RANDOM_PORT`.
  Verified live via the same manual curl smoke-test pattern as every prior
  step, in addition to the new automated coverage. This closes the
  biggest of the remaining UI-blocking gaps noted below - Geneteka/
  save-data/documents still aren't ported (see "Open items / TBD"), but
  the browser can now load and browse data end-to-end against the Java
  backend for the record types already ported (steps 2-6).
- **Done (bug found via real manual UI testing, not curl):** `/web/**`
  static asset serving. The first time the actual browser UI was opened
  against the Java backend (`http://localhost:8000`), the page loaded but
  completely unstyled with no JS running - every asset 404ing.
  `web/index.html` links its stylesheet and all five JS files with an
  absolute `/web/...` prefix (`<link href="/web/style.css">`, `<script
  src="/web/app.js">`, etc.), but the existing
  `spring.web.resources.static-locations: file:../web/` config only maps
  the bare `/**` pattern to that directory - so `/web/style.css` resolved
  against it as `../web/web/style.css` (a doubled "web" segment) and
  404'd. This bug predates today's session entirely (it's been there
  since step 1's static-locations setup) but was invisible until now
  because every prior verification was curl hitting specific known-good
  paths, never a real browser loading the full page and its linked
  assets. `config/DataStaticResourceConfig.java` (added earlier this
  session for `/data/**`) was renamed to `config/StaticResourceConfig.java`
  and now also registers an explicit `/web/**` → `file:../web/` resource
  handler alongside `/data/**` (the existing bare `/**` mapping is left in
  place, since `WelcomePageHandlerMapping` needs it to find `index.html`
  at `/`). Confirmed against the user's own live server before the fix
  (`GET /web/style.css`/`/web/app.js` → 404) and covered by a new
  regression test in `StaticAndSpaRoutingTest`
  (`webAssetsReferencedByIndexHtmlAreServedUnderWebPrefix`) so this can't
  silently break again.
- **Done:** step 7 (document management). Documents had zero Python test
  coverage before this step (unlike every prior endpoint family) - closed
  first with `tests/test_documents.py` (7 tests, golden fixtures via a new
  `tests/documents_golden_utils.py`, parallel to but distinct from
  `golden_utils.py` since `data/documents.json` is one flat
  `{doc_id: document}` map, not `GenealogyRepository`'s four collections).
  Checking the real file found it already fully schema-consistent (all 14
  documents share the identical 8-key set *and* order, all 133 pages share
  the identical 2-key shape) - no Phase-0-style normalization pass was
  needed, unlike every genealogy-model step. One real shape gotcha found
  and documented instead: `document.date` is a plain nullable year
  (`Integer`), not a `FlexibleDate` object like `Event.date`. Every test
  adds its own fixture document via a setup `add-document` call rather
  than anchoring to a real row (see `tests/anchors.py`'s documents
  section) - the sandbox's `data/documents/` dir starts empty on purpose
  (`tests/conftest.py` skips the real ~424MB of scanned page images), so a
  real document's page files wouldn't exist to test deletion against
  anyway, and documents.json's rows have no interesting cross-links worth
  anchoring to the way persons/events do.

  Ported to Java against those same fixtures: `model/Document.java` +
  `model/DocumentPage.java` (plain records, the usual `@JsonAnySetter`/
  `@JsonAnyGetter` catch-all), `repository/DocumentRepository.java` (a
  separate `@Component` from `GenealogyRepository`, reusing
  `GenealogyJsonMapper.create()` as-is since it was already generic; also
  owns the page-image directory, lazily `Files.createDirectories`-ing it
  on every access like `server.py`'s `_documents_dir()` does),
  `config/DocumentDataProperties.java` (a new `documents.file` property
  rather than a second field on `DataProperties`, which would have broken
  every existing single-arg `new DataProperties(file)` call site),
  `IdGenerator.nextDocumentId` (generalized the private `nextId` helper to
  take a configurable digit width, since documents use a 2-digit `D##`
  counter - `server.py`'s older `f'D{next_num:02d}'` - unlike every other
  entity's 4-digit counter), `service/DocumentService.java` (the only
  service in this codebase that performs real file I/O - base64
  decode/write on add, delete on delete/delete-page - so its
  `catch (RuntimeException e)` blocks became
  `catch (IOException | RuntimeException e)`, the one place Java's checked
  exceptions needed explicit handling that Python's blanket
  `except Exception` gets for free), four result records
  (`AddDocumentResult`/`UpdateDocumentResult`/`DeleteDocumentResult`/
  `DeleteDocumentPageResult` - kept separate per the codebase's
  one-type-per-endpoint convention even though three of the four share a
  `{success, document}` shape), and `web/DocumentController.java`.
  `web/SpaRoutingController.java` now also mirrors `/document/**` (with
  the same bare-`/document`-404 exclusion `/person` already had) -
  `StaticAndSpaRoutingTest` was updated accordingly, since it previously
  pinned the pre-port behavior (`/document/foo` → 404) as a passing
  regression test; that assertion now correctly expects `/document/<id>`
  to serve `index.html` instead. No `/data/**` static-serving changes were
  needed - `data/documents.json`/`data/documents/<filename>` were already
  served for free by the existing config (same directory as
  `genealogy_new_model.json`).

  New test-side component: `golden/DocumentGoldenFileTestSupport.java`, a
  single-map parallel to `GoldenFileTestSupport` (which is hardcoded to
  `GenealogyRepository`'s four collections) - mirrors
  `documents_golden_utils.py`'s split from `golden_utils.py` on the Python
  side. `service/DocumentServiceTest.java` (7 tests) exercises
  `DocumentService` directly against the same `tests/golden/*.json`
  fixtures the Python tests wrote, including reading back real page-file
  bytes from disk (`repository.pagesDirectory()`) to verify the
  base64-decode/write path, not just the JSON diff. Verified live end to
  end against a sandboxed copy (`add-document` with a real page write,
  `/document/<id>` → 200 `index.html`, bare `/document` → 404,
  `update-document`, `delete-document-page` removing the file from disk,
  `delete-document` removing the entry and confirming no `D##` string
  remains in the sandboxed `documents.json`, and the not-found path) - all
  47 Java tests and all 42 Python tests pass.
- **Done (deliberate Java-only divergence from Python, not a porting step):**
  `update-person` redesigned from partial-update (JSON-key-presence)
  semantics to a plain PUT plus change-detection event-sync.
  `PersonService.updatePerson` now takes a typed `UpdatePersonRequest`
  (replacing its `Map<String, Object>` + `RequestValues` reading, the last
  endpoint still on that pattern) and always overwrites every person field;
  its birth/death event-sync (`PersonService.syncLifeEvent`) only
  touches/reports an event when the computed new date/place genuinely
  differs from what's stored, rather than whenever the relevant JSON keys
  were merely present - which used to mark an event "updated" even when
  nothing inside it changed (a documented quirk in the old
  `update_person_null_place_marks_events_updated` fixture), and could never
  clear an existing date/place at all. The UI (`web/index.html`'s
  edit-person modal, `web/editor.js`'s `savePersonEdit`/`openEditModal`)
  was extended with real birth/death date+circa inputs (previously
  place-only) and now always sends every field, which is what makes the
  plain-PUT DTO possible - Jackson 3's record/constructor binding can't
  distinguish "JSON key absent" from "key present as null" (verified
  directly against this project's JsonMapper while investigating an
  `Optional<T>`-based alternative), so partial-update semantics on a typed
  record aren't expressible here at all; making the caller always send
  everything sidesteps the question instead of working around Jackson.
  Also surfaced and fixed a real data-model gotcha while building the
  change-detection comparison: this dataset has ~80 separate `Place`
  records all named "Małyszyn" (one per house number), and
  `PlaceResolver.resolveByNameOnly` always resolves any of them to the
  first match (`PL0001`) - comparing re-resolved ids would have falsely
  flagged every save of a person whose birthplace is one of the other 79
  duplicates as "changed" (and silently collapsed their event's `place_id`
  to `PL0001` in the process). Fixed by comparing place *names* against an
  existing event, only re-resolving (and only then risking that collapse)
  when the name actually differs - see `PersonService.syncLifeEvent`'s
  javadoc.

  **This is an intentional exception to this migration's Python/Java parity
  goal** (see "Goal" below), not an oversight: `app/genealogy_repository.py`'s
  `update_person` and `tests/test_update_person.py` are deliberately left
  unchanged and still pass (42 Python tests, unaffected) - confirmed
  unaffected by running the full Python suite after this change. Of the
  four `tests/golden/update_person_*.json` fixtures, only
  `update_person_creates_new_events.json` stays shared with Python
  (that scenario has no pre-existing event, so the redesign doesn't change
  its output); the other three are no longer valid inputs/outputs for the
  new PUT contract and are left untouched on disk for Python's tests only -
  `PersonServiceTest`'s Java-side coverage for those scenarios was
  rewritten as plain assertions with no golden fixture
  (`resendingUnchangedDatesAndPlacesTouchesNoEvents`,
  `onlyGenuinelyChangedLifeEventIsMarkedUpdated`,
  `clearingAnExistingPlaceRemovesItFromEvent`,
  `syncsDateIntoExistingEventsAndPreservesUnchangedPlaceIdentity`).
  **Consequence for the "Cutover gate" below:** the eventual dual-run
  parity harness will show a real, expected diff on `/api/update-person`
  for any partial-payload request - it needs an explicit carve-out for this
  one endpoint rather than being treated as a bug to fix.
- **Done (ad hoc, outside the numbered migration steps):** `/api/save-data`
  and `/api/geneteka-import` - the last two endpoints flagged in "Open
  items / TBD" as unported, both still live-wired to real UI (`/api/save-data`
  from `web/editor.js`'s merge-persons flow, `/api/geneteka-import` from the
  person card's Geneteka lookup buttons in `web/app.js`).
  `service/DataService.java` + `web/DataController.java` port
  `save_genealogy_data` (`app/genealogy_repository.py`) - a whole-document
  overwrite, not a merge like every add/update endpoint: `GenealogyRepository.replace`
  (new) swaps all four in-memory collections plus `metadata` from the
  posted `GenealogyDocument` and persists. Python's version is stateless
  (rereads/rewrites the file around every call); Java's already-resident
  in-memory store just gets swapped instead, same observable effect.
  `service/GenetekaService.java` + `web/GenetekaController.java` port
  `geneteka_import` - the two-step cookie-session HTTP flow
  (`java.net.http.HttpClient` + `CookieManager`, mirroring Python's
  `http.cookiejar`-backed `urllib` opener) and per-record-type HTML/regex
  parsing (birth/marriage/death row shapes, `parse_rodzice`, `extract_uwagi`,
  `extract_links`) are hand-ported 1:1; response modeled as a
  `GenetekaImportResult` sealed interface (`Success`/`Failure`) since the
  Python success/failure dicts have genuinely different key sets, matching
  this codebase's existing `AddDocumentResult`-style convention. No
  automated tests for `GenetekaService` - it proxies a live third-party site
  with no existing seam (or Python test) to fake it against; only
  `save-data` got the test treatment (`DataServiceTest`, `DataControllerTest`
  - the first automated web-layer POST-endpoint test in this codebase, since
  there's no Python golden fixture for save-data either to anchor a
  service-level golden test against - see `DataServiceTest`'s javadoc).
  This closes every endpoint CLAUDE.md documents as live except the four
  sync endpoints already flagged below as not actually existing in Python.

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

- **Framework:** Spring Boot 4.1.1 (current release as of this migration,
  generated via start.spring.io) — note this bundles **Jackson 3**, not
  Jackson 2: core/databind moved to the `tools.jackson.*` package
  (`ObjectMapper`/`JsonMapper` stay put, but `JsonSerializer`/`JsonDeserializer`
  are renamed `ValueSerializer`/`ValueDeserializer`, `SerializerProvider` is
  now `SerializationContext`, and `@JsonSerialize`/`@JsonDeserialize` moved
  from `jackson-annotations` into `tools.jackson.databind.annotation`).
  `jackson-annotations` itself (`@JsonProperty`, `@JsonAnySetter`, etc.)
  stayed at its old `com.fasterxml.jackson.annotation` package. Look up
  real signatures on the actual jars in `~/.m2` before writing Jackson code
  against this project — most Jackson 2 tutorials/examples don't apply.
- **Build tool:** Maven
- **Java version:** 21 (LTS — virtual threads, pattern matching/switch,
  sequenced collections; also just a better footing for a new project than
  17)
- **JSON:** Jackson (Spring Boot default). `FlexibleDate` turned out to
  need no custom serializer at all once its on-disk shape was closed (see
  "Data schema normalization" addendum) — it's a plain record.
- **Data model:** Java records — **not** a literal mirror of
  `new_data_model.py`'s dataclasses, which are stale/aspirational (e.g. they
  declare `Person.middle_name`/`previous_last_names`/`links` that no live
  code path ever writes, and don't have `Event.description`/`title`/`source`
  fields that the live server does write). Field lists are instead the
  canonical schema established by the Phase 0 normalization below — see
  "Data schema normalization" for the exact per-entity field lists. Each
  record additionally carries a Jackson catch-all
  (`@JsonAnySetter`/`@JsonAnyGetter` into a `Map<String, Object> extra`) so
  any field introduced later without a matching normalization pass still
  round-trips losslessly instead of being silently dropped on save.
- **Persistence (initial):** keep the single JSON file
  (`data/genealogy_new_model.json`) as the datastore, read/written via
  Jackson — same shape as today. Do **not** combine this rewrite with a move
  to a real database; that's a separate, later decision once Java parity is
  proven.
- **Frontend:** unchanged. Spring serves `web/` as external static content
  (`spring.web.resources.static-locations=file:../web/`) rather than
  copying it into `src/main/resources/static/`, so the actively-edited
  frontend isn't duplicated during the transition.

## Data schema normalization (Phase 0 — done)

Before writing any Java model code, `data/genealogy_new_model.json` was
checked against `new_data_model.py` and found schema-inconsistent: different
code paths (the original `process_genealogy.py` parser, `add_person`'s
auto-birth-event, `add_event`'s participant-driven birth events, and old
migration scripts) each wrote a different key set for the same entity type
over time (e.g. some persons had no `maiden_name` key at all rather than a
null one; some events had `content` but not `description`, or vice versa;
two places had a `type` key nothing else had).

This mattered for the migration specifically because `tests/golden_utils.py`'s
`dict_diff` does full dict equality to detect a "changed" record. Typed Java
records always serialize every declared field — so loading a person that
historically lacked `maiden_name` and writing it back unchanged would inject
`"maiden_name": null`, registering as a false "changed" entry and breaking
golden parity (mainly a risk for `update-person`/`update-event`, since
`add-*` fixtures already capture full-field-set records). Fixing the data
once, up front, means the Java model can be plain typed records — no
`Optional`/presence-wrapper complexity to distinguish "key absent" from "key
present but null".

**Fix applied** (see `normalize_data_schema.py`, kept in the repo root
alongside the other one-off `migrate_*.py` scripts): every record of a type
now carries the same canonical field set, with any field it previously
lacked added as `null` (or `[]` for list fields). Purely additive — no key
was renamed, merged, or dropped, and no existing value was touched.
`data/genealogy_new_model.backup.20260829.json` is the pre-normalization
snapshot. Canonical field lists (these are what the Java `model/` records
should declare):

- `persons`: `id, first_name, last_name, gender, maiden_name, occupation, tags, notes`
- `events`: `id, type, date, place_id, content, description, title, source, notes, tags, links`
- `places`: `id, name, parish_name, house_number, type`
- `event_participations`: `id, event_id, person_id, role` (was already
  consistent — no normalization needed)

Note `events.content` and `events.description` are genuinely distinct, not
redundant: `description` is a short auto-label ("Birth of X") written by the
auto-generated-event paths in `add_person`/`update_person`/`add_relationship`;
`content` is longer text — either a generated participant-role summary
(`add_event`/`update_event`) or, for legacy events, the raw original parser
transcription. Both are kept. `title` (currently always null) and `source`
(a provenance tag from one old migration) were also kept rather than
dropped, since `add_event`/`update_event` already read/write `title` today.

Verification for this pass: `python -m uv run pytest` (all 36 tests) and
`python -m uv run python tests/invariants.py` (no new issue codes vs. the
pre-normalization backup) both passed before the normalized file was
promoted over the original.

If a future field is added inconsistently again, re-run (or extend)
`normalize_data_schema.py` the same way — write to
`data/genealogy_new_model.normalized.json` first, review the printed
per-field-added summary, verify against the test suite + invariants, then
promote.

### Phase 0 addendum: key order and FlexibleDate shape (done during step 1)

Attempting step 1's round-trip exit criterion surfaced two gaps Phase 0
hadn't closed, because it only normalized field *presence*, not field
*order*, and only at the top level:

- **Per-record key order was inconsistent.** Real records of the same
  entity type had different on-disk key orders (e.g. some persons had
  `gender` before `maiden_name`, some after; `events` had 16 different
  orders). Harmless for Python, since `json.load`/`json.dump` just carry
  forward whatever order was already in the file - but fatal for a
  byte-identical Java round trip, since a typed Java record always
  serializes one fixed order for every instance of a type.
- **`events[*].date` had two inconsistent shapes.** `FlexibleDate.to_dict()`
  (`new_data_model.py`) omits `year`/`month`/`day`/`circa` keys entirely
  when falsy, but a different code path (visible in
  `app/genealogy_repository.py`'s birth-year-inference logic) always writes
  all four keys instead. 1547 events used one shape, 252 the other, on top
  of 164 events with `date: null`. This is now closed the same way: every
  non-null date always carries all four keys.

`normalize_data_schema.py` was extended to also (a) rewrite every record's
keys into the exact `CANONICAL_FIELDS` order, and (b) normalize every
`events[*].date` to `{year, month, day, circa}` (nulls/`false` where
unknown). Both passes are purely cosmetic - verified via an order/shape
-insensitive deep-equality check against the pre-pass file, plus
`tests/invariants.py` producing identical output before/after. Four golden
fixtures (`delete_event_removes_participations`,
`delete_person_cascade_and_preserve`, `update_event_swap_participants`,
`update_person_syncs_existing_events`) embedded the old date shape for
records incidental to what those tests exercise and needed regenerating;
each regeneration was diffed against its prior version first to confirm
only the `circa`/`day`/`month` keys were added, then `python -m uv run
pytest` (all 36) was reconfirmed green. Backups:
`data/genealogy_new_model.backup.20260829b.json` (pre-key-order-fix),
`data/genealogy_new_model.backup.20260829c.json` (pre-date-shape-fix).

This closure held for the *existing* file, but is not self-enforcing going
forward: `web/event-editor.js` builds outgoing event dates as
`{year, month, day}` with no `circa` key, and
`app/genealogy_repository.py`'s `add_event`/`update_event`
(`event_data['date']`) store whatever shape the request sent without
normalizing it. A new event added through the running app today would
therefore write a *third*, still-different date shape. Not fixed here
(it's live server behavior, not a migration-scaffolding concern), but
worth fixing in `app/genealogy_repository.py` before/alongside porting
`add_event`/`update_event` to Java (migration order step 3), so the
Python and Java implementations both keep writing the same closed shape.
See "Open items / TBD".

### Phase 0 addendum: `resolve_place`'s name-only branch (done during step 2)

Starting step 2 (`add-person`) surfaced the same class of gap for
`places`: `Place`'s canonical field set is `id, name, parish_name,
house_number, type` (see above), but `GenealogyRepository.resolve_place`
(`app/genealogy_repository.py`) - when called with `house_number=None`,
i.e. every `add_person`/`update_person` call site - created new places as
a 3-key dict (`id, name, type`), omitting `parish_name` and
`house_number` entirely rather than writing them as `null`. Phase 0's
normalization pass never caught this because it only normalized the
*existing* file; this branch keeps writing the non-canonical shape on
every call, live. Two golden fixtures had a newly-created place in this
shape: `add_person_full_with_places` and `update_person_creates_new_events`.

Fixed the same way as the date-shape addendum above: `resolve_place`'s
`house_number is None` branch now always writes all five canonical keys
(`parish_name`/`house_number` as `null`), so Java's `Place` record (which
always serializes every field) matches byte-for-byte. The other branch
(`house_number` given - `add_event`/`update_event`'s `handle_place`,
which also omits `parish_name`/`type`) was deliberately left as-is,
since it isn't exercised until step 3; fix it the same way when porting
`add_event`. Both affected fixtures were regenerated and diffed against
their prior versions to confirm only `house_number: null`/`parish_name:
null` were added, then `python -m uv run pytest` (all 36) and `python -m
uv run python tests/invariants.py` (no new issue codes) were reconfirmed
green before promoting.

### Phase 0 addendum: `add_person`'s birth/death event literals (done during step 2)

Same gap again, one level up: `add_person`'s birth-event and death-event
dict literals (`app/genealogy_repository.py`) omitted `content`/`title`/
`source` entirely - `tests/test_add_person.py` even had a docstring
noting this ("no 'content' key at all... a different event shape than
add_event/update_event produce") as expected behavior. This is a hard
blocker for the Java port specifically, not just a cosmetic gap: the
`GenealogyRepository`'s `events` map is `Map<String, Event>`, and `Event`
is a plain record that always serializes all 11 canonical fields (that
was the whole point of Phase 0 - see "Data schema normalization" above).
There is no way to make a typed `Event` instance omit a declared field,
so this quirk had to be closed in Python before `PersonService.addPerson`
could be ported at all, not deferred like the `resolve_place`
house_number branch was.

Fixed by adding `content`/`title`/`source` (all `null`) to both dict
literals, in canonical field order. The now-inaccurate docstring in
`test_add_person.py` was updated to drop the claim. All three
`add_person_*` golden fixtures were regenerated and diffed against their
prior versions (only `content`/`title`/`source: null` added, nothing
else), then the full suite (36) and invariants check were reconfirmed
green before promoting.

**Takeaway for later steps:** `update_person`'s equivalent birth/death
event literals (`app/genealogy_repository.py`, both the "update existing
event" and "create new event" branches) have the same gap and will block
step 4 the same way - fix them then. Check any other event dict literal
against `CANONICAL_FIELDS` before porting the endpoint that writes it,
rather than assuming Phase 0's at-rest normalization already covers it.

### Phase 0 addendum: add_event's event literals and date shape (done during step 3)

Checking `add_event` against `CANONICAL_FIELDS` per the takeaway above
found five more live-write gaps, all fixed the same way (regenerate
affected fixtures, diff against the prior version to confirm only the
expected keys were added, rerun the full suite + invariants):

- **`add_event`'s main event literal** (`new_event`) was missing
  `description`/`source` entirely (9 of 11 canonical keys), and stored
  `event_data['date']` unnormalized - the previously-flagged gap
  (`web/event-editor.js` sends no `circa` key). Fixed by adding
  `description`/`source: null` and routing the date through a new
  `normalize_date()` helper (fills `year`/`month`/`day`/`circa` the same
  way `normalize_data_schema.py`'s `DATE_FIELDS` pass does). This is the
  fix the "Open items / TBD" date-shape entry already called for.
- **`resolve_place`'s `house_number`-given branch** (`add_event`/
  `update_event`'s `handle_place`) had the exact gap flagged as deferred
  in the `resolve_place` addendum above - fixed the same way
  (`parish_name`/`type: null` added; unlike the other branch, `type` has
  no equivalent to default to `'settlement'`, so it's `null`).
- **Three more auto-birth/marriage-event literals** `add_event` reaches
  through unconditionally or for birth events - `create_parent_marriage_if_needed`
  (also used by `add_relationship`, step 5, not yet ported),
  `sync_parents_to_birth_events`, and `sync_ages_to_birth_years` - were
  each missing `title`/`source`, and `sync_ages_to_birth_years`'s literal
  additionally put its birth-label text in `content` instead of
  `description` (every sibling auto-birth-event literal uses
  `description` for this - a genuine misplacement, not just a missing
  key, fixed by moving the text to `description` and setting `content: ''`
  to match).

Regenerated and diffed 13 fixtures (all 12 `add_event_*` plus
`update_event_swap_and_new_child_combined`, whose setup step calls
`add_event`) against their prior versions via a structural (not textual)
diff asserting every added key was one of the expected canonical keys
with a `null`/`false`/`'settlement'` value and nothing else changed. Full
suite (36) and invariants reconfirmed green before promoting.

**Takeaway for later steps:** `update_event` has its own, not-yet-fixed
copies of the date-shape and event-literal gaps (it doesn't call
`add_event`'s new `normalize_date()` helper) - fix it the same way when
step 4 is ported.

### Phase 0 addendum: add_event's new-person literals (done during step 3)

One more gap, this time on `Person` rather than `Event`/`Place`:
`add_event`'s two new-person-creation literals (for a brand-new
participant, and for a brand-new `parent_mother`/`parent_father`) were
each missing `tags`/`notes` entirely (6 of 8 canonical `Person` fields) -
confirmed against `add_event_birth_new_child_new_parents`'s
`persons.added` entries before this fix. Same blocker as the others:
`Person` is a plain record that always serializes every field. Fixed by
adding `'tags': [], 'notes': None` to both literals. Regenerated and
structurally diffed the 5 affected fixtures (only `add_event_*` scenarios
that create a new person) - only `tags`/`notes` added, nothing else
changed. Full suite + invariants reconfirmed green.

`update_event` has byte-identical duplicate copies of both literals
(same gap, not fixed here - same step 4 deferral as everything else in
this section).

### Phase 0 addendum: update_person's/update_event's own gaps (done during step 4)

Checking `update_person`/`update_event` against `CANONICAL_FIELDS`/the two
prior addenda's deferred items (as the step-3 takeaways called for) found
exactly the five gaps those takeaways predicted, all fixed the same way
(regenerate the 4 affected fixtures, structurally diff against the prior
version to confirm only the expected keys/values changed, rerun the full
36-test suite):

- **`update_person`'s birth/death event literals** (the "create new event"
  branch, mirroring `add_person`'s already-fixed version) were missing
  `content`/`title`/`source` - fixed by adding all three (`null`) in
  canonical order. Confirmed via `update_person_creates_new_events`.
- **`update_event`'s own `event['date'] = event_data['date']` assignment**
  wasn't routed through `normalize_date()` (unlike `add_event`, fixed in
  step 3) - fixed by calling it here too, closing the exact gap the step 3
  addendum flagged. Confirmed via `update_event_swap_participants`'s
  `after.date` gaining a `circa` key.
- **`update_event`'s new-participant and new-parent person literals**
  (byte-identical duplicates of `add_event`'s, per the prior addendum) were
  missing `tags`/`notes` - fixed the same way (`[]`/`null`). Confirmed via
  `update_event_new_child_new_parents`.
- **`update_event`'s birth-event and marriage-event auto-creation
  literals** (same duplicates) were missing `title`/`source` - fixed the
  same way. Confirmed via `update_event_new_child_new_parents` (marriage
  event) and `update_event_swap_and_new_child_combined` (birth event, via
  its `is_child_in_birth_event` path not needing a fresh one - the
  marriage event literal is what's exercised there).

No further gaps: `sync_parents_to_birth_events`/`sync_ages_to_birth_years`/
`create_parent_marriage_if_needed`'s literals were already fixed in step 3
and are called unchanged by `update_event`; `resolve_place`/`handle_place`
were already fixed in steps 2-3 and `update_event` calls the same
`handle_place`. This closes every item the step 2/3 addenda deferred to
step 4 - see JAVA_MIGRATION.md's Status entry for step 4 for the Java side.

### Phase 0 addendum: add_relationship's event literals (done during step 5)

Same gap, found in the one remaining unchecked endpoint: `add_relationship`'s
four event-creation literals (the byte-identical birth-event literal
shared by the parent/child/godparent branches, plus the spouse branch's
marriage-event literal) were each missing `content`/`title`/`source` - the
same 8-of-11-canonical-keys shape as `add_person`'s pre-fix birth/death
literals. Fixed the same way (`content`/`title`/`source: null` added, in
canonical order). Confirmed live in `add_relationship_parent_new_birth_event`
and `add_relationship_spouse_new_marriage_event` (the two fixtures whose
scenario actually creates a new event rather than reusing one); regenerated
and structurally diffed both against their prior versions (only the three
expected keys added), then the full 36-test suite reconfirmed green before
promoting. This was the last event/person-literal-creating endpoint that
has a golden-fixture-backed test today - `add_person`, `update_person`,
`add_event`, `update_event`, and `add_relationship` (steps 2-5) are now
all closed against `CANONICAL_FIELDS`, so every `tests/golden/*.json`
fixture round-trips through a canonical-shaped record. See "Open items /
TBD" for a step-6/8 scoping gap this surfaced (unrelated to this
addendum's own fix).

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
│       │   │   │   ├── DataProperties.java        # @ConfigurationProperties("data") — path to
│       │   │   │   │                               # genealogy_new_model.json
│       │   │   │   └── JacksonConfig.java          # JsonMapperBuilderCustomizer bean — SNAKE_CASE
│       │   │   │                                   # naming for the HTTP (Spring MVC) Jackson mapper,
│       │   │   │                                   # separate from GenealogyJsonMapper (file I/O only)
│       │   │   │
│       │   │   ├── model/                         # records for the canonical schema (see above)
│       │   │   │   ├── Person.java
│       │   │   │   ├── Event.java
│       │   │   │   ├── EventParticipation.java
│       │   │   │   ├── FamilyRelationship.java     # not yet in the live JSON (see its javadoc) —
│       │   │   │   │                                # kept for the step 5 add-relationship port
│       │   │   │   ├── Place.java
│       │   │   │   ├── FlexibleDate.java           # plain record — no custom (de)serializer needed
│       │   │   │   │                                # now that date shape is closed (see Phase 0 addendum)
│       │   │   │   ├── GenealogyDocument.java      # root JSON shape - persons/places/events/
│       │   │   │   │                                # event_participations + a raw metadata map
│       │   │   │   └── serialization/
│       │   │   │       └── GenealogyJsonMapper.java # builds the JsonMapper: SNAKE_CASE naming +
│       │   │   │                                     # a pretty printer matched byte-for-byte to
│       │   │   │                                     # Python's json.dump(indent=2) on Windows (CRLF)
│       │   │   │
│       │   │   ├── repository/
│       │   │   │   └── GenealogyRepository.java   # @Component, loads JSON on @PostConstruct,
│       │   │   │                                  # holds in-memory store, saves on write
│       │   │   │
│       │   │   ├── service/                       # business logic — Spring-free plain classes,
│       │   │   │   │                               # this is the layer golden tests exercise directly
│       │   │   │   ├── RequestValues.java          # shared raw-request-map (Map<String,Object>)
│       │   │   │   │                                # reading helpers, mirroring Python's dict.get()
│       │   │   │   │                                # presence/truthiness chains - used by every
│       │   │   │   │                                # service below instead of a strict DTO
│       │   │   │   ├── IdGenerator.java            # next P####/E####/PL####/EP#### id, from the
│       │   │   │   │                                # current max id in the live map
│       │   │   │   ├── PlaceResolver.java          # ports resolve_place/handle_place (both branches)
│       │   │   │   ├── EventLookup.java            # ports find_birth/death_event_for_person,
│       │   │   │   │                                # find_marriage_event_between
│       │   │   │   ├── ParentMarriageService.java  # ports create_parent_marriage_if_needed
│       │   │   │   ├── PersonService.java + AddPersonResult.java     # add/update/delete-person
│       │   │   │   ├── EventService.java + AddEventResult.java       # add/update/delete-event
│       │   │   │   ├── RelationshipService.java    # add-relationship
│       │   │   │   └── SyncService.java            # sync-event-dates, sync-ages, dedupe-witnesses
│       │   │   │
│       │   │   ├── web/                            # @RestController layer — thin, parses request,
│       │   │   │   ├── PersonController.java       # delegates to service, returns JSON
│       │   │   │   ├── EventController.java
│       │   │   │   └── RelationshipController.java
│       │   │   │
│       │   │   ├── dto/                            # request/response bodies where they diverge
│       │   │   │                                   # from the domain model — not needed so far,
│       │   │   │                                   # requests are raw maps (see RequestValues),
│       │   │   │                                   # responses are the AddXResult sealed interfaces
│       │   │   │                                   # living next to their service instead
│       │   │   │
│       │   │   ├── exception/
│       │   │   │   └── GlobalExceptionHandler.java # @ControllerAdvice — centralizes error→JSON
│       │   │   │                                   # mapping (server.py does this ad hoc per-handler).
│       │   │   │                                   # Not needed yet - add/add-event never throw for
│       │   │                                   # expected failures (see AddPersonResult's javadoc)
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
│               │                                    # the golden-parity burden; live HTTP smoke tests
│               │                                    # done manually per step so far - see Status)
│               └── golden/
│                   └── GoldenFileTestSupport.java    # sandboxes a copy of the real data file, snapshots
│                                                     # repository state before/after a service call,
│                                                     # diffs it, normalizes newly-created ids to
│                                                     # placeholders, and compares against a fixture in
│                                                     # ../../../tests/golden — reused as-is by every
│                                                     # service's test class (see PersonServiceTest,
│                                                     # EventServiceTest)
```

Note on the golden fixtures: Java tests reference `tests/golden/` **directly**
(no copy into `src/test/resources`). Single source of truth, zero drift risk.
The tradeoff is a relative-path coupling from the `java/` module out to the
repo-root `tests/` folder — acceptable since both live in the same repo for
the duration of the migration.

## Migration order

Simplest-first, to stand up the model/repository/test-harness scaffolding
before tackling harder logic:

1. **[Done]** `model/` + `repository/` (data model, JSON load/save) — no
   business logic yet. Exit criterion: the Spring Boot app boots, loads the
   real `data/genealogy_new_model.json` without error
   (`GenealogyApplicationTests`), and a no-op load→save round trip is
   byte-identical to the source file (`GenealogyRepositoryRoundTripTest`),
   proving the model + repository are lossless before any service logic is
   layered on. `FamilyRelationship.java` was added per the model/ layout
   below but isn't wired into the repository yet, since relationships
   aren't a top-level collection in the live JSON (see its javadoc) — it's
   there for step 5.
2. **[Done]** `add-person` (simplest endpoint, smallest golden fixture
   set). `service/PersonService.java` + `web/PersonController.java`,
   byte-for-byte against `tests/golden/add_person_*.json`
   (`PersonServiceTest`). Required two Phase 0 follow-up fixes in the
   Python reference first (see the addenda above).
3. **[Done]** `add-event` (birth/death/marriage/generic — larger surface,
   exercises parent/child sync logic from `improvements.txt` steps
   29–34). `service/EventService.java` + `web/EventController.java`,
   byte-for-byte against all 12 `tests/golden/add_event_*.json` fixtures
   (`EventServiceTest`). Required six more Phase 0 follow-up fixes first
   (see the addenda above). Introduced `RequestValues`, `EventLookup`,
   `ParentMarriageService` as shared `service/` components for reuse by
   later steps.
4. **[Done]** `update-person`, `update-event`. `service/PersonService.updatePerson`
   + `service/EventService.updateEvent`, wired into the existing
   `PersonController`/`EventController`, byte-for-byte against all 8
   `tests/golden/update_person_*.json`/`update_event_*.json` fixtures.
   Required the five prerequisite Python fixes flagged in "Open items /
   TBD" below (now resolved - see the step 4 Phase 0 addendum above).
5. **[Done]** `add-relationship`. `service/RelationshipService.java` +
   `web/RelationshipController.java`, byte-for-byte against all 4
   `tests/golden/add_relationship_*.json` fixtures. Required one
   prerequisite Python fix (see the step 5 Phase 0 addendum above).
6. **[Done]** `delete-person`, `delete-event`. `PersonService.deletePerson`
   + `EventService.deleteEvent`, wired into the existing
   `PersonController`/`EventController`, byte-for-byte against both
   `tests/golden/delete_person_cascade_and_preserve.json`/
   `delete_event_removes_participations.json` fixtures. No prerequisite
   Python fixes needed (see the step 6 Status entry above).
7. **[Done]** Document management: `add-document`, `update-document`,
   `delete-document`, `delete-document-page`, plus mirroring `/document/*`
   into `SpaRoutingController`. Unlike every prior step, this endpoint
   family lives entirely outside `GenealogyRepository`/
   `genealogy_new_model.json` - it's still implemented ad hoc in
   `server.py` (never extracted into `app/genealogy_repository.py`), reads
   and writes its own flat-map JSON file (`data/documents.json`,
   `Map<docId, Document>` - no `GenealogyDocument`-style wrapper), and
   manages binary page-image files on disk under `data/documents/`. Had
   **zero existing Python test coverage** before this step (no
   `tests/test_documents.py`), unlike every other endpoint family, which
   already had golden fixtures proving Python behavior before the Java
   port started - closed the same way as steps 2-6 (Python golden-fixture
   tests first, then port to Java against those fixtures).
   See "Document management port (step 7)" below for the full writeup.
8. Sync endpoints: `generate-parent-marriages`, `sync-event-dates-to-persons`,
   `sync-all-ages-to-birth-years`, `deduplicate-witnesses-godparents` -
   **needs scoping first, see "Open items / TBD"**: none of
   these four methods currently exist in `app/genealogy_repository.py` or
   `server.py`, despite being listed as live endpoints in CLAUDE.md.
9. `geneteka-import` (GEDCOM lookup/import was removed from the Python app -
   see the "Explicitly out of scope" note below - so there is no longer a
   `gedcom-lookup`/`gedcom-person` pair to port)

Each step is done when: the Java service produces byte-for-byte-equivalent
JSON (structurally) against every relevant fixture in `tests/golden/`.

## Document management port (step 7, done)

Documents turned out to be architecturally separate from every entity
ported so far - a different JSON file, a different id scheme, and
(uniquely) binary files on disk - so they needed their own mini version of
the Phase 0 groundwork rather than just slotting into the existing
`GenealogyRepository`/service pattern. See the step 7 Status entry above
for the condensed summary; this section is the detailed record of what was
found and built.

**What's there today** (`server.py`, `web/document-manager.js`,
`data/documents.json`, `data/documents/`):

- `data/documents.json` is a flat `{doc_id: document}` map - `doc_id` is
  `D##` (zero-padded to 2 digits via `f'D{next_num:02d}'`, e.g. `D01`,
  growing to 3+ digits past `D99` the same way Python's `:02d` format
  does), not the `P####`/`E####`/4-digit style used elsewhere.
- Each `document` has exactly 8 fields, always in the same order: `id,
  name, date, notes, tags, link, events, pages`. Checked directly against
  the live file (14 documents, 133 pages): every record already has the
  identical key set *and* key order, and every page has exactly
  `{filename, transcription}` - so, unlike `genealogy_new_model.json`
  before Phase 0, **no normalization pass is needed** before this can be a
  plain Java record; every code path that writes a document
  (`add_document`/`update_document`) already produces this exact shape.
- `document.date` is a **plain nullable integer** (a year, e.g. `1868`),
  not a `FlexibleDate` object like `events[*].date` - confirmed against
  the live file (13 ints, 1 null, 0 objects). The Java `Document` record
  must declare `Integer date`, not reuse `FlexibleDate`.
- `add_document` decodes base64 page payloads and writes each to
  `data/documents/{doc_id}-{n}.{ext}` (1-indexed); `delete_document`/
  `delete_document_page` remove those files from disk. This file I/O has
  no equivalent anywhere else in the migration so far (every other
  endpoint only ever touches the one JSON file).
- Reads already work against the Java backend for free: `/data/**` static
  serving (done in an earlier ad hoc step) already serves both
  `/data/documents.json` and `/data/documents/<filename>` - `web/app.js`'s
  `loadData()` and `document-manager.js`'s `<img src>` tags need nothing
  new. Only the four POST endpoints and the `/document/*` SPA route are
  missing.
- `SpaRoutingController`'s javadoc had flagged `/document/*` as
  deliberately unmirrored pending this step - now updated, see below.

**Java shapes built:**

- `model/Document.java` - record `(String id, String name, Integer date,
  String notes, List<String> tags, String link, List<String> events,
  List<DocumentPage> pages)` + the usual `@JsonAnySetter`/`@JsonAnyGetter`
  catch-all, matching every other model record.
- `model/DocumentPage.java` - record `(String filename, String
  transcription)`, same catch-all.
- No root wrapper record needed (unlike `GenealogyDocument`) - the file's
  root shape is just `Map<String, Document>`, loaded/saved directly via
  Jackson's `TypeReference<Map<String, Document>>` map-type support.
- `repository/DocumentRepository.java` - `@Component`, parallel to (not
  reusing) `GenealogyRepository`: own `@PostConstruct` load, own
  in-memory `Map<String, Document>`, own save. Reuses
  `GenealogyJsonMapper.create()` as-is for the CRLF/snake_case/indent-2
  formatting (it's already generic, not tied to `GenealogyDocument`) -
  the same `@PostConstruct`-load-once-at-startup model as
  `GenealogyRepository` turned out to fit fine, no complications from
  `data/documents.json` being far smaller (14 records) or sandboxing.
  Also owns the page-image directory (`data/documents/`, derived from the
  same path's parent), lazily `Files.createDirectories`-ing it on every
  `pagesDirectory()` call - mirrors `server.py`'s `_documents_dir()`
  (`os.makedirs(d, exist_ok=True)` on every access, not just at startup).
- `config/DocumentDataProperties.java` - a new `documents.file` property
  in `application.yml` rather than a second field on `DataProperties`,
  which would have broken every existing single-arg
  `new DataProperties(file)` call site
  (`GoldenFileTestSupport.freshRepository`, `StaticResourceConfig`, etc.).
- `IdGenerator.nextDocumentId` - the private `nextId` helper gained a
  configurable digit-width parameter (existing callers pass `4`
  unchanged) so documents could reuse the same max-id-plus-one logic with
  `server.py`'s older 2-digit `f'D{next_num:02d}'` counter instead of
  every other entity's 4-digit one.
- `service/DocumentService.java` + four result records
  (`AddDocumentResult`/`UpdateDocumentResult`/`DeleteDocumentResult`/
  `DeleteDocumentPageResult`) - kept one type per endpoint per this
  codebase's established convention, even though three of the four share
  a `{success, document}` shape (only `DeleteDocumentResult.Success` is
  bare `{success}`, matching `delete_document`'s Python return exactly).
  Ports `add_document`/`update_document`/`delete_document`/
  `delete_document_page` byte-for-byte, including the base64 decode/
  file-write and file-delete side effects - the one service in this
  codebase where a checked `IOException` (from `Files.write`/
  `Files.deleteIfExists`/`Files.createDirectories`) needed catching
  alongside the usual `RuntimeException`, since Python's blanket
  `except Exception` covers file errors for free but Jackson's own
  read/write calls elsewhere in this codebase are unchecked
  (`JacksonException extends RuntimeException` in Jackson 3).
- `web/DocumentController.java` - thin controller, same style as
  `PersonController`/`EventController`.
- `SpaRoutingController` now also mirrors `/document/**` in its
  `@GetMapping`, with the same bare-path exclusion `/person` already had
  (Python's `self.path.startswith('/document/')` requires the trailing
  slash, so bare `/document` still 404s even though Spring's
  `/document/**` pattern would otherwise match it).

**Testing built (Python golden fixtures first, matching steps 2-6's
discipline):**

1. `tests/test_documents.py` (7 tests) - golden-fixture coverage for
   add/update/delete-document and delete-document-page, using the
   existing `live_server` fixture (`tests/conftest.py` already copied
   `documents.json` and created an empty `data/documents` dir into every
   sandbox, so no harness change was needed there beyond adding
   `LiveServer.get_documents_state()` to fetch `/data/documents.json`).
   Every test adds its own fixture document via a setup `add-document`
   call rather than anchoring to a real row - see `tests/anchors.py`'s
   documents section for why (the sandbox's `data/documents/` starts
   empty on purpose, and real rows have no interesting cross-links worth
   anchoring to). Uses a few bytes of fake page data, base64-encoded -
   content is only decoded and written, never validated as a real image.
2. `tests/documents_golden_utils.py` - new, parallel to (not merged into)
   `golden_utils.py`: reuses its already-generic `dict_diff` directly for
   the single `{doc_id: document}` map, but needed its own
   `D_NEW_n`-placeholder/fixture-write logic since `golden_utils.py`'s
   `state_diff`/`_new_id_placeholders`/`ID_PLACEHOLDER_PREFIXES` are
   hardcoded to `genealogy_new_model.json`'s four collections.
3. Since `add_document`'s actual page *files* on disk aren't part of
   `documents.json` (only `pages[*].filename` is), `test_documents.py`
   also asserts directly against the sandbox's `data/documents/<filename>`
   bytes, alongside the golden-fixture check for the JSON side.
4. `java/.../service/DocumentServiceTest.java` (7 tests) - same role as
   `PersonServiceTest`/`EventServiceTest`, against the exact same
   `tests/golden/*.json` fixtures the Python tests wrote. Needed a new
   `golden/DocumentGoldenFileTestSupport.java` (a single-map parallel to
   `GoldenFileTestSupport`, which is hardcoded to `GenealogyRepository`'s
   four collections) rather than a generalization of the existing one -
   mirrors the Python-side `documents_golden_utils.py` split. Also reads
   real page-file bytes back from `repository.pagesDirectory()` to verify
   the write path, matching the Python test's disk assertion.
5. Live HTTP smoke test against a sandboxed copy, run manually (same
   pattern as every prior step): add-document with a real page write,
   `/document/<id>` → 200 `index.html`, bare `/document` → 404,
   update-document, delete-document-page removing the file from disk,
   delete-document removing the entry and confirming no trace of the id
   remains in the sandboxed `documents.json`, and the not-found path for
   all three id-taking endpoints.
6. `web/StaticAndSpaRoutingTest.java` updated: it had pinned the
   *pre-port* behavior as a passing regression test
   (`/document/foo` → 404, under a test named
   `spaRoutingExcludesBarePersonAndDocumentUrls`) - that assertion now
   checks bare `/document` (not `/document/foo`) 404s, and
   `/document/D01` was added to the "serves index.html" test alongside
   `/events`/`/person/**`.

All 42 Python tests and all 47 Java tests pass.

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
  `migrate_to_new_model.py`, `migrate_to_event_relationships.py` — these
  are one-off scripts, not part of the running server
- Any change to `web/` (frontend stays vanilla JS, talks to REST regardless
  of backend language)
- GEDCOM lookup/import (`/api/gedcom-lookup`, `/api/gedcom-person/<id>`,
  `convert_gedcom_to_model.py`, `enrich_from_gedcom.py`,
  `data/gedcom_model.json`) and the orphaned `generate_enrichment_queue.py`/
  `data/enrichment_queue.json` were removed from the Python app entirely
  (unused feature cleanup, done alongside this migration) - nothing left to
  port for either

## Toolchain decisions

- **Maven:** no system Maven install on the dev machine — generate the
  Maven Wrapper (`mvnw`/`mvnw.cmd`/`.mvn/wrapper/`) into `java/` so the
  build is self-contained (downloads its own Maven distribution on first
  run). Use `./mvnw ...` from `java/`, not a bare `mvn`.
- **Java version:** only JDK 26 is installed, not JDK 21. Build with JDK 26
  but set `<maven.compiler.release>21</maven.compiler.release>` in
  `pom.xml`, so the source is restricted to Java 21 language features
  without installing a second JDK.
- **groupId/artifactId:** `com.emal.genealogy` / `genealogy-service`.

## Open items / TBD

- Whether `java/` becomes the permanent home once Python is retired, or gets
  flattened to repo root at that point
- Whether to eventually copy `web/` into `src/main/resources/static/` for a
  single self-contained fat jar (deferred until Java is the sole backend)
- **[Done]** `/data/**` static file serving - was blocking the browser UI
  from loading any data at all against the Java backend; closed by
  `config/DataStaticResourceConfig.java`, see the Status entry above.
  The four `/api/*-document*` endpoints were closed by step 7 (see its
  Status entry above); `/api/geneteka-import` and `/api/save-data` were
  closed by the ad hoc Status entry just above the "Cutover gate" section.
- **CLAUDE.md lists four sync endpoints** (`/api/generate-parent-marriages`,
  `/api/sync-event-dates-to-persons`, `/api/sync-all-ages-to-birth-years`,
  `/api/deduplicate-witnesses-godparents`) as live `server.py` routes, and
  the migration order's step 8 was scoped assuming they exist - but neither
  `server.py` nor `app/genealogy_repository.py` currently define any of
  them (`grep` for each name/route turns up nothing). Either they were
  removed/renamed at some point and CLAUDE.md is stale (same situation as
  its already-noted orphaned `generate_enrichment_queue.py` consumer), or
  they live somewhere not yet checked. Needs a look before step 8 is
  scoped for real - if they genuinely don't exist, step 8 shrinks to
  whatever subset does, or drops out of the migration order entirely.
- **[Done]** Document management (`/api/add-document`,
  `/api/update-document`, `/api/delete-document`,
  `/api/delete-document-page`, `/document/*` SPA routing) - see "Document
  management port (step 7, done)" below and the step 7 Status entry
  above.
- **[Done]** `/api/save-data` and `/api/geneteka-import` - see the ad hoc
  Status entry above (just before "## Goal" was previously the last gap;
  now just before "## Cutover gate"). Every endpoint CLAUDE.md documents as
  live is now ported.
