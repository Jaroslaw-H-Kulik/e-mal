# Real HTTP 400s for required-field validation

## Context

`AddPersonRequest`'s compact constructor silently turns a missing `givenName`/
`surname` into `""` rather than rejecting the request. That's one instance of
a broader pattern: every request record in `com.emal.genealogy.service`
either silently defaults missing fields or (for a few endpoints, e.g.
`AddRelationshipRequest`) throws a `NoSuchElementException` mirroring
Python's `KeyError`, which the try/catch in each service turns into a
`Failure` inside an HTTP 200. That convention is documented on purpose in
`PersonController`'s javadoc: it mirrors the old `server.py`, which never
used status codes to signal failure.

We own every caller (`web/*.js` is the only client), so the plan is to stop
treating "required field missing" as a runtime condition the service has to
handle, and instead reject it at the HTTP boundary as a real `400`, using
Bean Validation. The service layer should be able to trust that a request
that reached it already has its required fields — that's the actual
simplification: one validation mechanism instead of a mix of silent
defaults, hand-rolled `requireField` throws, and inline `== null` checks
scattered through 6 services.

This intentionally changes behavior for the fields identified below, and
retires the one existing test (`RelationshipServiceTest.missingRoleKeyFailsCleanly`)
that pins the old Python-KeyError-shaped behavior — replacing it with a
controller-level test asserting the new 400. That test's javadoc already
says it mirrors a specific Python test; moving off that convention for this
field is the point of the change, not an accident.

## What's actually required vs. legitimately optional

Checked each field against the UI (`web/index.html`'s `required` attributes,
`document-manager.js`'s own `if (!name) { alert(...) }` guard, and
`event-editor.js` always setting `type` programmatically) and against
existing service logic, to avoid turning genuinely-optional domain fields
(partial dates, "Unknown" gender as a real selectable value, blank→null
place/notes collapsing) into spurious 400s. Only fields that are (a) always
sent by every real caller and (b) meaningless if absent become required:

| Request | New `@NotBlank` fields | Stays optional (unchanged) |
|---|---|---|
| `AddPersonRequest` | `givenName`, `surname`, `gender` | maidenName, occupation, tags, notes, both year estimates, both places |
| `UpdatePersonRequest` | `personId`, `firstName`, `lastName`, `gender` | maidenName, occupation, tags, notes, both dates, both places |
| `AddEventRequest` | `type` | date, placeName, houseNumber, title, notes, tags, links, content, participants |
| `UpdateEventRequest` | `eventId`, `type` | same optional set as above |
| `EventParticipantRequest` | `role` | existingPersonId/firstName/lastName/etc. — mutually-exclusive-optional shape, untouched |
| `AddRelationshipRequest` | `basePersonId`, `targetPersonId`, `relationshipType`, `role` | — (all 4 already documented as genuinely required) |
| `DeletePersonRequest` / `DeleteEventRequest` / `DeleteDocumentRequest` | their single id field | — |
| `DeleteDocumentPageRequest` | `docId`, `filename` | — (this also fixes a latent NPE: `DocumentService.deleteDocumentPage` currently calls `pagesDirectory.resolve(filename)` with no null check) |
| `AddDocumentRequest` / `UpdateDocumentRequest` | `name` (per document-manager.js's own required-check); `pages` gets `@Valid` cascade | date, notes, tags, link, events |
| `AddDocumentPageRequest` | `data` | ext (defaults to "jpg", unchanged) |
| `UpdateDocumentPageRequest` | `filename` | transcription |

`EventParentRequest`, `DateRequest`, and `GenealogyDocument` (the raw
`/api/save-data` body) are untouched — no clear required field in the first
two, and the third is a bulk whole-document overwrite outside this scope.

## Implementation

1. **Add the dependency**: `spring-boot-starter-validation` to `pom.xml`.

2. **Annotate the fields in the table above** with `jakarta.validation.constraints.NotBlank`
   (custom `message = "..."` per field, e.g. `"givenName is required"`), and
   remove the now-redundant compact-constructor line that used to default
   that same field (e.g. `AddPersonRequest.java:30-32`'s givenName/surname/gender
   lines go away entirely; the blank-to-null and list-default lines for the
   fields that stay optional are untouched). Where a required field lives in
   a nested list element (`AddEventRequest.participants`, `AddDocumentRequest.pages`,
   `UpdateDocumentRequest.pages`), add `@Valid` to the list field itself so
   validation cascades into the list elements — plain `@Valid` on the
   controller parameter does not do this automatically.

3. **Add `@Valid`** to every `@RequestBody` parameter in `PersonController`,
   `EventController`, `RelationshipController`, and `DocumentController`
   (11 endpoints total). `DataController.saveData` is untouched.

4. **New global handler** — `com.emal.genealogy.web.ApiError` (a
   `record ApiError(boolean success, String error)`) and
   `com.emal.genealogy.web.ValidationExceptionHandler`, a
   `@RestControllerAdvice` with:
   - `@ExceptionHandler(MethodArgumentNotValidException.class)` → `400` with
     an `ApiError` body joining each field's message (so the frontend's
     existing `result.success`/`result.error` reads still work, just now
     alongside a real status code instead of always-200).
   - `@ExceptionHandler(HttpMessageNotReadableException.class)` → `400` with
     a generic `ApiError(false, "Malformed request body")`, for genuinely
     unparseable JSON (wrong types, truncated body).

