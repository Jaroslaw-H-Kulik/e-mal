package com.emal.genealogy.service;

import com.emal.genealogy.model.Event;
import com.emal.genealogy.model.EventParticipation;
import com.emal.genealogy.model.Person;
import com.emal.genealogy.model.Place;
import java.util.Map;
import java.util.stream.Stream;
import org.springframework.stereotype.Component;

/**
 * Ports GenealogyRepository's get_next_*_id helpers
 * (app/genealogy_repository.py) - each entity's id is a fixed prefix plus a
 * 4-digit, strictly-increasing counter derived from the current max id in
 * the map (not a stored counter), so ids stay identical to what the Python
 * backend would generate from the same data.
 */
@Component
public class IdGenerator {

    public String nextPersonId(Map<String, Person> persons) {
        return nextId(persons.values().stream().map(Person::id), "P", 1);
    }

    public String nextEventId(Map<String, Event> events) {
        return nextId(events.values().stream().map(Event::id), "E", 1);
    }

    public String nextEventParticipationId(Map<String, EventParticipation> eventParticipations) {
        return nextId(eventParticipations.values().stream().map(EventParticipation::id), "EP", 2);
    }

    public String nextPlaceId(Map<String, Place> places) {
        return nextId(places.values().stream().map(Place::id), "PL", 2);
    }

    private static String nextId(Stream<String> existingIds, String prefix, int prefixLength) {
        int maxId = existingIds.mapToInt(id -> Integer.parseInt(id.substring(prefixLength))).max().orElse(0);
        return String.format("%s%04d", prefix, maxId + 1);
    }
}
