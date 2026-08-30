package com.emal.genealogy.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.emal.genealogy.golden.GoldenFileTestSupport;
import com.emal.genealogy.golden.GoldenFileTestSupport.EntitySnapshot;
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
 * Layer 1 golden-master tests for EventService.addEvent - the Java
 * equivalent of tests/test_add_event.py, run directly against the
 * service, against the exact same tests/golden/add_event_*.json fixtures
 * the Python tests use as the oracle. See PersonServiceTest for the
 * harness pattern.
 */
class EventServiceTest {

    // tests/anchors.py constants this file's scenarios pin against.
    private static final String PLAIN_BIRTH_CHILD = "P0012";
    private static final String PLAIN_BIRTH_FATHER = "P0001";
    private static final String PLAIN_BIRTH_MOTHER = "P0002";
    private static final String MIXED_PARENT_EXISTING_FATHER = "P0038";
    private static final String CONFLICTING_FATHER = "P0046";
    private static final String UNRELATED_FEMALE = "P0033";
    private static final String UNRELATED_MALE = "P0038";
    private static final String SYNC_GROOM = "P0073";
    private static final String SYNC_GROOM_FATHER = "P0081";
    private static final String SYNC_BRIDE = "P0089";
    private static final String PLAIN_MARRIAGE_GROOM = "P0009";
    private static final String PLAIN_MARRIAGE_BRIDE = "P0021";
    private static final String PLAIN_DEATH_DECEASED = "P0012";
    private static final String PLAIN_GENERIC_PARTICIPANT = "P0033";
    private static final String EXISTING_PLACE_NAME = "Małyszyn";
    private static final String EXISTING_PLACE_HOUSE_NUMBER = "16";
    private static final String NEW_PLACE_NAME = "Nowa Wies TestOnly";
    private static final String NEW_PLACE_HOUSE_NUMBER = "5";

    // tests/anchors.py constants this file's update-event scenarios pin against.
    private static final String SWAP_EVENT = "E0013";
    private static final String SWAP_EVENT_PLACE_NAME = "Małyszyn";
    private static final String SWAP_EVENT_PLACE_HOUSE_NUMBER = "21";
    private static final String SWAP_KEEP_DECEASED = "P0020";
    private static final String SWAP_KEEP_WITNESS = "P0015";
    private static final String SWAP_DROP_WITNESS = "P0632";
    private static final String SWAP_NEW_WITNESS = "P0022";
    private static final String UPDATE_NEW_CHILD_EVENT = "E1746";
    private static final String COMBINED_SETUP_CHILD = "P0055";
    private static final String COMBINED_WITNESS_1 = "P0068";
    private static final String COMBINED_WITNESS_2 = "P0043";
    private static final String NONEXISTENT_EVENT_ID = "E9999";
    private static final String DELETE_EVENT_ID = "E0055";

    private record Link(String personId, String role) {
    }

    private static EventService newService(GenealogyRepository repository) {
        IdGenerator idGenerator = new IdGenerator();
        PlaceResolver placeResolver = new PlaceResolver(idGenerator);
        EventLookup eventLookup = new EventLookup();
        ParentMarriageService parentMarriageService = new ParentMarriageService(idGenerator, eventLookup);
        return new EventService(repository, idGenerator, placeResolver, eventLookup, parentMarriageService);
    }

    private static Map<String, Object> date(Integer year, Integer month, Integer day) {
        Map<String, Object> d = new LinkedHashMap<>();
        d.put("year", year);
        d.put("month", month);
        d.put("day", day);
        return d;
    }

    private static Map<String, Object> date(Integer year, Integer month, Integer day, boolean circa) {
        Map<String, Object> d = date(year, month, day);
        d.put("circa", circa);
        return d;
    }

    private static Map<String, Object> participant(String existingPersonId, String role) {
        Map<String, Object> p = new LinkedHashMap<>();
        p.put("existing_person_id", existingPersonId);
        p.put("role", role);
        return p;
    }

    private static Set<Link> linkedTo(EntitySnapshot after, String eventId) {
        return after.eventParticipations().values().stream()
                .filter(ep -> ep.eventId().equals(eventId))
                .map(ep -> new Link(ep.personId(), ep.role()))
                .collect(Collectors.toSet());
    }

    @Test
    void plainBirthAllExistingParticipants(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "birth");
        payload.put("date", date(1850, null, null));
        payload.put("notes", "Layer 1 golden-master test fixture");
        payload.put("participants", List.of(
                participant(PLAIN_BIRTH_CHILD, "child"),
                participant(PLAIN_BIRTH_FATHER, "father"),
                participant(PLAIN_BIRTH_MOTHER, "mother")));

