package com.emal.genealogy.service;

import com.emal.genealogy.model.Event;
import com.emal.genealogy.model.EventParticipation;
import com.emal.genealogy.model.FlexibleDate;
import com.emal.genealogy.model.Person;
import com.emal.genealogy.model.Place;
import com.emal.genealogy.repository.GenealogyRepository;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import org.springframework.stereotype.Component;

/**
 * Ports GenealogyRepository.add_person (app/genealogy_repository.py) - see
 * that method's comments for Step 9's auto-birth/auto-death-event
 * behavior: every add-person call creates a birth event unconditionally,
 * and a death event only if death data was supplied.
 *
 * Every endpoint here takes a typed request record ({@link AddPersonRequest},
 * {@link UpdatePersonRequest}, {@link DeletePersonRequest}) - see
 * AddPersonRequest's javadoc for the general DTO-over-Map rationale.
 *
 * updatePerson used to be the one exception: its birth/death event-sync used
 * to branch on JSON key *presence* (real PATCH semantics no plain Java
 * record can express - Jackson 3's record binding collapses "key absent" and
 * "key present as null" to the same value, verified directly against this
 * project's JsonMapper). Fixed not by working around Jackson but by making
 * the endpoint a genuine PUT instead: the UI (editor.js's savePersonEdit)
 * now always sends every field, so there's no "was this key present"
 * question left to answer, and event-sync switched from presence-triggered
 * to change-detection - {@link #syncLifeEvent} only touches/reports a
 * birth or death event when the computed new date/place actually differs
 * from what's stored, rather than whenever the relevant keys were present.
 * This is a deliberate, Java-only behavior improvement over
 * `app/genealogy_repository.py`'s `update_person` (which still has the old
 * presence-based quirk) - see JAVA_MIGRATION.md's `update-person` divergence
 * entry for why this one endpoint isn't kept in Python/Java parity.
 */
@Component
public class PersonService {

    private final GenealogyRepository repository;
    private final IdGenerator idGenerator;
    private final PlaceResolver placeResolver;
    private final EventLookup eventLookup;

    public PersonService(GenealogyRepository repository, IdGenerator idGenerator, PlaceResolver placeResolver, EventLookup eventLookup) {
        this.repository = repository;
        this.idGenerator = idGenerator;
        this.placeResolver = placeResolver;
        this.eventLookup = eventLookup;
    }

    public AddPersonResult addPerson(AddPersonRequest personData) {
        try {
            Map<String, Person> persons = repository.persons();
            Map<String, Place> places = repository.places();
            Map<String, Event> events = repository.events();
            Map<String, EventParticipation> eventParticipations = repository.eventParticipations();

            String newId = idGenerator.nextPersonId(persons);

            String firstName = personData.givenName();
            String lastName = personData.surname();
            String gender = personData.gender();
            String maidenName = personData.maidenName();
            String occupation = personData.occupation();
            List<String> tags = personData.tags();
            String notes = personData.notes();

            Person newPerson = new Person(newId, firstName, lastName, gender, maidenName, occupation, tags, notes, null);
            persons.put(newId, newPerson);

            FlexibleDate birthDate = resolveYearEstimate(personData.birthYearEstimate());
            FlexibleDate deathDate = resolveYearEstimate(personData.deathYearEstimate());

            Map<String, Event> newEvents = new LinkedHashMap<>();
            Map<String, EventParticipation> newParticipations = new LinkedHashMap<>();

            String placeOfBirth = personData.placeOfBirth();
            String birthPlaceId = placeOfBirth == null ? null : placeResolver.resolveByNameOnly(places, placeOfBirth);

            String birthEventId = idGenerator.nextEventId(events);
            Event birthEvent = new Event(
                    birthEventId, "birth", birthDate, birthPlaceId, null,
                    "Birth of " + firstName + " " + lastName, null, null,
                    "Auto-generated from person creation", List.of(), List.of(), null);
            events.put(birthEventId, birthEvent);

            String birthEpId = idGenerator.nextEventParticipationId(eventParticipations);
            EventParticipation birthEp = new EventParticipation(birthEpId, birthEventId, newId, "child", null);
            eventParticipations.put(birthEpId, birthEp);

            newEvents.put(birthEventId, birthEvent);
            newParticipations.put(birthEpId, birthEp);

            String placeOfDeath = personData.placeOfDeath();
            if (deathDate != null || placeOfDeath != null) {
                String deathPlaceId = placeOfDeath == null ? null : placeResolver.resolveByNameOnly(places, placeOfDeath);

                String deathEventId = idGenerator.nextEventId(events);
                Event deathEvent = new Event(
                        deathEventId, "death", deathDate, deathPlaceId, null,
                        "Death of " + firstName + " " + lastName, null, null,
                        "Auto-generated from person creation", List.of(), List.of(), null);
                events.put(deathEventId, deathEvent);

                String deathEpId = idGenerator.nextEventParticipationId(eventParticipations);
                EventParticipation deathEp = new EventParticipation(deathEpId, deathEventId, newId, "deceased", null);
                eventParticipations.put(deathEpId, deathEp);

                newEvents.put(deathEventId, deathEvent);
                newParticipations.put(deathEpId, deathEp);
            }

            repository.save();

            return new AddPersonResult.Success(newPerson, newEvents, newParticipations);
        } catch (RuntimeException e) {
            return new AddPersonResult.Failure(e.getMessage());
        }
    }

