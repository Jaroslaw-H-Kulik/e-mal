package com.emal.genealogy.service;

import com.emal.genealogy.model.Event;
import com.emal.genealogy.model.EventParticipation;
import com.emal.genealogy.model.FlexibleDate;
import com.emal.genealogy.model.Person;
import com.emal.genealogy.model.Place;
import com.emal.genealogy.repository.GenealogyRepository;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

/**
 * Ports GenealogyRepository.add_event/update_event (app/genealogy_repository.py),
 * including the sync_parents_to_birth_events/sync_ages_to_birth_years
 * helpers both call unconditionally and the create_parent_marriage_if_needed
 * call for birth events - see each private method's javadoc for which
 * Python method it mirrors.
 *
 * `eventData` is a typed {@link AddEventRequest}/{@link UpdateEventRequest}
 * (each participant an {@link EventParticipantRequest}) - see
 * AddPersonRequest's javadoc for the general DTO-over-Map rationale.
 */
@Component
public class EventService {

    private final GenealogyRepository repository;
    private final IdGenerator idGenerator;
    private final PlaceResolver placeResolver;
    private final EventLookup eventLookup;
    private final ParentMarriageService parentMarriageService;

    public EventService(
            GenealogyRepository repository, IdGenerator idGenerator, PlaceResolver placeResolver,
            EventLookup eventLookup, ParentMarriageService parentMarriageService) {
        this.repository = repository;
        this.idGenerator = idGenerator;
        this.placeResolver = placeResolver;
        this.eventLookup = eventLookup;
        this.parentMarriageService = parentMarriageService;
    }

    public AddEventResult addEvent(AddEventRequest eventData) {
        try {
            Map<String, Person> persons = repository.persons();
            Map<String, Place> places = repository.places();
            Map<String, Event> events = repository.events();
            Map<String, EventParticipation> eventParticipations = repository.eventParticipations();

            String eventId = idGenerator.nextEventId(events);
            String placeId = placeResolver.handlePlace(places, eventData.placeName(), eventData.houseNumber());

            String eventType = eventData.type();
            Event newEvent = new Event(
                    eventId, eventType, DateRequest.toFlexibleDateOrNull(eventData.date()),
                    placeId, "", null, eventData.title(), null, eventData.notes(),
                    eventData.tags(), eventData.links(), null);
            events.put(eventId, newEvent);

            List<String> contentParts = new ArrayList<>();
            List<Person> newPersons = new ArrayList<>();

            for (EventParticipantRequest participant : eventData.participants()) {
                processParticipant(participant, eventId, eventType, persons, events, eventParticipations, newPersons, contentParts);
            }

            String explicitContent = eventData.content();
            String finalContent = explicitContent != null
                    ? explicitContent
                    : (contentParts.isEmpty() ? "Event created" : String.join(", ", contentParts));
            newEvent = new Event(
                    newEvent.id(), newEvent.type(), newEvent.date(), newEvent.placeId(), finalContent,
                    newEvent.description(), newEvent.title(), newEvent.source(), newEvent.notes(),
                    newEvent.tags(), newEvent.links(), null);
            events.put(eventId, newEvent);

            syncParentsToBirthEvents(eventData.participants(), persons, events, eventParticipations);
            syncAgesToBirthYears(eventId, eventData.date(), eventData.participants(), persons, events, eventParticipations);

            if ("birth".equals(newEvent.type())) {
                parentMarriageService.createIfNeeded(events, eventParticipations, eventId, persons);
            }

            repository.save();

            return new AddEventResult.Success(newEvent, newPersons);
        } catch (RuntimeException e) {
            return new AddEventResult.Failure(e.getMessage());
        }
    }