5. **Simplify the services** now that the controller boundary guarantees
   non-blank required fields:
   - `RelationshipService`: delete `requireField`/`NoSuchElementException`
     and its 4 call sites; read `relData.basePersonId()` etc. directly. The
     "id doesn't exist in the map" checks (a different failure — well-formed
     but referencing nothing) stay as `Failure`s, unchanged.
   - `DocumentService.addDocument`: delete `requireField`, use
     `pageData.data()` directly.
   - `PersonService.updatePerson`/`deletePerson`, `EventService.updateEvent`/
     `deleteEvent`, `DocumentService.updateDocument`/`deleteDocument`/
     `deleteDocumentPage`: simplify `x == null || !map.containsKey(x)` down
     to `!map.containsKey(x)` (the null half is now unreachable).

6. **Update javadocs** that assert the old always-200 contract:
   `PersonController`, `EventController`, `RelationshipController`,
   `DocumentController` (each says "see PersonController's javadoc for the
   same shape/status-code rationale" — update the one source doc, the
   others already just point at it), plus the per-field rationale comments
   in the request records being changed (e.g. `AddRelationshipRequest`'s
   javadoc about `requireField` mirroring Python KeyError).

## Tests

- Convert `RelationshipServiceTest.missingRoleKeyFailsCleanly` into a new
  `RelationshipControllerTest` (new file, under
  `src/test/java/com/emal/genealogy/web/`, following
  `DataControllerTest`'s `@SpringBootTest(webEnvironment = RANDOM_PORT)` +
  `TestRestTemplate` pattern) asserting `POST /api/add-relationship` with a
  missing `role` returns `400` and an error body mentioning `role`. Remove
  the old service-level test (a `null` `role` can no longer reach the
  service through the HTTP path this test is meant to represent).
- Add 2-3 more representative controller tests alongside it, not one per
  endpoint: `POST /api/add-person` missing `givenName` → 400; `POST
  /api/delete-document-page` missing `filename` → 400 (covers the NPE-bug
  fix specifically).
- Run the full suite (`./mvnw test`, or the Windows `mvnw.cmd test`, from
  repo root) to confirm nothing else relied on the removed defaults.

## Verification

- `mvnw.cmd test` from repo root — full suite green, including the
  new/changed controller tests.
- Manual smoke check with the server running: POST to `/api/add-person`
  with `given_name` omitted should now come back `400` with
  `{"success":false,"error":"givenName is required"}`-shaped body instead
  of silently creating a nameless person.
