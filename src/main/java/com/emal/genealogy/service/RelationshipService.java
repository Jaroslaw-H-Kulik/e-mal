package com.emal.genealogy.service;

import com.emal.genealogy.model.Event;
import com.emal.genealogy.model.EventParticipation;
import com.emal.genealogy.model.Person;
import com.emal.genealogy.repository.GenealogyRepository;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;
import org.springframework.stereotype.Component;

/**
 * Ports GenealogyRepository.add_relationship, "Step 10"
 * (app/genealogy_repository.py). Despite its name, this never touches a
 * family_relationships collection - see FamilyRelationship's javadoc for
 * why that model exists but isn't wired into the repository. Every
 * relationship type is instead expressed by creating or reusing a birth or
 * marriage event and linking a participant into it, reusing the same
 * EventLookup/ParentMarriageService/IdGenerator components add-event and
 * update-event use.
 *
 * `relData` is a typed {@link AddRelationshipRequest} - but unlike the
 * add/update person/event endpoints, `base_person_id`/`target_person_id`/
 * `relationship_type`/`role` are all genuinely REQUIRED here: Python reads
 * each via direct dict indexing (`rel_data['role']`, etc.), so a missing
 * key raises KeyError and comes back as a plain `{'success': False}`
 * response (not a 500) via the method's own try/except. {@link #requireField}
 * mirrors that same error text on the DTO's (necessarily nullable, since a
 * record can't distinguish "key omitted" from "key present but null")
 * fields - see test_add_relationship.py::test_missing_role_key_fails_cleanly
 * for the pinned exact error text.
 */
@Component
public class RelationshipService {

    private final GenealogyRepository repository;
    private final IdGenerator idGenerator;
    private final EventLookup eventLookup;
    private final ParentMarriageService parentMarriageService;

    public RelationshipService(
            GenealogyRepository repository, IdGenerator idGenerator,
            EventLookup eventLookup, ParentMarriageService parentMarriageService) {
        this.repository = repository;
        this.idGenerator = idGenerator;
        this.eventLookup = eventLookup;
        this.parentMarriageService = parentMarriageService;
    }

    public AddRelationshipResult addRelationship(AddRelationshipRequest relData) {
        try {
            Map<String, Person> persons = repository.persons();
            Map<String, Event> events = repository.events();
            Map<String, EventParticipation> eventParticipations = repository.eventParticipations();

            String basePersonId = requireField("base_person_id", relData.basePersonId());
            String targetPersonId = requireField("target_person_id", relData.targetPersonId());
            String relType = requireField("relationship_type", relData.relationshipType());
            String role = requireField("role", relData.role());

            if (!persons.containsKey(basePersonId)) {
                return new AddRelationshipResult.Failure("Base person " + basePersonId + " not found");
            }
            if (!persons.containsKey(targetPersonId)) {
                return new AddRelationshipResult.Failure("Target person " + targetPersonId + " not found");
            }

            Person basePerson = persons.get(basePersonId);

            String createdEvent = null;
            String updatedEvent = null;

            switch (relType) {
                case "parent" -> {
                    BirthEventResult birthEvent = findOrCreateBirthEvent(events, eventParticipations, persons, basePersonId);
                    String epId = idGenerator.nextEventParticipationId(eventParticipations);
                    eventParticipations.put(
                            epId, new EventParticipation(epId, birthEvent.eventId(), targetPersonId, role, null));
                    parentMarriageService.createIfNeeded(events, eventParticipations, birthEvent.eventId(), persons);
                    if (birthEvent.created()) {
                        createdEvent = birthEvent.eventId();
                    } else {
                        updatedEvent = birthEvent.eventId();
                    }
                }
                case "child" -> {
                    String parentRole = determineParentRole(basePerson);
                    BirthEventResult birthEvent = findOrCreateBirthEvent(events, eventParticipations, persons, targetPersonId);
                    String epId = idGenerator.nextEventParticipationId(eventParticipations);
                    eventParticipations.put(
                            epId, new EventParticipation(epId, birthEvent.eventId(), basePersonId, parentRole, null));
                    parentMarriageService.createIfNeeded(events, eventParticipations, birthEvent.eventId(), persons);
                    if (birthEvent.created()) {
                        createdEvent = birthEvent.eventId();
                    } else {
                        updatedEvent = birthEvent.eventId();
                    }
                }
                case "spouse" -> {
                    String existingMarriage =
                            eventLookup.findMarriageEventBetween(events, eventParticipations, basePersonId, targetPersonId);
                    if (existingMarriage != null) {
                        updatedEvent = existingMarriage;
                    } else {
                        createdEvent = createMarriageEvent(events, eventParticipations, persons, basePersonId, targetPersonId);
                    }
                }
                case "godparent" -> {
                    BirthEventResult birthEvent = findOrCreateBirthEvent(events, eventParticipations, persons, basePersonId);
                    String epId = idGenerator.nextEventParticipationId(eventParticipations);
                    eventParticipations.put(
                            epId, new EventParticipation(epId, birthEvent.eventId(), targetPersonId, "godparent", null));
                    if (birthEvent.created()) {
                        createdEvent = birthEvent.eventId();
                    } else {
                        updatedEvent = birthEvent.eventId();
                    }
                }
                default -> {
                    return new AddRelationshipResult.Failure("Unknown relationship type: " + relType);
                }
            }

            repository.save();

            return new AddRelationshipResult.Success(createdEvent, updatedEvent);
        } catch (RuntimeException e) {
            return new AddRelationshipResult.Failure(e.getMessage());
        }
    }

