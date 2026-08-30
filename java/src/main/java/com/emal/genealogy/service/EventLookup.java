package com.emal.genealogy.service;

import com.emal.genealogy.model.Event;
import com.emal.genealogy.model.EventParticipation;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

/**
 * Ports GenealogyRepository's find_birth_event_for_person/
 * find_death_event_for_person/find_marriage_event_between
 * (app/genealogy_repository.py) - reused by add-event, update-event
 * (step 4), add-relationship (step 5), and the sync_* helpers.
 */
@Component
public class EventLookup {

    public String findBirthEventForPerson(Map<String, Event> events, Map<String, EventParticipation> eventParticipations, String personId) {
        return findEventForPersonInRole(events, eventParticipations, personId, "child", "birth");
    }

    public String findDeathEventForPerson(Map<String, Event> events, Map<String, EventParticipation> eventParticipations, String personId) {
        return findEventForPersonInRole(events, eventParticipations, personId, "deceased", "death");
    }

    private static String findEventForPersonInRole(
            Map<String, Event> events, Map<String, EventParticipation> eventParticipations,
            String personId, String role, String eventType) {
        for (EventParticipation ep : eventParticipations.values()) {
            if (ep.personId().equals(personId) && role.equals(ep.role())) {
                Event event = events.get(ep.eventId());
                if (event != null && eventType.equals(event.type())) {
                    return ep.eventId();
                }
            }
        }
        return null;
    }

    public String findMarriageEventBetween(
            Map<String, Event> events, Map<String, EventParticipation> eventParticipations,
            String person1Id, String person2Id) {
        List<String> person1Marriages = new ArrayList<>();
        for (EventParticipation ep : eventParticipations.values()) {
            if (ep.personId().equals(person1Id) && isSpouseRole(ep.role())) {
                Event event = events.get(ep.eventId());
                if (event != null && "marriage".equals(event.type())) {
                    person1Marriages.add(ep.eventId());
                }
            }
        }
        for (String eventId : person1Marriages) {
            for (EventParticipation ep : eventParticipations.values()) {
                if (ep.eventId().equals(eventId) && ep.personId().equals(person2Id) && isSpouseRole(ep.role())) {
                    return eventId;
                }
            }
        }
        return null;
    }

    private static boolean isSpouseRole(String role) {
        return "groom".equals(role) || "bride".equals(role);
    }
}
