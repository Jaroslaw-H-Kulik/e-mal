package com.emal.genealogy.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

import com.emal.genealogy.golden.GoldenFileTestSupport;
import com.emal.genealogy.golden.GoldenFileTestSupport.EntitySnapshot;
import com.emal.genealogy.model.Event;
import com.emal.genealogy.model.EventParticipation;
import com.emal.genealogy.model.FlexibleDate;
import com.emal.genealogy.model.Person;
import com.emal.genealogy.repository.GenealogyRepository;
import java.io.IOException;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Layer 1 golden-master tests for PersonService.addPerson - the Java
 * equivalent of tests/test_add_person.py, run directly against the
 * service (no HTTP, matching the "service tests carry the golden-parity
 * burden" plan in JAVA_MIGRATION.md), against the exact same
 * tests/golden/*.json fixtures the Python tests use as the oracle.
 */
class PersonServiceTest {

    private static final IdGenerator ID_GENERATOR = new IdGenerator();
    private static final PlaceResolver PLACE_RESOLVER = new PlaceResolver(ID_GENERATOR);
    private static final EventLookup EVENT_LOOKUP = new EventLookup();

    // Matches tests/anchors.py::EXISTING_PLACE_NAME (resolves to PL0001 in the real dataset).
    private static final String EXISTING_PLACE_NAME = "Małyszyn";

    // tests/anchors.py constants this file's update-person scenarios pin against.
    private static final String UPDATE_PERSON_NO_EVENTS = "P0012";
    private static final String UPDATE_PERSON_HAS_EVENTS = "P0001";
    private static final String UPDATE_PERSON_BIRTH_EVENT = "E0539";
    private static final String UPDATE_PERSON_DEATH_EVENT = "E0543";
    private static final String NONEXISTENT_PERSON_ID = "P9999";
    private static final String DELETE_PERSON_ID = "P0011";

    private static PersonService newService(GenealogyRepository repository) {
        return new PersonService(repository, ID_GENERATOR, PLACE_RESOLVER, EVENT_LOOKUP);
    }

    private static DateRequest date(Integer year, Integer month, Integer day, boolean circa) {
        return new DateRequest(year, month, day, circa);
    }

    /** Round-trips a stored event's date back into a request-shaped DateRequest, for "resend unchanged" tests. */
    private static DateRequest dateRequest(FlexibleDate date) {
        return date == null ? null : new DateRequest(date.year(), date.month(), date.day(), date.circa());
    }

    private static UpdatePersonRequest updateRequest(
            Person person, DateRequest birthDate, String placeOfBirth, DateRequest deathDate, String placeOfDeath) {
        return new UpdatePersonRequest(
                person.id(), person.firstName(), person.lastName(), person.maidenName(), person.gender(),
                person.occupation(), person.tags(), person.notes(), birthDate, placeOfBirth, deathDate, placeOfDeath);
    }

    @Test
    void minimalPersonGetsAutoBirthEventOnly(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        PersonService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        AddPersonRequest payload = new AddPersonRequest(
                "TestMinimal", "Fixture", "M", null, null, null, null, null, null, null, null);
        AddPersonResult result = service.addPerson(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_person_minimal", result, before, after);

        AddPersonResult.Success success = assertInstanceOf(AddPersonResult.Success.class, result);
        assertEquals(1, success.newEvents().size());
        Event birthEvent = after.events().get(success.newEvents().keySet().iterator().next());
        assertEquals("birth", birthEvent.type());
        assertNull(birthEvent.date());
        assertNull(birthEvent.placeId());
        assertNull(success.person().occupation());
        assertEquals(List.of(), success.person().tags());
        assertNull(success.person().notes());
    }

    @Test
    void fullPersonCreatesBirthAndDeathEventsWithPlaces(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        PersonService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        AddPersonRequest payload = new AddPersonRequest(
                "TestFull", "Fixture", "F", "MaidenFixture", "seamstress", List.of("test"), "fixture notes",
                1850, 1920, EXISTING_PLACE_NAME, "Nowa Wies AddPersonTestOnly");

        AddPersonResult result = service.addPerson(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_person_full_with_places", result, before, after);

        AddPersonResult.Success success = assertInstanceOf(AddPersonResult.Success.class, result);
        assertEquals(2, success.newEvents().size());
        assertEquals(
                success.newEvents().keySet().stream().map(id -> after.events().get(id).type()).collect(Collectors.toSet()),
                Set.of("birth", "death"));
        assertEquals(before.places().size() + 1, after.places().size());
        Event birthEvent = success.newEvents().keySet().stream()
                .map(id -> after.events().get(id))
                .filter(e -> "birth".equals(e.type()))
                .findFirst()
                .orElseThrow();
        assertEquals(1850, birthEvent.date().year());
        assertEquals(true, birthEvent.date().circa());
        assertEquals("PL0001", birthEvent.placeId());
    }

    /**
     * Java-only coverage (no golden fixture - see PersonService's javadoc
     * and JAVA_MIGRATION.md's update-person divergence entry): resending a
     * person's real current birth/death date+place unchanged, alongside
     * genuinely changed basic fields, must touch no events at all. Replaces
     * the old presence-based basicFieldUpdateHasNoEventSideEffects test,
     * whose partial payload shape is no longer how this endpoint works.
     */
    @Test
    void resendingUnchangedDatesAndPlacesTouchesNoEvents(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        PersonService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Person currentPerson = before.persons().get(UPDATE_PERSON_HAS_EVENTS);
        Event currentBirth = before.events().get(UPDATE_PERSON_BIRTH_EVENT);
        Event currentDeath = before.events().get(UPDATE_PERSON_DEATH_EVENT);
        String birthPlaceName = currentBirth.placeId() == null ? null : before.places().get(currentBirth.placeId()).name();
        String deathPlaceName = currentDeath.placeId() == null ? null : before.places().get(currentDeath.placeId()).name();

        UpdatePersonRequest payload = new UpdatePersonRequest(
                UPDATE_PERSON_HAS_EVENTS, "UpdatedFirst", "UpdatedLast", currentPerson.maidenName(), "M",
                "farmer", List.of("updated"), "updated notes",
                dateRequest(currentBirth.date()), birthPlaceName, dateRequest(currentDeath.date()), deathPlaceName);

        UpdatePersonResult result = service.updatePerson(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        UpdatePersonResult.Success success = assertInstanceOf(UpdatePersonResult.Success.class, result);
        assertEquals(List.of(), success.updatedEvents());
        assertEquals("UpdatedFirst", success.person().firstName());
        assertEquals(before.events(), after.events());
        assertEquals(before.places(), after.places());
    }

    /**
     * Java-only coverage (no golden fixture): changing only the birth date/
     * place while resending the death date/place unchanged must report and
     * mutate the birth event only - the death event stays untouched.
     * Replaces the old nullPlaceOnPersonWithExistingEventsStillMarksThemUpdated
     * test, which pinned the presence-based quirk this change deliberately
     * removes (an event used to be marked "updated" even when nothing
     * inside it actually changed).
     */
    @Test
    void onlyGenuinelyChangedLifeEventIsMarkedUpdated(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        PersonService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Person currentPerson = before.persons().get(UPDATE_PERSON_HAS_EVENTS);
        Event currentDeath = before.events().get(UPDATE_PERSON_DEATH_EVENT);
        String deathPlaceName = currentDeath.placeId() == null ? null : before.places().get(currentDeath.placeId()).name();

        UpdatePersonRequest payload = updateRequest(
                currentPerson, date(1799, 6, 1, false), EXISTING_PLACE_NAME,
                dateRequest(currentDeath.date()), deathPlaceName);

        UpdatePersonResult result = service.updatePerson(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        UpdatePersonResult.Success success = assertInstanceOf(UpdatePersonResult.Success.class, result);
        assertEquals(List.of(UPDATE_PERSON_BIRTH_EVENT), success.updatedEvents());
        assertEquals(1799, after.events().get(UPDATE_PERSON_BIRTH_EVENT).date().year());
        assertEquals(currentDeath, after.events().get(UPDATE_PERSON_DEATH_EVENT));
    }

    /**
     * Java-only coverage (no golden fixture): a new capability this change
     * adds as a side effect of switching to change-detection - clearing an
     * existing place by sending null now actually clears it (the old
     * presence+truthy-gated code could never clear a place, only add/
     * overwrite with a truthy value).
     */
    @Test
    void clearingAnExistingPlaceRemovesItFromEvent(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        PersonService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Person currentPerson = before.persons().get(UPDATE_PERSON_HAS_EVENTS);
        Event currentBirth = before.events().get(UPDATE_PERSON_BIRTH_EVENT);
        Event currentDeath = before.events().get(UPDATE_PERSON_DEATH_EVENT);
        assertNotNull(currentBirth.placeId());
        String deathPlaceName = currentDeath.placeId() == null ? null : before.places().get(currentDeath.placeId()).name();

        UpdatePersonRequest payload = updateRequest(
                currentPerson, dateRequest(currentBirth.date()), null,
                dateRequest(currentDeath.date()), deathPlaceName);

        UpdatePersonResult result = service.updatePerson(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        UpdatePersonResult.Success success = assertInstanceOf(UpdatePersonResult.Success.class, result);
        assertEquals(List.of(UPDATE_PERSON_BIRTH_EVENT), success.updatedEvents());
        assertNull(after.events().get(UPDATE_PERSON_BIRTH_EVENT).placeId());
        assertEquals(currentBirth.date(), after.events().get(UPDATE_PERSON_BIRTH_EVENT).date());
        assertEquals(currentDeath, after.events().get(UPDATE_PERSON_DEATH_EVENT));
    }

    @Test
    void createsBirthAndDeathEventsWhenNoneExist(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        PersonService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        UpdatePersonRequest payload = updateRequest(
                before.persons().get(UPDATE_PERSON_NO_EVENTS),
                date(1852, null, null, true), "UpdatePersonTestBirthPlace",
                date(1930, null, null, true), "UpdatePersonTestDeathPlace");

        UpdatePersonResult result = service.updatePerson(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("update_person_creates_new_events", result, before, after);

        UpdatePersonResult.Success success = assertInstanceOf(UpdatePersonResult.Success.class, result);
        assertEquals(2, success.updatedEvents().size());
        assertEquals(before.places().size() + 2, after.places().size());
    }

    /**
     * Java-only coverage (no golden fixture - see the javadoc on
     * PersonService.syncLifeEvent): this scenario's expected output now
     * genuinely diverges from the old shared
     * update_person_syncs_existing_events.json fixture, which is left
     * untouched on disk for Python's unchanged test_update_person.py.
     * P0001's birth event (E0539) already has a "Małyszyn" place
     * (PL0053, one of ~80 same-named place records in this dataset) - the
     * old fixture pinned resolveByNameOnly's lossy id-collapsing (silently
     * becoming PL0001 on every save); this test instead pins the corrected
     * behavior: the date change (1785 -> 1799) is detected and applied, but
     * since the *place name* didn't change, PL0053 is preserved rather than
     * collapsed. The death event (E0543) has no place before this call, so
     * assigning "Małyszyn" there is a genuine change and correctly resolves
     * to PL0001 (nothing to preserve).
     */
    @Test
    void syncsDateIntoExistingEventsAndPreservesUnchangedPlaceIdentity(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        PersonService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Event currentBirth = before.events().get(UPDATE_PERSON_BIRTH_EVENT);
        Event currentDeath = before.events().get(UPDATE_PERSON_DEATH_EVENT);
        assertEquals("PL0053", currentBirth.placeId());
        assertNull(currentDeath.placeId());

        UpdatePersonRequest payload = updateRequest(
                before.persons().get(UPDATE_PERSON_HAS_EVENTS),
                date(1799, 6, 1, false), EXISTING_PLACE_NAME,
                date(1870, null, null, true), EXISTING_PLACE_NAME);

        UpdatePersonResult result = service.updatePerson(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        UpdatePersonResult.Success success = assertInstanceOf(UpdatePersonResult.Success.class, result);
        assertEquals(Set.of(UPDATE_PERSON_BIRTH_EVENT, UPDATE_PERSON_DEATH_EVENT), Set.copyOf(success.updatedEvents()));
        assertEquals(before.events().size(), after.events().size());
        assertEquals(1799, after.events().get(UPDATE_PERSON_BIRTH_EVENT).date().year());
        assertEquals(1870, after.events().get(UPDATE_PERSON_DEATH_EVENT).date().year());
        assertEquals("PL0053", after.events().get(UPDATE_PERSON_BIRTH_EVENT).placeId());
        assertEquals("PL0001", after.events().get(UPDATE_PERSON_DEATH_EVENT).placeId());
    }

    @Test
    void nonexistentPersonFailsCleanly(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        PersonService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        UpdatePersonRequest payload = new UpdatePersonRequest(
                NONEXISTENT_PERSON_ID, "X", null, null, null, null, null, null, null, null, null, null);

        UpdatePersonResult result = service.updatePerson(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        assertEquals(new UpdatePersonResult.Failure("Person not found"), result);
        assertEquals(before, after);
    }

    @Test
    void deletePersonCascadesEmptyEventsButPreservesOthers(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        PersonService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        DeletePersonResult result = service.deletePerson(new DeletePersonRequest(DELETE_PERSON_ID));
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("delete_person_cascade_and_preserve", result, before, after);

        DeletePersonResult.Success success = assertInstanceOf(DeletePersonResult.Success.class, result);
        assertFalse(after.persons().containsKey(DELETE_PERSON_ID));
        assertEquals(Set.of("E0004", "E0653"), Set.copyOf(success.deletedEvents()));

        for (String eventId : List.of("E0555", "E0651", "E0776")) {
            assertEquals(before.events().get(eventId), after.events().get(eventId));
            boolean stillLinked = after.eventParticipations().values().stream()
                    .anyMatch(ep -> ep.eventId().equals(eventId) && ep.personId().equals(DELETE_PERSON_ID));
            assertFalse(stillLinked);
        }

        for (String eventId : List.of("E1415", "E1416")) {
            Set<String> remainingRoles = after.eventParticipations().values().stream()
                    .filter(ep -> ep.eventId().equals(eventId))
                    .map(EventParticipation::role)
                    .collect(Collectors.toSet());
            assertFalse(remainingRoles.contains("groom"));
        }
    }

    @Test
    void deletePersonNonexistentFailsCleanly(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        PersonService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        DeletePersonResult result = service.deletePerson(new DeletePersonRequest(NONEXISTENT_PERSON_ID));
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        assertEquals(new DeletePersonResult.Failure("Person not found"), result);
        assertEquals(before, after);
    }
}