    /**
     * Ports update_event (app/genealogy_repository.py). Unlike add_event,
     * this mutates an existing event record in place - type/title/date/
     * tags/links/notes/place_id are all unconditionally overwritten
     * (with the same request-map defaults add_event uses), but content/
     * description/source are left as whatever the existing event already
     * had until content is recomputed after the participant loop (content)
     * or never touched at all (description/source - update_event has no
     * code path that reassigns either). The participant list is fully
     * replaced (old participations deleted, new ones built via the same
     * {@link #processParticipant} helper add_event uses), and the
     * shared sync/parent-marriage helpers are reused unchanged.
     */
    public UpdateEventResult updateEvent(UpdateEventRequest eventData) {
        try {
            Map<String, Person> persons = repository.persons();
            Map<String, Place> places = repository.places();
            Map<String, Event> events = repository.events();
            Map<String, EventParticipation> eventParticipations = repository.eventParticipations();

            String eventId = eventData.eventId();
            if (eventId == null || !events.containsKey(eventId)) {
                return new UpdateEventResult.Failure("Event " + eventId + " not found");
            }

            Event existing = events.get(eventId);
            String eventType = eventData.type();
            String placeId = placeResolver.handlePlace(places, eventData.placeName(), eventData.houseNumber());

            Event event = new Event(
                    existing.id(), eventType, DateRequest.toFlexibleDateOrNull(eventData.date()),
                    placeId, existing.content(), existing.description(),
                    eventData.title(), existing.source(), eventData.notes(),
                    eventData.tags(), eventData.links(), null);
            events.put(eventId, event);

            for (String oldEpId : eventParticipations.entrySet().stream()
                    .filter(entry -> entry.getValue().eventId().equals(eventId))
                    .map(Map.Entry::getKey)
                    .toList()) {
                eventParticipations.remove(oldEpId);
            }

            List<String> contentParts = new ArrayList<>();
            List<Person> newPersons = new ArrayList<>();

            for (EventParticipantRequest participant : eventData.participants()) {
                processParticipant(participant, eventId, eventType, persons, events, eventParticipations, newPersons, contentParts);
            }

            String explicitContent = eventData.content();
            String finalContent = explicitContent != null
                    ? explicitContent
                    : (contentParts.isEmpty() ? "Event updated" : String.join(", ", contentParts));
            event = new Event(
                    event.id(), event.type(), event.date(), event.placeId(), finalContent,
                    event.description(), event.title(), event.source(), event.notes(),
                    event.tags(), event.links(), null);
            events.put(eventId, event);

            syncParentsToBirthEvents(eventData.participants(), persons, events, eventParticipations);
            syncAgesToBirthYears(eventId, eventData.date(), eventData.participants(), persons, events, eventParticipations);

            if ("birth".equals(event.type())) {
                parentMarriageService.createIfNeeded(events, eventParticipations, eventId, persons);
            }

            List<Person> modifiedPersons = new ArrayList<>();
            for (EventParticipantRequest participant : eventData.participants()) {
                String pid = participant.existingPersonId();
                if (pid != null && persons.containsKey(pid) && isTruthy(participant.maidenName())) {
                    modifiedPersons.add(persons.get(pid));
                }
            }

            repository.save();

            Map<String, EventParticipation> updatedParticipations = new LinkedHashMap<>();
            for (Map.Entry<String, EventParticipation> entry : eventParticipations.entrySet()) {
                if (entry.getValue().eventId().equals(eventId)) {
                    updatedParticipations.put(entry.getKey(), entry.getValue());
                }
            }

            return new UpdateEventResult.Success(event, updatedParticipations, newPersons, modifiedPersons);
        } catch (RuntimeException e) {
            return new UpdateEventResult.Failure(e.getMessage());
        }
    }

    /**
     * Ports delete_event (app/genealogy_repository.py): removes the event
     * and every event_participations entry for it. Never touches the
     * persons collection - unlike delete_person, which cascades the other
     * direction (see test_delete_event.py's docstring).
     */
    public DeleteEventResult deleteEvent(DeleteEventRequest requestData) {
        try {
            Map<String, Event> events = repository.events();
            Map<String, EventParticipation> eventParticipations = repository.eventParticipations();

            String eventId = requestData.eventId();
            if (eventId == null || !events.containsKey(eventId)) {
                return new DeleteEventResult.Failure("Event not found");
            }

            events.remove(eventId);

            List<String> epsToDelete = eventParticipations.entrySet().stream()
                    .filter(entry -> entry.getValue().eventId().equals(eventId))
                    .map(Map.Entry::getKey)
                    .toList();
            for (String epId : epsToDelete) {
                eventParticipations.remove(epId);
            }

            repository.save();

            return new DeleteEventResult.Success(epsToDelete.size());
        } catch (RuntimeException e) {
            return new DeleteEventResult.Failure(e.getMessage());
        }
    }

