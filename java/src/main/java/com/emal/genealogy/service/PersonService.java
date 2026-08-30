package com.emal.genealogy.service;

import static com.emal.genealogy.service.RequestValues.isTruthy;
import static com.emal.genealogy.service.RequestValues.stringOrDefault;
import static com.emal.genealogy.service.RequestValues.toInteger;
import static com.emal.genealogy.service.RequestValues.truthyString;

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
import java.util.Set;
import org.springframework.stereotype.Component;

/**
 * Ports GenealogyRepository.add_person (app/genealogy_repository.py) - see
 * that method's comments for Step 9's auto-birth/auto-death-event
 * behavior: every add-person call creates a birth event unconditionally,
 * and a death event only if death data was supplied.
 *
 * `personData` is handled as a raw request map, with the same
 * key-presence/fallback-chain semantics as Python's `.get()` calls,
 * rather than a strict DTO - the real Add Person form
 * (web/index.html's add-person-form) sends given_name/surname +
 * birth_year_estimate/death_year_estimate (see tests/test_add_person.py).
 * See RequestValues for the shared map-reading helpers.
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

    public AddPersonResult addPerson(Map<String, Object> personData) {
        try {
            Map<String, Person> persons = repository.persons();
            Map<String, Place> places = repository.places();
            Map<String, Event> events = repository.events();
            Map<String, EventParticipation> eventParticipations = repository.eventParticipations();

            String newId = idGenerator.nextPersonId(persons);

            String firstName = stringOrDefault(personData, "given_name", null, "");
            String lastName = stringOrDefault(personData, "surname", null, "");
            String gender = stringOrDefault(personData, "gender", null, "U");
            String maidenName = stringOrDefault(personData, "maiden_name", null, null);
            String occupation = stringOrDefault(personData, "occupation", "occupations", null);
            List<String> tags = tagsOrDefault(personData);
            String notes = notesOrNull(personData);

            Person newPerson = new Person(newId, firstName, lastName, gender, maidenName, occupation, tags, notes, null);
            persons.put(newId, newPerson);

            FlexibleDate birthDate = resolveDate(personData, "birth_year_estimate");
            FlexibleDate deathDate = resolveDate(personData, "death_year_estimate");

            List<String> createdEvents = new ArrayList<>();
            Map<String, Event> newEvents = new LinkedHashMap<>();
            Map<String, EventParticipation> newParticipations = new LinkedHashMap<>();

            String placeOfBirth = truthyString(personData, "place_of_birth");
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

            createdEvents.add(birthEventId);
            newEvents.put(birthEventId, birthEvent);
            newParticipations.put(birthEpId, birthEp);

            String placeOfDeath = truthyString(personData, "place_of_death");
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

                createdEvents.add(deathEventId);
                newEvents.put(deathEventId, deathEvent);
                newParticipations.put(deathEpId, deathEp);
            }

            repository.save();

            return new AddPersonResult.Success(
                    newPerson, createdEvents, newEvents, newParticipations, "Successfully added person " + newId);
        } catch (RuntimeException e) {
            return new AddPersonResult.Failure(e.getMessage());
        }
    }

    /**
     * Ports update_person, "Step 9 bidirectional sync" (app/genealogy_repository.py):
     * updates whichever person fields the request key-set touches (presence,
     * not truthiness - see {@link #applyPersonFieldUpdates}), then syncs
     * birth_date/place_of_birth and death_date/place_of_death into the
     * person's existing birth/death event (creating one if none exists and
     * real data was supplied). Person not found is a plain Failure, not an
     * exception - same rationale as AddPersonResult.
     */
    public UpdatePersonResult updatePerson(Map<String, Object> personData) {
        try {
            Map<String, Person> persons = repository.persons();
            Map<String, Place> places = repository.places();
            Map<String, Event> events = repository.events();
            Map<String, EventParticipation> eventParticipations = repository.eventParticipations();

            String personId = RequestValues.asStringOrNull(personData.get("person_id"));
            if (personId == null || !persons.containsKey(personId)) {
                return new UpdatePersonResult.Failure("Person not found");
            }

            Person person = applyPersonFieldUpdates(persons.get(personId), personData);
            persons.put(personId, person);

            List<String> updatedEvents = new ArrayList<>();

            if (personData.containsKey("birth_date") || personData.containsKey("place_of_birth")) {
                String birthEventId = eventLookup.findBirthEventForPerson(events, eventParticipations, personId);
                if (birthEventId != null) {
                    events.put(birthEventId, applyEventDateAndPlaceUpdate(
                            events.get(birthEventId), personData, "birth_date", "place_of_birth", places));
                    updatedEvents.add(birthEventId);
                } else if (RequestValues.isTruthy(personData.get("birth_date"))
                        || RequestValues.isTruthy(personData.get("place_of_birth"))) {
                    updatedEvents.add(createAutoLifeEvent(
                            events, eventParticipations, "birth", "child", "Birth",
                            personId, person, personData, "birth_date", "place_of_birth", places));
                }
            }

            if (personData.containsKey("death_date") || personData.containsKey("place_of_death")) {
                String deathEventId = eventLookup.findDeathEventForPerson(events, eventParticipations, personId);
                if (deathEventId != null) {
                    events.put(deathEventId, applyEventDateAndPlaceUpdate(
                            events.get(deathEventId), personData, "death_date", "place_of_death", places));
                    updatedEvents.add(deathEventId);
                } else if (RequestValues.isTruthy(personData.get("death_date"))
                        || RequestValues.isTruthy(personData.get("place_of_death"))) {
                    updatedEvents.add(createAutoLifeEvent(
                            events, eventParticipations, "death", "deceased", "Death",
                            personId, person, personData, "death_date", "place_of_death", places));
                }
            }

            repository.save();

            return new UpdatePersonResult.Success(person, updatedEvents, "Successfully updated person " + personId);
        } catch (RuntimeException e) {
            return new UpdatePersonResult.Failure(e.getMessage());
        }
    }

    /** Mirrors update_person's field-by-field block: each field updates only if its key is PRESENT in the request (not just truthy). */
    private static Person applyPersonFieldUpdates(Person person, Map<String, Object> personData) {
        String firstName = personData.containsKey("first_name")
                ? RequestValues.asStringOrNull(personData.get("first_name")) : person.firstName();
        String lastName = personData.containsKey("last_name")
                ? RequestValues.asStringOrNull(personData.get("last_name")) : person.lastName();
        String maidenName = personData.containsKey("maiden_name")
                ? RequestValues.asStringOrNull(personData.get("maiden_name")) : person.maidenName();
        String gender = personData.containsKey("gender")
                ? RequestValues.asStringOrNull(personData.get("gender")) : person.gender();
        String occupation = personData.containsKey("occupation")
                ? RequestValues.asStringOrNull(personData.get("occupation")) : person.occupation();
        List<String> tags = personData.containsKey("tags") ? RequestValues.stringList(personData.get("tags")) : person.tags();
        String notes = personData.containsKey("notes") ? RequestValues.truthy(personData.get("notes")) : person.notes();

        return new Person(person.id(), firstName, lastName, gender, maidenName, occupation, tags, notes, person.extra());
    }

    /** Mirrors update_person's "Update existing event" branch: date/place only change if their key is present AND truthy. */
    private Event applyEventDateAndPlaceUpdate(
            Event event, Map<String, Object> personData, String dateKey, String placeKey, Map<String, Place> places) {
        FlexibleDate date = event.date();
        if (personData.containsKey(dateKey) && RequestValues.isTruthy(personData.get(dateKey))) {
            date = RequestValues.toFlexibleDate(RequestValues.asMap(personData.get(dateKey)));
        }
        String placeId = event.placeId();
        if (personData.containsKey(placeKey) && RequestValues.isTruthy(personData.get(placeKey))) {
            placeId = placeResolver.resolveByNameOnly(places, personData.get(placeKey).toString());
        }
        return new Event(event.id(), event.type(), date, placeId, event.content(), event.description(),
                event.title(), event.source(), event.notes(), event.tags(), event.links(), event.extra());
    }

    /** Mirrors update_person's "Create event if data provided" branch, shared by the birth and death cases. */
    private String createAutoLifeEvent(
            Map<String, Event> events, Map<String, EventParticipation> eventParticipations,
            String eventType, String role, String labelVerb, String personId, Person person,
            Map<String, Object> personData, String dateKey, String placeKey, Map<String, Place> places) {
        FlexibleDate date = RequestValues.toFlexibleDate(RequestValues.asMap(personData.get(dateKey)));
        String placeId = null;
        if (RequestValues.isTruthy(personData.get(placeKey))) {
            placeId = placeResolver.resolveByNameOnly(places, personData.get(placeKey).toString());
        }

        String eventId = idGenerator.nextEventId(events);
        Event event = new Event(
                eventId, eventType, date, placeId, null,
                labelVerb + " of " + person.firstName() + " " + person.lastName(), null, null,
                "Auto-generated from person update", List.of(), List.of(), null);
        events.put(eventId, event);

        String epId = idGenerator.nextEventParticipationId(eventParticipations);
        eventParticipations.put(epId, new EventParticipation(epId, eventId, personId, role, null));

        return eventId;
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
     * test_delete_person.py's docstring. `deleted_relationships` is always
     * 0: family_relationships isn't a top-level collection in the live
     * JSON (see FamilyRelationship's javadoc), so GenealogyRepository has
     * no such map to cascade into - dead code for this dataset in Python
     * too, not a gap in this port.
     */
    public DeletePersonResult deletePerson(Map<String, Object> requestData) {
        try {
            Map<String, Person> persons = repository.persons();
            Map<String, Event> events = repository.events();
            Map<String, EventParticipation> eventParticipations = repository.eventParticipations();

            String personId = truthyString(requestData, "person_id");
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

            return new DeletePersonResult.Success(
                    personId, epsToDelete.size(), 0, eventsDeleted, "Successfully deleted person " + personId);
        } catch (RuntimeException e) {
            return new DeletePersonResult.Failure(e.getMessage());
        }
    }

    private static List<String> tagsOrDefault(Map<String, Object> data) {
        return RequestValues.stringList(data.get("tags"));
    }

    /** Mirrors {@code data.get('notes') or None}: absent key or empty string both collapse to null. */
    private static String notesOrNull(Map<String, Object> data) {
        return RequestValues.truthy(data.get("notes"));
    }

    private static FlexibleDate resolveDate(Map<String, Object> personData, String yearEstimateKey) {
        if (personData.containsKey(yearEstimateKey) && isTruthy(personData.get(yearEstimateKey))) {
            return new FlexibleDate(toInteger(personData.get(yearEstimateKey)), null, null, true);
        }
        return null;
    }
}