    /**
     * PUT semantics: every field is read straight off the request and
     * written unconditionally (see {@link #applyPersonFieldUpdates}), then
     * birth/death date+place are synced into the person's existing birth/
     * death event via change-detection ({@link #syncLifeEvent}) - creating
     * one if none exists and real data was supplied, touching/reporting an
     * existing one only if the computed new values actually differ from
     * what's stored. Person not found is a plain Failure, not an exception -
     * same rationale as AddPersonResult.
     */
    public UpdatePersonResult updatePerson(UpdatePersonRequest personData) {
        try {
            Map<String, Person> persons = repository.persons();
            Map<String, Place> places = repository.places();
            Map<String, Event> events = repository.events();
            Map<String, EventParticipation> eventParticipations = repository.eventParticipations();

            String personId = personData.personId();
            if (personId == null || !persons.containsKey(personId)) {
                return new UpdatePersonResult.Failure("Person not found");
            }

            Person person = applyPersonFieldUpdates(persons.get(personId), personData);
            persons.put(personId, person);

            List<String> updatedEvents = new ArrayList<>();

            String birthEventId = eventLookup.findBirthEventForPerson(events, eventParticipations, personId);
            String syncedBirth = syncLifeEvent(
                    events, eventParticipations, places, personId, person, birthEventId,
                    personData.birthDate(), personData.placeOfBirth(), "birth", "child", "Birth");
            if (syncedBirth != null) {
                updatedEvents.add(syncedBirth);
            }

            String deathEventId = eventLookup.findDeathEventForPerson(events, eventParticipations, personId);
            String syncedDeath = syncLifeEvent(
                    events, eventParticipations, places, personId, person, deathEventId,
                    personData.deathDate(), personData.placeOfDeath(), "death", "deceased", "Death");
            if (syncedDeath != null) {
                updatedEvents.add(syncedDeath);
            }

            repository.save();

            return new UpdatePersonResult.Success(person, updatedEvents);
        } catch (RuntimeException e) {
            return new UpdatePersonResult.Failure(e.getMessage());
        }
    }

    private static Person applyPersonFieldUpdates(Person person, UpdatePersonRequest personData) {
        return new Person(
                person.id(), personData.firstName(), personData.lastName(), personData.gender(),
                personData.maidenName(), personData.occupation(), personData.tags(), personData.notes(),
                person.extra());
    }