    /**
     * Shared by add_event and update_event's per-participant handling
     * (identical block in both Python methods): resolves the participant
     * to a person id - creating a brand-new person (plus any inline
     * parents, their auto-birth-event, and their auto-marriage-event) if
     * no existing_person_id was given but a first/last name was, or
     * applying name updates to an already-existing person otherwise -
     * then links whichever person id results to targetEventId under the
     * participant's role and appends to contentParts/newPersons.
     */
    private void processParticipant(
            EventParticipantRequest participant, String targetEventId, String eventType,
            Map<String, Person> persons, Map<String, Event> events, Map<String, EventParticipation> eventParticipations,
            List<Person> newPersons, List<String> contentParts) {
        String personId = participant.existingPersonId();
        boolean isExistingPerson = personId != null;

        String firstNameRaw = participant.firstName();
        String lastNameRaw = participant.lastName();
        String participantRole = participant.role();

        if (personId == null && isTruthy(firstNameRaw) && isTruthy(lastNameRaw)) {
            personId = createParticipantPersonWithParents(
                    participant, targetEventId, eventType, participantRole,
                    firstNameRaw, lastNameRaw,
                    persons, events, eventParticipations, newPersons);
        }

        if (isExistingPerson && persons.containsKey(personId)) {
            persons.put(personId, applyNameUpdates(persons.get(personId), participant));
        }

        if (personId != null) {
            String epId = idGenerator.nextEventParticipationId(eventParticipations);
            eventParticipations.put(epId, new EventParticipation(epId, targetEventId, personId, participantRole, null));

            Person person = persons.get(personId);
            String personName = person.firstName() + " " + person.lastName();
            Integer age = participant.age();
            if (isTruthy(age)) {
                personName += " (" + age + ")";
            }
            contentParts.add(participantRole + ": " + personName);
        }
    }

    /**
     * The "create a brand-new participant person" branch of
     * {@link #processParticipant} - a self-contained chunk shared verbatim
     * by add_event/update_event (app/genealogy_repository.py): creates the
     * person, any inline parent_mother/parent_father persons, links new
     * parents into targetEventId if this participant IS that event's own
     * birth (isChildInBirthEvent) or into their existing birth event, else
     * creates a fresh birth event for them; then a marriage event between
     * the two parents if both were created. Returns the new person's id.
     */
    private String createParticipantPersonWithParents(
            EventParticipantRequest participant, String targetEventId, String eventType, String participantRole,
            String firstName, String lastName,
            Map<String, Person> persons, Map<String, Event> events, Map<String, EventParticipation> eventParticipations,
            List<Person> newPersons) {
        String personId = idGenerator.nextPersonId(persons);

        FlexibleDate birthDate = null;
        Integer calculatedBirthYear = participant.calculatedBirthYear();
        if (isTruthy(calculatedBirthYear)) {
            birthDate = new FlexibleDate(calculatedBirthYear, null, null, true);
        }

        String participantGender = RequestValues.truthy(participant.gender());
        String inferredGender = participantGender != null ? participantGender : roleGender(participantRole);

        Person newPerson = new Person(
                personId, firstName, lastName, inferredGender,
                participant.maidenName(), participant.occupation(),
                List.of(), null, null);
        persons.put(personId, newPerson);
        newPersons.add(newPerson);

        Map<String, String> createdParents = new LinkedHashMap<>();
        createdParents.put("mother", null);
        createdParents.put("father", null);

        for (String parentType : List.of("mother", "father")) {
            EventParentRequest parentData = "mother".equals(parentType) ? participant.parentMother() : participant.parentFather();
            if (parentData != null && isTruthy(parentData.firstName()) && isTruthy(parentData.lastName())) {
                String parentId = isTruthy(parentData.existingPersonId()) ? parentData.existingPersonId() : null;
                if (parentId == null) {
                    parentId = idGenerator.nextPersonId(persons);
                    Person parentPerson = new Person(
                            parentId, parentData.firstName(), parentData.lastName(),
                            "mother".equals(parentType) ? "F" : "M",
                            parentData.maidenName(),
                            null, List.of(), null, null);
                    persons.put(parentId, parentPerson);
                    newPersons.add(parentPerson);
                }
                createdParents.put(parentType, parentId);
            }
        }

        boolean isChildInBirthEvent = "child".equals(participantRole) && "birth".equals(eventType);
        String existingBirthEventId = eventLookup.findBirthEventForPerson(events, eventParticipations, personId);

        if (isChildInBirthEvent) {
            linkNewParentsToEvent(eventParticipations, targetEventId, createdParents);
        } else if (existingBirthEventId != null) {
            linkNewParentsToEvent(eventParticipations, existingBirthEventId, createdParents);
        } else {
            String birthEventId = idGenerator.nextEventId(events);
            Event birthEvent = new Event(
                    birthEventId, "birth", birthDate, null, "",
                    "Birth of " + firstName + " " + lastName, null, null,
                    "Auto-generated from event participation", List.of(), List.of(), null);
            events.put(birthEventId, birthEvent);

            String childEpId = idGenerator.nextEventParticipationId(eventParticipations);
            eventParticipations.put(childEpId, new EventParticipation(childEpId, birthEventId, personId, "child", null));

            for (Map.Entry<String, String> entry : createdParents.entrySet()) {
                if (entry.getValue() != null) {
                    String epId = idGenerator.nextEventParticipationId(eventParticipations);
                    eventParticipations.put(
                            epId, new EventParticipation(epId, birthEventId, entry.getValue(), entry.getKey(), null));
                }
            }
        }

        String motherId = createdParents.get("mother");
        String fatherId = createdParents.get("father");
        if (motherId != null && fatherId != null) {
            String marriageEventId = idGenerator.nextEventId(events);
            Person mother = persons.get(motherId);
            Person father = persons.get(fatherId);
            Event marriageEvent = new Event(
                    marriageEventId, "marriage", null, null, "",
                    "Marriage of " + father.firstName() + " " + father.lastName()
                            + " and " + mother.firstName() + " " + mother.lastName(),
                    null, null, "Auto-generated from child birth event", List.of(), List.of(), null);
            events.put(marriageEventId, marriageEvent);

            String groomEpId = idGenerator.nextEventParticipationId(eventParticipations);
            eventParticipations.put(groomEpId, new EventParticipation(groomEpId, marriageEventId, fatherId, "groom", null));
            String brideEpId = idGenerator.nextEventParticipationId(eventParticipations);
            eventParticipations.put(brideEpId, new EventParticipation(brideEpId, marriageEventId, motherId, "bride", null));
        }

        return personId;
    }