    /** Mirrors RequestValues.requireString's Python-KeyError-shaped message for a field that's null (JSON key omitted). */
    private static String requireField(String key, String value) {
        if (value == null) {
            throw new NoSuchElementException("'" + key + "'");
        }
        return value;
    }

    private record BirthEventResult(String eventId, boolean created) {
    }

    /**
     * Shared by the parent/child/godparent branches (identical block in
     * the Python original): reuses childId's existing birth event, or
     * creates a fresh one (with childId linked as "child") if none exists.
     */
    private BirthEventResult findOrCreateBirthEvent(
            Map<String, Event> events, Map<String, EventParticipation> eventParticipations,
            Map<String, Person> persons, String childId) {
        String birthEventId = eventLookup.findBirthEventForPerson(events, eventParticipations, childId);
        if (birthEventId != null) {
            return new BirthEventResult(birthEventId, false);
        }

        birthEventId = idGenerator.nextEventId(events);
        Person child = persons.get(childId);
        Event birthEvent = new Event(
                birthEventId, "birth", null, null, null,
                "Birth of " + child.firstName() + " " + child.lastName(), null, null,
                "Auto-generated from relationship addition", List.of(), List.of(), null);
        events.put(birthEventId, birthEvent);

        String childEpId = idGenerator.nextEventParticipationId(eventParticipations);
        eventParticipations.put(childEpId, new EventParticipation(childEpId, birthEventId, childId, "child", null));

        return new BirthEventResult(birthEventId, true);
    }

    /** The spouse branch's "create new marriage event" path - gender-derived groom/bride roles, both participants linked. */
    private String createMarriageEvent(
            Map<String, Event> events, Map<String, EventParticipation> eventParticipations,
            Map<String, Person> persons, String person1Id, String person2Id) {
        String marriageEventId = idGenerator.nextEventId(events);
        Person person1 = persons.get(person1Id);
        Person person2 = persons.get(person2Id);

        Event marriageEvent = new Event(
                marriageEventId, "marriage", null, null, null,
                "Marriage of " + person1.firstName() + " " + person1.lastName()
                        + " and " + person2.firstName() + " " + person2.lastName(),
                null, null, "Auto-generated from relationship addition", List.of(), List.of(), null);
        events.put(marriageEventId, marriageEvent);

        for (Map.Entry<String, Person> pair : List.of(Map.entry(person1Id, person1), Map.entry(person2Id, person2))) {
            String epId = idGenerator.nextEventParticipationId(eventParticipations);
            String participantRole = "M".equals(pair.getValue().gender()) ? "groom" : "bride";
            eventParticipations.put(epId, new EventParticipation(epId, marriageEventId, pair.getKey(), participantRole, null));
        }

        return marriageEventId;
    }

    /** Mirrors determine_parent_role (app/genealogy_repository.py). */
    private static String determineParentRole(Person person) {
        return "M".equals(person.gender()) ? "father" : "mother";
    }
}