        AddEventResult result = service.addEvent(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_event_plain_birth_existing_participants", result, before, after);

        AddEventResult.Success success = assertInstanceOf(AddEventResult.Success.class, result);
        assertEquals(List.of(), success.newPersons());
    }

    @Test
    void birthWithBrandNewChildAndNewParents(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> child = new LinkedHashMap<>();
        child.put("first_name", "TestChild");
        child.put("last_name", "Fixture");
        child.put("role", "child");
        Map<String, Object> mother = new LinkedHashMap<>();
        mother.put("first_name", "TestMother");
        mother.put("last_name", "Fixture");
        Map<String, Object> father = new LinkedHashMap<>();
        father.put("first_name", "TestFather");
        father.put("last_name", "Fixture");
        child.put("parent_mother", mother);
        child.put("parent_father", father);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "birth");
        payload.put("date", date(1880, 5, 1));
        payload.put("notes", "Layer 1 golden-master test fixture");
        payload.put("participants", List.of(child));

        AddEventResult result = service.addEvent(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_event_birth_new_child_new_parents", result, before, after);

        AddEventResult.Success success = assertInstanceOf(AddEventResult.Success.class, result);
        assertEquals(3, success.newPersons().size());
        Set<String> linkedRoles = linkedTo(after, success.event().id()).stream().map(Link::role).collect(Collectors.toSet());
        assertEquals(Set.of("child", "mother", "father"), linkedRoles);
        assertEquals("child: TestChild Fixture", success.event().content());
    }

    @Test
    void newChildMixedNewAndExistingParent(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> child = new LinkedHashMap<>();
        child.put("first_name", "TestChild4");
        child.put("last_name", "Fixture");
        child.put("role", "child");
        Map<String, Object> mother = new LinkedHashMap<>();
        mother.put("first_name", "TestMother4");
        mother.put("last_name", "Fixture");
        Map<String, Object> father = new LinkedHashMap<>();
        father.put("existing_person_id", MIXED_PARENT_EXISTING_FATHER);
        father.put("first_name", "Bernard");
        father.put("last_name", "Borowiec");
        child.put("parent_mother", mother);
        child.put("parent_father", father);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "birth");
        payload.put("date", date(1881, null, null));
        payload.put("notes", "Layer 1 golden-master test fixture");
        payload.put("participants", List.of(child));

        AddEventResult result = service.addEvent(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_event_new_child_mixed_parent", result, before, after);

        AddEventResult.Success success = assertInstanceOf(AddEventResult.Success.class, result);
        assertEquals(2, success.newPersons().size());
        assertTrue(linkedTo(after, success.event().id()).contains(new Link(MIXED_PARENT_EXISTING_FATHER, "father")));
    }

    @Test
    void newChildConflictingFatherNotDeduplicated(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> child = new LinkedHashMap<>();
        child.put("first_name", "TestChild5");
        child.put("last_name", "Fixture");
        child.put("role", "child");
        Map<String, Object> newFather = new LinkedHashMap<>();
        newFather.put("first_name", "TestFather5");
        newFather.put("last_name", "Fixture");
        child.put("parent_father", newFather);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "birth");
        payload.put("date", date(1882, null, null));
        payload.put("notes", "Layer 1 golden-master test fixture");
        payload.put("participants", List.of(participant(CONFLICTING_FATHER, "father"), child));

        AddEventResult result = service.addEvent(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_event_new_child_conflicting_father", result, before, after);

        AddEventResult.Success success = assertInstanceOf(AddEventResult.Success.class, result);
        List<String> fathers = linkedTo(after, success.event().id()).stream()
                .filter(l -> l.role().equals("father"))
                .map(Link::personId)
                .toList();
        assertEquals(2, fathers.size());
        assertTrue(fathers.contains(CONFLICTING_FATHER));
    }

    @Test
    void newChildBothParentsAlreadyExisting(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> child = new LinkedHashMap<>();
        child.put("first_name", "TestChild6");
        child.put("last_name", "Fixture");
        child.put("role", "child");
        Map<String, Object> mother = new LinkedHashMap<>();
        mother.put("existing_person_id", UNRELATED_FEMALE);
        mother.put("first_name", "Marianna");
        mother.put("last_name", "Jarosz");
        Map<String, Object> father = new LinkedHashMap<>();
        father.put("existing_person_id", UNRELATED_MALE);
        father.put("first_name", "Bernard");
        father.put("last_name", "Borowiec");
        child.put("parent_mother", mother);
        child.put("parent_father", father);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "birth");
        payload.put("date", date(1883, null, null));
        payload.put("notes", "Layer 1 golden-master test fixture");
        payload.put("participants", List.of(child));