    private static String roleGender(String role) {
        return switch (role == null ? "" : role) {
            case "groom", "father" -> "M";
            case "bride", "mother" -> "F";
            default -> "U";
        };
    }

    private static boolean isTruthy(String value) {
        return value != null && !value.isEmpty();
    }

    private static boolean isTruthy(Integer value) {
        return value != null && value != 0;
    }

    private void linkNewParentsToEvent(
            Map<String, EventParticipation> eventParticipations, String targetEventId, Map<String, String> createdParents) {
        for (Map.Entry<String, String> entry : createdParents.entrySet()) {
            String parentType = entry.getKey();
            String parentId = entry.getValue();
            if (parentId == null) {
                continue;
            }
            String finalParentId = parentId;
            boolean alreadyParticipant = eventParticipations.values().stream()
                    .anyMatch(ep -> ep.eventId().equals(targetEventId) && ep.personId().equals(finalParentId));
            if (!alreadyParticipant) {
                String epId = idGenerator.nextEventParticipationId(eventParticipations);
                eventParticipations.put(epId, new EventParticipation(epId, targetEventId, parentId, parentType, null));
            }
        }
    }

    /** Mirrors add_event/update_event's "Update name fields for existing persons if changed in the form" block. */
    private static Person applyNameUpdates(Person existing, EventParticipantRequest participant) {
        Person updated = existing;

        String lastName = participant.lastName();
        String trimmedLastName = lastName == null ? "" : lastName.strip();
        if (!trimmedLastName.isEmpty() && !trimmedLastName.equals(updated.lastName())) {
            updated = new Person(
                    updated.id(), updated.firstName(), trimmedLastName, updated.gender(), updated.maidenName(),
                    updated.occupation(), updated.tags(), updated.notes(), updated.extra());
        }

        String maidenName = participant.maidenName();
        String trimmedMaidenName = maidenName == null ? "" : maidenName.strip();
        if (!trimmedMaidenName.isEmpty() && !trimmedMaidenName.equals(updated.maidenName())) {
            updated = new Person(
                    updated.id(), updated.firstName(), updated.lastName(), updated.gender(), trimmedMaidenName,
                    updated.occupation(), updated.tags(), updated.notes(), updated.extra());
        }

        return updated;
    }

