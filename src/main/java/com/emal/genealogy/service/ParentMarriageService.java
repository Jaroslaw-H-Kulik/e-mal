package com.emal.genealogy.service;

import com.emal.genealogy.model.Event;
import com.emal.genealogy.model.EventParticipation;
import com.emal.genealogy.model.FlexibleDate;
import com.emal.genealogy.model.Person;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

/**
 * Ports GenealogyRepository.create_parent_marriage_if_needed
 * (app/genealogy_repository.py, "Step 13") - auto-creates a marriage
 * event between a birth event's father and mother participants if both
 * are present and no marriage event between them already exists. Used by
 * add-event (birth events) and add-relationship (step 5, not yet
 * ported).
 */
@Component
public class ParentMarriageService {

    private final IdGenerator idGenerator;
    private final EventLookup eventLookup;

    public ParentMarriageService(IdGenerator idGenerator, EventLookup eventLookup) {
        this.idGenerator = idGenerator;
        this.eventLookup = eventLookup;
    }

    /** Returns the created (or pre-existing) marriage event id, or null if the birth event doesn't have both parents. */
    public String createIfNeeded(
            Map<String, Event> events, Map<String, EventParticipation> eventParticipations,
            String birthEventId, Map<String, Person> persons) {
        String fatherId = null;
        String motherId = null;
        for (EventParticipation ep : eventParticipations.values()) {
            if (ep.eventId().equals(birthEventId)) {
                if ("father".equals(ep.role())) {
                    fatherId = ep.personId();
                } else if ("mother".equals(ep.role())) {
                    motherId = ep.personId();
                }
            }
        }

        if (fatherId == null || motherId == null) {
            return null;
        }

        String existingMarriage = eventLookup.findMarriageEventBetween(events, eventParticipations, fatherId, motherId);
        if (existingMarriage != null) {
            return null;
        }

        String marriageEventId = idGenerator.nextEventId(events);
        Person father = persons.get(fatherId);
        Person mother = persons.get(motherId);

        Event marriageEvent = new Event(
                marriageEventId, "marriage", (FlexibleDate) null, null, "",
                "Marriage of " + father.firstName() + " " + father.lastName()
                        + " and " + mother.firstName() + " " + mother.lastName(),
                null, null, "Auto-generated from birth event " + birthEventId + " (Step 30)", List.of(), List.of(), null);
        events.put(marriageEventId, marriageEvent);

        String groomEpId = idGenerator.nextEventParticipationId(eventParticipations);
        eventParticipations.put(groomEpId, new EventParticipation(groomEpId, marriageEventId, fatherId, "groom", null));

        String brideEpId = idGenerator.nextEventParticipationId(eventParticipations);
        eventParticipations.put(brideEpId, new EventParticipation(brideEpId, marriageEventId, motherId, "bride", null));

        return marriageEventId;
    }
}