        AddEventResult result = service.addEvent(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_event_new_child_both_parents_existing", result, before, after);

        AddEventResult.Success success = assertInstanceOf(AddEventResult.Success.class, result);
        assertEquals(1, success.newPersons().size());
        Set<Link> linked = linkedTo(after, success.event().id());
        assertTrue(linked.contains(new Link(UNRELATED_FEMALE, "mother")));
        assertTrue(linked.contains(new Link(UNRELATED_MALE, "father")));

        boolean autoMarriageCreated = after.events().keySet().stream()
                .filter(id -> !before.events().containsKey(id))
                .anyMatch(id -> "marriage".equals(after.events().get(id).type()));
        assertTrue(autoMarriageCreated);
    }

    @Test
    void existingParentWithoutNameFieldsIsSilentlyDropped(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> child = new LinkedHashMap<>();
        child.put("first_name", "TestChild8");
        child.put("last_name", "Fixture");
        child.put("role", "child");
        Map<String, Object> mother = new LinkedHashMap<>();
        mother.put("existing_person_id", UNRELATED_FEMALE);
        child.put("parent_mother", mother);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "birth");
        payload.put("date", date(1885, null, null));
        payload.put("notes", "Layer 1 golden-master test fixture");
        payload.put("participants", List.of(child));

        AddEventResult result = service.addEvent(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden(
                "add_event_existing_parent_without_names_dropped", result, before, after);

        AddEventResult.Success success = assertInstanceOf(AddEventResult.Success.class, result);
        assertEquals(1, success.newPersons().size());
        Set<Link> linked = linkedTo(after, success.event().id());
        assertEquals(Set.of(new Link(success.newPersons().get(0).id(), "child")), linked);
        assertTrue(linked.stream().noneMatch(l -> l.personId().equals(UNRELATED_FEMALE)));
    }

    @Test
    void syncParentsToBirthEventsViaRoleSuffix(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "marriage");
        payload.put("date", date(1850, null, null));
        payload.put("notes", "Layer 1 golden-master test fixture");
        payload.put("participants", List.of(
                participant(SYNC_GROOM, "groom"),
                participant(SYNC_BRIDE, "bride"),
                participant(SYNC_GROOM_FATHER, "groom_parent_father")));

        AddEventResult result = service.addEvent(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_event_sync_parents_role_suffix", result, before, after);

        assertInstanceOf(AddEventResult.Success.class, result);
        List<String> newBirthEvents = after.events().keySet().stream()
                .filter(id -> !before.events().containsKey(id))
                .filter(id -> "birth".equals(after.events().get(id).type()))
                .toList();
        assertEquals(1, newBirthEvents.size());
        Set<Link> linked = linkedTo(after, newBirthEvents.get(0));
        assertTrue(linked.contains(new Link(SYNC_GROOM, "child")));
        assertTrue(linked.contains(new Link(SYNC_GROOM_FATHER, "father")));
    }

    @Test
    void plainMarriageEvent(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "marriage");
        payload.put("date", date(1850, null, null));
        payload.put("notes", "Layer 1 golden-master test fixture");
        payload.put("participants", List.of(
                participant(PLAIN_MARRIAGE_GROOM, "groom"), participant(PLAIN_MARRIAGE_BRIDE, "bride")));

        AddEventResult result = service.addEvent(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_event_plain_marriage", result, before, after);
        assertInstanceOf(AddEventResult.Success.class, result);
    }

    @Test
    void plainDeathEvent(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "death");
        payload.put("date", date(1850, null, null));
        payload.put("notes", "Layer 1 golden-master test fixture");
        payload.put("participants", List.of(participant(PLAIN_DEATH_DECEASED, "deceased")));

        AddEventResult result = service.addEvent(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_event_plain_death", result, before, after);
        assertInstanceOf(AddEventResult.Success.class, result);
    }

    @Test
    void plainGenericEvent(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "generic");
        payload.put("date", date(1850, null, null));
        payload.put("notes", "Layer 1 golden-master test fixture");
        payload.put("participants", List.of(participant(PLAIN_GENERIC_PARTICIPANT, "participant")));