    /**
     * Ports sync_parents_to_birth_events (app/genealogy_repository.py):
     * a participant supplied as a second top-level entry with role
     * "&lt;main_role&gt;_parent_&lt;father|mother&gt;" (both sides via
     * existing_person_id only) gets linked into the main person's birth
     * event. Best-effort like the Python original - swallows exceptions
     * rather than failing the whole add-event/update-event call. Shared by
     * both.
     */
    private void syncParentsToBirthEvents(
            List<EventParticipantRequest> participants, Map<String, Person> persons,
            Map<String, Event> events, Map<String, EventParticipation> eventParticipations) {
        try {
            record ParentSync(String childId, String parentId, String parentRole) {
            }
            List<ParentSync> parentRolesToSync = new ArrayList<>();

            for (EventParticipantRequest participant : participants) {
                String role = participant.role();
                if (role == null) {
                    role = "";
                }
                String personId = participant.existingPersonId();

                if (role.contains("_parent_")) {
                    String[] parts = role.split("_parent_", -1);
                    if (parts.length == 2) {
                        String mainRole = parts[0];
                        String parentType = parts[1];
                        String mainPersonId = null;
                        for (EventParticipantRequest p : participants) {
                            if (mainRole.equals(p.role())) {
                                mainPersonId = p.existingPersonId();
                                break;
                            }
                        }
                        if (mainPersonId != null && personId != null) {
                            parentRolesToSync.add(new ParentSync(mainPersonId, personId, parentType));
                        }
                    }
                }
            }

            for (ParentSync sync : parentRolesToSync) {
                String birthEventId = eventLookup.findBirthEventForPerson(events, eventParticipations, sync.childId());

                if (birthEventId == null) {
                    Person child = persons.get(sync.childId());
                    if (child == null) {
                        continue;
                    }
                    birthEventId = idGenerator.nextEventId(events);
                    Event birthEvent = new Event(
                            birthEventId, "birth", null, null, "",
                            "Birth of " + child.firstName() + " " + child.lastName(),
                            null, null, "Auto-generated for parent synchronization", List.of(), List.of(), null);
                    events.put(birthEventId, birthEvent);

                    String childEpId = idGenerator.nextEventParticipationId(eventParticipations);
                    eventParticipations.put(
                            childEpId, new EventParticipation(childEpId, birthEventId, sync.childId(), "child", null));
                }

                String finalBirthEventId = birthEventId;
                boolean parentExists = eventParticipations.values().stream().anyMatch(ep ->
                        ep.eventId().equals(finalBirthEventId)
                                && sync.parentRole().equals(ep.role())
                                && sync.parentId().equals(ep.personId()));

                if (!parentExists) {
                    boolean slotTaken = eventParticipations.values().stream().anyMatch(ep ->
                            ep.eventId().equals(finalBirthEventId) && sync.parentRole().equals(ep.role()));
                    if (!slotTaken) {
                        String epId = idGenerator.nextEventParticipationId(eventParticipations);
                        eventParticipations.put(
                                epId, new EventParticipation(epId, finalBirthEventId, sync.parentId(), sync.parentRole(), null));
                    }
                }
            }
        } catch (RuntimeException e) {
            // Mirror Python: don't fail the whole event operation if sync fails.
        }
    }

    /**
     * Ports sync_ages_to_birth_years, "Step 21"/"Step 29"
     * (app/genealogy_repository.py): when a participant carries an age
     * and the main event has a year, calculates and writes/creates their
     * birth year. Best-effort like the Python original. Shared by
     * add_event and update_event.
     */
    private void syncAgesToBirthYears(
            String eventId, DateRequest eventDate, List<EventParticipantRequest> participants, Map<String, Person> persons,
            Map<String, Event> events, Map<String, EventParticipation> eventParticipations) {
        try {
            if (eventDate == null || !isTruthy(eventDate.year())) {
                return;
            }
            int eventYear = eventDate.year();

            for (EventParticipantRequest participant : participants) {
                Integer ageRaw = participant.age();
                String personId = participant.existingPersonId();

                if (isTruthy(ageRaw) && personId != null && persons.containsKey(personId)) {
                    int age = ageRaw;
                    FlexibleDate calculatedDate = new FlexibleDate(eventYear - age, null, null, true);

                    String birthEventId = eventLookup.findBirthEventForPerson(events, eventParticipations, personId);
                    if (birthEventId != null) {
                        Event existing = events.get(birthEventId);
                        events.put(birthEventId, new Event(
                                existing.id(), existing.type(), calculatedDate, existing.placeId(), existing.content(),
                                existing.description(), existing.title(), existing.source(), existing.notes(),
                                existing.tags(), existing.links(), null));
                    } else {
                        String newBirthEventId = idGenerator.nextEventId(events);
                        Person person = persons.get(personId);
                        Event birthEvent = new Event(
                                newBirthEventId, "birth", calculatedDate, null, "",
                                "Birth of " + person.firstName() + " " + person.lastName(),
                                null, null, "Auto-generated from age " + age + " in event " + eventId,
                                List.of(), List.of(), null);
                        events.put(newBirthEventId, birthEvent);

                        String epId = idGenerator.nextEventParticipationId(eventParticipations);
                        eventParticipations.put(epId, new EventParticipation(epId, newBirthEventId, personId, "child", null));
                    }
                }
            }
        } catch (RuntimeException e) {
            // Mirror Python: don't fail the whole event operation if sync fails.
        }
    }
}
