package com.emal.genealogy.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNull;

import com.emal.genealogy.golden.GoldenFileTestSupport;
import com.emal.genealogy.golden.GoldenFileTestSupport.EntitySnapshot;
import com.emal.genealogy.model.Event;
import com.emal.genealogy.model.EventParticipation;
import com.emal.genealogy.repository.GenealogyRepository;
import java.io.IOException;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
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

    private static Map<String, Object> date(Integer year, Integer month, Integer day, boolean circa) {
        Map<String, Object> d = new LinkedHashMap<>();
        d.put("year", year);
        d.put("month", month);
        d.put("day", day);
        d.put("circa", circa);
        return d;
    }

    @Test
    void minimalPersonGetsAutoBirthEventOnly(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        PersonService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> payload = Map.of(
                "given_name", "TestMinimal",
                "surname", "Fixture",
                "gender", "M");
        AddPersonResult result = service.addPerson(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_person_minimal", result, before, after);

        AddPersonResult.Success success = assertInstanceOf(AddPersonResult.Success.class, result);
        assertEquals(1, success.createdEvents().size());
        Event birthEvent = after.events().get(success.createdEvents().get(0));
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
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("given_name", "TestFull");
        payload.put("surname", "Fixture");
        payload.put("maiden_name", "MaidenFixture");
        payload.put("gender", "F");
        payload.put("occupation", "seamstress");
        payload.put("tags", List.of("test"));
        payload.put("notes", "fixture notes");
        payload.put("birth_year_estimate", 1850);
        payload.put("death_year_estimate", 1920);
        payload.put("place_of_birth", EXISTING_PLACE_NAME);
        payload.put("place_of_death", "Nowa Wies AddPersonTestOnly");

        AddPersonResult result = service.addPerson(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_person_full_with_places", result, before, after);

        AddPersonResult.Success success = assertInstanceOf(AddPersonResult.Success.class, result);
        assertEquals(2, success.createdEvents().size());
        assertEquals(
                success.createdEvents().stream().map(id -> after.events().get(id).type()).collect(Collectors.toSet()),
                Set.of("birth", "death"));
        assertEquals(before.places().size() + 1, after.places().size());
        Event birthEvent = success.createdEvents().stream()
                .map(id -> after.events().get(id))
                .filter(e -> "birth".equals(e.type()))
                .findFirst()
                .orElseThrow();
        assertEquals(1850, birthEvent.date().year());
        assertEquals(true, birthEvent.date().circa());
        assertEquals("PL0001", birthEvent.placeId());
    }

    @Test
    void basicFieldUpdateHasNoEventSideEffects(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        PersonService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("person_id", UPDATE_PERSON_NO_EVENTS);
        payload.put("first_name", "UpdatedFirst");
        payload.put("last_name", "UpdatedLast");
        payload.put("gender", "M");
        payload.put("occupation", "farmer");
        payload.put("tags", List.of("updated"));
        payload.put("notes", "updated notes");

        UpdatePersonResult result = service.updatePerson(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("update_person_basic_fields_no_events", result, before, after);

        UpdatePersonResult.Success success = assertInstanceOf(UpdatePersonResult.Success.class, result);
        assertEquals(List.of(), success.updatedEvents());
        assertEquals("UpdatedFirst", success.person().firstName());
        assertEquals(before.events(), after.events());
    }

    @Test
    void nullPlaceOnPersonWithExistingEventsStillMarksThemUpdated(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        PersonService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("person_id", UPDATE_PERSON_HAS_EVENTS);
        payload.put("place_of_birth", null);
        payload.put("place_of_death", null);

        UpdatePersonResult result = service.updatePerson(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("update_person_null_place_marks_events_updated", result, before, after);

        UpdatePersonResult.Success success = assertInstanceOf(UpdatePersonResult.Success.class, result);
        assertEquals(Set.of(UPDATE_PERSON_BIRTH_EVENT, UPDATE_PERSON_DEATH_EVENT), Set.copyOf(success.updatedEvents()));
        for (String eventId : success.updatedEvents()) {
            assertEquals(before.events().get(eventId), after.events().get(eventId));
        }
    }

    @Test
    void createsBirthAndDeathEventsWhenNoneExist(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        PersonService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("person_id", UPDATE_PERSON_NO_EVENTS);
        payload.put("birth_date", date(1852, null, null, true));
        payload.put("place_of_birth", "UpdatePersonTestBirthPlace");
        payload.put("death_date", date(1930, null, null, true));
        payload.put("place_of_death", "UpdatePersonTestDeathPlace");

        UpdatePersonResult result = service.updatePerson(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("update_person_creates_new_events", result, before, after);

        UpdatePersonResult.Success success = assertInstanceOf(UpdatePersonResult.Success.class, result);
        assertEquals(2, success.updatedEvents().size());
        assertEquals(before.places().size() + 2, after.places().size());
    }

    @Test
    void syncsDateAndPlaceIntoExistingEvents(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        PersonService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("person_id", UPDATE_PERSON_HAS_EVENTS);
        payload.put("birth_date", date(1799, 6, 1, false));
        payload.put("place_of_birth", EXISTING_PLACE_NAME);
        payload.put("death_date", date(1870, null, null, true));
        payload.put("place_of_death", EXISTING_PLACE_NAME);

        UpdatePersonResult result = service.updatePerson(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("update_person_syncs_existing_events", result, before, after);

        UpdatePersonResult.Success success = assertInstanceOf(UpdatePersonResult.Success.class, result);
        assertEquals(Set.of(UPDATE_PERSON_BIRTH_EVENT, UPDATE_PERSON_DEATH_EVENT), Set.copyOf(success.updatedEvents()));
        assertEquals(before.events().size(), after.events().size());
        assertEquals(1799, after.events().get(UPDATE_PERSON_BIRTH_EVENT).date().year());
        assertEquals(1870, after.events().get(UPDATE_PERSON_DEATH_EVENT).date().year());
        assertEquals("PL0001", after.events().get(UPDATE_PERSON_BIRTH_EVENT).placeId());
    }

    @Test
    void nonexistentPersonFailsCleanly(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        PersonService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> payload = Map.of("person_id", NONEXISTENT_PERSON_ID, "first_name", "X");

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
        DeletePersonResult result = service.deletePerson(Map.of("person_id", DELETE_PERSON_ID));
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("delete_person_cascade_and_preserve", result, before, after);

        DeletePersonResult.Success success = assertInstanceOf(DeletePersonResult.Success.class, result);
        assertEquals(0, success.deletedRelationships());
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
        DeletePersonResult result = service.deletePerson(Map.of("person_id", NONEXISTENT_PERSON_ID));
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        assertEquals(new DeletePersonResult.Failure("Person not found"), result);
        assertEquals(before, after);
    }
}