        AddEventResult result = service.addEvent(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_event_plain_generic", result, before, after);
        assertInstanceOf(AddEventResult.Success.class, result);
    }

    @Test
    void createsNewPlace(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "generic");
        payload.put("date", date(1850, null, null));
        payload.put("place_name", NEW_PLACE_NAME);
        payload.put("house_number", NEW_PLACE_HOUSE_NUMBER);
        payload.put("notes", "Layer 1 golden-master test fixture");
        payload.put("participants", List.of(participant(PLAIN_GENERIC_PARTICIPANT, "participant")));

        AddEventResult result = service.addEvent(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_event_creates_new_place", result, before, after);

        assertInstanceOf(AddEventResult.Success.class, result);
        assertEquals(before.places().size() + 1, after.places().size());
    }

    @Test
    void reusesExistingPlace(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "generic");
        payload.put("date", date(1850, null, null));
        payload.put("place_name", EXISTING_PLACE_NAME);
        payload.put("house_number", EXISTING_PLACE_HOUSE_NUMBER);
        payload.put("notes", "Layer 1 golden-master test fixture");
        payload.put("participants", List.of(participant(PLAIN_GENERIC_PARTICIPANT, "participant")));

        AddEventResult result = service.addEvent(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_event_reuses_existing_place", result, before, after);

        assertInstanceOf(AddEventResult.Success.class, result);
        assertEquals(before.places().size(), after.places().size());
    }