    /**
     * Change-detection sync for one of the birth/death event slots: resolves
     * the request's date/place, and either updates the existing event (only
     * if something actually differs from what's stored) or creates a fresh
     * one (only if there's real data and no existing event) - returns the
     * touched/created event's id, or null if nothing changed.
     *
     * <p>For an existing event, the place comparison is done by *name*, not
     * by re-resolving and comparing ids: {@link PlaceResolver#resolveByNameOnly}
     * matches case-insensitively against every place sharing that name and
     * returns the first one found, but this dataset has ~80 separate `Place`
     * records all named "Małyszyn" (one per house number) - re-resolving an
     * unchanged name would silently collapse whichever specific one an event
     * actually pointed to down to the first match, misreporting it as
     * "changed" on every save even when the user never touched the place
     * field. Comparing names first and only re-resolving when the name
     * genuinely differs avoids both the false "changed" signal and that
     * data-loss.
     */
    private String syncLifeEvent(
            Map<String, Event> events, Map<String, EventParticipation> eventParticipations, Map<String, Place> places,
            String personId, Person person, String existingEventId, DateRequest requestDate, String requestPlaceName,
            String eventType, String role, String labelVerb) {
        FlexibleDate newDate = DateRequest.toFlexibleDateOrNull(requestDate);

        if (existingEventId != null) {
            Event existing = events.get(existingEventId);
            String existingPlaceName = existing.placeId() == null ? null : places.get(existing.placeId()).name();
            boolean placeChanged = !namesEqual(requestPlaceName, existingPlaceName);
            boolean dateChanged = !Objects.equals(newDate, existing.date());
            if (!dateChanged && !placeChanged) {
                return null;
            }
            String placeId = placeChanged
                    ? (requestPlaceName == null ? null : placeResolver.resolveByNameOnly(places, requestPlaceName))
                    : existing.placeId();
            events.put(existingEventId, new Event(
                    existing.id(), existing.type(), newDate, placeId, existing.content(), existing.description(),
                    existing.title(), existing.source(), existing.notes(), existing.tags(), existing.links(), existing.extra()));
            return existingEventId;
        }

        String newPlaceId = requestPlaceName == null ? null : placeResolver.resolveByNameOnly(places, requestPlaceName);
        if (newDate == null && newPlaceId == null) {
            return null;
        }

        String eventId = idGenerator.nextEventId(events);
        Event event = new Event(
                eventId, eventType, newDate, newPlaceId, null,
                labelVerb + " of " + person.firstName() + " " + person.lastName(), null, null,
                "Auto-generated from person update", List.of(), List.of(), null);
        events.put(eventId, event);

        String epId = idGenerator.nextEventParticipationId(eventParticipations);
        eventParticipations.put(epId, new EventParticipation(epId, eventId, personId, role, null));

        return eventId;
    }

    /** Case-insensitive, null-safe - mirrors PlaceResolver.resolveByNameOnly's own matching rule. */
    private static boolean namesEqual(String a, String b) {
        if (a == null || b == null) {
            return a == b;
        }
        return a.equalsIgnoreCase(b);
    }

    /**
     * Ports delete_person (app/genealogy_repository.py): removes the
     * person, every event_participations entry for them, and cascades to
     * delete any event left with zero remaining participants as a result
     * (sorted by id for determinism - matches Python's {@code sorted()}
     * over a set, needed there to counter dict/set iteration order not
     * being guaranteed across runs, kept here for identical
     * `deleted_events` ordering). Has no guard against removing a
     * cardinality-required role (e.g. a marriage's only groom) - this is
     * intentional parity with a real, currently-unhandled data-integrity
     * gap in the Python original, not a Java-side omission; see
     * test_delete_person.py's docstring. The response carries no
     * `deleted_relationships`/`person_id` counters: family_relationships
     * isn't a top-level collection in the live JSON (see
     * FamilyRelationship's javadoc), so a relationship cascade count would
     * always be 0, and the caller already knows the id it sent - both were
     * dead weight inherited from the Python dict shape, dropped from both
     * sides together (see app/genealogy_repository.py's delete_person).
     */
    public DeletePersonResult deletePerson(DeletePersonRequest requestData) {
        try {
            Map<String, Person> persons = repository.persons();
            Map<String, Event> events = repository.events();
            Map<String, EventParticipation> eventParticipations = repository.eventParticipations();

            String personId = requestData.personId();
            if (personId == null || !persons.containsKey(personId)) {
                return new DeletePersonResult.Failure("Person not found");
            }

            persons.remove(personId);

            List<String> epsToDelete = eventParticipations.entrySet().stream()
                    .filter(entry -> entry.getValue().personId().equals(personId))
                    .map(Map.Entry::getKey)
                    .toList();

            Set<String> eventsToCheck = new LinkedHashSet<>();
            for (String epId : epsToDelete) {
                eventsToCheck.add(eventParticipations.get(epId).eventId());
                eventParticipations.remove(epId);
            }

            List<String> eventsDeleted = new ArrayList<>();
            for (String eventId : eventsToCheck.stream().sorted().toList()) {
                long remainingParticipants = eventParticipations.values().stream()
                        .filter(ep -> ep.eventId().equals(eventId))
                        .count();
                if (remainingParticipants == 0) {
                    events.remove(eventId);
                    eventsDeleted.add(eventId);
                }
            }

            repository.save();

            return new DeletePersonResult.Success(epsToDelete.size(), eventsDeleted);
        } catch (RuntimeException e) {
            return new DeletePersonResult.Failure(e.getMessage());
        }
    }

    

    /** Mirrors resolveDate's old isTruthy check on the raw map value: null or 0 both mean "no estimate". */
    private static FlexibleDate resolveYearEstimate(Integer yearEstimate) {
        if (yearEstimate == null || yearEstimate == 0) {
            return null;
        }
        return new FlexibleDate(yearEstimate, null, null, true);
    }
}