    @Test
    void swapParticipantsOnExistingEvent(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("event_id", SWAP_EVENT);
        payload.put("type", "death");
        payload.put("date", date(1831, 2, 7));
        payload.put("place_name", SWAP_EVENT_PLACE_NAME);
        payload.put("house_number", SWAP_EVENT_PLACE_HOUSE_NUMBER);
        payload.put("notes", "Source line: 46");
        payload.put("tags", List.of());
        payload.put("links", List.of(
                "https://www.familysearch.org/ark:/61903/3:1:939V-T69C-NG?cc=1407440&lang=en&i=187"));
        payload.put("participants", List.of(
                participant(SWAP_KEEP_DECEASED, "deceased"),
                participant(SWAP_KEEP_WITNESS, "witness"),
                participant(SWAP_NEW_WITNESS, "witness")));

        UpdateEventResult result = service.updateEvent(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("update_event_swap_participants", result, before, after);

        assertInstanceOf(UpdateEventResult.Success.class, result);
        Set<String> oldParticipantIds = before.eventParticipations().values().stream()
                .filter(ep -> ep.eventId().equals(SWAP_EVENT)).map(EventParticipation::personId).collect(Collectors.toSet());
        Set<String> newParticipantIds = after.eventParticipations().values().stream()
                .filter(ep -> ep.eventId().equals(SWAP_EVENT)).map(EventParticipation::personId).collect(Collectors.toSet());
        assertTrue(oldParticipantIds.contains(SWAP_DROP_WITNESS));
        assertFalse(newParticipantIds.contains(SWAP_DROP_WITNESS));
        assertTrue(newParticipantIds.contains(SWAP_NEW_WITNESS));
    }

    @Test
    void newChildAndParentsOnExistingBirthEvent(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> child = new LinkedHashMap<>();
        child.put("first_name", "TestChild2");
        child.put("last_name", "Fixture");
        child.put("role", "child");
        Map<String, Object> mother = new LinkedHashMap<>();
        mother.put("first_name", "TestMother2");
        mother.put("last_name", "Fixture");
        Map<String, Object> father = new LinkedHashMap<>();
        father.put("first_name", "TestFather2");
        father.put("last_name", "Fixture");
        child.put("parent_mother", mother);
        child.put("parent_father", father);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("event_id", UPDATE_NEW_CHILD_EVENT);
        payload.put("type", "birth");
        payload.put("date", date(1802, null, null, true));
        payload.put("notes", "Migrated from person model (step 56.1)");
        payload.put("tags", List.of());
        payload.put("links", List.of());
        payload.put("participants", List.of(child));

        UpdateEventResult result = service.updateEvent(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("update_event_new_child_new_parents", result, before, after);

        UpdateEventResult.Success success = assertInstanceOf(UpdateEventResult.Success.class, result);
        assertEquals(3, success.newPersons().size());
        assertEquals(after.events().size(), before.events().size() + 1);
        Set<String> linkedRoles = linkedTo(after, UPDATE_NEW_CHILD_EVENT).stream().map(Link::role).collect(Collectors.toSet());
        assertEquals(Set.of("child", "mother", "father"), linkedRoles);
        assertEquals("child: TestChild2 Fixture", success.event().content());
    }

    @Test
    void swapParticipantsAndNewChildCombined(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot preSetup = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> setupPayload = new LinkedHashMap<>();
        setupPayload.put("type", "birth");
        setupPayload.put("date", date(1884, null, null));
        setupPayload.put("notes", "Layer 1 golden-master test fixture (setup)");
        setupPayload.put("participants", List.of(
                participant(COMBINED_SETUP_CHILD, "child"),
                participant(COMBINED_WITNESS_1, "witness"),
                participant(COMBINED_WITNESS_2, "witness")));

        AddEventResult setupResult = service.addEvent(setupPayload);
        AddEventResult.Success setupSuccess = assertInstanceOf(AddEventResult.Success.class, setupResult);
        String targetEventId = setupSuccess.event().id();
        EntitySnapshot postSetup = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> setupDiff = GoldenFileTestSupport.stateDiff(preSetup, postSetup);

        Map<String, Object> child = new LinkedHashMap<>();
        child.put("first_name", "TestChild7");
        child.put("last_name", "Fixture");
        child.put("role", "child");
        Map<String, Object> mother = new LinkedHashMap<>();
        mother.put("first_name", "TestMother7");
        mother.put("last_name", "Fixture");
        Map<String, Object> father = new LinkedHashMap<>();
        father.put("first_name", "TestFather7");
        father.put("last_name", "Fixture");
        child.put("parent_mother", mother);
        child.put("parent_father", father);

        Map<String, Object> updatePayload = new LinkedHashMap<>();
        updatePayload.put("event_id", targetEventId);
        updatePayload.put("type", "birth");
        updatePayload.put("date", date(1884, null, null));
        updatePayload.put("notes", "Layer 1 golden-master test fixture (setup)");
        updatePayload.put("tags", List.of());
        updatePayload.put("links", List.of());
        updatePayload.put("participants", List.of(
                participant(COMBINED_WITNESS_1, "witness"),
                participant(COMBINED_WITNESS_2, "witness"),
                child));

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        UpdateEventResult result = service.updateEvent(updatePayload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden(
                "update_event_swap_and_new_child_combined", result, before, after, List.of(setupDiff));

        UpdateEventResult.Success success = assertInstanceOf(UpdateEventResult.Success.class, result);
        assertEquals(3, success.newPersons().size());

        Set<Link> finalParticipants = linkedTo(after, targetEventId);
        assertTrue(finalParticipants.contains(new Link(COMBINED_WITNESS_1, "witness")));
        assertTrue(finalParticipants.contains(new Link(COMBINED_WITNESS_2, "witness")));
        assertTrue(finalParticipants.stream().noneMatch(l -> l.personId().equals(COMBINED_SETUP_CHILD)));
        Set<String> roles = finalParticipants.stream().map(Link::role).collect(Collectors.toSet());
        assertEquals(Set.of("witness", "child", "mother", "father"), roles);
        assertEquals(after.eventParticipations().size(), before.eventParticipations().size() + 4);
    }

    @Test
    void nonexistentEventIdFailsCleanly(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("event_id", NONEXISTENT_EVENT_ID);
        payload.put("type", "generic");
        payload.put("date", null);
        payload.put("participants", List.of());

        UpdateEventResult result = service.updateEvent(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        assertEquals(new UpdateEventResult.Failure("Event " + NONEXISTENT_EVENT_ID + " not found"), result);
        assertEquals(before, after);
    }

    @Test
    void deletesEventAndAllItsParticipations(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        DeleteEventResult result = service.deleteEvent(Map.of("event_id", DELETE_EVENT_ID));
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("delete_event_removes_participations", result, before, after);

        DeleteEventResult.Success success = assertInstanceOf(DeleteEventResult.Success.class, result);
        assertEquals(3, success.deletedParticipations());
        assertFalse(after.events().containsKey(DELETE_EVENT_ID));
        assertEquals(before.persons(), after.persons());
    }

    @Test
    void deleteEventNonexistentFailsCleanly(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        EventService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        DeleteEventResult result = service.deleteEvent(Map.of("event_id", NONEXISTENT_EVENT_ID));
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        assertEquals(new DeleteEventResult.Failure("Event not found"), result);
        assertEquals(before, after);
    }
}
